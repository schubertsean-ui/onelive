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

EXISTENCE vs FIELD (ONE-LIVE-TRUST.md, founder-ratified 2026-09-02; wired here
2026-09-03, Session Contract #56). "Does this happening exist?" and "is this
field printable as fact?" are DIFFERENT questions and this module must never
answer the first with the second. Existence is decided by the DOOR — the
corroboration tier in worker.gating, unchanged. A field the evidence disagrees
about is reported as a HOLE on the verdict (`GateVerdict.field_holes`) and the
candidate still passes; the publisher writes the hole honestly (NULL) rather
than picking one of the claims, because "do not invent a clock to pass a gate"
cuts both ways — refusing to LIST a real show because its clock is unsettled is
the same fabrication pointed the other way. Two ESCALATE reasons survive
because neither is an existence question: a schema-invalid extraction (the
extractor guessing is never a door) and a private/RSVP event (a
publish-appropriateness call a human owns).

Deliberately does NOT import worker.promote (checked by tools/trust_gate.py's
promote-import allowlist) — this module only decides, it never acts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from worker.gating import GateResult, multi_confirm_gate


class GateDecision(Enum):
    """The three-way trust outcome. PASS/HOLD mirror the base gate's
    ok_to_promote true/false; ESCALATE is the trust-critical branch a naive
    "never ask a human" heuristic would wrongly collapse into PASS."""

    PASS = "pass"
    HOLD = "hold"
    ESCALATE = "escalate"


#: The FIELD whose claims this gate reconciles. Named as a constant because the
#: publisher (worker/promote.py) keys its honest-hole write on the same string,
#: and the two must never drift apart.
FIELD_START_TIME = "start_time"


@dataclass
class GateVerdict:
    decision: GateDecision
    reason: str
    base: GateResult
    signals: Dict[str, Any] = field(default_factory=dict)
    #: Fields the evidence does NOT settle, as {field: why}. A hole is a FIELD
    #: answer, never an existence answer: the candidate still carries whatever
    #: decision the door earned, and the publisher writes the named field as
    #: NULL instead of choosing between the competing claims.
    field_holes: Dict[str, str] = field(default_factory=dict)
    #: Ambiguities worth recording that decide nothing on their own (today: the
    #: dedupe hint). Kept off `reason` so a PASS still reads as the door's own
    #: verdict, and read by the publisher for its audit row.
    notes: List[str] = field(default_factory=list)


def _as_instant(value: Any) -> Optional[datetime]:
    """One start-time claim as a UTC instant, or None when it is not a time.

    A naive timestamp is read as UTC — the SAME convention
    worker.crawl_state._as_utc uses, so the scheduler and the gate can never
    disagree about what a stored naive value means. Anything unparseable comes
    back None and is compared as its raw text instead (below): a garbage claim
    must not silently merge into a real one.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return None
        # 'Z' is valid ISO-8601 and is what most calendars emit; fromisoformat
        # only learned it in 3.11, so normalize it rather than depend on the
        # interpreter version.
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def start_time_claims(evidence_signals: Dict[str, Any]) -> Tuple[Any, ...]:
    """The DISTINCT start-time claims the evidence actually makes.

    Compared as INSTANTS, not as strings, and this is the whole point. The
    column `event_candidate.start_time` is `timestamptz` (migration 0002), so
    psycopg2 returns a tz-aware datetime whose `.isoformat()` ends `+00:00`,
    while the stored `extracted` jsonb keeps whatever string the parser wrote
    ('...Z', or no offset at all). Those are ONE clock written two ways, and
    string comparison scored them as two — so every timed candidate looked
    self-contradictory and could never publish. Measured, not argued: see
    tests/test_gate_existence.py::test_one_clock_written_two_ways_is_one_claim.

    Silence is not a claim: a None/empty entry is dropped, because evidence
    that says nothing about the clock is weaker evidence, never a conflict.
    An unparseable claim keeps its raw text as its own identity rather than
    collapsing into the parsed ones.
    """
    claims = []
    for raw in (evidence_signals.get("start_times") or []):
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        instant = _as_instant(raw)
        key = instant if instant is not None else f"unparseable:{str(raw).strip()}"
        if key not in claims:
            claims.append(key)
    return tuple(claims)


def _has_conflicting_start_time(evidence_signals: Dict[str, Any]) -> bool:
    """True if independent evidence genuinely disagrees on when the event starts.

    NO LONGER AN ESCALATE REASON (founder, 2026-09-03; ONE-LIVE-TRUST.md
    "Parser got two times → still a trusted door. Hole on the clock."). It now
    only marks the CLOCK as a hole — see evaluate_gate. Kept as a named
    predicate so the question stays askable and testable in one place.
    """
    return len(start_time_claims(evidence_signals)) > 1


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
    this gate's control flow.

    NO LONGER AN ESCALATE REASON (founder, 2026-09-03). "Is this row the same
    row as that one?" is an IDENTITY question — the domain of mutation, where
    it stays fail-closed (worker/listing_update.py: a listing that could be two
    rows identifies neither). It was never an existence question, and using it
    as one had a mechanical consequence nobody intended: the hint fires on any
    other live candidate at the same venue and minute, which a SECOND CRAWL OF
    THE SAME PAGE creates by construction (worker/candidate_store.create_candidate
    inserts, it does not upsert), so re-reading a calendar permanently escalated
    every event on it. Now recorded as a note the publisher audits.
    """
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
                   for more evidence. Social-alone and scrapers live here, and
                   that is ONE-LIVE-TRUST.md's own rule, unchanged.
      2. ESCALATE — base gate says ok_to_promote, but publishing at all is a
                   human's call: a validation_error provenance (the extraction
                   itself is schema-invalid, so what we hold may not be a real
                   statement) or a private/RSVP event. Neither is an existence
                   test; both are reasons a person decides.
      3. PASS    — base gate says ok_to_promote. An unsettled FIELD does not
                   change this: it is reported in `field_holes` and the
                   publisher writes that field as NULL.

    FIELD HOLES, NOT REFUSALS (founder, 2026-09-03). A conflicting start_time
    and a dedupe hint used to ESCALATE here, which made a candidate from a
    trusted door unpublishable — an existence answer given by a field test, the
    exact inversion ONE-LIVE-TRUST.md forbids. A trusted door that states a
    happening is listable; a clock two readings disagree about is a hole on the
    clock, and a later tick may fill it.
    """
    extracted = extracted or {}
    evidence_signals = evidence_signals or {}

    base = multi_confirm_gate(source_classes, sxsw_mode=sxsw_mode)

    # Field-level findings are computed for EVERY decision, HOLD included: a
    # held candidate that later earns corroboration must not silently acquire a
    # settled clock it never had.
    field_holes: Dict[str, str] = {}
    claims = start_time_claims(evidence_signals)
    if len(claims) > 1:
        field_holes[FIELD_START_TIME] = (
            f"{len(claims)} irreconcilable start-time claims in the evidence — "
            f"the clock is a hole; the listing is not"
        )
    notes: List[str] = []
    if _has_dedupe_ambiguity(evidence_signals):
        notes.append(
            "another live candidate names this venue at this minute — identity "
            "is unsettled, which decides nothing about existence")

    if not base.ok_to_promote:
        return GateVerdict(
            decision=GateDecision.HOLD,
            reason=base.reason,
            base=base,
            signals=evidence_signals,
            field_holes=field_holes,
            notes=notes,
        )

    escalate_reasons: List[str] = []
    if _has_validation_error_provenance(extracted):
        escalate_reasons.append("extraction flagged validation_error in provenance")
    if _is_private_rsvp(extracted):
        escalate_reasons.append("private/RSVP event requires human publish judgement")

    if escalate_reasons:
        return GateVerdict(
            decision=GateDecision.ESCALATE,
            reason="; ".join(escalate_reasons),
            base=base,
            signals=evidence_signals,
            field_holes=field_holes,
            notes=notes,
        )

    return GateVerdict(
        decision=GateDecision.PASS,
        reason=base.reason,
        base=base,
        signals=evidence_signals,
        field_holes=field_holes,
        notes=notes,
    )
