"""Change-set discipline gate — docs/skills/change_set_discipline.md.

This exists because the lesson was written twice as prose and executed zero
times. The tests therefore check the one property prose cannot have: that
something FAILS.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import tools.change_set_gate as gate  # noqa: E402


def _measure(files: int, lines: int) -> dict:
    return {"base": "b", "head": "h", "reviewable_files": files,
            "reviewable_lines": lines, "largest": []}


def test_a_change_past_the_review_ceiling_FAILS(monkeypatch, capsys):
    """Beyond the measured collapse point a change is skimmed, not reviewed."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(5, gate.HARD_LINES + 1))
    monkeypatch.setattr(gate, "load_freeze", lambda: None)
    monkeypatch.setattr(gate, "_git", lambda *a: "x")
    assert gate.main([]) == 1
    assert "SPLIT IT" in capsys.readouterr().err


def test_too_many_files_FAILS(monkeypatch, capsys):
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(gate.HARD_FILES + 1, 100))
    monkeypatch.setattr(gate, "load_freeze", lambda: None)
    monkeypatch.setattr(gate, "_git", lambda *a: "x")
    assert gate.main([]) == 1
    assert "files exceeds" in capsys.readouterr().err


def test_a_change_within_limits_PASSES(monkeypatch):
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD": _measure(4, 120))
    monkeypatch.setattr(gate, "load_freeze", lambda: None)
    monkeypatch.setattr(gate, "_git", lambda *a: "x")
    assert gate.main([]) == 0


def test_the_soft_limit_WARNS_but_does_not_block(monkeypatch, capsys):
    """400 lines is where detection degrades, not where review is impossible.
    Failing there would make the gate unusable and it would be turned off."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(5, gate.SOFT_LINES + 10))
    monkeypatch.setattr(gate, "load_freeze", lambda: None)
    monkeypatch.setattr(gate, "_git", lambda *a: "x")
    assert gate.main([]) == 0
    assert "degrade" in capsys.readouterr().out


def test_SCOPE_GROWTH_UNDER_REVIEW_fails(monkeypatch, capsys):
    """THE rule. A review whose subject expands between rounds cannot converge:
    each round judges a bigger change than the last, and fixes from one round
    become the blockers of the next. #68 (22 rounds) and #74 (11) both died
    here."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(10, 1000))
    monkeypatch.setattr(gate, "load_freeze", lambda: {
        "branch": "feature", "reviewable_files": 8,
        "reviewable_lines": 1000 - gate.MAX_GROWTH_LINES - 1})
    monkeypatch.setattr(gate, "_git", lambda *a: "feature")
    assert gate.main([]) == 1
    err = capsys.readouterr().err
    assert "SCOPE GREW UNDER REVIEW" in err
    assert "new branch" in err.lower(), "must name the remedy, not just the sin"


def test_adopting_a_blocker_is_allowed_growth(monkeypatch):
    """The tolerance is not zero on purpose: fixing what a reviewer found
    legitimately adds lines. Zero tolerance would make the gate absurd and it
    would be disabled, which is the failure mode this whole file guards."""
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(8, 1000))
    monkeypatch.setattr(gate, "load_freeze", lambda: {
        "branch": "feature", "reviewable_files": 8,
        "reviewable_lines": 1000 - (gate.MAX_GROWTH_LINES // 2)})
    monkeypatch.setattr(gate, "_git", lambda *a: "feature")
    assert gate.main([]) == 0


def test_a_freeze_from_ANOTHER_branch_does_not_gate_this_one(monkeypatch):
    monkeypatch.setattr(gate, "measure", lambda base, head="HEAD":
                        _measure(10, 900))
    monkeypatch.setattr(gate, "load_freeze", lambda: {
        "branch": "some-other-branch", "reviewable_files": 1,
        "reviewable_lines": 1})
    monkeypatch.setattr(gate, "_git", lambda *a: "feature")
    assert gate.main([]) == 0   # size limits still apply below the ceiling


def test_a_corrupt_freeze_record_REFUSES_rather_than_reading_as_absent(tmp_path,
                                                                      monkeypatch):
    """An unreadable scope record silently disabling the scope rule is the
    failure-reads-as-empty class applied to the gate itself."""
    bad = tmp_path / "SCOPE_FREEZE.json"
    bad.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(gate, "FREEZE", bad)
    with pytest.raises(SystemExit, match="not valid JSON"):
        gate.load_freeze()


def test_generated_artifacts_do_not_count_against_the_reviewer(monkeypatch):
    """A reviewer does not read a generated target list line by line. Counting
    it like logic would make the gate fire on noise and get it switched off."""
    numstat = ("10\t0\ttools/real_code.py\n"
               "9000\t0\tsources/capcog_venue_targets.json\n")
    monkeypatch.setattr(gate, "_git",
                        lambda *a: numstat if a[0] == "diff" else "sha")
    m = gate.measure("base")
    assert m["reviewable_lines"] == 10
    assert m["reviewable_files"] == 1


def test_the_gate_is_wired_into_validate():
    """A gate that no pipeline runs is the prose it replaced."""
    v = (REPO / "tools" / "validate").read_text(encoding="utf-8")
    assert "change_set_gate" in v, "gate exists but nothing executes it"


def test_the_canon_document_exists_and_cites_its_evidence():
    doc = (REPO / "docs" / "skills" / "change_set_discipline.md"
           ).read_text(encoding="utf-8")
    for anchor in ("24 lines", "400", "dora.dev", "SCOPE FREEZE",
                   "one reversible decision"):
        assert anchor.lower() in doc.lower(), anchor
