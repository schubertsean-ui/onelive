#!/usr/bin/env python3
"""Dump the per-source evidence the scorecard scores: rows ingested, fetches tried.

Founder directive, 2026-07-26: the scorecard must be "an ongoing performance
measure". Without this producer it is not one — `source_scorecard.py` prints
UNKNOWN for every row forever, because UNKNOWN is what it honestly reports when
no evidence is supplied. This is the step that supplies it.

Runs where the database is reachable (CI), not in the network-less dev sandbox,
and writes two plain JSON files the scorecard reads.

THE JOIN IS THE WHOLE RISK. The scorecard attributes evidence by REGISTRY ID.
The database speaks three other vocabularies:

    licensed_event.source_provider   'ticketmaster' | 'seatgeek'
    event_candidate.source_name      the catalog's human name
    raw_fetch -> source.name         the catalog's human name

An identifier that fails to map does not raise anything by itself — it simply
contributes to no source, and the scorecard then reports a live feed as
NEVER_TRIED with zero throughput. That is `failure-reads-as-empty`, and it is
the single most likely way this file lies. So every unmapped identifier is
collected and the run EXITS NON-ZERO naming them. A partial dump is worse than
no dump, because a partial dump looks like a measurement.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

REGISTRY = REPO / "sources" / "source_registry.json"

# Provider strings the licensed importers write, mapped to registry ids. Small
# and explicit: these come from our own code, so an unknown one means an
# importer landed without being registered — worth failing on, not guessing.
PROVIDER_TO_REGISTRY_ID = {
    "ticketmaster": "ticketmaster_discovery",
    "seatgeek": "seatgeek",
    "eventbrite": "eventbrite_api",
}


def _norm(value) -> str:
    return " ".join(str(value or "").strip().lower().split())


def build_name_index(registry: dict) -> dict:
    """Normalised name -> registry id, for the DB's human-name vocabularies."""
    index: dict = {}
    for s in registry.get("sources", []):
        for key in (s.get("name"), s.get("id"), s.get("code_id")):
            n = _norm(key)
            if n:
                index.setdefault(n, s["id"])
    return index


def resolve(identifier, index: dict, unmapped: set):
    """Registry id for a DB identifier, or None — recording the miss."""
    n = _norm(identifier)
    if not n:
        return None
    hit = PROVIDER_TO_REGISTRY_ID.get(n) or index.get(n)
    if hit is None:
        unmapped.add(str(identifier))
    return hit


def read_evidence(conn, index: dict, unmapped: set) -> tuple:
    rows: list = []
    attempts: list = []
    with conn.cursor() as cur:
        # Licensed rows carry their provider directly.
        cur.execute("""
            select source_provider, venue_name, venue_city
              from licensed_event
        """)
        for provider, venue, city in cur.fetchall():
            sid = resolve(provider, index, unmapped)
            if sid:
                rows.append({"source_name": sid, "venue_name": venue,
                             "venue_city": city})

        # Candidate rows carry the catalog's human name. Only PROMOTED
        # candidates count as throughput: a candidate sitting in needs_review is
        # a source that produced something, not a source that delivered an event
        # to a user, and conflating the two would credit a feed for work the
        # gate has not accepted.
        cur.execute("""
            select source_name, venue_name, city
              from event_candidate
             where promoted_event_id is not null
        """)
        for name, venue, city in cur.fetchall():
            sid = resolve(name, index, unmapped)
            if sid:
                rows.append({"source_name": sid, "venue_name": venue,
                             "venue_city": city})

        # Fetch attempts. raw_fetch records a fetch that PRODUCED CONTENT — see
        # the caveat emitted alongside this dump; there is no failed-attempt row
        # to read, so `ok` is true by construction here rather than by measure.
        cur.execute("""
            select s.name, rf.fetched_at
              from raw_fetch rf
              join source s on s.source_id = rf.source_id
        """)
        for name, at in cur.fetchall():
            sid = resolve(name, index, unmapped)
            if sid:
                attempts.append({"source_name": sid, "ok": True,
                                 "at": at.isoformat() if at else None})
    return rows, attempts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", default=str(REGISTRY))
    ap.add_argument("--rows-out", default="source_rows.json")
    ap.add_argument("--attempts-out", default="source_attempts.json")
    args = ap.parse_args(argv)

    dsn = os.environ.get("ONELIVE_DB_DSN")
    if not dsn:
        raise SystemExit(
            "dump_source_evidence: FAIL — ONELIVE_DB_DSN is empty. Writing "
            "empty evidence files would make every source read as NEVER_TRIED, "
            "which is a claim about the sources rather than about the missing "
            "connection.")

    registry = json.loads(pathlib.Path(args.registry).read_text(encoding="utf-8"))
    index = build_name_index(registry)
    unmapped: set = set()

    import psycopg2  # imported here so --help works without the dependency
    conn = psycopg2.connect(dsn)
    try:
        rows, attempts = read_evidence(conn, index, unmapped)
    finally:
        conn.close()

    pathlib.Path(args.rows_out).write_text(json.dumps(rows, indent=2),
                                           encoding="utf-8")
    pathlib.Path(args.attempts_out).write_text(json.dumps(attempts, indent=2),
                                               encoding="utf-8")
    print(f"dump_source_evidence: {len(rows)} row(s), {len(attempts)} attempt(s)")
    print("  CAVEAT, carried with the numbers: raw_fetch records only fetches "
          "that returned content.")
    print("  There is no failed-attempt table, so TRIED_FAILING cannot yet be "
          "distinguished from NEVER_TRIED.")
    print("  A source that is attempted and always denied reads as NEVER_TRIED "
          "until failures are recorded (R-054).")

    if unmapped:
        print(f"\ndump_source_evidence: FAIL — {len(unmapped)} database "
              f"identifier(s) map to no registry source:", file=sys.stderr)
        for u in sorted(unmapped):
            print(f"    {u!r}", file=sys.stderr)
        print("  Their rows were dropped, so the scorecard would report those "
              "sources as dead while they are live. Add them to the catalog, or "
              "to PROVIDER_TO_REGISTRY_ID, and re-run.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
