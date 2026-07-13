"""Tests for worker/run_once.py budget ceilings (§14.3 — caps before the loop).

Pure logic, no DB/network: proves the per-run source ceiling truncates
deterministically and loudly, that CLI beats env beats uncapped in
_resolve_source_cap, and that a garbage env value fails loud instead of
silently running uncapped.
"""
import pytest

from worker.run_once import _resolve_source_cap, apply_source_ceiling

_SOURCES = [{"name": f"s{i}"} for i in range(5)]


def test_ceiling_truncates_in_order_and_warns(caplog):
    with caplog.at_level("WARNING"):
        capped = apply_source_ceiling(_SOURCES, 2)
    assert capped == _SOURCES[:2]
    assert any("budget ceiling" in r.message for r in caplog.records)


def test_ceiling_noop_when_under_cap_or_uncapped(caplog):
    with caplog.at_level("WARNING"):
        assert apply_source_ceiling(_SOURCES, 10) == _SOURCES
        assert apply_source_ceiling(_SOURCES, None) == _SOURCES
        assert apply_source_ceiling(_SOURCES, 0) == _SOURCES  # 0/neg = uncapped
    assert not any("budget ceiling" in r.message for r in caplog.records)


def test_cap_resolution_cli_beats_env_beats_uncapped(monkeypatch):
    monkeypatch.setenv("ONELIVE_MAX_SOURCES_PER_RUN", "7")
    assert _resolve_source_cap(3) == 3
    assert _resolve_source_cap(None) == 7
    monkeypatch.delenv("ONELIVE_MAX_SOURCES_PER_RUN")
    assert _resolve_source_cap(None) is None


def test_garbage_env_cap_fails_loud(monkeypatch):
    monkeypatch.setenv("ONELIVE_MAX_SOURCES_PER_RUN", "twenty")
    with pytest.raises(SystemExit):
        _resolve_source_cap(None)
