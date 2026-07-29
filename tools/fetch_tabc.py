#!/usr/bin/env python3
"""Fetch TABC licensed PRODUCERS (breweries / wineries / distilleries) for our
counties and write sources/tabc_producers.json — the authoritative kind index
that tools/gen_tasting_venues.py prefers over its keyword guess.

Stdlib only (urllib), NO AI. Reads the TABC public dataset on data.texas.gov
(Socrata). Runs where egress reaches data.texas.gov (GitHub Actions / a laptop) —
the dev sandbox's network policy blocks it, which is exactly why the CLASSIFY
logic (tools/tabc_classify.py) is fixture-tested separately and this fetch is a
thin, configurable shell.

The dataset id and field names are DECLARED as constants/env so the first live
run can correct them without touching logic:
  TABC_DATASET   Socrata resource id (default below)
  TABC_DOMAIN    data host (default data.texas.gov)
Output rows: {"trade_name", "county", "kind"} — already mapped to our kinds, so
the generator just reads them.

Usage: python3 tools/fetch_tabc.py            # writes sources/tabc_producers.json
       python3 tools/fetch_tabc.py --dry-run  # print counts, write nothing
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.parse
import urllib.request

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.tabc_classify import PERMIT_KIND, permit_kind  # noqa: E402

OUT = _ROOT / "sources" / "tabc_producers.json"

# The counties OneLive covers (CAPCOG 10 + the Hill Country pair). TABC stores
# county names uppercased; we compare case-insensitively.
COUNTIES = {
    "TRAVIS", "WILLIAMSON", "HAYS", "BASTROP", "CALDWELL", "BLANCO", "BURNET",
    "FAYETTE", "LEE", "LLANO", "GILLESPIE",
}

# Socrata resource — DECLARED so a live run can correct it in one place. The TABC
# "active permits/licenses" dataset on the state open-data portal.
TABC_DOMAIN = os.environ.get("TABC_DOMAIN", "data.texas.gov")
TABC_DATASET = os.environ.get("TABC_DATASET", "kdux-xnbh")
# Field names in the dataset (also overridable), tried in order by build_index's
# accepted spellings — kept explicit for the correcting run.
_PERMIT_FIELDS = ("permit_type", "license_type", "type", "tabc_permit_type")
_NAME_FIELDS = ("trade_name", "location_name", "name", "business_name")
_COUNTY_FIELDS = ("county", "location_county")


def _get(url: str, timeout: int = 60) -> list:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _field(row: dict, names) -> "str | None":
    for n in names:
        v = row.get(n)
        if v:
            return str(v)
    return None


def fetch_rows(max_rows: int = 50000) -> list:
    """Page the Socrata dataset and return raw rows (no filtering) — filtering is
    done locally so a field-name mismatch is a visible zero, not a silent SoQL
    error."""
    rows: list = []
    page = 1000
    for offset in range(0, max_rows, page):
        q = urllib.parse.urlencode({"$limit": page, "$offset": offset})
        url = f"https://{TABC_DOMAIN}/resource/{TABC_DATASET}.json?{q}"
        batch = _get(url)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page:
            break
    return rows


def to_producers(rows: list) -> list:
    """Keep only producer permits in our counties; map to {trade_name, county,
    kind}. Deterministic, no network — the part that matters for correctness."""
    out = []
    seen = set()
    for r in rows:
        kind = permit_kind(_field(r, _PERMIT_FIELDS))
        if not kind:
            continue
        county = (_field(r, _COUNTY_FIELDS) or "").strip().upper()
        # Fail-closed (adversarial-review #104 r3): a row whose county is missing,
        # blank, or outside our region is REJECTED — an out-of-region or
        # unqualifiable permit must never enter the authoritative index. If the
        # live county field name drifts, EVERY row drops (a visible zero the run
        # warns on), not a statewide flood admitted silently.
        if county not in COUNTIES:
            continue
        name = _field(r, _NAME_FIELDS)
        if not name:
            continue
        key = (name.strip().lower(), county)
        if key in seen:
            continue
        seen.add(key)
        out.append({"trade_name": name.strip(), "county": county.title(), "kind": kind})
    out.sort(key=lambda p: (p["county"], p["trade_name"].lower()))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fetch TABC producer permits.")
    ap.add_argument("--dry-run", action="store_true", help="print counts, write nothing")
    ap.add_argument("--max-rows", type=int, default=50000)
    args = ap.parse_args(argv)

    print(f"fetch_tabc: dataset {TABC_DOMAIN}/{TABC_DATASET}, kinds={sorted(set(PERMIT_KIND.values()))}")
    rows = fetch_rows(args.max_rows)
    producers = to_producers(rows)
    from collections import Counter
    by_kind = Counter(p["kind"] for p in producers)
    print(f"fetch_tabc: {len(rows)} rows -> {len(producers)} producers in-region {dict(by_kind)}")
    if not producers:
        print("fetch_tabc: WARNING — zero producers. Check TABC_DATASET / field "
              "names against the live schema (see constants).", file=sys.stderr)
    if args.dry_run:
        return 0
    OUT.write_text(json.dumps(producers, indent=2) + "\n", encoding="utf-8")
    print(f"fetch_tabc: wrote {OUT.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
