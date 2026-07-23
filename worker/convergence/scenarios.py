"""Monte Carlo scenario scoring for the convergence model (C2, SHADOW-ONLY).

Greppable summary: pure-stdlib world sampling + outcome classification +
aggregation per docs/strategy/ONE_LIVE_CONVERGENCE_v1.md §5 ("Scenario
scoring") and §11 phase C2. Because SL opinions ARE Beta distributions
(spec §3/§5), plain Monte Carlo sampling is exact and trivial: each world
draws a probability from every field's Beta and every source's reliability
Beta, then draws boolean field truths. Worlds are classified into the
spec's three outcome modes — fully_wrong (event not real / cancelled),
partially_wrong (right event, wrong field — carrying WHICH field), right —
and aggregated into per-mode probabilities plus per-field failure
attribution ("failures cluster where", spec §5).

Replayability is a hard requirement (spec §9 rejected particle filters
precisely because "stochastic non-replayability" is an audit liability):
every sampling call takes an EXPLICIT caller-supplied integer seed with no
default, uses its own random.Random instance (never the process-global
RNG), and iterates fields/sources in sorted-name order so the same seed
yields the same worlds regardless of caller dict ordering.

Shadow posture (spec §11): zero product-path coupling. The only project
import is worker/convergence/sl.py (the C1 substrate); nothing here reads
or writes pipeline state, and the count-based gate keeps deciding until
the founder ratifies coupling at C5.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from random import Random
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

from worker.convergence.sl import PRIOR_WEIGHT, Opinion, trust_discount

# The three outcome modes of spec §5, in canonical order. These strings are
# the shared vocabulary between scenario aggregation and the expected-loss
# decision layer (worker/convergence/decisions.py imports them from here so
# the two modules can never drift apart on mode names).
MODE_FULLY_WRONG = "fully_wrong"
MODE_PARTIALLY_WRONG = "partially_wrong"
MODE_RIGHT = "right"
MODES = (MODE_FULLY_WRONG, MODE_PARTIALLY_WRONG, MODE_RIGHT)


@dataclass(frozen=True)
class World:
    """One sampled world (spec §5): a boolean truth per field plus the
    per-source reliability draw that produced it.

    `field_truths` maps field name -> "is this field's claimed value true in
    this world". `source_reliabilities` records the sampled reliability of
    each source in this world — kept on the world so failure clustering can
    be traced back to its cause ("failures cluster in worlds where the
    aggregator feed is stale", spec §5) during audit. Replay/audit
    material, so both mappings are made read-only at construction
    (evaluator r3, PR #54 — same discipline as the decision records).
    """

    field_truths: Mapping[str, bool]
    source_reliabilities: Mapping[str, float]

    def __post_init__(self) -> None:
        # A world is replay/audit material and is also fed straight into
        # classify_world, whose mode decision turns on field truth. Both
        # fields are validated at construction (evaluator r4, PR #54) so a
        # forged or mis-deserialized world fails loud HERE rather than
        # being silently coerced by truthiness downstream:
        #   - field_truths values must be REAL bools (a non-empty string
        #     like "False" is truthy and would classify a phantom as real);
        #   - source_reliabilities must be finite floats in [0, 1] (a
        #     probability outside the unit interval is malformed evidence).
        for name, truth in self.field_truths.items():
            if not isinstance(truth, bool):
                raise ValueError(
                    f"World.field_truths[{name!r}]={truth!r} must be a bool; "
                    f"a non-bool truth would be coerced by truthiness in "
                    f"classification, hiding malformed input (spec §5)."
                )
        for name, rel in self.source_reliabilities.items():
            if isinstance(rel, bool) or not isinstance(rel, (int, float)):
                raise ValueError(
                    f"World.source_reliabilities[{name!r}]={rel!r} must be a "
                    f"number in [0, 1]."
                )
            if not math.isfinite(rel) or not (0.0 <= rel <= 1.0):
                raise ValueError(
                    f"World.source_reliabilities[{name!r}]={rel!r} must be a "
                    f"finite reliability in [0, 1] (it is a sampled "
                    f"probability — outside the unit interval is malformed)."
                )
        object.__setattr__(
            self, "field_truths", MappingProxyType(dict(self.field_truths))
        )
        object.__setattr__(
            self,
            "source_reliabilities",
            MappingProxyType(dict(self.source_reliabilities)),
        )


@dataclass(frozen=True)
class WorldOutcome:
    """A classified world (spec §5): one of the three modes, and for
    partially_wrong the sorted tuple of WHICH fields were wrong.

    `wrong_fields` is empty for `right` (nothing wrong) and for
    `fully_wrong` (the event is not real, so per-field errors inside a
    phantom world are not separately attributable — spec §5 grades partial
    modes only within right-event worlds).

    A classified world is audit evidence, so the public constructor fails
    loud on impossible states and normalizes `wrong_fields` to an immutable
    tuple (evaluator r8, PR #54): the mode must be a real mode; wrong_fields
    must be unique strings; and the WorldOutcome invariant — wrong_fields
    non-empty iff partially_wrong — holds at construction, not merely when
    the outcome later reaches aggregate(). aggregate() keeps its own checks
    as defense in depth (against object.__new__ forgeries and because it
    ALSO enforces field-membership, which a lone outcome cannot know).
    """

    mode: str
    wrong_fields: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(
                f"WorldOutcome.mode={self.mode!r} must be one of {MODES!r}."
            )
        # A bare string/bytes is iterable and tuple("date") would silently
        # become ("d","a","t","e") — every char is a str and none repeat, so
        # it would sail past the checks below and corrupt field attribution
        # (evaluator r9, PR #54: a regression in the r8 fix itself). Reject
        # it before normalizing.
        if isinstance(self.wrong_fields, (str, bytes)):
            raise ValueError(
                f"WorldOutcome.wrong_fields must be a sequence of field-name "
                f"strings, not a bare {type(self.wrong_fields).__name__} "
                f"{self.wrong_fields!r} (which would be split into "
                f"characters)."
            )
        wf = tuple(self.wrong_fields)  # normalize list -> immutable tuple
        for name in wf:
            if not isinstance(name, str):
                raise ValueError(
                    f"WorldOutcome.wrong_fields must be field-name strings; "
                    f"got {name!r}."
                )
        if len(set(wf)) != len(wf):
            raise ValueError(
                f"WorldOutcome.wrong_fields has duplicate(s): {wf!r} — a "
                f"field is wrong once per world."
            )
        if self.mode == MODE_PARTIALLY_WRONG and not wf:
            raise ValueError(
                "WorldOutcome partially_wrong must name at least one wrong "
                "field (spec §5 carries WHICH field)."
            )
        if self.mode != MODE_PARTIALLY_WRONG and wf:
            raise ValueError(
                f"WorldOutcome mode {self.mode!r} carries wrong_fields {wf!r}; "
                f"only partially_wrong attributes per-field failures."
            )
        object.__setattr__(self, "wrong_fields", wf)


@dataclass(frozen=True)
class ScenarioSummary:
    """Aggregated scenario output (spec §5): P(mode) per mode plus
    per-field failure attribution.

    `mode_probs` always carries all three MODES keys. `field_failure_rates`
    is, per attributable field, the fraction of ALL worlds in which that
    field was wrong inside a real-event world. `partial_attribution` is the
    same count conditioned on partially_wrong worlds ("failures cluster
    where") — empty when no world was partially wrong, because the
    conditional is undefined there (fail-closed: an empty dict cannot be
    misread as "every field is fine"). Audit output, so the mappings are
    read-only at construction (evaluator r3, PR #54).
    """

    n_worlds: int
    mode_probs: Mapping[str, float]
    field_failure_rates: Mapping[str, float]
    partial_attribution: Mapping[str, float]

    def __post_init__(self) -> None:
        # aggregate() always produces a valid summary, but the public
        # constructor is a way to manufacture impossible audit evidence —
        # validated here so a forged summary fails loud (evaluator r4 nit,
        # PR #54).
        if isinstance(self.n_worlds, bool) or not isinstance(self.n_worlds, int) \
                or self.n_worlds <= 0:
            raise ValueError(
                f"ScenarioSummary.n_worlds={self.n_worlds!r} must be a "
                f"positive int."
            )
        if set(self.mode_probs) != set(MODES):
            raise ValueError(
                f"ScenarioSummary.mode_probs keys must be exactly {MODES!r}; "
                f"got {sorted(self.mode_probs)!r}."
            )
        for label, rates in (
            ("mode_probs", self.mode_probs),
            ("field_failure_rates", self.field_failure_rates),
            ("partial_attribution", self.partial_attribution),
        ):
            for key, val in rates.items():
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise ValueError(
                        f"ScenarioSummary.{label}[{key!r}]={val!r} must be a "
                        f"number."
                    )
                if not math.isfinite(val) or not (0.0 <= val <= 1.0):
                    raise ValueError(
                        f"ScenarioSummary.{label}[{key!r}]={val!r} must be a "
                        f"finite rate in [0, 1]."
                    )
        mode_total = sum(self.mode_probs.values())
        if abs(mode_total - 1.0) > 1e-6:
            raise ValueError(
                f"ScenarioSummary.mode_probs must sum to 1; got {mode_total!r}."
            )
        # Cross-field invariant (evaluator r5, PR #54). A field can only be
        # wrong INSIDE a partially_wrong world, so by construction
        #   field_failure_rates[f] = partial_attribution[f] * P(partially_wrong)
        # exactly (count_f/n = (count_f/n_partial) * (n_partial/n)), and both
        # collapse to zero when no world is partially wrong. Enforcing the
        # identity here makes a contradictory summary — e.g. a nonzero
        # failure rate with P(partially_wrong)=0, or a rate exceeding the
        # partial probability — unconstructable, not just unproduced.
        pw = self.mode_probs[MODE_PARTIALLY_WRONG]
        if self.partial_attribution:
            if pw <= 1e-9:
                raise ValueError(
                    f"ScenarioSummary: partial_attribution is non-empty but "
                    f"P(partially_wrong)={pw!r} — no partially_wrong world "
                    f"means no per-field attribution is defined."
                )
            if set(self.partial_attribution) != set(self.field_failure_rates):
                raise ValueError(
                    f"ScenarioSummary: partial_attribution fields "
                    f"{sorted(self.partial_attribution)!r} and "
                    f"field_failure_rates fields "
                    f"{sorted(self.field_failure_rates)!r} must match."
                )
            for f, rate in self.field_failure_rates.items():
                expected = self.partial_attribution[f] * pw
                if abs(rate - expected) > 1e-9:
                    raise ValueError(
                        f"ScenarioSummary: field_failure_rates[{f!r}]={rate!r} "
                        f"contradicts partial_attribution[{f!r}] * "
                        f"P(partially_wrong) = {expected!r} (a field's overall "
                        f"failure rate is exactly its partial-conditional rate "
                        f"times the partial probability)."
                    )
        else:
            if pw > 1e-9:
                raise ValueError(
                    f"ScenarioSummary: partial_attribution is empty but "
                    f"P(partially_wrong)={pw!r} > 0 — a partially_wrong world "
                    f"must carry its per-field attribution."
                )
            for f, rate in self.field_failure_rates.items():
                if rate > 1e-9:
                    raise ValueError(
                        f"ScenarioSummary: field_failure_rates[{f!r}]={rate!r} "
                        f"is nonzero while no world is partially wrong — a "
                        f"field can only fail inside a partially_wrong world."
                    )
        for name in ("mode_probs", "field_failure_rates", "partial_attribution"):
            object.__setattr__(
                self, name, MappingProxyType(dict(getattr(self, name)))
            )


def _require_seed(seed: object) -> int:
    """Validate the explicit replay seed (spec §9: stochastic
    non-replayability is an audit liability — every run must be exactly
    reproducible from its recorded seed). No default exists anywhere in
    this module; a missing seed is a TypeError at the call site."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(
            f"seed must be an int (explicit, caller-supplied — spec §9 "
            f"replayability); got {type(seed).__name__}: {seed!r}."
        )
    return seed


def _sample_probability(rng: Random, opinion: Opinion) -> float:
    """Draw one world-probability from the Beta distribution the opinion IS
    (spec §3: an opinion is "a probability distribution we can sample from
    (this is what makes the Monte Carlo pass in §5 nearly free)").

    Beta parameters follow the standard SL correspondence: alpha = r + W*a,
    beta = s + W*(1-a). Degenerate limits are handled deterministically
    rather than fabricated: a dogmatic opinion (u=0) is a point mass at b;
    alpha=0 (or beta=0) is the Beta limit concentrated at 0 (or 1).
    """
    if opinion.u <= 0.0:
        return opinion.b
    r, s = opinion.to_evidence()
    alpha = r + PRIOR_WEIGHT * opinion.a
    beta = s + PRIOR_WEIGHT * (1.0 - opinion.a)
    if alpha <= 0.0:
        return 0.0
    if beta <= 0.0:
        return 1.0
    return rng.betavariate(alpha, beta)


def sample_worlds(
    field_opinions: Mapping[str, Opinion],
    source_reliabilities: Mapping[str, Opinion],
    field_sources: Mapping[str, Sequence[str]],
    existence_field: str,
    n_worlds: int,
    *,
    seed: int,
) -> list[World]:
    """Sample `n_worlds` worlds for one claim (spec §5 "Scenario scoring":
    "sample thousands of worlds from the field Dirichlets and per-source
    reliability Betas. In each world, is the event real? Is the date
    right?").

    Per world: (1) draw each source's reliability from its reliability
    opinion's Beta; (2) for each field, discount the field's opinion by the
    sampled reliability of every source backing it (sl.trust_discount —
    distrust becomes uncertainty, never opposite belief); (3) draw the
    field's probability from the discounted opinion's Beta, then draw the
    boolean truth. Fields with no entry in `field_sources` are taken at
    face value (no discount).

    `seed` is keyword-only with NO default (spec §9: replayable or it does
    not run); `existence_field` names the field whose falsity means the
    event is not real (the fully_wrong mode of spec §5) and must be present
    in `field_opinions`. All structural errors fail loudly
    (docs/CODING_CONVENTIONS.md, fail-loud-on-misconfiguration).
    """
    _require_seed(seed)
    if not isinstance(n_worlds, int) or isinstance(n_worlds, bool) or n_worlds <= 0:
        raise ValueError(
            f"n_worlds must be a positive int; got {n_worlds!r} (zero worlds "
            f"would make every aggregate probability undefined)."
        )
    if not field_opinions:
        raise ValueError("field_opinions is empty: nothing to sample.")
    if existence_field not in field_opinions:
        raise ValueError(
            f"existence_field {existence_field!r} is not among the field "
            f"opinions {sorted(field_opinions)!r}; without it no world can "
            f"be classified fully_wrong vs partially_wrong (spec §5)."
        )
    unknown_fields = set(field_sources) - set(field_opinions)
    if unknown_fields:
        raise ValueError(
            f"field_sources references unknown field(s) "
            f"{sorted(unknown_fields)!r}; every key must name a field in "
            f"field_opinions."
        )
    for fname, sources in field_sources.items():
        # A bare string is iterable and would be silently consumed
        # character-by-character as "sources" (evaluator r6 nit, PR #54):
        # require an actual list/tuple sequence so a misconfiguration like
        # {"date": "venue_site"} fails loud with a clear message instead of
        # citing unknown single-character sources.
        if isinstance(sources, str) or not isinstance(sources, (list, tuple)):
            raise ValueError(
                f"field {fname!r} sources must be a list/tuple of source "
                f"names, not {type(sources).__name__}: {sources!r} (a bare "
                f"string would be iterated character by character)."
            )
        if len(set(sources)) != len(tuple(sources)):
            raise ValueError(
                f"field {fname!r} lists duplicate source(s) in {tuple(sources)!r}; "
                f"sampling applies trust_discount ONCE per entry, so a "
                f"repeated source would double-discount the field's opinion "
                f"and corrupt the trust math (the set()-based unknown-source "
                f"check below would hide it) — evaluator r4, PR #54. Each "
                f"source backs a field at most once."
            )
        unknown_sources = set(sources) - set(source_reliabilities)
        if unknown_sources:
            raise ValueError(
                f"field {fname!r} cites source(s) {sorted(unknown_sources)!r} "
                f"with no reliability opinion; a source without a measured "
                f"reliability cannot enter the sampler (spec §5/§7)."
            )
    referenced = {src for sources in field_sources.values() for src in sources}
    unused = set(source_reliabilities) - referenced
    if unused:
        raise ValueError(
            f"source_reliabilities contains source(s) {sorted(unused)!r} "
            f"referenced by no field in field_sources; an unused row would "
            f"still be sampled, silently shifting the RNG stream for every "
            f"subsequent draw — the same seed would yield different worlds "
            f"whenever an irrelevant source is added, which spec §9 "
            f"replayability forbids (evaluator r2, PR #54). Pass exactly "
            f"the sources the fields cite."
        )

    rng = Random(seed)
    # Sorted iteration order makes the draw sequence a pure function of the
    # seed, independent of caller dict insertion order (spec §9 replayability).
    source_names = sorted(source_reliabilities)
    field_names = sorted(field_opinions)

    worlds: list[World] = []
    for _ in range(n_worlds):
        reliab = {
            name: _sample_probability(rng, source_reliabilities[name])
            for name in source_names
        }
        truths: dict[str, bool] = {}
        for fname in field_names:
            opinion = field_opinions[fname]
            for src in field_sources.get(fname, ()):
                opinion = trust_discount(opinion, reliab[src])
            p = _sample_probability(rng, opinion)
            truths[fname] = rng.random() < p
        worlds.append(World(field_truths=truths, source_reliabilities=reliab))
    return worlds


def classify_world(world: World, existence_field: str) -> WorldOutcome:
    """Classify one world into the spec's three modes (spec §5):
    fully_wrong — the event doesn't exist / is cancelled ("user shows up to
    a dark room: trust catastrophe"); partially_wrong — right event, wrong
    field(s), carrying WHICH fields; right — everything true."""
    if existence_field not in world.field_truths:
        raise ValueError(
            f"existence_field {existence_field!r} is not among this world's "
            f"fields {sorted(world.field_truths)!r}; cannot classify (spec §5)."
        )
    if not world.field_truths[existence_field]:
        return WorldOutcome(mode=MODE_FULLY_WRONG, wrong_fields=())
    wrong = tuple(sorted(
        name for name, true in world.field_truths.items()
        if name != existence_field and not true
    ))
    if wrong:
        return WorldOutcome(mode=MODE_PARTIALLY_WRONG, wrong_fields=wrong)
    return WorldOutcome(mode=MODE_RIGHT, wrong_fields=())


def aggregate(
    outcomes: Sequence[WorldOutcome], field_names: Iterable[str]
) -> ScenarioSummary:
    """Aggregate classified worlds into the spec §5 output: "P(fully
    wrong), P(partially wrong, by mode)" plus per-field failure attribution
    ("failures cluster where").

    `field_names` lists the attributable (non-existence) fields, so fields
    that never failed still show an explicit 0.0 rate — absence of a row is
    never the encoding of "fine". An outcome citing a field outside
    `field_names` fails loudly: silently dropping it would corrupt the
    attribution the founder reads. Internally contradictory outcomes fail
    loudly the same way, in BOTH directions: non-empty `wrong_fields` on a
    `right` or `fully_wrong` outcome, and empty `wrong_fields` on a
    `partially_wrong` outcome, are each refused — the WorldOutcome
    invariant (wrong_fields iff partially_wrong) is enforced here, not
    assumed, because a summary quietly built from contradictory outcomes
    would be unauditable scenario evidence (evaluator r1, PR #54).
    """
    if not outcomes:
        raise ValueError(
            "aggregate() over zero outcomes: probabilities would be "
            "undefined (0/0); refusing to emit fabricated numbers."
        )
    fields = sorted(field_names)
    known = set(fields)
    mode_counts = {mode: 0 for mode in MODES}
    field_wrong_counts = {name: 0 for name in fields}
    n_partial = 0
    for outcome in outcomes:
        if outcome.mode not in mode_counts:
            raise ValueError(
                f"Unknown outcome mode {outcome.mode!r}; expected one of "
                f"{MODES!r} (spec §5)."
            )
        mode_counts[outcome.mode] += 1
        if outcome.mode == MODE_PARTIALLY_WRONG:
            if not outcome.wrong_fields:
                raise ValueError(
                    f"partially_wrong outcome with empty wrong_fields: the "
                    f"mode asserts a field failed but names none — an "
                    f"unattributable partial failure cannot enter the "
                    f"attribution (spec §5 carries WHICH field)."
                )
            if len(set(outcome.wrong_fields)) != len(outcome.wrong_fields):
                raise ValueError(
                    f"partially_wrong outcome names duplicate wrong_fields "
                    f"{outcome.wrong_fields!r}: a field is wrong once per "
                    f"world, and counting a duplicate would push failure "
                    f"rates past 1.0 — impossible probabilities in the "
                    f"audit evidence (evaluator r2, PR #54). wrong_fields "
                    f"is a set of names, never a multiset."
                )
            n_partial += 1
        elif outcome.wrong_fields:
            raise ValueError(
                f"{outcome.mode!r} outcome carries wrong_fields "
                f"{outcome.wrong_fields!r}: only partially_wrong attributes "
                f"per-field failures (WorldOutcome invariant); counting "
                f"these would contradict mode_probs in the same summary."
            )
        for name in outcome.wrong_fields:
            if name not in known:
                raise ValueError(
                    f"Outcome cites wrong field {name!r} not in field_names "
                    f"{fields!r}; refusing to silently drop it from the "
                    f"attribution."
                )
            field_wrong_counts[name] += 1
    n = len(outcomes)
    return ScenarioSummary(
        n_worlds=n,
        mode_probs={mode: mode_counts[mode] / n for mode in MODES},
        field_failure_rates={
            name: field_wrong_counts[name] / n for name in fields
        },
        partial_attribution=(
            {name: field_wrong_counts[name] / n_partial for name in fields}
            if n_partial else {}
        ),
    )


def run_scenarios(
    field_opinions: Mapping[str, Opinion],
    source_reliabilities: Mapping[str, Opinion],
    field_sources: Mapping[str, Sequence[str]],
    existence_field: str,
    n_worlds: int,
    *,
    seed: int,
) -> ScenarioSummary:
    """One-call scenario pass (spec §5): sample -> classify -> aggregate.

    Deterministic and replayable from (inputs, seed) alone — same seed,
    same summary, always (spec §9). Attribution covers every non-existence
    field, explicit zeros included.
    """
    worlds = sample_worlds(
        field_opinions,
        source_reliabilities,
        field_sources,
        existence_field,
        n_worlds,
        seed=seed,
    )
    outcomes = [classify_world(w, existence_field) for w in worlds]
    attributable = [f for f in sorted(field_opinions) if f != existence_field]
    return aggregate(outcomes, attributable)
