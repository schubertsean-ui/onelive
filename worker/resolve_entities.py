"""Entity resolution for venues and artists.

Resolution priority (in order):
  1. exact match      — case-insensitive exact name match (city-scoped for venues).
  2. trigram fuzzy    — pg_trgm similarity above FUZZY_THRESHOLD (handles minor
                        spelling/spacing variants without creating a duplicate),
                        scoped by the same city filter as the exact-match step.
  3. placeholder      — get-or-create: insert a new row as a fallback.

These functions operate on a caller-supplied cursor and never open their own
connection or COMMIT. The caller (worker/promote.py) runs them inside the same
transaction as the event dedupe-check-and-insert, so if that transaction rolls
back (e.g. a duplicate is detected) any placeholder venue/artist rows created
here roll back too — otherwise repeated retries of a duplicate-blocked candidate
would orphan a fresh placeholder venue on every attempt (venue has no unique
name constraint).

Fuzzy matching uses the pg_trgm `%` operator (WHERE name %% <input>), which the
trigram GIN indexes in supabase/migrations/0005_pg_trgm.sql CAN serve; the older
`similarity(name, x) >= t` form forced a sequential scan. The match cutoff is set
per session via `SET pg_trgm.similarity_threshold` so the `%` operator honours it.

The `%` operator and `similarity()` are schema-qualified to `extensions`
(`OPERATOR(extensions.%%)` and `extensions.similarity(...)`) so resolution does
NOT depend on the connection's search_path. Migration 0006 relocates pg_trgm from
`public` to the `extensions` schema; on Supabase, role-level search_path settings
take precedence over the database-level `ALTER DATABASE ... SET search_path`, so we
cannot rely on that default including `extensions`. Qualifying at the call site is
what makes fuzzy matching resolve after the move (see the DB integration
test in tests/test_migration_0006_rls.py that connects WITHOUT extensions on the
search_path).
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/resolve_entities.py)
"""
import json
import logging
from typing import List, Optional, Tuple

import psycopg2
from psycopg2 import sql

logger = logging.getLogger(__name__)

# The only table/id-column pairs entity resolution is ever allowed to touch.
# _fuzzy_match composes identifiers via psycopg2.sql.Identifier (never string
# interpolation), and this allowlist is asserted at the call boundary so a
# caller can never smuggle an arbitrary identifier into composed SQL.
_RESOLVABLE = {
    "venue": "venue_id",
    "artist": "artist_id",
}

# Similarity in [0,1]; 0.45 tolerates minor variants ("Mohawk" vs "The Mohawk")
# while staying strict enough not to collapse genuinely different names.
FUZZY_THRESHOLD = 0.45


def _fuzzy_match(cur, table: str, id_col: str, name: str, threshold: float,
                 city: Optional[str] = None) -> Optional[Tuple[str, float]]:
    """Return (id, similarity) of the best trigram match for `name`, or None.

    Uses the pg_trgm `%` operator so the trigram GIN index is used, with the
    match cutoff set via `SET pg_trgm.similarity_threshold`. The operator and
    `similarity()` are schema-qualified to `extensions` so this resolves
    regardless of the connection's search_path (see module docstring). When
    `city` is provided the candidate set is scoped to that city (mirroring the
    exact-match step) so a same-named entity in another city can never be merged.

    Wrapped in a SAVEPOINT so a genuine "no match" degrades to exact + placeholder
    without aborting the caller's transaction. IMPORTANT: a schema-resolution
    failure (operator/function does not exist, SQLSTATE 42883) is NOT treated as a
    soft miss — it means the `extensions`-qualified pg_trgm objects are not
    reachable, which would silently collapse resolution to placeholder-only and
    spawn duplicate venue/artist rows. We log an error and re-raise those so the
    misconfiguration is loud, not invisible.
    """
    # Defense in depth: identifiers are composed with psycopg2.sql.Identifier
    # below, but we still refuse any table/id_col outside the known allowlist so
    # composed SQL can only ever name the two entity tables it is meant to.
    if _RESOLVABLE.get(table) != id_col:
        raise ValueError(f"refusing to resolve against unknown table/id_col: {table!r}/{id_col!r}")
    try:
        cur.execute("SAVEPOINT fuzzy_match")
        # SET does not accept a bound parameter for its value, so compose the
        # statement with psycopg2.sql (sql.Literal safely quotes the value)
        # rather than %-formatting a string. threshold is a float constant.
        cur.execute(sql.SQL("SET LOCAL pg_trgm.similarity_threshold = {}").format(
            sql.Literal(float(threshold))))
        id_ident = sql.Identifier(id_col)
        tbl_ident = sql.Identifier(table)
        if city is not None:
            cur.execute(
                sql.SQL(
                    "select {id}, extensions.similarity(name, %s) as sim from {tbl} "
                    "where name OPERATOR(extensions.%%) %s "
                    "and (city is null or lower(city)=lower(%s)) "
                    "order by sim desc limit 1"
                ).format(id=id_ident, tbl=tbl_ident),
                (name, name, city))
        else:
            cur.execute(
                sql.SQL(
                    "select {id}, extensions.similarity(name, %s) as sim from {tbl} "
                    "where name OPERATOR(extensions.%%) %s order by sim desc limit 1"
                ).format(id=id_ident, tbl=tbl_ident),
                (name, name))
        row = cur.fetchone()
        cur.execute("RELEASE SAVEPOINT fuzzy_match")
        if row:
            return str(row[0]), float(row[1])
        return None
    except psycopg2.Error as exc:
        # Roll back the failed statement first so the caller's transaction stays
        # usable whether we re-raise or fall back.
        cur.execute("ROLLBACK TO SAVEPOINT fuzzy_match")
        # SQLSTATE 42883 (undefined_function) covers both "operator does not
        # exist" and "function does not exist" — i.e. the extensions-qualified
        # pg_trgm objects could not be resolved. Fail loudly: silently falling
        # back here is exactly the bug the second review round caught.
        if getattr(exc, "pgcode", None) == "42883":
            logger.error(
                "fuzzy match failed to resolve pg_trgm in the `extensions` schema "
                "(SQLSTATE 42883) for %s.%s <- %r; refusing to silently degrade to "
                "placeholder-only matching. Check that migration 0006 applied and "
                "that the operator/similarity() are schema-qualified.",
                table, id_col, name)
            raise
        # Any other error is a genuine soft miss — skip the fuzzy step.
        logger.warning("fuzzy match skipped for %s.%s <- %r due to %s; "
                       "falling back to placeholder", table, id_col, name, exc)
        return None


def _log_fuzzy_merge(cur, entity_type: str, entity_id: str, input_name: str, sim: float) -> None:
    """Record a fuzzy-match merge so low-confidence merges stay traceable."""
    logger.info("fuzzy-match merge: %s %s <- %r (similarity=%.3f)",
                entity_type, entity_id, input_name, sim)
    cur.execute(
        """
          insert into audit_log(actor_type, action, entity_type, entity_id, payload)
          values ('system','fuzzy_match_merge',%s,%s,%s::jsonb)
        """,
        (entity_type, entity_id,
         json.dumps({"input_name": input_name, "similarity": round(sim, 3)})))


def resolve_venue_id(cur, venue_name: str, city: str = "Austin") -> str:
    """Resolve (or create) a venue id using the caller's cursor/transaction."""
    venue_name = (venue_name or "").strip()
    city = (city or "").strip()
    # 1. exact match (city-scoped)
    cur.execute(
        "select venue_id from venue where lower(name)=lower(%s) and (city is null or lower(city)=lower(%s)) limit 1",
        (venue_name, city))
    row = cur.fetchone()
    if row:
        return str(row[0])
    # 2. trigram fuzzy match (only for real names, not the placeholder), scoped
    #    to the same city as the exact step so we never merge across cities.
    if venue_name:
        match = _fuzzy_match(cur, "venue", "venue_id", venue_name, FUZZY_THRESHOLD, city=city)
        if match:
            vid, sim = match
            _log_fuzzy_merge(cur, "venue", vid, venue_name, sim)
            return vid
    # 3. placeholder fallback
    cur.execute("insert into venue(name, city) values (%s,%s) returning venue_id",
                (venue_name or "Unknown Venue", city or None))
    return str(cur.fetchone()[0])


def resolve_artist_ids(cur, artist_names: List[str]) -> List[str]:
    """Resolve (or create) artist ids using the caller's cursor/transaction."""
    out = []
    for name in (artist_names or []):
        n = (name or "").strip()
        if not n:
            continue
        # 1. exact match
        cur.execute("select artist_id from artist where lower(name)=lower(%s) limit 1", (n,))
        row = cur.fetchone()
        if row:
            out.append(str(row[0]))
            continue
        # 2. trigram fuzzy match (artist has no city dimension)
        match = _fuzzy_match(cur, "artist", "artist_id", n, FUZZY_THRESHOLD)
        if match:
            aid, sim = match
            _log_fuzzy_merge(cur, "artist", aid, n, sim)
            out.append(aid)
            continue
        # 3. placeholder fallback (get-or-create)
        cur.execute("insert into artist(name) values (%s) returning artist_id", (n,))
        out.append(str(cur.fetchone()[0]))
    return out
