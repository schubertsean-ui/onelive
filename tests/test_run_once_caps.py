"""Tests for worker/run_once.py budget ceilings (§14.3 — caps before the loop).

Pure logic, no DB/network: proves the per-run source ceiling truncates
deterministically and loudly, FAILS CLOSED on 0/negative/garbage values from
every input channel (CLI flag, argparse type, env var — a budget guard must
never fail open; evaluator finding PR #12 round 1), and that CLI beats env
beats uncapped-with-loud-warning in _resolve_source_cap. Also pins the
Step-5 arming rotation contract (FRICTION_LOG entry #3): under a recurring
capped run, source order IS coverage, so ordering must be
least-recently-fetched-first with never-fetched ahead of everything.
"""
import argparse
import datetime as _dt

import pytest

from worker.run_once import (
    _positive_int,
    _resolve_source_cap,
    apply_source_ceiling,
    order_for_rotation,
)

_SOURCES = [{"name": f"s{i}"} for i in range(5)]


def test_ceiling_truncates_in_order_and_warns(caplog):
    with caplog.at_level("WARNING"):
        capped = apply_source_ceiling(_SOURCES, 2)
    assert capped == _SOURCES[:2]
    assert any("budget ceiling" in r.message for r in caplog.records)


def test_ceiling_noop_when_under_cap_or_explicitly_uncapped(caplog):
    with caplog.at_level("WARNING"):
        assert apply_source_ceiling(_SOURCES, 10) == _SOURCES
        assert apply_source_ceiling(_SOURCES, None) == _SOURCES
    assert not any("budget ceiling" in r.message for r in caplog.records)


@pytest.mark.parametrize("bad_cap", [0, -1, -100])
def test_zero_or_negative_ceiling_fails_closed(bad_cap):
    """0/negative must never mean uncapped — the guard fails closed."""
    with pytest.raises(ValueError, match="fails closed"):
        apply_source_ceiling(_SOURCES, bad_cap)


def test_cap_resolution_cli_beats_env_beats_uncapped(monkeypatch):
    monkeypatch.setenv("ONELIVE_MAX_SOURCES_PER_RUN", "7")
    assert _resolve_source_cap(3) == 3
    assert _resolve_source_cap(None) == 7
    monkeypatch.delenv("ONELIVE_MAX_SOURCES_PER_RUN")
    assert _resolve_source_cap(None) is None


@pytest.mark.parametrize("bad_env", ["twenty", "0", "-3", ""])
def test_bad_env_cap_fails_loud(monkeypatch, bad_env):
    monkeypatch.setenv("ONELIVE_MAX_SOURCES_PER_RUN", bad_env)
    with pytest.raises(SystemExit):
        _resolve_source_cap(None)


def test_nonpositive_cli_cap_fails_loud(monkeypatch):
    monkeypatch.delenv("ONELIVE_MAX_SOURCES_PER_RUN", raising=False)
    with pytest.raises(SystemExit):
        _resolve_source_cap(0)


@pytest.mark.parametrize("bad_arg", ["0", "-2", "abc"])
def test_argparse_type_rejects_nonpositive_and_garbage(bad_arg):
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int(bad_arg)


def test_argparse_type_accepts_positive():
    assert _positive_int("25") == 25


def _row(sid, last, config=None):
    # Mirrors the real SELECT's column order, config included: the rotation key
    # unpacks first/last by position-name precisely so a middle column can be
    # added without shifting what gets sorted — this row proves that holds.
    return (sid, f"name-{sid}", f"https://x/{sid}", "venue_site", config or {}, last)


_TZ = _dt.timezone.utc


def test_rotation_never_fetched_first_then_stalest():
    """Never-fetched sources lead; fetched ones follow stalest-first. This is
    the property that makes the capped scheduled cron sweep the catalog
    instead of starving the tail (the cap truncates AFTER this ordering)."""
    fresh = _row("c", _dt.datetime(2026, 7, 21, 12, 0, tzinfo=_TZ))
    stale = _row("b", _dt.datetime(2026, 7, 1, 12, 0, tzinfo=_TZ))
    never = _row("a", None)
    assert order_for_rotation([fresh, stale, never]) == [never, stale, fresh]


def test_rotation_tiebreak_is_deterministic_by_source_id():
    same_ts = _dt.datetime(2026, 7, 20, 9, 0, tzinfo=_TZ)
    rows = [_row("z", same_ts), _row("m", same_ts), _row("a", same_ts),
            _row("q", None), _row("b", None)]
    ordered = order_for_rotation(rows)
    assert [r[0] for r in ordered] == ["b", "q", "a", "m", "z"]


def test_rotation_composes_with_ceiling_to_rotate_coverage():
    """Simulate two consecutive capped runs: run 1 takes the never-fetched
    pair; once they carry fresh timestamps, run 2's window moves on to the
    previously-starved stale source — coverage rotates, never pins."""
    t = lambda d: _dt.datetime(2026, 7, d, 12, 0, tzinfo=_TZ)
    rows = [_row("s1", None), _row("s2", None), _row("s3", t(1))]
    run1 = apply_source_ceiling(order_for_rotation(rows), 2)
    assert [r[0] for r in run1] == ["s1", "s2"]
    rows2 = [_row("s1", t(21)), _row("s2", t(21)), _row("s3", t(1))]
    run2 = apply_source_ceiling(order_for_rotation(rows2), 2)
    assert run2[0][0] == "s3"


def test_run_real_wires_rotation_before_the_cap(monkeypatch):
    """PR #43 r1 nit made regression-proof: _run_real must pass the DB rows
    through order_for_rotation() BEFORE apply_source_ceiling(). The fake DB
    returns fresh-first rows; with cap=2, only rotation-before-cap yields
    [never-fetched, stalest] — a cap applied to raw DB order would keep
    'fresh' and starve the tail, which is the exact defect rotation fixes."""
    import contextlib

    import ai.claude_provider as claude_provider
    import worker.candidate_store as candidate_store
    import worker.run_once as run_once

    fresh = _row("fresh", _dt.datetime(2026, 7, 21, tzinfo=_TZ))
    stale = _row("stale", _dt.datetime(2026, 7, 1, tzinfo=_TZ))
    never = _row("never", None)

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, sql):
            assert "last_fetched_at" in sql  # the rotation column is queried

        def fetchall(self):
            return [fresh, stale, never]  # deliberately freshest-first

    class _Conn:
        def cursor(self):
            return _Cursor()

    @contextlib.contextmanager
    def _fake_db():
        yield _Conn()

    captured = {}

    class _Report:
        run_id = "wiring-test"
        counts = {"errors": 0}
        results = []

    def _fake_run_loop(ai, sources, sxsw_mode, dsn):
        captured["sources"] = sources
        return _Report()

    monkeypatch.setenv("ONELIVE_DB_DSN", "postgresql://unused")
    monkeypatch.setattr(claude_provider, "ClaudeProvider", lambda: object())
    monkeypatch.setattr(candidate_store, "db", _fake_db)
    monkeypatch.setattr(run_once, "run_loop", _fake_run_loop)

    assert run_once._run_real(max_sources=2) == 0
    assert [s["source_id"] for s in captured["sources"]] == ["never", "stale"]
