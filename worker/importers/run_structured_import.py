#!/usr/bin/env python3
"""Run the structured first-party feed import: read the master source catalog →
select entries that plausibly publish a machine-readable calendar (ICS / JSON-LD)
→ fetch + parse + classify each into the 22 cultural domains → upsert into
`licensed_event`. Deterministic, no AI. Runs on GitHub Actions (egress reaches the
public calendars; the dev sandbox is network-blocked).

These are FIRST-PARTY sources (venue / university / library / civic / museum) that
publish their OWN schedule as structured data — an authoritative anchor, so rows
are 'confirmed' by construction and flow through the separate licensed_event store
WITHOUT the AI-extraction / human-promote path.

Fail-loud discipline:
  * Missing DSN on a real (non-dry-run) write fails LOUD (worker.db_config).
  * ONE source yielding zero events does NOT fail the run — it is LOGGED (a venue
    calendar can legitimately be empty or briefly unreachable; the others still
    land). But if EVERY selected source yields zero, that is a systemic breakage
    (bad selection, an API-shape/JSON-LD-markup change across the board, or
    normalization drift) — the run FAILS, never a silent green no-op.

Usage:
  python -m worker.importers.run_structured_import [--catalog PATH] [--only id,id]
      [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import pathlib
from collections import Counter

from worker.db_config import resolve_dsn
from worker.importers.structured_feed import import_source

log = logging.getLogger("structured_import")

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_CATALOG = REPO / "sources" / "master_sources_catalog_120.json"

# `allowed`/`access_method` tokens that indicate a source plausibly exposes a
# machine-readable calendar (ICS or JSON-LD). Conservative on PURPOSE: we only
# reach for sources that advertise structured data, never every public web page.
_STRUCTURED_ALLOWED = {
    "ics_feed_if_offered", "localist_json_feed", "feed_if_offered",
    "ics_upload", "partner_export", "official_feed",
}
_STRUCTURED_ACCESS_TOKENS = ("ics", "localist", "feed")


def _is_structured_candidate(entry: dict) -> bool:
    """True when a catalog entry advertises a structured calendar AND has a URL to
    fetch. base_url may be an HTML calendar page — import_source auto-detects and
    parses whatever embedded JSON-LD (or a served .ics) it finds."""
    if not entry.get("base_url"):
        return False
    allowed = {str(a).lower() for a in (entry.get("allowed") or [])}
    if allowed & _STRUCTURED_ALLOWED:
        return True
    access = str(entry.get("access_method") or "").lower()
    return any(tok in access for tok in _STRUCTURED_ACCESS_TOKENS)


def _select(catalog: list[dict], only: set[str], limit: int | None) -> list[dict]:
    picks = [e for e in catalog if _is_structured_candidate(e)]
    if only:
        picks = [e for e in picks if str(e.get("id")) in only]
    if limit is not None:
        picks = picks[:limit]
    return picks


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", default=str(DEFAULT_CATALOG),
                    help="path to the master source catalog JSON")
    ap.add_argument("--only", default="",
                    help="comma-separated catalog ids to restrict to (subset of the "
                         "structured candidates)")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap the number of sources fetched (smoke runs)")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + parse + summarize, but do NOT write the DB")
    args = ap.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        log.error("--limit must be >= 1 — failing closed.")
        return 2

    catalog_path = pathlib.Path(args.catalog)
    if not catalog_path.exists():
        log.error("catalog %s does not exist — cannot select sources. Failing closed.",
                  catalog_path)
        return 2
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        log.error("catalog %s is not valid JSON (%s) — failing closed.", catalog_path, exc)
        return 2

    only = {t.strip() for t in args.only.split(",") if t.strip()}
    sources = _select(catalog, only, args.limit)
    if not sources:
        log.error("no structured-feed candidates selected from %s (only=%s) — the "
                  "catalog has no ICS/JSON-LD sources matching, or --only excluded "
                  "them all. Failing closed.", catalog_path, sorted(only) or "-")
        return 2

    log.info("scope: %d first-party structured-feed source(s) (ICS / JSON-LD) from %s",
             len(sources), catalog_path.name)

    all_norm: list[dict] = []
    per_source: Counter = Counter()
    zero_sources: list[str] = []
    for entry in sources:
        sid = str(entry.get("id"))
        url = entry.get("base_url")
        domain_hint = entry.get("cultural_domain")
        try:
            norm = import_source(url, source_name=sid, cultural_domain=domain_hint)
        except OSError as exc:
            # A single source being unreachable is logged, not fatal — the others
            # still import. (Not a swallowed error: it is surfaced in the run log.)
            log.warning("source %-26s FETCH FAILED (%s): %s", sid, url, exc)
            zero_sources.append(sid)
            continue
        per_source[sid] = len(norm)
        if not norm:
            log.warning("source %-26s yielded 0 events (%s) — logged, not fatal.", sid, url)
            zero_sources.append(sid)
            continue
        log.info("source %-26s %4d events  (%s)", sid, len(norm), domain_hint or "unclassified")
        all_norm.extend(norm)

    by_domain = Counter(n["category"] for n in all_norm)
    by_provider = Counter(n["source_provider"] for n in all_norm)
    log.info("Structured import: %d source(s) selected, %d yielded zero, %d events total",
             len(sources), len(zero_sources), len(all_norm))
    log.info("By parse provider: %s", dict(by_provider))
    for dom, c in by_domain.most_common():
        log.info("  %-18s %d", dom, c)

    # Location-data coverage (calendars rarely carry coordinates; be honest).
    with_addr = sum(1 for n in all_norm if n.get("venue_address"))
    with_city = sum(1 for n in all_norm if n.get("venue_city"))
    with_venue = sum(1 for n in all_norm if n.get("venue_name"))
    log.info("Location coverage: venue %d/%d, address %d/%d, city %d/%d",
             with_venue, len(all_norm), with_addr, len(all_norm), with_city, len(all_norm))

    # A real-data importer must not exit green on nothing. ONE empty source is
    # tolerated (logged above); EVERY source empty is a systemic failure.
    if not all_norm:
        log.error("normalized 0 events across ALL %d selected source(s) — a systemic "
                  "breakage (bad selection, blanket JSON-LD/ICS markup change, or "
                  "normalization drift). Failing loud.", len(sources))
        return 3

    if args.dry_run:
        log.info("dry-run: no DB write")
        return 0

    import psycopg2

    from worker.importers.licensed_store import upsert_events
    conn = psycopg2.connect(resolve_dsn())  # fail loud on missing DSN
    try:
        written = upsert_events(conn, all_norm)
    finally:
        conn.close()
    log.info("upserted %d events into licensed_event", written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
