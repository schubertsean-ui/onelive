"""Tests for tools/kaizen_trends.py — the mechanical Kaizen trend meter.

The meter's job (founder direction 2026-07-18): trends are COMPUTED, never
asserted. These tests cover the parser, the class-family alarm (the mechanized
repeat-class rule the evaluator enforced by judgment on PR #35 r2), the
addressed-marker logic, escape detection, and a smoke run against the real
ledger.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.kaizen_trends import (
    build_report,
    class_counts,
    family_addressed,
    family_groups,
    m1_direction,
    parse_pr_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "kaizen_trends.py"
REAL_LEDGER = REPO_ROOT / "docs" / "metrics" / "KAIZEN_LEDGER.md"

FAKE_LEDGER = """
# KAIZEN LEDGER (fixture)

## PR rows

| Date | PR | M1 rounds | M2 catches (gate: class × n) | M4 gate-gaps closed | M5 est. cost | Notes |
|---|---|---|---|---|---|---|
| 2026-07-01 | #1 | 5 | evaluator: empty-env ×1, silent-truncation ×1 | — | ~5 calls | |
| 2026-07-02 | #2 | 4 | CI: empty-env ×1; evaluator: coverage-gap ×2 | coverage floor added | ~4 calls | |
| 2026-07-03 | #3 | 2 | evaluator: fail-open-empty-env ×2 | — | ~2 calls | |
| 2026-07-04 | #4 | 1 | founder(Red): missed-citation ×1 | addressed-thing fixed | ~1 call | |

## Other section (ignored by the parser)

| 2026-07-05 | not-a-pr-row | x | fake ×9 | | | |
"""


def test_parser_reads_only_pr_rows():
    rows = parse_pr_rows(FAKE_LEDGER)
    assert len(rows) == 4
    assert rows[0]["pr"] == "#1"
    assert all("fake" not in r["m2"] for r in rows)


def test_class_counts_sum_across_rows():
    counts = class_counts(parse_pr_rows(FAKE_LEDGER))
    assert counts["empty-env"] == 2
    assert counts["fail-open-empty-env"] == 2
    assert counts["coverage-gap"] == 2


def test_containment_families_group_related_tokens():
    groups = family_groups(["empty-env", "fail-open-empty-env", "coverage-gap"])
    fams = [sorted(g) for g in groups]
    assert ["empty-env", "fail-open-empty-env"] in fams
    assert ["coverage-gap"] in fams


def test_unaddressed_family_over_threshold_raises_finding():
    # empty-env family totals 4 with no M4 marker naming it → alarm.
    _, findings = build_report(FAKE_LEDGER)
    assert any("empty-env" in f and "REPEAT-CLASS ALARM" in f for f in findings)


def test_family_with_m4_marker_is_addressed():
    rows = parse_pr_rows(FAKE_LEDGER)
    assert family_addressed({"addressed-thing"}, rows)
    assert not family_addressed({"empty-env", "fail-open-empty-env"}, rows)


def test_m1_direction_falling_is_improving():
    assert "FALLING" in m1_direction([5, 4, 2, 1])
    assert "RISING" in m1_direction([1, 2, 4, 5])
    assert m1_direction([3]) == "insufficient data"


def test_escape_token_is_a_hard_finding():
    ledger = FAKE_LEDGER + "\n| 2026-07-06 | #5 | 1 | M3-ESCAPE prod-bad-fact ×1 | — | — | escape |\n"
    _, findings = build_report(ledger)
    assert any("M3 ESCAPES" in f for f in findings)


def test_report_contains_the_curves():
    report, _ = build_report(FAKE_LEDGER)
    for needle in (
        "m3_escapes: 0",
        "m1_rounds_to_green",
        "founder_red_catches: 1",
        "catches_per_gate",
        "repeat_class_alarms",
    ):
        assert needle in report


def test_cli_missing_ledger_fails_closed():
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--ledger", "docs/NO_SUCH_LEDGER.md"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert proc.returncode == 2
    assert "cannot read" in proc.stderr


def test_real_ledger_parses_and_has_zero_escapes():
    # Smoke against the live ledger: it must parse (rows exist) and record
    # zero M3 escapes — if this fails on escapes, that is the alarm working.
    text = REAL_LEDGER.read_text(encoding="utf-8")
    report, findings = build_report(text)
    assert "ledger_rows:" in report
    assert "m3_escapes: 0" in report
    assert not any("M3 ESCAPES" in f for f in findings)
