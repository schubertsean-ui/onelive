"""Tests for tools/po_battery.py — the po provocation-battery generator.

Proves: every standalone operator appears in the output; random entry and
the founder-directed RANDOM+operator combos are present; seeding makes the
battery deterministic while different seeds vary the random word; movement
techniques are always attached; empty statements fail loud.
"""
import importlib.util
import pathlib
import sys

import pytest

_TOOL_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "po_battery.py"
_spec = importlib.util.spec_from_file_location("po_battery", _TOOL_PATH)
po = importlib.util.module_from_spec(_spec)
sys.modules["po_battery"] = po
_spec.loader.exec_module(po)

STATEMENT = "venues publish their own events"


def test_every_standalone_operator_present():
    out = po.build_battery(STATEMENT, seed=1)
    for title in ("P1 ESCAPE", "P2 REVERSAL", "P3 EXAGGERATION",
                  "P4 DISTORTION", "P5 WISHFUL", "P6 ABSURD",
                  "P7 RANDOM ENTRY"):
        assert title in out, f"operator {title} missing from battery"


def test_random_plus_operator_combos_present():
    out = po.build_battery(STATEMENT, seed=1, combos=2)
    assert "P8.1 RANDOM +" in out
    assert "P8.2 RANDOM +" in out


def test_movement_techniques_always_attached():
    out = po.build_battery(STATEMENT, seed=1)
    for fragment in ("extract a principle", "focus on the difference",
                     "moment to moment", "positive aspects",
                     "special circumstances"):
        assert fragment in out


def test_seed_makes_battery_deterministic():
    assert po.build_battery(STATEMENT, seed=42) == po.build_battery(STATEMENT, seed=42)


def test_different_seeds_vary_the_random_word():
    words = {po.build_battery(STATEMENT, seed=s) for s in range(8)}
    assert len(words) > 1, "random entry must actually vary across seeds"


def test_statement_is_embedded_and_judging_deferred():
    out = po.build_battery(STATEMENT, seed=1)
    assert STATEMENT in out
    assert "before judging" in out
    assert "never bypasses its filters" in out


def test_empty_statement_fails_loud():
    with pytest.raises(ValueError):
        po.build_battery("   ")
    assert po.main(["   "]) == 2


def test_cli_prints_battery(capsys):
    assert po.main([STATEMENT, "--seed", "7"]) == 0
    assert "PO BATTERY" in capsys.readouterr().out
