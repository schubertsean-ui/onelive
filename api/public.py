"""Public read API: /tonight and /events. Never filters on confidence state —
disputed events are always shown as disputed, never dropped (CLAUDE.md 4-state
confidence model; guarded by a structural test in tests/test_gates.py).
"""
from datetime import datetime, timedelta, timezone
import os

from fastapi import APIRouter
import psycopg2


DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")

router = APIRouter(tags=["public"])


def db():
    return psycopg2.connect(DB_DSN)


@router.get("/events")
def events(limit: int = 50):
    with db() as conn:
        with conn.cursor() as cur:
            # No confidence filter here: every state (including 'disputed') is
            # returned. Disputed events are shown as disputed, never dropped.
            cur.execute("""
              select event_id, venue_id, artist_ids, start_time, end_time, status, confidence,
                     is_private_rsvp, private_access, notes
              from event
              where status='scheduled'
              order by start_time asc
              limit %s
            """, (limit,))
            rows = cur.fetchall()
    return [{
        "event_id": str(r[0]),
        "venue_id": str(r[1]) if r[1] else None,
        "artist_ids": [str(x) for x in (r[2] or [])],
        "start_time": r[3].isoformat() if r[3] else None,
        "end_time": r[4].isoformat() if r[4] else None,
        "status": r[5],
        "confidence": r[6],
        "is_private_rsvp": bool(r[7]),
        "private_access": r[8] or {},
        "notes": r[9],
    } for r in rows]


@router.get("/tonight")
def tonight(city: str = "Austin", hours: int = 12, limit: int = 50):
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=hours)
    with db() as conn:
        with conn.cursor() as cur:
            # Confidence only affects ordering, never inclusion. 'disputed' events
            # sort last but are always returned (shown as disputed, never dropped).
            cur.execute("""
              select e.event_id, e.start_time, e.confidence, e.notes,
                     v.venue_id, v.name, v.city, e.artist_ids
              from event e
              left join venue v on v.venue_id = e.venue_id
              where e.status='scheduled'
                and e.start_time >= %s
                and e.start_time <= %s
                and (v.city is null or v.city = %s)
              order by
                case e.confidence
                  when 'confirmed' then 1
                  when 'likely' then 2
                  when 'unverified' then 3
                  when 'disputed' then 4
                  else 5
                end asc,
                e.start_time asc
              limit %s
            """, (now, window_end, city, limit))
            rows = cur.fetchall()
    return [{
        "event_id": str(r[0]),
        "start_time": r[1].isoformat() if r[1] else None,
        "confidence": r[2],
        "notes": r[3],
        "venue": {"venue_id": str(r[4]) if r[4] else None, "name": r[5], "city": r[6]},
        "artist_ids": [str(x) for x in (r[7] or [])],
    } for r in rows]
