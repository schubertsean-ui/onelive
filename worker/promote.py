"""Promotion: event_candidate -> canonical event, gated by multi_confirm_gate.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/promote.py)
"""
import json
import os
import psycopg2

from worker.gating import multi_confirm_gate
from worker.confidence import derive_confidence, is_valid_confidence
from worker.resolve_entities import resolve_venue_id, resolve_artist_ids
from worker.dedupe import find_possible_duplicates

DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def db():
    return psycopg2.connect(DB_DSN)


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
            gate = multi_confirm_gate(classes, sxsw_mode=sxsw_mode)
            if not gate.ok_to_promote:
                raise ValueError(gate.reason)

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
