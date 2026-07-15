"""Tests for the first-real-run fixes (2026-07-15).

Proves: (1) a run where EVERY attempted source errored raises
TotalRunFailure — so the deadman context pings /fail instead of recording
a healthy heartbeat for a dead run; partial errors stay a success; (2) the
extraction model default is a live routed-tier id, never the retired one,
and env resolution fails closed on present-but-empty (the CI empty-env
class, 4th appearance).
"""
import pytest

from ai.claude_provider import (
    DEFAULT_MODEL,
    ClaudeProvider,
    ExtractionConfigError,
)
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


# --- extraction model resolution ----------------------------------------------
def test_default_model_is_routed_tier_not_the_retired_id():
    assert DEFAULT_MODEL == "claude-haiku-4-5"
    assert "3-5" not in DEFAULT_MODEL  # the id that 404'd on the first run


def test_env_override_precedence(monkeypatch):
    monkeypatch.setenv("ONELIVE_MODEL_EXTRACTION", "claude-sonnet-4-6")
    monkeypatch.setenv("ONELIVE_CLAUDE_MODEL", "legacy-id")
    p = ClaudeProvider(api_key="test")
    assert p.model == "claude-sonnet-4-6"
    monkeypatch.delenv("ONELIVE_MODEL_EXTRACTION")
    assert ClaudeProvider(api_key="test").model == "legacy-id"
    monkeypatch.delenv("ONELIVE_CLAUDE_MODEL")
    assert ClaudeProvider(api_key="test").model == DEFAULT_MODEL


def test_empty_model_env_fails_closed(monkeypatch):
    """Present-but-empty is a misconfiguration, never a silent default —
    the 4th appearance of this defect class (see KAIZEN class watch)."""
    for env_name in ("ONELIVE_MODEL_EXTRACTION", "ONELIVE_CLAUDE_MODEL"):
        monkeypatch.setenv(env_name, "   ")
        with pytest.raises(ExtractionConfigError, match="set but empty"):
            ClaudeProvider(api_key="test")
        monkeypatch.delenv(env_name)
