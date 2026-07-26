#!/usr/bin/env python3
"""Build the CAPCOG venue TARGET LIST — the denominator coverage is measured against.

Founder, 2026-07-26: "Use TABC but there [are gobs] of other sources — we've
already been over this several times... All the answers are already in our
content."

Correct on both counts, so this builds the denominator in LAYERS, starting with
the layer that needs no network and no credential — the catalogue this project
already curated:

  layer 1  CATALOG   sources/master_sources_catalog_120.json — 116 curated
                     Austin/CAPCOG sources, 51 of them venue calendars, each
                     already vetted as a real first-party venue or institution.
                     Available RIGHT NOW, offline. This is a FLOOR, not the
                     universe: it is the set we chose to track.

  layer 2  TABC      Texas Alcoholic Beverage Commission licensed premises
                     (data.texas.gov), filtered to the ten CAPCOG counties.
                     Authoritative for bars and music venues; needs egress, so
                     it runs where the importers run, not in the dev sandbox.

  layer 3  PLACES    Google Places, for the venue types TABC cannot see —
                     theatres, museums, libraries, galleries. Needs the
                     founder's existing key.

Layers merge by (name, city); every target records which layer produced it, so
the denominator can never quietly become "whatever we happened to find". A
target whose county cannot be resolved is written to a SEPARATE unresolved list
rather than being assigned a plausible county — an invented county would inflate
one county's coverage and hide a gap in another.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from worker.region.capcog import (  # noqa: E402
    CAPCOG_PLACES,
    CAPCOG_COUNTIES,
    county_for_place,
    normalize_place,
)

CATALOG = REPO / "sources" / "master_sources_catalog_120.json"
OUT = REPO / "sources" / "capcog_venue_targets.json"

# Catalog categories that name a PLACE a person can physically attend. Ticketing
# aggregators, social accounts and search benchmarks are excluded: they are
# channels, not venues, and counting them would inflate the denominator with
# things that have no address.
VENUE_CATEGORIES = {
    "venue_calendar", "university_calendar", "library_calendar",
    "city_calendar", "festival_feed",
}


def from_catalog(catalog: list) -> tuple:
    """Layer 1. Returns (targets, unresolved)."""
    targets: list = []
    unresolved: list = []
    for row in catalog:
        if row.get("category") not in VENUE_CATEGORIES:
            continue
        name = (row.get("name") or "").strip()
        if not name:
            continue
        county = normalize_place(row.get("county"))
        city = row.get("city")
        resolved_by = "county_field"
        if county not in CAPCOG_COUNTIES and city:
            county, resolved_by = county_for_place(city), "city_field"
        if county not in CAPCOG_COUNTIES:
            # READ the name, do not guess from it. "Mohawk Austin" and
            # "Paramount Theatre (Austin)" state their city in the title; that
            # is evidence on the row, not an assumption about where a venue
            # probably is. Longest place name first so "Round Rock" is not
            # matched as "Round Top" would be, and the match must sit on a word
            # boundary so "Austintatious" cannot resolve to Austin.
            for place in sorted(CAPCOG_PLACES, key=len, reverse=True):
                if re.search(rf"\b{re.escape(place)}\b", name.lower()):
                    county, resolved_by = CAPCOG_PLACES[place], "name_text"
                    city = city or place
                    break
        entry = {
            "name": name,
            "city": city,
            "county": county,
            "county_resolved_by": resolved_by if county in CAPCOG_COUNTIES else None,
            "source_layer": "catalog",
            "catalog_id": row.get("id"),
            "url": row.get("base_url"),
            "cultural_domain": row.get("cultural_domain"),
        }
        (targets if county in CAPCOG_COUNTIES else unresolved).append(entry)
    return targets, unresolved


def merge(existing: list, incoming: list) -> list:
    """Merge across layers. First layer wins, so a hand-curated catalog entry is
    never overwritten by a bulk import of the same venue.

    Evaluator blocker (Gemini seat): the key used to be (name, city) on both
    sides. Layer 1 entries mostly have NO city — the catalog states a county —
    so a Travis venue with city null would not dedupe against the same venue
    arriving from TABC with city "austin", and the denominator would carry the
    venue TWICE. A denominator that double-counts is a silently wrong
    denominator, which is the whole thing this file exists to avoid.

    So: name is the identity, city only separates when BOTH sides state one and
    they disagree. A city-less entry absorbs the same-named incoming one rather
    than duplicating it.
    """
    def name_of(t):
        return (t.get("name") or "").strip().lower()

    by_name: dict = {}
    for t in existing:
        by_name.setdefault(name_of(t), set()).add(normalize_place(t.get("city")) or "")

    out = list(existing)
    for t in incoming:
        n, c = name_of(t), normalize_place(t.get("city")) or ""
        known = by_name.get(n)
        if known is not None and (c in known or "" in known or not c):
            continue          # same venue already present
        by_name.setdefault(n, set()).add(c)
        out.append(t)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", default=str(CATALOG))
    ap.add_argument("--tabc", help="JSON of TABC rows (layer 2, fetched where "
                                   "egress exists)")
    ap.add_argument("--places", help="JSON of Google Places rows (layer 3)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    catalog = json.loads(pathlib.Path(args.catalog).read_text(encoding="utf-8"))
    if isinstance(catalog, dict):
        catalog = catalog.get("sources") or catalog.get("catalog") or []

    targets, unresolved = from_catalog(catalog)
    layers = {"catalog": len(targets)}

    for flag, layer in ((args.tabc, "tabc"), (args.places, "places")):
        if not flag:
            continue
        rows = json.loads(pathlib.Path(flag).read_text(encoding="utf-8"))
        incoming: list = []
        for r in rows:
            county = normalize_place(r.get("county")) or county_for_place(r.get("city"))
            if county not in CAPCOG_COUNTIES:
                continue
            incoming.append({
                "name": r.get("name"), "city": r.get("city"), "county": county,
                "source_layer": layer,
            })
        before = len(targets)
        targets = merge(targets, incoming)
        layers[layer] = len(targets) - before

    per_county: dict = {c: 0 for c in sorted(CAPCOG_COUNTIES)}
    for t in targets:
        per_county[t["county"]] += 1

    doc = {
        "generated_by": "tools/build_capcog_targets.py",
        "is_complete_universe": False,
        "completeness_note": (
            "FLOOR, not the universe. Layer 1 is the curated catalog — the "
            "venues this project chose to track — so coverage against it "
            "answers 'are we ingesting what we already know about?', NOT 'what "
            "share of CAPCOG venues exist?'. Layers 2 (TABC) and 3 (Places) "
            "raise it toward the real universe. Report the layer set with any "
            "coverage figure."),
        "layers_present": sorted(layers),
        "counts_added_per_layer": layers,
        "target_count": len(targets),
        "per_county": per_county,
        "unresolved_county_count": len(unresolved),
        "venues": targets,
        "unresolved_county": unresolved,
    }
    pathlib.Path(args.out).write_text(json.dumps(doc, indent=2) + "\n",
                                      encoding="utf-8")

    print(f"build_capcog_targets: {len(targets)} target venue(s) -> {args.out}")
    print(f"  layers: {layers}")
    for county, n in per_county.items():
        print(f"    {county:<12} {n}")
    if unresolved:
        print(f"  county UNRESOLVED (not assigned a plausible county, listed "
              f"separately): {len(unresolved)}")
        for u in unresolved[:10]:
            print(f"    - {u['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
