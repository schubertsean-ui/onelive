#!/usr/bin/env python3
"""Run the SeatGeek licensed-feed import: fetch real CAPCOG SeatGeek events →
classify into the 22 cultural domains → upsert into `licensed_event`.
Deterministic, no AI. Runs on GitHub Actions (egress reaches SeatGeek; the dev
sandbox is network-blocked). Fails LOUD on missing key/DSN — never silently
no-ops. Uses the logging module so counts/errors are observable in the run log
and aggregation. Mirrors worker.importers.run_licensed_import (Ticketmaster).

Usage: python -m worker.importers.run_seatgeek_import [--max-pages N] [--dry-run]
"""
from __future__ import annotations

import argparse
import logging
import os
from collections import Counter

from worker.db_config import resolve_dsn
from worker.importers.normalize import normalize_seatgeek
from worker.importers.seatgeek import CAPCOG_RANGE_MILES, fetch_events_capcog

log = logging.getLogger("seatgeek_import")


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-pages", type=int, default=10,
                    help="pages per time-window (SeatGeek per_page<=100)")
    ap.add_argument("--windows", type=int, default=6,
                    help="number of rolling ~monthly windows to sweep (full forward calendar)")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + normalize + summarize, but do NOT write the DB")
    args = ap.parse_args(argv)

    if args.max_pages < 1 or args.windows < 1:
        log.error("--max-pages and --windows must be >= 1 — failing closed.")
        return 2

    cid = os.environ.get("SEATGEEK_CLIENT_ID")
    if not cid:
        log.error("SEATGEEK_CLIENT_ID is not set — cannot import. Failing closed.")
        return 2

    log.info("scope: CAPCOG ~%d mi radius around Austin, sweeping %d rolling ~monthly "
             "windows (full forward calendar so every category is pulled). "
             "Radius still approximate (R-025).", CAPCOG_RANGE_MILES, args.windows)
    raws = list(fetch_events_capcog(cid, windows=args.windows, per_window_pages=args.max_pages, per_page=100))
    norm = [n for n in (normalize_seatgeek(e) for e in raws) if n]
    by_domain = Counter(n["category"] for n in norm)

    log.info("SeatGeek CAPCOG import: fetched %d, normalized %d (skipped %d missing id/title)",
             len(raws), len(norm), len(raws) - len(norm))
    for dom, c in by_domain.most_common():
        log.info("  %-18s %d", dom, c)

    # Location-data coverage (answers "is real geo actually captured?").
    with_geo = sum(1 for n in norm if n.get("venue_lat") is not None and n.get("venue_lng") is not None)
    with_addr = sum(1 for n in norm if n.get("venue_address"))
    with_city = sum(1 for n in norm if n.get("venue_city"))
    total = len(norm) or 1
    log.info("Location coverage: coords %d/%d (%d%%), address %d/%d, city %d/%d",
             with_geo, len(norm), round(100 * with_geo / total), with_addr, len(norm), with_city, len(norm))

    # Emit the greppable UNMAPPED marker per distinct event type so coverage
    # gaps are visible and actionable (which provider taxonomy to map next).
    from collections import Counter as _C

    from worker.importers.domain_map import unmapped as _unmapped
    unm = _C()
    for n in norm:
        if n.get("category") == "unmapped":
            t = (n.get("raw") or {}).get("type") or "?"
            unm[t] += 1
    for etype, n in unm.most_common(20):
        log.info("%s  (x%d)", _unmapped("seatgeek", etype), n)

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
