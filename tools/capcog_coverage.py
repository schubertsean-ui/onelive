#!/usr/bin/env python3
"""CAPCOG coverage: what fraction of the market do we actually have?

Founder directive, 2026-07-26, verbatim in substance: "If you haven't already
created the 'total potential number of venues in CAPCOG' list and are comparing
your data ingestion to that, you're not very good at your job because you don't
know what you're testing against or reaching for."

That criticism was correct. Every coverage number this project has reported —
"85 -> 168 events" — was a numerator with no denominator, which cannot answer
the only question that matters: how much of the market is missing.

This tool reports two things, and refuses to blur them:

  1. REGION CORRECTNESS (provable today, no network): of the events we hold,
     how many are inside CAPCOG, how many are outside it, and how many are in
     places we cannot classify. Any non-zero OUTSIDE count is a defect — those
     rows reach a user who cannot attend them.

  2. COVERAGE AGAINST THE DENOMINATOR (needs the target list): of the venues
     that exist in CAPCOG, how many are we ingesting at all?

When no target list exists, this prints NO TARGET LIST and exits non-zero. It
does NOT compute a coverage percentage against the venues we happen to have,
which would be a self-grading denominator: 100% of what we found is what we
found. That number would be worse than no number, because it reads as success.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.region.capcog import (  # noqa: E402
    CAPCOG_COUNTIES,
    county_for_place,
    normalize_place,
    region_report,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_TARGETS = REPO / "sources" / "capcog_venue_targets.json"


def load_rows(path: str | None) -> list:
    """Event/venue rows from a JSON dump. The DB path lives in the caller
    (Actions has the DSN; this sandbox does not), so the tool stays runnable
    and testable without a database."""
    if not path:
        return []
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def load_targets(path: pathlib.Path) -> list | None:
    """The denominator: venues known to exist in CAPCOG. None when absent —
    an explicit missing-denominator state, never an assumed one."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SystemExit(f"capcog_coverage: target list {path} is not valid JSON ({exc})")
    venues = data.get("venues") if isinstance(data, dict) else data
    if not isinstance(venues, list):
        raise SystemExit(
            f"capcog_coverage: target list {path} has no 'venues' array — refusing "
            f"to guess its shape")
    return venues


def venue_key(name: str | None, city: str | None) -> str | None:
    """Match key for a venue. Name plus city, both normalized — a bare name
    collides across towns ('The Grand' exists more than once)."""
    if not name:
        return None
    return f"{str(name).strip().lower()}|{normalize_place(city) or ''}"


def coverage(rows: list, targets: list | None) -> dict:
    """Ingested venues vs the target denominator, per county."""
    have: set = set()
    for row in rows:
        key = venue_key(row.get("venue_name"), row.get("venue_city") or row.get("city"))
        if key:
            have.add(key)
    if targets is None:
        return {"status": "NO_TARGET_LIST", "ingested_venue_count": len(have)}

    per_county: dict = {c: {"target": 0, "covered": 0, "missing": []} for c in
                        sorted(CAPCOG_COUNTIES)}
    matched = 0
    for t in targets:
        city = t.get("city")
        county = t.get("county") or county_for_place(city)
        if county not in per_county:
            # A target row outside CAPCOG is a defect in the TARGET LIST, and it
            # must not quietly inflate or deflate coverage.
            continue
        per_county[county]["target"] += 1
        key = venue_key(t.get("name"), city)
        if key and key in have:
            per_county[county]["covered"] += 1
            matched += 1
        else:
            per_county[county]["missing"].append(t.get("name"))
    total_target = sum(c["target"] for c in per_county.values())
    return {
        "status": "MEASURED",
        "ingested_venue_count": len(have),
        "target_venue_count": total_target,
        "covered_venue_count": matched,
        "coverage_pct": (round(100.0 * matched / total_target, 1)
                         if total_target else None),
        "per_county": per_county,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", help="JSON dump of ingested event/venue rows")
    ap.add_argument("--targets", default=str(DEFAULT_TARGETS),
                    help="CAPCOG venue target list (the denominator)")
    ap.add_argument("--fail-on-outside", action="store_true",
                    help="exit non-zero when any held event is OUTSIDE CAPCOG")
    args = ap.parse_args(argv)

    rows = load_rows(args.rows)
    report = region_report(rows)

    print("== REGION CORRECTNESS (of the events we hold) ==")
    print(f"  inside CAPCOG : {report['inside_count']}")
    print(f"  OUTSIDE CAPCOG: {report['outside_count']}"
          + ("   <-- DEFECT: these reach users who cannot attend them"
             if report["outside_count"] else ""))
    print(f"  unknown place : {report['unknown_count']}"
          + ("   <-- classify these; unknown is not the same as outside"
             if report["unknown_count"] else ""))
    print(f"  no city field : {report['missing_city_count']}")
    if report["outside_by_place"]:
        print("  outside, by place: " + ", ".join(
            f"{p}={n}" for p, n in report["outside_by_place"].items()))
    if report["unknown_by_place"]:
        print("  unknown, by place: " + ", ".join(
            f"{p}={n}" for p, n in report["unknown_by_place"].items()))
    print(f"  counties covered: {', '.join(report['counties_covered']) or 'NONE'}")
    print(f"  counties ABSENT : {', '.join(report['counties_absent']) or 'none'}")

    cov = coverage(rows, load_targets(pathlib.Path(args.targets)))
    print()
    print("== COVERAGE AGAINST THE DENOMINATOR ==")
    if cov["status"] == "NO_TARGET_LIST":
        print(f"  NO TARGET LIST at {args.targets}.")
        print(f"  We hold {cov['ingested_venue_count']} distinct venue(s), but with no")
        print("  denominator that number answers nothing: it cannot say what share of")
        print("  CAPCOG we cover. Build the target list first (tools/build_capcog_targets.py,")
        print("  which needs network egress and so runs in Actions, not this sandbox).")
        return 2
    print(f"  venues ingested : {cov['ingested_venue_count']}")
    print(f"  venues targeted : {cov['target_venue_count']}")
    print(f"  covered         : {cov['covered_venue_count']}  ({cov['coverage_pct']}%)")
    for county, c in cov["per_county"].items():
        pct = round(100.0 * c["covered"] / c["target"], 1) if c["target"] else None
        print(f"    {county:<12} {c['covered']:>4}/{c['target']:<4} "
              f"{'' if pct is None else str(pct) + '%'}")

    if args.fail_on_outside and report["outside_count"]:
        print("\ncapcog_coverage: FAIL — events outside CAPCOG are being held/served.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
