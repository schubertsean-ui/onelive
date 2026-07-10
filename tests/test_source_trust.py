"""Tests for the source-trust scoring substrate (three mechanisms):

1. Source-credibility weighting: per-type defaults, per-source override, and the
   aggregated-weight -> 4-state confidence mapping.
2. Source Priority Ranking Model: score across all four bands, scale
   normalization, and versioned coefficients.
3. Reputation decay/growth: multiplier behaviour incl. floor/cap edge cases and
   the pluggable-function contract.

All pure-logic (no DB) — they exercise the config-driven modules against the
default sources/trust_config.json.
"""
import pytest

from worker import trust_config
from worker.source_credibility import (
    type_default_weight,
    effective_weight,
    aggregate_weight,
    derive_confidence_from_weight,
)
from worker.source_rank import (
    SourceMetrics,
    compute_priority_score,
    priority_band,
    rank_source,
)
from worker.source_reliability import (
    TRUE_POSITIVE,
    FALSE_POSITIVE,
    decay_growth_v1,
    get_decay_growth,
    apply_reputation_update,
    DECAY_GROWTH_FUNCTIONS,
)
from worker.confidence import CONFIDENCE_STATES, is_valid_confidence


# ==========================================================================
# Mechanism 1 — source-credibility weighting
# ==========================================================================

@pytest.mark.parametrize("stype,expected", [
    ("venue_calendar", 1.0),
    ("venue_claim", 1.0),
    ("artist_claim", 1.0),
    ("ticketing", 0.9),
    ("community_calendar", 0.7),
    ("artist_website", 0.6),
    ("linktree", 0.6),
    ("soundcloud", 0.6),
    ("bandcamp", 0.6),
    ("instagram", 0.4),
    ("facebook", 0.4),
    ("anonymous", 0.2),
])
def test_type_default_weights_match_spec(stype, expected):
    assert type_default_weight(stype) == expected


def test_unknown_type_falls_back_to_default_weight():
    # Unknown types degrade to the configurable anonymous baseline, not an error.
    assert type_default_weight("some_new_source_type") == trust_config.default_source_type_weight()


def test_effective_weight_uses_type_default_when_no_override():
    assert effective_weight("ticketing") == 0.9


def test_effective_weight_override_beats_type_default():
    # A per-source override (e.g. a decayed reputation) wins over the baseline.
    assert effective_weight("venue_calendar", override=0.42) == 0.42


def test_effective_weight_override_zero_is_respected():
    # 0.0 is a real override, not "unset" — must not fall back to the type default.
    assert effective_weight("venue_calendar", override=0.0) == 0.0


def test_effective_weight_clamped_to_unit_scale():
    assert effective_weight("venue_calendar", override=1.5) == 1.0
    assert effective_weight("venue_calendar", override=-0.5) == 0.0


def test_aggregate_weight_sums_sources():
    assert aggregate_weight([0.9, 0.6, 0.4]) == pytest.approx(1.9)


@pytest.mark.parametrize("weight,expected", [
    (2.0, "likely"),       # >= 1.8
    (1.8, "likely"),       # boundary
    (1.79, "unverified"),
    (1.0, "unverified"),   # boundary
    (0.99, "disputed"),
    (0.0, "disputed"),
])
def test_confidence_from_aggregated_weight(weight, expected):
    assert derive_confidence_from_weight(weight) == expected


def test_confidence_from_weight_returns_canonical_states():
    for w in (0.0, 1.0, 1.8, 3.0):
        assert is_valid_confidence(derive_confidence_from_weight(w))


def test_two_anchor_sources_reach_likely():
    # venue_calendar (1.0) + ticketing (0.9) = 1.9 -> likely.
    total = aggregate_weight([effective_weight("venue_calendar"), effective_weight("ticketing")])
    assert derive_confidence_from_weight(total) == "likely"


def test_single_anonymous_source_is_disputed_by_weight():
    total = aggregate_weight([effective_weight("anonymous")])
    assert derive_confidence_from_weight(total) == "disputed"


# ==========================================================================
# Mechanism 2 — Source Priority Ranking Model
# ==========================================================================

def _metrics(v):
    return SourceMetrics(v, v, v, v, v)


def test_priority_score_full_unit_scale_is_100():
    assert compute_priority_score(_metrics(1.0)) == 100.0


def test_priority_score_zero_is_zero():
    assert compute_priority_score(_metrics(0.0)) == 0.0


def test_priority_score_weighted_formula():
    m = SourceMetrics(
        credibility_weight=0.95,
        access_reliability=0.95,
        coverage_uniqueness=0.90,
        update_frequency_score=0.95,
        verification_anchor_score=1.00,
    )
    # 0.95*.4 + 0.95*.2 + 0.90*.15 + 0.95*.15 + 1.00*.10 = 0.9475 -> 94.75
    assert compute_priority_score(m) == 94.75


def test_percent_scale_matches_unit_scale():
    # Same underlying values on 0-100 must give the same score as 0-1.
    unit = compute_priority_score(_metrics(0.8), scale="unit")
    pct = compute_priority_score(_metrics(80.0), scale="percent")
    assert unit == pct == 80.0


def test_out_of_range_unit_input_fails_loud():
    with pytest.raises(ValueError):
        compute_priority_score(_metrics(1.5), scale="unit")


def test_out_of_range_percent_input_fails_loud():
    with pytest.raises(ValueError):
        compute_priority_score(_metrics(150.0), scale="percent")


def test_unknown_scale_rejected():
    with pytest.raises(ValueError):
        compute_priority_score(_metrics(0.5), scale="bogus")


@pytest.mark.parametrize("score,band,label", [
    (100.0, "P0", "Anchor truth"),
    (85.0, "P0", "Anchor truth"),
    (84.99, "P1", "High trust"),
    (70.0, "P1", "High trust"),
    (69.99, "P2", "Corroboration"),
    (50.0, "P2", "Corroboration"),
    (49.99, "P3", "Weak signal"),
    (0.0, "P3", "Weak signal"),
])
def test_priority_bands_cover_all_four(score, band, label):
    assert priority_band(score) == (band, label)


def test_rank_source_p0():
    r = rank_source(_metrics(0.95))
    assert r.band == "P0"
    assert r.label == "Anchor truth"
    assert r.formula_version == "v1"
    assert r.score == 95.0


def test_rank_source_p3_weak_signal():
    r = rank_source(_metrics(0.2))
    assert r.band == "P3"
    assert r.score == 20.0


def test_rank_source_records_formula_version_for_audit():
    # The version stamped on the result must match the config's current version.
    version, _ = trust_config.priority_formula()
    assert rank_source(_metrics(0.5)).formula_version == version


def test_unknown_formula_version_rejected():
    with pytest.raises(KeyError):
        compute_priority_score(_metrics(0.5), formula_version="v99")


# ==========================================================================
# Mechanism 3 — reputation decay/growth
# ==========================================================================

def test_false_positive_decays_by_multiplier():
    assert decay_growth_v1(1.0, FALSE_POSITIVE) == pytest.approx(0.85)


def test_true_positive_grows_by_multiplier():
    assert decay_growth_v1(0.5, TRUE_POSITIVE) == pytest.approx(0.51)


def test_decay_is_floored_at_0_1():
    # Repeated false positives never sink below the configured floor.
    w = 0.11
    for _ in range(20):
        w = decay_growth_v1(w, FALSE_POSITIVE)
    assert w == pytest.approx(0.1)


def test_single_decay_can_hit_floor_exactly():
    # 0.1 * 0.85 = 0.085 -> floored to 0.1.
    assert decay_growth_v1(0.1, FALSE_POSITIVE) == pytest.approx(0.1)


def test_growth_is_capped_at_1_0():
    # A near-max weight can't exceed the cap after a true positive.
    assert decay_growth_v1(0.99, TRUE_POSITIVE) == pytest.approx(1.0)


def test_growth_from_max_stays_at_cap():
    assert decay_growth_v1(1.0, TRUE_POSITIVE) == pytest.approx(1.0)


def test_unknown_outcome_rejected():
    with pytest.raises(ValueError):
        decay_growth_v1(0.5, "maybe")


def test_get_decay_growth_defaults_to_current_version():
    assert get_decay_growth() is decay_growth_v1
    assert get_decay_growth("v1") is decay_growth_v1


def test_unknown_decay_growth_version_rejected():
    with pytest.raises(KeyError):
        get_decay_growth("v2")


def test_decay_growth_is_pluggable_registry():
    # The registry is the swap point for a future (e.g. Wilson-score) rule.
    assert "v1" in DECAY_GROWTH_FUNCTIONS
    assert callable(DECAY_GROWTH_FUNCTIONS["v1"])


def test_apply_reputation_update_routes_through_registry():
    assert apply_reputation_update(1.0, FALSE_POSITIVE) == pytest.approx(0.85)
    assert apply_reputation_update(0.5, TRUE_POSITIVE) == pytest.approx(0.51)


# ==========================================================================
# Config sanity — the shipped defaults are internally consistent
# ==========================================================================

def test_priority_coefficients_sum_to_one():
    _, coeffs = trust_config.priority_formula()
    assert sum(coeffs.values()) == pytest.approx(1.0)


def test_confidence_thresholds_only_use_canonical_states():
    for row in trust_config.confidence_weight_thresholds():
        assert row["state"] in CONFIDENCE_STATES


def test_bands_are_contiguous_and_sorted():
    bands = trust_config.priority_bands()
    scores = [b["min_score"] for b in bands]
    assert scores == sorted(scores, reverse=True)
    assert bands[-1]["min_score"] == 0  # a catch-all band always matches
