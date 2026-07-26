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
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from worker.region.capcog import CAPCOG_COUNTIES, normalize_place  # noqa: E402

# TABC "Licenses / Permits" on the Texas open-data portal. Socrata serves JSON
# at /resource/<id>.json with SoQL query parameters.
DATASET = "naix-2893"
BASE_URL = f"https://data.texas.gov/resource/{DATASET}.json"

# The fields this tool consumes. Declared, then VERIFIED against the live
# payload — never assumed. Socrata lowercases and underscores column names.
FIELD_NAME = "trade_name"
FIELD_CITY = "city"
FIELD_COUNTY = "county"
REQUIRED_FIELDS = (FIELD_NAME, FIELD_CITY, FIELD_COUNTY)

PAGE = 1000
MAX_PAGES = 60          # 60k records is far beyond CAPCOG's share; a bound, not a filter


def _get(url: str, timeout: int = 60) -> list:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verify_shape(sample: dict) -> None:
    """Fail LOUD when the live payload is not the shape this tool consumes."""
    missing = [f for f in REQUIRED_FIELDS if f not in sample]
    if missing:
        raise SystemExit(
            f"fetch_tabc_capcog: FAIL — the live TABC payload is missing the "
            f"field(s) this tool reads: {missing}.\n"
            f"  Actual keys on the first record: {sorted(sample)}\n"
            f"  The dataset's schema changed, or {DATASET} is not the licences "
            f"dataset. Refusing to continue: yielding zero rows here would read "
            f"as 'CAPCOG has no venues', which is a lie, not an empty result.")


def fetch(counties: set, limit_pages: int = MAX_PAGES) -> tuple:
    """Every licensed premise whose county is in `counties`. Returns
    (rows, pages_read, records_seen)."""
    # Socrata filters server-side, so we ask only for the counties we want
    # rather than paging the whole state and discarding 95% of it.
    quoted = ",".join(f"'{c.upper()}'" for c in sorted(counties))
    where = urllib.parse.quote(f"upper({FIELD_COUNTY}) in({quoted})")
    out: list = []
    seen = 0
    verified = False
    page = 0
    while page < limit_pages:
        url = (f"{BASE_URL}?$select={','.join(REQUIRED_FIELDS)}"
               f"&$where={where}&$limit={PAGE}&$offset={page * PAGE}")
        try:
            batch = _get(url)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:500]
            raise SystemExit(
                f"fetch_tabc_capcog: FAIL — HTTP {exc.code} from data.texas.gov: "
                f"{body}\n  A failed fetch is NOT an empty county.")
        if not batch:
            break
        if not verified:
            verify_shape(batch[0])
            verified = True
        seen += len(batch)
        for r in batch:
            county = normalize_place(r.get(FIELD_COUNTY))
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
    args = ap.parse_args(argv)

    rows, pages, seen = fetch(set(CAPCOG_COUNTIES), args.max_pages)
    if not rows:
        raise SystemExit(
            "fetch_tabc_capcog: FAIL — zero CAPCOG premises returned. Ten "
            "counties containing Austin do not have zero licensed premises, so "
            "this is a query or schema problem, not a finding.")

    by_county: dict = {}
    for r in rows:
        by_county[r["county"]] = by_county.get(r["county"], 0) + 1

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
