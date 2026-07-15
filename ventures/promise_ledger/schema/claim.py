"""Claim Schema v0 — the "promise markup" (market analysis harvest H13).

The claim, not the document, is the primary unit. Every claim is an immutable
record of what an entity said, where, and when; its lifecycle advances by
APPENDING events (never editing) so the ledger stays point-in-time correct.

Design constraints this schema enforces (see ventures/promise_ledger/README.md):
- lifecycle includes `silently_dropped` — a promise that vanishes between
  communications is a first-class, detectable state (H1);
- fulfillment verdicts carry the 4-state confidence model
  (unverified/likely/confirmed/disputed) — never a bare boolean (H10);
- every field that makes a checkable assertion carries provenance
  (source document URL + as-of timestamp);
- entity keys prefer LEI (the FDTA-mandated cross-agency identifier), with
  CIK/ticker as secondary keys.

stdlib-only (dataclasses) so the schema package runs anywhere the repo's
tests run, with a hand-rolled validator and a JSON Schema export kept in
lockstep by tests.
"""

from __future__ import annotations

import dataclasses
import datetime
import enum
import re
from dataclasses import dataclass, field
from typing import Optional


class ClaimKind(enum.Enum):
    NUMERIC_GUIDANCE = "numeric_guidance"      # "revenue of $1.2-1.4B in FY27"
    DATED_EVENT = "dated_event"                # "launch in Q3 2027"
    QUALITATIVE_COMMITMENT = "qualitative_commitment"  # "we will reduce churn"
    CAPABILITY_ASSERTION = "capability_assertion"      # "our AI does X" (AI-washing class)


class LifecycleState(enum.Enum):
    MADE = "made"
    REITERATED = "reiterated"
    MODIFIED = "modified"
    FULFILLED = "fulfilled"
    BROKEN = "broken"
    SILENTLY_DROPPED = "silently_dropped"
    WITHDRAWN = "withdrawn"          # explicitly retracted by the issuer
    EXPIRED_UNRESOLVED = "expired_unresolved"  # due date passed, outcome undeterminable


class FulfillmentConfidence(enum.Enum):
    """OneLive's 4-state confidence model applied to fulfillment verdicts.

    A verdict is a (LifecycleState, FulfillmentConfidence, evidence) triple —
    'broken/likely' and 'broken/confirmed' are different products of very
    different legal weight, and 'disputed' is always displayed, never hidden.
    """
    UNVERIFIED = "unverified"
    LIKELY = "likely"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"


_LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")
_CIK_RE = re.compile(r"^\d{10}$")  # SEC requires zero-padded 10-digit CIKs


@dataclass(frozen=True)
class EntityRef:
    """Who made the claim. LEI-first (FDTA); CIK zero-padded per SEC rules."""
    name: str
    lei: Optional[str] = None
    cik: Optional[str] = None
    ticker: Optional[str] = None

    def validate(self) -> list[str]:
        errors = []
        if not self.name.strip():
            errors.append("entity.name must be non-empty")
        if self.lei is not None and not _LEI_RE.match(self.lei):
            errors.append(f"entity.lei {self.lei!r} is not a valid 20-char LEI")
        if self.cik is not None and not _CIK_RE.match(self.cik):
            errors.append(f"entity.cik {self.cik!r} must be zero-padded to 10 digits")
        if self.lei is None and self.cik is None:
            errors.append("entity needs at least one stable identifier (lei or cik)")
        return errors


@dataclass(frozen=True)
class Provenance:
    """Where and when a statement was made — every assertion carries one."""
    source_url: str
    source_kind: str                  # e.g. "8-K/EX-99.1", "press_release", "ir_page"
    published_at: datetime.datetime   # when the source says it was published
    retrieved_at: datetime.datetime   # when WE saw it (as-of-known-when anchor)
    excerpt_sha256: Optional[str] = None  # hash of the stored verbatim excerpt (internal-only text)

    def validate(self) -> list[str]:
        errors = []
        if not self.source_url.startswith(("http://", "https://")):
            errors.append(f"provenance.source_url {self.source_url!r} must be a URL")
        if not self.source_kind.strip():
            errors.append("provenance.source_kind must be non-empty")
        if self.published_at.tzinfo is None or self.retrieved_at.tzinfo is None:
            errors.append("provenance timestamps must be timezone-aware")
        elif self.published_at > self.retrieved_at:
            # a source cannot have been published after we read it — the
            # time-incoherence class caught by the research evaluator (r8)
            errors.append("provenance.published_at is after retrieved_at — time-incoherent")
        return errors


@dataclass(frozen=True)
class Claim:
    """An extracted, re-expressed promise. The verbatim source text is stored
    elsewhere (internal-only); this record carries the re-expression."""
    claim_id: str                     # stable content-derived id (caller-assigned)
    entity: EntityRef
    kind: ClaimKind
    statement: str                    # the RE-EXPRESSED claim, not verbatim source
    provenance: Provenance
    metric: Optional[str] = None      # for numeric guidance: what is measured
    target_low: Optional[float] = None
    target_high: Optional[float] = None
    unit: Optional[str] = None
    due_date: Optional[datetime.date] = None  # parsed from claim language (H9)
    due_date_text: Optional[str] = None       # the original phrasing ("by Q3 2027")

    def validate(self) -> list[str]:
        errors = []
        if not self.claim_id.strip():
            errors.append("claim_id must be non-empty")
        if not self.statement.strip():
            errors.append("statement must be non-empty")
        errors += self.entity.validate()
        errors += self.provenance.validate()
        if self.kind == ClaimKind.NUMERIC_GUIDANCE:
            if (self.metric is None or not self.metric.strip()
                    or (self.target_low is None and self.target_high is None)):
                errors.append("numeric_guidance requires metric and at least one target bound")
            if self.unit is None or not self.unit.strip():
                errors.append("numeric_guidance requires a unit — unitless targets cannot be "
                              "compared or audited")
            if (self.target_low is not None and self.target_high is not None
                    and self.target_low > self.target_high):
                errors.append("target_low exceeds target_high")
        has_due_text = self.due_date_text is not None and self.due_date_text.strip() != ""
        if self.kind == ClaimKind.DATED_EVENT and self.due_date is None and not has_due_text:
            errors.append("dated_event requires due_date or a non-empty due_date_text — "
                          "a dated event without a date is a false trust record")
        if self.due_date is not None and not has_due_text:
            errors.append("a parsed due_date must keep its original non-empty due_date_text "
                          "(provenance of the parse)")
        return errors


@dataclass(frozen=True)
class LifecycleEvent:
    """Append-only lifecycle progression. Events never edit prior events."""
    claim_id: str
    state: LifecycleState
    confidence: FulfillmentConfidence
    observed_at: datetime.datetime
    evidence: tuple[Provenance, ...] = field(default_factory=tuple)
    note: Optional[str] = None        # re-expressed rationale, never verbatim source

    # Verdict states carry the strongest legal weight, but EVERY lifecycle
    # event is a sourced assertion in an append-only trust ledger — a
    # withdrawal, modification, or reiteration without source evidence is an
    # unsupported ledger mutation (evaluator r20). For EXPIRED_UNRESOLVED the
    # evidence is the original claim's provenance (the source of the due date
    # that expired).
    _VERDICT_STATES = frozenset({
        LifecycleState.FULFILLED, LifecycleState.BROKEN, LifecycleState.SILENTLY_DROPPED,
    })

    def validate(self) -> list[str]:
        errors = []
        if not self.claim_id.strip():
            errors.append("lifecycle.claim_id must be non-empty")
        if self.observed_at.tzinfo is None:
            errors.append("lifecycle.observed_at must be timezone-aware")
        if not self.evidence:
            if self.state in self._VERDICT_STATES:
                errors.append(f"verdict state {self.state.value!r} requires evidence — "
                              "a verdict without evidence is an accusation")
            else:
                errors.append(f"lifecycle state {self.state.value!r} requires evidence — "
                              "every event in an append-only trust ledger is a sourced "
                              "assertion (for expired_unresolved, cite the original "
                              "claim's provenance)")
        for ev in self.evidence:
            errors += ev.validate()
        return errors


def validate(obj) -> list[str]:
    """Uniform entry point: returns a list of human-readable errors (empty = valid)."""
    if not hasattr(obj, "validate"):
        return [f"{type(obj).__name__} is not a schema object"]
    return obj.validate()


def _nonblank(extra: dict | None = None) -> dict:
    """JSON Schema for a string that is non-empty AND not whitespace-only —
    parity with the Python validators' .strip() semantics (evaluator r21).
    `pattern` is unanchored, so \\S means 'contains a non-space character'."""
    out = {"type": "string", "minLength": 1, "pattern": "\\S"}
    if extra:
        out.update(extra)
    return out


def to_json_schema() -> dict:
    """Export a JSON Schema for the Claim record (the interchange format —
    the 'promise markup' consumed by MCP tools and customer pipelines).
    Kept in lockstep with the dataclasses by tests."""
    def enum_values(e):
        return [m.value for m in e]

    provenance_schema = _provenance_json_schema()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": ("https://github.com/schubertsean-ui/onelive/blob/master/"
                "ventures/promise_ledger/schema/claim/v0"),
        "title": "Claim",
        "description": (
            "The promise-markup interchange record. Mirrors the Python validator in "
            "ventures/promise_ledger/schema/claim.py, which remains AUTHORITATIVE. "
            "One invariant is NOT expressible in JSON Schema and MUST be enforced by "
            "consumers in code: provenance.published_at <= provenance.retrieved_at "
            "(time-incoherent records are invalid). See x-invariants."
        ),
        "x-invariants": [
            "provenance.published_at <= provenance.retrieved_at (cross-field date "
            "comparison; not expressible in JSON Schema 2020-12 without extensions)",
            "target_low <= target_high when both are present (cross-field numeric "
            "comparison; not expressible in JSON Schema 2020-12 without extensions)",
        ],
        "type": "object",
        "required": ["claim_id", "entity", "kind", "statement", "provenance"],
        "properties": {
            "claim_id": _nonblank(),
            "entity": {
                "type": "object",
                "required": ["name"],
                # mirror EntityRef.validate: at least one stable identifier,
                # and the identifier satisfying the branch must be a NON-NULL
                # pattern-valid string (a present-but-null lei/cik does not
                # count — evaluator r21).
                "anyOf": [
                    {"required": ["lei"],
                     "properties": {"lei": {"type": "string", "pattern": _LEI_RE.pattern}}},
                    {"required": ["cik"],
                     "properties": {"cik": {"type": "string", "pattern": _CIK_RE.pattern}}},
                ],
                "properties": {
                    "name": _nonblank(),
                    "lei": {"type": ["string", "null"], "pattern": _LEI_RE.pattern},
                    "cik": {"type": ["string", "null"], "pattern": _CIK_RE.pattern},
                    "ticker": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
            "kind": {"enum": enum_values(ClaimKind)},
            "statement": _nonblank(),
            "provenance": provenance_schema,
            "metric": {"type": ["string", "null"]},
            "target_low": {"type": ["number", "null"]},
            "target_high": {"type": ["number", "null"]},
            "unit": {"type": ["string", "null"]},
            "due_date": {"type": ["string", "null"], "format": "date"},
            "due_date_text": {"type": ["string", "null"]},
        },
        # mirror Claim.validate's conditional requirements:
        "allOf": [
            {   # numeric_guidance requires metric + at least one target bound
                "if": {"properties": {"kind": {"const": ClaimKind.NUMERIC_GUIDANCE.value}}},
                "then": {
                    "required": ["metric", "unit"],
                    "properties": {"metric": _nonblank(), "unit": _nonblank()},
                    "anyOf": [
                        {"required": ["target_low"], "properties": {"target_low": {"type": "number"}}},
                        {"required": ["target_high"], "properties": {"target_high": {"type": "number"}}},
                    ],
                },
            },
            {   # dated_event requires a due date or its original text
                "if": {"properties": {"kind": {"const": ClaimKind.DATED_EVENT.value}}},
                "then": {"anyOf": [
                    {"required": ["due_date"],
                     "properties": {"due_date": {"type": "string", "format": "date"}}},
                    {"required": ["due_date_text"],
                     "properties": {"due_date_text": _nonblank()}},
                ]},
            },
            {   # a parsed due_date must keep its original NON-BLANK phrasing
                "if": {"required": ["due_date"], "properties": {"due_date": {"type": "string"}}},
                "then": {"required": ["due_date_text"],
                         "properties": {"due_date_text": _nonblank()}},
            },
        ],
        "additionalProperties": False,
        "$defs": {
            "lifecycle_state": {"enum": enum_values(LifecycleState)},
            "fulfillment_confidence": {"enum": enum_values(FulfillmentConfidence)},
        },
    }


def _provenance_json_schema() -> dict:
    """Shared by the Claim and LifecycleEvent interchange schemas: evidence IS
    provenance — a record with no source URL, kind, or timestamps is not
    evidence, and must not validate as such."""
    return {
        "type": "object",
        "required": ["source_url", "source_kind", "published_at", "retrieved_at"],
        "properties": {
            "source_url": {"type": "string", "format": "uri", "pattern": "^https?://"},
            "source_kind": _nonblank(),
            "published_at": {"type": "string", "format": "date-time"},
            "retrieved_at": {"type": "string", "format": "date-time"},
            "excerpt_sha256": {"type": ["string", "null"]},
        },
        "additionalProperties": False,
    }


def to_lifecycle_event_json_schema() -> dict:
    """Interchange schema for LifecycleEvent — verdict states require evidence,
    and evidence items are full Provenance records (an empty object is not
    evidence; evaluator r19). The Python validator stays authoritative."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": ("https://github.com/schubertsean-ui/onelive/blob/master/"
                "ventures/promise_ledger/schema/lifecycle_event/v0"),
        "title": "LifecycleEvent",
        "description": (
            "Mirrors LifecycleEvent.validate in ventures/promise_ledger/schema/"
            "claim.py, which remains AUTHORITATIVE. Consumers MUST additionally "
            "enforce the x-invariants (cross-field comparisons JSON Schema cannot "
            "express)."
        ),
        "x-invariants": [
            "for every evidence item: published_at <= retrieved_at (cross-field "
            "date comparison; not expressible in JSON Schema 2020-12)",
        ],
        "type": "object",
        # evidence is required for EVERY event: each lifecycle assertion in an
        # append-only trust ledger must be sourced (evaluator r20) — verdict
        # states are merely the highest-stakes case of the same rule.
        "required": ["claim_id", "state", "confidence", "observed_at", "evidence"],
        "properties": {
            "claim_id": _nonblank(),
            "state": {"enum": [m.value for m in LifecycleState]},
            "confidence": {"enum": [m.value for m in FulfillmentConfidence]},
            "observed_at": {"type": "string", "format": "date-time"},
            "evidence": {"type": "array", "minItems": 1,
                         "items": _provenance_json_schema()},
            "note": {"type": ["string", "null"]},
        },
        "additionalProperties": False,
    }


def dataclass_field_names(cls) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}
