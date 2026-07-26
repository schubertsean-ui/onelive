#!/usr/bin/env python3
"""Build the registry of EVERY ingestion source identified across the build.

Founder directive, 2026-07-26: "every potential data source for ingestion that
has been identified throughout the entire build process. It should be
extensive."

Two populations, joined here, because neither alone is the answer:

  1. The 116 curated rows in the master source catalog — the locale instances.
  2. The sources that exist in CODE or in a founder decision but were never
     catalog rows: the ticketing APIs, the venue-enumeration sources (TABC,
     Places), and the newsletter path. These are the ones a catalog-only list
     silently omits, which is exactly how "extensive" quietly becomes "the ones
     we already wrote down".

Every row is bound to a locale-independent CLASS from worker/sources/taxonomy.py,
so the same registry shape works for any metro: swap the instances, keep the
classes. A catalog category with no class mapping FAILS the build rather than
being dropped — an unmapped source would vanish from the scorecard, and a source
you cannot see is worse than one you know is broken.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from worker.sources.taxonomy import SOURCE_CLASSES  # noqa: E402

CATALOG = REPO / "sources" / "master_sources_catalog_120.json"
OUT = REPO / "sources" / "source_registry.json"

# Catalog category -> taxonomy class. Hand-written because it is a fact about
# our catalog's vocabulary, not derivable — and therefore cross-checked below
# against every category the live catalog actually uses.
CATEGORY_TO_CLASS = {
    "ticketing": "ticketing_api",
    "venue_calendar": "venue_calendar",
    "university_calendar": "university_calendar",
    "library_calendar": "library_calendar",
    "city_calendar": "city_civic_calendar",
    "festival_feed": "festival_feed",
    "local_media": "local_media",
    "social": "social",
    "link_hub": "link_hub",
    "community": "community_board",
    "directory": "directory",
    "artist_aggregator": "artist_aggregator",
    "artist_directory": "artist_identity",
    "music_platform": "music_platform",
    "search_benchmark": "search_benchmark",
    "claimed_upload": "claimed_upload",
    "email_opt_in": "email_newsletter",
    "calendar_feed": "venue_calendar",
}

# Sources that live in code or in a founder decision but were never catalog
# rows. Without these the registry is not "every source identified" — it is
# every source someone remembered to catalogue.
NON_CATALOG_SOURCES = [
    {"id": "ticketmaster_api", "name": "Ticketmaster Discovery API",
     "source_class": "ticketing_api", "needs_credential": True,
     "evidence": "worker/importers/ticketmaster.py",
     "remediation": "Live and credentialed. Replace the 75-mile radius scoping "
                    "with county-scoped queries so it stops fetching "
                    "out-of-market rows (R-025)."},
    {"id": "seatgeek_api", "name": "SeatGeek API", "source_class": "ticketing_api",
     "needs_credential": True, "evidence": "worker/importers/seatgeek.py",
     "remediation": "Founder mints SEATGEEK_CLIENT_ID; then ONE dry-run "
                    "verifies the payload shape before the feed is trusted "
                    "(R-029)."},
    {"id": "eventbrite_api", "name": "Eventbrite API", "source_class": "ticketing_api",
     "needs_credential": True, "evidence": "worker/importers/eventbrite.py",
     "remediation": "Founder mints EVENTBRITE_TOKEN; same one-dry-run shape "
                    "verification (R-029). Migration 0011 lands with it."},
    {"id": "tabc_licensed_premises", "name": "TABC licensed premises (state ABC open data)",
     "source_class": "alcohol_licensing", "needs_credential": False,
     "evidence": "tools/fetch_tabc_capcog.py",
     "remediation": "Built and founder-chosen. Runs in the CAPCOG Coverage "
                    "workflow; needs the workflow on the default branch before "
                    "GitHub will dispatch it."},
    {"id": "places_api", "name": "Places API (venue enumeration)",
     "source_class": "places_api", "needs_credential": True,
     "evidence": "docs/GO_LIVE_PLAN.md — denominator layer 3",
     "remediation": "Founder has a key. Wire layer 3 to cover the venue types a "
                    "liquor licence cannot see: theatres, museums, libraries, "
                    "all-ages rooms."},
    {"id": "venue_newsletters", "name": "Venue newsletters (opt-in email)",
     "source_class": "email_newsletter", "needs_credential": True,
     "evidence": "docs/GO_LIVE_PLAN.md — 55 of 64 curated sources have no feed",
     "remediation": "Founder provides a dedicated address; then subscribe + "
                    "parse. This is the ONLY route to most of the long tail."},
    {"id": "city_open_data", "name": "City/county open-data portal",
     "source_class": "open_data_portal", "needs_credential": False,
     "evidence": "taxonomy — identified, never instantiated for Austin",
     "remediation": "Identify the Austin/Travis portal datasets (special-event "
                    "permits, venue licences) and instantiate."},
]


def build(catalog: list) -> list:
    out: list = []
    unmapped: set = set()
    for row in catalog:
        cat = row.get("category")
        cls = CATEGORY_TO_CLASS.get(cat)
        if cls is None:
            unmapped.add(cat)
            continue
        out.append({
            "id": row.get("id"),
            "name": row.get("name"),
            "source_class": cls,
            "catalog_category": cat,
            "base_url": row.get("base_url"),
            "county": row.get("county"),
            "cultural_domain": row.get("cultural_domain"),
            "access_method": row.get("access_method"),
            "needs_credential": str(row.get("access_method") or "").startswith(
                ("api_key", "oauth", "api_key_oauth")),
            "credential_present": None,
            "origin": "catalog",
        })
    if unmapped:
        # An unmapped category would DISAPPEAR from the scorecard — a source you
        # cannot see is worse than one you know is broken.
        raise SystemExit(
            f"build_source_registry: FAIL — catalog categories with no taxonomy "
            f"class: {sorted(unmapped)}. Map them in CATEGORY_TO_CLASS or the "
            f"sources vanish from the scorecard.")
    for extra in NON_CATALOG_SOURCES:
        out.append({**extra, "catalog_category": None, "origin": "code_or_decision",
                    "credential_present": None})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", default=str(CATALOG))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)

    catalog = json.loads(pathlib.Path(args.catalog).read_text(encoding="utf-8"))
    if isinstance(catalog, dict):
        catalog = catalog.get("sources") or catalog.get("catalog")
        if catalog is None:
            raise SystemExit("build_source_registry: FAIL — catalog has neither "
                             "'sources' nor 'catalog'; corrupt, not empty.")
    sources = build(catalog)

    by_class: dict = {}
    by_provides: dict = {}
    for s in sources:
        by_class[s["source_class"]] = by_class.get(s["source_class"], 0) + 1
        p = SOURCE_CLASSES[s["source_class"]]["provides"]
        by_provides[p] = by_provides.get(p, 0) + 1

    doc = {
        "generated_by": "tools/build_source_registry.py",
        "source_count": len(sources),
        "class_count": len(by_class),
        "by_class": dict(sorted(by_class.items())),
        "by_provides": dict(sorted(by_provides.items())),
        "taxonomy_classes_total": len(SOURCE_CLASSES),
        "classes_with_no_instance": sorted(set(SOURCE_CLASSES) - set(by_class)),
        "sources": sources,
    }
    pathlib.Path(args.out).write_text(json.dumps(doc, indent=2) + "\n",
                                      encoding="utf-8")
    print(f"build_source_registry: {len(sources)} source(s), "
          f"{len(by_class)} class(es) -> {args.out}")
    for provides, n in sorted(by_provides.items()):
        print(f"    provides {provides:<9} {n}")
    if doc["classes_with_no_instance"]:
        print(f"  classes with NO instance yet (the expansion worklist): "
              f"{', '.join(doc['classes_with_no_instance'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
