"""Tests for supabase/migrations/0007_narrow_event_public_read.sql.

Two kinds of coverage (same split as tests/test_migration_0006_rls.py):

  * Pure-logic / structural (no DB): parse the migration SQL and assert the
    `event` public_read policy's USING clause now references BOTH privacy
    columns (`is_private_rsvp` and `private_access`) instead of `using (true)`,
    and that it is still a SELECT-only policy granted to anon + authenticated.
    Also asserts (against 0006, which is authoritative for venue/artist) that
    the venue/artist policies remain `using (true)` — they have no privacy
    columns so they are intentionally left unchanged.

  * Backend guarantee (no DB): the FastAPI /tonight and /events endpoints read
    events via the service-role psycopg2 connection, which BYPASSES RLS. This
    migration therefore cannot change what the backend returns — in particular
    it does not filter on confidence, so the "disputed always renders / no
    confidence filter" guarantee is unaffected by the RLS narrowing.

  * DB integration (@dbintegration, skips without ONELIVE_TEST_DB_DSN): with
    the migration applied, an anon/authenticated-role connection sees only the
    public event, not the private one, while a service-role connection sees
    both.
"""
import os
import re

import pytest

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "supabase", "migrations",
)
MIGRATION_0007 = os.path.join(MIGRATIONS_DIR, "0007_narrow_event_public_read.sql")
MIGRATION_0006 = os.path.join(MIGRATIONS_DIR, "0006_rls_policies.sql")


def _statements(path):
    """Lowercased, whitespace-normalized statements split on ';', comments stripped."""
    with open(path) as f:
        raw = f.read()
    no_comments = "\n".join(
        line for line in raw.splitlines() if not line.strip().startswith("--")
    )
    for stmt in no_comments.split(";"):
        s = " ".join(stmt.lower().split())
        if s:
            yield s


def _event_policy_stmt():
    """The single `create policy public_read on event ...` statement in 0007."""
    for s in _statements(MIGRATION_0007):
        if re.match(r"create policy \S+ on event", s):
            return s
    return None


# --------------------------------------------------------------------------
# Structural: the event policy is narrowed (no longer `using (true)`)
# --------------------------------------------------------------------------

def test_event_policy_drops_and_recreates_public_read():
    stmts = list(_statements(MIGRATION_0007))
    assert any(
        re.match(r"drop policy if exists public_read on event$", s) for s in stmts
    ), "0007 must drop the existing public_read policy on event first"
    assert _event_policy_stmt() is not None, "0007 must recreate public_read on event"


def test_event_policy_is_select_only_for_anon_and_authenticated():
    s = _event_policy_stmt()
    assert s is not None
    assert re.search(
        r"create policy \S+ on event for select to anon, authenticated", s
    ), "event policy must stay SELECT-only, granted to anon + authenticated"


def test_event_policy_using_references_both_privacy_columns():
    """The narrowed USING clause must gate on BOTH privacy columns and must NOT
    be the old blanket `using (true)`."""
    s = _event_policy_stmt()
    assert s is not None
    m = re.search(r"using \((.*)\)\s*$", s)
    assert m, f"could not find a USING clause in event policy: {s!r}"
    using = m.group(1)
    assert "is_private_rsvp" in using, "USING clause must reference is_private_rsvp"
    assert "private_access" in using, "USING clause must reference private_access"
    assert using.strip() != "true", "USING clause must not be the old blanket `using (true)`"


def test_event_policy_matches_expected_narrowing():
    """Exact-intent guard: is_private_rsvp = false AND private_access = '{}'."""
    s = _event_policy_stmt()
    assert s is not None
    assert re.search(
        r"using \(\s*is_private_rsvp\s*=\s*false\s+and\s+private_access\s*=\s*'\{\}'::jsonb\s*\)",
        s,
    ), f"event USING clause does not match the expected narrowing: {s!r}"


def test_no_write_policy_introduced_on_event():
    """0007 must not sneak in any write-capable policy (a `for`-less CREATE
    POLICY defaults to FOR ALL = read + write)."""
    for s in _statements(MIGRATION_0007):
        m = re.match(r"create policy \S+ on (\w+)", s)
        if not m:
            continue
        fm = re.search(r"\bfor (select|insert|update|delete|all)\b", s)
        cmd = fm.group(1) if fm else "all"
        assert cmd == "select", f"0007 introduced a non-select policy on {m.group(1)}: {cmd}"


def test_venue_and_artist_policies_remain_using_true():
    """venue/artist have no privacy columns, so their public_read policies stay
    `using (true)`. 0007 must not touch them; 0006 remains authoritative and
    still grants them the blanket read."""
    # 0007 must not redefine venue/artist policies at all.
    for s in _statements(MIGRATION_0007):
        m = re.match(r"create policy \S+ on (\w+)", s)
        if m:
            assert m.group(1) == "event", (
                f"0007 should only touch the event policy, found one on {m.group(1)}"
            )
    # 0006 still has venue/artist as `using (true)`.
    joined_0006 = " ".join(_statements(MIGRATION_0006))
    for t in ("venue", "artist"):
        assert re.search(
            rf"create policy \S+ on {t} for select to anon, authenticated using \(true\)",
            joined_0006,
        ), f"{t} public_read policy should remain `using (true)` in 0006"


# --------------------------------------------------------------------------
# Backend guarantee: RLS narrowing cannot change service-role API reads
# --------------------------------------------------------------------------

API_PUBLIC = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api", "public.py",
)


def test_backend_reads_via_service_role_psycopg2_not_supabase_client():
    """The /tonight + /events endpoints use a direct psycopg2 connection
    (service role, bypasses RLS), NOT the Supabase anon-key client SDK. This is
    why narrowing the RLS policy has zero effect on the backend. Guard it so a
    future refactor to the anon-key client SDK (which WOULD be filtered by this
    policy) is caught here."""
    with open(API_PUBLIC) as f:
        src = f.read()
    assert "psycopg2.connect" in src, "public.py must connect via psycopg2 (service role)"
    assert "create_client" not in src and "from supabase" not in src, (
        "public.py must NOT use the Supabase client SDK (anon key) — that path "
        "would be constrained by the narrowed RLS policy"
    )


def test_public_endpoints_do_not_filter_on_confidence():
    """Confidence-never-filters guarantee is independent of RLS. /tonight orders
    by confidence but never filters it out; /events applies no confidence
    predicate. The 0007 RLS change (which only affects anon/authenticated
    Supabase-client reads, not the service-role backend) must not regress this."""
    with open(API_PUBLIC) as f:
        src = f.read().lower()
    # No `where ... confidence ...` predicate in either endpoint.
    assert not re.search(r"where[^;]*confidence\s*(=|in|!=|<>)", src), (
        "an endpoint appears to FILTER on confidence in a WHERE clause"
    )
    # disputed must remain a rank, never an exclusion.
    assert "when 'disputed' then" in src, "disputed must still be ranked (never dropped)"


# --------------------------------------------------------------------------
# DB integration (needs a live Postgres with migrations 0006 + 0007 applied)
# --------------------------------------------------------------------------

@pytest.mark.dbintegration
def test_db_anon_sees_only_public_events(db_conn):
    """As the `anon` (and `authenticated`) role the narrowed policy must hide a
    private event while still showing a public one; the service-role connection
    (default in this fixture) must still see BOTH."""
    cur = db_conn.cursor()
    cur.execute("SAVEPOINT narrow_event_test")
    try:
        # Two events: one public, one private (via is_private_rsvp).
        cur.execute(
            "insert into event(status, confidence, is_private_rsvp, private_access) "
            "values ('scheduled','confirmed', false, '{}'::jsonb) returning event_id"
        )
        public_id = str(cur.fetchone()[0])
        cur.execute(
            "insert into event(status, confidence, is_private_rsvp, private_access) "
            "values ('scheduled','confirmed', true, '{}'::jsonb) returning event_id"
        )
        private_rsvp_id = str(cur.fetchone()[0])
        # A third event private via a non-empty private_access blob.
        cur.execute(
            "insert into event(status, confidence, is_private_rsvp, private_access) "
            "values ('scheduled','confirmed', false, '{\"ticket_holders\":true}'::jsonb) "
            "returning event_id"
        )
        private_access_id = str(cur.fetchone()[0])

        # Service role (superuser / bypass RLS) sees all three.
        cur.execute(
            "select event_id from event where event_id = any(%s)",
            ([public_id, private_rsvp_id, private_access_id],),
        )
        seen_service = {str(r[0]) for r in cur.fetchall()}
        assert {public_id, private_rsvp_id, private_access_id} <= seen_service, (
            "service-role connection must still see every event (bypasses RLS)"
        )

        # Now become anon (RLS enforced). The narrowed policy hides both private
        # events and shows only the public one.
        for role in ("anon", "authenticated"):
            cur.execute("SAVEPOINT role_test")
            try:
                cur.execute(f"SET LOCAL ROLE {role}")
                cur.execute(
                    "select event_id from event where event_id = any(%s)",
                    ([public_id, private_rsvp_id, private_access_id],),
                )
                seen = {str(r[0]) for r in cur.fetchall()}
                assert public_id in seen, f"{role} must see the public event"
                assert private_rsvp_id not in seen, (
                    f"{role} must NOT see the is_private_rsvp event"
                )
                assert private_access_id not in seen, (
                    f"{role} must NOT see the non-empty private_access event"
                )
            finally:
                cur.execute("RESET ROLE")
                cur.execute("ROLLBACK TO SAVEPOINT role_test")
    finally:
        cur.execute("ROLLBACK TO SAVEPOINT narrow_event_test")
