#!/usr/bin/env python3
"""Discover Austin Eventbrite organizers via the Google Programmable Search API.

Founder-approved discovery path #2 (2026-08-04, "Focus on 1 and 2"): search
engines license their index for programmatic queries — this is the legitimate
automated way to find `eventbrite.com/o/...` organizer pages without fetching
eventbrite.com (whose edge blocks datacenter crawlers) and without deception.

Uses Google's Custom Search JSON API (100 free queries/day):
  GET https://www.googleapis.com/customsearch/v1?key=..&cx=..&q=..&start=N
with queries like `site:eventbrite.com/o "austin"`. Organizer ids are read off
result URLs/snippets — published by Eventbrite, surfaced by Google, never
guessed. Output is CANDIDATES for human review before anything is committed.

Requires (repo secrets in CI; env vars locally):
  GOOGLE_CSE_KEY — API key: https://developers.google.com/custom-search/v1/introduction
  GOOGLE_CSE_CX  — Programmable Search Engine id ("search the entire web" on):
                   https://programmablesearchengine.google.com/

Fail-loud contract: missing credentials exit 2; zero organizer ids across all
queried pages exits 3 (quota/config problem or empty index — never an empty
green). Bounded: --max-queries caps API calls (each returns <=10 results).

Usage: python tools/search_discover_eventbrite.py [--max-queries 8] [--terms austin]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/customsearch/v1"
# Scheme optional (snippets print bare "eventbrite.com/o/..."); domain pinned
# to eventbrite.com; lookbehind blocks lookalike prefixes ("fakeeventbrite.com").
_ORG_RE = re.compile(
    r"(?<![a-z0-9-])(?:www\.)?eventbrite\.com/o/([a-z0-9\-%]*?)-(\d{6,})",
    re.I)


def search_page(key: str, cx: str, query: str, start: int, timeout: int = 20) -> dict:
    """One Custom Search API call (documented endpoint, keyed access)."""
    qs = urllib.parse.urlencode({"key": key, "cx": cx, "q": query,
                                 "start": start, "num": 10})
    req = urllib.request.Request(f"{API}?{qs}",
                                 headers={"User-Agent": "1LiveSourceDiscovery/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def extract_orgs(payload: dict) -> dict[str, str]:
    """organizer_id -> slug name, read from result links/snippets."""
    text = json.dumps(payload)
    out: dict[str, str] = {}
    for slug, oid in _ORG_RE.findall(text):
        out.setdefault(oid, urllib.parse.unquote(slug).replace("-", " ").strip())
    return out


def main(argv=None) -> int:
    """Query the search API for Austin organizer pages; emit JSON candidates."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-queries", type=int, default=8,
                    help="API calls this run (free tier: 100/day)")
    ap.add_argument("--terms", default="austin",
                    help='locality terms, comma-separated (default "austin")')
    args = ap.parse_args(argv)

    key = os.environ.get("GOOGLE_CSE_KEY", "").strip()
    cx = os.environ.get("GOOGLE_CSE_CX", "").strip()
    if not key or not cx:
        print("GOOGLE_CSE_KEY / GOOGLE_CSE_CX missing — create a free key at "
              "https://developers.google.com/custom-search/v1/introduction and "
              "an engine id at https://programmablesearchengine.google.com/",
              file=sys.stderr)
        return 2

    terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    queries = [f'site:eventbrite.com/o "{t}"' for t in terms]
    orgs: dict[str, str] = {}
    calls = 0
    failures = 0
    for q in queries:
        start = 1
        while calls < args.max_queries:
            calls += 1
            try:
                page = search_page(key, cx, q, start)
            except Exception as exc:  # noqa: BLE001 — per-call report; zero-total fails below
                failures += 1
                print(f"query {q!r} start={start}: failed ({exc})", file=sys.stderr)
                break
            orgs.update({k: v for k, v in extract_orgs(page).items()
                         if k not in orgs})
            nxt = (page.get("queries") or {}).get("nextPage")
            if not nxt:
                break
            start = nxt[0].get("startIndex", start + 10)
            time.sleep(1)
        if calls >= args.max_queries:
            break

    if not orgs:
        print(f"0 organizer ids from {calls} API call(s) ({failures} failed) — "
              "quota/config problem or empty results; failing loud (never an "
              "empty green).", file=sys.stderr)
        return 3

    out = {"api_calls": calls, "calls_failed": failures,
           "organizers": [{"org_id": oid, "name": name or "(slug not in result)"}
                          for oid, name in sorted(orgs.items())]}
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    print(f"search: {len(orgs)} organizer id(s) from {calls} call(s).",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
