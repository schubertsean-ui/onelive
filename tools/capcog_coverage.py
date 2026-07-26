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


def load_targets(path: pathlib.Path):
    """The denominator: venues known to exist in CAPCOG. None when absent —
    an explicit missing-denominator state, never an assumed one."""
    if not path.exists():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SystemExit(f"capcog_coverage: target list {path} is not valid JSON ({exc})")
    venues = data.get("venues") if isinstance(data, dict) else data
    if not isinstance(venues, list):
        raise SystemExit(
            f"capcog_coverage: target list {path} has no 'venues' array — refusing "
            f"to guess its shape")
    # Carry the denominator's OWN declaration of its limits (evaluator blocker
    # r2): load_targets used to return the venues array and drop
    # is_complete_universe / layers_present / completeness_note, so the report
    # could print a percentage while discarding the file's statement that it is
    # only a floor. A number that has shed its own caveat is how "coverage"
    # becomes a claim about the market when it is a claim about our catalog.
    meta = data if isinstance(data, dict) else {}
    return venues, {
        "is_complete_universe": bool(meta.get("is_complete_universe", False)),
        "layers_present": meta.get("layers_present") or [],
        "completeness_note": meta.get("completeness_note") or "",
    }


def venue_name_key(name: str | None) -> str | None:
    """Normalized venue NAME. The primary match key."""
    if not name:
        return None
    return str(name).strip().lower() or None


def index_by_name(rows: list) -> dict:
    """{normalized name -> set of normalized cities seen for it}."""
    idx: dict = {}
    for row in rows:
        key = venue_name_key(row.get("venue_name"))
        if key:
            idx.setdefault(key, set()).add(
                normalize_place(row.get("venue_city") or row.get("city")) or "")
    return idx


def target_is_covered(target: dict, idx: dict) -> tuple:
    """Is this target venue present in what we ingested? Returns
    (covered, ambiguous).

    Evaluator blocker (Gemini seat, spec-vs-contract lens): matching used to be
    an exact `name|city` string on BOTH sides. 61 of 69 catalog targets carry no
    city — the catalog rows state a county, not a town — so every one of them
    computed `name|` while the ingested row computed `name|austin`, the lookup
    missed, and coverage reported ~0%. A measurement tool that under-reports to
    zero is worse than none: it would have had me tell the founder we cover
    nothing, in the exact session where a wrong number was the complaint.

    So city is a DISAMBIGUATOR, not part of the key. A target matches on name;
    city only has to agree when BOTH sides actually state one. When a
    city-less target matches a name that we ingested in more than one distinct
    town, that is AMBIGUOUS — counted and reported, never silently resolved in
    either direction.
    """
    key = venue_name_key(target.get("name"))
    if key is None or key not in idx:
        return False, False
    cities = idx[key]
    tcity = normalize_place(target.get("city"))
    if tcity:
        return (tcity in cities or cities == {""}), False
    known = {c for c in cities if c}
    return True, len(known) > 1


def coverage(rows: list, targets: list | None) -> dict:
    """Ingested venues vs the target denominator, per county."""
    idx = index_by_name(rows)
    if targets is None:
        return {"status": "NO_TARGET_LIST", "ingested_venue_count": len(idx)}

    per_county: dict = {c: {"target": 0, "covered": 0, "missing": []} for c in
                        sorted(CAPCOG_COUNTIES)}
    matched = 0
    ambiguous_names: list = []
    for t in targets:
        city = t.get("city")
        county = t.get("county") or county_for_place(city)
        if county not in per_county:
            # A target row outside CAPCOG is a defect in the TARGET LIST, and it
            # must not quietly inflate or deflate coverage.
            continue
        per_county[county]["target"] += 1
        covered, ambiguous = target_is_covered(t, idx)
        if ambiguous:
            ambiguous_names.append(t.get("name"))
        if covered:
            per_county[county]["covered"] += 1
            matched += 1
        else:
            per_county[county]["missing"].append(t.get("name"))
    total_target = sum(c["target"] for c in per_county.values())
    return {
        "status": "MEASURED",
        "ingested_venue_count": len(idx),
        "ambiguous_matches": ambiguous_names,
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

    targets, tmeta = load_targets(pathlib.Path(args.targets))
    cov = coverage(rows, targets)
    print()
    print("== COVERAGE AGAINST THE DENOMINATOR ==")
    if cov["status"] == "NO_TARGET_LIST":
        print(f"  NO TARGET LIST at {args.targets}.")
        print(f"  We hold {cov['ingested_venue_count']} distinct venue(s), but with no")
        print("  denominator that number answers nothing: it cannot say what share of")
        print("  CAPCOG we cover. Build the target list first (tools/build_capcog_targets.py,")
        print("  which needs network egress and so runs in Actions, not this sandbox).")
        return 2
    # The caveat travels WITH the figure, never as a footnote someone can quote
    # around (evaluator blocker r2). A percentage against a floor is not market
    # coverage, and the line that prints it has to say so.
    if not (tmeta or {}).get("is_complete_universe", False):
        layers = ", ".join((tmeta or {}).get("layers_present") or ["unknown"])
        print(f"  *** FLOOR, NOT THE MARKET UNIVERSE — layers present: {layers}")
        print(f"  *** This percentage answers 'are we ingesting what we already")
        print(f"  *** know about?', NOT 'what share of CAPCOG venues exist?'.")
    if cov.get("ambiguous_matches"):
        print(f"  ambiguous name-only matches (not silently resolved): "
              f"{', '.join(cov['ambiguous_matches'])}")
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
