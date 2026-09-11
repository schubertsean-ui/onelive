"""FL-010. Read docs/fix-library/FL-010.md first."""
from pathlib import Path

from worker.locale_pack.desk_fill import fill_patch, fills, venue_label
from worker.locale_pack.fill_public import public_fill_patch

ROOT = Path(__file__).resolve().parents[1]


def test_venue_label_strips_street():
    assert venue_label("Hays City Store, 8989 FM 150, Driftwood, TX 78619") == "Hays City Store"


def test_empty_place_plus_hays_city_store_is_a_fill():
    stored = {
        "title": "Dave Orr Band",
        "place": None,
        "night": "2026-09-10",
        "clocks": ["2026-09-10T18:00:00"],
        "listing_url": "https://calendar.austinchronicle.com/event/dave-orr-band",
    }
    fresh = dict(stored, place="Hays City Store, 8989 FM 150, Driftwood, TX 78619")
    assert fills(stored, fresh) == ["place"]
    assert fill_patch(fresh, ["place"])["venue_name"] == "Hays City Store"


def test_public_fill_patch_carries_title_clock_place():
    fresh = {
        "title": "Dave Orr Band",
        "place": "Hays City Store, 8989 FM 150, Driftwood, TX 78619",
        "clocks": ["2026-09-10T18:00:00-05:00"],
    }
    patch = public_fill_patch(fresh)
    assert patch["venue_name"] == "Hays City Store"
    assert patch["start_time"] == "2026-09-10T18:00:00-05:00"
    assert patch["title"] == "Dave Orr Band"


def test_ingest_no_longer_has_null_only_venue_id_case():
    text = (ROOT / "tools" / "desk_ingest.py").read_text(encoding="utf-8")
    assert "fill_public_rows" in text
    assert "set venue_name" not in text.split("def ingest(", 1)[0]
