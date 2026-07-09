"""Tests for supabase/migrations/0006_rls_policies.sql.

Two kinds of coverage:

  * Pure-logic / structural (no DB): parse the migration SQL and assert it
    enables RLS on all 14 public tables, grants ONLY read (SELECT) to
    anon/authenticated on the 4 public-read tables, adds NO policy at all to
    the 10 service-role-only tables, and moves pg_trgm into the `extensions`
    schema while recreating both trigram GIN indexes. These guard the exact
    policy model the founder approved from silently drifting.

  * DB integration (@dbintegration, skips without ONELIVE_TEST_DB_DSN): after
    the migration has moved pg_trgm to `extensions`, fuzzy entity resolution
    still works — the `%` operator and similarity() still resolve and the
    trigram index still backs the lookup.
"""
import os
import re

import pytest

MIGRATION = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "supabase", "migrations", "0006_rls_policies.sql",
)

ALL_TABLES = [
    "source", "venue", "artist", "event", "event_candidate",
    "candidate_evidence", "source_reliability", "audit_log", "raw_fetch",
    "raw_event", "advertiser", "ad_campaign", "ad_creative", "ad_placement_rule",
]
# source_reliability is INTERNAL trust-scoring data accessed only via the backend
# service-role connection (worker/source_reliability.py) — the second review round
# moved it out of public-read into the service-role-only (no-policy) bucket so the
# anon key can never read internal scoring. See migration 0006 comments + STATE.md.
PUBLIC_READ = {"event", "venue", "artist"}
SERVICE_ONLY = set(ALL_TABLES) - PUBLIC_READ

assert len(ALL_TABLES) == 14
assert len(SERVICE_ONLY) == 11


def _sql():
    with open(MIGRATION) as f:
        return f.read()


def _statements():
    """Lowercased, whitespace-normalized statements split on ';'."""
    raw = _sql()
    # strip line comments so `-- ... enable row level security` prose in the
    # header can't produce false matches.
    no_comments = "\n".join(
        line for line in raw.splitlines() if not line.strip().startswith("--")
    )
    for stmt in no_comments.split(";"):
        s = " ".join(stmt.lower().split())
        if s:
            yield s


def _policies():
    """Map table -> set of policy commands (select/insert/update/delete/all).

    A CREATE POLICY with no `for` clause defaults to FOR ALL in Postgres (read
    AND write). The previous parser only matched policies with an explicit `for`,
    so a `for`-less (therefore write-capable) policy slipped past the negative
    tests undetected. We now match every CREATE POLICY and attribute a missing
    `for` clause as `all`, so it is correctly flagged as write-capable.
    """
    out = {}
    for s in _statements():
        m = re.match(r"create policy \S+ on (\w+)", s)
        if not m:
            continue
        fm = re.search(r"\bfor (select|insert|update|delete|all)\b", s)
        cmd = fm.group(1) if fm else "all"
        out.setdefault(m.group(1), set()).add(cmd)
    return out


def test_rls_enabled_on_all_14_tables():
    stmts = list(_statements())
    for t in ALL_TABLES:
        assert any(
            re.match(rf"alter table {t} enable row level security$", s) for s in stmts
        ), f"RLS not enabled on {t}"


def test_public_read_tables_have_only_select_policy():
    policies = _policies()
    for t in PUBLIC_READ:
        assert t in policies, f"{t} is missing its public read policy"
        assert policies[t] == {"select"}, (
            f"{t} must have ONLY a select policy, got {policies[t]}"
        )


def test_public_read_policy_grants_anon_and_authenticated():
    for t in PUBLIC_READ:
        assert any(
            re.search(rf"create policy \S+ on {t} for select to anon, authenticated", s)
            for s in _statements()
        ), f"{t} select policy must grant anon + authenticated"


def test_service_role_tables_have_no_policies():
    policies = _policies()
    for t in SERVICE_ONLY:
        assert t not in policies, (
            f"{t} is service-role-only and must have NO policy (default-deny)"
        )


def test_no_write_policies_anywhere():
    policies = _policies()
    for t, cmds in policies.items():
        assert cmds <= {"select"}, f"unexpected write policy on {t}: {cmds}"


def test_pg_trgm_moved_to_extensions_schema():
    joined = " ".join(_statements())
    assert "create schema if not exists extensions" in joined
    assert "drop extension if exists pg_trgm" in joined
    assert "create extension if not exists pg_trgm schema extensions" in joined


def test_trigram_indexes_recreated():
    joined = " ".join(_statements())
    for idx, table in (("idx_venue_name_trgm", "venue"), ("idx_artist_name_trgm", "artist")):
        assert re.search(
            rf"create index if not exists {idx} on {table} using gin",
            joined,
        ), f"{idx} not recreated after moving pg_trgm"


def test_trigram_indexes_are_schema_qualified():
    """After pg_trgm moves to `extensions`, the recreated GIN indexes MUST use the
    schema-qualified `extensions.gin_trgm_ops` opclass — an unqualified
    `gin_trgm_ops` would fail (or silently resolve to a stale public opclass)
    depending on search_path. Guards the fix from regressing to a bare opclass."""
    joined = " ".join(_statements())
    for idx, table in (("idx_venue_name_trgm", "venue"), ("idx_artist_name_trgm", "artist")):
        assert re.search(
            rf"create index if not exists {idx} on {table} using gin "
            rf"\(name extensions\.gin_trgm_ops\)",
            joined,
        ), f"{idx} must use the schema-qualified extensions.gin_trgm_ops opclass"


# --------------------------------------------------------------------------
# DB integration (needs a live Postgres with migration 0006 applied)
# --------------------------------------------------------------------------

@pytest.mark.dbintegration
def test_db_pg_trgm_in_extensions_schema(db_conn):
    """pg_trgm lives in the `extensions` schema, not `public`, after migration."""
    cur = db_conn.cursor()
    cur.execute(
        "select n.nspname from pg_extension e "
        "join pg_namespace n on n.oid = e.extnamespace where e.extname = 'pg_trgm'"
    )
    row = cur.fetchone()
    assert row is not None, "pg_trgm not installed"
    assert row[0] == "extensions", f"pg_trgm should be in 'extensions', found {row[0]!r}"


@pytest.mark.dbintegration
def test_db_fuzzy_resolution_works_after_move(db_conn):
    """Fuzzy entity resolution (the `%` operator + similarity()) still resolves
    with pg_trgm relocated to `extensions` — proves the search_path/qualification
    fix works end to end."""
    from worker.resolve_entities import resolve_venue_id

    cur = db_conn.cursor()
    cur.execute("SAVEPOINT trgm_move_test")
    try:
        cur.execute(
            "insert into venue(name, city) values ('The Mohawk','Austin') returning venue_id"
        )
        vid = str(cur.fetchone()[0])
        # "Mohawk" only matches "The Mohawk" via trigram fuzzy — which requires
        # pg_trgm's % operator to be resolvable on the search_path.
        assert resolve_venue_id(cur, "Mohawk", "Austin") == vid
    finally:
        cur.execute("ROLLBACK TO SAVEPOINT trgm_move_test")


@pytest.mark.dbintegration
def test_db_fuzzy_resolution_works_without_extensions_on_search_path(db_conn):
    """Regression test for the second-review-round finding: fuzzy matching must
    work even when the connection's search_path does NOT include `extensions`.

    This proves the CODE-LEVEL fix (schema-qualifying the `%` operator and
    similarity() to `extensions` in worker/resolve_entities.py) is what makes
    resolution work — not the migration's `ALTER DATABASE ... SET search_path`,
    which on Supabase can be overridden by role-level settings. We force a
    search_path of just `public` (no extensions); if the code still relied on an
    unqualified operator this would raise SQLSTATE 42883 and fall through to a
    placeholder (vid != new id), failing the assert.
    """
    from worker.resolve_entities import resolve_venue_id

    cur = db_conn.cursor()
    cur.execute("SAVEPOINT no_ext_path_test")
    try:
        # Deliberately exclude `extensions` from the search_path for this session.
        cur.execute("SET LOCAL search_path TO public")
        cur.execute(
            "insert into venue(name, city) values ('The Mohawk','Austin') returning venue_id"
        )
        vid = str(cur.fetchone()[0])
        # Must resolve via schema-qualified trigram fuzzy despite extensions not
        # being on the search_path.
        assert resolve_venue_id(cur, "Mohawk", "Austin") == vid
    finally:
        cur.execute("ROLLBACK TO SAVEPOINT no_ext_path_test")
