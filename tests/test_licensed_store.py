"""Network/DB-free unit tests for worker/importers/licensed_store.py — the
deterministic upsert. A fake connection records the SQL + bound params.
"""
import json
import pathlib

import worker.importers.licensed_store as ls
from worker.importers.normalize import normalize_ticketmaster

FIX = pathlib.Path(__file__).parent / "fixtures" / "licensed"


class _FakeCursor:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params):
        self.calls.append((sql, params))


class _FakeConn:
    def __init__(self):
        self.cur = _FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1


def test_upsert_sql_is_static_and_parametrized():
    assert ls.UPSERT_SQL.count("%s") == len(ls._COLS)
    assert "on conflict (source_provider, external_id) do update" in ls.UPSERT_SQL
    assert "updated_at = now()" in ls.UPSERT_SQL
    # the conflict key columns are NOT in the update set
    assert "source_provider = excluded.source_provider" not in ls.UPSERT_SQL


def test_upsert_binds_all_columns_in_order_and_commits():
    conn = _FakeConn()
    ev = {"source_provider": "ticketmaster", "external_id": "x1", "title": "T", "raw": {"a": 1}}
    n = ls.upsert_events(conn, [ev])
    assert n == 1 and conn.commits == 1
    sql, params = conn.cur.calls[0]
    assert sql is ls.UPSERT_SQL
    assert len(params) == len(ls._COLS)
    assert params[0] == "ticketmaster" and params[1] == "x1" and params[2] == "T"
    assert params[ls._COLS.index("confidence")] == "confirmed"  # default
    assert params[ls._COLS.index("status")] == "scheduled"      # default


def test_upsert_real_normalized_fixture():
    ev = normalize_ticketmaster(json.loads((FIX / "ticketmaster_event.json").read_text()))
    conn = _FakeConn()
    ls.upsert_events(conn, [ev])
    _, params = conn.cur.calls[0]
    assert params[ls._COLS.index("category")] == "performing-arts"
    assert params[ls._COLS.index("venue_name")] == "Bass Concert Hall"
    assert params[ls._COLS.index("confidence")] == "confirmed"


def test_raw_is_adapted_via_psycopg2_json():
    # The raw payload must go through psycopg2's Json adapter (jsonb), never a
    # plain string — guards against the removed fallback silently returning.
    from psycopg2.extras import Json
    conn = _FakeConn()
    ls.upsert_events(conn, [{"source_provider": "ticketmaster", "external_id": "j1",
                             "title": "T", "raw": {"k": "v"}}])
    _, params = conn.cur.calls[0]
    assert isinstance(params[ls._COLS.index("raw")], Json)


def test_upsert_multiple_events():
    conn = _FakeConn()
    evs = [{"source_provider": "ticketmaster", "external_id": str(i), "title": f"e{i}"}
           for i in range(5)]
    assert ls.upsert_events(conn, evs) == 5
    assert len(conn.cur.calls) == 5
    assert conn.commits == 1
