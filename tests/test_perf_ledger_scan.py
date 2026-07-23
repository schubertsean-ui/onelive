"""Tests for tools/perf_ledger_scan.py — the mechanical arm of KAIZEN §M9.

Pins the structural discipline (a PENDING prediction is complete before it ships;
a MEASURED row carries a real baseline, actual, signed error, non-PENDING verdict)
AND the red-team hardening (a Band is required; MET is numeric — |signed error| ≤
Band). A missing/unparseable M9 section fails loud (exit 2). The live ledger must
always pass.
"""
import pathlib

import pytest

from tools import perf_ledger_scan as pls

# 12-column schema (2026-07-23 red-team hardening): Band + signed error added.
_HEADER = (
    "| ID | Change | Metric | Baseline | Expected | Basis | Trigger & method "
    "| Band | Actual | Signed error | Verdict | Status |"
)
_SEP = "|---|---|---|---|---|---|---|---|---|---|---|---|"

_GOOD_PENDING = (
    "| EP-9 | caching | ratio/call | PENDING (pre-merge) | −45% "
    "| console + cache 0.1x | 24h; actual=mean(1−billed/uncached) | ±10pp "
    "| PENDING | PENDING | PENDING | PENDING-MEASUREMENT |"
)
_GOOD_MEASURED = (
    "| EP-8 | batch | ratio/job | 1.00 | −50% | batch 50% off "
    "| first job; billed÷nonbatch−1 | ±5pp | −52% | −2pp | MET | MEASURED |"
)


def _section(*rows: str) -> str:
    return "## M9 x\n\nintro\n\n" + "\n".join((_HEADER, _SEP, *rows)) + "\n"


def test_complete_rows_pass():
    assert pls.scan(_section(_GOOD_PENDING, _GOOD_MEASURED)) == []


def test_pending_missing_expected_flags():
    bad = (
        "| EP-1 | x | r | PENDING | — | basis | 24h; method | ±10pp "
        "| PENDING | PENDING | PENDING | PENDING-MEASUREMENT |"
    )
    assert any("expected is empty" in v.lower() for v in pls.scan(_section(bad)))


def test_pending_missing_band_flags():
    bad = (
        "| EP-1b | x | r | PENDING | −45% | basis | 24h; method | — "
        "| PENDING | PENDING | PENDING | PENDING-MEASUREMENT |"
    )
    assert any("band is empty" in v.lower() for v in pls.scan(_section(bad)))


def test_pending_missing_basis_flags():
    bad = (
        "| EP-2 | x | r | PENDING | −45% | — | 24h; method | ±10pp "
        "| PENDING | PENDING | PENDING | PENDING-MEASUREMENT |"
    )
    assert any("basis is empty" in v.lower() for v in pls.scan(_section(bad)))


def test_measured_with_pending_baseline_flags():
    bad = (
        "| EP-3 | x | r | PENDING (not yet) | −45% | b | t; m | ±10pp "
        "| −46% | −1pp | MET | MEASURED |"
    )
    assert any("baseline is still" in v.lower() for v in pls.scan(_section(bad)))


def test_measured_with_empty_actual_flags():
    bad = (
        "| EP-4 | x | r | 1.00 | −45% | b | t; m | ±10pp | — | — | MET "
        "| MEASURED |"
    )
    assert any("actual is not filled" in v.lower() for v in pls.scan(_section(bad)))


def test_measured_with_bad_verdict_flags():
    bad = (
        "| EP-5 | x | r | 1.00 | −45% | b | t; m | ±10pp | −45% | 0pp | GREAT "
        "| MEASURED |"
    )
    assert any("verdict" in v.lower() for v in pls.scan(_section(bad)))


def test_met_outside_band_flags():
    # |signed error| 25pp exceeds the ±10pp band, so MET is a lie.
    bad = (
        "| EP-6 | x | r | 1.00 | −45% | b | t; m | ±10pp | −20% | +25pp | MET "
        "| MEASURED |"
    )
    assert any("exceeds the" in v.lower() for v in pls.scan(_section(bad)))


def test_within_band_but_not_met_flags():
    # |signed error| 2pp is within ±10pp, so the verdict must be MET, not UNDER.
    bad = (
        "| EP-7 | x | r | 1.00 | −45% | b | t; m | ±10pp | −43% | +2pp | UNDER "
        "| MEASURED |"
    )
    assert any("must be met" in v.lower() for v in pls.scan(_section(bad)))


def test_under_outside_band_passes():
    # A genuine miss: 25pp worse than expected, correctly verdicted UNDER.
    ok = (
        "| EP-7b | x | r | 1.00 | −45% | b | t; m | ±10pp | −20% | +25pp | UNDER "
        "| MEASURED |"
    )
    assert pls.scan(_section(ok)) == []


def test_unknown_status_flags():
    bad = (
        "| EP-8x | x | r | 1.00 | −45% | b | t; m | ±10pp | −45% | 0pp | MET "
        "| DONE |"
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


def test_num_parses_signed_and_marked_values():
    assert pls._num("+2pp") == 2.0
    assert pls._num("−3pp") == -3.0
    assert pls._num("±10pp") == 10.0
    assert pls._num("−45%") == -45.0
    assert pls._num("PENDING") is None


def test_live_ledger_passes():
    ledger = pathlib.Path(pls.LEDGER)
    assert ledger.exists(), "the real ledger must exist"
    assert pls.scan(ledger.read_text(encoding="utf-8")) == []
