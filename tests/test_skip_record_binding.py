"""Tests for tools/skip_record_binding.py — the mechanical skip→Record gate.

Covers the class fixes ledgered 2026-07-18 (skip-report-missing-record-citation;
unverifiable-claim family #20/#27/#35): an environmental SKIP in tools/validate
must bind to an OPEN docs/RECORD.md row or the gate goes red. These tests can
actually fail: they assert both the binding success path and every refusal path
(no row, resolved row, unreadable register).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.skip_record_binding import find_open_record_row, parse_record_rows

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "skip_record_binding.py"
REAL_RECORD = REPO_ROOT / "docs" / "RECORD.md"

FAKE_RECORD = """
# RECORD — deferral register (test fixture)

| ID | Date | Deferred | Bar | Trigger | Status |
|---|---|---|---|---|---|
| R-101 | 2026-07-01 | `alpha_check` gate SKIPs in sandbox | §9.6 | preview URL exists | OPEN |
| R-102 | 2026-07-02 | `beta_check` threshold unratified | §11.2 | founder ratifies | RESOLVED (founder 2026-07-03) |
| R-103 | 2026-07-04 | unrelated row about nothing | §1 | never fires | OPEN |
"""


def test_open_row_binds():
    assert find_open_record_row("alpha_check", FAKE_RECORD) == "R-101"


def test_resolved_row_never_binds():
    # Resolved debt cannot excuse a live skip.
    assert find_open_record_row("beta_check", FAKE_RECORD) is None


def test_unnamed_check_never_binds():
    assert find_open_record_row("gamma_check", FAKE_RECORD) is None


def test_empty_check_name_never_binds():
    # A blank name must not substring-match every row.
    assert find_open_record_row("", FAKE_RECORD) is None
    assert find_open_record_row("   ", FAKE_RECORD) is None


def test_parse_extracts_ids_and_statuses():
    rows = parse_record_rows(FAKE_RECORD)
    ids = [r[0] for r in rows]
    assert ids == ["R-101", "R-102", "R-103"]
    statuses = {r[0]: r[2] for r in rows}
    assert statuses["R-101"] == "OPEN"
    assert statuses["R-102"].startswith("RESOLVED")


def test_real_register_binds_visual_regression_to_r002():
    # Integration against the live register: the standing R-002 row must
    # satisfy the binding for the visual_regression skip. If R-002 is ever
    # resolved (Step 9 baselines captured), this test flips to asserting
    # no binding — that flip is the desired loud signal to remove the skip.
    text = REAL_RECORD.read_text(encoding="utf-8")
    assert find_open_record_row("visual_regression", text) == "R-002"


def _run_cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *argv],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_cli_success_prints_row_id():
    proc = _run_cli("visual_regression")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "R-002"


def test_cli_unrecorded_skip_fails_loud():
    proc = _run_cli("definitely_not_a_recorded_check")
    assert proc.returncode == 1
    assert "unrecorded skip is a violation" in proc.stderr


def test_cli_missing_register_fails_closed():
    # An unreadable register must be exit 2 (loud), never a silent pass.
    proc = _run_cli("visual_regression", "--record", "docs/DOES_NOT_EXIST.md")
    assert proc.returncode == 2
    assert "cannot read" in proc.stderr
