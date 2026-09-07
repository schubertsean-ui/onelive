"""Ceremony is off. Product writes are allowed with no Session Contract.

Founder 2026-09-07: the plan-first hook burned the turn budget before code.
"""
import importlib.util
import json
import os

_spec = importlib.util.spec_from_file_location(
    "plan_first_gate",
    os.path.join(os.path.dirname(__file__), "..", "tools", "plan_first_gate.py"))
pfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pfg)

REPO = pfg.REPO_ROOT


def _edit(path):
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


def test_product_file_allowed_with_no_plan():
    decision, reason = pfg.decide(
        _edit(os.path.join(REPO, "worker", "promote.py")),
        state_text="# STATE\nno contract\n")
    assert decision == "allow"
    assert "ceremony off" in reason


def test_product_file_allowed_when_state_unreadable(tmp_path):
    decision, reason = pfg.decide(
        {"tool_name": "Write",
         "tool_input": {"file_path": str(tmp_path / "product.py")}},
        repo_root=str(tmp_path), state_text=None)
    assert decision == "allow"


def test_hooks_are_unwired():
    """Silently re-wiring plan-first hooks fails the suite."""
    with open(os.path.join(REPO, ".claude", "settings.json"), encoding="utf-8") as f:
        settings = json.load(f)
    hooks = settings.get("hooks") or {}
    assert hooks.get("SessionStart", []) == []
    assert hooks.get("PreToolUse", []) == []
