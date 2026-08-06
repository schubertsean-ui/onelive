#!/usr/bin/env python3
"""Discover Austin Eventbrite organizers via the Brave Search API (licensed).

Founder-approved discovery path #2 (2026-08-04, "Focus on 1 and 2"): search
engines license their index for programmatic queries — this is the legitimate
automated way to find `eventbrite.com/o/...` organizer pages without fetching
eventbrite.com (whose edge blocks datacenter crawlers) and without deception.

Uses Brave's Web Search API via tools/search_api.py (founder-ratified
provider switch 2026-08-05 — Google's Custom Search refuses this account at
the account level; see docs/memory/decisions/). Queries like
`site:eventbrite.com/o "austin"`; organizer ids are read off result
URLs/snippets — published by Eventbrite, surfaced by the search index, never
guessed. Output is CANDIDATES for human review before anything is committed.

Requires (repo secret in CI; env var locally):
  BRAVE_SEARCH_API_KEY — https://api-dashboard.search.brave.com/ (Free plan:
                         2,000 queries/month, 1 request/second)

Fail-loud contract: a missing credential exits 2; zero organizer ids across
all queried pages exits 3 (quota/config problem or empty index — never an
empty green). Bounded: --max-queries caps API calls (each returns <=20
results).

Usage: python tools/search_discover_eventbrite.py [--max-queries 8] [--terms austin]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse

from tools.search_api import MissingKey, SearchError, api_key, search

# Scheme optional (snippets print bare "eventbrite.com/o/..."); domain pinned
# to eventbrite.com; lookbehind blocks lookalike prefixes ("fakeeventbrite.com").
_ORG_RE = re.compile(
    r"(?<![a-z0-9-])(?:www\.)?eventbrite\.com/o/([a-z0-9\-%]*?)-(\d{6,})",
    re.I)


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
                    help="API calls this run (Brave free plan: 2,000/month)")
    ap.add_argument("--terms", default="austin",
                    help='locality terms, comma-separated (default "austin")')
    args = ap.parse_args(argv)

    try:
        api_key()
    except MissingKey as exc:
        print(str(exc), file=sys.stderr)
        return 2

    terms = [t.strip() for t in args.terms.split(",") if t.strip()]
    queries = [f'site:eventbrite.com/o "{t}"' for t in terms]
    orgs: dict[str, str] = {}
    calls = 0
    failures = 0
    for q in queries:
        offset = 0
        while calls < args.max_queries:
            calls += 1
            try:
                page = search(q, count=20, offset=offset)
            except SearchError as exc:
                failures += 1
                print(f"  error body: {exc.body[:300]}", file=sys.stderr)
                print(f"query {q!r} offset={offset}: failed ({exc})", file=sys.stderr)
                break
            except Exception as exc:  # noqa: BLE001 — per-call report; zero-total fails below
                failures += 1
                print(f"query {q!r} offset={offset}: failed ({exc})", file=sys.stderr)
                break
            before = len(orgs)
            orgs.update({k: v for k, v in extract_orgs(page).items()
                         if k not in orgs})
            # Brave pages by offset (max 9); stop when a page adds nothing new
            # or yields no results — there is no explicit next-page cursor.
            if len(orgs) == before or not (page.get("web") or {}).get("results"):
                break
            offset += 1
            if offset > 9:
                break
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
