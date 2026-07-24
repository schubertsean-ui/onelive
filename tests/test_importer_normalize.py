"""Unit tests for the deterministic licensed-feed importer core
(worker/importers/{domain_map,normalize}.py). No network, no DB — fixtures only,
so this proves the full mapping/normalization WITHOUT a live API key.

Fixtures under tests/fixtures/licensed/ are modeled on the documented
Ticketmaster Discovery / SeatGeek Platform schemas; they are replaced with
captured live payloads once the keys land (the shapes are asserted here so a
drift in the real payload fails loudly).
"""
import json
import pathlib

from worker.importers.domain_map import (
    DOMAINS,
    seatgeek_domain,
    ticketmaster_domain,
    unmapped,
)
from worker.importers.normalize import normalize_seatgeek, normalize_ticketmaster

FIX = pathlib.Path(__file__).parent / "fixtures" / "licensed"


def _load(name):
    return json.loads((FIX / name).read_text())


# ---- domain_map --------------------------------------------------------------

def test_tm_segment_music_is_live_music():
    assert ticketmaster_domain("Music", "Jazz", "Bebop") == ("live-music", "Jazz · Bebop")


def test_tm_arts_theatre_refines_by_genre():
    assert ticketmaster_domain("Arts & Theatre", "Theatre", None)[0] == "theater"
    assert ticketmaster_domain("Arts & Theatre", "Classical", None)[0] == "performing-arts"
    assert ticketmaster_domain("Arts & Theatre", "Comedy", None)[0] == "comedy"
    assert ticketmaster_domain("Arts & Theatre", "Dance", None)[0] == "dance"
    assert ticketmaster_domain("Arts & Theatre", "Children's Theatre", None)[0] == "family"


def test_tm_sports_and_film():
    assert ticketmaster_domain("Sports", "Basketball", "NBA")[0] == "sports"
    assert ticketmaster_domain("Film", "Miscellaneous", None)[0] == "film"


def test_tm_unknown_segment_falls_back_visibly():
    domain, _ = ticketmaster_domain("Nonsense", "Whatever", None)
    assert domain == "fairs-expos"
    assert "UNMAPPED" in unmapped("ticketmaster", "Nonsense/Whatever")


def test_sg_type_mapping():
    assert seatgeek_domain("concert", ["Indie Rock"]) == ("live-music", "Indie Rock")
    assert seatgeek_domain("theater", None)[0] == "theater"
    assert seatgeek_domain("comedy", None)[0] == "comedy"
    assert seatgeek_domain("nba", None)[0] == "sports"
    assert seatgeek_domain("classical_opera", None)[0] == "performing-arts"


def test_all_mapped_domains_are_canonical():
    for seg, gen in [("Music", "Rock"), ("Sports", "NBA"), ("Arts & Theatre", "Theatre"),
                     ("Arts & Theatre", "Classical"), ("Film", None)]:
        d, _ = ticketmaster_domain(seg, gen, None)
        assert d in DOMAINS


# ---- Ticketmaster normalize --------------------------------------------------

def test_tm_normalize_fields():
    ev = normalize_ticketmaster(_load("ticketmaster_event.json"))
    assert ev is not None
    assert ev["source_provider"] == "ticketmaster"
    assert ev["external_id"] == "vvG1zZfbn0aK-A"
    assert ev["title"] == "Austin Symphony: Beethoven's Ninth"
    assert ev["category"] == "performing-arts"
    assert ev["subsegment"] == "Classical · Classical/Vocal"
    assert ev["start_time"] == "2026-07-25T01:00:00Z"
    assert ev["on_sale_status"] == "onsale"
    assert ev["status"] == "scheduled"
    assert ev["price_min"] == 25.0 and ev["price_max"] == 95.0
    assert ev["currency"] == "USD"
    assert ev["is_free"] is False
    assert ev["venue_name"] == "Bass Concert Hall"
    assert ev["venue_city"] == "Austin"
    assert ev["venue_lat"] == 30.2849 and ev["venue_lng"] == -97.7304
    assert ev["performer"] == "Austin Symphony Orchestra"
    assert ev["confidence"] == "confirmed"
    # widest 16:9 image chosen
    assert ev["image_url"].endswith("widest.jpg")


def test_tm_cancelled_status_maps_event_status():
    raw = _load("ticketmaster_event.json")
    raw["dates"]["status"]["code"] = "cancelled"
    ev = normalize_ticketmaster(raw)
    assert ev["on_sale_status"] == "cancelled"
    assert ev["status"] == "cancelled"


def test_tm_missing_id_or_name_returns_none():
    assert normalize_ticketmaster({"name": "no id"}) is None
    assert normalize_ticketmaster({"id": "x"}) is None


def test_tm_free_event_flag():
    raw = _load("ticketmaster_event.json")
    raw["priceRanges"] = [{"currency": "USD", "min": 0.0, "max": 0.0}]
    ev = normalize_ticketmaster(raw)
    assert ev["is_free"] is True


# ---- SeatGeek normalize ------------------------------------------------------

def test_sg_normalize_fields():
    ev = normalize_seatgeek(_load("seatgeek_event.json"))
    assert ev is not None
    assert ev["source_provider"] == "seatgeek"
    assert ev["external_id"] == "6234567"
    assert ev["title"] == "Spoon"
    assert ev["category"] == "live-music"
    assert ev["subsegment"] == "Indie Rock"
    assert ev["start_time"] == "2026-07-25T02:00:00Z"  # UTC made explicit for timestamptz
    assert ev["price_min"] == 35.0 and ev["price_max"] == 75.0
    assert ev["currency"] == "USD"
    assert ev["venue_name"] == "Stubb's"
    assert ev["venue_lat"] == 30.2686 and ev["venue_lng"] == -97.7361
    assert ev["performer"] == "Spoon"
    assert ev["confidence"] == "confirmed"


def test_sg_missing_id_or_title_returns_none():
    assert normalize_seatgeek({"title": "no id"}) is None
    assert normalize_seatgeek({"id": 1}) is None
