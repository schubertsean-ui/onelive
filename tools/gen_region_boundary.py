#!/usr/bin/env python3
"""Generate web/lib/capcog-boundary.json from the Python boundary.

The market boundary must exist ONCE. The server filters by it, the web read path
filters by it, and a second hand-maintained copy in TypeScript would drift —
which is the incomplete-enumeration class this project keeps paying for. So
worker/region/capcog.py is the single source of truth and this emits the JSON
the web layer imports. A test asserts the committed file still matches, so
drift fails the suite instead of silently serving two different markets.
"""
from __future__ import annotations

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from worker.region.capcog import (  # noqa: E402
    CAPCOG_COUNTIES, CAPCOG_PLACES, KNOWN_OUTSIDE, TRAILING_QUALIFIERS,
    county_in_place, in_capcog_county, normalize_county, normalize_place,
)

OUT = REPO / "web" / "lib" / "capcog-boundary.json"

# Inputs both normalizers must agree on, emitted WITH their Python answers so
# the TypeScript test checks against the source of truth rather than against a
# hand-copied expectation. The reviewer's finding was that the two normalizers
# drifted while the two DATA tables were kept in sync — the tables were
# generated and the logic was not. These vectors close that half.
NORMALIZATION_VECTORS = [
    "Austin", "Austin, TX", "austin, texas", "Austin, TX 78701",
    "Austin, TX 78701-1234", "Austin, TX, USA", "Austin, Texas, United States",
    "San Antonio", "San Antonio, TX", "San Antonio, TX, USA",
    "SAN ANTONIO, TX 78205, USA", "San Antonio, Texas, United States",
    "New Braunfels, TX, USA", "Round Rock, TX", "Columbus", "  ", "",
    # r12: county qualifiers, which defeated the boundary until 2026-07-26.
    "San Antonio, Bexar County, TX", "san antonio, bexar county",
    "SAN ANTONIO, BEXAR COUNTY, TEXAS, USA", "Austin, Travis County, TX",
    # r12: prototype-property names, which `key in obj` reported as real places.
    "constructor", "toString", "valueOf", "hasOwnProperty", "__proto__",
]

# County vectors: the two normalizers must agree on these too, and the TS side
# must not hand-maintain a second outside-county list.
COUNTY_VECTORS = ["Bexar County, TX", "bexar", "TRAVIS COUNTY", "Travis",
                  "Nowhere County", "", "   "]

# r13: county evidence carried INSIDE a city string, with everything a feed
# might append after it. The anchor only matches once the trailing qualifiers
# are gone, and both normalizers must agree on that.
EMBEDDED_COUNTY_VECTORS = [
    "Unlisted Spot, Bexar County, TX", "Unlisted Spot, Bexar County, TX, USA",
    "Unlisted Spot, Bexar County, TX 78205", "unlisted spot, bexar county",
    "Nowhere Bar, Travis County, TX", "Austin, TX", "San Antonio", "",
]


def build() -> dict:
    return {
        "_generated_by": ("tools/gen_region_boundary.py from "
                          "worker/region/capcog.py — DO NOT EDIT BY HAND"),
        "counties": sorted(CAPCOG_COUNTIES),
        "places": dict(sorted(CAPCOG_PLACES.items())),
        "known_outside": dict(sorted(KNOWN_OUTSIDE.items())),
        # Order matters: two-letter forms must be tried after their longer
        # variants, so the list is emitted as a sequence, not a set.
        "trailing_qualifiers": list(TRAILING_QUALIFIERS),
        "normalization_vectors": [
            {"input": v, "expected": normalize_place(v)}
            for v in NORMALIZATION_VECTORS
        ],
        "embedded_county_vectors": [
            {"input": v, "expected": county_in_place(v)}
            for v in EMBEDDED_COUNTY_VECTORS
        ],
        "county_vectors": [
            {"input": v, "expected": normalize_county(v),
             "verdict": in_capcog_county(v)}
            for v in COUNTY_VECTORS
        ],
    }


def main() -> int:
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"gen_region_boundary: {len(CAPCOG_PLACES)} place(s) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
