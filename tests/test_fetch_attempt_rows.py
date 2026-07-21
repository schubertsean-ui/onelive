"""raw_fetch ATTEMPT rows (PR #43 r2 — a real rotation-coverage bug).

The capped scheduled loop rotates sources on max(raw_fetch.fetched_at); if
only SUCCESSFUL fetches left rows, a permanently-failing or perpetually-304
source would look never/least-fetched forever, lead every rotation window,
and monopolize the per-run budget. These tests pin the fix at the adapter:
failed and not-modified fetches record best-effort attempt rows
(content_hash "attempt:<outcome>"), and the recorder can NEVER mask the
original error — a broken DB during the attempt write still surfaces the
fetch failure, not the bookkeeping failure.

Hermetic: `requests.get` and the module's `db()` are monkeypatched.
"""
import pytest
import requests

import worker.fetch.http_fetch as http_fetch


class _FakeCursor:
    def __init__(self, sink, fail=False):
        self._sink = sink
        self._fail = fail

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        if self._fail:
            raise RuntimeError("db is down")
        self._sink.append((" ".join(sql.split()), params))


class _FakeConn:
    def __init__(self, sink, fail=False):
        self._sink = sink
        self._fail = fail
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return _FakeCursor(self._sink, self._fail)

    def commit(self):
        self.committed = True


@pytest.fixture()
def db_rows(monkeypatch):
    rows = []
    monkeypatch.setattr(http_fetch, "db", lambda: _FakeConn(rows))
    return rows


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code
        self.headers = {}
        self.content = b""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error")


def _params_of(rows):
    assert len(rows) == 1
    _sql, params = rows[0]
    return params


def test_failed_fetch_records_attempt_and_reraises(monkeypatch, db_rows):
    monkeypatch.setattr(http_fetch.requests, "get", lambda *a, **k: _Resp(500))
    with pytest.raises(requests.HTTPError):
        http_fetch.fetch_url(source_id="sid-1", url="https://x/1",
                             min_interval_s=0.0)
    params = _params_of(db_rows)
    assert params[0] == "sid-1"
    assert params[2] == "attempt:failed"


def test_connection_error_records_attempt_and_reraises(monkeypatch, db_rows):
    def boom(*a, **k):
        raise requests.ConnectionError("dns dead")
    monkeypatch.setattr(http_fetch.requests, "get", boom)
    with pytest.raises(requests.ConnectionError):
        http_fetch.fetch_url(source_id="sid-2", url="https://x/2",
                             min_interval_s=0.0)
    assert _params_of(db_rows)[2] == "attempt:failed"


def test_not_modified_records_attempt_and_returns(monkeypatch, db_rows):
    monkeypatch.setattr(http_fetch.requests, "get", lambda *a, **k: _Resp(304))
    result = http_fetch.fetch_url(source_id="sid-3", url="https://x/3",
                                  min_interval_s=0.0)
    assert result["status"] == "not_modified"
    assert _params_of(db_rows)[2] == "attempt:not_modified"


def test_recorder_never_masks_but_is_loud_and_attached(monkeypatch, caplog):
    """DB down during the attempt write on the FAILED path (r8 contract):
    the caller still sees the FETCH failure, but the bookkeeping failure is
    (a) logged at ERROR level and (b) attached to the original exception as
    a traceback note — loud structured evidence, never a quiet swallow."""
    monkeypatch.setattr(http_fetch, "db", lambda: _FakeConn([], fail=True))
    monkeypatch.setattr(http_fetch.requests, "get", lambda *a, **k: _Resp(503))
    with caplog.at_level("ERROR"):
        with pytest.raises(requests.HTTPError) as excinfo:
            http_fetch.fetch_url(source_id="sid-4", url="https://x/4",
                                 min_interval_s=0.0)
    assert any("attempt-row write FAILED" in r.message for r in caplog.records)
    notes = getattr(excinfo.value, "__notes__", [])
    assert any("attempt-row write failed" in n for n in notes)


def test_304_attempt_write_failure_fails_loud(monkeypatch):
    """r3 finding: on the 304 path there is NO original error, so a
    swallowed attempt-write failure would silently re-introduce the
    capped-window starvation bug. The write failure must propagate as this
    source's loud failure — never a quiet 'not_modified' success."""
    monkeypatch.setattr(http_fetch, "db", lambda: _FakeConn([], fail=True))
    monkeypatch.setattr(http_fetch.requests, "get", lambda *a, **k: _Resp(304))
    with pytest.raises(RuntimeError, match="db is down"):
        http_fetch.fetch_url(source_id="sid-304", url="https://x/304",
                             min_interval_s=0.0)


def test_recorder_is_noop_without_source_id(monkeypatch, db_rows):
    """The smoke stub source has no source_id — nothing to rotate, nothing
    written."""
    monkeypatch.setattr(http_fetch.requests, "get", lambda *a, **k: _Resp(500))
    with pytest.raises(requests.HTTPError):
        http_fetch.fetch_url(source_id=None, url="https://x/5",
                             min_interval_s=0.0)
    assert db_rows == []


def test_attempt_rows_satisfy_the_real_migration_schema():
    """r5 nit: bind the adapter's schema assumptions to the REAL migration
    text, not prose. Attempt rows rely on exactly three properties of
    supabase/migrations/0003_raw_fetch.sql: content_hash is text (accepts
    the 'attempt:<outcome>' token) and not-null (we always provide it),
    storage_ref is NULLABLE (attempt rows pass NULL), headers is jsonb
    (carries the outcome/detail payload). If the migration ever changes any
    of these, this test — not a production insert — is what breaks."""
    import pathlib
    sql = (pathlib.Path(__file__).resolve().parent.parent
           / "supabase" / "migrations" / "0003_raw_fetch.sql").read_text()
    table = sql.split("create table if not exists raw_fetch", 1)[1]
    table = table.split(");", 1)[0]
    cols = {}
    for line in table.splitlines():
        line = line.strip().rstrip(",")
        if line and not line.startswith(("(", "--")):
            name = line.split()[0]
            cols[name] = line
    assert "content_hash" in cols and "text" in cols["content_hash"]
    assert "not null" in cols["content_hash"]
    assert "storage_ref" in cols and "not null" not in cols["storage_ref"]
    assert "headers" in cols and "jsonb" in cols["headers"]
    assert "source_id" in cols and "references source" in cols["source_id"]
    # Repeated attempt rows reuse constant hashes ("attempt:failed"), so
    # raw_fetch must have NO uniqueness over source_id/content_hash — pin
    # that assumption against the whole migration text (r13 nit): the only
    # allowed unique-ish construct is the primary key.
    assert "unique" not in sql.lower().split("raw_fetch", 1)[1].split(");", 1)[0]
    for line in table.splitlines():
        if "content_hash" in line or "source_id" in line:
            assert "unique" not in line.lower()


def test_successful_fetch_row_shape_unchanged(monkeypatch, db_rows, tmp_path):
    """Success still writes the real content row (sha256 hash, storage ref)
    — attempt rows are additive, not a rewrite of the success path."""
    monkeypatch.setattr(http_fetch, "RAW_DIR", str(tmp_path))

    class _OkResp(_Resp):
        def __init__(self):
            super().__init__(200)
            self.content = b"<html>hi</html>"

    class _OkCursor(_FakeCursor):
        def execute(self, sql, params=None):
            super().execute(sql, params)

        def fetchone(self):
            return ("rf-uuid",)

    class _OkConn(_FakeConn):
        def cursor(self):
            return _OkCursor(self._sink)

    monkeypatch.setattr(http_fetch, "db", lambda: _OkConn(db_rows))
    monkeypatch.setattr(http_fetch.requests, "get", lambda *a, **k: _OkResp())
    result = http_fetch.fetch_url(source_id="sid-6", url="https://x/6",
                                  min_interval_s=0.0)
    assert result["status"] == "ok"
    params = _params_of(db_rows)
    assert params[2] == http_fetch.sha256(b"<html>hi</html>")
    assert not params[2].startswith(http_fetch.ATTEMPT_HASH_PREFIX)
