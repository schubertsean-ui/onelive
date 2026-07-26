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
    CAPCOG_COUNTIES, CAPCOG_PLACES, KNOWN_OUTSIDE,
)

OUT = REPO / "web" / "lib" / "capcog-boundary.json"


def build() -> dict:
    return {
        "_generated_by": ("tools/gen_region_boundary.py from "
                          "worker/region/capcog.py — DO NOT EDIT BY HAND"),
        "counties": sorted(CAPCOG_COUNTIES),
        "places": dict(sorted(CAPCOG_PLACES.items())),
        "known_outside": dict(sorted(KNOWN_OUTSIDE.items())),
    }


def main() -> int:
    OUT.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"gen_region_boundary: {len(CAPCOG_PLACES)} place(s) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
