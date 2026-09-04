"""DB access layer for event_candidate / candidate_evidence.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/candidate_store.py)
"""
from typing import Optional, Dict, Any, List, Tuple
import json

import psycopg2

from worker.db_config import resolve_dsn
from worker.identity import (
    IDENTITY_KEY,
    carried_identity,
    demote_door_addresses,
    read_identity,
)


def db():
    return psycopg2.connect(resolve_dsn())


def _with_identity(
    extracted: Dict[str, Any],
    raw_text: Any = None,
    *,
    source_url: Optional[str] = None,
) -> Dict[str, Any]:
    """`extracted` plus a canonical `_identity`, or unchanged when neither the
    payload nor the raw block states one.

    Two producers, in a fixed order, and the order is a rule about authority:

      1. the CALLER'S OWN payload (`worker/claim/intake.py` stating a
         claimant's row url, a structured parse stating an ICS `UID`);
      2. failing that, the identity CARRIED BY THE BLOCK the payload was
         extracted from — `raw_text` is the per-listing block
         `worker/segment.py` cut, and it remembers the `<a href>` or JSON-LD
         `url`/`@id` its own markup stated (`worker.identity.carry_identity`).

    The block is only ever a FALLBACK, never a merge: a payload that states an
    identity is the producer that knows what it is describing, and mixing a
    second source's fields into it could assemble an identity no one stated.
    A payload that states nothing takes the block's whole identity or none.

    THE BLOCK'S IDENTITY IS THEN CHECKED AGAINST THE PAGE IT CAME FROM
    (`demote_door_addresses`, founder Session Contract #59). A block that
    declares the very page it was read from has named the DOOR, not the night:
    a block carries an identity only when `worker/segment.py` found two or more
    listings on that page, so the page is a LIST by construction and its own
    address belongs to every listing on it. Left on `listing_url`/`source_href`
    it would answer SAME for two different nights on the adopt rung and license
    a write onto the wrong one — the founder's stated harm. It is MOVED to
    `entity_url` rather than dropped: the door is real, it is simply not a
    handle on a happening, and `identity_verdict` never reads it.

    ONLY THE BLOCK BRANCH IS DEMOTED, and the reason is specific to the two
    producers that actually reach this seam. An earlier version of this
    docstring justified the exemption by naming
    `worker/importers/structured_feed.py` as a per-event detail feed whose page
    IS its listing. THAT WAS FALSE — that module never calls `create_candidate`
    at all (it writes the licensed store), and an adversarial-review seat
    questioning the exemption is what sent me to check. The true reason is
    stronger, and it is about what `source_url` MEANS to each caller:

      * `worker/ai_extract.py` passes the crawled PAGE, which may hold many
        listings — so a payload url equal to it would indeed be a door. It
        cannot occur: the certified extraction schema states no
        identity-shaped field, pinned by a blocking test
        (`tests/test_identity_stack.py::
        test_the_certified_extraction_schema_states_no_identity_field`,
        re-asserted at this seam by
        `tests/test_entity_vs_happening_id.py::
        test_a_crawled_payload_states_no_identity_to_demote`), and the provider
        meta merged beside it is `_`-prefixed. Adding `url` to
        `worker/ai_models.py` turns that test RED and says why, so the branch
        is fail-closed rather than merely empty.
      * `api/claims.py` passes `source_url=listing.url or claim.feed_url`, so
        when a claimant states a url the page and the listing are THE SAME
        STRING by construction. Demoting there would move class E's ONLY
        identity — the url the venue typed into their own row — onto
        `entity_url` and leave the claim path with nothing. That is not a
        hypothetical cost: it is every claimed listing, and it is pinned by
        `tests/test_entity_vs_happening_id.py::
        test_a_claimed_listings_own_url_survives_being_its_own_source_url`.

    So the exemption is not "callers know best" in general. It is that neither
    caller can present the shape the demotion exists to catch, and that for one
    of them the demotion would be the defect.

    A COPY is returned rather than a mutation of the caller's dict: the caller
    (worker/ai_extract.py's fan-out, api/claims.py's loop) may hold the payload
    across events, and a shared dict that grows an `_identity` from one listing
    would attach it to the next.

    An identity ALREADY canonicalized is re-read from `_identity` and rewritten
    from itself, so a re-submitted candidate cannot end up with two disagreeing
    copies of its own id (red class: a tool rewriting a shared artifact must
    preserve the fields it does not own — here, by re-deriving from the field
    that owns the answer).
    """
    identity = read_identity(extracted)
    if not identity.stated_any:
        identity = demote_door_addresses(carried_identity(raw_text), source_url)
    if not identity.stated_any:
        return extracted
    out = dict(extracted)
    out[IDENTITY_KEY] = identity.as_dict()
    return out


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
    """Write one candidate. The single seam every producer goes through, which
    is why the identity canonicalization lives HERE rather than in each caller.

    `extracted` is stored with a canonical `_identity` sub-object holding
    whatever identity the CALLER'S OWN payload stated (an ICS `UID`, a
    schema.org `Event.url`/`@id`, a claimant's row url) or, failing that,
    whatever the BLOCK in `raw_text` carried from its own markup (a listing's
    anchor, a JSON-LD Event's url/@id — `worker/segment.py`) — see
    worker/identity.py for the three carriers and for what is deliberately NOT
    read as one. Nothing is invented: a listing that neither states an identity
    nor was cut from markup that stated one gets no `_identity` key at all, and
    the ladder then falls to its composite rung.

    The `_provenance` key on the same jsonb is the precedent for a namespaced
    machine-read sub-object, so this needs no migration, no new column and no
    change to any workflow that applies one.
    """
    extracted = _with_identity(extracted, raw_text, source_url=source_url)
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
                # str(), not the object: a segmented block reaches here as an
                # `IdentifiedBlock` (a str subclass carrying its identity), and
                # the driver is handed the plain text it has always been handed
                # rather than a subclass whose adaptation would be one more
                # thing to be right about. The identity has already been read
                # off it above, into the jsonb.
                str(raw_text) if raw_text is not None else None,
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
    COMPARE-AND-SWAP (evaluator findings, PR #182 r2+r3): the update fires
    ONLY while the row still holds `expected_status` AND is still UNSTAMPED
    (`gate_reason IS NULL`) — status alone is not enough, because an
    ESCALATED row deliberately keeps status='needs_review' while carrying
    its recorded reason, and a fresh verdict must never overwrite a recorded
    escalation/adjudication. If anything moved the row between the caller's
    read and this write, the update matches 0 rows and returns False, and
    the NEWER trust state wins
    (a gate verdict computed against a stale snapshot must never erase an
    adjudicated one). Callers must treat False as "skip loudly", never retry
    blindly. Pass `cur` to reuse an open transaction; otherwise a
    short-lived connection is opened and committed.
    """
    sql = """
      update event_candidate
      set status=%s, gate_reason=%s, required_next=%s, updated_at=now()
      where candidate_id=%s and status=%s and gate_reason is null
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
