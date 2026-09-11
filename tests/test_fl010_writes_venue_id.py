"""FL-010. Tonight prints venue.name via event.venue_id. That is the write target."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fill_helper_maps_place_to_venue_name_for_resolve():
    from worker.locale_pack.desk_fill import fill_patch
    patch = fill_patch({"place": "Hays City Store"}, ["place"])
    assert patch["venue_name"] == "Hays City Store"


def test_desk_ingest_fill_writes_venue_id_not_venue_name_column():
    text = (ROOT / "tools" / "desk_ingest.py").read_text(encoding="utf-8")
    assert "resolve_venue_id" in text
    assert "set venue_id" in text
    assert "fill(event_id, fill_patch(fresh" in text
