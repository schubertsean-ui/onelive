#!/usr/bin/env python3
"""Fail CI if desk_publish grows a completeness hold."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "worker" / "locale_pack" / "desk_publish.py"
FORBIDDEN = (
    "no desk stated a date",
    "unplaced",
    "no place",
    "night and no time",
)


def main() -> int:
    text = PUBLISH.read_text(encoding="utf-8")
    bad = [s for s in FORBIDDEN if s in text]
    if bad:
        print("hold_scan: forbidden hold strings still in desk_publish.py:", bad)
        return 1
    if re.search(r"hold_reason\s*=\s*[\"']unplaced[\"']", text):
        print("hold_scan: unplaced hold_reason assignment")
        return 1
    print("hold_scan: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
