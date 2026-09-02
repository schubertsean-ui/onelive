"""Real-Postgres leg for the crawl scheduler's four queries.

WHY THIS EXISTS: the same reason tests/integration/test_promote_pg.py does.
`worker/crawl_state.py` is entirely new SQL — correlated subqueries, a jsonb
path into `_usage`, a `::bigint` cast, `'-infinity'::timestamptz`, a join
through `promoted_event_id` — and every unit test for it drives a FAKE cursor.
A fake cursor cannot see a syntax error, a wrong column name, a bad cast, or a
`%` psycopg2 would try to interpolate. That is the red class
db-type-mismatch-invisible-to-hermetic-tests, and it has shipped through 2,000+
green tests here before. The scheduler decides what the armed cron fetches, so
a query that raises here would take the whole tick down.

These run the REAL statements against a real PostgreSQL with the repo's own
committed migrations applied. They assert the SQL EXECUTES and returns the
right shape on real rows — the half hermetic tests structurally cannot cover.

ENV-GATED, loud: only when ONELIVE_TEST_PG_DSN is set (CI's db-integration
workflow). Without it they SKIP with a visible reason, never silently pass.
"""
from __future__ import annotations

import datetime as _dt
import os
import pathlib
import uuid

import pytest

DSN = os.environ.get("ONELIVE_TEST_PG_DSN")

pytestmark = pytest.mark.skipif(
    not DSN,
    reason="ONELIVE_TEST_PG_DSN not set — the real-Postgres crawl-state leg "
    "runs in CI (db-integration.yml); this skip is loud by design, not a pass.",
)

MIGRATIONS = pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations"
_TZ = _dt.timezone.utc


@pytest.fixture(scope="module")
def pg():
    import psycopg2

    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        # FRESH schema, same policy and same reason as the promote leg: some
        # historical migrations are one-shot, and a half-used database is not
        # the schema under test. The DSN must NEVER point at real data.
        cur.execute("drop schema if exists public cascade")
        cur.execute("drop schema if exists extensions cascade")
        cur.execute("create schema public")
        cur.execute("grant all on schema public to public")
        for role in ("anon", "authenticated"):
            cur.execute(
                "do $$ begin if not exists (select 1 from pg_roles where "
                f"rolname = '{role}') then create role {role} nologin; end if; "
                "end $$;")
        cur.execute("create schema if not exists extensions")
        cur.execute("select current_database()")
        dbname = cur.fetchone()[0]
        cur.execute(
            f'alter database "{dbname}" set search_path = public, extensions')
        cur.execute("set search_path = public, extensions")
        for path in sorted(MIGRATIONS.glob("*.sql")):
            cur.execute(path.read_text())
    os.environ["ONELIVE_DB_DSN"] = DSN
    yield conn
    conn.close()


def _source(cur, name=None, url="https://venue.example/"):
    name = name or f"IT Crawl {uuid.uuid4().hex[:8]}"
    cur.execute(
        "insert into source(name, source_type, base_url, enabled) "
        "values (%s,'venue_calendar',%s,true) returning source_id",
        (name, url))
    return cur.fetchone()[0]


def _fetch(cur, source_id, url, content_hash, when, headers="{}"):
    cur.execute(
        "insert into raw_fetch(source_id, fetch_url, content_hash, headers, "
        "fetched_at) values (%s,%s,%s,%s::jsonb,%s)",
        (source_id, url, content_hash, headers, when))


def _candidate(cur, source_id, url, when, extracted="{}"):
    cur.execute(
        "insert into event_candidate(source_id, source_url, extracted, created_at) "
        "values (%s,%s,%s::jsonb,%s) returning candidate_id",
        (source_id, url, extracted, when))
    return cur.fetchone()[0]


def test_state_query_runs_and_derives_every_fact(pg):
    """The scheduler's main read: last attempt, last VERIFIED, last success,
    fail streak and best_url, all derived from rows the pipeline already
    writes. If any correlated subquery is malformed the tick dies here."""
    from worker.crawl_state import load_crawl_states

    now = _dt.datetime.now(_TZ)
    with pg.cursor() as cur:
        sid = _source(cur, url="https://venue.example/")
        # Two successes on the calendar page, one on the homepage: best_url is
        # the door that produced the MOST candidates, not the newest one.
        _fetch(cur, sid, "https://venue.example/", "aaa", now - _dt.timedelta(hours=9))
        _fetch(cur, sid, "https://venue.example/events", "bbb",
               now - _dt.timedelta(hours=8))
        # Two failures SINCE the last non-failed row -> streak of 2.
        _fetch(cur, sid, "https://venue.example/events", "attempt:failed",
               now - _dt.timedelta(hours=2))
        _fetch(cur, sid, "https://venue.example/events", "attempt:failed",
               now - _dt.timedelta(hours=1))
        _candidate(cur, sid, "https://venue.example/events", now - _dt.timedelta(hours=8))
        _candidate(cur, sid, "https://venue.example/events", now - _dt.timedelta(hours=8))
        _candidate(cur, sid, "https://venue.example/", now - _dt.timedelta(hours=9))

        states = load_crawl_states(cur=cur)

    state = states[str(sid)]
    assert state.best_url == "https://venue.example/events"
    assert state.fail_streak == 2
    assert state.last_attempt_at is not None
    assert state.last_verified_at is not None
    assert state.last_success_at is not None
    # The distinction the founder asked for, on real rows: we ATTEMPTED an hour
    # ago and VERIFIED eight hours ago. A schema that collapsed them would let
    # a run of failures read as confirmations.
    assert state.last_attempt_at > state.last_verified_at


def test_a_never_fetched_source_survives_the_infinity_coalesce(pg):
    """`'-infinity'::timestamptz` in the fail-streak subquery is exactly the
    kind of literal a fake cursor never evaluates."""
    from worker.crawl_state import load_crawl_states

    with pg.cursor() as cur:
        sid = _source(cur, url="https://brandnew.example/")
        states = load_crawl_states(cur=cur)
    state = states[str(sid)]
    assert state.fail_streak == 0
    assert state.last_attempt_at is None
    assert state.is_due()


def test_fingerprint_query_returns_the_last_success_for_that_url(pg):
    """Per-URL, and it must skip attempt rows — the `not like 'attempt:%'`
    pattern is a psycopg2 interpolation hazard if the SQL is written wrong."""
    from worker.crawl_state import load_door_fingerprint

    now = _dt.datetime.now(_TZ)
    with pg.cursor() as cur:
        sid = _source(cur, url="https://fp.example/")
        _fetch(cur, sid, "https://fp.example/events", "older-hash",
               now - _dt.timedelta(hours=5),
               headers='{"etag": "W/\\"v1\\"", "last_modified": "Mon, 01 Sep 2026"}')
        _fetch(cur, sid, "https://fp.example/events", "newest-hash",
               now - _dt.timedelta(hours=1),
               headers='{"etag": "W/\\"v2\\"", "last_modified": "Tue, 02 Sep 2026"}')
        _fetch(cur, sid, "https://fp.example/events", "attempt:failed", now)
        _fetch(cur, sid, "https://fp.example/other", "other-hash", now)

        fp = load_door_fingerprint(sid, "https://fp.example/events", cur=cur)
        missing = load_door_fingerprint(sid, "https://fp.example/never", cur=cur)

    assert fp is not None
    assert fp.content_hash == "newest-hash", "an attempt row is not a success"
    assert fp.etag == 'W/"v2"'
    assert fp.last_modified == "Tue, 02 Sep 2026"
    assert missing is None


def test_event_refresh_query_joins_through_promoted_event_id(pg):
    """The defining page comes from event_candidate.source_url via
    promoted_event_id — NOT event.source_url, which migration 0020 fills with
    the source's homepage. Only a real join proves that path exists."""
    from worker.crawl_state import load_event_refresh_rows, plan_event_refreshes

    now = _dt.datetime.now(_TZ)
    with pg.cursor() as cur:
        sid = _source(cur, url="https://prox.example/")
        # Two upcoming events on ONE page, plus one already over.
        for start in (now + _dt.timedelta(days=5), now + _dt.timedelta(hours=4)):
            cur.execute("insert into event(start_time) values (%s) returning event_id",
                        (start,))
            eid = cur.fetchone()[0]
            cid = _candidate(cur, sid, "https://prox.example/calendar", now)
            cur.execute("update event_candidate set promoted_event_id = %s "
                        "where candidate_id = %s", (eid, cid))
        cur.execute("insert into event(start_time, end_time) values (%s,%s) "
                    "returning event_id",
                    (now - _dt.timedelta(days=2), now - _dt.timedelta(days=2)))
        past = cur.fetchone()[0]
        cid = _candidate(cur, sid, "https://prox.example/archive", now)
        cur.execute("update event_candidate set promoted_event_id = %s "
                    "where candidate_id = %s", (past, cid))

        rows = load_event_refresh_rows(cur=cur)

    urls = {r[1] for r in rows}
    assert "https://prox.example/calendar" in urls
    assert "https://prox.example/archive" not in urls, (
        "'then stop after end' is in the WHERE clause, not in the caller")

    planned = plan_event_refreshes(rows, now=now)
    ours = [p for p in planned if p.url == "https://prox.example/calendar"]
    assert len(ours) == 1, "one page fetch covers all events on that page"
    assert ours[0].events == 2


def test_a_dateless_published_row_never_enters_the_proximity_query(pg):
    """Founder: "Dateless rows: source-door schedule only." Enforced in SQL."""
    from worker.crawl_state import load_event_refresh_rows

    now = _dt.datetime.now(_TZ)
    with pg.cursor() as cur:
        sid = _source(cur, url="https://dateless.example/")
        cur.execute("insert into event(start_time) values (null) returning event_id")
        eid = cur.fetchone()[0]
        cid = _candidate(cur, sid, "https://dateless.example/list", now)
        cur.execute("update event_candidate set promoted_event_id = %s "
                    "where candidate_id = %s", (eid, cid))
        rows = load_event_refresh_rows(cur=cur)
    assert "https://dateless.example/list" not in {r[1] for r in rows}


def test_usage_query_sums_real_jsonb_and_never_raises_on_a_bad_stamp(pg):
    """The cost report's read. Every hazard here is server-side: the jsonb
    path, the ::bigint cast, the timestamptz cast, and a malformed `_usage`
    that must contribute zero rather than take the telemetry down."""
    from worker.crawl_state import load_extraction_usage

    now = _dt.datetime.now(_TZ)
    since = (now - _dt.timedelta(minutes=5)).isoformat()
    with pg.cursor() as cur:
        sid = _source(cur, url="https://usage.example/")
        _candidate(cur, sid, "https://usage.example/a", now,
                   extracted='{"_usage": {"input_tokens": 1200, "output_tokens": 90}}')
        _candidate(cur, sid, "https://usage.example/b", now,
                   extracted='{"_usage": {"input_tokens": 800, "output_tokens": 10}}')
        # A provider that reported nothing, an importer row with no usage at
        # all, and a malformed stamp: all must contribute 0, none may raise.
        _candidate(cur, sid, "https://usage.example/c", now,
                   extracted='{"_usage": {"input_tokens": null, "output_tokens": null}}')
        _candidate(cur, sid, "https://usage.example/d", now, extracted='{}')
        _candidate(cur, sid, "https://usage.example/e", now,
                   extracted='{"_usage": {"input_tokens": "lots", "output_tokens": []}}')
        # Older than the window: another tick's spend, not this one's.
        _candidate(cur, sid, "https://usage.example/old",
                   now - _dt.timedelta(hours=3),
                   extracted='{"_usage": {"input_tokens": 999999, "output_tokens": 1}}')

        tokens_in, tokens_out = load_extraction_usage(since, cur=cur)

    assert tokens_in == 2000, "only this tick's rows, only real numbers"
    assert tokens_out == 100
