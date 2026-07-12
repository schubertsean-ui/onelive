"""Duplicate detection for canonical events (same venue + overlapping time window).
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/dedupe.py)
"""
from typing import List
import os

import psycopg2


DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def db():
    return psycopg2.connect(DB_DSN)


_DUP_SQL = """
  select event_id
  from event
  where venue_id=%s
    and start_time between %s - interval '%s minutes'
                    and %s + interval '%s minutes'
"""


def find_possible_duplicates(venue_id: str, start_time, window_minutes: int = 90, cur=None) -> List[str]:
    """Return ids of existing canonical events that may duplicate this one.

    Pass `cur` to run inside the caller's transaction (so the dedupe check shares
    a consistent snapshot with any entities just resolved). If omitted, a
    short-lived read-only connection is opened.
    """
    params = (venue_id, start_time, window_minutes, start_time, window_minutes)
    if cur is not None:
        cur.execute(_DUP_SQL, params)
        return [str(r[0]) for r in cur.fetchall()]
    with db() as conn:
        with conn.cursor() as own:
            own.execute(_DUP_SQL, params)
            return [str(r[0]) for r in own.fetchall()]
