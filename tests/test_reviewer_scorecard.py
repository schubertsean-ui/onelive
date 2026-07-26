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


def test_malformed_row_with_extra_pipes_fails_loud():
    # #71 r4 nit: the r3 exact-schema fix must be red-tested so it cannot
    # regress unnoticed. Extra raw pipes shift which cell is read as M2.
    bad = ("| 2026-07-25 | #97 (in flight: r1) | 1 | evaluator r1: a-class ×1 "
           "| fix | with | extra | pipes |\n")
    with pytest.raises(ValueError, match="malformed ledger round row"):
        rs.parse_arcs(bad)


def test_uncounted_and_single_word_tokens_are_not_scorecard_inputs():
    # The ×n count is mandatory, and legacy single-word tokens are out of
    # M9's scope by documented design (#71 r4 nit).
    ledger = ("| 2026-07-25 | #96 (in flight: r1) | 1 | evaluator r1: mentions "
              "some-class without a count and contradictions ×2 | fix | c | n |\n")
    arcs, _ = rs.parse_arcs(ledger)
    assert arcs[96][1] == set()


def test_round1_recall_requires_an_actual_round_one():
    ledger = ("| 2026-07-25 | #95 (in flight: r2) | 2 | evaluator r2: alpha-class ×1 | f | c | n |\n"
              "| 2026-07-25 | #95 (in flight: r3) | 3 | evaluator r3: beta-class ×1 | f | c | n |\n")
    arcs, merged = rs.parse_arcs(ledger)
    assert rs.scorecard(arcs, merged)[95]["round1_recall"] is None
    with_r1 = ledger + ("| 2026-07-25 | #95 (in flight: r1) | 1 | evaluator r1: alpha-class ×1 | f | c | n |\n")
    arcs, merged = rs.parse_arcs(with_r1)
    assert rs.scorecard(arcs, merged)[95]["round1_recall"] == 0.5
