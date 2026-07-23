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
    """

    mode: str
    wrong_fields: tuple[str, ...]


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
