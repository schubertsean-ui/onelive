#!/usr/bin/env python3
"""Run the Eventbrite licensed-feed import: poll a configured list of KNOWN
Eventbrite organizer/venue ids → classify into the 22 cultural domains → upsert
into `licensed_event`. Deterministic, no AI. Runs on GitHub Actions (egress
reaches Eventbrite; the dev sandbox is network-blocked). Fails LOUD on missing
token/DSN and never exits green on zero events — a silent no-op would hide a bad
token, an empty/mis-configured id list, or an API-shape change.

Eventbrite REMOVED public event search in 2020, so there is nothing to keyword/geo
query: the trusted organizer/venue id list IS the query. Supply it explicitly via
--org-ids / --venue-ids, or via a small newline/comma file with --ids-file. An
empty id list fails closed.

Usage:
  python -m worker.importers.run_eventbrite_import --org-ids 111,222 [--dry-run]
  python -m worker.importers.run_eventbrite_import --ids-file config/eventbrite_orgs.txt
  python -m worker.importers.run_eventbrite_import --venue-ids 333 --kind venue
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
from collections import Counter

from worker.db_config import resolve_dsn
from worker.importers.eventbrite import fetch_known
from worker.importers.normalize import normalize_eventbrite

log = logging.getLogger("eventbrite_import")


def _parse_ids(raw: str | None) -> list[str]:
    """Split a comma/whitespace/newline-separated id blob into a clean list."""
    if not raw:
        return []
    out: list[str] = []
    for tok in raw.replace(",", " ").split():
        tok = tok.strip()
        # Ignore blank lines and '#' comments in an --ids-file.
        if tok and not tok.startswith("#"):
            out.append(tok)
    return out


_PROVENANCE_PATH = (pathlib.Path(__file__).resolve().parent.parent.parent
                    / "sources" / "eventbrite_provenance.json")


def _provenance_event_ids(path: pathlib.Path = None) -> set[str]:
    """The harvest-bound event-id allow-list (sources/eventbrite_provenance.json).

    The event-id lane's trust boundary (evaluator findings, PR #178 r1+r2):
    the ids ARE the query, so an id that never came out of a REAL harvest of
    our own catalog pages must not reach the importer at all — otherwise
    arbitrary third-party events could enter licensed_event as trusted
    provider data. The registry's binding to real harvest evidence is
    AUTHENTICATED mechanically (tests/test_eventbrite_provenance_authentic.py
    re-verifies every listed id against the digest-pinned harvest artifact
    via the Actions API in trust-gate); founder curation is recorded in the
    file as honest provenance, deliberately not the load-bearing gate.
    Missing/unreadable registry fails CLOSED (an absent allow-list is an
    empty allow-list, never a bypass).
    """
    path = path or _PROVENANCE_PATH
    if not path.exists():
        raise RuntimeError(
            f"provenance registry {path} does not exist — the event-id lane "
            "has no allow-list without it; failing closed.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {e["event_id"] for e in data.get("event_ids", [])}


def _collect_ids(args) -> list[str]:
    ids: list[str] = []
    by_kind = {"organization": args.org_ids, "venue": args.venue_ids,
               "event": getattr(args, "event_ids", "")}
    ids += _parse_ids(by_kind[args.kind])
    if args.ids_file:
        p = pathlib.Path(args.ids_file)
        if not p.exists():
            raise RuntimeError(f"--ids-file {args.ids_file!r} does not exist — failing closed.")
        ids += _parse_ids(p.read_text())
    # De-dup while preserving order.
    seen: set[str] = set()
    return [i for i in ids if not (i in seen or seen.add(i))]


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--org-ids", default="",
                    help="comma/space-separated known Eventbrite organization ids to poll")
    ap.add_argument("--venue-ids", default="",
                    help="comma/space-separated known Eventbrite venue ids (with --kind venue)")
    ap.add_argument("--event-ids", default="",
                    help="comma/space-separated Eventbrite EVENT ids (with --kind event — "
                         "the harvest lanes produce these; the only id space the API "
                         "serves for third parties)")
    ap.add_argument("--ids-file", default=None,
                    help="path to a file of ids (newline/comma separated, '#' comments ok)")
    ap.add_argument("--kind", choices=("organization", "venue", "event"), default="organization",
                    help="which endpoint the ids address (default: organization)")
    ap.add_argument("--max-pages", type=int, default=20,
                    help="max continuation pages per polled id")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + normalize + summarize, but do NOT write the DB")
    args = ap.parse_args(argv)

    if args.max_pages < 1:
        log.error("--max-pages must be >= 1 — failing closed.")
        return 2

    token = os.environ.get("EVENTBRITE_TOKEN")
    if not token:
        log.error("EVENTBRITE_TOKEN is not set — cannot import. Failing closed. "
                  "(Founder-crucial new service credential; agents never mint keys.)")
        return 2

    ids = _collect_ids(args)
    if args.kind == "event":
        # Digits-only shape check first (Eventbrite event ids are numeric;
        # anything else can't be a harvested id and must not touch the URL
        # path), then the provenance allow-list — both fail closed.
        malformed = [i for i in ids if not i.isdigit()]
        if malformed:
            log.error("non-numeric event id(s) rejected: %s — failing closed.",
                      ", ".join(malformed))
            return 2
        allowed = _provenance_event_ids()
        rogue = [i for i in ids if i not in allowed]
        if rogue:
            log.error(
                "event id(s) not in the founder-reviewed provenance registry "
                "(sources/eventbrite_provenance.json): %s — the event-id lane "
                "imports ONLY harvested, reviewed ids. Failing closed.",
                ", ".join(rogue))
            return 2
    if not ids:
        log.error("no Eventbrite %s ids supplied (--org-ids/--venue-ids/--ids-file) — "
                  "there is no public search fallback, so an empty id list is a no-op. "
                  "Failing closed.", args.kind)
        return 2

    log.info("scope: polling %d known Eventbrite %s id(s) for live events "
             "(public search was removed in 2020 — the trusted id list IS the query).",
             len(ids), args.kind)
    raws = list(fetch_known(token, ids, kind=args.kind, max_pages=args.max_pages))
    norm = [n for n in (normalize_eventbrite(e) for e in raws) if n]
    by_domain = Counter(n["category"] for n in norm)

    log.info("Eventbrite import: fetched %d, normalized %d (skipped %d missing id/title)",
             len(raws), len(norm), len(raws) - len(norm))
    for dom, c in by_domain.most_common():
        log.info("  %-18s %d", dom, c)

    # Location-data coverage (answers "is real geo actually captured?").
    with_geo = sum(1 for n in norm if n.get("venue_lat") is not None and n.get("venue_lng") is not None)
    with_addr = sum(1 for n in norm if n.get("venue_address"))
    with_city = sum(1 for n in norm if n.get("venue_city"))
    log.info("Location coverage: coords %d/%d, address %d/%d, city %d/%d",
             with_geo, len(norm), with_addr, len(norm), with_city, len(norm))

    # Emit the greppable UNMAPPED marker per distinct category/subcategory so
    # coverage gaps are visible and actionable (which taxonomy to map next).
    from worker.importers.domain_map import unmapped as _unmapped
    unm = Counter()
    for n in norm:
        if n.get("category") == "unmapped":
            raw = n.get("raw") or {}
            cat = (raw.get("category") or {}).get("name")
            sub = (raw.get("subcategory") or {}).get("name")
            unm[f"{cat} / {sub}"] += 1
    for key, c in unm.most_common(20):
        log.info("%s  (x%d)", _unmapped("eventbrite", key), c)

    # A real-data importer must not exit green on nothing — zero normalized events
    # means a bad token, an empty/mis-scoped id list, an API-shape change, or
    # normalization drift. Fail LOUD instead of a silent no-op.
    if not norm:
        log.error("normalized 0 events from %d fetched — bad token / empty or wrong "
                  "id list / API-shape or normalization drift. Failing loud.", len(raws))
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
