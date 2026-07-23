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
        nothing is defaulted or repaired here."""
        try:
            data = json.loads(text)
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
    evidence.
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
    and tuples.
    """

    prior_decision: DecisionRecord
    posterior_decisions: tuple[tuple[float, DecisionRecord], ...]
    prior_expected_loss: float
    posterior_expected_loss: float
    gross_value: float
    net_value: float
    fetch_worth_it: bool


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
