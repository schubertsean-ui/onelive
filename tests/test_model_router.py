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


def test_defaults_resolve_for_every_stage(monkeypatch):
    monkeypatch.delenv("OPENAI_REVIEW_MODEL", raising=False)
    for stage, model in mr.STAGE_MODELS.items():
        monkeypatch.delenv(f"ONELIVE_MODEL_{stage.upper()}", raising=False)
        assert mr.resolve_model(stage) == model


def test_env_override_beats_default(monkeypatch):
    monkeypatch.setenv("ONELIVE_MODEL_MECHANICAL", "claude-sonnet-4-6")
    assert mr.resolve_model("mechanical") == "claude-sonnet-4-6"


def test_evaluator_precedence_specific_beats_legacy(monkeypatch):
    monkeypatch.setenv("OPENAI_REVIEW_MODEL", "legacy-model")
    monkeypatch.delenv("ONELIVE_MODEL_EVALUATOR", raising=False)
    assert mr.resolve_model("evaluator") == "legacy-model"
    monkeypatch.setenv("ONELIVE_MODEL_EVALUATOR", "specific-model")
    assert mr.resolve_model("evaluator") == "specific-model"


def test_unknown_stage_fails_loud():
    with pytest.raises(KeyError):
        mr.resolve_model("vibes")


def test_empty_override_fails_loud(monkeypatch):
    monkeypatch.setenv("ONELIVE_MODEL_STANDARD", "")
    with pytest.raises(ValueError):
        mr.resolve_model("standard")


def test_cli_exit_codes(monkeypatch, capsys):
    monkeypatch.delenv("ONELIVE_MODEL_CRITICAL", raising=False)
    assert mr.main(["critical"]) == 0
    assert capsys.readouterr().out.strip() == "claude-opus-4-8"
    assert mr.main(["bogus"]) == 2
