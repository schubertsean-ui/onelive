"""Tests for tools/model_router.py — the stage→model cost-routing resolver.

Hermetic: pure logic. Proves policy defaults resolve, env overrides win in
the documented precedence (ONELIVE_MODEL_<STAGE> > legacy OPENAI_REVIEW_MODEL
> default), unknown stages fail loud (typos must never silently route), and
present-but-empty overrides raise (the PR #11/#12 empty-env lesson).
"""
import importlib.util
import pathlib
import sys

import pytest

_TOOL_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "model_router.py"
_spec = importlib.util.spec_from_file_location("model_router", _TOOL_PATH)
mr = importlib.util.module_from_spec(_spec)
sys.modules["model_router"] = mr
_spec.loader.exec_module(mr)


def test_defaults_resolve_for_every_unblocked_stage(monkeypatch):
    monkeypatch.delenv("OPENAI_REVIEW_MODEL", raising=False)
    for stage, model in mr.STAGE_MODELS.items():
        if stage == "extraction":
            continue  # fail-closed until R-006 ratifies — proven below
        monkeypatch.delenv(f"ONELIVE_MODEL_{stage.upper()}", raising=False)
        assert mr.resolve_model(stage) == model


def test_extraction_fails_closed_until_threshold_ratified(monkeypatch):
    """R-006: the §11.2 extraction hallucination threshold is unratified, so
    the extraction stage must not resolve to ANY model — and an env override
    must not bypass the block (it's about the missing gate, not the model)."""
    assert mr.EXTRACTION_THRESHOLD_RATIFIED is False
    with pytest.raises(ValueError, match="R-006"):
        mr.resolve_model("extraction")
    monkeypatch.setenv("ONELIVE_MODEL_EXTRACTION", "claude-opus-4-8")
    with pytest.raises(ValueError, match="R-006"):
        mr.resolve_model("extraction")


def test_extraction_resolves_once_ratified(monkeypatch):
    """When the founder ratifies the threshold (flag flipped in that commit),
    extraction routes to its documented starting tier."""
    monkeypatch.setattr(mr, "EXTRACTION_THRESHOLD_RATIFIED", True)
    monkeypatch.delenv("ONELIVE_MODEL_EXTRACTION", raising=False)
    assert mr.resolve_model("extraction") == mr.STAGE_MODELS["extraction"]


def test_env_override_beats_default(monkeypatch):
    monkeypatch.setenv("ONELIVE_MODEL_MECHANICAL", "claude-sonnet-4-6")
    assert mr.resolve_model("mechanical") == "claude-sonnet-4-6"


def test_evaluator_precedence_specific_beats_legacy(monkeypatch):
    monkeypatch.setenv("OPENAI_REVIEW_MODEL", "gpt-5.5-legacy")
    monkeypatch.delenv("ONELIVE_MODEL_EVALUATOR", raising=False)
    assert mr.resolve_model("evaluator") == "gpt-5.5-legacy"
    monkeypatch.setenv("ONELIVE_MODEL_EVALUATOR", "gpt-5.5-specific")
    assert mr.resolve_model("evaluator") == "gpt-5.5-specific"


def test_evaluator_rejects_generator_family_override(monkeypatch):
    """Trust invariant (charter §0.2): a Claude/Anthropic model must never be
    routed into the evaluator slot — that would be the generator grading its
    own work. Both env channels must fail closed, case-insensitively."""
    monkeypatch.delenv("OPENAI_REVIEW_MODEL", raising=False)
    for env_name in ("ONELIVE_MODEL_EVALUATOR", "OPENAI_REVIEW_MODEL"):
        for bad in ("claude-opus-4-8", "Claude-Haiku-4-5", "anthropic/claude-sonnet-4-6"):
            monkeypatch.setenv(env_name, bad)
            with pytest.raises(ValueError, match="write/grade separation"):
                mr.resolve_model("evaluator")
        monkeypatch.delenv(env_name, raising=False)


def test_evaluator_default_is_not_generator_family():
    """The policy default itself must satisfy the separation invariant."""
    assert not any(
        m in mr.STAGE_MODELS["evaluator"].lower()
        for m in ("claude", "anthropic")
    )


def test_generator_stages_still_accept_claude_overrides(monkeypatch):
    """The separation rule constrains ONLY the evaluator slot — generator
    stages routing to Claude tiers is the whole point of the policy."""
    monkeypatch.setenv("ONELIVE_MODEL_MECHANICAL", "claude-opus-4-8")
    assert mr.resolve_model("mechanical") == "claude-opus-4-8"


def test_unknown_stage_fails_loud():
    with pytest.raises(KeyError):
        mr.resolve_model("vibes")


def test_empty_override_fails_loud(monkeypatch):
    monkeypatch.setenv("ONELIVE_MODEL_STANDARD", "")
    with pytest.raises(ValueError):
        mr.resolve_model("standard")


def test_whitespace_only_override_fails_loud(monkeypatch):
    """Whitespace-only is the same misconfig class as empty (CI forwards
    unset vars as empty strings; a stray space must not sneak past)."""
    monkeypatch.setenv("ONELIVE_MODEL_STANDARD", "   ")
    with pytest.raises(ValueError):
        mr.resolve_model("standard")


def test_override_value_is_stripped(monkeypatch):
    monkeypatch.setenv("ONELIVE_MODEL_STANDARD", " claude-sonnet-4-6 ")
    assert mr.resolve_model("standard") == "claude-sonnet-4-6"


def test_implausible_model_ids_fail_loud(monkeypatch):
    """Overrides must look like model ids — newlines especially matter because
    CI writes the resolved id into $GITHUB_OUTPUT, where an embedded newline
    could smuggle extra output lines."""
    for bad in ("model\nextra=1", "model with spaces", "model;rm", "$(cmd)"):
        monkeypatch.setenv("ONELIVE_MODEL_STANDARD", bad)
        with pytest.raises(ValueError, match="plausible model id"):
            mr.resolve_model("standard")


def test_cli_exit_codes(monkeypatch, capsys):
    monkeypatch.delenv("ONELIVE_MODEL_CRITICAL", raising=False)
    assert mr.main(["critical"]) == 0
    assert capsys.readouterr().out.strip() == "claude-opus-4-8"
    assert mr.main(["bogus"]) == 2
