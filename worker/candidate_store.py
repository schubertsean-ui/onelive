"""DB access layer for event_candidate / candidate_evidence.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/candidate_store.py)
"""
from typing import Optional, Dict, Any, List
import json
import os

import psycopg2


DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def db():
    return psycopg2.connect(DB_DSN)


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
