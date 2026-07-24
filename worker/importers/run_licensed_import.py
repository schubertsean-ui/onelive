#!/usr/bin/env python3
"""Run the licensed-feed import: fetch real CAPCOG Ticketmaster events → classify
into the 22 cultural domains → upsert into `licensed_event`. Deterministic, no
AI. Runs on GitHub Actions (egress reaches Ticketmaster; the dev sandbox is
network-blocked). Fails LOUD on missing key/DSN — never silently no-ops. Uses the
logging module so counts/errors are observable in the run log and aggregation.

Usage: python -m worker.importers.run_licensed_import [--max-pages N] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import os
from collections import Counter

from worker.db_config import resolve_dsn
from worker.importers.normalize import normalize_ticketmaster
from worker.importers.ticketmaster import fetch_events

log = logging.getLogger("licensed_import")


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-pages", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + normalize + summarize, but do NOT write the DB")
    args = ap.parse_args(argv)

    if args.max_pages < 1:
        log.error("--max-pages must be >= 1 (got %d) — failing closed.", args.max_pages)
        return 2

    key = os.environ.get("TICKETMASTER_API_KEY")
    if not key:
        log.error("TICKETMASTER_API_KEY is not set — cannot import. Failing closed.")
        return 2

    raws = list(fetch_events(key, size=100, max_pages=args.max_pages))
    norm = [n for n in (normalize_ticketmaster(e) for e in raws) if n]
    by_domain = Counter(n["category"] for n in norm)

    log.info("Ticketmaster CAPCOG import: fetched %d, normalized %d", len(raws), len(norm))
    for dom, c in by_domain.most_common():
        log.info("  %-18s %d", dom, c)

    # Location-data coverage (answers "is real geo actually captured?").
    with_geo = sum(1 for n in norm if n.get("venue_lat") is not None and n.get("venue_lng") is not None)
    with_addr = sum(1 for n in norm if n.get("venue_address"))
    with_city = sum(1 for n in norm if n.get("venue_city"))
    total = len(norm) or 1
    log.info("Location coverage: coords %d/%d (%d%%), address %d/%d, city %d/%d",
             with_geo, len(norm), round(100 * with_geo / total), with_addr, len(norm), with_city, len(norm))

    # Emit the greppable UNMAPPED marker per distinct classification so coverage
    # gaps are visible and actionable (which provider taxonomy to map next).
    from collections import Counter as _C

    from worker.importers.domain_map import unmapped as _unmapped
    unm = _C()
    for n in norm:
        if n.get("category") == "unmapped":
            cls = (n.get("raw") or {}).get("classifications") or [{}]
            c0 = cls[0] if cls else {}
            seg = (c0.get("segment") or {}).get("name")
            gen = (c0.get("genre") or {}).get("name")
            unm[f"{seg} / {gen}"] += 1
    for key, n in unm.most_common(20):
        log.info("%s  (x%d)", _unmapped("ticketmaster", key), n)

    # A real-data importer must not exit green on nothing — zero events means a
    # bad key, a provider/CAPCOG scoping error, an API-shape change, or
    # normalization drift. Fail LOUD instead of a silent no-op.
    if not norm:
        log.error("normalized 0 events from %d fetched — bad key / provider query / "
                  "CAPCOG scoping / API-shape or normalization drift. Failing loud.", len(raws))
        return 3

    if args.dry_run:
        log.info("dry-run: no DB write")
        return 0

    import psycopg2

    from worker.importers.licensed_store import upsert_events
    conn = psycopg2.connect(resolve_dsn())
    try:
        written = upsert_events(conn, norm)
    finally:
        conn.close()
    log.info("upserted %d events into licensed_event", written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
