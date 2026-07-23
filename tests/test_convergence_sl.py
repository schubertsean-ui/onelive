"""Tests for the C1 Subjective Logic substrate (worker/convergence/sl.py).

Covers, per the C1 phase definition (docs/strategy/ONE_LIVE_CONVERGENCE_v1.md
§3, §11): evidence-mapping round-trips, fail-loud b+d+u=1 validation, golden
fusion cases with hand-computed expected values, cumulative-vs-averaging
divergence on identical inputs, trust-discount and aging monotonicity, and
every branch of the four_state mapping including the structural
disputed-vs-unverified distinction (b,d both high vs u high). Pure logic —
no DB, no markers.
"""
import math

import pytest

from worker.convergence.sl import (
    PRIOR_WEIGHT,
    FourStateThresholds,
    Opinion,
    age_evidence,
    averaging_fusion,
    cumulative_fusion,
    four_state,
    trust_discount,
)

APPROX = 1e-12

# A reasonable, self-consistent cutline set for exercising the mapping. NOT
# ratified product values — those are a founder-crucial C5 decision (spec
# §11, decision 3), which is exactly why sl.py refuses to default them.
THRESHOLDS = FourStateThresholds(
    disputed_min_b=0.35,
    disputed_min_d=0.35,
    confirmed_min_b=0.70,
    confirmed_max_u=0.15,
    likely_min_b=0.40,
    unverified_min_u=0.60,
)


# --- Opinion construction: fail-loud b+d+u=1 validation -----------------------

class TestOpinionValidation:
    def test_valid_opinion_constructs(self):
        op = Opinion(b=0.5, d=0.3, u=0.2, a=0.4)
        assert op.b == 0.5 and op.d == 0.3 and op.u == 0.2 and op.a == 0.4

    def test_mass_sum_above_one_fails_loud(self):
        with pytest.raises(ValueError, match=r"b\+d\+u=1"):
            Opinion(b=0.6, d=0.3, u=0.2, a=0.5)

    def test_mass_sum_below_one_fails_loud(self):
        with pytest.raises(ValueError, match=r"b\+d\+u=1"):
            Opinion(b=0.2, d=0.2, u=0.2, a=0.5)

    @pytest.mark.parametrize("field,kwargs", [
        ("b", dict(b=-0.1, d=0.6, u=0.5, a=0.5)),
        ("d", dict(b=0.6, d=-0.1, u=0.5, a=0.5)),
        ("u", dict(b=0.6, d=0.5, u=-0.1, a=0.5)),
        ("a", dict(b=0.5, d=0.3, u=0.2, a=1.5)),
        ("b", dict(b=1.2, d=0.0, u=-0.2, a=0.5)),
    ])
    def test_component_out_of_range_fails_loud(self, field, kwargs):
        with pytest.raises(ValueError):
            Opinion(**kwargs)

    @pytest.mark.parametrize("kwargs", [
        dict(b=-1e-12, d=0.5, u=0.5 + 1e-12, a=0.5),
        dict(b=0.5, d=1.0 + 1e-12, u=0.0, a=0.5),
        dict(b=0.5, d=0.5, u=0.0, a=-1e-15),
    ])
    def test_component_bounds_are_exact_no_epsilon(self, kwargs):
        """r7 nit pinned: component bounds are EXACT [0, 1] — a value of
        -1e-12 is a caller bug, not float dust (dust lives in sums only;
        the b+d+u sum keeps its epsilon, tested separately)."""
        with pytest.raises(ValueError):
            Opinion(**kwargs)

    def test_float_dust_tolerated(self):
        # 0.1+0.2+0.7 != 1.0 exactly in floats; validation must accept dust
        # while still rejecting real errors (previous tests). Assert the
        # opinion actually constructs with its components intact (test_audit:
        # a no-assert test cannot fail and proves nothing).
        op = Opinion(b=0.1, d=0.2, u=0.7, a=0.5)
        assert (op.b, op.d, op.u, op.a) == (0.1, 0.2, 0.7, 0.5)
        assert op.b + op.d + op.u == pytest.approx(1.0)

    def test_opinion_is_immutable(self):
        op = Opinion(b=0.5, d=0.3, u=0.2, a=0.5)
        with pytest.raises(AttributeError):
            op.b = 0.9

    def test_expectation_projects_uncertainty_at_base_rate(self):
        # E = b + a*u = 0.5 + 0.4*0.2 = 0.58
        assert Opinion(b=0.5, d=0.3, u=0.2, a=0.4).expectation == pytest.approx(0.58, abs=APPROX)


# --- Beta evidence mapping: bijection with W=2 --------------------------------

class TestEvidenceMapping:
    def test_prior_weight_is_two(self):
        # Spec §3: prior weight W=2, fixed. The bijection's meaning depends on it.
        assert PRIOR_WEIGHT == 2.0

    def test_from_evidence_golden(self):
        # r=3, s=1, W=2: denominator 3+1+2=6 -> b=3/6, d=1/6, u=2/6.
        op = Opinion.from_evidence(3, 1, a=0.5)
        assert op.b == pytest.approx(0.5, abs=APPROX)
        assert op.d == pytest.approx(1 / 6, abs=APPROX)
        assert op.u == pytest.approx(1 / 3, abs=APPROX)

    def test_zero_evidence_is_vacuous(self):
        op = Opinion.from_evidence(0, 0, a=0.3)
        assert op.b == 0.0 and op.d == 0.0 and op.u == 1.0 and op.a == 0.3

    @pytest.mark.parametrize("r,s", [(0, 0), (3, 1), (1, 4), (10, 10), (0.5, 2.5), (100, 0)])
    def test_round_trip_evidence_to_opinion_to_evidence(self, r, s):
        got_r, got_s = Opinion.from_evidence(r, s).to_evidence()
        assert got_r == pytest.approx(r, abs=1e-9)
        assert got_s == pytest.approx(s, abs=1e-9)

    def test_round_trip_opinion_to_evidence_to_opinion(self):
        op = Opinion(b=0.5, d=0.25, u=0.25, a=0.7)
        r, s = op.to_evidence()
        back = Opinion.from_evidence(r, s, a=op.a)
        assert back.b == pytest.approx(op.b, abs=1e-9)
        assert back.d == pytest.approx(op.d, abs=1e-9)
        assert back.u == pytest.approx(op.u, abs=1e-9)
        assert back.a == op.a

    def test_negative_evidence_fails_loud(self):
        with pytest.raises(ValueError, match="non-negative"):
            Opinion.from_evidence(-1, 2)
        with pytest.raises(ValueError, match="non-negative"):
            Opinion.from_evidence(2, -0.5)

    def test_dogmatic_opinion_has_no_evidence_ledger(self):
        with pytest.raises(ValueError, match="[Dd]ogmatic"):
            Opinion(b=1.0, d=0.0, u=0.0, a=0.5).to_evidence()


# --- Cumulative fusion (independent sources) ----------------------------------

class TestCumulativeFusion:
    # Golden pair used throughout: A from evidence (r=3, s=1), B from (r=1, s=1).
    #   A: denom 6 -> b=1/2, d=1/6, u=1/3
    #   B: denom 4 -> b=1/4, d=1/4, u=1/2

    def test_golden_closed_form(self):
        # kappa = uA + uB - uA*uB = 1/3 + 1/2 - 1/6 = 2/3
        # b = (bA*uB + bB*uA)/kappa = (1/2*1/2 + 1/4*1/3)/(2/3)
        #   = (1/4 + 1/12)/(2/3) = (1/3)/(2/3) = 1/2
        # d = (1/6*1/2 + 1/4*1/3)/(2/3) = (1/12 + 1/12)/(2/3) = (1/6)/(2/3) = 1/4
        # u = (1/3*1/2)/(2/3) = (1/6)/(2/3) = 1/4
        a = Opinion.from_evidence(3, 1)
        b = Opinion.from_evidence(1, 1)
        fused = cumulative_fusion(a, b)
        assert fused.b == pytest.approx(0.5, abs=APPROX)
        assert fused.d == pytest.approx(0.25, abs=APPROX)
        assert fused.u == pytest.approx(0.25, abs=APPROX)

    def test_equals_pooled_evidence(self):
        # Spec §3: cumulative fusion IS evidence pooling — (3,1)+(1,1)=(4,2),
        # denom 8 -> b=1/2, d=1/4, u=1/4 (same numbers as the closed form).
        fused = cumulative_fusion(Opinion.from_evidence(3, 1), Opinion.from_evidence(1, 1))
        pooled = Opinion.from_evidence(4, 2)
        assert fused.b == pytest.approx(pooled.b, abs=APPROX)
        assert fused.d == pytest.approx(pooled.d, abs=APPROX)
        assert fused.u == pytest.approx(pooled.u, abs=APPROX)

    def test_commutative(self):
        x, y = Opinion.from_evidence(5, 2), Opinion.from_evidence(1, 3)
        xy, yx = cumulative_fusion(x, y), cumulative_fusion(y, x)
        assert xy.b == pytest.approx(yx.b, abs=APPROX)
        assert xy.u == pytest.approx(yx.u, abs=APPROX)

    def test_vacuous_is_neutral(self):
        # Fusing with "no evidence" changes nothing: (r,s)+(0,0)=(r,s).
        x = Opinion.from_evidence(3, 1, a=0.5)
        fused = cumulative_fusion(x, Opinion.from_evidence(0, 0, a=0.5))
        assert fused.b == pytest.approx(x.b, abs=APPROX)
        assert fused.d == pytest.approx(x.d, abs=APPROX)
        assert fused.u == pytest.approx(x.u, abs=APPROX)

    def test_reduces_uncertainty(self):
        # More independent evidence must never make us less sure.
        x, y = Opinion.from_evidence(3, 1), Opinion.from_evidence(1, 1)
        fused = cumulative_fusion(x, y)
        assert fused.u < x.u and fused.u < y.u

    def test_dogmatic_dominates(self):
        # uX=0 (infinite evidence): the closed form gives the dogmatic
        # opinion unchanged — finite evidence cannot move infinite evidence.
        dogmatic = Opinion(b=1.0, d=0.0, u=0.0, a=0.5)
        fused = cumulative_fusion(dogmatic, Opinion.from_evidence(1, 1))
        assert fused.b == pytest.approx(1.0, abs=APPROX)
        assert fused.u == pytest.approx(0.0, abs=APPROX)

    def test_two_dogmatic_fails_loud(self):
        d1 = Opinion(b=1.0, d=0.0, u=0.0, a=0.5)
        d2 = Opinion(b=0.0, d=1.0, u=0.0, a=0.5)
        with pytest.raises(ValueError, match="dogmatic"):
            cumulative_fusion(d1, d2)

    def test_equal_base_rates_preserved(self):
        fused = cumulative_fusion(
            Opinion.from_evidence(3, 1, a=0.3), Opinion.from_evidence(1, 1, a=0.3)
        )
        assert fused.a == pytest.approx(0.3, abs=APPROX)

    def test_differing_base_rates_golden(self):
        # aA=0.5, aB=0.3, uA=1/3, uB=1/2:
        # num = aA*uB + aB*uA - (aA+aB)*uA*uB = 1/4 + 1/10 - 0.8/6
        #     = 15/60 + 6/60 - 8/60 = 13/60
        # den = uA + uB - 2*uA*uB = 1/3 + 1/2 - 1/3 = 1/2
        # a = (13/60)/(1/2) = 13/30
        fused = cumulative_fusion(
            Opinion.from_evidence(3, 1, a=0.5), Opinion.from_evidence(1, 1, a=0.3)
        )
        assert fused.a == pytest.approx(13 / 30, abs=APPROX)


# --- Averaging fusion (dependent sources) -------------------------------------

class TestAveragingFusion:
    def test_golden_closed_form(self):
        # Same A=(1/2,1/6,1/3), B=(1/4,1/4,1/2) as the cumulative golden.
        # denom = uA + uB = 1/3 + 1/2 = 5/6
        # b = (bA*uB + bB*uA)/denom = (1/4 + 1/12)/(5/6) = (1/3)/(5/6) = 2/5
        # d = (1/6*1/2 + 1/4*1/3)/(5/6) = (1/6)/(5/6) = 1/5
        # u = 2*uA*uB/denom = 2*(1/6)/(5/6) = (1/3)/(5/6) = 2/5
        fused = averaging_fusion(Opinion.from_evidence(3, 1), Opinion.from_evidence(1, 1))
        assert fused.b == pytest.approx(0.4, abs=APPROX)
        assert fused.d == pytest.approx(0.2, abs=APPROX)
        assert fused.u == pytest.approx(0.4, abs=APPROX)

    def test_idempotent_on_identical_opinions(self):
        # The defining property: a source syndicating itself must not count
        # twice (spec §3 — "two aggregators syndicating one feed").
        x = Opinion.from_evidence(3, 1, a=0.4)
        fused = averaging_fusion(x, x)
        assert fused.b == pytest.approx(x.b, abs=APPROX)
        assert fused.d == pytest.approx(x.d, abs=APPROX)
        assert fused.u == pytest.approx(x.u, abs=APPROX)
        assert fused.a == pytest.approx(x.a, abs=APPROX)

    def test_commutative(self):
        x, y = Opinion.from_evidence(5, 2), Opinion.from_evidence(1, 3)
        xy, yx = averaging_fusion(x, y), averaging_fusion(y, x)
        assert xy.b == pytest.approx(yx.b, abs=APPROX)
        assert xy.u == pytest.approx(yx.u, abs=APPROX)

    def test_both_dogmatic_takes_componentwise_mean(self):
        d1 = Opinion(b=1.0, d=0.0, u=0.0, a=0.5)
        d2 = Opinion(b=0.0, d=1.0, u=0.0, a=0.5)
        fused = averaging_fusion(d1, d2)
        assert fused.b == pytest.approx(0.5, abs=APPROX)
        assert fused.d == pytest.approx(0.5, abs=APPROX)
        assert fused.u == pytest.approx(0.0, abs=APPROX)

    def test_base_rate_is_plain_average(self):
        fused = averaging_fusion(
            Opinion.from_evidence(3, 1, a=0.2), Opinion.from_evidence(1, 1, a=0.6)
        )
        assert fused.a == pytest.approx(0.4, abs=APPROX)


# --- Cumulative vs averaging: divergence on the same inputs -------------------

class TestFusionDivergence:
    def test_same_inputs_diverge(self):
        # Golden numbers from the two classes above: cumulative (1/2,1/4,1/4)
        # vs averaging (2/5,1/5,2/5) on identical inputs.
        x, y = Opinion.from_evidence(3, 1), Opinion.from_evidence(1, 1)
        cum, avg = cumulative_fusion(x, y), averaging_fusion(x, y)
        assert cum.b == pytest.approx(0.5, abs=APPROX)
        assert avg.b == pytest.approx(0.4, abs=APPROX)
        assert cum.u == pytest.approx(0.25, abs=APPROX)
        assert avg.u == pytest.approx(0.4, abs=APPROX)

    def test_cumulative_more_certain_than_averaging(self):
        # Independent evidence pools (u shrinks); dependent evidence must not
        # (double-count guard) — so cumulative always ends at least as
        # certain as averaging on the same non-degenerate inputs.
        x, y = Opinion.from_evidence(4, 1), Opinion.from_evidence(2, 3)
        assert cumulative_fusion(x, y).u < averaging_fusion(x, y).u

    def test_averaging_never_beats_most_certain_input(self):
        # Averaging fusion cannot conjure certainty beyond its inputs:
        # u_avg = 2*uX*uY/(uX+uY) is the harmonic-style mean, >= min(uX, uY).
        x, y = Opinion.from_evidence(10, 0), Opinion.from_evidence(1, 1)
        assert averaging_fusion(x, y).u >= min(x.u, y.u) - APPROX


# --- Trust discounting --------------------------------------------------------

class TestTrustDiscount:
    def test_scalar_golden(self):
        # t=0.5 on (0.6, 0.2, 0.2): b'=0.3, d'=0.1, u'=1-0.5*(0.8)=0.6.
        got = trust_discount(Opinion(b=0.6, d=0.2, u=0.2, a=0.5), 0.5)
        assert got.b == pytest.approx(0.3, abs=APPROX)
        assert got.d == pytest.approx(0.1, abs=APPROX)
        assert got.u == pytest.approx(0.6, abs=APPROX)
        assert got.a == 0.5

    def test_opinion_trust_uses_expectation(self):
        # Trust opinion (0.7, 0.1, 0.2, a=0.5): t = b + a*u = 0.7+0.1 = 0.8.
        # On (0.6, 0.2, 0.2): b'=0.48, d'=0.16, u'=1-0.8*0.8=0.36.
        trust = Opinion(b=0.7, d=0.1, u=0.2, a=0.5)
        got = trust_discount(Opinion(b=0.6, d=0.2, u=0.2, a=0.5), trust)
        assert got.b == pytest.approx(0.48, abs=APPROX)
        assert got.d == pytest.approx(0.16, abs=APPROX)
        assert got.u == pytest.approx(0.36, abs=APPROX)

    def test_full_trust_is_identity(self):
        op = Opinion(b=0.6, d=0.2, u=0.2, a=0.5)
        got = trust_discount(op, 1.0)
        assert got.b == pytest.approx(op.b, abs=APPROX)
        assert got.u == pytest.approx(op.u, abs=APPROX)

    def test_zero_trust_yields_vacuous(self):
        got = trust_discount(Opinion(b=0.6, d=0.2, u=0.2, a=0.5), 0.0)
        assert got.b == pytest.approx(0.0, abs=APPROX)
        assert got.d == pytest.approx(0.0, abs=APPROX)
        assert got.u == pytest.approx(1.0, abs=APPROX)

    def test_monotone_lower_trust_higher_uncertainty(self):
        # Spec §3: discounting weakens; u' = 1 - t*(b+d) strictly grows as
        # trust falls (for any opinion carrying actual evidence).
        op = Opinion(b=0.6, d=0.2, u=0.2, a=0.5)
        us = [trust_discount(op, t).u for t in (1.0, 0.8, 0.5, 0.2, 0.0)]
        assert us == sorted(us) and len(set(us)) == len(us)

    def test_distrust_never_flips_belief_to_disbelief(self):
        got = trust_discount(Opinion(b=0.9, d=0.0, u=0.1, a=0.5), 0.1)
        assert got.d == pytest.approx(0.0, abs=APPROX)

    def test_out_of_range_scalar_fails_loud(self):
        op = Opinion(b=0.6, d=0.2, u=0.2, a=0.5)
        with pytest.raises(ValueError):
            trust_discount(op, 1.5)
        with pytest.raises(ValueError):
            trust_discount(op, -0.1)

    def test_wrong_type_fails_loud(self):
        with pytest.raises(TypeError):
            trust_discount(Opinion(b=0.6, d=0.2, u=0.2, a=0.5), "0.5")


# --- Evidence aging -----------------------------------------------------------

class TestAgeEvidence:
    def test_golden_half_life_step(self):
        # (r=8, s=2) -> b=8/12, d=2/12, u=2/12. Factor 0.5 -> (4, 1):
        # denom 7 -> b=4/7, d=1/7, u=2/7.
        aged = age_evidence(Opinion.from_evidence(8, 2), 0.5)
        assert aged.b == pytest.approx(4 / 7, abs=APPROX)
        assert aged.d == pytest.approx(1 / 7, abs=APPROX)
        assert aged.u == pytest.approx(2 / 7, abs=APPROX)

    def test_identity_at_factor_one(self):
        op = Opinion.from_evidence(8, 2, a=0.4)
        aged = age_evidence(op, 1.0)
        assert aged.b == pytest.approx(op.b, abs=APPROX)
        assert aged.u == pytest.approx(op.u, abs=APPROX)

    def test_monotone_more_decay_more_uncertainty(self):
        op = Opinion.from_evidence(8, 2)
        us = [age_evidence(op, f).u for f in (1.0, 0.7, 0.4, 0.1)]
        assert us == sorted(us) and len(set(us)) == len(us)

    def test_preserves_belief_disbelief_ratio(self):
        # Staleness makes us less sure, not differently opinionated: both
        # counts shrink by the same factor, so b/d is invariant.
        op = Opinion.from_evidence(8, 2)
        aged = age_evidence(op, 0.3)
        assert aged.b / aged.d == pytest.approx(op.b / op.d, abs=1e-9)

    def test_composes_exponentially(self):
        # Two half-steps = one quarter-step: exp decay composes by product.
        op = Opinion.from_evidence(8, 2)
        twice = age_evidence(age_evidence(op, 0.5), 0.5)
        once = age_evidence(op, 0.25)
        assert twice.u == pytest.approx(once.u, abs=APPROX)
        assert twice.b == pytest.approx(once.b, abs=APPROX)

    def test_preserves_base_rate(self):
        assert age_evidence(Opinion.from_evidence(8, 2, a=0.7), 0.5).a == 0.7

    def test_vacuous_is_fixed_point(self):
        aged = age_evidence(Opinion.from_evidence(0, 0), 0.5)
        assert aged.u == pytest.approx(1.0, abs=APPROX)

    @pytest.mark.parametrize("factor", [0.0, -0.5, 1.5, math.inf])
    def test_out_of_range_factor_fails_loud(self, factor):
        with pytest.raises(ValueError):
            age_evidence(Opinion.from_evidence(8, 2), factor)

    def test_dogmatic_opinion_fails_loud(self):
        with pytest.raises(ValueError, match="[Dd]ogmatic"):
            age_evidence(Opinion(b=1.0, d=0.0, u=0.0, a=0.5), 0.5)


# --- four_state mapping -------------------------------------------------------

class TestFourState:
    def test_high_uncertainty_is_unverified(self):
        # Spec §3 table: high u -> "nobody really knows yet".
        assert four_state(Opinion(b=0.1, d=0.1, u=0.8, a=0.5), THRESHOLDS) == "unverified"

    def test_moderate_belief_is_likely(self):
        # b=0.5 clears likely_min_b=0.4; u=0.4 below the unverified floor
        # and above confirmed_max_u; d=0.1 below the disputed floor.
        assert four_state(Opinion(b=0.5, d=0.1, u=0.4, a=0.5), THRESHOLDS) == "likely"

    def test_high_belief_low_uncertainty_is_confirmed(self):
        assert four_state(Opinion(b=0.85, d=0.05, u=0.10, a=0.5), THRESHOLDS) == "confirmed"

    def test_high_belief_and_high_disbelief_is_disputed(self):
        assert four_state(Opinion(b=0.45, d=0.45, u=0.10, a=0.5), THRESHOLDS) == "disputed"

    def test_thin_evidence_below_every_bar_falls_back_to_unverified(self):
        # b=0.3 (< likely), d=0.3 (< disputed), u=0.4 (< unverified floor):
        # clears no cutline -> fail-closed reading is "unverified".
        assert four_state(Opinion(b=0.3, d=0.3, u=0.4, a=0.5), THRESHOLDS) == "unverified"

    def test_disputed_vs_unverified_structural_distinction(self):
        # Spec §3: conflict (b,d both high, u squeezed out) and ignorance
        # (u high) both read "not confirmed" under counting, but are
        # structurally different states under SL — same b/d ratio, opposite
        # diagnosis, different answer.
        conflict = Opinion(b=0.45, d=0.45, u=0.10, a=0.5)
        ignorance = Opinion(b=0.05, d=0.05, u=0.90, a=0.5)
        assert four_state(conflict, THRESHOLDS) == "disputed"
        assert four_state(ignorance, THRESHOLDS) == "unverified"

    def test_disputed_outranks_confirmed(self):
        # Spec §6.6: a b/d collision routes to disputed even at
        # confirmed-strength belief (shown, never hidden). Cutlines chosen
        # so one opinion satisfies both signatures.
        overlap = FourStateThresholds(
            disputed_min_b=0.30,
            disputed_min_d=0.25,
            confirmed_min_b=0.60,
            confirmed_max_u=0.20,
            likely_min_b=0.40,
            unverified_min_u=0.60,
        )
        both = Opinion(b=0.65, d=0.25, u=0.10, a=0.5)
        assert both.b >= overlap.confirmed_min_b and both.u <= overlap.confirmed_max_u
        assert four_state(both, overlap) == "disputed"

    def test_returns_only_ratified_state_names(self):
        # Sweep the opinion simplex; every output must be one of the four
        # ratified confidence states (CLAUDE.md: 4-state model, confirmed
        # decision).
        states = set()
        steps = [i / 20 for i in range(21)]
        for b in steps:
            for d in steps:
                if b + d <= 1.0 + 1e-9:
                    op = Opinion(b=b, d=d, u=max(0.0, 1.0 - b - d), a=0.5)
                    states.add(four_state(op, THRESHOLDS))
        assert states == {"unverified", "likely", "confirmed", "disputed"}


# --- FourStateThresholds validation -------------------------------------------

class TestThresholdValidation:
    def test_component_out_of_range_fails_loud(self):
        with pytest.raises(ValueError):
            FourStateThresholds(
                disputed_min_b=0.35, disputed_min_d=0.35, confirmed_min_b=1.2,
                confirmed_max_u=0.15, likely_min_b=0.4, unverified_min_u=0.6,
            )

    def test_unreachable_disputed_state_fails_loud(self):
        # disputed_min_b + disputed_min_d > 1 would silently disable the
        # conflict state (b+d<=1 always) — must fail at construction.
        with pytest.raises(ValueError, match="disputed"):
            FourStateThresholds(
                disputed_min_b=0.6, disputed_min_d=0.6, confirmed_min_b=0.7,
                confirmed_max_u=0.15, likely_min_b=0.4, unverified_min_u=0.6,
            )

    def test_likely_above_confirmed_fails_loud(self):
        with pytest.raises(ValueError, match="likely_min_b"):
            FourStateThresholds(
                disputed_min_b=0.35, disputed_min_d=0.35, confirmed_min_b=0.5,
                confirmed_max_u=0.15, likely_min_b=0.6, unverified_min_u=0.6,
            )

    def test_confirmed_overlapping_unverified_fails_loud(self):
        with pytest.raises(ValueError, match="confirmed_max_u"):
            FourStateThresholds(
                disputed_min_b=0.35, disputed_min_d=0.35, confirmed_min_b=0.7,
                confirmed_max_u=0.6, likely_min_b=0.4, unverified_min_u=0.6,
            )


# --- Shadow isolation (C1 invariant: zero product-path coupling) --------------

class TestShadowIsolation:
    def test_sl_module_imports_nothing_from_the_pipeline(self):
        # Spec §11 C1: "zero product-path coupling". The substrate must be
        # pure stdlib — no worker/ai/api imports, no third-party packages.
        import worker.convergence.sl as sl_module
        import sys
        source = open(sl_module.__file__, encoding="utf-8").read()
        import ast
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        for mod in imported:
            top = mod.split(".")[0]
            assert top in sys.stdlib_module_names or mod == "__future__", (
                f"sl.py imports non-stdlib module {mod!r}; C1 must stay "
                f"standalone (spec §11: shadow, zero pipeline coupling)."
            )
            assert top not in ("worker", "ai", "api", "tools"), (
                f"sl.py imports pipeline module {mod!r}; C1 forbids coupling."
            )
