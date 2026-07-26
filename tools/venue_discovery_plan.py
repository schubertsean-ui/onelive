#!/usr/bin/env python3
"""Generate the web-search plan that finds venues and sources a licence file misses.

Founder directive, 2026-07-26: "Surely your work accesses multiple sources to
verify what a place is, including something as simple as a web search, a places
search, using all the local sources we've identified eg am fm radio, local
periodicals, etc."

WHY THIS EXISTS. The denominator's layer 2 is TABC — every establishment
licensed to serve mixed beverages. That is 2,873 rooms and it is genuinely
authoritative, but it is authoritative about ALCOHOL, not about live
performance. It cannot see:

  - the Texas dance hall circuit (Freyburg Hall, Sengelmann, Swiss Alp)
  - county fairgrounds and civic pavilions
  - theatres, museums, libraries, galleries
  - all-ages rooms, record stores, coffee houses with stages
  - performing-arts nonprofits that present in halls they do not own

and it cannot see the CHANNELS the outer counties actually publish through:
chamber-of-commerce calendars, visitor bureaus, local periodicals, and radio
station event pages. Seven of the ten CAPCOG counties had zero curated sources
before this pass; the first two searches found a 1912 dance hall and a polka
newspaper with a live music calendar.

WHAT THIS FILE IS AND IS NOT. It generates QUERIES. It does not run them — web
search is an agent capability, not something a worker process can call — so the
honest division is: this module owns the plan (deterministic, reviewable,
portable), the agent runs it, and the results land in sources/discovered/ with
the query and the asserting page recorded on every row.

PORTABILITY IS THE POINT. Nothing about Austin is encoded in the method. Give it
a different county list and the same plan finds the same source classes in any
metro — which is what "a consistent source for any locale" requires.

TRUST. Every result is a LEAD. A search result is a far weaker claim than a
licence record, and this pipeline never pretends otherwise: discovered rows
enter the registry with origin `web_discovery` and score NEVER_TRIED until a
real fetch proves the feed exists and parses. Nothing discovered here reaches a
reader without passing the same gate as everything else.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from worker.region.capcog import CAPCOG_COUNTIES, CAPCOG_PLACES  # noqa: E402

# Locale-independent. Each template describes a CLASS of thing to look for; the
# {place} slot is filled per county/town. Ordered roughly by yield-per-query
# observed on the first pass.
QUERY_TEMPLATES = [
    ("venue_calendar",
     "{place} live music venue calendar"),
    ("community_board",
     "{place} chamber of commerce events calendar"),
    ("city_civic_calendar",
     "{place} visitor bureau things to do live music"),
    ("directory",
     "{place} music venue directory list of venues"),
    ("local_media",
     "{place} local newspaper events listings live music"),
    ("broadcast_calendar",
     "{place} radio station community events calendar"),
    ("performing_arts",
     "{place} theatre performing arts center season schedule"),
    ("museum_gallery",
     "{place} museum gallery events programs calendar"),
    ("library_calendar",
     "{place} public library events calendar"),
    ("festival_feed",
     "{place} annual festival fair rodeo schedule"),
    ("venue_calendar",
     "{place} all ages venue no alcohol coffee shop with stage"),
    ("venue_calendar",
     "{place} dance hall historic venue live music"),
]

# Classes a liquor licence structurally cannot enumerate. Used to report which
# part of the plan is closing a KNOWN blind spot rather than duplicating TABC.
BLIND_TO_ALCOHOL_LICENCE = {
    "performing_arts", "museum_gallery", "library_calendar",
    "broadcast_calendar", "directory", "local_media",
}


def places_for(county: str) -> list:
    """The towns this county publishes under, largest-name-first for stability."""
    return sorted((p for p, c in CAPCOG_PLACES.items() if c == county), key=str)


def build_plan(counties, per_county_places: int = 3) -> list:
    """(county, place, source_class, query) for every county x template.

    The COUNTY itself is always queried, plus its largest few towns: a county
    name finds the county-level channels (tourism, fairgrounds), a town name
    finds the rooms. Querying only one of the two misses half the population.
    """
    plan: list = []
    for county in sorted(counties):
        targets = [county] + places_for(county)[:per_county_places]
        seen: set = set()
        for place in targets:
            if place in seen:
                continue
            seen.add(place)
            label = f"{place} texas" if place == county else f"{place} texas"
            for source_class, template in QUERY_TEMPLATES:
                plan.append({
                    "county": county,
                    "place": place,
                    "source_class": source_class,
                    "closes_licence_blind_spot": source_class in BLIND_TO_ALCOHOL_LICENCE,
                    "query": template.format(place=label),
                })
    return plan


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--counties", nargs="*", default=sorted(CAPCOG_COUNTIES),
                    help="counties to plan for (defaults to CAPCOG's ten)")
    ap.add_argument("--places-per-county", type=int, default=3)
    ap.add_argument("--only-blind-spots", action="store_true",
                    help="only the classes a liquor licence cannot enumerate")
    ap.add_argument("--json", action="store_true", help="emit the plan as JSON")
    args = ap.parse_args(argv)

    unknown = sorted(set(args.counties) - set(CAPCOG_COUNTIES))
    if unknown:
        # Planning searches for a county outside the market is how out-of-market
        # venues get discovered and then quietly imported.
        raise SystemExit(
            f"venue_discovery_plan: FAIL — not CAPCOG counties: {unknown}. "
            f"The market is the ten named counties; searching outside it is how "
            f"out-of-market venues enter the denominator.")

    plan = build_plan(args.counties, args.places_per_county)
    if args.only_blind_spots:
        plan = [q for q in plan if q["closes_licence_blind_spot"]]

    if args.json:
        print(json.dumps(plan, indent=2))
        return 0

    print(f"venue_discovery_plan: {len(plan)} query/queries across "
          f"{len(args.counties)} county/counties")
    blind = sum(1 for q in plan if q["closes_licence_blind_spot"])
    print(f"  {blind} of them target a class TABC structurally cannot see")
    print()
    current = None
    for q in plan:
        if q["county"] != current:
            current = q["county"]
            print(f"  == {current} ==")
        mark = "*" if q["closes_licence_blind_spot"] else " "
        print(f"   {mark} [{q['source_class']:<20}] {q['query']}")
    print()
    print("  * = a population a liquor licence cannot enumerate")
    print("  Run these as web searches; record results in sources/discovered/ "
          "with the query and asserting URL on every row.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
