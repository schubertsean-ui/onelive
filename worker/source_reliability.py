"""Adjusts per-source reliability score based on outcomes (false positives decay weight).
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/source_reliability.py)
"""
import os
import psycopg2

DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")


def db():
    return psycopg2.connect(DB_DSN)


def adjust_source_reliability(source_id: str, delta: float):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
              insert into source_reliability (source_id, reliability_score)
              values (%s, 0.5)
              on conflict (source_id) do nothing
            """, (source_id,))
            cur.execute("""
              update source_reliability
              set reliability_score = greatest(0, least(1, reliability_score + %s)),
                  last_updated = now()
              where source_id=%s
            """, (delta, source_id))
        conn.commit()
