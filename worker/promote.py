"""Promotion: event_candidate -> canonical event, gated by multi_confirm_gate.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/promote.py)
"""
import json

import psycopg2

from worker.candidate_store import load_candidate_gate_signals
from worker.confidence import derive_confidence, is_valid_confidence
from worker.db_config import resolve_dsn
from worker.dedupe import find_possible_duplicates
from worker.resolve_entities import resolve_venue_id, resolve_artist_ids
from worker.trust_gate3 import GateDecision, evaluate_gate


def db():
    return psycopg2.connect(resolve_dsn())


def assert_promotable(*, source_classes, sxsw_mode, extracted, evidence_signals):
    """Full three-way trust-gate guard for the publish step. Raises ValueError
    unless the candidate is a real PASS. Extracted as a pure function so the
    "only a PASS from real data may be published" invariant is unit-testable
    without a database, and so both the orchestrator-facing gate and this
    promotion-time re-check enforce the identical rule.
    """
    verdict = evaluate_gate(
        source_classes=source_classes,
        sxsw_mode=sxsw_mode,
        extracted=extracted,
        evidence_signals=evidence_signals,
    )
    if verdict.decision is not GateDecision.PASS:
        raise ValueError(
            f"promotion refused: trust gate did not PASS "
            f"({verdict.decision.value}: {verdict.reason})"
        )
    return verdict


def promote_candidate(candidate_id: str) -> str:
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("select sxsw_mode from event_candidate where candidate_id=%s", (candidate_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("candidate not found")
            sxsw_mode = bool(row[0])

            cur.execute("select source_class from candidate_evidence where candidate_id=%s", (candidate_id,))
            classes = [r[0] for r in cur.fetchall()]

            # Re-run the FULL three-way trust gate here — not just the 2-way
            # source-count gate — against the candidate's REAL stored extraction
            # and evidence signals, loaded on THIS cursor so we gate on the same
            # snapshot we promote from. This is the last, authoritative guard
            # before a row reaches the canonical `event` table: promotion is the
            # publish step, so anything that is not a PASS produced from real
            # data (HOLD for weak corroboration, ESCALATE for validation-error /
            # private-RSVP / conflicting-start-time / dedupe ambiguity) is
            # refused here regardless of how it got to this call. evaluate_gate
            # wraps multi_confirm_gate, so the count-based check is subsumed.
            extracted, evidence_signals = load_candidate_gate_signals(candidate_id, cur=cur)
            assert_promotable(
                source_classes=classes,
                sxsw_mode=sxsw_mode,
                extracted=extracted,
                evidence_signals=evidence_signals,
            )

            # Derive the initial 4-state confidence from the evidence that
            # cleared the gate (anchor -> confirmed, corroborated -> likely).
            confidence = derive_confidence(classes, sxsw_mode=sxsw_mode)

            cur.execute("""
              select title, start_time, end_time, venue_name, city, artist_names,
                     is_private_rsvp, private_access, ticket_link, rsvp_link, raw_text
              from event_candidate
              where candidate_id=%s
            """, (candidate_id,))
            c = cur.fetchone()
            if not c:
                raise ValueError("candidate not found")
            (title, start_time, end_time, venue_name, city, artist_names, is_private,
             private_access, ticket_link, rsvp_link, raw_text) = c

            # Resolve entities on THIS cursor so placeholder venue/artist rows are
            # part of the same transaction as the dedupe-check-and-insert below.
            # If dedupe raises and we roll back, those placeholders roll back too
            # (venue has no unique name constraint, so a leaked placeholder would
            # accumulate a duplicate on every retry of a duplicate-blocked candidate).
            venue_id = resolve_venue_id(cur, venue_name or "Unknown Venue", city or "Austin")
            artist_ids = resolve_artist_ids(cur, artist_names or [])

            # Dedupe check (if duplicates exist, do not auto-merge; require ops decision)
            dups = find_possible_duplicates(venue_id, start_time, cur=cur) if start_time else []
            if dups:
                raise ValueError(f"Possible duplicate canonical events exist: {dups}")

            cur.execute("""
              insert into event(
                venue_id, artist_ids, start_time, end_time,
                status, confidence, override_lock,
                is_private_rsvp, private_access, notes
              )
              values (%s,%s,%s,%s,'scheduled',%s,false,%s,%s::jsonb,%s)
              returning event_id
            """, (
                venue_id,
                artist_ids,
                start_time,
                end_time,
                confidence,
                bool(is_private),
                json.dumps(private_access or {}),
                title or (raw_text or "")[:120]
            ))
            event_id = cur.fetchone()[0]

            cur.execute("""
              update event_candidate
              set status='promoted', promoted_event_id=%s
              where candidate_id=%s
            """, (event_id, candidate_id))

            cur.execute("""
              insert into audit_log(actor_type, action, entity_type, entity_id, payload)
              values ('admin','promote','candidate',%s,%s::jsonb)
            """, (candidate_id, json.dumps({"event_id": str(event_id), "confidence": confidence})))
        conn.commit()
    return str(event_id)


def set_event_confidence(event_id: str, confidence: str, actor_type: str = "admin") -> None:
    """Explicitly transition a canonical event to any of the 4 confidence states.

    Used by ops/moderation. Setting 'disputed' NEVER deletes the row — the event
    stays visible and is rendered as disputed by the public API.
    """
    if not is_valid_confidence(confidence):
        raise ValueError(f"invalid confidence state: {confidence!r}")
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update event set confidence=%s, updated_at=now() where event_id=%s",
                (confidence, event_id))
            if cur.rowcount == 0:
                raise ValueError("event not found")
            cur.execute("""
              insert into audit_log(actor_type, action, entity_type, entity_id, payload)
              values (%s,'set_confidence','event',%s,%s::jsonb)
            """, (actor_type, event_id, json.dumps({"confidence": confidence})))
        conn.commit()


def mark_event_disputed(event_id: str, actor_type: str = "admin") -> None:
    """Flag an event as disputed. It remains visible; it is never deleted."""
    set_event_confidence(event_id, "disputed", actor_type=actor_type)
