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


def _row(sid, last):
    return (sid, f"name-{sid}", f"https://x/{sid}", "venue_site", last)


_TZ = _dt.timezone.utc


def test_rotation_never_fetched_first_then_stalest():
    """Never-fetched sources lead; fetched ones follow stalest-first. This is
    the property that makes an hourly capped cron sweep the catalog instead
    of starving the tail (the cap truncates AFTER this ordering)."""
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
