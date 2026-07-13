"""Tests for worker/run_once.py budget ceilings (§14.3 — caps before the loop).

Pure logic, no DB/network: proves the per-run source ceiling truncates
deterministically and loudly, FAILS CLOSED on 0/negative/garbage values from
every input channel (CLI flag, argparse type, env var — a budget guard must
never fail open; evaluator finding PR #12 round 1), and that CLI beats env
beats uncapped-with-loud-warning in _resolve_source_cap.
"""
import argparse

import pytest

from worker.run_once import _positive_int, _resolve_source_cap, apply_source_ceiling

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


@pytest.mark.parametrize("bad_env", ["twenty", "0", "-3"])
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
