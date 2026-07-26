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
    normalize_place,
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
    }


def main() -> int:
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"gen_region_boundary: {len(CAPCOG_PLACES)} place(s) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
