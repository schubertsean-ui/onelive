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

# Catalog categories that can contribute a target at all. Ticketing aggregators,
# social accounts and search benchmarks never do: they are channels with no
# address.
VENUE_CATEGORIES = {
    "venue_calendar", "university_calendar", "library_calendar",
    "city_calendar", "festival_feed",
}

# The launch metric is "X of Y CAPCOG VENUES". Admitting every row above as a
# venue made that number structurally false — "Visit Austin Events" is a city
# calendar, "Fusebox Festival" is an event, and "Austin Symphony Orchestra"
# performs in other people's halls. None of the three is a place a person can
# be at, and counting them inflated the denominator with things that can never
# be "covered" in the sense the metric means.
#
# Nothing is DROPPED. Every row stays in the file carrying a `target_kind`, and
# the coverage report scores against VENUE while listing the other kinds beside
# it. Silently filtering them would shrink the denominator invisibly — and
# because a smaller denominator RAISES the percentage, that is the direction
# that flatters us, which is exactly the direction that has to be declared.
KIND_VENUE = "venue"            # an addressable place a person attends
KIND_PRODUCER = "producer"      # programs events in venues it does not own
KIND_FESTIVAL = "festival"      # a recurring event, not a place
KIND_CHANNEL = "channel"        # a calendar feed covering many places

TARGET_KINDS = (KIND_VENUE, KIND_PRODUCER, KIND_FESTIVAL, KIND_CHANNEL)

KIND_BY_CATEGORY = {
    "venue_calendar": KIND_VENUE,
    "festival_feed": KIND_FESTIVAL,
    "university_calendar": KIND_CHANNEL,
    "library_calendar": KIND_CHANNEL,
    "city_calendar": KIND_VENUE,   # most are a specific museum/park; see overrides
}

# Read per row, because the catalog's category does not always describe the
# thing: several museums are filed under `city_calendar`, and several touring
# companies and annual events are filed under `venue_calendar`. Keyed on catalog
# id — a name match would be the name-only-county-collision class in another
# coat. A stale id fails the build rather than silently doing nothing.
KIND_OVERRIDE = {
    # Filed as venue_calendar, but they perform in halls they do not own.
    "austin_symphony": KIND_PRODUCER,
    "ballet_austin": KIND_PRODUCER,
    "austin_opera": KIND_PRODUCER,
    "tapestry_dance": KIND_PRODUCER,
    "golden_hornet": KIND_PRODUCER,
    "austin_chamber_music_center": KIND_PRODUCER,
    "haam": KIND_PRODUCER,
    "austin_history_center": KIND_PRODUCER,
    "austin_fc": KIND_PRODUCER,
    "round_rock_express": KIND_PRODUCER,
    "austin_spurs": KIND_PRODUCER,
    "txstate_presents": KIND_PRODUCER,
    "texas_performing_arts": KIND_PRODUCER,
    # Filed as venue_calendar / city_calendar, but they are annual events.
    "rodeo_austin": KIND_FESTIVAL,
    "sfc_farmers_market": KIND_FESTIVAL,
    # Filed as city_calendar, but they ARE a calendar for a whole city.
    "visit_austin": KIND_CHANNEL,
    "city_of_austin_events": KIND_CHANNEL,
}


def assert_overrides_are_live(catalog: list) -> None:
    """Every KIND_OVERRIDE id must still exist in the catalog.

    A stale override stops applying SILENTLY and the row reverts to its category
    default — a festival counted as a venue again, with nothing to notice it.
    Checked against the real catalog in main(), not inside from_catalog, so that
    a caller passing a subset (tests, a single-layer run) is not failed for rows
    it never claimed to include.
    """
    stale = sorted(set(KIND_OVERRIDE) - {r.get("id") for r in catalog})
    if stale:
        raise SystemExit(
            f"build_capcog_targets: FAIL — KIND_OVERRIDE names catalog id(s) "
            f"that no longer exist: {stale}. A stale override stops applying "
            f"silently and the row reverts to its category default, which is "
            f"how a festival gets counted as a venue again.")


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
            "target_kind": KIND_OVERRIDE.get(
                row.get("id"), KIND_BY_CATEGORY[row["category"]]),
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

    # Keyed by (name, COUNTY). r2 collapsed on name alone when either side
    # lacked a city, which r3 caught as the other half of the same defect: a
    # city-less Travis entry would absorb a genuinely different same-named
    # venue in Llano, UNDERCOUNTING the denominator. County is the coarse
    # location every layer actually carries, so it is the safe discriminator.
    by_key: dict = {}
    for t in existing:
        by_key.setdefault((name_of(t), t.get("county")), set()).add(
            normalize_place(t.get("city")) or "")

    out = list(existing)
    for t in incoming:
        n, county = name_of(t), t.get("county")
        c = normalize_place(t.get("city")) or ""
        known = by_key.get((n, county))
        if known is not None and (c in known or "" in known or not c):
            continue          # same venue, same county — already present
        by_key.setdefault((n, county), set()).add(c)
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
        # A dict with neither key is CORRUPT INPUT, not an empty catalog
        # (evaluator blocker r2). Coercing it to [] produced a successful,
        # empty denominator — schema drift rendering as "CAPCOG has no venues".
        catalog = catalog.get("sources") or catalog.get("catalog")
        if catalog is None:
            raise SystemExit(
                f"build_capcog_targets: FAIL — {args.catalog} is a JSON object "
                f"with neither a 'sources' nor a 'catalog' array. That is a "
                f"corrupt/changed catalog, not an empty one; refusing to emit a "
                f"denominator from it.")
    if not isinstance(catalog, list):
        raise SystemExit(
            f"build_capcog_targets: FAIL — {args.catalog} is not a list of rows.")

    assert_overrides_are_live(catalog)
    targets, unresolved = from_catalog(catalog)
    layers = {"catalog": len(targets)}

    for flag, layer in ((args.tabc, "tabc"), (args.places, "places")):
        if not flag:
            continue
        rows = json.loads(pathlib.Path(flag).read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise SystemExit(
                f"build_capcog_targets: FAIL — {flag} is not a list of rows.")
        incoming: list = []
        skipped: list = []
        for r in rows:
            # Layer 1 strips names and refuses blank ones; layers 2 and 3 took
            # r.get("name") RAW. An unstripped or nameless import went straight
            # into the denominator, where the coverage tool then read it as a
            # corrupt target file and refused to run — a defect in this builder
            # surfacing as a failure two tools downstream. Every layer is held
            # to the same shape, and what is dropped is NAMED rather than
            # quietly absent. Evaluator finding, PR #83 r1.
            if not isinstance(r, dict):
                skipped.append({"why": "row is not an object", "row": repr(r)[:80]})
                continue
            name = (r.get("name") or "").strip()
            if not name:
                skipped.append({"why": "no name", "row": repr(r)[:80]})
                continue
            county = normalize_place(r.get("county")) or county_for_place(r.get("city"))
            if county not in CAPCOG_COUNTIES:
                continue
            incoming.append({
                "name": name, "city": r.get("city"), "county": county,
                "source_layer": layer,
                # A liquor licence and a Places result are both issued to a
                # physical address, so these layers are venues by construction.
                "target_kind": KIND_VENUE,
            })
        if skipped:
            print(f"  {layer}: {len(skipped)} row(s) EXCLUDED and named:")
            for x in skipped[:20]:
                print(f"    {x['why']}: {x['row']}")
            if len(skipped) > 20:
                print(f"    ... and {len(skipped) - 20} more")
        before = len(targets)
        targets = merge(targets, incoming)
        layers[layer] = len(targets) - before

    # Per-county counts are VENUE counts, because that is what the launch
    # metric measures. A county total that quietly included festivals and city
    # calendars would make the per-county gap look smaller than it is.
    per_county: dict = {c: 0 for c in sorted(CAPCOG_COUNTIES)}
    for t in targets:
        if t.get("target_kind") == KIND_VENUE:
            per_county[t["county"]] += 1

    by_kind: dict = {k: 0 for k in TARGET_KINDS}
    for t in targets:
        by_kind[t.get("target_kind", KIND_VENUE)] += 1

    catalog_only = set(layers) == {"catalog"}
    doc = {
        "generated_by": "tools/build_capcog_targets.py",
        # A catalog-only build is what gets COMMITTED, because the sandbox has
        # no egress to fetch TABC. Its per-county zeros then sit in the repo
        # looking like findings about those counties while the docs quote the
        # measured figure — the exact stale-number trap this file exists to
        # prevent. So a catalog-only artifact says so in its first field.
        # NO NUMBER IS QUOTED HERE, DELIBERATELY. The first version of this
        # banner named the then-current measured figure — and went stale within
        # the hour when the address fix moved it. A hardcoded number inside the
        # device that exists to prevent stale numbers is the defect eating its
        # own tail. Point at where the live figure comes from; never restate it.
        "_READ_THIS_FIRST": (
            "CATALOG-ONLY FLOOR — NOT THE MEASURED DENOMINATOR. The counties "
            "showing zero below are counties this project had not catalogued, "
            "NOT counties without venues. The real figure is produced by the "
            "CAPCOG Coverage workflow, which fetches TABC where egress exists; "
            "read it from that workflow's most recent run, never from this "
            "file. Do not quote the numbers here as the market."
        ) if catalog_only else (
            "MEASURED denominator, built from the layers named in "
            "layers_present."),
        "is_complete_universe": False,
        # The number the launch metric divides by. Named separately from
        # target_count so a reader cannot quote the larger figure by accident.
        "venue_target_count": by_kind[KIND_VENUE],
        "by_target_kind": by_kind,
        "target_kind_note": (
            "Only `venue` rows are the denominator for 'X of Y CAPCOG venues'. "
            "`producer` (companies performing in other people's halls), "
            "`festival` (annual events) and `channel` (city/campus calendars) "
            "are kept, listed and reported, but they are not places that can be "
            "covered in the sense the metric means. They were previously "
            "counted as venues, which inflated the denominator; excluding them "
            "RAISES the coverage percentage, so the change is stated here "
            "rather than left to be discovered."),
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

    if not targets:
        raise SystemExit(
            "build_capcog_targets: FAIL — ZERO target venues. The ten CAPCOG "
            "counties are not empty, so this is category/schema drift, not a "
            "finding. Refusing to write a denominator that would render as "
            "0% or 100% coverage depending on which way it is read.")
    if not by_kind[KIND_VENUE]:
        raise SystemExit(
            "build_capcog_targets: FAIL — targets exist but NONE of them is a "
            "venue. The launch metric divides by the venue count, so this "
            "would render as 0% or 100% depending which way it is read.")
    print(f"build_capcog_targets: {len(targets)} target(s) -> {args.out}")
    print(f"  VENUE targets (the denominator): {by_kind[KIND_VENUE]}")
    for kind in TARGET_KINDS[1:]:
        if by_kind[kind]:
            print(f"    not a venue — {kind}: {by_kind[kind]} "
                  f"(kept and listed, excluded from the metric)")
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
