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
    # Same fail-loud shape as load_targets. Corrupt rows raised a bare
    # JSONDecodeError here while the target file produced a structured
    # message — the numerator and the denominator must fail the same way, or
    # one of them looks like a crash and the other like a decision.
    # Evaluator nit, PR #83 r1.
    try:
        rows = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        raise SystemExit(
            f"capcog_coverage: FAIL — {path} could not be read as JSON "
            f"({exc}). An unreadable numerator is not an empty one.")
    if not isinstance(rows, list):
        raise SystemExit(
            f"capcog_coverage: FAIL — {path} is not a list of rows.")
    return rows


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

    # Score against PLACES only. The target file also carries producers (a
    # company that performs in halls it does not own), festivals (annual
    # events) and channels (a whole city's calendar). None can be "covered" in
    # the sense "X of Y CAPCOG venues" means, and counting them made the
    # denominator structurally wrong. They stay in the file — the non-venue
    # count is reported beside the metric — but they are not divided by.
    #
    # A row with no `target_kind` is treated as a venue: this file predates the
    # field, and defaulting the other way would silently delete most of the
    # denominator against an older target list.
    non_venue = [v for v in venues
                 if v.get("target_kind") not in (None, "venue")]
    venues = [v for v in venues if v.get("target_kind") in (None, "venue")]
    return venues, {
        "is_complete_universe": bool(meta.get("is_complete_universe", False)),
        "layers_present": meta.get("layers_present") or [],
        "completeness_note": meta.get("completeness_note") or "",
        "non_venue_targets_excluded": len(non_venue),
        "non_venue_by_kind": {
            k: sum(1 for v in non_venue if v.get("target_kind") == k)
            for k in sorted({v.get("target_kind") for v in non_venue})
        },
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


def _county_of_ingested_city(city: str) -> str | None:
    """CAPCOG county for an ingested row's city, or None when unknown."""
    return county_for_place(city)


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

    # City-less target. r1 made matching name-first so 61 city-less targets
    # would stop reading as misses; r3 caught that the same change lets a name
    # match cross COUNTY lines and OVERSTATE coverage — "The Parish" in Travis
    # counted as covered by a same-named room in Llano, or by one in San
    # Antonio. Under-reporting and over-reporting are the same defect pointed in
    # opposite directions, so the county has to agree.
    tcounty = target.get("county")
    known = {c for c in cities if c}
    if not known:
        return True, False          # ingested rows carry no city either
    matching = {c for c in known if _county_of_ingested_city(c) == tcounty}
    if not matching:
        return False, False         # every same-named row is in another county
    return True, len(matching) > 1


def coverage(rows: list, targets: list | None) -> dict:
    """Ingested venues vs the target denominator, per county."""
    idx = index_by_name(rows)
    if targets is None:
        return {"status": "NO_TARGET_LIST", "ingested_venue_count": len(idx)}

    per_county: dict = {c: {"target": 0, "covered": 0, "missing": []} for c in
                        sorted(CAPCOG_COUNTIES)}
    # SUPPLY CAP — one ingested row cannot cover many premises.
    #
    # Correcting TABC to count distinct premises BY ADDRESS made the
    # denominator premise-accurate (two Torchy's = two venues) while this
    # matcher still keyed on name. So a single ingested "Torchy's / Austin"
    # row would satisfy EVERY Torchy's target in the county — a fix to one side
    # of a ratio silently overstating the other. Coverage may not exceed the
    # number of distinct venues we actually hold under that name.
    supply: dict = {}
    for name, cities in idx.items():
        supply[name] = len(cities) or 1
    matched = 0
    ambiguous_names: list = []
    malformed: list = []
    for t in targets:
        city = t.get("city")
        county = t.get("county") or county_for_place(city)
        # A malformed denominator row is CORRUPT INPUT, not a smaller market
        # (evaluator blocker r3). Silently `continue`-ing shrank the denominator
        # and inflated the percentage, and a nameless row was counted as a miss
        # with `None` in the missing list. Both are recorded and surfaced.
        if not (t.get("name") or "").strip():
            malformed.append(f"<nameless row, county={county!r}>")
            continue
        if county not in per_county:
            malformed.append(f"{t.get('name')} (county={county!r} not in CAPCOG)")
            continue
        per_county[county]["target"] += 1
        covered, ambiguous = target_is_covered(t, idx)
        if ambiguous:
            # AN AMBIGUOUS MATCH IS NOT COVERAGE. Naming the ambiguity in the
            # report while still incrementing `covered` meant the percentage
            # already contained the very matches we said we would not resolve
            # silently — the caveat travelled in prose and the number travelled
            # everywhere. Ambiguity is counted as NOT covered, which understates
            # rather than overstates, and every such target is listed so it can
            # be resolved rather than assumed.
            ambiguous_names.append(t.get("name"))
            per_county[county]["missing"].append(t.get("name"))
            continue
        key = venue_name_key(t.get("name"))
        if covered and supply.get(key, 0) > 0:
            supply[key] -= 1
            per_county[county]["covered"] += 1
            matched += 1
        else:
            # Either no match, or the name matched but we have already credited
            # every distinct venue we hold under it. The remaining targets are
            # genuinely uncovered premises, not duplicates of a covered one.
            per_county[county]["missing"].append(t.get("name"))
    total_target = sum(c["target"] for c in per_county.values())
    return {
        "status": "MEASURED",
        "ingested_venue_count": len(idx),
        "ambiguous_matches": ambiguous_names,
        "malformed_target_rows": malformed,
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
    if cov.get("malformed_target_rows"):
        print(f"  MALFORMED target rows EXCLUDED from the denominator "
              f"({len(cov['malformed_target_rows'])}) — the target list is "
              f"corrupt, not the market smaller:")
        for row in cov["malformed_target_rows"][:10]:
            print(f"    - {row}")
    if cov.get("ambiguous_matches"):
        print(f"  ambiguous name-only matches (not silently resolved): "
              f"{', '.join(cov['ambiguous_matches'])}")
    excluded = (tmeta or {}).get("non_venue_targets_excluded") or 0
    if excluded:
        # Declared, because excluding them SHRINKS the denominator and so
        # RAISES this percentage. A change that flatters the number has to be
        # visible next to the number.
        kinds = ", ".join(f"{k} {n}" for k, n in
                          ((tmeta or {}).get("non_venue_by_kind") or {}).items())
        print(f"  NOT counted as venues ({excluded}): {kinds}")
        print(f"  These are producers, annual events and city-wide calendars — "
              f"kept in the target file, not places that can be covered.")
    print(f"  venues ingested : {cov['ingested_venue_count']}")
    print(f"  venues targeted : {cov['target_venue_count']}")
    # A percentage computed from a denominator we KNOW is corrupt must not be
    # printed at all. Reporting the malformed rows and then printing the number
    # anyway was the swallowed-corrupt-data class: the caveat travels in the log
    # and the number travels everywhere else, so the number outlives its warning.
    if cov.get("malformed_target_rows"):
        print(f"  covered         : {cov['covered_venue_count']} of "
              f"{cov['target_venue_count']}")
        print(f"  PERCENTAGE SUPPRESSED — the denominator contains "
              f"{len(cov['malformed_target_rows'])} corrupt row(s). A share of a "
              f"corrupt market is not a measurement.")
    else:
        print(f"  covered         : {cov['covered_venue_count']}  "
              f"({cov['coverage_pct']}%)")
        for county, c in cov["per_county"].items():
            pct = round(100.0 * c["covered"] / c["target"], 1) if c["target"] else None
            print(f"    {county:<12} {c['covered']:>4}/{c['target']:<4} "
                  f"{'' if pct is None else str(pct) + '%'}")

    if cov.get("malformed_target_rows"):
        # Non-zero, so the workflow cannot upload a coverage artifact built on a
        # denominator it already knows is broken.
        print("\ncapcog_coverage: FAIL — the target list is corrupt, not the "
              "market smaller. Fix the denominator and re-run.", file=sys.stderr)
        return 1
    if args.fail_on_outside and report["outside_count"]:
        print("\ncapcog_coverage: FAIL — events outside CAPCOG are being held/served.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
