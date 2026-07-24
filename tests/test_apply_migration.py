"""Tests for tools/apply_migration.py — the idempotent single-file migration
applier. DB-free: a fake connection records the executed SQL.
"""
import importlib.util
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "apply_migration", _ROOT / "tools" / "apply_migration.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql):
        self.executed.append(sql)


class _FakeConn:
    def __init__(self):
        self.cur = _FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1


def test_apply_sql_executes_and_commits():
    m = _mod()
    conn = _FakeConn()
    m.apply_sql(conn, "create table if not exists x (id int);")
    assert conn.cur.executed == ["create table if not exists x (id int);"]
    assert conn.commits == 1


def test_main_missing_file_exits_2():
    m = _mod()
    assert m.main(["/no/such/migration.sql"]) == 2


def test_real_migration_0010_is_readable():
    p = _ROOT / "supabase" / "migrations" / "0010_licensed_feed_and_domains.sql"
    assert p.is_file()
    assert "licensed_event" in p.read_text()
