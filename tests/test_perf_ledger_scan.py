"""Tests for tools/perf_ledger_scan.py — the mechanical arm of KAIZEN §M9.

Pins the structural discipline: a PENDING prediction must be complete before
it ships; a MEASURED row must carry a real baseline, actual, delta, and a
non-PENDING verdict; a missing/unparseable M9 section fails loud (exit 2).
The live ledger must always pass.
"""
import pathlib

import pytest

from tools import perf_ledger_scan as pls

_HEADER = (
    "| ID | Change | Metric (unit) | Baseline | Expected (%Δ) | Basis "
    "| Trigger | Actual (%Δ) | Delta | Verdict | Status |"
)
_SEP = "|---|---|---|---|---|---|---|---|---|---|---|"

_GOOD_PENDING = (
    "| EP-9 | caching | $/call | PENDING (measured pre-merge) | −45% "
    "| console + cache 0.1x | 24h traffic | PENDING | PENDING | PENDING "
    "| PENDING-MEASUREMENT |"
)
_GOOD_MEASURED = (
    "| EP-8 | batch | $/job | 1.00 | −50% | batch 50% off | first job "
    "| 0.52 | +2pp | MET | MEASURED |"
)


def _section(*rows: str) -> str:
    return "## M9 x\n\nintro\n\n" + "\n".join((_HEADER, _SEP, *rows)) + "\n"


def test_complete_rows_pass():
    assert pls.scan(_section(_GOOD_PENDING, _GOOD_MEASURED)) == []


def test_pending_missing_expected_flags():
    bad = (
        "| EP-1 | x | $/call | PENDING | — | some basis | 24h | PENDING "
        "| PENDING | PENDING | PENDING-MEASUREMENT |"
    )
    violations = pls.scan(_section(bad))
    assert any("expected is empty" in v.lower() for v in violations)


def test_pending_missing_basis_flags():
    bad = (
        "| EP-2 | x | $/call | PENDING | −45% | — | 24h | PENDING "
        "| PENDING | PENDING | PENDING-MEASUREMENT |"
    )
    assert any("basis is empty" in v.lower() for v in pls.scan(_section(bad)))


def test_measured_with_pending_baseline_flags():
    bad = (
        "| EP-3 | x | $/call | PENDING (not yet) | −45% | b | t | 0.55 "
        "| +0pp | MET | MEASURED |"
    )
    assert any("baseline is still" in v.lower() for v in pls.scan(_section(bad)))


def test_measured_with_empty_actual_flags():
    bad = (
        "| EP-4 | x | $/call | 1.00 | −45% | b | t | — | — | MET | MEASURED |"
    )
    violations = pls.scan(_section(bad))
    assert any("actual is not filled" in v.lower() for v in violations)


def test_measured_with_bad_verdict_flags():
    bad = (
        "| EP-5 | x | $/call | 1.00 | −45% | b | t | 0.55 | +0pp | GREAT "
        "| MEASURED |"
    )
    assert any("verdict" in v.lower() for v in pls.scan(_section(bad)))


def test_unknown_status_flags():
    bad = (
        "| EP-6 | x | $/call | 1.00 | −45% | b | t | 0.55 | +0pp | MET | DONE |"
    )
    assert any("status" in v.lower() for v in pls.scan(_section(bad)))


def test_missing_section_is_hard_failure():
    with pytest.raises(pls.LedgerError):
        pls.scan("# no m9 here\n\nsome text\n")


def test_missing_column_is_hard_failure():
    header = "| ID | Change | Metric | Status |"
    sep = "|---|---|---|---|"
    row = "| EP-7 | x | y | MEASURED |"
    text = "## M9\n\n" + "\n".join((header, sep, row)) + "\n"
    with pytest.raises(pls.LedgerError):
        pls.scan(text)


def test_live_ledger_passes():
    ledger = pathlib.Path(pls.LEDGER)
    assert ledger.exists(), "the real ledger must exist"
    assert pls.scan(ledger.read_text(encoding="utf-8")) == []
