"""FL-010. Empty Place on a public row + incoming Hays City Store = fill that row."""
from worker.locale_pack.desk_fill import fill_patch, fills


def test_empty_place_plus_hays_city_store_is_a_fill():
    stored = {
        "title": "Dave Orr Band",
        "place": None,
        "night": "2026-09-10",
        "clocks": ["2026-09-10T18:00:00"],
        "listing_url": "https://calendar.austinchronicle.com/event/dave-orr-band",
        "vias": ["Austin Chronicle Events"],
    }
    fresh = dict(stored, place="Hays City Store")
    assert fills(stored, fresh) == ["place"]
    assert fill_patch(fresh, ["place"])["venue_name"] == "Hays City Store"


def test_same_place_is_not_a_fill():
    stored = {"place": "Hays City Store", "clocks": ["2026-09-10T18:00:00-05:00"]}
    fresh = {"place": "Hays City Store", "clocks": ["2026-09-10T18:00:00-05:00"]}
    assert fills(stored, fresh) == []


def test_empty_clock_plus_chicago_6pm_is_a_fill():
    stored = {"place": "Hays City Store", "clocks": []}
    fresh = {"place": "Hays City Store", "clocks": ["2026-09-10T18:00:00-05:00"]}
    assert fills(stored, fresh) == ["clocks"]
    assert fill_patch(fresh, ["clocks"])["start_time"] == "2026-09-10T18:00:00-05:00"
