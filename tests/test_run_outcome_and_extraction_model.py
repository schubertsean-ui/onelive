"""Tests for the first-real-run fixes (2026-07-15).

Proves: (1) a run where EVERY attempted source errored raises
TotalRunFailure — so the deadman context pings /fail instead of recording
a healthy heartbeat for a dead run; partial errors stay a success; (2) the
REAL provider consults the routing gate at its own entry point — blocked
while the golden-set gate is unshipped (R-013), single-sourced model id
once it ships, fail-closed on present-but-empty env AND blank explicit
model arguments.
"""
import pytest

from ai.claude_provider import ClaudeProvider, ExtractionConfigError
from worker.run_once import TotalRunFailure, enforce_useful_work


# --- zero-useful-work runs must fail loud ------------------------------------
def test_all_sources_errored_raises():
    with pytest.raises(TotalRunFailure, match="zero useful work"):
        enforce_useful_work({"errors": 3}, attempted=3)


def test_more_errors_than_attempted_still_raises():
    with pytest.raises(TotalRunFailure):
        enforce_useful_work({"errors": 5}, attempted=3)


def test_partial_errors_are_a_loud_success(caplog):
    with caplog.at_level("WARNING"):
        enforce_useful_work({"errors": 1, "passed": 2}, attempted=3)
    assert "1 of 3" in caplog.text


def test_clean_run_is_silent_success(caplog):
    with caplog.at_level("WARNING"):
        enforce_useful_work({"errors": 0, "passed": 3}, attempted=3)
    assert "errored" not in caplog.text


def test_zero_attempted_does_not_raise():
    """No sources attempted is handled upstream (its own loud error path) —
    this guard must not misfire on the empty case."""
    assert enforce_useful_work({"errors": 0}, attempted=0) is None


# --- extraction model resolution: the gate lives AT the entry point ----------
def test_provider_blocked_while_golden_gate_absent():
    """Integration (evaluator finding, PR #21 r1): constructing the REAL
    provider with no explicit model must consult the routing gate and fail
    loudly while the golden-set gate is unshipped (R-013) — the invariant
    is enforced where extraction actually runs, not only in the tool."""
    with pytest.raises(ExtractionConfigError, match="R-013"):
        ClaudeProvider(api_key="test")


def test_provider_resolves_via_router_once_gate_ships(monkeypatch):
    import tools.model_router as mr
    monkeypatch.setattr(mr, "EXTRACTION_THRESHOLD_RATIFIED", True)
    monkeypatch.delenv("ONELIVE_MODEL_EXTRACTION", raising=False)
    monkeypatch.delenv("ONELIVE_CLAUDE_MODEL", raising=False)
    p = ClaudeProvider(api_key="test")
    assert p.model == mr.STAGE_MODELS["extraction"]  # single-sourced id
    monkeypatch.setenv("ONELIVE_MODEL_EXTRACTION", "claude-sonnet-4-6")
    assert ClaudeProvider(api_key="test").model == "claude-sonnet-4-6"


def test_provider_empty_env_fails_closed_via_router(monkeypatch):
    """Present-but-empty env is rejected by the router the provider now
    consults (4th appearance of the empty-env class — KAIZEN class watch)."""
    import tools.model_router as mr
    monkeypatch.setattr(mr, "EXTRACTION_THRESHOLD_RATIFIED", True)
    monkeypatch.setenv("ONELIVE_MODEL_EXTRACTION", "   ")
    with pytest.raises(ExtractionConfigError, match="empty"):
        ClaudeProvider(api_key="test")


def test_explicit_model_channel_fails_closed_on_blank():
    """The test/caller-owned explicit channel must not fail open either:
    model="" or whitespace is misconfiguration, never 'use the default'
    (evaluator finding, PR #21 r1)."""
    for blank in ("", "   "):
        with pytest.raises(ExtractionConfigError, match="empty/whitespace"):
            ClaudeProvider(api_key="test", model=blank)
    assert ClaudeProvider(api_key="test", model=" claude-test ").model == "claude-test"
