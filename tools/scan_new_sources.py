#!/usr/bin/env python3
"""Source scanner v1 — find event-producing sources the catalog doesn't know yet.

Founder-directed (2026-08-04): "we should have a source scanner agent whose job
is to search the web periodically i.e. doing broad yet focused searches for all
of our categories and all of our keywords … so that we are constantly
identifying new sources as new artists start up new venues"; and the proving
case (2026-08-05): "have you just done a web search of 'city' live music
venues and 'city' bars … Saxon Pub is an Austin institution" — which was NOT
in the catalog until the Eventbrite harvest stumbled onto it.

Method: run a category × term query pack through the Brave Search API
(licensed programmatic use of a search index — the same lane as
search_discover_eventbrite.py; founder-ratified provider switch 2026-08-05,
Google refused the account), collect result domains, and DIFF them against
the committed source catalog. Output: NEW domains only, each with the queries
that surfaced it and example page titles — CANDIDATES for human curation into
the catalog. Nothing is fetched from the found sites here and nothing enters
the pipeline until a curated catalog row exists (custody unchanged).

Requires BRAVE_SEARCH_API_KEY. Bounded by --max-queries (Brave free plan:
2,000/month at 1 req/s). Fail-loud: a missing key exits 2; zero results across all queries
exit 3 (quota/config — never an empty green). Zero NEW domains with results
present exits 0 honestly (catalog already covers what search surfaced).

Usage: python tools/scan_new_sources.py [--city "Austin"] [--max-queries 20]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse

from tools.search_api import MissingKey, SearchError, api_key, search, web_results

CATALOG_DEFAULT = "sources/master_sources_catalog_120.json"

# The founder's query shapes, per catalog category family. Deliberately plain
# phrases a person would type — the point is breadth, not cleverness.
QUERY_PACK = [
    "live music venues",
    "bars with live music",
    "music venue calendar",
    "comedy club",
    "theater performances calendar",
    "art gallery openings",
    "museum events calendar",
    "dance hall",
    "brewery live music events",
    "winery events",
    "coffee shop open mic",
    "bookstore author events",
    "farmers market events",
    "community center events calendar",
    "church concert series",
    "university events calendar",
    "poetry reading open mic",
    "trivia night bars",
    "festival calendar",
    "record store in-store performance",
]

# Domains that can never be a first-party event source: platforms, socials,
# aggregators we already treat separately, and generic press. Kept small and
# obvious — everything else is left for HUMAN curation to judge.
PLATFORM_DOMAINS = {
    "facebook.com", "instagram.com", "x.com", "twitter.com", "tiktok.com",
    "youtube.com", "yelp.com", "tripadvisor.com", "reddit.com", "wikipedia.org",
    "eventbrite.com", "ticketmaster.com", "seatgeek.com", "stubhub.com",
    "bandsintown.com", "songkick.com", "meetup.com", "google.com",
    "linktr.ee", "spotify.com", "apple.com", "expedia.com", "opentable.com",
}


def norm_domain(url: str) -> str | None:
    """Registrable-ish domain of a result URL (www stripped, lowercased)."""
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return None
    host = host.lower().lstrip(".")
    return host[4:] if host.startswith("www.") else (host or None)


def catalog_domains(catalog: list[dict]) -> set[str]:
    """Domains the catalog already covers (from each entry's base_url)."""
    out = set()
    for s in catalog:
        d = norm_domain(s.get("base_url") or "")
        if d:
            out.add(d)
    return out


def is_platform(domain: str) -> bool:
    """True for platform/aggregator domains that are never first-party sources."""
    return any(domain == p or domain.endswith("." + p) for p in PLATFORM_DOMAINS)


def main(argv=None) -> int:
    """Run the query pack, diff result domains against the catalog, emit JSON."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--city", default="Austin",
                    help='market prefix for every query (default "Austin")')
    ap.add_argument("--max-queries", type=int, default=20,
                    help="API calls this run (Brave free plan: 2,000/month)")
    ap.add_argument("--catalog", default=CATALOG_DEFAULT)
    args = ap.parse_args(argv)

    try:
        api_key()
    except MissingKey as exc:
        print(str(exc), file=sys.stderr)
        return 2

    with open(args.catalog, encoding="utf-8") as fh:
        known = catalog_domains(json.load(fh))

    found: dict[str, dict] = {}
    calls = 0
    failures = 0
    total_results = 0
    for term in QUERY_PACK[: args.max_queries]:
        q = f"{args.city} {term}"
        calls += 1
        try:
            page = search(q, count=20)
        except SearchError as exc:
            failures += 1
            print(f"query {q!r}: failed ({exc})", file=sys.stderr)
            continue
        except Exception as exc:  # noqa: BLE001 — per-call report; zero-total fails below
            failures += 1
            print(f"query {q!r}: failed ({exc})", file=sys.stderr)
            continue
        for item in web_results(page):
            total_results += 1
            d = norm_domain(item["url"])
            if not d or d in known or is_platform(d):
                continue
            entry = found.setdefault(d, {"domain": d, "queries": [],
                                         "example_titles": [], "example_urls": []})
            if q not in entry["queries"]:
                entry["queries"].append(q)
            if len(entry["example_titles"]) < 3:
                entry["example_titles"].append(item["title"][:120])
                entry["example_urls"].append(item["url"])

    if total_results == 0:
        print(f"0 search results across {calls} call(s) ({failures} failed) — "
              "quota/config problem; failing loud (never an empty green).",
              file=sys.stderr)
        return 3

    out = {
        "city": args.city,
        "api_calls": calls,
        "calls_failed": failures,
        "results_seen": total_results,
        "catalog_domains": len(known),
        "new_domain_candidates": sorted(
            found.values(), key=lambda e: -len(e["queries"])),
    }
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    print(f"scan: {len(found)} NEW domain candidate(s) from {total_results} "
          f"results across {calls} queries ({failures} failed); catalog knew "
          f"{len(known)} domains.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
