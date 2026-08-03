"""Guards for the integrity plugin (integrity-plugin/).

Keeps the portable plugin truthful and in lockstep with the repo-local
enforcement so other lanes inherit exactly what onelive runs:
- manifests parse and agree on names/paths;
- plugin hook commands only invoke ${CLAUDE_PLUGIN_ROOT} scripts that exist;
- the plugin gate's decision logic matches the repo-local gate on the shared
  contract convention (five uppercase fields + STATUS: OPEN);
- fail-closed branches hold (unreadable state, malformed .plan-first.json).
"""
import importlib.util
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_DIR = os.path.join(REPO, "integrity-plugin", "plugins", "integrity")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


plugin_gate = _load(
    "plugin_plan_first_gate",
    os.path.join(PLUGIN_DIR, "scripts", "plan_first_gate.py"))
local_gate = _load(
    "local_plan_first_gate",
    os.path.join(REPO, "tools", "plan_first_gate.py"))

FULL_PLAN_OPEN = """# STATE

## Session Contract #1 (test)
- WHAT: build X.
- HOW: small batches.
- WHY: founder directed.
- WHY-IT-MATTERS: ships value.
- EXPECTED OUTCOMES: gates green.
STATUS: OPEN.
"""


def _edit(root, rel):
    return {"tool_name": "Edit",
            "tool_input": {"file_path": os.path.join(root, rel)}}


def test_marketplace_and_plugin_manifests_agree():
    mp_path = os.path.join(REPO, "integrity-plugin", ".claude-plugin",
                           "marketplace.json")
    with open(mp_path, encoding="utf-8") as f:
        mp = json.load(f)
    assert mp["name"] == "onelive-integrity"
    [entry] = mp["plugins"]
    assert entry["name"] == "integrity"
    assert entry["source"] == "./plugins/integrity"

    with open(os.path.join(PLUGIN_DIR, ".claude-plugin", "plugin.json"),
              encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["name"] == "integrity"


def test_plugin_hooks_only_invoke_plugin_scripts():
    with open(os.path.join(PLUGIN_DIR, "hooks", "hooks.json"),
              encoding="utf-8") as f:
        hooks = json.load(f)["hooks"]
    shape = re.compile(
        r'^python3 "\$\{CLAUDE_PLUGIN_ROOT\}"/scripts/[a-z0-9_]+\.py$')
    commands = [h["command"]
                for matchers in hooks.values()
                for m in matchers for h in m["hooks"]]
    assert commands, "plugin wires no hooks"
    for cmd in commands:
        assert h_type_is_command(hooks, cmd)
        assert shape.match(cmd), cmd
        script = cmd.split("/scripts/", 1)[1]
        assert os.path.isfile(os.path.join(PLUGIN_DIR, "scripts", script)), script


def h_type_is_command(hooks, cmd):
    for matchers in hooks.values():
        for m in matchers:
            for h in m["hooks"]:
                if h.get("command") == cmd and h.get("type") == "command":
                    return True
    return False


def test_plugin_and_local_gate_agree_on_the_contract_convention(tmp_path):
    """Lockstep guard: both gates must accept the same OPEN five-field
    contract and both must reject the same planless state."""
    product = str(tmp_path / "worker" / "promote.py")
    for state, expected in ((FULL_PLAN_OPEN, "allow"),
                            ("# STATE\nno contract\n", "deny")):
        p_dec, _ = plugin_gate.decide(
            {"tool_name": "Edit", "tool_input": {"file_path": product}},
            root=str(tmp_path), state_text=state)
        l_dec, _ = local_gate.decide(
            {"tool_name": "Edit", "tool_input": {"file_path": product}},
            repo_root=str(tmp_path), state_text=state)
        assert p_dec == l_dec == expected


def test_plugin_gate_fails_closed_on_missing_state(tmp_path):
    decision, reason = plugin_gate.decide(
        _edit(str(tmp_path), "api/main.py"), root=str(tmp_path))
    assert decision == "deny"
    assert "fail closed" in reason


def test_plugin_gate_fails_closed_on_malformed_config(tmp_path):
    (tmp_path / ".plan-first.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "STATE.md").write_text(FULL_PLAN_OPEN, encoding="utf-8")
    decision, reason = plugin_gate.decide(
        _edit(str(tmp_path), "api/main.py"), root=str(tmp_path))
    assert decision == "deny"
    assert ".plan-first.json" in reason


def test_plugin_gate_honors_custom_state_file(tmp_path):
    (tmp_path / ".plan-first.json").write_text(
        json.dumps({"state_file": "LANE_STATE.md"}), encoding="utf-8")
    (tmp_path / "LANE_STATE.md").write_text(FULL_PLAN_OPEN, encoding="utf-8")
    decision, _ = plugin_gate.decide(
        _edit(str(tmp_path), "api/main.py"), root=str(tmp_path))
    assert decision == "allow"
    # And the custom state file itself is bookkeeping (writable).
    decision, _ = plugin_gate.decide(
        _edit(str(tmp_path), "LANE_STATE.md"), root=str(tmp_path))
    assert decision == "allow"


def test_charter_and_pastein_exist_and_are_nonempty():
    for rel in ("charter/OPERATING_INTEGRITY_CHARTER.md",
                "charter/CLAUDE_PROJECT_PASTEIN.md"):
        path = os.path.join(PLUGIN_DIR, rel)
        assert os.path.isfile(path), f"missing {rel}"
        with open(path, encoding="utf-8") as f:
            assert len(f.read()) > 500, f"{rel} suspiciously empty"
