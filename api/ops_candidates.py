"""Ops inbox API: list/review event candidates and the human promote action.

This is the one legitimate human-in-the-loop path that calls worker.promote
directly (see tools/trust_gate.py PROMOTE_IMPORT_ALLOWLIST) — an operator
reviews evidence, then promotes; the AI extraction layer never promotes.
"""
from typing import Any, Dict, List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import psycopg2

from api.deps import get_db, require_admin
from worker.gating import multi_confirm_gate
from worker.promote import promote_candidate




router = APIRouter(prefix="/ops", tags=["ops"])


class EvidenceIn(BaseModel):
    source_class: str
    source_name: str = ""
    source_url: str = ""
    quote: str = ""


@router.get("/candidates/inbox")
def inbox(status: str = "needs_review", admin=Depends(require_admin), conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("""
          select candidate_id, title, start_time, venue_name, city, status, gate_reason, required_next
          from event_candidate
          where status=%s
          order by created_at desc
          limit 200
        """, (status,))
        rows = cur.fetchall()
    return [{
        "candidate_id": str(r[0]),
        "title": r[1],
        "start_time": r[2].isoformat() if r[2] else None,
        "venue_name": r[3],
        "city": r[4],
        "status": r[5],
        "gate_reason": r[6],
        "required_next": r[7],
    } for r in rows]


@router.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: str, admin=Depends(require_admin), conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("""
          select candidate_id, extracted, raw_text, title, start_time, end_time, venue_name, city, artist_names,
                 ticket_link, rsvp_link, is_private_rsvp, private_access, status, sxsw_mode
          from event_candidate
          where candidate_id=%s
        """, (candidate_id,))
        r = cur.fetchone()
        if not r:
            raise HTTPException(404, "candidate not found")

        cur.execute("""
          select evidence_id, source_class, source_name, source_url, quote, captured_at
          from candidate_evidence
          where candidate_id=%s
          order by captured_at desc
        """, (candidate_id,))
        ev = cur.fetchall()
    return {
        "candidate": {
            "candidate_id": str(r[0]),
            "extracted": r[1],
            "raw_text": r[2],
            "title": r[3],
            "start_time": r[4].isoformat() if r[4] else None,
            "end_time": r[5].isoformat() if r[5] else None,
            "venue_name": r[6],
            "city": r[7],
            "artist_names": r[8] or [],
            "ticket_link": r[9],
            "rsvp_link": r[10],
            "is_private_rsvp": bool(r[11]),
            "private_access": r[12] or {},
            "status": r[13],
            "sxsw_mode": bool(r[14]),
        },
        "evidence": [{
            "evidence_id": str(e[0]),
            "source_class": e[1],
            "source_name": e[2],
            "source_url": e[3],
            "quote": e[4],
            "captured_at": e[5].isoformat() if e[5] else None
        } for e in ev]
    }


@router.post("/candidates/{candidate_id}/evidence")
def add_evidence(candidate_id: str, payload: EvidenceIn, admin=Depends(require_admin), conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("select sxsw_mode from event_candidate where candidate_id=%s", (candidate_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "candidate not found")
        sxsw_mode = bool(row[0])
        cur.execute("""
          insert into candidate_evidence(candidate_id, source_class, source_name, source_url, quote)
          values (%s,%s,%s,%s,%s)
        """, (candidate_id, payload.source_class, payload.source_name, payload.source_url, payload.quote))

        cur.execute("select source_class from candidate_evidence where candidate_id=%s", (candidate_id,))
        classes = [r[0] for r in cur.fetchall()]
        gate = multi_confirm_gate(classes, sxsw_mode=sxsw_mode)
        cur.execute("""
          update event_candidate
          set status=%s, gate_reason=%s, required_next=%s, updated_at=now()
          where candidate_id=%s
        """, (gate.status, gate.reason, gate.required_next, candidate_id))
        cur.execute("""
          insert into audit_log(actor_type, action, entity_type, entity_id, payload)
          values ('admin','add_evidence','candidate',%s,%s::jsonb)
        """, (candidate_id, json.dumps(payload.model_dump())))
    conn.commit()
    return {"ok": True}


@router.post("/candidates/{candidate_id}/promote")
def promote(candidate_id: str, admin=Depends(require_admin)):
    # promote_candidate uses its own DB connection for simplicity in v1
    try:
        event_id = promote_candidate(candidate_id)
        return {"ok": True, "event_id": event_id}
    except Exception as e:
        raise HTTPException(400, str(e))
