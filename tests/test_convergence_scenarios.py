"""Tests for the C2 scenario + decision layer (worker/convergence/
scenarios.py, worker/convergence/decisions.py).

Covers, per the C2 phase definition (docs/strategy/ONE_LIVE_CONVERGENCE_v1.md
§5, §11): deterministic replayable world sampling with an explicit mandatory
seed (same seed -> identical output, different seed -> different, absent seed
-> fail loud), classification of every outcome mode with hand-built worlds,
aggregation goldens with hand-computed arithmetic, expected-loss / decide /
VoI goldens matching the worked examples in
docs/strategy/ONE_LIVE_COST_MATRIX_DRAFT_v1.md, fail-loud CostMatrix
validation (missing cells above all), and the C1 shadow-isolation AST test
extended to both new modules. Pure logic — no DB, no markers.
"""
import ast
import json
import sys

import pytest

from worker.convergence.decisions import (
    CostMatrix,
    decide,
    expected_loss,
    voi,
)
from worker.convergence.scenarios import (
    MODE_FULLY_WRONG,
    MODE_PARTIALLY_WRONG,
    MODE_RIGHT,
    MODES,
    World,
    WorldOutcome,
    aggregate,
    classify_world,
    run_scenarios,
    sample_worlds,
)
from worker.convergence.sl import Opinion

APPROX = 1e-12

# Deterministic building blocks: dogmatic opinions are point masses, so the
# sampler's output is exactly predictable (worlds become hand-computable
# goldens instead of statistical checks). a=0.0 so that even a discounted-
# to-vacuous opinion stays deterministic (Beta(0, W) concentrates at 0).
ALWAYS_TRUE = Opinion(b=1.0, d=0.0, u=0.0, a=0.0)
ALWAYS_FALSE = Opinion(b=0.0, d=1.0, u=0.0, a=0.0)

# The DRAFT matrix from docs/strategy/ONE_LIVE_COST_MATRIX_DRAFT_v1.md §2
# (standard tier). Test data only — NOT ratified product values; the real
# numbers are the founder's C2 ratification (spec §11 decision 1), which is
# exactly why decisions.py refuses to bundle any default.
DRAFT_COSTS = {
    "surface_confirmed": {"fully_wrong": 100, "partially_wrong": 6, "right": 0},
    "surface_likely": {"fully_wrong": 40, "partially_wrong": 4, "right": 1},
    "hold": {"fully_wrong": 2, "partially_wrong": 10, "right": 15},
    "flag_disputed": {"fully_wrong": 3, "partially_wrong": 6, "right": 8},
}


def _stochastic_inputs():
    """Non-degenerate opinions so sampling actually varies world to world."""
    field_opinions = {
        "exists": Opinion.from_evidence(8, 2, a=0.5),
        "date": Opinion.from_evidence(4, 1, a=0.5),
        "start_time": Opinion.from_evidence(2, 2, a=0.5),
    }
    source_reliabilities = {
        "venue_site": Opinion.from_evidence(9, 1, a=0.5),
        "aggregator": Opinion.from_evidence(3, 3, a=0.5),
    }
    field_sources = {
        "exists": ("venue_site",),
        "date": ("venue_site", "aggregator"),
        "start_time": ("aggregator",),
    }
    return field_opinions, source_reliabilities, field_sources


def _forge_outcome(mode, wrong_fields):
    """Build a WorldOutcome bypassing __post_init__ (object.__new__), to
    exercise aggregate()'s OWN defense-in-depth checks — WorldOutcome now
    rejects these states at construction (evaluator r8), but aggregate must
    still catch a forged/deserialized outcome that never ran validation."""
    o = object.__new__(WorldOutcome)
    object.__setattr__(o, "mode", mode)
    object.__setattr__(o, "wrong_fields", wrong_fields)
    return o


def _mk_voi(**kwargs):
    """Build a VoiRecord directly, to exercise its validations. Evaluator
    r13 replaced the r12 factory token (importable, convention-only) with
    self-verifying matrix storage: VoiRecord is publicly constructible, but
    every embedded DecisionRecord carries its cost matrix (verified against
    its terms), and VoiRecord rejects decisions under different matrices —
    so a directly-built VoiRecord can only be a legitimate single-matrix
    VoI, not a cross-matrix forgery (test_forged_voi_record_cross_matrix)."""
    from worker.convergence.decisions import VoiRecord
    return VoiRecord(**kwargs)


# --- Seed discipline: explicit, mandatory, replayable -------------------------

class TestSeedDiscipline:
    def test_missing_seed_fails_loud(self):
        # Spec §9: stochastic non-replayability is an audit liability. The
        # seed is keyword-only with NO default: omitting it is a TypeError
        # at the call site, never a silent nondeterministic run.
        fo, sr, fs = _stochastic_inputs()
        with pytest.raises(TypeError):
            sample_worlds(fo, sr, fs, "exists", 10)
        with pytest.raises(TypeError):
            run_scenarios(fo, sr, fs, "exists", 10)

    @pytest.mark.parametrize("bad_seed", [None, "42", 1.5, True])
    def test_non_int_seed_fails_loud(self, bad_seed):
        fo, sr, fs = _stochastic_inputs()
        with pytest.raises(TypeError, match="seed"):
            sample_worlds(fo, sr, fs, "exists", 10, seed=bad_seed)

    def test_same_seed_identical_output(self):
        fo, sr, fs = _stochastic_inputs()
        a = run_scenarios(fo, sr, fs, "exists", 300, seed=42)
        b = run_scenarios(fo, sr, fs, "exists", 300, seed=42)
        assert a == b
        # And at the raw-world level too, including the reliability draws.
        wa = sample_worlds(fo, sr, fs, "exists", 50, seed=7)
        wb = sample_worlds(fo, sr, fs, "exists", 50, seed=7)
        assert wa == wb

    def test_two_seed_golden_summaries(self):
        # Evaluator r1 nit (PR #54): a bare "a != b" different-seed check
        # is probabilistic in principle (r3 removed it as redundant);
        # these pinned goldens make the check exact — the two summaries
        # differ AND each matches its pin — and they double
        # as a replay-drift detector — if a CPython upgrade ever changes
        # random.Random's distribution algorithms, spec §9 replayability is
        # broken and this test says so loudly instead of letting recorded
        # seeds silently stop reproducing their audited summaries.
        #
        # SUPPORTED-VERSION BOUNDARY (evaluator r5 nit, PR #54): these
        # goldens are deliberately coupled to CPython's random.Random
        # (Mersenne Twister) betavariate/random implementation. They hold
        # on CPython 3.12 (the CI + worker runtime, worker/requirements +
        # setup-python 3.12). A CPython minor/major bump that alters those
        # algorithms is EXPECTED to fail here — that is the drift alarm, not
        # a flaky test; re-pin the goldens against the new interpreter and
        # note the version in docs/evidence when replay provenance moves.
        fo, sr, fs = _stochastic_inputs()
        a = run_scenarios(fo, sr, fs, "exists", 300, seed=1)
        b = run_scenarios(fo, sr, fs, "exists", 300, seed=2)
        assert a.mode_probs == {
            MODE_FULLY_WRONG: 0.27666666666666667,
            MODE_PARTIALLY_WRONG: 0.49,
            MODE_RIGHT: 0.23333333333333334,
        }
        assert a.field_failure_rates == {
            "date": 0.29, "start_time": 0.3566666666666667,
        }
        assert b.mode_probs == {
            MODE_FULLY_WRONG: 0.2633333333333333,
            MODE_PARTIALLY_WRONG: 0.51,
            MODE_RIGHT: 0.22666666666666666,
        }
        assert b.field_failure_rates == {
            "date": 0.32, "start_time": 0.3433333333333333,
        }


# --- World sampling: deterministic goldens ------------------------------------

class TestSampling:
    def test_dogmatic_true_fields_always_right(self):
        # Point-mass opinions: p(exists)=1, p(date)=1 in every world, so
        # every world is classified `right` — mode_probs {0, 0, 1} exactly.
        summary = run_scenarios(
            {"exists": ALWAYS_TRUE, "date": ALWAYS_TRUE},
            {}, {}, "exists", 200, seed=3,
        )
        assert summary.mode_probs == {
            MODE_FULLY_WRONG: 0.0, MODE_PARTIALLY_WRONG: 0.0, MODE_RIGHT: 1.0,
        }
        assert summary.field_failure_rates == {"date": 0.0}
        assert summary.partial_attribution == {}

    def test_dogmatic_false_field_always_partially_wrong(self):
        # exists always true, date always false -> every world is
        # partially_wrong and the wrong field is carried by name (spec §5:
        # "right event, wrong field — carry WHICH field").
        summary = run_scenarios(
            {"exists": ALWAYS_TRUE, "date": ALWAYS_FALSE, "price": ALWAYS_TRUE},
            {}, {}, "exists", 200, seed=3,
        )
        assert summary.mode_probs[MODE_PARTIALLY_WRONG] == 1.0
        assert summary.field_failure_rates == {"date": 1.0, "price": 0.0}
        assert summary.partial_attribution == {"date": 1.0, "price": 0.0}

    def test_nonexistent_event_always_fully_wrong(self):
        # exists false dominates: even with another wrong field the mode is
        # fully_wrong (a phantom has no separately-attributable details).
        summary = run_scenarios(
            {"exists": ALWAYS_FALSE, "date": ALWAYS_FALSE},
            {}, {}, "exists", 100, seed=5,
        )
        assert summary.mode_probs[MODE_FULLY_WRONG] == 1.0
        assert summary.field_failure_rates == {"date": 0.0}

    def test_zero_reliability_source_zeroes_its_field(self):
        # date is dogmatically true BUT its only source has dogmatic-zero
        # reliability: trust_discount(t=0) yields the vacuous opinion with
        # a=0, whose Beta(0, 2) limit concentrates at p=0 -> date is wrong
        # in every world. Reliability visibly drives outcomes (spec §5:
        # "failures cluster in worlds where the aggregator feed is stale").
        summary = run_scenarios(
            {"exists": ALWAYS_TRUE, "date": ALWAYS_TRUE},
            {"aggregator": ALWAYS_FALSE},
            {"date": ("aggregator",)},
            "exists", 100, seed=9,
        )
        assert summary.mode_probs[MODE_PARTIALLY_WRONG] == 1.0
        assert summary.field_failure_rates == {"date": 1.0}

    def test_full_reliability_source_leaves_field_intact(self):
        # Same setup with a perfectly reliable source: t=1 discount is the
        # identity, so date stays right in every world.
        summary = run_scenarios(
            {"exists": ALWAYS_TRUE, "date": ALWAYS_TRUE},
            {"aggregator": Opinion(b=1.0, d=0.0, u=0.0, a=1.0)},
            {"date": ("aggregator",)},
            "exists", 100, seed=9,
        )
        assert summary.mode_probs[MODE_RIGHT] == 1.0

    def test_sampled_frequency_tracks_opinion_expectation(self):
        # exists ~ from_evidence(8,2): Beta(alpha=8+1, beta=2+1)=Beta(9,3),
        # mean 0.75 -> P(fully_wrong) = 0.25. With 4000 worlds the observed
        # frequency must sit within 0.03 (>4 sigma; deterministic under the
        # fixed seed, so this cannot flake).
        summary = run_scenarios(
            {"exists": Opinion.from_evidence(8, 2, a=0.5)},
            {}, {}, "exists", 4000, seed=11,
        )
        assert abs(summary.mode_probs[MODE_FULLY_WRONG] - 0.25) < 0.03

    def test_worlds_record_reliability_draws(self):
        fo, sr, fs = _stochastic_inputs()
        worlds = sample_worlds(fo, sr, fs, "exists", 5, seed=1)
        assert len(worlds) == 5
        for w in worlds:
            assert set(w.source_reliabilities) == {"venue_site", "aggregator"}
            for t in w.source_reliabilities.values():
                assert 0.0 <= t <= 1.0
            assert set(w.field_truths) == {"exists", "date", "start_time"}

    def test_missing_existence_field_fails_loud(self):
        with pytest.raises(ValueError, match="existence_field"):
            sample_worlds({"date": ALWAYS_TRUE}, {}, {}, "exists", 10, seed=1)

    def test_unknown_source_fails_loud(self):
        with pytest.raises(ValueError, match="reliability"):
            sample_worlds(
                {"exists": ALWAYS_TRUE}, {}, {"exists": ("ghost_feed",)},
                "exists", 10, seed=1,
            )

    def test_string_field_sources_value_fails_loud(self):
        # Evaluator r6 nit (PR #54): a bare string is iterable and would be
        # consumed character-by-character; require a real sequence.
        with pytest.raises(ValueError, match="not str|list/tuple"):
            sample_worlds(
                {"exists": ALWAYS_TRUE},
                {"venue_site": ALWAYS_TRUE},
                {"exists": "venue_site"},  # string, not ("venue_site",)
                "exists", 10, seed=1,
            )

    def test_duplicate_source_in_field_sources_fails_loud(self):
        # Evaluator r4 (PR #54): a duplicated source double-discounts the
        # field's opinion (trust_discount runs once per entry), and the
        # set()-based unknown-source check hides it.
        with pytest.raises(ValueError, match="duplicate source"):
            sample_worlds(
                {"exists": ALWAYS_TRUE},
                {"venue_site": ALWAYS_TRUE},
                {"exists": ("venue_site", "venue_site")},
                "exists", 10, seed=1,
            )

    def test_unused_source_reliability_fails_loud(self):
        # Evaluator r2 (PR #54): an unused reliability row would still be
        # sampled, silently shifting the RNG stream — same seed, different
        # worlds whenever an irrelevant source is added, which spec §9
        # replayability forbids. The input set must be exactly the sampled
        # set.
        with pytest.raises(ValueError, match="referenced by no field"):
            sample_worlds(
                {"exists": ALWAYS_TRUE},
                {"venue_site": ALWAYS_TRUE, "idle_feed": ALWAYS_TRUE},
                {"exists": ("venue_site",)},
                "exists", 10, seed=1,
            )

    def test_unknown_field_in_field_sources_fails_loud(self):
        with pytest.raises(ValueError, match="unknown field"):
            sample_worlds(
                {"exists": ALWAYS_TRUE}, {"s": ALWAYS_TRUE},
                {"date": ("s",)}, "exists", 10, seed=1,
            )

    @pytest.mark.parametrize("n", [0, -5, 2.5, True])
    def test_bad_n_worlds_fails_loud(self, n):
        with pytest.raises(ValueError, match="n_worlds"):
            sample_worlds({"exists": ALWAYS_TRUE}, {}, {}, "exists", n, seed=1)

    def test_empty_field_opinions_fails_loud(self):
        with pytest.raises(ValueError, match="empty"):
            sample_worlds({}, {}, {}, "exists", 10, seed=1)


# --- Outcome classification ----------------------------------------------------

class TestClassification:
    def test_fully_wrong(self):
        # Spec §5: event not real / cancelled -> fully_wrong; a phantom's
        # other fields are not separately attributable (wrong_fields empty).
        world = World(
            field_truths={"exists": False, "date": False, "price": True},
            source_reliabilities={},
        )
        outcome = classify_world(world, "exists")
        assert outcome == WorldOutcome(mode=MODE_FULLY_WRONG, wrong_fields=())

    def test_partially_wrong_carries_which_fields(self):
        # Spec §5: "right event, wrong start time / wrong tag / wrong price"
        # — the wrong fields are named, sorted for determinism.
        world = World(
            field_truths={"exists": True, "date": True,
                          "start_time": False, "price": False},
            source_reliabilities={},
        )
        outcome = classify_world(world, "exists")
        assert outcome.mode == MODE_PARTIALLY_WRONG
        assert outcome.wrong_fields == ("price", "start_time")

    def test_right(self):
        world = World(
            field_truths={"exists": True, "date": True},
            source_reliabilities={},
        )
        assert classify_world(world, "exists") == WorldOutcome(
            mode=MODE_RIGHT, wrong_fields=()
        )

    def test_existence_only_claim_can_be_right(self):
        world = World(field_truths={"exists": True}, source_reliabilities={})
        assert classify_world(world, "exists").mode == MODE_RIGHT

    def test_missing_existence_field_fails_loud(self):
        world = World(field_truths={"date": True}, source_reliabilities={})
        with pytest.raises(ValueError, match="existence_field"):
            classify_world(world, "exists")

    def test_non_bool_field_truth_fails_at_world_construction(self):
        # Evaluator r4 (PR #54): a forged/deserialized world with a
        # non-bool truth ("False" is a truthy string) must fail loud at
        # construction, never be coerced by truthiness in classification.
        with pytest.raises(ValueError, match="must be a bool"):
            World(field_truths={"exists": "False"}, source_reliabilities={})
        with pytest.raises(ValueError, match="must be a bool"):
            World(field_truths={"exists": 1}, source_reliabilities={})

    def test_out_of_range_reliability_fails_at_world_construction(self):
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            World(field_truths={"exists": True},
                  source_reliabilities={"venue_site": 1.5})
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            World(field_truths={"exists": True},
                  source_reliabilities={"venue_site": float("nan")})


class TestWorldOutcomeConstruction:
    """Evaluator r8 (PR #54): WorldOutcome is a public classified-world
    audit record; its constructor fails loud on impossible states and
    normalizes wrong_fields to an immutable tuple — the invariant holds at
    construction, not merely when the outcome later reaches aggregate()."""

    def test_bad_mode_rejected(self):
        with pytest.raises(ValueError, match="must be one of"):
            WorldOutcome(mode="sideways", wrong_fields=())

    def test_wrong_fields_outside_partially_wrong_rejected(self):
        for mode in (MODE_RIGHT, MODE_FULLY_WRONG):
            with pytest.raises(ValueError, match="only partially_wrong"):
                WorldOutcome(mode=mode, wrong_fields=("date",))

    def test_partially_wrong_needs_a_field(self):
        with pytest.raises(ValueError, match="at least one wrong field"):
            WorldOutcome(mode=MODE_PARTIALLY_WRONG, wrong_fields=())

    def test_duplicate_wrong_fields_rejected(self):
        with pytest.raises(ValueError, match="duplicate"):
            WorldOutcome(mode=MODE_PARTIALLY_WRONG,
                         wrong_fields=("date", "date"))

    def test_non_string_wrong_field_rejected(self):
        with pytest.raises(ValueError, match="field-name strings"):
            WorldOutcome(mode=MODE_PARTIALLY_WRONG, wrong_fields=(3,))

    def test_bare_string_wrong_fields_rejected(self):
        # Evaluator r9 (PR #54): a regression in the r8 fix — tuple("date")
        # would silently become ("d","a","t","e"). A bare string must fail
        # loud, not be split into characters.
        with pytest.raises(ValueError, match="not a bare str"):
            WorldOutcome(mode=MODE_PARTIALLY_WRONG, wrong_fields="date")

    def test_list_wrong_fields_normalized_to_tuple(self):
        # A mutable list is frozen to a tuple so the evidence cannot be
        # edited after construction (the "mutable wrong_fields" concern).
        o = WorldOutcome(mode=MODE_PARTIALLY_WRONG, wrong_fields=["date"])
        assert isinstance(o.wrong_fields, tuple)
        assert o.wrong_fields == ("date",)

    def test_valid_outcomes_construct(self):
        assert WorldOutcome(mode=MODE_RIGHT, wrong_fields=()).wrong_fields == ()
        assert WorldOutcome(
            mode=MODE_PARTIALLY_WRONG, wrong_fields=("date", "start_time")
        ).mode == MODE_PARTIALLY_WRONG

    def test_wrong_fields_normalized_sorted(self):
        # Evaluator r10 nit (PR #54): the documented "sorted tuple" holds at
        # construction, so equality is order-independent.
        o = WorldOutcome(mode=MODE_PARTIALLY_WRONG,
                         wrong_fields=("start_time", "date"))
        assert o.wrong_fields == ("date", "start_time")
        assert o == WorldOutcome(mode=MODE_PARTIALLY_WRONG,
                                 wrong_fields=("date", "start_time"))


# --- Aggregation: hand-computed golden ----------------------------------------

class TestAggregation:
    def test_golden_hand_computed(self):
        # 4 worlds: 1 fully_wrong, 2 partially_wrong (one with date wrong;
        # one with date AND start_time wrong), 1 right.
        #   mode_probs: fully 1/4=0.25, partial 2/4=0.5, right 1/4=0.25
        #   field_failure_rates (over ALL 4 worlds):
        #     date wrong in 2 worlds -> 2/4 = 0.5
        #     start_time wrong in 1 world -> 1/4 = 0.25
        #   partial_attribution (over the 2 partial worlds):
        #     date 2/2 = 1.0; start_time 1/2 = 0.5
        outcomes = [
            WorldOutcome(mode=MODE_FULLY_WRONG, wrong_fields=()),
            WorldOutcome(mode=MODE_PARTIALLY_WRONG, wrong_fields=("date",)),
            WorldOutcome(mode=MODE_PARTIALLY_WRONG,
                         wrong_fields=("date", "start_time")),
            WorldOutcome(mode=MODE_RIGHT, wrong_fields=()),
        ]
        summary = aggregate(outcomes, ["date", "start_time"])
        assert summary.n_worlds == 4
        assert summary.mode_probs == {
            MODE_FULLY_WRONG: 0.25, MODE_PARTIALLY_WRONG: 0.5, MODE_RIGHT: 0.25,
        }
        assert summary.field_failure_rates == {"date": 0.5, "start_time": 0.25}
        assert summary.partial_attribution == {"date": 1.0, "start_time": 0.5}

    def test_never_failed_field_gets_explicit_zero(self):
        # Absence of a row must never be the encoding of "fine".
        summary = aggregate(
            [WorldOutcome(mode=MODE_RIGHT, wrong_fields=())], ["date"]
        )
        assert summary.field_failure_rates == {"date": 0.0}

    def test_no_partial_worlds_means_empty_attribution(self):
        # The conditional P(field wrong | partially_wrong) is undefined with
        # zero partial worlds; the summary says so with an empty dict rather
        # than fabricating zeros for a distribution that has no denominator.
        summary = aggregate(
            [WorldOutcome(mode=MODE_FULLY_WRONG, wrong_fields=())], ["date"]
        )
        assert summary.partial_attribution == {}

    def test_empty_outcomes_fails_loud(self):
        with pytest.raises(ValueError, match="zero outcomes"):
            aggregate([], ["date"])

    def test_unknown_mode_fails_loud(self):
        # aggregate() still defends against a forged outcome that bypassed
        # WorldOutcome's own construction check (object.__new__).
        with pytest.raises(ValueError, match="Unknown outcome mode"):
            aggregate([_forge_outcome("sideways", ())], [])

    def test_wrong_field_outside_field_names_fails_loud(self):
        with pytest.raises(ValueError, match="not in field_names"):
            aggregate(
                [WorldOutcome(mode=MODE_PARTIALLY_WRONG, wrong_fields=("tag",))],
                ["date"],
            )

    def test_duplicate_field_names_rejected(self):
        # Evaluator r10 nit (PR #54): silently de-duplicating field_names
        # would hide a malformed attribution request.
        with pytest.raises(ValueError, match="duplicate"):
            aggregate(
                [WorldOutcome(mode=MODE_RIGHT, wrong_fields=())],
                ["date", "date"],
            )

    def test_aggregate_defends_against_bare_string_wrong_fields(self):
        # Evaluator r14 nit (PR #54): WorldOutcome rejects a bare-string
        # wrong_fields at construction; aggregate() defends in depth against
        # a forged outcome (object.__new__ bypass) that would otherwise be
        # attributed character by character.
        with pytest.raises(ValueError, match="bare str"):
            aggregate([_forge_outcome(MODE_PARTIALLY_WRONG, "date")], ["date"])

    def test_forged_scenario_summary_fails_loud(self):
        # Evaluator r4 nit (PR #54): aggregate() is always valid, but the
        # public ScenarioSummary constructor must not manufacture
        # impossible audit evidence.
        from worker.convergence.scenarios import ScenarioSummary

        good = {MODE_FULLY_WRONG: 0.25, MODE_PARTIALLY_WRONG: 0.5,
                MODE_RIGHT: 0.25}
        # non-positive n_worlds
        with pytest.raises(ValueError, match="n_worlds"):
            ScenarioSummary(n_worlds=0, mode_probs=good,
                            field_failure_rates={}, partial_attribution={})
        # mode keys wrong
        with pytest.raises(ValueError, match="mode_probs keys"):
            ScenarioSummary(n_worlds=4, mode_probs={"x": 1.0},
                            field_failure_rates={}, partial_attribution={})
        # probability out of range
        with pytest.raises(ValueError, match=r"\[0, 1\]"):
            ScenarioSummary(
                n_worlds=4,
                mode_probs={MODE_FULLY_WRONG: -0.1, MODE_PARTIALLY_WRONG: 0.6,
                            MODE_RIGHT: 0.5},
                field_failure_rates={}, partial_attribution={})
        # does not sum to 1
        with pytest.raises(ValueError, match="sum to 1"):
            ScenarioSummary(
                n_worlds=4,
                mode_probs={MODE_FULLY_WRONG: 0.1, MODE_PARTIALLY_WRONG: 0.1,
                            MODE_RIGHT: 0.1},
                field_failure_rates={}, partial_attribution={})

    def test_scenario_summary_cross_field_invariant_enforced(self):
        # Evaluator r5 (PR #54): field_failure_rates[f] must equal
        # partial_attribution[f] * P(partially_wrong) exactly — a field can
        # only fail inside a partially_wrong world.
        from worker.convergence.scenarios import ScenarioSummary

        # nonzero failure rate while no world is partially wrong
        with pytest.raises(ValueError, match="no world is partially wrong"):
            ScenarioSummary(
                n_worlds=4,
                mode_probs={MODE_FULLY_WRONG: 0.5, MODE_PARTIALLY_WRONG: 0.0,
                            MODE_RIGHT: 0.5},
                field_failure_rates={"date": 0.5}, partial_attribution={})
        # partial probability > 0 but no attribution carried
        with pytest.raises(ValueError, match="partial_attribution is empty"):
            ScenarioSummary(
                n_worlds=4,
                mode_probs={MODE_FULLY_WRONG: 0.25, MODE_PARTIALLY_WRONG: 0.5,
                            MODE_RIGHT: 0.25},
                field_failure_rates={"date": 0.0}, partial_attribution={})
        # rate contradicts the identity (0.9 != 1.0 * 0.5)
        with pytest.raises(ValueError, match="contradicts"):
            ScenarioSummary(
                n_worlds=4,
                mode_probs={MODE_FULLY_WRONG: 0.25, MODE_PARTIALLY_WRONG: 0.5,
                            MODE_RIGHT: 0.25},
                field_failure_rates={"date": 0.9},
                partial_attribution={"date": 1.0})
        # the consistent construction is accepted
        ok = ScenarioSummary(
            n_worlds=4,
            mode_probs={MODE_FULLY_WRONG: 0.25, MODE_PARTIALLY_WRONG: 0.5,
                        MODE_RIGHT: 0.25},
            field_failure_rates={"date": 0.5},
            partial_attribution={"date": 1.0})
        assert ok.field_failure_rates["date"] == 0.5

    # Evaluator r1 (PR #54): aggregate() must ENFORCE the WorldOutcome
    # invariant (wrong_fields iff partially_wrong), not assume it — a
    # summary quietly counting field failures from `right`/`fully_wrong`
    # outcomes would contradict its own mode_probs.
    @pytest.mark.parametrize("mode", [MODE_RIGHT, MODE_FULLY_WRONG])
    def test_wrong_fields_outside_partially_wrong_fails_loud(self, mode):
        # aggregate() defense against a forged outcome (bypasses the
        # WorldOutcome construction check tested in TestWorldOutcome).
        with pytest.raises(ValueError, match="only partially_wrong"):
            aggregate([_forge_outcome(mode, ("date",))], ["date"])

    def test_partially_wrong_without_fields_fails_loud(self):
        with pytest.raises(ValueError, match="empty wrong_fields"):
            aggregate([_forge_outcome(MODE_PARTIALLY_WRONG, ())], ["date"])

    def test_duplicate_wrong_fields_fail_loud(self):
        # Evaluator r2 (PR #54): a duplicated field name would be counted
        # twice, pushing field_failure_rates / partial_attribution past
        # 1.0 — impossible probabilities in audit evidence. wrong_fields
        # is a set of names, never a multiset. (Forged outcome: aggregate
        # defends even when WorldOutcome's own dedup check was bypassed.)
        with pytest.raises(ValueError, match="duplicate wrong_fields"):
            aggregate(
                [_forge_outcome(MODE_PARTIALLY_WRONG, ("date", "date"))],
                ["date"],
            )


# --- CostMatrix: explicit, complete, fail-loud --------------------------------

class TestCostMatrix:
    def test_valid_matrix_constructs(self):
        matrix = CostMatrix(costs=DRAFT_COSTS)
        assert matrix.actions == (
            "surface_confirmed", "surface_likely", "hold", "flag_disputed",
        )
        assert matrix.costs["hold"]["right"] == 15.0

    def test_missing_cell_fails_loud(self):
        # A hole in the value system must never be silently read as zero
        # cost (spec §5) — drop one mode from one action and construction
        # must refuse.
        broken = {a: dict(row) for a, row in DRAFT_COSTS.items()}
        del broken["hold"]["right"]
        with pytest.raises(ValueError, match="missing cost cell"):
            CostMatrix(costs=broken)

    def test_unknown_mode_fails_loud(self):
        broken = {a: dict(row) for a, row in DRAFT_COSTS.items()}
        broken["hold"]["sideways"] = 1
        with pytest.raises(ValueError, match="unknown outcome mode"):
            CostMatrix(costs=broken)

    @pytest.mark.parametrize("bad", [-1, float("inf"), float("nan"), "5", True])
    def test_bad_cost_value_fails_loud(self, bad):
        broken = {a: dict(row) for a, row in DRAFT_COSTS.items()}
        broken["hold"]["right"] = bad
        with pytest.raises(ValueError):
            CostMatrix(costs=broken)

    def test_empty_matrix_fails_loud(self):
        with pytest.raises(ValueError, match="non-empty"):
            CostMatrix(costs={})

    def test_non_mapping_row_fails_loud(self):
        with pytest.raises(ValueError, match="must map"):
            CostMatrix(costs={"hold": [1, 2, 3]})

    def test_from_json_round_trip(self):
        matrix = CostMatrix.from_json(json.dumps(DRAFT_COSTS))
        assert matrix == CostMatrix(costs=DRAFT_COSTS)

    def test_from_json_invalid_json_fails_loud(self):
        with pytest.raises(ValueError, match="invalid JSON"):
            CostMatrix.from_json("{not json")

    def test_from_json_duplicate_action_key_fails_loud(self):
        # Evaluator r3 (PR #54): plain json.loads is last-wins on
        # duplicate keys — in the trust-path value-system config a
        # duplicated action or mode cell would silently override a
        # ratified value. Both nesting levels must refuse.
        doc = (
            '{"hold": {"fully_wrong": 2, "partially_wrong": 10, "right": 15},'
            ' "hold": {"fully_wrong": 0, "partially_wrong": 0, "right": 0}}'
        )
        with pytest.raises(ValueError, match="duplicate JSON key"):
            CostMatrix.from_json(doc)

    def test_from_json_duplicate_mode_key_fails_loud(self):
        doc = (
            '{"hold": {"fully_wrong": 2, "partially_wrong": 10,'
            ' "right": 15, "right": 0}}'
        )
        with pytest.raises(ValueError, match="duplicate JSON key"):
            CostMatrix.from_json(doc)

    def test_from_json_non_object_fails_loud(self):
        with pytest.raises(ValueError, match="top level"):
            CostMatrix.from_json("[1, 2]")

    def test_later_mutation_of_input_dict_cannot_alter_matrix(self):
        source = {a: dict(row) for a, row in DRAFT_COSTS.items()}
        matrix = CostMatrix(costs=source)
        source["hold"]["right"] = 9999
        assert matrix.costs["hold"]["right"] == 15.0

    def test_constructed_matrix_is_deeply_immutable(self):
        # Evaluator r1 (PR #54): a frozen dataclass over mutable nested
        # dicts let `matrix.costs[a][m] = x` (or del) bypass every
        # validation guarantee post-construction. Both nesting levels must
        # refuse writes for the object's whole lifetime.
        matrix = CostMatrix(costs=DRAFT_COSTS)
        with pytest.raises(TypeError):
            matrix.costs["hold"]["right"] = 0
        with pytest.raises(TypeError):
            del matrix.costs["hold"]["right"]
        with pytest.raises(TypeError):
            matrix.costs["hold"] = {}
        with pytest.raises(TypeError):
            del matrix.costs["hold"]
        # And the guarantee held: nothing changed.
        assert matrix.costs["hold"]["right"] == 15.0
        assert set(matrix.actions) == set(DRAFT_COSTS)


# --- expected_loss / decide: golden arithmetic --------------------------------

class TestExpectedLossAndDecide:
    # Worked example 1 from ONE_LIVE_COST_MATRIX_DRAFT_v1.md §4:
    # P = {fully_wrong: 0.05, partially_wrong: 0.15, right: 0.80}
    #   surface_confirmed: 0.05*100 + 0.15*6 + 0.80*0  = 5.00+0.90+0.00 = 5.90
    #   surface_likely:    0.05*40  + 0.15*4 + 0.80*1  = 2.00+0.60+0.80 = 3.40
    #   hold:              0.05*2   + 0.15*10 + 0.80*15 = 0.10+1.50+12.0 = 13.60
    #   flag_disputed:     0.05*3   + 0.15*6 + 0.80*8  = 0.15+0.90+6.40 = 7.45
    PROBS_1 = {"fully_wrong": 0.05, "partially_wrong": 0.15, "right": 0.80}
    # Worked example 2 (§5): P = {0.005, 0.035, 0.96}
    #   surface_confirmed: 0.5+0.21+0     = 0.710
    #   surface_likely:    0.2+0.14+0.96  = 1.300
    #   hold:              0.01+0.35+14.4 = 14.760
    #   flag_disputed:     0.015+0.21+7.68 = 7.905
    PROBS_2 = {"fully_wrong": 0.005, "partially_wrong": 0.035, "right": 0.96}

    def test_expected_loss_golden(self):
        matrix = CostMatrix(costs=DRAFT_COSTS)
        assert expected_loss("surface_confirmed", self.PROBS_1, matrix) == pytest.approx(5.90, abs=APPROX)
        assert expected_loss("surface_likely", self.PROBS_1, matrix) == pytest.approx(3.40, abs=APPROX)
        assert expected_loss("hold", self.PROBS_1, matrix) == pytest.approx(13.60, abs=APPROX)
        assert expected_loss("flag_disputed", self.PROBS_1, matrix) == pytest.approx(7.45, abs=APPROX)

    def test_decide_example_1_chooses_quiet_framing(self):
        matrix = CostMatrix(costs=DRAFT_COSTS)
        record = decide(list(matrix.actions), self.PROBS_1, matrix)
        assert record.chosen == "surface_likely"
        assert record.expected_losses["surface_likely"] == pytest.approx(3.40, abs=APPROX)
        # Full arithmetic is returned, not just the winner (spec §5:
        # auditable rationale): each term is P(mode)*cost.
        assert record.terms["surface_confirmed"]["fully_wrong"] == pytest.approx(5.00, abs=APPROX)
        assert record.terms["hold"]["right"] == pytest.approx(12.00, abs=APPROX)
        assert sum(record.terms["flag_disputed"].values()) == pytest.approx(
            record.expected_losses["flag_disputed"], abs=APPROX
        )

    def test_decide_example_2_commits_to_confirmed(self):
        matrix = CostMatrix(costs=DRAFT_COSTS)
        record = decide(list(matrix.actions), self.PROBS_2, matrix)
        assert record.chosen == "surface_confirmed"
        assert record.expected_losses["surface_confirmed"] == pytest.approx(0.710, abs=APPROX)
        assert record.expected_losses["flag_disputed"] == pytest.approx(7.905, abs=APPROX)

    def test_tie_breaks_to_earliest_caller_action(self):
        # Two identically-priced actions: the winner is the first in the
        # caller's order, deterministically — flip the order, flip the win.
        matrix = CostMatrix(costs={
            "a": {"fully_wrong": 1, "partially_wrong": 1, "right": 1},
            "b": {"fully_wrong": 1, "partially_wrong": 1, "right": 1},
        })
        probs = {"fully_wrong": 0.2, "partially_wrong": 0.3, "right": 0.5}
        assert decide(["a", "b"], probs, matrix).chosen == "a"
        assert decide(["b", "a"], probs, matrix).chosen == "b"

    def test_unpriced_action_fails_loud(self):
        matrix = CostMatrix(costs=DRAFT_COSTS)
        with pytest.raises(ValueError, match="no row"):
            expected_loss("promote_everything", self.PROBS_1, matrix)
        with pytest.raises(ValueError, match="no row"):
            decide(["hold", "promote_everything"], self.PROBS_1, matrix)

    def test_empty_or_duplicate_actions_fail_loud(self):
        matrix = CostMatrix(costs=DRAFT_COSTS)
        with pytest.raises(ValueError, match="at least one"):
            decide([], self.PROBS_1, matrix)
        with pytest.raises(ValueError, match="duplicates"):
            decide(["hold", "hold"], self.PROBS_1, matrix)

    @pytest.mark.parametrize("bad_probs", [
        {"fully_wrong": 0.5, "partially_wrong": 0.2, "right": 0.2},  # sums 0.9
        {"fully_wrong": 0.5, "right": 0.5},                          # missing mode
        {"fully_wrong": 0.5, "partially_wrong": 0.2, "right": 0.2,
         "sideways": 0.1},                                           # unknown mode
        {"fully_wrong": -0.1, "partially_wrong": 0.3, "right": 0.8}, # negative
    ])
    def test_malformed_mode_probs_fail_loud(self, bad_probs):
        matrix = CostMatrix(costs=DRAFT_COSTS)
        with pytest.raises(ValueError):
            expected_loss("hold", bad_probs, matrix)

    def test_decision_record_is_deeply_immutable(self):
        # Evaluator r2 (PR #54): a decision record is audit evidence, and
        # evidence that can be edited after the fact is not evidence —
        # same discipline as CostMatrix, both nesting levels.
        matrix = CostMatrix(costs=DRAFT_COSTS)
        record = decide(
            ["hold", "surface_likely"],
            {"fully_wrong": 0.2, "partially_wrong": 0.3, "right": 0.5},
            matrix,
        )
        with pytest.raises(TypeError):
            record.expected_losses["hold"] = 0.0
        with pytest.raises(TypeError):
            record.terms["hold"]["right"] = 0.0
        with pytest.raises(TypeError):
            record.terms["hold"] = {}
        with pytest.raises(TypeError):
            record.mode_probs["right"] = 1.0

    def test_forged_inconsistent_record_fails_loud(self):
        # Evaluator r3 (PR #54): the public constructor must not be a way
        # to manufacture bogus audit evidence — a record whose chosen
        # action, totals, and terms contradict each other fails at
        # construction.
        from worker.convergence.decisions import DecisionRecord

        # A valid matrix to satisfy the (last) matrix-verify field; each
        # case below trips an EARLIER consistency check, so the matrix's
        # exact values are irrelevant here.
        mtx = CostMatrix(costs=DRAFT_COSTS)
        probs = {"fully_wrong": 0.0, "partially_wrong": 0.0, "right": 1.0}
        good_terms = {"hold": {"fully_wrong": 0.0, "partially_wrong": 0.0,
                               "right": 15.0}}
        # chosen not among the actions
        with pytest.raises(ValueError, match="not among"):
            DecisionRecord(chosen="ghost", expected_losses={"hold": 15.0},
                           terms=good_terms, mode_probs=probs, matrix=mtx)
        # total contradicts its own terms row
        with pytest.raises(ValueError, match="sum of its terms"):
            DecisionRecord(chosen="hold", expected_losses={"hold": 1.0},
                           terms=good_terms, mode_probs=probs, matrix=mtx)
        # a terms row missing a mode
        with pytest.raises(ValueError, match="exactly"):
            DecisionRecord(chosen="hold", expected_losses={"hold": 15.0},
                           terms={"hold": {"right": 15.0}}, mode_probs=probs,
                           matrix=mtx)
        # chosen does not achieve the minimum
        with pytest.raises(ValueError, match="minimum expected loss"):
            DecisionRecord(
                chosen="hold",
                expected_losses={"hold": 15.0, "flag_disputed": 8.0},
                terms={
                    "hold": {"fully_wrong": 0.0, "partially_wrong": 0.0,
                             "right": 15.0},
                    "flag_disputed": {"fully_wrong": 0.0,
                                      "partially_wrong": 0.0, "right": 8.0},
                },
                mode_probs=probs,
                matrix=mtx,
            )

    def test_nonzero_term_under_zero_probability_mode_fails_loud(self):
        # Evaluator r7 (PR #54): terms[action][mode] = P(mode) * cost, so a
        # zero-probability mode forces a zero term — a nonzero term there is
        # impossible under any finite cost matrix. This is the COMPLETE
        # term-vs-probability consistency condition (a positive P(mode)
        # admits any non-negative term via cost = term / P(mode)).
        from worker.convergence.decisions import DecisionRecord

        # P(fully_wrong)=0 but hold's fully_wrong term is 100 (row still
        # sums to its stated total, so only the r7 check catches it).
        with pytest.raises(ValueError, match="zero-probability mode forces"):
            DecisionRecord(
                chosen="hold",
                expected_losses={"hold": 115.0},
                terms={"hold": {"fully_wrong": 100.0, "partially_wrong": 0.0,
                                "right": 15.0}},
                mode_probs={"fully_wrong": 0.0, "partially_wrong": 0.0,
                            "right": 1.0},
                matrix=CostMatrix(costs=DRAFT_COSTS),
            )

    def test_record_with_malformed_mode_probs_fails_loud(self):
        # Evaluator r5 (PR #54): the record CARRIES the distribution its
        # arithmetic was computed under, so a forged record with malformed
        # mode_probs (missing mode / doesn't sum to 1 / NaN) must fail.
        from worker.convergence.decisions import DecisionRecord

        good_terms = {"hold": {"fully_wrong": 0.0, "partially_wrong": 0.0,
                               "right": 15.0}}
        mtx = CostMatrix(costs=DRAFT_COSTS)
        with pytest.raises(ValueError, match="mode_probs"):
            DecisionRecord(chosen="hold", expected_losses={"hold": 15.0},
                           terms=good_terms, matrix=mtx,
                           mode_probs={"fully_wrong": 0.5, "right": 0.5})
        with pytest.raises(ValueError, match="sum to 1"):
            DecisionRecord(chosen="hold", expected_losses={"hold": 15.0},
                           terms=good_terms, matrix=mtx,
                           mode_probs={"fully_wrong": 0.2, "partially_wrong": 0.2,
                                       "right": 0.2})

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
    def test_non_finite_or_negative_audit_arithmetic_fails_loud(self, bad):
        # Evaluator r4 (PR #54): NaN slips past `abs(nan) > eps` (all NaN
        # comparisons are false), so a fabricated record carrying NaN/inf/
        # negative losses would look internally consistent. Per-cell
        # finite-non-negative validation closes that hole — in BOTH the
        # totals and the terms cells.
        from worker.convergence.decisions import DecisionRecord

        probs = {"fully_wrong": 0.0, "partially_wrong": 0.0, "right": 1.0}
        # NaN/inf trip the finite check; -1.0 trips the non-negative check —
        # both messages contain "finite".
        with pytest.raises(ValueError, match="finite"):
            DecisionRecord(
                chosen="hold", expected_losses={"hold": bad},
                terms={"hold": {"fully_wrong": 0.0, "partially_wrong": 0.0,
                                "right": bad}},
                mode_probs=probs, matrix=CostMatrix(costs=DRAFT_COSTS))

    @pytest.mark.parametrize("tiny_bad", [-1e-12, 1.0 + 1e-12])
    def test_tiny_out_of_range_prob_rejected_exactly(self, tiny_bad):
        # Per-probability bounds are EXACT (sl.py component-bound
        # convention, PR #51 r7): dust tolerance lives in the SUM check
        # only. A -1e-12 probability is a caller normalization bug.
        matrix = CostMatrix(costs=DRAFT_COSTS)
        rest = (1.0 - tiny_bad) / 2 if tiny_bad < 0 else 0.0
        probs = {
            "fully_wrong": tiny_bad,
            "partially_wrong": rest,
            "right": (1.0 - tiny_bad - rest),
        }
        with pytest.raises(ValueError, match="outside \\[0, 1\\]"):
            expected_loss("hold", probs, matrix)

    @pytest.mark.parametrize("not_a_mapping", [["a", "b"], 5, "probs", None])
    def test_non_mapping_mode_probs_gives_valueerror(self, not_a_mapping):
        # Evaluator r4 nit (PR #54): a non-mapping caller must get the
        # module's explicit ValueError, not a raw TypeError leaking from
        # set().
        matrix = CostMatrix(costs=DRAFT_COSTS)
        with pytest.raises(ValueError, match="must be a mapping"):
            expected_loss("hold", not_a_mapping, matrix)


# --- VoI: golden arithmetic ----------------------------------------------------

class TestVoi:
    # Compact 2-action matrix for hand arithmetic:
    #   show: fw=10 pw=4 r=0     hold: fw=0 pw=1 r=5
    SMALL = {
        "show": {"fully_wrong": 10, "partially_wrong": 4, "right": 0},
        "hold": {"fully_wrong": 0, "partially_wrong": 1, "right": 5},
    }
    # Prior P = {fw 0.4, pw 0.0, r 0.6}:
    #   EL(show) = 0.4*10 + 0 + 0     = 4.0
    #   EL(hold) = 0     + 0 + 0.6*5  = 3.0   -> prior best: hold, 3.0
    PRIOR = {"fully_wrong": 0.4, "partially_wrong": 0.0, "right": 0.6}
    # A perfectly-resolving fetch: branch fw (p 0.4) -> best is hold at 0;
    # branch r (p 0.6) -> best is show at 0. Posterior expected loss = 0.
    PERFECT = [
        (0.4, {"fully_wrong": 1.0, "partially_wrong": 0.0, "right": 0.0}),
        (0.6, {"fully_wrong": 0.0, "partially_wrong": 0.0, "right": 1.0}),
    ]

    def test_voi_golden(self):
        # gross = prior(3.0) - posterior(0.0) = 3.0; net = 3.0 - 1.0 = 2.0.
        record = voi(self.PRIOR, self.PERFECT, 1.0, CostMatrix(costs=self.SMALL))
        assert record.prior_expected_loss == pytest.approx(3.0, abs=APPROX)
        assert record.prior_decision.chosen == "hold"
        assert record.posterior_expected_loss == pytest.approx(0.0, abs=APPROX)
        assert record.gross_value == pytest.approx(3.0, abs=APPROX)
        assert record.net_value == pytest.approx(2.0, abs=APPROX)
        assert record.fetch_worth_it is True
        # Per-branch decisions are preserved with their full arithmetic.
        (p_fw, dec_fw), (p_r, dec_r) = record.posterior_decisions
        assert (p_fw, dec_fw.chosen) == (0.4, "hold")
        assert (p_r, dec_r.chosen) == (0.6, "show")

    def test_break_even_fetch_is_not_bought(self):
        # Spec §5 + cost discipline: spend follows decision value; net must
        # be STRICTLY positive. gross 3.0 at cost 3.0 -> net 0.0 -> no.
        record = voi(self.PRIOR, self.PERFECT, 3.0, CostMatrix(costs=self.SMALL))
        assert record.net_value == pytest.approx(0.0, abs=APPROX)
        assert record.fetch_worth_it is False

    def test_voi_matches_draft_doc_worked_example(self):
        # ONE_LIVE_COST_MATRIX_DRAFT_v1.md §6: from example 1's position
        # (prior best surface_likely at 3.40), a perfect fetch lands at
        # 0.05*2 (hold) + 0.15*4 (surface_likely) + 0.80*0 (confirmed)
        # = 0.70. Gross 3.40-0.70 = 2.70; at fetch cost 0.5, net = 2.20.
        matrix = CostMatrix(costs=DRAFT_COSTS)
        prior = {"fully_wrong": 0.05, "partially_wrong": 0.15, "right": 0.80}
        perfect = [
            (0.05, {"fully_wrong": 1.0, "partially_wrong": 0.0, "right": 0.0}),
            (0.15, {"fully_wrong": 0.0, "partially_wrong": 1.0, "right": 0.0}),
            (0.80, {"fully_wrong": 0.0, "partially_wrong": 0.0, "right": 1.0}),
        ]
        record = voi(prior, perfect, 0.5, matrix)
        assert record.prior_expected_loss == pytest.approx(3.40, abs=APPROX)
        assert record.posterior_expected_loss == pytest.approx(0.70, abs=APPROX)
        assert record.gross_value == pytest.approx(2.70, abs=APPROX)
        assert record.net_value == pytest.approx(2.20, abs=APPROX)
        assert record.fetch_worth_it is True

    def test_uninformative_fetch_is_worthless(self):
        # A fetch whose every branch reproduces the prior teaches nothing:
        # posterior = prior best (3.0), gross = 0, net = -cost.
        record = voi(
            self.PRIOR, [(1.0, self.PRIOR)], 0.25, CostMatrix(costs=self.SMALL)
        )
        assert record.gross_value == pytest.approx(0.0, abs=APPROX)
        assert record.net_value == pytest.approx(-0.25, abs=APPROX)
        assert record.fetch_worth_it is False

    def test_branch_probabilities_must_sum_to_one(self):
        with pytest.raises(ValueError, match="sum to 1"):
            voi(
                self.PRIOR,
                [(0.4, self.PERFECT[0][1]), (0.4, self.PERFECT[1][1])],
                1.0,
                CostMatrix(costs=self.SMALL),
            )

    def test_empty_scenarios_fail_loud(self):
        with pytest.raises(ValueError, match="at least one posterior"):
            voi(self.PRIOR, [], 1.0, CostMatrix(costs=self.SMALL))

    def test_incoherent_posterior_scenarios_rejected(self):
        # Evaluator r9 (PR #54): the branch-weighted mixture of posteriors
        # must reproduce the current belief (law of total probability). A
        # set whose branches sum to 1 but average to a DIFFERENT belief is
        # not a valid refinement — VoI over it is meaningless and a
        # spend-gating primitive must refuse it.
        # PRIOR = {fw 0.4, pw 0, r 0.6}; this mixture averages to
        # {fw 1.0, r 0.0} != PRIOR though branch probs sum to 1.
        incoherent = [
            (1.0, {"fully_wrong": 1.0, "partially_wrong": 0.0, "right": 0.0}),
        ]
        with pytest.raises(ValueError, match="Incoherent posterior"):
            voi(self.PRIOR, incoherent, 1.0, CostMatrix(costs=self.SMALL))

    def test_voi_record_stores_fetch_cost(self):
        # Evaluator r9 (PR #54): fetch_cost is carried so net is
        # recomputable (net == gross - fetch_cost).
        record = voi(self.PRIOR, self.PERFECT, 1.0, CostMatrix(costs=self.SMALL))
        assert record.fetch_cost == 1.0
        assert record.net_value == pytest.approx(
            record.gross_value - record.fetch_cost, abs=APPROX
        )

    @pytest.mark.parametrize("bad_cost", [-1.0, float("inf"), float("nan"), "1"])
    def test_bad_fetch_cost_fails_loud(self, bad_cost):
        with pytest.raises(ValueError, match="fetch_cost"):
            voi(self.PRIOR, self.PERFECT, bad_cost, CostMatrix(costs=self.SMALL))

    def test_forged_voi_record_fails_loud(self):
        # Evaluator r5 (PR #54): VoiRecord is audit evidence — its public
        # constructor must reject internally contradictory records.
        from worker.convergence.decisions import VoiRecord

        matrix = CostMatrix(costs=self.SMALL)
        good = voi(self.PRIOR, self.PERFECT, 1.0, matrix)  # net 2.0, worth-it
        # net < 0 marked worth-it: the contradiction the field exists to bar.
        # (fetch_cost = gross - net keeps the arithmetic self-consistent so
        # ONLY the fetch_worth_it check fires.)
        with pytest.raises(ValueError, match="fetch_worth_it"):
            _mk_voi(
                prior_decision=good.prior_decision,
                posterior_decisions=good.posterior_decisions,
                prior_expected_loss=good.prior_expected_loss,
                posterior_expected_loss=good.posterior_expected_loss,
                fetch_cost=good.gross_value + 1.0,
                gross_value=good.gross_value,
                net_value=-1.0, fetch_worth_it=True,
            )
        # gross must equal prior - posterior.
        with pytest.raises(ValueError, match="does not equal"):
            _mk_voi(
                prior_decision=good.prior_decision,
                posterior_decisions=good.posterior_decisions,
                prior_expected_loss=3.0, posterior_expected_loss=0.0,
                fetch_cost=1.0,
                gross_value=99.0, net_value=98.0, fetch_worth_it=True,
            )
        # NaN loss field.
        with pytest.raises(ValueError, match="finite"):
            _mk_voi(
                prior_decision=good.prior_decision,
                posterior_decisions=good.posterior_decisions,
                prior_expected_loss=float("nan"), posterior_expected_loss=0.0,
                fetch_cost=1.0,
                gross_value=0.0, net_value=0.0, fetch_worth_it=False,
            )
        # branch probabilities that do not sum to 1.
        bad_branches = (good.posterior_decisions[0],)  # only one branch, p=0.4
        with pytest.raises(ValueError, match="sum to 1"):
            _mk_voi(
                prior_decision=good.prior_decision,
                posterior_decisions=bad_branches,
                prior_expected_loss=good.prior_expected_loss,
                posterior_expected_loss=good.posterior_expected_loss,
                fetch_cost=good.fetch_cost,
                gross_value=good.gross_value, net_value=good.net_value,
                fetch_worth_it=good.fetch_worth_it,
            )
        # net must equal gross - fetch_cost (r9): net<=gross alone is not
        # enough — the exact spend arithmetic must be recomputable.
        with pytest.raises(ValueError, match="gross_value - fetch_cost"):
            _mk_voi(
                prior_decision=good.prior_decision,
                posterior_decisions=good.posterior_decisions,
                prior_expected_loss=good.prior_expected_loss,
                posterior_expected_loss=good.posterior_expected_loss,
                fetch_cost=1.0, gross_value=good.gross_value,
                net_value=good.gross_value - 0.25,  # != gross - 1.0
                fetch_worth_it=True,
            )

    def test_voi_record_scalar_losses_must_match_embedded_decisions(self):
        # Evaluator r6 (PR #54): the scalar loss summaries must agree with
        # the DecisionRecords they summarize — otherwise the record holds
        # two contradictory representations of the same quantity.
        from worker.convergence.decisions import VoiRecord

        matrix = CostMatrix(costs=self.SMALL)
        good = voi(self.PRIOR, self.PERFECT, 1.0, matrix)
        # prior_expected_loss disagrees with prior_decision's chosen loss.
        # (Recompute a self-consistent gross/net so ONLY this check fires.)
        bad_prior = good.prior_expected_loss + 1.0
        with pytest.raises(ValueError, match="prior_decision's chosen loss"):
            _mk_voi(
                prior_decision=good.prior_decision,
                posterior_decisions=good.posterior_decisions,
                prior_expected_loss=bad_prior,
                posterior_expected_loss=good.posterior_expected_loss,
                fetch_cost=1.0,
                gross_value=bad_prior - good.posterior_expected_loss,
                net_value=bad_prior - good.posterior_expected_loss - 1.0,
                fetch_worth_it=(bad_prior - good.posterior_expected_loss - 1.0) > 0,
            )
        # posterior_expected_loss disagrees with the branch-weighted mixture.
        bad_post = good.posterior_expected_loss + 1.0
        with pytest.raises(ValueError, match="branch-weighted mixture"):
            _mk_voi(
                prior_decision=good.prior_decision,
                posterior_decisions=good.posterior_decisions,
                prior_expected_loss=good.prior_expected_loss,
                posterior_expected_loss=bad_post,
                fetch_cost=1.0,
                gross_value=good.prior_expected_loss - bad_post,
                net_value=good.prior_expected_loss - bad_post - 1.0,
                fetch_worth_it=(good.prior_expected_loss - bad_post - 1.0) > 0,
            )

    def test_forged_voi_record_incoherent_mixture_rejected(self):
        # Evaluator r10 (PR #54): voi() rejects incoherent scenario sets,
        # but a forged VoiRecord bypasses voi() — the RECORD constructor
        # must also verify its posterior mixture reproduces the prior
        # belief. Here the single branch's mode_probs ({fw:1}) do not
        # average back to PRIOR ({fw 0.4, ...}), though every scalar check
        # is self-consistent.
        from worker.convergence.decisions import VoiRecord

        matrix = CostMatrix(costs=self.SMALL)
        actions = list(matrix.actions)
        prior_dec = decide(actions, self.PRIOR, matrix)
        branch_dec = decide(
            actions,
            {"fully_wrong": 1.0, "partially_wrong": 0.0, "right": 0.0},
            matrix,
        )
        p_loss = prior_dec.expected_losses[prior_dec.chosen]
        b_loss = branch_dec.expected_losses[branch_dec.chosen]
        gross = p_loss - b_loss
        with pytest.raises(ValueError, match="posterior mixture"):
            _mk_voi(
                prior_decision=prior_dec,
                posterior_decisions=((1.0, branch_dec),),  # mixture = {fw:1}
                prior_expected_loss=p_loss,
                posterior_expected_loss=b_loss,
                fetch_cost=1.0,
                gross_value=gross,
                net_value=gross - 1.0,
                fetch_worth_it=(gross - 1.0) > 0,
            )

    def test_forged_voi_record_mismatched_action_set_rejected(self):
        # Evaluator r11 (PR #54): every embedded decision must be over the
        # same action set as the prior, or the VoI compares different option
        # sets before vs after the fetch. (The same-cost-matrix half is now
        # fully closed by self-verifying matrix storage — r13/r14,
        # test_forged_voi_record_cross_matrix_rejected — not deferred.)
        from worker.convergence.decisions import VoiRecord

        matrix = CostMatrix(costs=self.SMALL)          # actions: show, hold
        actions = list(matrix.actions)
        prior_dec = decide(actions, self.PRIOR, matrix)
        # A branch decided over a DIFFERENT action set (only "hold").
        odd = decide(["hold"], self.PRIOR, matrix)
        p_loss = prior_dec.expected_losses[prior_dec.chosen]
        o_loss = odd.expected_losses[odd.chosen]
        gross = p_loss - o_loss
        with pytest.raises(ValueError, match="tie-break order"):
            _mk_voi(
                prior_decision=prior_dec,
                posterior_decisions=((1.0, odd),),
                prior_expected_loss=p_loss,
                posterior_expected_loss=o_loss,
                fetch_cost=0.0,
                gross_value=gross,
                net_value=gross,
                fetch_worth_it=gross > 0,
            )

    def test_forged_voi_record_different_tiebreak_order_rejected(self):
        # Evaluator r15 (PR #54): the DECISION's action order is its
        # tie-break policy (decide() breaks ties toward the earliest
        # action), independent of matrix.actions. Same actions + same matrix
        # but a different tie-break order is a different policy, and a set
        # comparison would have missed it — the check compares ordered
        # action tuples.
        from worker.convergence.decisions import VoiRecord

        matrix = CostMatrix(costs=self.SMALL)          # show, hold
        prior_dec = decide(["show", "hold"], self.PRIOR, matrix)
        # Same matrix, same action SET, DIFFERENT tie-break order.
        branch_dec = decide(["hold", "show"], self.PRIOR, matrix)
        assert tuple(prior_dec.expected_losses) != tuple(branch_dec.expected_losses)
        p_loss = prior_dec.expected_losses[prior_dec.chosen]
        b_loss = branch_dec.expected_losses[branch_dec.chosen]
        gross = p_loss - b_loss
        with pytest.raises(ValueError, match="tie-break order"):
            VoiRecord(
                prior_decision=prior_dec,
                posterior_decisions=((1.0, branch_dec),),
                prior_expected_loss=p_loss,
                posterior_expected_loss=b_loss,
                fetch_cost=0.0,
                gross_value=gross,
                net_value=gross,
                fetch_worth_it=gross > 0,
            )

    def test_forged_voi_record_cross_matrix_rejected(self):
        # Evaluator r13 (PR #54): the cross-matrix forgery — prior decided
        # under one value system, posterior under another — is closed by
        # SELF-VERIFYING matrix storage, not by construction privacy. Each
        # DecisionRecord carries its cost matrix (verified against its
        # terms), and VoiRecord rejects decisions under different matrices.
        # This replaces the r12 factory token, which was importable and so
        # convention-only.
        from worker.convergence.decisions import VoiRecord

        matrix_a = CostMatrix(costs=self.SMALL)
        matrix_b = CostMatrix(costs={
            "show": {"fully_wrong": 10, "partially_wrong": 4, "right": 0},
            "hold": {"fully_wrong": 0, "partially_wrong": 1, "right": 6},  # 5->6
        })
        actions = list(matrix_a.actions)
        prior_dec = decide(actions, self.PRIOR, matrix_a)
        branch_dec = decide(actions, self.PRIOR, matrix_b)  # DIFFERENT matrix
        p_loss = prior_dec.expected_losses[prior_dec.chosen]
        b_loss = branch_dec.expected_losses[branch_dec.chosen]
        gross = p_loss - b_loss
        with pytest.raises(ValueError, match="DIFFERENT cost matrix"):
            VoiRecord(
                prior_decision=prior_dec,
                posterior_decisions=((1.0, branch_dec),),  # coherent, 1 branch
                prior_expected_loss=p_loss,
                posterior_expected_loss=b_loss,
                fetch_cost=0.0,
                gross_value=gross,
                net_value=gross,
                fetch_worth_it=gross > 0,
            )
        # A genuine single-matrix voi() record still constructs fine.
        assert voi(self.PRIOR, self.PERFECT, 1.0, matrix_a).fetch_cost == 1.0

    def test_forged_voi_record_order_only_matrix_difference_rejected(self):
        # Evaluator r14 (PR #54): action ORDER is the deterministic
        # tie-break preference, and CostMatrix value-equality ignores key
        # order — so two numerically-identical matrices with different
        # action order are DIFFERENT policies. The same-matrix check must
        # compare order too.
        from worker.convergence.decisions import VoiRecord

        cells = self.SMALL
        matrix_a = CostMatrix(costs={"show": cells["show"], "hold": cells["hold"]})
        matrix_b = CostMatrix(costs={"hold": cells["hold"], "show": cells["show"]})
        # Same values, different action order -> value-equal but different
        # tie-break policy.
        assert matrix_a == matrix_b
        assert matrix_a.actions != matrix_b.actions
        actions = list(matrix_a.actions)
        prior_dec = decide(actions, self.PRIOR, matrix_a)
        branch_dec = decide(list(matrix_b.actions), self.PRIOR, matrix_b)
        p_loss = prior_dec.expected_losses[prior_dec.chosen]
        b_loss = branch_dec.expected_losses[branch_dec.chosen]
        gross = p_loss - b_loss
        with pytest.raises(ValueError, match="tie-break order|DIFFERENT cost"):
            VoiRecord(
                prior_decision=prior_dec,
                posterior_decisions=((1.0, branch_dec),),
                prior_expected_loss=p_loss,
                posterior_expected_loss=b_loss,
                fetch_cost=0.0,
                gross_value=gross,
                net_value=gross,
                fetch_worth_it=gross > 0,
            )

    def test_voi_record_outer_list_frozen_to_tuple(self):
        # Evaluator r5/r8 (PR #54): an OUTER list of (prob, decision) TUPLE
        # pairs is normalized to a tuple at construction (audit evidence is
        # immutable). Note the accepted shape precisely: each PAIR must
        # itself be a tuple — a list-pair is rejected, verified below — so
        # this only freezes the outer container, not inner pairs.
        from worker.convergence.decisions import VoiRecord

        matrix = CostMatrix(costs=self.SMALL)
        good = voi(self.PRIOR, self.PERFECT, 1.0, matrix)
        rebuilt = _mk_voi(
            prior_decision=good.prior_decision,
            posterior_decisions=list(good.posterior_decisions),  # outer LIST
            prior_expected_loss=good.prior_expected_loss,
            posterior_expected_loss=good.posterior_expected_loss,
            fetch_cost=good.fetch_cost,
            gross_value=good.gross_value, net_value=good.net_value,
            fetch_worth_it=good.fetch_worth_it,
        )
        assert isinstance(rebuilt.posterior_decisions, tuple)
        # A list-PAIR (rather than a tuple pair) is rejected — the accepted
        # shape is exactly (prob, DecisionRecord) tuples.
        bp, dec = good.posterior_decisions[0]
        with pytest.raises(ValueError, match="must be a"):
            _mk_voi(
                prior_decision=good.prior_decision,
                posterior_decisions=[[bp, dec]],  # list pair, not tuple
                prior_expected_loss=good.prior_expected_loss,
                posterior_expected_loss=good.posterior_expected_loss,
                fetch_cost=good.fetch_cost,
                gross_value=good.gross_value, net_value=good.net_value,
                fetch_worth_it=good.fetch_worth_it,
            )


# --- Shadow isolation (C2 invariant: zero product-path coupling) --------------

class TestShadowIsolation:
    # Same AST pattern as C1's suite (tests/test_convergence_sl.py),
    # extended to both C2 modules: stdlib plus the enumerated convergence-
    # package siblings only — never the pipeline, gate, or tooling.
    ALLOWED_PROJECT_IMPORTS = {
        "worker/convergence/scenarios.py": {"worker.convergence.sl"},
        "worker/convergence/decisions.py": {
            "worker.convergence.sl", "worker.convergence.scenarios",
        },
    }

    @pytest.mark.parametrize("rel_path", sorted(ALLOWED_PROJECT_IMPORTS))
    def test_module_imports_nothing_from_the_pipeline(self, rel_path):
        # Spec §11 C2: "Still shadow." The scenario/decision layer must be
        # pure stdlib plus its convergence-package siblings — no worker
        # pipeline, ai, api, or tools imports, no third-party packages.
        import worker.convergence.scenarios as scen
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(scen.__file__))))
        path = os.path.join(repo_root, *rel_path.split("/"))
        with open(path, encoding="utf-8") as f:  # r5 nit: no leaked fd
            source = f.read()
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
        allowed_project = self.ALLOWED_PROJECT_IMPORTS[rel_path]
        for mod in imported:
            if mod in allowed_project:
                continue
            top = mod.split(".")[0]
            assert top in sys.stdlib_module_names or mod == "__future__", (
                f"{rel_path} imports non-stdlib module {mod!r}; C2 must stay "
                f"standalone (spec §11: shadow, zero pipeline coupling)."
            )
            assert top not in ("worker", "ai", "api", "tools"), (
                f"{rel_path} imports project module {mod!r} outside the "
                f"allowed convergence substrate {sorted(allowed_project)!r}; "
                f"C2 forbids pipeline coupling."
            )

    def test_modes_vocabulary_is_shared_not_duplicated(self):
        # decisions.py must consume scenarios.MODES (one vocabulary, no
        # drift): the spec's three modes, in canonical order.
        from worker.convergence import decisions as dec_module
        assert dec_module.MODES is MODES
        assert MODES == ("fully_wrong", "partially_wrong", "right")

    def test_pipeline_does_not_import_the_convergence_modules(self):
        # Evaluator r12 nit (PR #54): the forward sweep proves convergence
        # imports nothing from the pipeline; this REVERSE sweep proves the
        # pipeline (worker/, api/ — excluding the convergence package
        # itself and tests) imports nothing FROM worker.convergence. Both
        # directions together make "shadow-only, zero coupling" mechanical.
        import os
        import worker.convergence.scenarios as scen
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(scen.__file__))))
        offenders = []
        for pkg in ("worker", "api"):
            pkg_dir = os.path.join(repo_root, pkg)
            if not os.path.isdir(pkg_dir):
                continue
            for dirpath, _dirs, files in os.walk(pkg_dir):
                # Skip the convergence package itself (siblings may import
                # siblings) and any test trees.
                rel = os.path.relpath(dirpath, repo_root).replace(os.sep, "/")
                if "convergence" in rel.split("/") or "test" in rel:
                    continue
                for fn in files:
                    if not fn.endswith(".py"):
                        continue
                    fp = os.path.join(dirpath, fn)
                    with open(fp, encoding="utf-8") as f:
                        tree = ast.parse(f.read())
                    for node in ast.walk(tree):
                        mods = []
                        if isinstance(node, ast.Import):
                            mods = [a.name for a in node.names]
                        elif isinstance(node, ast.ImportFrom):
                            mods = [node.module or ""]
                        if any(m == "worker.convergence"
                               or m.startswith("worker.convergence.")
                               for m in mods):
                            offenders.append(
                                os.path.relpath(fp, repo_root).replace(os.sep, "/")
                            )
        assert offenders == [], (
            f"pipeline module(s) import worker.convergence — C2 must stay "
            f"shadow (spec §11), imported by nothing in the product path: "
            f"{sorted(set(offenders))!r}"
        )
