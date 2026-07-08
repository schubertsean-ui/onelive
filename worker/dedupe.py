"""Duplicate detection for canonical events (same venue + overlapping time window).
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/dedupe.py)
"""
import os
import psycopg2
from typing import List

DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def db():
    return psycopg2.connect(DB_DSN)


def find_possible_duplicates(venue_id: str, start_time, window_minutes: int = 90) -> List[str]:
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              select event_id
              from event
              where venue_id=%s
                and start_time between %s - interval '%s minutes'
                                and %s + interval '%s minutes'
            """, (venue_id, start_time, window_minutes, start_time, window_minutes))
            return [str(r[0]) for r in cur.fetchall()]
