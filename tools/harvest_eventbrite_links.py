#!/usr/bin/env python3
"""Harvest Eventbrite organizer/event links from OUR OWN cataloged source pages.

Founder-approved discovery path #1 (2026-08-04, "Focus on 1 and 2"): Eventbrite's
edge 405-blocks datacenter crawlers, so we never fetch eventbrite.com here at
all. Instead we read the pages of sources ALREADY in the ratified catalog
(sources/master_sources_catalog_120.json — Austin venues, festivals, city/
university calendars, local media) and collect the Eventbrite links THOSE pages
publish: "/o/<slug>-<id>" organizer links and "/e/...-<id>" event links. A venue
putting its own Eventbrite link on its own website is first-party provenance for
that link — nothing is guessed, nothing is fetched from a party that said no.

Each catalog entry is fetched only if its own `allowed` list grants a public_*
access method — the catalog's per-source access contract is enforced here, not
just documented. Event ids feed tools/resolve_eventbrite_event_orgs.py (the
official API, founder token) to obtain the organizer behind each event.

Fail-loud contract: ZERO fetched pages exits 3 (network/blocking problem —
never an empty green). Zero LINKS across successfully fetched pages exits 0
with explicit zero counts printed: that is a true observation about our
sources, not a harness failure. Bounded (--max-sources), polite (per-fetch
delay), identified UA.

Usage: python tools/harvest_eventbrite_links.py [--max-sources N] [--catalog PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request

CATALOG_DEFAULT = "sources/master_sources_catalog_120.json"
UA = ("Mozilla/5.0 (compatible; 1LiveSourceDiscovery/1.0; "
      "+https://1live.co; contact schubertsean@gmail.com)")

# The catalog access methods that permit reading a source's public pages. A
# source granting only feeds/API/partner access is NOT fetched by this tool.
PUBLIC_ACCESS = {"public_calendar_pages", "public_pages", "public_event_pages"}

# Eventbrite links as third-party pages publish them (scheme optional — pages
# and widgets print bare or protocol-relative forms; org/event id = trailing
# digit run). Domain pinned to eventbrite.com; the lookbehind blocks lookalike
# prefixes ("fakeeventbrite.com").
_ORG_RE = re.compile(
    r"(?<![a-z0-9-])(?:www\.)?eventbrite\.com/o/([a-z0-9\-%]*?)-(\d{6,})",
    re.I)
_EVENT_RE = re.compile(
    r"(?<![a-z0-9-])(?:www\.)?eventbrite\.com/e/[a-z0-9\-%]*?(\d{9,})",
    re.I)


def eligible_sources(catalog: list[dict]) -> list[dict]:
    """Catalog entries this tool may fetch: a base_url plus a public_* access
    grant in the entry's OWN allowed list (the per-source access contract)."""
    out = []
    for s in catalog:
        if not s.get("base_url"):
            continue
        if not PUBLIC_ACCESS.intersection(s.get("allowed") or []):
            continue
        # eventbrite.com itself is in the catalog as a ticketing entry; its
        # pages are exactly what the edge blocks — and what we don't need.
        if "eventbrite." in s["base_url"]:
            continue
        out.append(s)
    return out


def extract_links(html: str) -> tuple[dict[str, str], set[str]]:
    """Pull (organizer_id -> slug_name, event_ids) from one page's HTML."""
    orgs: dict[str, str] = {}
    for slug, oid in _ORG_RE.findall(html):
        orgs.setdefault(oid, slug.replace("-", " ").strip())
    events = {eid for eid in _EVENT_RE.findall(html)}
    return orgs, events


def fetch(url: str, timeout: int = 20) -> str:
    """One page, honest identified UA + standard headers."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
                   "*/*;q=0.8"),
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main(argv=None) -> int:
    """Fetch eligible catalog pages, collect Eventbrite org/event links, emit JSON."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-sources", type=int, default=0,
                    help="cap on catalog pages fetched (0 = all eligible)")
    ap.add_argument("--catalog", default=CATALOG_DEFAULT,
                    help=f"source catalog path (default {CATALOG_DEFAULT})")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="seconds between fetches (politeness)")
    args = ap.parse_args(argv)

    with open(args.catalog, encoding="utf-8") as fh:
        catalog = json.load(fh)
    sources = eligible_sources(catalog)
    if args.max_sources > 0:
        sources = sources[: args.max_sources]
    if not sources:
        print("no eligible sources in the catalog — nothing to fetch",
              file=sys.stderr)
        return 3

    org_names: dict[str, str] = {}
    org_found_on: dict[str, set[str]] = {}
    event_found_on: dict[str, set[str]] = {}
    fetched = 0
    failed = 0
    for s in sources:
        try:
            html = fetch(s["base_url"])
        except Exception as exc:  # noqa: BLE001 — per-source report; zero-total fails below
            failed += 1
            print(f"{s['id']}: fetch failed ({exc})", file=sys.stderr)
            continue
        fetched += 1
        orgs, events = extract_links(html)
        for oid, name in orgs.items():
            org_names.setdefault(oid, name)
            org_found_on.setdefault(oid, set()).add(s["id"])
        for eid in events:
            event_found_on.setdefault(eid, set()).add(s["id"])
        time.sleep(args.delay)

    if fetched == 0:
        print(f"0 of {len(sources)} source pages fetched — network or blocking "
              "problem; failing loud (never an empty green).", file=sys.stderr)
        return 3

    out = {
        "sources_eligible": len(sources),
        "sources_fetched": fetched,
        "sources_failed": failed,
        "organizers": [
            {"org_id": oid, "name": org_names.get(oid) or "(slug not on page)",
             "found_on": sorted(found)}
            for oid, found in sorted(org_found_on.items(),
                                     key=lambda kv: -len(kv[1]))
        ],
        "event_ids": [
            {"event_id": eid, "found_on": sorted(found)}
            for eid, found in sorted(event_found_on.items(),
                                     key=lambda kv: -len(kv[1]))
        ],
    }
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    print(f"harvest: {len(out['organizers'])} organizer id(s), "
          f"{len(out['event_ids'])} event id(s) across {fetched} fetched / "
          f"{failed} failed page(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
