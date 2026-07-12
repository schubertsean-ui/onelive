"""Hermetic tests for the field-kind-aware extraction scorer.

Each new behavior is proven in BOTH directions: it fires when it should, and it
does NOT false-positive on clean/equivalent input. A sabotage test proves the
scorer can report a discrepancy (it is not vacuously green).
"""
import importlib

import pytest

from ai.eval_harness import (
    DEFAULT_FIELD_KINDS,
    FieldKind,
    aggregate,
    score_extraction,
)


# --- TIME --------------------------------------------------------------------
@pytest.mark.parametrize("pred,exp", [
    ("8pm", "20:00"),
    ("8 pm", "20:00"),
    ("8:00 PM", "20:00"),
    ("8:00pm", "8pm"),
    ("noon", "12:00"),
    ("midnight", "00:00"),
    ("7:30pm", "19:30"),
])
def test_time_equivalent_spellings_are_true_positive(pred, exp):
    s = score_extraction({"start_time": pred}, {"start_time": exp})
    assert s.true_positives == 1
    assert s.false_positives == 0 and s.false_negatives == 0
    assert s.hallucination_rate == 0.0
    assert not s.unparsed_values


def test_time_wrong_value_is_fp_and_fn():
    s = score_extraction({"start_time": "8pm"}, {"start_time": "9pm"})
    assert s.true_positives == 0
    assert s.false_positives == 1 and s.false_negatives == 1
    assert "start_time" in s.mismatched_fields
    assert s.hallucination_rate == 1.0


def test_time_unparseable_is_recorded_and_falls_back_no_crash():
    # Garbage predicted time vs a real one: recorded as unparsed, compared as
    # text (so NOT silently equal), and does not raise.
    s = score_extraction({"start_time": "whenever-ish"}, {"start_time": "8pm"})
    assert ("start_time", "whenever-ish") in s.unparsed_values
    assert s.true_positives == 0  # text fallback: "whenever-ish" != "8pm"
    assert s.false_positives == 1 and s.false_negatives == 1


def test_time_identical_unparseable_text_still_matches_via_fallback():
    s = score_extraction({"start_time": "next friday"},
                         {"start_time": "Next Friday"})
    assert s.true_positives == 1        # text fallback treats them equal
    assert ("start_time", "next friday") in s.unparsed_values  # still surfaced


# --- DATE --------------------------------------------------------------------
@pytest.mark.parametrize("pred,exp", [
    ("2026-03-14", "March 14, 2026"),
    ("3/14/2026", "2026-03-14"),
    ("Mar 14, 2026", "2026-03-14"),
])
def test_date_equivalent_forms_match(pred, exp):
    s = score_extraction({"date": pred}, {"date": exp})
    assert s.true_positives == 1 and s.false_positives == 0


def test_date_wrong_value_fails():
    s = score_extraction({"date": "2026-03-14"}, {"date": "2026-03-15"})
    assert s.false_positives == 1 and s.false_negatives == 1
    assert "date" in s.mismatched_fields


def test_date_missing_year_compares_month_day():
    # No year on prediction -> compare month-day only, so it matches.
    s = score_extraction({"date": "Mar 14"}, {"date": "2026-03-14"})
    assert s.true_positives == 1
    # But a different month-day still fails.
    s2 = score_extraction({"date": "Mar 15"}, {"date": "2026-03-14"})
    assert s2.false_positives == 1 and s2.false_negatives == 1


def test_date_unparseable_recorded_and_falls_back():
    s = score_extraction({"date": "sometime soon"}, {"date": "2026-03-14"})
    assert ("date", "sometime soon") in s.unparsed_values
    assert s.true_positives == 0


# --- VENUE -------------------------------------------------------------------
@pytest.mark.parametrize("pred,exp", [
    ("The Mohawk", "Mohawk"),
    ("Austin, TX", "Austin"),
    ("the  mohawk!", "Mohawk"),
])
def test_venue_lenient_matches(pred, exp):
    s = score_extraction({"venue": pred}, {"venue": exp})
    assert s.true_positives == 1 and s.false_positives == 0


def test_venue_different_venue_fails():
    s = score_extraction({"venue": "The Mohawk"}, {"venue": "Emo's"})
    assert s.false_positives == 1 and s.false_negatives == 1


def test_venue_alias_is_known_limit_and_flagged():
    # Documented KNOWN LIMIT: shallow canonicalization does not unify true
    # aliases, so this is (correctly, for now) a mismatch.
    s = score_extraction({"venue": "Emo's"}, {"venue": "Emo's East"})
    assert s.true_positives == 0 and s.false_positives == 1


# --- LIST_TEXT partial credit ------------------------------------------------
def test_list_partial_credit_three_of_four():
    expected = {"lineup": ["Alpha", "Bravo", "Charlie", "Delta"]}
    predicted = {"lineup": ["alpha", "bravo", "charlie"]}  # missing Delta
    s = score_extraction(predicted, expected)
    assert s.true_positives == 3
    assert s.false_negatives == 1
    assert s.false_positives == 0
    assert s.by_field["lineup"] == "partial"
    # NOT a total field failure:
    assert s.recall == pytest.approx(0.75)


def test_list_extra_act_is_fp_and_hallucinated():
    expected = {"lineup": ["Alpha", "Bravo"]}
    predicted = {"lineup": ["Alpha", "Bravo", "Ghost Act"]}
    s = score_extraction(predicted, expected)
    assert s.true_positives == 2
    assert s.false_positives == 1
    assert "lineup" in s.hallucinated_fields
    assert s.hallucination_rate == pytest.approx(1 / 3)


def test_list_perfect_match_no_hallucination():
    d = {"artists": ["A", "B", "C"]}
    s = score_extraction(d, d)
    assert s.true_positives == 3
    assert s.false_positives == 0 and s.false_negatives == 0
    assert s.by_field["artists"] == "tp"


# --- diagnostics -------------------------------------------------------------
def test_by_field_outcomes_map():
    s = score_extraction(
        {"title": "Show", "venue": "Ghost Venue"},
        {"title": "Show", "city": "Austin"},
    )
    assert s.by_field["title"] == "tp"
    assert s.by_field["venue"] == "fp"   # asserted, not in truth
    assert s.by_field["city"] == "fn"    # in truth, missed


def test_scalar_mismatch_labeled_distinctly_from_pure_fp():
    # Both present but different is NOT the same as a pure hallucination (truth
    # absent). The per-field map must preserve the distinction, and the mismatch
    # must still count as BOTH a false positive and a false negative.
    s = score_extraction({"title": "Wrong Title"}, {"title": "Right Title"})
    assert s.by_field["title"] == "mismatch"
    assert s.false_positives == 1
    assert s.false_negatives == 1
    assert "title" in s.mismatched_fields
    assert "title" in s.hallucinated_fields
    # And a genuine pure-hallucination field is still labeled "fp", not "mismatch":
    s2 = score_extraction({"venue": "Ghost"}, {"venue": None})
    assert s2.by_field["venue"] == "fp"


# --- aggregate: statistical rigor --------------------------------------------
def _corpus():
    return [
        score_extraction({"start_time": "8pm"}, {"start_time": "20:00"}),
        score_extraction({"venue": "Ghost"}, {"venue": None}),
        score_extraction({"title": "A"}, {"title": "A", "city": "Austin"}),
        score_extraction({"date": "junk"}, {"date": "2026-03-14"}),
    ]


def test_aggregate_returns_confidence_intervals():
    agg = aggregate(_corpus())
    for key in ("f1_ci95", "hallucination_rate_ci95"):
        lo, hi = agg[key]
        assert 0.0 <= lo <= hi <= 1.0


def test_aggregate_deterministic_same_seed():
    a = aggregate(_corpus(), seed=777)
    b = aggregate(_corpus(), seed=777)
    assert a == b
    assert a["f1_ci95"] == b["f1_ci95"]
    assert a["hallucination_rate_ci95"] == b["hallucination_rate_ci95"]


def test_aggregate_n_lt_2_is_safe_point_estimate():
    single = [score_extraction({"title": "A"}, {"title": "A"})]
    agg = aggregate(single)
    assert agg["n_examples"] == 1
    assert agg["f1_ci95"] == [agg["f1"], agg["f1"]]
    assert agg["hallucination_rate_ci95"] == [agg["hallucination_rate"],
                                              agg["hallucination_rate"]]
    assert aggregate([]) ["n_examples"] == 0  # empty corpus does not crash


def test_aggregate_surfaces_n_unparsed():
    agg = aggregate(_corpus())
    assert agg["n_unparsed"] >= 1  # the "junk" date fell back and was recorded


# --- Sunset Law: evaluate_extraction retired ---------------------------------
def test_evaluate_extraction_is_retired():
    mod = importlib.import_module("ai.eval_harness")
    assert not hasattr(mod, "evaluate_extraction"), \
        "evaluate_extraction must be retired (Sunset Law); use accuracy/f1"


def test_accuracy_property_is_the_scalar_replacement():
    assert score_extraction({"a": 1}, {"a": 1}).accuracy == 1.0
    assert score_extraction({"a": 1}, {"a": 2}).accuracy == 0.0
    assert score_extraction({}, {}).accuracy == 1.0


# --- sabotage: prove the scorer can fail --------------------------------------
def test_sabotage_known_wrong_expected_is_reported():
    # Feed a KNOWN-wrong expected value; a real scorer must report the
    # discrepancy. If this ever passes as a match, the scorer is vacuous.
    s = score_extraction(
        {"venue": "The Mohawk", "start_time": "8pm"},
        {"venue": "Completely Different Hall", "start_time": "3am"},
    )
    assert s.true_positives == 0
    assert s.false_positives == 2 and s.false_negatives == 2
    assert set(s.mismatched_fields) == {"venue", "start_time"}
    assert s.f1 == 0.0


# --- schema wiring -----------------------------------------------------------
def test_default_field_kinds_cover_core_fields():
    assert DEFAULT_FIELD_KINDS["start_time"] is FieldKind.TIME
    assert DEFAULT_FIELD_KINDS["date"] is FieldKind.DATE
    assert DEFAULT_FIELD_KINDS["venue"] is FieldKind.VENUE
    assert DEFAULT_FIELD_KINDS["lineup"] is FieldKind.LIST_TEXT


def test_unknown_field_defaults_to_text():
    # A field not in the map compares as plain text (case-insensitive).
    s = score_extraction({"title": "Big  SHOW"}, {"title": "big show"})
    # whitespace differs -> text norm only strips ends/case, so this differs;
    # but exact case-folded equal matches:
    s2 = score_extraction({"title": "Big Show"}, {"title": "big show"})
    assert s2.true_positives == 1
    assert score_extraction({"custom": "x"}, {"custom": "x"}).true_positives == 1
    assert s.false_positives == 1  # internal double-space is a genuine diff
