#!/usr/bin/env python3
"""Discover Austin Eventbrite ORGANIZER ids from Eventbrite's own public pages.

Eventbrite removed public event search from its API in 2020 — a curated,
trusted organizer-id list IS the query (worker/importers/run_eventbrite_import).
This tool builds that list's CANDIDATES honestly: it reads Eventbrite's public
Austin browse pages (the access method the ratified source catalog allows for
this source: "public_event_pages") and extracts organizer ids that EVENTBRITE
ITSELF publishes in page markup — ids are never guessed, never fabricated.

Runs on GitHub runners (the dev sandbox's egress policy blocks eventbrite.com).
Output: JSON to stdout — [{"org_id", "name", "seen": N}] sorted by frequency —
for human review before anything is committed; the committed list then feeds
the official API (with the founder-minted token) through the R-029 dry-run
before a single DB write.

Fail-loud: zero discovered ids exits 3 (page-shape drift or blocking), never an
empty green. Bounded: --max-pages caps the crawl; polite 1s delay between pages.

Usage: python tools/discover_eventbrite_orgs.py [--max-pages 8] [--city tx--austin]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from collections import Counter

BROWSE_URL = "https://www.eventbrite.com/d/{city}/all-events/?page={page}"
UA = ("Mozilla/5.0 (compatible; 1LiveSourceDiscovery/1.0; "
      "+https://1live.co; contact schubertsean@gmail.com)")

# Organizer ids as Eventbrite itself publishes them:
#   * organizer page hrefs:  /o/<slug>-<digits>
#   * embedded JSON fields:  "organizer_id": "<digits>"  /  "organizerId":"<digits>"
_HREF_RE = re.compile(r"/o/([a-z0-9\-]*?)-(\d{6,})", re.I)
_JSON_RE = re.compile(r'"organizer[_]?[iI]d"\s*:\s*"?(\d{6,})"?')
# Organizer display names near JSON ids when present.
_NAME_RE = re.compile(r'"organizer"\s*:\s*{[^{}]*?"name"\s*:\s*"([^"]{2,80})"[^{}]*?"id"\s*:\s*"?(\d{6,})"?')


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-pages", type=int, default=8,
                    help="browse pages to read (bounded, polite)")
    ap.add_argument("--city", default="tx--austin",
                    help="Eventbrite destination slug (default tx--austin)")
    args = ap.parse_args(argv)
    if args.max_pages < 1:
        print("--max-pages must be >= 1", file=sys.stderr)
        return 2

    ids: Counter[str] = Counter()
    slug_names: dict[str, str] = {}
    json_names: dict[str, str] = {}
    pages_ok = 0
    for page in range(1, args.max_pages + 1):
        url = BROWSE_URL.format(city=args.city, page=page)
        try:
            html = fetch(url)
        except Exception as exc:  # noqa: BLE001 — report and continue; total-zero fails below
            print(f"page {page}: fetch failed ({exc})", file=sys.stderr)
            continue
        pages_ok += 1
        for slug, oid in _HREF_RE.findall(html):
            ids[oid] += 1
            if slug and oid not in slug_names:
                slug_names[oid] = slug.replace("-", " ").strip()
        for oid in _JSON_RE.findall(html):
            ids[oid] += 1
        for name, oid in _NAME_RE.findall(html):
            json_names[oid] = name
            ids[oid] += 0  # name only; count comes from the id patterns
        time.sleep(1)

    if not ids:
        print(f"discovered 0 organizer ids across {pages_ok} fetched page(s) — "
              "page-shape drift or blocking; failing loud (never an empty green).",
              file=sys.stderr)
        return 3

    out = [
        {"org_id": oid,
         "name": json_names.get(oid) or slug_names.get(oid) or "(name not on page)",
         "seen": n}
        for oid, n in ids.most_common()
    ]
    json.dump({"city": args.city, "pages_fetched": pages_ok,
               "distinct_organizers": len(out), "organizers": out},
              sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
