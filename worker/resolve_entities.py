"""Entity resolution for venues and artists.

Resolution priority (in order):
  1. exact match      — case-insensitive exact name match.
  2. trigram fuzzy    — pg_trgm similarity above FUZZY_THRESHOLD (handles minor
                        spelling/spacing variants without creating a duplicate).
  3. placeholder      — get-or-create: insert a new row as a fallback.

pg_trgm + the trigram GIN indexes are provided by supabase/migrations/0005_pg_trgm.sql.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/resolve_entities.py)
"""
import os
import psycopg2
from typing import List, Optional

DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")

# Similarity in [0,1]; 0.45 tolerates minor variants ("Mohawk" vs "The Mohawk")
# while staying strict enough not to collapse genuinely different names.
FUZZY_THRESHOLD = 0.45


def db():
    return psycopg2.connect(DB_DSN)


def _fuzzy_match_id(cur, table: str, id_col: str, name: str, threshold: float) -> Optional[str]:
    """Return the best trigram match id for `name` in `table`, or None.

    Uses pg_trgm similarity(). Falls back to None (not an error) if pg_trgm is
    unavailable, so resolution degrades to exact-match + placeholder rather than
    crashing the pipeline.
    """
    try:
        cur.execute(
            f"select {id_col}, similarity(name, %s) as sim from {table} "
            f"where similarity(name, %s) >= %s order by sim desc limit 1",
            (name, name, threshold))
        row = cur.fetchone()
        return str(row[0]) if row else None
    except psycopg2.Error:
        # pg_trgm not enabled yet — skip fuzzy step gracefully.
        cur.connection.rollback()
        return None


def resolve_venue_id(venue_name: str, city: str = "Austin") -> str:
    venue_name = (venue_name or "").strip()
    city = (city or "").strip()
    with db() as conn:
        with conn.cursor() as cur:
            # 1. exact match
            cur.execute(
                "select venue_id from venue where lower(name)=lower(%s) and (city is null or lower(city)=lower(%s)) limit 1",
                (venue_name, city))
            row = cur.fetchone()
            if row:
                return str(row[0])
            # 2. trigram fuzzy match (only for real names, not the placeholder)
            if venue_name:
                fuzzy = _fuzzy_match_id(cur, "venue", "venue_id", venue_name, FUZZY_THRESHOLD)
                if fuzzy:
                    return fuzzy
            # 3. placeholder fallback
            cur.execute("insert into venue(name, city) values (%s,%s) returning venue_id",
                        (venue_name or "Unknown Venue", city or None))
            vid = cur.fetchone()[0]
        conn.commit()
    return str(vid)


def resolve_artist_ids(artist_names: List[str]) -> List[str]:
    out = []
    with db() as conn:
        with conn.cursor() as cur:
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
                # 2. trigram fuzzy match
                fuzzy = _fuzzy_match_id(cur, "artist", "artist_id", n, FUZZY_THRESHOLD)
                if fuzzy:
                    out.append(fuzzy)
                    continue
                # 3. placeholder fallback (get-or-create)
                cur.execute("insert into artist(name) values (%s) returning artist_id", (n,))
                out.append(str(cur.fetchone()[0]))
        conn.commit()
    return out
