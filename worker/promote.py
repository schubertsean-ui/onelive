"""Promotion: event_candidate -> canonical event, gated by multi_confirm_gate.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/promote.py)
"""
import json

import psycopg2

from worker.candidate_store import load_candidate_gate_signals
from worker.classify import resolve_category
from worker.confidence import derive_confidence, is_valid_confidence
from worker.db_config import resolve_dsn
from worker.dedupe import find_possible_duplicates
from worker.importers.domain_map import UNMAPPED
from worker.resolve_entities import resolve_venue_id, resolve_artist_ids
from worker.source_catalog import cultural_domain_for_source
from worker.trust_gate3 import GateDecision, evaluate_gate


def db():
    return psycopg2.connect(resolve_dsn())


def card_fields(title, ticket_link, *, schema_type=None, venue_domain_hint=None,
                venue_business_type=None):
    """Derive the user-facing card columns on `event` (title, category,
    subsegment, ticket_url) from the candidate's OWN real data — the fields
    migration 0010 added and documented promote.py as the writer of, but which
    were never populated (so promoted discovered events rendered titleless and in
    'Other'). Pure function so the mapping is unit-testable without a database.

    Category is resolved by the Router classifier (worker.classify) from the
    STRONGEST available signal — the event's schema.org @type, then the host
    venue's business type / curated domain, then a last-resort title read — each
    with provenance (docs/memory/decisions/2026-07-25_graph-engineering-
    adoption.md). NO FABRICATION: when every signal is silent the category stays
    NULL and the feed shows it honestly as 'Other', never a guessed domain.
    price/image/currency are absent from the crawl extraction schema, so they
    stay NULL rather than being invented.
    """
    r = resolve_category(
        schema_type=schema_type,
        venue_domain_hint=venue_domain_hint,
        venue_business_type=venue_business_type,
        title=title,
    )
    return {
        "title": title or None,
        "category": None if r.domain == UNMAPPED else r.domain,
        "subsegment": r.genre,
        "ticket_url": ticket_link or None,
    }


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
            # cleared the gate (anchor OR corroborated -> confirmed; founder
            # ruling 2026-08-04, "Just 'confirmed' - remove 'likely'").
            confidence = derive_confidence(classes, sxsw_mode=sxsw_mode)

            cur.execute("""
              select title, start_time, end_time, venue_name, city, artist_names,
                     is_private_rsvp, private_access, ticket_link, rsvp_link, raw_text,
                     source_name
              from event_candidate
              where candidate_id=%s
            """, (candidate_id,))
            c = cur.fetchone()
            if not c:
                raise ValueError("candidate not found")
            (title, start_time, end_time, venue_name, city, artist_names, is_private,
             private_access, ticket_link, rsvp_link, raw_text, source_name) = c

            # Resolve entities on THIS cursor so placeholder venue/artist rows are
            # part of the same transaction as the dedupe-check-and-insert below.
            # If dedupe raises and we roll back, those placeholders roll back too
            # (venue has no unique name constraint, so a leaked placeholder would
            # accumulate a duplicate on every retry of a duplicate-blocked candidate).
            # city passes through AS-IS, including NULL. It is never defaulted to
            # "Austin" (Coverage Law: label the truth, do not invent a locale) —
            # resolve_venue_id stores an unknown city as NULL, and both view
            # filters keep NULL-city rows, so nothing is lost by being honest.
            venue_id = resolve_venue_id(cur, venue_name or "Unknown Venue", city)
            artist_ids = resolve_artist_ids(cur, artist_names or [])

            # Dedupe check (if duplicates exist, do not auto-merge; require ops decision)
            dups = find_possible_duplicates(venue_id, start_time, cur=cur) if start_time else []
            if dups:
                raise ValueError(f"Possible duplicate canonical events exist: {dups}")

            # User-facing card columns (title/category/subsegment/ticket_url) from
            # the candidate's OWN data — the fields 0010 added and named promote.py
            # as writer of. Without these a promoted event had no title (only the
            # truncated raw_text in `notes`) and no category (→ always 'Other'),
            # so it could not appear as a real card on the feed. Derivation is
            # deterministic + non-fabricating (see card_fields).
            #
            # Feed the classifier the source's CURATED cultural_domain (founder:
            # "read what the source IS" — a museum's event is visual-arts). This
            # is the human-vetted catalog signal (resolve_category signal #3),
            # ranked above the title-keyword last resort. None for an unknown /
            # untagged source, so the classifier falls through honestly — never a
            # fabricated category. This finally WIRES the resolver in production;
            # before it, promote passed no signal and every event fell to the title.
            venue_domain_hint = cultural_domain_for_source(source_name)
            card = card_fields(title, ticket_link, venue_domain_hint=venue_domain_hint)

            # Source provenance rides onto the public row (migration 0020) so
            # the consumer "How we know" sheet can name and link the source
            # this event was published from. REGISTRY-BOUND (evaluator #188
            # r1, absence-only): the public row carries the REGISTRY's
            # canonical name + base_url, or nothing — a candidate whose
            # source_name matches no registry row publishes NULLs and the UI
            # keeps its generic listing wording, so an unverified/mistyped
            # provenance label can never reach the public trust surface. The
            # registry keys name uniquely (0009), so the lookup is at most
            # one row. No fabrication.
            source_name_pub = None
            source_url = None
            if source_name:
                cur.execute(
                    "select name, base_url from source where lower(name)=lower(%s)",
                    (source_name,))
                src_row = cur.fetchone()
                if src_row:
                    source_name_pub, source_url = src_row[0], src_row[1]

            cur.execute("""
              insert into event(
                venue_id, artist_ids, start_time, end_time,
                status, confidence, override_lock,
                is_private_rsvp, private_access, notes,
                title, category, subsegment, ticket_url,
                source_name, source_url
              )
              values (%s,%s::uuid[],%s,%s,'scheduled',%s,false,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)
              returning event_id
            """, (
                venue_id,
                artist_ids,
                start_time,
                end_time,
                confidence,
                bool(is_private),
                json.dumps(private_access or {}),
                title or (raw_text or "")[:120],
                card["title"],
                card["category"],
                card["subsegment"],
                card["ticket_url"],
                source_name_pub,
                source_url,
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
