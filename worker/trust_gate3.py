"""Three-way trust gate — the Harness core.

`worker.gating.multi_confirm_gate` is a 2-way gate: promotable or not. That is
correct for *corroboration counting*, but corroboration count alone is not
enough to safely auto-publish. Trust requires a third outcome: when evidence
is technically sufficient by count BUT internally contradictory or otherwise
requires a human's judgement, we must not silently promote on the strength of
the count-based gate alone. This module wraps (never replaces)
`multi_confirm_gate` and adds that third outcome.

This is the literal enforcement of the project's gate-custodied-publication
rule ("AI never publishes directly") at the decision layer: this module never promotes anything by
itself (see worker/promote.py, which re-checks the 2-way gate independently —
defense in depth). It only classifies a candidate into PASS / HOLD / ESCALATE
so the orchestrator (worker/orchestrator.py) knows what to do next.

Deliberately does NOT import worker.promote (checked by tools/trust_gate.py's
promote-import allowlist) — this module only decides, it never acts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from worker.gating import GateResult, multi_confirm_gate


class GateDecision(Enum):
    """The three-way trust outcome. PASS/HOLD mirror the base gate's
    ok_to_promote true/false; ESCALATE is the trust-critical branch a naive
    "never ask a human" heuristic would wrongly collapse into PASS."""

    PASS = "pass"
    HOLD = "hold"
    ESCALATE = "escalate"


@dataclass
class GateVerdict:
    decision: GateDecision
    reason: str
    base: GateResult
    signals: Dict[str, Any] = field(default_factory=dict)


def _has_conflicting_start_time(evidence_signals: Dict[str, Any]) -> bool:
    """True if independent evidence disagrees on when the event starts.

    Evidence_signals carries `start_times`: the list of start_time strings
    observed across evidence rows (may include None for evidence that didn't
    state one). We only compare non-null values — an evidence row that is
    silent about start_time is not a conflict; it is weaker evidence.
    """
    start_times = evidence_signals.get("start_times") or []
    observed = {t for t in start_times if t}
    return len(observed) > 1


def _has_validation_error_provenance(extracted: Dict[str, Any]) -> bool:
    """True if the extraction pipeline itself flagged this candidate as
    schema-invalid (worker.ai_extract sets extracted["_provenance"]
    ["validation_error"] = True rather than silently dropping a malformed
    extraction). An anchor-backed candidate with a flagged extraction is
    exactly the "count says yes, content says maybe not" case ESCALATE
    exists for.
    """
    provenance = extracted.get("_provenance")
    if not isinstance(provenance, dict):
        return False
    return bool(provenance.get("validation_error"))


def _is_private_rsvp(extracted: Dict[str, Any]) -> bool:
    """Private/RSVP-gated events need a human's judgement on whether it's
    appropriate to publish at all, regardless of how well-corroborated the
    existence of the event is."""
    return bool(extracted.get("is_private_rsvp", False))


def _has_dedupe_ambiguity(evidence_signals: Dict[str, Any]) -> bool:
    """True if the caller has already flagged a possible-duplicate hint
    (e.g. from a pre-promote dedupe probe). Kept as an explicit signal key so
    callers can wire in stronger dedupe heuristics later without touching
    this gate's control flow."""
    return bool(evidence_signals.get("dedupe_ambiguous", False))


def evaluate_gate(
    *,
    source_classes: List[str],
    sxsw_mode: bool = False,
    extracted: Optional[Dict[str, Any]] = None,
    evidence_signals: Optional[Dict[str, Any]] = None,
) -> GateVerdict:
    """Classify a candidate into PASS / HOLD / ESCALATE.

    Deterministic, three ordered rules:
      1. HOLD    — base gate says not ok_to_promote (insufficient
                   corroboration). Not an error, not an escalation: wait
                   for more evidence.
      2. ESCALATE — base gate says ok_to_promote, but the evidence itself is
                   conflicting or ambiguous (conflicting start_time,
                   validation_error provenance, private/RSVP, or a
                   dedupe-ambiguity hint). Promotable-by-count is NOT the same
                   as safe-to-auto-publish.
      3. PASS    — base gate says ok_to_promote AND no conflict signals.
                   Safe to hand to promote_candidate (which re-checks the
                   2-way gate itself; this module never promotes).
    """
    extracted = extracted or {}
    evidence_signals = evidence_signals or {}

    base = multi_confirm_gate(source_classes, sxsw_mode=sxsw_mode)

    if not base.ok_to_promote:
        return GateVerdict(
            decision=GateDecision.HOLD,
            reason=base.reason,
            base=base,
            signals=evidence_signals,
        )

    conflict_reasons: List[str] = []
    if _has_conflicting_start_time(evidence_signals):
        conflict_reasons.append("conflicting start_time across evidence")
    if _has_validation_error_provenance(extracted):
        conflict_reasons.append("extraction flagged validation_error in provenance")
    if _is_private_rsvp(extracted):
        conflict_reasons.append("private/RSVP event requires human publish judgement")
    if _has_dedupe_ambiguity(evidence_signals):
        conflict_reasons.append("dedupe-ambiguity hint present")

    if conflict_reasons:
        return GateVerdict(
            decision=GateDecision.ESCALATE,
            reason="; ".join(conflict_reasons),
            base=base,
            signals=evidence_signals,
        )

    return GateVerdict(
        decision=GateDecision.PASS,
        reason=base.reason,
        base=base,
        signals=evidence_signals,
    )
