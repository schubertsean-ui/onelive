"""Preempt Ticket B: deleted holds must stay deleted."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BANNED = (
    "del as_of",
    "date-TBA only shows under",
    "held until a desk states",
)

SCAN = [
    ROOT / "worker" / "locale_pack" / "desk_read.py",
    ROOT / "worker" / "locale_pack" / "desk_publish.py",
    ROOT / "web" / "lib" / "feed.ts",
]


def test_deleted_hold_strings_stay_gone():
    hits = []
    for path in SCAN:
        text = path.read_text(encoding="utf-8")
        for needle in BANNED:
            if needle in text:
                hits.append(f"{path.relative_to(ROOT)}: {needle}")
    assert hits == [], "deleted hold returned:\n" + "\n".join(hits)
