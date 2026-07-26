"""M9 reviewer scorecard: mechanical ledger derivation, fail-loud parsing."""
import importlib.util
import pathlib
import sys

import pytest

_TOOL = pathlib.Path(__file__).resolve().parent.parent / "tools" / "reviewer_scorecard.py"
_spec = importlib.util.spec_from_file_location("reviewer_scorecard", _TOOL)
rs = importlib.util.module_from_spec(_spec)
sys.modules["reviewer_scorecard"] = rs
_spec.loader.exec_module(rs)

LEDGER = """| Date | PR | M1 | M2 catches | fix | cost | notes |
|---|---|---|---|---|---|---|
| 2026-07-25 | #65 (in flight: r3) | 3 | evaluator r3: caller-suppliable-custody-inputs ×5 | fix | c | n |
| 2026-07-25 | #65 (in flight: r11) | 11 | evaluator r11: caller-suppliable-custody-inputs ×1 clock | fix | c | n |
| 2026-07-25 | #65 (MERGED abc123) | 15 | full chain | fix | c | n |
| 2026-07-25 | #70 (in flight: r1) | 1 | evaluator r1: fresh-class ×1 | fix | c | n |
"""


def test_arc_parsing_and_metrics():
    arcs, merged = rs.parse_arcs(LEDGER)
    assert merged[65] == 15
    card = rs.scorecard(arcs, merged)
    # #65: caller-suppliable-custody-inputs appears in r3 AND r11 -> 1 sibling miss.
    assert card[65]["sibling_misses"] == 1
    assert card[65]["distinct_classes"] == 1
    # #71 r3: #65 has NO r1 row, so round-1 recall is unmeasurable —
    # explicitly None, never the flattering "earliest recorded" reading.
    assert card[65]["round1_recall"] is None
    # #70 does have an r1 row, and its only class surfaced there.
    assert card[70]["round1_recall"] == 1.0


def test_no_classed_findings_is_explicit_not_a_division_error():
    arcs, merged = rs.parse_arcs(
        "| 2026-07-25 |#9 (in flight: r1)|1| evaluator r1: a prose finding, no class token |f|c|n|\n"
    )
    card = rs.scorecard(arcs, merged)
    assert card[9]["round1_recall"] is None  # guarded, no ZeroDivision


def test_real_ledger_parses_clean():
    # The shipped ledger must parse without raising (second consumer of the
    # no-raw-pipes rule).
    text = (pathlib.Path(rs.REPO_ROOT) / "docs" / "metrics" / "KAIZEN_LEDGER.md").read_text()
    arcs, merged = rs.parse_arcs(text)
    assert arcs  # arcs were found
