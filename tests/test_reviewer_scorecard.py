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


def _real_ledger():
    return (pathlib.Path(rs.REPO_ROOT) / "docs" / "metrics"
            / "KAIZEN_LEDGER.md").read_text()


def test_real_ledger_parses_clean():
    # The shipped ledger must parse without raising (second consumer of the
    # no-raw-pipes rule).
    arcs, merged = rs.parse_arcs(_real_ledger())
    assert arcs  # arcs were found


def test_real_ledger_agrees_with_KNOWN_merge_facts():
    # #71 r10 BLOCKER: "it parses" is not "it is right". The scorecard
    # reported PR #67 as in flight while the same diff's handoff called it
    # merged — the merged row was simply missing, and a non-crash test
    # could never say so. These arcs are merged on master (verify with
    # `git log --grep "(#NN)"`), so the scorecard must report their real
    # rounds-to-green. A future close that forgets its ledger row fails
    # HERE rather than surfacing as a confident false metric.
    _, merged = rs.parse_arcs(_real_ledger())
    for pr, m1 in ((65, 15), (67, 9), (69, 3), (70, 1)):
        assert merged.get(pr) == m1, (
            f"PR #{pr} is merged on master but the ledger reports "
            f"M1={merged.get(pr)!r}, expected {m1}")


def test_an_arc_with_no_merged_row_is_named_not_guessed():
    # The same blocker's other half: an arc the ledger has not closed must
    # NOT be reported as "in flight", which is a claim about GitHub state
    # this tool cannot see. It says what it knows.
    arcs, merged = rs.parse_arcs(
        "| 2026-07-25 | #98 (in flight: r1) | 1 | evaluator r1: some-class ×1 "
        "| fix | cost | note |\n")
    assert 98 in arcs and 98 not in merged
    card = rs.scorecard(arcs, merged)
    assert card[98]["m1_merged"] is None


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


def test_malformed_MERGED_row_with_extra_pipes_fails_loud():
    # #71 r11 BLOCKER: the exact-schema check covered round rows only, so
    # a merged row with raw pipes shifted which cell is read as M1 — the
    # headline metric — and stayed green. One rule, both row kinds.
    bad = ("| 2026-07-25 | #96 (MERGED abc1234 — a thing) | 9 | full | chain "
           "| with | extra | pipes |\n")
    with pytest.raises(ValueError, match="malformed ledger merged row"):
        rs.parse_arcs(bad)


def test_wellformed_MERGED_row_still_parses():
    good = ("| 2026-07-25 | #96 (MERGED abc1234 — a thing) | 9 | findings "
            "| fix | cost | note |\n")
    _, merged = rs.parse_arcs(good)
    assert merged == {96: 9}
