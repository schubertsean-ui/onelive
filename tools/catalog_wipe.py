#!/usr/bin/env python3
"""Empty the live catalog. Founder 2026-09-10: wipe, then one ingest.

Deletes happenings only. Pack, source, and place tables stay.
"""
from __future__ import annotations

import os
import sys

import psycopg2

TABLES = (
    "candidate_evidence",
    "event_candidate",
    "event",
    "licensed_event",
)


def main() -> int:
    dsn = os.environ.get("ONELIVE_DB_DSN", "").strip()
    if not dsn:
        print("ONELIVE_DB_DSN missing", file=sys.stderr)
        return 2
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()
    before = {}
    for table in TABLES:
        cur.execute(f"select count(*) from {table}")
        before[table] = cur.fetchone()[0]
    print("before", before)
    cur.execute(
        "truncate table candidate_evidence, event_candidate, event, "
        "licensed_event restart identity cascade"
    )
    after = {}
    for table in TABLES:
        cur.execute(f"select count(*) from {table}")
        after[table] = cur.fetchone()[0]
    print("after", after)
    if any(after.values()):
        conn.rollback()
        print("wipe failed; rolled back", after, file=sys.stderr)
        return 1
    conn.commit()
    print("catalog empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
