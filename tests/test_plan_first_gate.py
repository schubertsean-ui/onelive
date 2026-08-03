"""Tests for the §4a plan-first PreToolUse gate (tools/plan_first_gate.py).

Guards the guard: the gate must (a) block product-file edits when no OPEN
contract carries the five plan fields, (b) allow bookkeeping surfaces
unconditionally so the contract itself can be written, (c) fail CLOSED on an
unreadable STATE.md, and (d) never confuse lowercase prose with the uppercase
field labels. Origin: KAIZEN 2026-08-03 build-before-plan (founder-caught).
"""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "plan_first_gate",
    os.path.join(os.path.dirname(__file__), "..", "tools", "plan_first_gate.py"))
pfg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pfg)

REPO = pfg.REPO_ROOT

FULL_PLAN_OPEN = """# STATE

## Session Contract #99 (test)

PLAN:
- WHAT: build X.
- HOW: in small batches.
- WHY: the founder directed it.
- WHY-IT-MATTERS: it ships value.
- EXPECTED OUTCOMES: X works, gates green.

STATUS: OPEN.

## Session Contract #98 (older)
STATUS: DELIVERED.
"""

def _edit(path):
    return {"tool_name": "Edit", "tool_input": {"file_path": path}}


def test_product_file_blocked_without_open_plan():
    state = "# STATE\n\n## Session Contract #1\nGOAL: x\nSTATUS: DELIVERED.\n"
    decision, reason = pfg.decide(_edit(os.path.join(REPO, "worker", "promote.py")),
                                  state_text=state)
    assert decision == "deny"
    assert "§4a" in reason and "WHAT" in reason


def test_product_file_allowed_with_open_five_field_plan():
    decision, _ = pfg.decide(_edit(os.path.join(REPO, "worker", "promote.py")),
                             state_text=FULL_PLAN_OPEN)
    assert decision == "allow"


def test_open_contract_missing_a_field_blocks():
    state = FULL_PLAN_OPEN.replace("- EXPECTED OUTCOMES: X works, gates green.\n", "")
    decision, _ = pfg.decide(_edit(os.path.join(REPO, "api", "main.py")),
                             state_text=state)
    assert decision == "deny"


def test_delivered_contract_with_plan_fields_blocks():
    state = FULL_PLAN_OPEN.replace("STATUS: OPEN.", "STATUS: DELIVERED.")
    decision, _ = pfg.decide(_edit(os.path.join(REPO, "api", "main.py")),
                             state_text=state)
    assert decision == "deny"


def test_lowercase_prose_does_not_satisfy_labels():
    state = ("# STATE\n\n## Session Contract #2\n"
             "we know what to do and how, and why it matters; expected outcomes "
             "are described in prose.\nSTATUS: OPEN.\n")
    decision, _ = pfg.decide(_edit(os.path.join(REPO, "web", "lib", "feed.ts")),
                             state_text=state)
    assert decision == "deny"


def test_bookkeeping_surfaces_always_allowed():
    state = "# STATE\n(no contracts at all)\n"
    for rel in ("STATE.md", "TODOS.md", "docs/ONE_LIVE_CHANGE_LOG.md",
                "docs/memory/RED_CLASSES.md", "docs/metrics/KAIZEN_LEDGER.md",
                "docs/session_arcs/2026-08-03_x.md", ".claude/settings.json"):
        decision, reason = pfg.decide(_edit(os.path.join(REPO, rel)),
                                      state_text=state)
        assert decision == "allow", (rel, reason)


def test_outside_repo_allowed():
    decision, _ = pfg.decide(_edit("/tmp/scratchpad/notes.md"), state_text="")
    assert decision == "allow"


def test_unreadable_state_fails_closed(tmp_path):
    # Point the gate at an empty repo root with no STATE.md at all.
    decision, reason = pfg.decide(
        {"tool_name": "Write",
         "tool_input": {"file_path": str(tmp_path / "product.py")}},
        repo_root=str(tmp_path), state_text=None)
    assert decision == "deny"
    assert "fail closed" in reason


def test_missing_file_path_allows():
    decision, _ = pfg.decide({"tool_name": "Edit", "tool_input": {}},
                             state_text="")
    assert decision == "allow"


def test_hooks_stay_wired_in_project_settings():
    """The founder's 'never have to check' property: silently unwiring either
    hook from .claude/settings.json fails the suite (and validate, and CI)."""
    import json
    with open(os.path.join(REPO, ".claude", "settings.json"), encoding="utf-8") as f:
        settings = json.load(f)
    hooks = settings["hooks"]

    session_start_cmds = [h["command"]
                          for m in hooks["SessionStart"] for h in m["hooks"]
                          if h.get("type") == "command"]
    assert any("plan_first_banner.py" in c for c in session_start_cmds)

    pre_tool = [m for m in hooks["PreToolUse"]
                if "Write" in m.get("matcher", "") and "Edit" in m.get("matcher", "")]
    assert pre_tool, "PreToolUse Write|Edit matcher missing"
    gate_cmds = [h["command"] for m in pre_tool for h in m["hooks"]
                 if h.get("type") == "command"]
    assert any("plan_first_gate.py" in c for c in gate_cmds)


def test_founder_canonical_fourth_field_satisfies_gate():
    # Founder-corrected 2026-08-03: WHY-THAT-WHY-MATTERS ("why THAT 'why'
    # matters") is the canonical phrasing; the gate accepts it and the
    # WHY-IT-MATTERS shorthand equally.
    state = FULL_PLAN_OPEN.replace("- WHY-IT-MATTERS: it ships value.",
                                   "- WHY-THAT-WHY-MATTERS: it ships value.")
    decision, _ = pfg.decide(_edit(os.path.join(REPO, "api", "main.py")),
                             state_text=state)
    assert decision == "allow"
