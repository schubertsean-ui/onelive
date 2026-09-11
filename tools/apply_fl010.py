#!/usr/bin/env python3
"""Point desk_ingest.fill_published_holes at fill_public_rows. Delete the old fill."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGEST = ROOT / "tools" / "desk_ingest.py"

WRAPPER = '''def fill_published_holes(event_id: str, patch: dict) -> str:
    """FL-010. Public Place/clock write. See worker.locale_pack.fill_public."""
    from worker.locale_pack.fill_public import fill_public_rows  # noqa: PLC0415
    return fill_public_rows(event_id, patch)


'''


def main() -> int:
    text = INGEST.read_text(encoding="utf-8")
    if "from worker.locale_pack.fill_public import" not in text:
        text = text.replace(
            "from worker.locale_pack.desk_fill import fill_patch, fills  # noqa: E402",
            "from worker.locale_pack.desk_fill import fill_patch, fills  # noqa: E402\n"
            "from worker.locale_pack.fill_public import public_fill_patch  # noqa: E402",
            1,
        )
    start = text.find("def fill_published_holes")
    end = text.find("def ingest(", start + 1 if start >= 0 else 0)
    if start < 0 or end < 0:
        raise SystemExit("fill_published_holes / ingest not found")
    text = text[:start] + WRAPPER + text[end:]
    text = text.replace(
        'fill(event_id, fill_patch(fresh, ["place"]))',
        "fill(event_id, public_fill_patch(fresh))",
    )
    if 'set venue_name' in text[start:start + 800] if start >= 0 else False:
        raise SystemExit("old venue_name fill survived")
    INGEST.write_text(text, encoding="utf-8")
    print("FL-010 wrapper wired into", INGEST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
