#!/usr/bin/env python3
"""Fetch TABC licensed premises for the ten CAPCOG counties — denominator layer 2.

Founder-directed 2026-07-26: "Use TABC."

The Texas Alcoholic Beverage Commission publishes every licensed premise in the
state as open data on data.texas.gov (Socrata). Each record carries a business
name, a city and a COUNTY, which is exactly the shape the denominator needs and
why this is the right layer-2 source: authoritative, free, no credential, and
county-tagged so it maps onto the CAPCOG boundary without guessing.

WHAT THIS DOES NOT COVER, said up front so the number is never oversold: a
liquor licence is a proxy for "music venue", not a definition of one. It will
miss theatres, museums, libraries, galleries and all-ages rooms that serve no
alcohol, and it will include bars and restaurants that never host a show. It
raises the floor toward the real universe; it is not the universe. Layer 3
(Places) is what covers the non-alcohol venues.

LIVE-SHAPE DISCIPLINE (docs/RECORD.md R-029's rule, applied before it can bite):
this module makes NO silent assumption about the payload. The dataset's field
names are declared below, every one is checked against the FIRST record
returned, and a mismatch FAILS LOUD with the actual keys printed — rather than
quietly yielding zero rows, which would read as "CAPCOG has no venues" and be
precisely the failure-reads-as-empty class this project has paid for repeatedly.

Run it where egress exists (GitHub Actions); the dev sandbox has none.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from worker.region.capcog import (CAPCOG_COUNTIES, county_for_place,
                                  normalize_place)  # noqa: E402

# TABC "Licenses / Permits" on the Texas open-data portal. Socrata serves JSON
# at /resource/<id>.json with SoQL query parameters.
DATASET = "naix-2893"
BASE_URL = f"https://data.texas.gov/resource/{DATASET}.json"

# The fields this tool consumes — READ OFF THE LIVE DATASET (--describe), not
# written from memory. The first version guessed `trade_name`/`city`/`county`
# and the query was rejected outright; the sandbox has no egress, so the schema
# is only observable from CI, and guessing cost a round trip that asking did
# not.
FIELD_NAME = "location_name"
FIELD_CITY = "location_city"
FIELD_COUNTY = "location_county"
FIELD_END = "obligation_end_date_yyyymmdd"
REQUIRED_FIELDS = (FIELD_NAME, FIELD_CITY, FIELD_COUNTY, FIELD_END)

# `location_county` is a NUMERIC CODE, not a name — Texas numbers its 254
# counties alphabetically (Harris = 101, confirmed against a live record). These
# are the ten CAPCOG counties in that scheme.
#
# A wrong code here would silently return the WRONG COUNTY'S bars and report
# them as CAPCOG venues — the same class as the 75-mile radius that started all
# of this, in a different disguise. So the mapping is not trusted: every fetched
# row's CITY is checked against the CAPCOG place table, and a code whose rows
# are dominated by unrecognised cities fails the run (see verify_counties).
COUNTY_CODES = {
    11: "bastrop", 16: "blanco", 27: "burnet", 28: "caldwell", 75: "fayette",
    105: "hays", 144: "lee", 150: "llano", 227: "travis", 246: "williamson",
}

# How much of a county's rows may carry a city the boundary does not recognise
# before the county code itself is suspect. Small towns legitimately miss the
# table, so this is not zero — but a code pointing at the wrong county produces
# almost entirely unrecognised cities, which is what this catches.
MAX_UNRECOGNISED_SHARE = 0.60

# How much of a county's rows may name a town the boundary places in a
# DIFFERENT county. Not zero: Austin straddles Travis, Williamson and Hays, so
# legitimate cross-county rows exist. A wrong code, by contrast, returns another
# county wholesale and nearly every row disagrees.
MAX_WRONG_COUNTY_SHARE = 0.50

PAGE = 1000
MAX_PAGES = 60          # 60k records is far beyond CAPCOG's share; a bound, not a filter


def _get(url: str, timeout: int = 60) -> list:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def describe() -> int:
    """Print the dataset's ACTUAL columns and one sample record.

    Added after this tool failed with `no-such-column: trade_name`. The column
    names had been written from memory, and no amount of local testing could
    catch that — the sandbox has no egress to data.texas.gov, so the schema is
    only observable from CI. Guessing again and pushing again is the expensive
    loop; asking the dataset what it contains costs one 15-second run.
    """
    sample = _get(f"{BASE_URL}?$limit=1")
    if not sample:
        raise SystemExit(
            f"fetch_tabc_capcog --describe: {DATASET} returned no rows at all. "
            f"That is an empty or wrong dataset id, not a schema answer.")
    row = sample[0]
    print(f"dataset {DATASET} — {len(row)} column(s):")
    for key in sorted(row):
        value = str(row[key])
        print(f"    {key:<32} = {value[:60]}")
    return 0


def verify_shape(sample: dict, fields: tuple = REQUIRED_FIELDS) -> None:
    """Fail LOUD when the live payload is not the shape this tool consumes.

    `fields` is narrowed for grouped queries: the date column is a filter, not
    a projection, so it is legitimately absent from a GROUP BY result.
    """
    missing = [f for f in fields if f not in sample]
    if missing:
        raise SystemExit(
            f"fetch_tabc_capcog: FAIL — the live TABC payload is missing the "
            f"field(s) this tool reads: {missing}.\n"
            f"  Actual keys on the first record: {sorted(sample)}\n"
            f"  The dataset's schema changed, or {DATASET} is not the licences "
            f"dataset. Refusing to continue: yielding zero rows here would read "
            f"as 'CAPCOG has no venues', which is a lie, not an empty result.")


def verify_counties(rows: list) -> dict:
    """Cross-check the county-CODE mapping against the cities that came back.

    The codes are a fact about TABC's encoding, and a wrong one would return
    another county's bars and label them CAPCOG — the same defect class as the
    75-mile radius, wearing a different hat. Rather than trust the table, check
    it against evidence already on the rows: the CAPCOG place list says which
    county a town is in, so a code pointing somewhere else shows up as a flood
    of cities the boundary does not know.
    """
    per_county: dict = {}
    for r in rows:
        stat = per_county.setdefault(
            r["county"], {"rows": 0, "unrecognised": 0, "wrong_county": 0,
                          "examples": []})
        stat["rows"] += 1
        actual = county_for_place(r.get("city"))
        if actual is None:
            stat["unrecognised"] += 1
            if len(stat["examples"]) < 5 and r.get("city"):
                stat["examples"].append(r["city"])
        elif actual != r["county"]:
            stat["wrong_county"] += 1
            if len(stat["examples"]) < 5:
                stat["examples"].append(f"{r['city']} -> {actual}")

    bad: list = []
    for county, stat in sorted(per_county.items()):
        if not stat["rows"]:
            continue
        # Judged as a SHARE, never on a single row. Real cities straddle county
        # lines — Austin sits mostly in Travis but reaches into Williamson and
        # Hays — so one row whose city maps elsewhere is geography, not a bug.
        # A wrong CODE is different in kind: it returns another county wholesale,
        # so nearly every row disagrees.
        wrong = stat["wrong_county"] / stat["rows"]
        if wrong > MAX_WRONG_COUNTY_SHARE:
            bad.append(f"{county}: {wrong:.0%} of rows carry a city that belongs "
                       f"to a different county ({stat['examples']})")
            continue
        share = stat["unrecognised"] / stat["rows"]
        if share > MAX_UNRECOGNISED_SHARE:
            bad.append(f"{county}: {share:.0%} of rows carry a city the CAPCOG "
                       f"boundary does not recognise ({stat['examples']})")
    if bad:
        raise SystemExit(
            "fetch_tabc_capcog: FAIL — the county-code mapping does not agree "
            "with the cities returned:\n  " + "\n  ".join(bad) +
            "\n  A wrong county code returns another county's premises and "
            "labels them CAPCOG. Refusing to build a denominator from it.")
    return per_county


def fetch(counties: set, limit_pages: int = MAX_PAGES,
          active_since: str | None = None) -> tuple:
    """Every licensed premise whose county is in `counties`. Returns
    (rows, pages_read, records_seen).

    `active_since` keeps only premises with activity on or after that date.
    This dataset is MONTHLY RECEIPTS, so every establishment appears once per
    reporting month and long-closed bars are still in it. Without the filter
    the denominator would include venues that shut years ago — which understates
    coverage by padding the divisor with places nobody can go to.
    """
    # Socrata filters server-side, so we ask only for the counties we want
    # rather than paging the whole state and discarding 95% of it. Codes are
    # numeric, so they are NOT quoted — quoting them yields zero rows, which
    # would read as "CAPCOG has no bars".
    codes = ",".join(str(c) for c in sorted(
        code for code, name in COUNTY_CODES.items() if name in counties))
    clause = f"{FIELD_COUNTY} in({codes})"
    if active_since:
        clause += f" AND {FIELD_END} >= '{active_since}'"
    where = urllib.parse.quote(clause)
    # GROUP server-side. This is monthly receipts: ten counties over an 18-month
    # window is tens of thousands of rows describing a few thousand premises, and
    # paging all of them took minutes to compute something Socrata can collapse
    # in one pass. Deduping locally as well is not redundant — the group is by
    # RAW name/city, and normalisation (case, punctuation) can still merge two
    # groups into one premise.
    grouped = f"{FIELD_NAME},{FIELD_CITY},{FIELD_COUNTY}"
    group = urllib.parse.quote(grouped)
    select = urllib.parse.quote(grouped)
    out: list = []
    seen = 0
    verified = False
    page = 0
    while page < limit_pages:
        url = (f"{BASE_URL}?$select={select}&$group={group}"
               f"&$where={where}&$limit={PAGE}&$offset={page * PAGE}")
        try:
            batch = _get(url)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise SystemExit(
                f"fetch_tabc_capcog: FAIL — HTTP {exc.code} from data.texas.gov: "
                f"{body}\n  A failed fetch is NOT an empty county.")
        except urllib.error.URLError as exc:
            # Connection drop / DNS / TLS. It already failed loud as a traceback
            # (evaluator nit), but a bare stack trace makes an operator guess
            # whether the county is empty or the network was. Say which.
            raise SystemExit(
                f"fetch_tabc_capcog: FAIL — could not reach data.texas.gov "
                f"({exc.reason}).\n  A network failure is NOT an empty county; "
                f"re-run when connectivity is restored.")
        if not batch:
            break
        if not verified:
            verify_shape(batch[0], (FIELD_NAME, FIELD_CITY, FIELD_COUNTY))
            verified = True
        seen += len(batch)
        for r in batch:
            try:
                code = int(r.get(FIELD_COUNTY))
            except (TypeError, ValueError):
                continue
            county = COUNTY_CODES.get(code)
            if county not in counties:
                continue          # server-side filter double-checked locally
            name = (r.get(FIELD_NAME) or "").strip()
            if not name:
                continue
            out.append({"name": name,
                        "city": normalize_place(r.get(FIELD_CITY)),
                        "county": county,
                        "source_layer": "tabc"})
        page += 1
        if len(batch) < PAGE:
            break
    return out, page, seen


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(REPO / "sources" / "tabc_capcog_raw.json"))
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES)
    ap.add_argument("--describe", action="store_true",
                    help="print the dataset's actual columns and exit — use "
                         "this instead of guessing column names")
    ap.add_argument("--active-since", default=None,
                    help="ISO date; keep only premises reporting on or after "
                         "it. Defaults to 18 months back.")
    args = ap.parse_args(argv)

    if args.describe:
        return describe()

    # This is MONTHLY receipts data, so a still-trading bar appears dozens of
    # times and a bar that closed in 2015 is still in the file. Without a
    # recency window the denominator would count long-dead venues, which
    # understates coverage by padding the divisor with places nobody can go to.
    active_since = args.active_since or (
        datetime.date.today() - datetime.timedelta(days=548)).isoformat()

    raw, pages, seen = fetch(set(CAPCOG_COUNTIES), args.max_pages, active_since)
    if not raw:
        raise SystemExit(
            "fetch_tabc_capcog: FAIL — zero CAPCOG premises returned. Ten "
            "counties containing Austin do not have zero licensed premises, so "
            "this is a query or schema problem, not a finding.")

    # The county codes are checked against the cities that came back BEFORE
    # anything is written — a wrong code is another county's bars wearing a
    # CAPCOG label.
    verify_counties(raw)

    # One row per PREMISE, not per reporting month.
    rows: list = []
    dedupe: set = set()
    for r in raw:
        key = ((r["name"] or "").strip().lower(), r["city"] or "")
        if key in dedupe:
            continue
        dedupe.add(key)
        rows.append(r)

    by_county: dict = {}
    for r in rows:
        by_county[r["county"]] = by_county.get(r["county"], 0) + 1
    print(f"  active-since window: {active_since} "
          f"(monthly rows {len(raw)} -> {len(rows)} distinct premises)")

    pathlib.Path(args.out).write_text(json.dumps(rows, indent=2) + "\n",
                                      encoding="utf-8")
    print(f"fetch_tabc_capcog: {len(rows)} CAPCOG premise(s) from {seen} record(s) "
          f"over {pages} page(s) -> {args.out}")
    for county in sorted(CAPCOG_COUNTIES):
        print(f"    {county:<12} {by_county.get(county, 0)}")
    if pages >= args.max_pages:
        # Non-zero, not a note (evaluator blocker r2): a warning that returns
        # success lets the workflow build and publish a percentage from a
        # KNOWN-truncated denominator. A denominator we know is short is not a
        # denominator.
        print(f"fetch_tabc_capcog: FAIL — hit the {args.max_pages}-page bound, "
              f"so the result is TRUNCATED and the denominator would be short. "
              f"Raise --max-pages and re-run.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
