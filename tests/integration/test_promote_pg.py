"""Real-Postgres leg for the publish path (OPERATING_RULES: 'Real-database leg
for publish-path changes', founder-ratified 2026-08-05 — decision record
docs/memory/decisions/2026-08-05_founder-path-preflight-and-real-db-leg.md).

WHY THIS EXISTS: the artist_ids uuid[]/text[] refusal (autopromote run
30994644214: 155 errors; first pass: 64) was invisible to every fake-cursor
test by construction — server-side type/constraint checks have no hermetic
analogue (red class db-type-mismatch-invisible-to-hermetic-tests). This module
runs the ACTUAL promote path against a real PostgreSQL with the repo's own
migrations applied, so that class of defect fails in CI, never live.

ENV-GATED, loud (red class env-dependent-hermetic-test): these tests run only
when ONELIVE_TEST_PG_DSN is set (CI's db-integration workflow sets it against
a service container; locally, point it at any disposable database — the suite
DROPS AND RECREATES public objects via the migrations, so never a real DSN).
Without the env they SKIP with a visible reason — never silently pass.
"""
from __future__ import annotations

import os
import pathlib
import uuid

import pytest

DSN = os.environ.get("ONELIVE_TEST_PG_DSN")

pytestmark = pytest.mark.skipif(
    not DSN,
    reason="ONELIVE_TEST_PG_DSN not set — the real-Postgres publish-path leg "
    "runs in CI (db-integration.yml); this skip is loud by design, not a pass.",
)

MIGRATIONS = pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations"


@pytest.fixture(scope="module")
def pg():
    import psycopg2

    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        # FRESH schema every run: some historical migrations are one-shot
        # (0009's named unique constraint), so re-applying onto a used
        # database fails — and a half-used database is not the schema under
        # test anyway. This is why the DSN must NEVER point at real data.
        cur.execute("drop schema if exists public cascade")
        cur.execute("drop schema if exists extensions cascade")
        cur.execute("create schema public")
        cur.execute("grant all on schema public to public")
        # Supabase provides these roles; plain Postgres does not. The RLS/grant
        # migrations (0006/0007/0012/0016/0017/0020) reference them, so create
        # them idempotently before applying the real migration files verbatim.
        for role in ("anon", "authenticated"):
            cur.execute(
                "do $$ begin if not exists (select 1 from pg_roles where "
                f"rolname = '{role}') then create role {role} nologin; end if; "
                "end $$;")
        # Supabase routes extensions into an `extensions` schema; a plain CI
        # container installs them into public. Make both shapes work by
        # ensuring the schema exists and is on every new connection's path
        # (mirrors Supabase's own search_path).
        cur.execute("create schema if not exists extensions")
        cur.execute("select current_database()")
        dbname = cur.fetchone()[0]
        cur.execute(
            f'alter database "{dbname}" set search_path = public, extensions')
        cur.execute("set search_path = public, extensions")
        # Every migration, in order, exactly as committed — the point is that
        # the schema under test IS the schema the migrations produce.
        for path in sorted(MIGRATIONS.glob("*.sql")):
            cur.execute(path.read_text())
    # promote.py connects via resolve_dsn(); point it at this database for the
    # duration of the module.
    os.environ["ONELIVE_DB_DSN"] = DSN
    yield conn
    conn.close()


def _seed_candidate(cur, *, source_registered: bool, with_artists: bool):
    """One PASS-able candidate: anchor (ticketing) evidence, public, one
    consistent start time — the exact shape assert_promotable PASSes."""
    suffix = uuid.uuid4().hex[:8]
    src_name = f"IT Source {suffix}"
    if source_registered:
        cur.execute(
            "insert into source(name, source_type, base_url) "
            "values (%s,'venue_calendar','https://it-source.example/cal') ",
            (src_name,))
    cur.execute(
        """
        insert into event_candidate(
          source_name, source_class, raw_text, extracted, title, start_time,
          venue_name, city, artist_names, ticket_link, status)
        values (%s,'ticketing','raw', '{}'::jsonb, %s,
                now() + interval '7 day', %s, 'Austin', %s,
                'https://tix.example/it', 'needs_review')
        returning candidate_id
        """,
        # Two structurally DISSIMILAR names on purpose: resolve_artist_ids
        # fuzzy-merges near-identical names by design (trigram threshold),
        # and this test asserts two DISTINCT artists round-trip the uuid[]
        # insert — name similarity would test the matcher, not the cast.
        (src_name, f"IT Show {suffix}", f"IT Venue {suffix}",
         [f"Zq Ensemble {suffix}", f"Marrow Choir {uuid.uuid4().hex[:8]}"] if with_artists else []),
    )
    cid = str(cur.fetchone()[0])
    cur.execute(
        "insert into candidate_evidence(candidate_id, source_class, source_name)"
        " values (%s,'ticketing',%s)", (cid, src_name))
    return cid, src_name


def test_promote_with_artists_writes_uuid_array_and_registry_provenance(pg):
    """The escaped class, replayed for real: a candidate WITH artist names must
    promote (uuid[] insert against the server's type check) and carry the
    registry's canonical provenance onto the public row."""
    from worker.promote import promote_candidate

    with pg.cursor() as cur:
        cid, src_name = _seed_candidate(cur, source_registered=True, with_artists=True)

    event_id = promote_candidate(cid)

    with pg.cursor() as cur:
        cur.execute(
            "select artist_ids, source_name, source_url, title, ticket_url,"
            "       confidence, status from event where event_id=%s",
            (event_id,))
        artist_ids, source_name, source_url, title, ticket_url, confidence, status = cur.fetchone()
    # psycopg2 may hand uuid[] back as a raw array literal depending on
    # registered adapters — normalize before asserting, the column TYPE is
    # what the insert's ::uuid[] cast already proved server-side.
    if isinstance(artist_ids, str):
        artist_ids = [x for x in artist_ids.strip("{}").split(",") if x]
    assert len(artist_ids) == 2
    assert len({str(a) for a in artist_ids}) == 2  # two DISTINCT artists
    assert all(uuid.UUID(str(a)) for a in artist_ids)
    assert source_name == src_name  # registry canonical name
    assert source_url == "https://it-source.example/cal"
    assert title.startswith("IT Show ")
    assert ticket_url == "https://tix.example/it"
    assert confidence == "confirmed"
    assert status == "scheduled"


def test_unregistered_source_publishes_null_provenance(pg):
    """Registry-bound fail-closed (evaluator #188 r1), proven on a real DB: a
    candidate whose source_name matches no registry row publishes NULLs."""
    from worker.promote import promote_candidate

    with pg.cursor() as cur:
        cid, _ = _seed_candidate(cur, source_registered=False, with_artists=False)

    event_id = promote_candidate(cid)

    with pg.cursor() as cur:
        cur.execute(
            "select source_name, source_url from event where event_id=%s",
            (event_id,))
        source_name, source_url = cur.fetchone()
    assert source_name is None
    assert source_url is None


def test_backfill_is_registry_bound(pg):
    """0020's backfill statement, exercised for real: a pre-0020 promoted row
    (simulated: provenance nulled) backfills ONLY when the candidate's source
    matches the registry, taking the registry's canonical values."""
    from worker.promote import promote_candidate

    with pg.cursor() as cur:
        cid, src_name = _seed_candidate(cur, source_registered=True, with_artists=False)
    event_id = promote_candidate(cid)

    with pg.cursor() as cur:
        cur.execute("update event set source_name=null, source_url=null where event_id=%s",
                    (event_id,))
        # Re-run the committed migration file verbatim — idempotence is part of
        # its contract (tools/apply_migration.py).
        cur.execute((MIGRATIONS / "0020_event_provenance.sql").read_text())
        cur.execute("select source_name, source_url from event where event_id=%s",
                    (event_id,))
        source_name, source_url = cur.fetchone()
    assert source_name == src_name
    assert source_url == "https://it-source.example/cal"
