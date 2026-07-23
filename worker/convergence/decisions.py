"""Expected-loss decision layer + Value of Information (C2, SHADOW-ONLY).

Greppable summary: pure-stdlib implementation of spec §5's "Expected-loss
decision" and "Value of Information (VoI)" (docs/strategy/
ONE_LIVE_CONVERGENCE_v1.md). Belief and action are separated: the gate
action is chosen by minimizing expected loss under an EXPLICIT asymmetric
cost matrix (`CostMatrix`), and every decision returns its full arithmetic
(per-action, per-mode prob*cost terms) so the rationale is auditable, not
just the winner. `voi` prices a re-fetch: expected loss reduction minus
fetch cost (spec §5 — "the expected loss reduction from one more signal
versus its cost").

DRAFT-UNRATIFIED posture: the real cost numbers are a founder-crucial
ratification (spec §11, decision 1 — "the gate's value system; it is
founder voice, not agent judgment") and NONE ship in this code. There are
no default costs, no bundled matrix, no fallback values anywhere: callers
load an explicit matrix (the proposal under ratification is
docs/strategy/ONE_LIVE_COST_MATRIX_DRAFT_v1.md; once ratified it becomes a
versioned config file on the trust path, where any loosening is a
gate-threshold relaxation and founder-crucial per the charter).

Shadow posture (spec §11, phase C2): zero product-path coupling. Project
imports are worker/convergence/sl.py's phase siblings only (here:
worker/convergence/scenarios.py, for the shared outcome-mode vocabulary);
nothing here reads or writes pipeline state, and the count-based gate
keeps deciding until the founder ratifies coupling at C5.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from worker.convergence.scenarios import MODES

# Tolerance for "these probabilities sum to 1" checks ONLY. Individual
# probabilities are bounds-checked EXACTLY — [0, 1], no epsilon — matching
# the sl.py component-bound convention (PR #51 r7): float dust accumulates
# in SUMS, so that is the only place a tolerance is honest; a single
# probability of -1e-12 is a caller normalization bug, not dust.
_SUM_EPS = 1e-6


def _require_finite(label: str, value: object) -> float:
    """A number that enters an audit record must be a finite real
    (evaluator r4/r5, PR #54) — NaN silently passes a bare `> _SUM_EPS`
    comparison (all NaN comparisons are false), so a fabricated record
    carrying NaN would look internally consistent while being
    un-recomputable. Sign is NOT constrained here (a VoI gross/net value
    is legitimately negative)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{label} must be a number; got "
            f"{type(value).__name__}: {value!r}."
        )
    num = float(value)
    if not math.isfinite(num):
        raise ValueError(
            f"{label}={num!r} must be finite — NaN/inf is not audit evidence."
        )
    return num


def _require_audit_number(label: str, value: object) -> float:
    """A loss that enters an audit record must be finite AND non-negative
    (evaluator r4, PR #54)."""
    num = _require_finite(label, value)
    if num < 0.0:
        raise ValueError(
            f"{label}={num!r} must be a finite non-negative "
            f"loss — NaN/inf/negative arithmetic is not audit evidence."
        )
    return num


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """json.loads object_pairs_hook: refuse duplicate keys at every
    nesting level instead of Python's silent last-wins (evaluator r3,
    PR #54 — in the value-system config a duplicate key is an override
    that must never pass quietly)."""
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(
                f"CostMatrix.from_json: duplicate JSON key {key!r} — "
                f"last-wins parsing would silently override a "
                f"value-system cell; the config must state every key "
                f"exactly once."
            )
        out[key] = value
    return out


def _validate_cost(action: str, mode: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"CostMatrix[{action!r}][{mode!r}] must be a number; got "
            f"{type(value).__name__}: {value!r}."
        )
    cost = float(value)
    if not math.isfinite(cost) or cost < 0.0:
        raise ValueError(
            f"CostMatrix[{action!r}][{mode!r}]={cost!r} must be a finite "
            f"non-negative loss (spec §5: impact lives in the loss matrix; "
            f"a negative or infinite 'loss' would let one cell silently "
            f"dominate or invert every decision)."
        )
    return cost


@dataclass(frozen=True)
class CostMatrix:
    """Explicit per-(action, outcome-mode) losses (spec §5: "an explicit
    asymmetric cost matrix ... a versioned, founder-ratified config file —
    impact lives in the loss matrix, never smuggled into the probability").

    `costs` maps action -> {mode -> loss} and must be complete: every
    action carries exactly the three spec-§5 outcome modes
    (fully_wrong / partially_wrong / right). A missing cell fails loudly at
    construction — a hole in the value system must never be silently read
    as zero cost. No defaults exist (module docstring: the numbers are the
    founder's C2 ratification, spec §11 decision 1).

    After construction `costs` is a DEEPLY READ-ONLY view (MappingProxyType
    at both levels over dicts nothing else references): the complete/
    non-negative/explicit guarantees hold for the object's whole lifetime,
    not just at validation time — a frozen dataclass wrapping mutable
    nested dicts would let `matrix.costs[a][m] = x` bypass every check
    (evaluator r1, PR #54).
    """

    costs: Mapping[str, Mapping[str, float]]

    def __post_init__(self) -> None:
        if not isinstance(self.costs, Mapping) or not self.costs:
            raise ValueError(
                f"CostMatrix requires a non-empty mapping of action -> "
                f"{{mode -> loss}}; got {self.costs!r}."
            )
        validated: dict[str, dict[str, float]] = {}
        expected = set(MODES)
        for action, row in self.costs.items():
            if not isinstance(action, str) or not action:
                raise ValueError(
                    f"CostMatrix action names must be non-empty strings; "
                    f"got {action!r}."
                )
            if not isinstance(row, Mapping):
                raise ValueError(
                    f"CostMatrix[{action!r}] must map outcome mode -> loss; "
                    f"got {row!r}."
                )
            missing = expected - set(row)
            if missing:
                raise ValueError(
                    f"CostMatrix[{action!r}] is missing cost cell(s) for "
                    f"mode(s) {sorted(missing)!r}; every (action, mode) cell "
                    f"is required (spec §5 — a hole in the value system is "
                    f"not zero cost)."
                )
            unknown = set(row) - expected
            if unknown:
                raise ValueError(
                    f"CostMatrix[{action!r}] has unknown outcome mode(s) "
                    f"{sorted(unknown)!r}; the modes are exactly {MODES!r} "
                    f"(spec §5)."
                )
            validated[action] = MappingProxyType({
                mode: _validate_cost(action, mode, row[mode]) for mode in MODES
            })
        # Freeze a validated float copy — deeply read-only, and built from
        # fresh dicts so neither the caller's input dict nor any alias can
        # desynchronize a constructed matrix after validation.
        object.__setattr__(self, "costs", MappingProxyType(validated))

    @property
    def actions(self) -> tuple[str, ...]:
        """Actions in matrix order (the config file's declaration order,
        which is also the deterministic tie-break preference in `voi`)."""
        return tuple(self.costs)

    @classmethod
    def from_json(cls, text: str) -> "CostMatrix":
        """Load a matrix from a JSON document of shape
        {action: {mode: loss}} — the on-disk form the ratified versioned
        config file will use (spec §5). All validation is the constructor's;
        nothing is defaulted or repaired here — EXCEPT duplicate-key
        refusal, which only the parser can see: plain json.loads is
        last-wins on duplicate keys, so a duplicated action or mode cell
        in the config would silently override a value-system entry
        (evaluator r3, PR #54 — on a trust-path config that is a hidden
        loosening vector, and it fails loud here instead)."""
        try:
            data = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
        except json.JSONDecodeError as exc:
            raise ValueError(f"CostMatrix.from_json: invalid JSON ({exc}).") from exc
        if not isinstance(data, dict):
            raise ValueError(
                f"CostMatrix.from_json: top level must be an object mapping "
                f"action -> {{mode -> loss}}; got {type(data).__name__}."
            )
        return cls(costs=data)


def _validate_mode_probs(mode_probs: Mapping[str, float]) -> dict[str, float]:
    """Fail-loud validation of a mode-probability distribution: exactly the
    three spec-§5 modes, each EXACTLY in [0, 1] (no epsilon — normalization
    is the caller's job; see _SUM_EPS), summing to 1 within _SUM_EPS."""
    if not isinstance(mode_probs, Mapping):
        raise ValueError(
            f"mode_probs must be a mapping of mode -> probability; got "
            f"{type(mode_probs).__name__}: {mode_probs!r} (evaluator r4 "
            f"nit, PR #54 — a non-mapping caller gets this ValueError, not "
            f"a raw TypeError from set())."
        )
    if set(mode_probs) != set(MODES):
        raise ValueError(
            f"mode_probs keys must be exactly {MODES!r}; got "
            f"{sorted(mode_probs)!r} (spec §5: the three outcome modes)."
        )
    out: dict[str, float] = {}
    for mode in MODES:
        p = mode_probs[mode]
        if isinstance(p, bool) or not isinstance(p, (int, float)):
            raise ValueError(
                f"mode_probs[{mode!r}] must be a number; got {p!r}."
            )
        p = float(p)
        if not (0.0 <= p <= 1.0):
            raise ValueError(
                f"mode_probs[{mode!r}]={p!r} is outside [0, 1] (exact "
                f"bounds — a probability out of range by any amount is a "
                f"normalization bug at the caller, never dust)."
            )
        out[mode] = p
    total = sum(out.values())
    if abs(total - 1.0) > _SUM_EPS:
        raise ValueError(
            f"mode_probs must sum to 1; got {total!r} from {out!r}."
        )
    return out


def expected_loss(
    action: str,
    mode_probs: Mapping[str, float],
    matrix: CostMatrix,
) -> float:
    """Expected loss of one action under the mode distribution (spec §5):
    sum over the three outcome modes of P(mode) * cost(action, mode)."""
    if action not in matrix.costs:
        raise ValueError(
            f"Action {action!r} has no row in the cost matrix (actions: "
            f"{list(matrix.actions)!r}); an unpriced action cannot be "
            f"evaluated (spec §5)."
        )
    probs = _validate_mode_probs(mode_probs)
    return sum(probs[mode] * matrix.costs[action][mode] for mode in MODES)


@dataclass(frozen=True)
class DecisionRecord:
    """A decision with its complete arithmetic (spec §5: the rationale must
    be auditable — "a countable, showable rationale" — never just the
    winner).

    `terms[action][mode]` = P(mode) * cost(action, mode); summing a row
    gives `expected_losses[action]`; `chosen` is the argmin, ties broken
    deterministically toward the earliest action in the caller's order.

    Like CostMatrix, the mappings are made DEEPLY READ-ONLY at
    construction (evaluator r2, PR #54): a decision record is audit
    evidence, and evidence that can be edited after the fact is not
    evidence. And construction VALIDATES internal consistency (evaluator
    r3): the public constructor must not be a way to manufacture a record
    whose chosen action, totals, and terms contradict each other — every
    row sums to its stated total, every row carries exactly the three
    modes, and `chosen` achieves the minimum total. (First-minimal
    tie-breaking is decide()'s contract over the CALLER's action order,
    which the record cannot see; the record enforces achieves-the-min.)
    """

    chosen: str
    expected_losses: Mapping[str, float]
    terms: Mapping[str, Mapping[str, float]]
    mode_probs: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "expected_losses", MappingProxyType(dict(self.expected_losses))
        )
        object.__setattr__(
            self,
            "terms",
            MappingProxyType(
                {a: MappingProxyType(dict(row)) for a, row in self.terms.items()}
            ),
        )
        object.__setattr__(
            self, "mode_probs", MappingProxyType(dict(self.mode_probs))
        )
        # The record CARRIES the distribution its arithmetic was computed
        # under, so that distribution must itself be well-formed (exactly
        # the three modes, each in [0, 1], summing to 1) — otherwise the
        # public constructor could stamp audit evidence with missing/extra
        # modes or NaN/negative probabilities (evaluator r5, PR #54). decide()
        # already validates before building, so this only bites forgeries.
        _validate_mode_probs(self.mode_probs)
        if set(self.terms) != set(self.expected_losses) or not self.expected_losses:
            raise ValueError(
                f"DecisionRecord: terms actions {sorted(self.terms)!r} and "
                f"expected_losses actions {sorted(self.expected_losses)!r} "
                f"must be the same non-empty set."
            )
        if self.chosen not in self.expected_losses:
            raise ValueError(
                f"DecisionRecord: chosen {self.chosen!r} is not among the "
                f"evaluated actions {sorted(self.expected_losses)!r}."
            )
        for action, total in self.expected_losses.items():
            _require_audit_number(f"DecisionRecord.expected_losses[{action!r}]", total)
        for action, row in self.terms.items():
            if set(row) != set(MODES):
                raise ValueError(
                    f"DecisionRecord: terms[{action!r}] modes "
                    f"{sorted(row)!r} must be exactly {MODES!r}."
                )
            for mode, term in row.items():
                _require_audit_number(f"DecisionRecord.terms[{action!r}][{mode!r}]", term)
            # NB: the sum check below relies on every term being finite —
            # a NaN slips past `abs(nan) > eps` (nan comparisons are false),
            # which is exactly the fabricated-evidence hole the per-cell
            # _require_audit_number above closes (evaluator r4, PR #54).
            if abs(sum(row.values()) - self.expected_losses[action]) > _SUM_EPS:
                raise ValueError(
                    f"DecisionRecord: expected_losses[{action!r}]="
                    f"{self.expected_losses[action]!r} does not equal the "
                    f"sum of its terms row {sum(row.values())!r} — a record "
                    f"whose arithmetic cannot be recomputed from itself is "
                    f"not audit evidence."
                )
        best = min(self.expected_losses.values())
        if abs(self.expected_losses[self.chosen] - best) > _SUM_EPS:
            raise ValueError(
                f"DecisionRecord: chosen {self.chosen!r} "
                f"(loss {self.expected_losses[self.chosen]!r}) does not "
                f"achieve the minimum expected loss {best!r}."
            )


def decide(
    actions: Sequence[str],
    mode_probs: Mapping[str, float],
    matrix: CostMatrix,
) -> DecisionRecord:
    """Choose the loss-minimizing action (spec §5 "Expected-loss
    decision": "The gate action ... is chosen by minimizing expected loss
    under an explicit asymmetric cost matrix").

    Returns the FULL arithmetic — every action's per-mode prob*cost terms
    and totals — so any reviewer can recompute the choice from the record
    alone. Ties break toward the earliest action in `actions` (the caller's
    stated preference order), deterministically. Duplicate or unpriced
    actions fail loudly.
    """
    if not actions:
        raise ValueError("decide() needs at least one candidate action.")
    if len(set(actions)) != len(actions):
        raise ValueError(
            f"decide() actions contain duplicates: {list(actions)!r} — a "
            f"repeated action would make the tie-break order ambiguous."
        )
    probs = _validate_mode_probs(mode_probs)
    terms: dict[str, dict[str, float]] = {}
    totals: dict[str, float] = {}
    for action in actions:
        if action not in matrix.costs:
            raise ValueError(
                f"Action {action!r} has no row in the cost matrix (actions: "
                f"{list(matrix.actions)!r}); an unpriced action cannot "
                f"compete (spec §5)."
            )
        row = {
            mode: probs[mode] * matrix.costs[action][mode] for mode in MODES
        }
        terms[action] = row
        totals[action] = sum(row.values())
    # min() returns the FIRST minimal element (documented CPython
    # guarantee), so ties break toward the earliest action in `actions`
    # with a single O(n) pass — no per-comparison index scans.
    chosen = min(actions, key=totals.__getitem__)
    return DecisionRecord(
        chosen=chosen,
        expected_losses=totals,
        terms=terms,
        mode_probs=probs,
    )


@dataclass(frozen=True)
class VoiRecord:
    """Value-of-Information arithmetic, in full (spec §5 "Value of
    Information (VoI)"), auditable end to end:

    prior_expected_loss      — best achievable loss acting NOW;
    posterior_expected_loss  — sum over fetch-outcome branches of
                               P(branch) * best loss AFTER seeing it;
    gross_value              — prior minus posterior (what the signal is
                               worth before paying for it);
    net_value                — gross_value minus fetch_cost;
    fetch_worth_it           — net_value strictly positive (spec §5 +
                               cost-discipline charter: spend follows
                               decision value; a fetch that merely breaks
                               even is not bought).

    Deeply immutable like DecisionRecord: every mapping it reaches lives
    inside its (deep-frozen) DecisionRecords, its own fields are scalars
    and tuples. And, like the other audit records, the public constructor
    VALIDATES internal consistency (evaluator r5, PR #54) so a forged
    VoiRecord — net<0 marked worth-it, NaN losses, branch probabilities
    that do not sum to 1, a mutable list of posterior decisions — fails
    loud rather than being manufacturable.
    """

    prior_decision: DecisionRecord
    posterior_decisions: tuple[tuple[float, DecisionRecord], ...]
    prior_expected_loss: float
    posterior_expected_loss: float
    gross_value: float
    net_value: float
    fetch_worth_it: bool

    def __post_init__(self) -> None:
        if not isinstance(self.prior_decision, DecisionRecord):
            raise ValueError(
                f"VoiRecord.prior_decision must be a DecisionRecord; got "
                f"{type(self.prior_decision).__name__}."
            )
        # Losses are finite non-negative; gross/net are finite but may be
        # negative (an incoherent-mixture fetch can raise expected loss,
        # and net is gross minus a non-negative cost).
        _require_audit_number("VoiRecord.prior_expected_loss",
                              self.prior_expected_loss)
        _require_audit_number("VoiRecord.posterior_expected_loss",
                              self.posterior_expected_loss)
        gross = _require_finite("VoiRecord.gross_value", self.gross_value)
        net = _require_finite("VoiRecord.net_value", self.net_value)
        # Freeze posterior_decisions to a tuple and validate each branch.
        frozen: list[tuple[float, DecisionRecord]] = []
        branch_total = 0.0
        for i, pair in enumerate(self.posterior_decisions):
            if not (isinstance(pair, tuple) and len(pair) == 2):
                raise ValueError(
                    f"VoiRecord.posterior_decisions[{i}] must be a "
                    f"(branch_prob, DecisionRecord) pair; got {pair!r}."
                )
            branch_p, dec = pair
            if isinstance(branch_p, bool) or not isinstance(branch_p, (int, float)):
                raise ValueError(
                    f"VoiRecord.posterior_decisions[{i}] branch probability "
                    f"must be a number; got {branch_p!r}."
                )
            branch_p = float(branch_p)
            if not math.isfinite(branch_p) or not (0.0 <= branch_p <= 1.0):
                raise ValueError(
                    f"VoiRecord.posterior_decisions[{i}] branch probability "
                    f"{branch_p!r} must be finite in [0, 1]."
                )
            if not isinstance(dec, DecisionRecord):
                raise ValueError(
                    f"VoiRecord.posterior_decisions[{i}] second element must "
                    f"be a DecisionRecord; got {type(dec).__name__}."
                )
            frozen.append((branch_p, dec))
            branch_total += branch_p
        if not frozen:
            raise ValueError(
                "VoiRecord.posterior_decisions is empty: a fetch with no "
                "outcome branch has no defined value."
            )
        if abs(branch_total - 1.0) > _SUM_EPS:
            raise ValueError(
                f"VoiRecord branch probabilities must sum to 1; got "
                f"{branch_total!r}."
            )
        object.__setattr__(self, "posterior_decisions", tuple(frozen))
        # Cross-OBJECT consistency (evaluator r6, PR #54): a VoiRecord holds
        # the same quantities in two representations — scalar loss summaries
        # AND the embedded DecisionRecords they summarize — so the two must
        # agree, or the record is internally contradictory audit evidence
        # while still satisfying the scalar-only checks below. prior loss is
        # the prior decision's chosen loss; posterior loss is the
        # branch-probability-weighted mixture of each branch decision's
        # chosen loss (exactly what voi() computes).
        prior_from_decision = self.prior_decision.expected_losses[
            self.prior_decision.chosen
        ]
        if abs(self.prior_expected_loss - prior_from_decision) > _SUM_EPS:
            raise ValueError(
                f"VoiRecord.prior_expected_loss={self.prior_expected_loss!r} "
                f"does not match prior_decision's chosen loss "
                f"{prior_from_decision!r}."
            )
        posterior_from_decisions = sum(
            bp * dec.expected_losses[dec.chosen]
            for bp, dec in self.posterior_decisions
        )
        if abs(self.posterior_expected_loss - posterior_from_decisions) > _SUM_EPS:
            raise ValueError(
                f"VoiRecord.posterior_expected_loss="
                f"{self.posterior_expected_loss!r} does not match the "
                f"branch-weighted mixture of the posterior decisions' chosen "
                f"losses ({posterior_from_decisions!r})."
            )
        # Cross-field arithmetic must be recomputable from the record:
        # gross = prior - posterior, and net = gross - (non-negative cost)
        # so net can never EXCEED gross. fetch_worth_it is exactly net>0.
        if abs(gross - (self.prior_expected_loss - self.posterior_expected_loss)) \
                > _SUM_EPS:
            raise ValueError(
                f"VoiRecord.gross_value={gross!r} does not equal "
                f"prior_expected_loss - posterior_expected_loss "
                f"({self.prior_expected_loss - self.posterior_expected_loss!r})."
            )
        if net > gross + _SUM_EPS:
            raise ValueError(
                f"VoiRecord.net_value={net!r} exceeds gross_value={gross!r}; "
                f"net = gross - fetch_cost and fetch_cost is non-negative."
            )
        if not isinstance(self.fetch_worth_it, bool):
            raise ValueError(
                f"VoiRecord.fetch_worth_it must be a bool; got "
                f"{type(self.fetch_worth_it).__name__}."
            )
        if self.fetch_worth_it != (net > 0.0):
            raise ValueError(
                f"VoiRecord.fetch_worth_it={self.fetch_worth_it} contradicts "
                f"net_value={net!r} (worth-it is exactly net_value > 0 — spec "
                f"§5 + cost discipline: a break-even fetch is not bought)."
            )


def voi(
    current_mode_probs: Mapping[str, float],
    posterior_scenarios_if_fetched: Sequence[tuple[float, Mapping[str, float]]],
    fetch_cost: float,
    matrix: CostMatrix,
) -> VoiRecord:
    """Price one more fetch (spec §5 "Value of Information": "the expected
    loss reduction from one more signal versus its cost" — the re-fetch
    gating rule; "a claim at 0.99 belief buys nothing from a re-fetch; a
    high-traffic event three weeks out at 0.8 buys a lot").

    `posterior_scenarios_if_fetched` enumerates what the fetch might
    reveal: (branch probability, posterior mode distribution) pairs whose
    branch probabilities sum to 1. VoI = [best loss now] - [expected best
    loss after fetching] - fetch_cost, decided over every action in the
    matrix (matrix order is the tie-break order). The caller owns the
    coherence of its posterior scenarios (for a coherent predictive mixture
    the gross value is never negative; this function reports whatever the
    supplied scenarios imply rather than repairing them — the honest number
    is the auditable one).
    """
    if isinstance(fetch_cost, bool) or not isinstance(fetch_cost, (int, float)):
        raise ValueError(f"fetch_cost must be a number; got {fetch_cost!r}.")
    fetch_cost = float(fetch_cost)
    if not math.isfinite(fetch_cost) or fetch_cost < 0.0:
        raise ValueError(
            f"fetch_cost={fetch_cost!r} must be finite and non-negative "
            f"(spec §5: a fetch has a real, positive-or-zero price)."
        )
    if not posterior_scenarios_if_fetched:
        raise ValueError(
            "voi() needs at least one posterior scenario: a fetch that "
            "cannot produce any outcome has no defined value."
        )
    actions = list(matrix.actions)
    prior_decision = decide(actions, current_mode_probs, matrix)
    prior_loss = prior_decision.expected_losses[prior_decision.chosen]

    branch_total = 0.0
    posterior_loss = 0.0
    posterior_decisions: list[tuple[float, DecisionRecord]] = []
    for i, (branch_p, branch_probs) in enumerate(posterior_scenarios_if_fetched):
        if isinstance(branch_p, bool) or not isinstance(branch_p, (int, float)):
            raise ValueError(
                f"Posterior scenario {i}: branch probability must be a "
                f"number; got {branch_p!r}."
            )
        branch_p = float(branch_p)
        if not (0.0 <= branch_p <= 1.0):
            raise ValueError(
                f"Posterior scenario {i}: branch probability {branch_p!r} "
                f"is outside [0, 1] (exact bounds — normalization is the "
                f"caller's job, never dust)."
            )
        branch_decision = decide(actions, branch_probs, matrix)
        posterior_decisions.append((branch_p, branch_decision))
        posterior_loss += (
            branch_p * branch_decision.expected_losses[branch_decision.chosen]
        )
        branch_total += branch_p
    if abs(branch_total - 1.0) > _SUM_EPS:
        raise ValueError(
            f"Posterior scenario branch probabilities must sum to 1; got "
            f"{branch_total!r} — an incomplete fetch-outcome distribution "
            f"would silently bias the VoI."
        )
    gross = prior_loss - posterior_loss
    net = gross - fetch_cost
    return VoiRecord(
        prior_decision=prior_decision,
        posterior_decisions=tuple(posterior_decisions),
        prior_expected_loss=prior_loss,
        posterior_expected_loss=posterior_loss,
        gross_value=gross,
        net_value=net,
        fetch_worth_it=net > 0.0,
    )
