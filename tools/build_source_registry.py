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

# Sources that exist in CODE or in a founder decision. Most of them are ALSO
# catalog rows under a different id, which is the trap: appending them blindly
# produced a registry where Ticketmaster appeared twice (`ticketmaster_discovery`
# and `ticketmaster_api`) and Eventbrite appeared twice under the SAME id. That
# is not a cosmetic duplicate. The scorecard attributes evidence by id, so one
# row would show the real throughput and its twin would show a permanent zero —
# a live feed rendered half-dead, and an inflated source count on top. So these
# entries MERGE onto the catalog row when `merge_into` names one, and are only
# appended when the source genuinely has no catalog entry.
CODE_AND_DECISION_SOURCES = [
    {"id": "ticketmaster_api", "merge_into": "ticketmaster_discovery",
     "name": "Ticketmaster Discovery API",
     "source_class": "ticketing_api", "needs_credential": True,
     "evidence": "worker/importers/ticketmaster.py",
     "remediation": "Live and credentialed. Replace the 75-mile radius scoping "
                    "with county-scoped queries so it stops fetching "
                    "out-of-market rows (R-025)."},
    {"id": "seatgeek_api", "merge_into": "seatgeek", "name": "SeatGeek API",
     "source_class": "ticketing_api",
     "needs_credential": True, "evidence": "worker/importers/seatgeek.py",
     "remediation": "Founder mints SEATGEEK_CLIENT_ID; then ONE dry-run "
                    "verifies the payload shape before the feed is trusted "
                    "(R-029)."},
    {"id": "eventbrite_api", "merge_into": "eventbrite_api",
     "name": "Eventbrite API", "source_class": "ticketing_api",
     "needs_credential": True, "evidence": "worker/importers/eventbrite.py",
     "remediation": "Founder mints EVENTBRITE_TOKEN; same one-dry-run shape "
                    "verification (R-029). Migration 0011 lands with it."},
    # Google Places is catalogued as a `directory` row (venue IDENTITY). The code
    # path uses it for venue ENUMERATION — denominator layer 3 — which provides
    # VENUES, so the merge deliberately overrides the class to match what the
    # source is actually used for. One row, the used class, no phantom twin.
    {"id": "places_api", "merge_into": "google_places",
     "name": "Places API (venue enumeration)",
     "source_class": "places_api", "needs_credential": True,
     "evidence": "docs/GO_LIVE_PLAN.md — denominator layer 3",
     "remediation": "Founder has a key. Wire layer 3 to cover the venue types a "
                    "liquor licence cannot see: theatres, museums, libraries, "
                    "all-ages rooms."},
    {"id": "venue_newsletters", "merge_into": "email_opt_in",
     "name": "Venue newsletters (opt-in email)",
     "source_class": "email_newsletter", "needs_credential": True,
     "evidence": "docs/GO_LIVE_PLAN.md — 55 of 64 curated sources have no feed",
     "remediation": "Founder provides a dedicated address; then subscribe + "
                    "parse. This is the ONLY route to most of the long tail."},
    # Genuinely absent from the catalog — these two are the reason this list
    # exists at all.
    {"id": "tabc_licensed_premises", "merge_into": None,
     "name": "TABC licensed premises (state ABC open data)",
     "source_class": "alcohol_licensing", "needs_credential": False,
     "evidence": "tools/fetch_tabc_capcog.py",
     "remediation": "Built and founder-chosen. Runs in the CAPCOG Coverage "
                    "workflow; needs the workflow on the default branch before "
                    "GitHub will dispatch it."},
    {"id": "city_open_data", "merge_into": None,
     "name": "City/county open-data portal",
     "source_class": "open_data_portal", "needs_credential": False,
     "evidence": "taxonomy — identified, never instantiated for Austin",
     "remediation": "Identify the Austin/Travis portal datasets (special-event "
                    "permits, venue licences) and instantiate."},
]


def build(catalog: list) -> list:
    out: list = []
    by_id: dict = {}
    unmapped: set = set()
    for row in catalog:
        cat = row.get("category")
        cls = CATEGORY_TO_CLASS.get(cat)
        if cls is None:
            unmapped.add(cat)
            continue
        entry = {
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
        }
        if entry["id"] in by_id:
            raise SystemExit(
                f"build_source_registry: FAIL — the catalog itself contains the "
                f"id {entry['id']!r} twice. Evidence is attributed by id, so a "
                f"duplicate splits one source's throughput across two rows.")
        by_id[entry["id"]] = entry
        out.append(entry)
    if unmapped:
        # An unmapped category would DISAPPEAR from the scorecard — a source you
        # cannot see is worse than one you know is broken.
        raise SystemExit(
            f"build_source_registry: FAIL — catalog categories with no taxonomy "
            f"class: {sorted(unmapped)}. Map them in CATEGORY_TO_CLASS or the "
            f"sources vanish from the scorecard.")

    for extra in CODE_AND_DECISION_SOURCES:
        target = extra.get("merge_into")
        if target is not None:
            row = by_id.get(target)
            if row is None:
                # A stale merge target would silently become an append — the
                # exact duplicate this list was rewritten to prevent.
                raise SystemExit(
                    f"build_source_registry: FAIL — {extra['id']!r} declares "
                    f"merge_into={target!r}, which is not a catalog id. Fix the "
                    f"target or set merge_into=None; a wrong target reintroduces "
                    f"the duplicate row it was meant to prevent.")
            # Catalog keeps its id and name (they are what the catalog's own
            # tooling references); the code/decision entry supplies what only it
            # knows — the class actually exercised, the credential requirement,
            # the code path, and the specific fix.
            row.update({
                "source_class": extra["source_class"],
                "needs_credential": extra["needs_credential"],
                "evidence": extra["evidence"],
                "remediation": extra["remediation"],
                "origin": "catalog+code_or_decision",
                "code_id": extra["id"],
            })
            continue
        if extra["id"] in by_id:
            raise SystemExit(
                f"build_source_registry: FAIL — {extra['id']!r} is not marked as "
                f"a merge but collides with a catalog id. Set merge_into to that "
                f"id so the two become one row.")
        row = {k: v for k, v in extra.items() if k != "merge_into"}
        row.update({"catalog_category": None, "origin": "code_or_decision",
                    "credential_present": None})
        by_id[row["id"]] = row
        out.append(row)
    return out


DISCOVERED = REPO / "sources" / "discovered"


def load_discovered() -> list:
    """Agent-discovered sources (sources/discovered/*.json).

    These are LEADS. A web-search result is a far weaker claim than a licence
    record, and the registry must never let the two blur: every row lands with
    origin `web_discovery` and `credential_present` unset, so the scorecard
    reports it as NEVER_TRIED until a real fetch proves the feed exists and
    parses. That is the honest status — "nobody has tried this yet" — and it is
    exactly the distinction the scorecard was built to preserve.

    They are included rather than kept aside because the alternative is worse:
    seven CAPCOG counties had ZERO curated sources, and a registry that omits
    every known lead reports that gap as if nothing could be done about it.
    """
    out: list = []
    if not DISCOVERED.is_dir():
        return out
    # WHERE each id came from, so a duplicate names both files rather than
    # just saying "duplicate". The collision check below only compared
    # discovered ids against CURATED ones, so two leads sharing an id — within
    # one file or across two — merged into the registry silently. That splits
    # one source's evidence across two rows, or overstates it by counting one
    # source twice, which is the duplicate defect this whole builder exists to
    # stop, in the one place I had not looked. Evaluator finding, PR #85 r1.
    seen: dict = {}
    for path in sorted(DISCOVERED.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in doc.get("sources", []):
            rid = row.get("id")
            if rid in seen:
                raise SystemExit(
                    f"build_source_registry: FAIL — discovered source id "
                    f"{rid!r} appears twice: {seen[rid]} and {path.name}. Two "
                    f"leads under one id either split a source's evidence "
                    f"across two rows or count one source twice; both make the "
                    f"registry lie about how many sources we have.")
            seen[rid] = path.name
            cls = row.get("source_class")
            if cls not in SOURCE_CLASSES:
                raise SystemExit(
                    f"build_source_registry: FAIL — discovered source "
                    f"{row.get('id')!r} in {path.name} declares source_class "
                    f"{cls!r}, which is not in the taxonomy. An unmapped class "
                    f"would vanish from the scorecard.")
            out.append({
                "id": row["id"],
                "name": row.get("name"),
                "source_class": cls,
                "catalog_category": None,
                "base_url": row.get("url"),
                "county": row.get("county"),
                "cultural_domain": None,
                "access_method": "scrape",
                "needs_credential": False,
                "credential_present": None,
                "origin": "web_discovery",
                "verified": False,
                "discovered_via": doc.get("discovered_via", "web_search"),
                "discovered_at": doc.get("discovered_at"),
                "evidence": row.get("url"),
                "remediation": row.get("note") or (
                    "Discovered by web search and NOT yet verified. Attempt one "
                    "fetch to confirm the calendar exists and parses before "
                    "trusting anything from it."),
            })
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

    # Discovered leads join the registry, but an id collision with a curated
    # row must not silently overwrite a verified source with an unverified one.
    known = {s["id"] for s in sources}
    discovered = load_discovered()
    clashes = sorted(s["id"] for s in discovered if s["id"] in known)
    if clashes:
        raise SystemExit(
            f"build_source_registry: FAIL — discovered source id(s) collide "
            f"with curated rows: {clashes}. Rename them; a lead must never "
            f"overwrite a source that has actually been verified.")
    sources.extend(discovered)

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
