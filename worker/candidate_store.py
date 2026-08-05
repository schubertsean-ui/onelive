"""DB access layer for event_candidate / candidate_evidence.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/candidate_store.py)
"""
from typing import Optional, Dict, Any, List, Tuple
import json

import psycopg2

from worker.db_config import resolve_dsn


def db():
    return psycopg2.connect(resolve_dsn())


def create_candidate(
    *,
    source_id: Optional[str],
    source_name: str,
    source_url: str,
    source_class: str,
    raw_text: str,
    extracted: Dict[str, Any],
    sxsw_mode: bool,
) -> str:
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              insert into event_candidate(
                source_id, source_name, source_url, source_class, raw_text, extracted,
                title, start_time, end_time, venue_name, city, artist_names, ticket_link, rsvp_link,
                is_private_rsvp, private_access, status, sxsw_mode
              )
              values (
                %s,%s,%s,%s,%s,%s::jsonb,
                %s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s::jsonb,%s,%s
              )
              returning candidate_id
            """, (
                source_id,
                source_name,
                source_url,
                source_class,
                raw_text,
                json.dumps(extracted),
                extracted.get("title"),
                extracted.get("start_time"),
                extracted.get("end_time"),
                extracted.get("venue_name"),
                extracted.get("city"),
                extracted.get("artist_names") or [],
                extracted.get("ticket_link"),
                extracted.get("rsvp_link"),
                bool(extracted.get("is_private_rsvp", False)),
                json.dumps(extracted.get("private_access") or {}),
                "needs_review",
                bool(sxsw_mode),
            ))
            cid = cur.fetchone()[0]
        conn.commit()
    return str(cid)


def stamp_gate_verdict(
    candidate_id: str,
    *,
    status: str,
    gate_reason: str,
    required_next: str,
    expected_status: str,
    cur=None,
) -> bool:
    """Persist a gate verdict onto the candidate ROW (status + reason +
    required_next), exactly the columns the human ops action stamps
    (api/ops_candidates.py add_evidence). Stamping is CLASSIFICATION, never
    publication: the only status this writes toward publishing is
    'ready_to_promote', which merely makes the candidate VISIBLE to the two
    custody-holding publish paths (the ratified autopromote pass and the
    authenticated ops promote) — both re-run their own gates before acting
    (defense in depth). Without this write the gate verdict lived only in the
    replay log, so the DB population autopromote selects was structurally
    empty (2026-08-05 diagnosis: examined=0 forever, and /ops per-item
    stamping was the rejected per-item-approval loop in disguise).
    COMPARE-AND-SWAP (evaluator finding, PR #182 r2): the update fires ONLY
    while the row still holds `expected_status` — if ops, a dispute, or any
    adjudication moved the row between the caller's read and this write, the
    update matches 0 rows and returns False, and the NEWER trust state wins
    (a gate verdict computed against a stale snapshot must never erase an
    adjudicated one). Callers must treat False as "skip loudly", never retry
    blindly. Pass `cur` to reuse an open transaction; otherwise a
    short-lived connection is opened and committed.
    """
    sql = """
      update event_candidate
      set status=%s, gate_reason=%s, required_next=%s, updated_at=now()
      where candidate_id=%s and status=%s
    """
    params = (status, gate_reason, required_next, candidate_id, expected_status)
    if cur is not None:
        cur.execute(sql, params)
        return cur.rowcount == 1
    with db() as conn:
        with conn.cursor() as own:
            own.execute(sql, params)
            stamped = own.rowcount == 1
        conn.commit()
    return stamped


def add_evidence(candidate_id: str, source_class: str, source_name: str, source_url: str, quote: str = "") -> str:
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              insert into candidate_evidence(candidate_id, source_class, source_name, source_url, quote)
              values (%s,%s,%s,%s,%s)
              returning evidence_id
            """, (candidate_id, source_class, source_name, source_url, quote))
            eid = cur.fetchone()[0]
        conn.commit()
    return str(eid)


def record_ai_degradation(payload: Dict[str, Any]) -> None:
    """Persist an AI-extraction degradation event to audit_log so a transient
    provider failure is observable in ops, never invisibly conflated with a
    genuine "no event found". Used as the provider's audit_hook."""
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into audit_log(actor_type, action, entity_type, payload)
                values ('system','ai_extraction_degraded','source',%s::jsonb)
                """,
                (json.dumps(payload),))
        conn.commit()


def list_candidate_source_classes(candidate_id: str) -> List[str]:
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("select source_class from candidate_evidence where candidate_id=%s", (candidate_id,))
            return [r[0] for r in cur.fetchall()]


def _load_gate_signals(cur, candidate_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Read the REAL stored extraction + evidence-derived gate signals for a
    candidate on `cur`. Shared body of load_candidate_gate_signals so a caller
    already inside a transaction (worker.promote) can run the exact same load on
    its own cursor and gate on the same snapshot it promotes from.
    """
    cur.execute(
        """
        select extracted, start_time, venue_name, is_private_rsvp
        from event_candidate where candidate_id=%s
        """,
        (candidate_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"candidate not found: {candidate_id}")
    extracted, start_time, venue_name, is_private_rsvp = row
    extracted = dict(extracted or {})
    # The dedicated column is authoritative: fold it in so a private/RSVP event
    # can never look public to the gate because of a stale jsonb copy.
    extracted["is_private_rsvp"] = bool(is_private_rsvp) or bool(extracted.get("is_private_rsvp"))

    # Distinct non-null start-time claims across the candidate's own column and
    # its stored extracted payload; >1 distinct value is a real cross-signal
    # conflict for trust_gate3 (which ESCALATEs rather than PASSing).
    start_times: List[str] = []
    if start_time is not None:
        start_times.append(start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time))
    ex_start = extracted.get("start_time")
    if ex_start:
        start_times.append(str(ex_start))

    # Dedupe hint from real stored data: another live candidate naming the same
    # venue at the same start_time is a genuine "two candidates, one slot"
    # ambiguity a human should resolve before publish.
    dedupe_ambiguous = False
    if venue_name and start_time is not None:
        cur.execute(
            """
            select count(*) from event_candidate
            where candidate_id <> %s
              and lower(venue_name) = lower(%s)
              and start_time = %s
              and status in ('needs_review', 'ready_to_promote')
            """,
            (candidate_id, venue_name, start_time),
        )
        dedupe_ambiguous = cur.fetchone()[0] > 0

    return extracted, {"start_times": start_times, "dedupe_ambiguous": dedupe_ambiguous}


def load_candidate_gate_signals(candidate_id: str, cur=None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load a candidate's REAL stored extraction + evidence signals for gate3.

    Returns (extracted, evidence_signals) where `extracted` is the stored
    `extracted` jsonb (carrying `_provenance.validation_error` and the
    authoritative `is_private_rsvp`) and `evidence_signals` is
    {"start_times": [...], "dedupe_ambiguous": bool}. This is the single seam
    the orchestrator and the promotion guard use so gate3 sees actual stored
    facts — never a test-only injected shortcut. Pass `cur` to reuse an open
    transaction; otherwise a short-lived connection is opened.
    """
    if cur is not None:
        return _load_gate_signals(cur, candidate_id)
    with db() as conn:
        with conn.cursor() as own:
            return _load_gate_signals(own, candidate_id)
