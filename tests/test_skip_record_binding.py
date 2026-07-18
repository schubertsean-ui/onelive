"""Tests for the skip→Record gate: tools/skip_record_binding.py + the
sourced binding loop tools/validate_bind_skips.sh.

Covers the class fixes ledgered 2026-07-18 (skip-report-missing-record-citation;
unverifiable-claim family #20/#27/#35) and the evaluator r3 fail-open findings:
binding requires the STRUCTURED backticked `check_name` marker (incidental
prose mentions never bind), and quick-mode exemption is keyed off the QSKIP
status (note text containing "--quick" exempts nothing). These tests can
actually fail: success path plus every refusal/bypass path is asserted.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.skip_record_binding import find_open_record_row, parse_record_rows

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "skip_record_binding.py"
BIND_SH = REPO_ROOT / "tools" / "validate_bind_skips.sh"
REAL_RECORD = REPO_ROOT / "docs" / "RECORD.md"

FAKE_RECORD = """
# RECORD — deferral register (test fixture)

| ID | Date | Deferred | Bar | Trigger | Status |
|---|---|---|---|---|---|
| R-101 | 2026-07-01 | `alpha_check` gate SKIPs in sandbox | §9.6 | preview URL exists | OPEN |
| R-102 | 2026-07-02 | `beta_check` threshold unratified | §11.2 | founder ratifies | RESOLVED (founder 2026-07-03) |
| R-103 | 2026-07-04 | prose row that mentions gamma_check without a code marker | §1 | never fires | OPEN |
"""


def test_open_row_with_backticked_marker_binds():
    assert find_open_record_row("alpha_check", FAKE_RECORD) == "R-101"


def test_resolved_row_never_binds():
    # Resolved debt cannot excuse a live skip.
    assert find_open_record_row("beta_check", FAKE_RECORD) is None


def test_incidental_prose_mention_never_binds():
    # Evaluator r3: a raw substring hit on an unrelated row must not satisfy
    # the binding — only the structured backticked token does.
    assert find_open_record_row("gamma_check", FAKE_RECORD) is None


def test_unnamed_check_never_binds():
    assert find_open_record_row("delta_check", FAKE_RECORD) is None


def test_empty_check_name_never_binds():
    assert find_open_record_row("", FAKE_RECORD) is None
    assert find_open_record_row("   ", FAKE_RECORD) is None


def test_parse_extracts_ids_and_statuses():
    rows = parse_record_rows(FAKE_RECORD)
    assert [r[0] for r in rows] == ["R-101", "R-102", "R-103"]
    statuses = {r[0]: r[2] for r in rows}
    assert statuses["R-101"] == "OPEN"
    assert statuses["R-102"].startswith("RESOLVED")


def test_real_register_binding_is_consistent_for_visual_regression():
    # Integration against the live register, without pinning live debt
    # forever (evaluator r4 nit): expectation is derived by an independent
    # line scan, so the test keeps passing when R-002 is eventually resolved
    # — the semantics themselves are pinned by the fixture tests above.
    text = REAL_RECORD.read_text(encoding="utf-8")
    expected = None
    for line in text.splitlines():
        if line.startswith("| R-") and "`visual_regression`" in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[-1].upper().startswith("OPEN"):
                expected = cells[0]
                break
    assert find_open_record_row("visual_regression", text) == expected


def _run_cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *argv],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def test_cli_prints_row_id_when_register_has_one():
    proc = _run_cli("visual_regression")
    if find_open_record_row(
        "visual_regression", REAL_RECORD.read_text(encoding="utf-8")
    ):
        assert proc.returncode == 0
        assert proc.stdout.strip().startswith("R-")
    else:
        assert proc.returncode == 1


def test_cli_unrecorded_skip_fails_loud():
    proc = _run_cli("definitely_not_a_recorded_check")
    assert proc.returncode == 1
    assert "unrecorded skip is a violation" in proc.stderr


def test_cli_missing_register_fails_closed():
    proc = _run_cli("visual_regression", "--record", "docs/DOES_NOT_EXIST.md")
    assert proc.returncode == 2
    assert "cannot read" in proc.stderr


# ---- The sourced binding loop itself (tools/validate_bind_skips.sh) ---------


def _run_bind_loop(*result_rows: str) -> tuple[str, str]:
    """Source the real loop with the given RESULTS rows; return its outcome.

    Emits "ANY_FAIL=<n>" then one "ROW:<status>|<name>|<note>" line per bound
    row, so assertions read the loop's actual behavior, not a reimplementation.
    """
    rows_bash = " ".join(
        '"' + row.replace("\t", r"\t") + '"' for row in result_rows
    )
    script = f"""
    set -u
    PY={sys.executable}
    REPO_ROOT={REPO_ROOT}
    ANY_FAIL=0
    RESULTS=({rows_bash})
    RESULTS=("${{RESULTS[@]//\\\\t/$'\\t'}}")
    source {BIND_SH}
    bind_skips
    echo "ANY_FAIL=$ANY_FAIL"
    for row in "${{BOUND_RESULTS[@]}}"; do
      IFS=$'\\t' read -r s n t <<< "$row"
      echo "ROW:$s|$n|$t"
    done
    """
    proc = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, cwd=REPO_ROOT
    )
    return proc.stdout, proc.stderr


def test_loop_binds_recorded_environmental_skip():
    out, _ = _run_bind_loop("SKIP\tvisual_regression\tapp not running")
    assert "ANY_FAIL=0" in out
    assert "ROW:SKIP|visual_regression|app not running — R-002" in out


def test_loop_fails_unrecorded_environmental_skip():
    out, _ = _run_bind_loop("SKIP\tfake_unrecorded_check\tenv absent")
    assert "ANY_FAIL=1" in out
    assert "ROW:FAIL|fake_unrecorded_check|" in out


def test_loop_note_mentioning_quick_does_not_exempt():
    # Evaluator r3 bypass regression: an environmental SKIP whose free-text
    # note contains "--quick" must still bind or fail — exemption is by the
    # QSKIP status only, never by note content.
    out, _ = _run_bind_loop("SKIP\tfake_unrecorded_check\tskipped like --quick")
    assert "ANY_FAIL=1" in out
    assert "ROW:FAIL|fake_unrecorded_check|" in out


def test_loop_qskip_status_is_exempt_and_displayed_as_skip():
    # QSKIP (structured quick-mode state) passes through without binding —
    # even for a name with no Record row — and renders as SKIP in the summary.
    out, _ = _run_bind_loop("QSKIP\tperf benchmarks\t--quick (rerun before close)")
    assert "ANY_FAIL=0" in out
    assert "ROW:SKIP|perf benchmarks|--quick (rerun before close)" in out


def test_loop_pass_and_fail_rows_flow_through_untouched():
    out, _ = _run_bind_loop("PASS\tlint\t", "FAIL\tpytest (full suite)\t")
    assert "ANY_FAIL=0" in out  # pre-existing FAIL rows don't re-set the flag here
    assert "ROW:PASS|lint|" in out
    assert "ROW:FAIL|pytest (full suite)|" in out
