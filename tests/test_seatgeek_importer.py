"""Unit tests for the SeatGeek licensed-feed fetch client
(worker/importers/seatgeek.py). No network, no DB — the HTTP layer is
monkeypatched and normalize runs on an inline SeatGeek-shaped fixture, so this
proves the fetch/window/de-dupe logic AND the mapping WITHOUT a live client id.

The inline fixture is modeled on the documented SeatGeek Platform /2/events
schema; it is replaced with a captured live payload once the key lands (the
shape is asserted here so a drift in the real payload fails loudly).
"""
import datetime as dt

import pytest

from worker.importers import seatgeek as sg
from worker.importers.normalize import normalize_seatgeek


# ---- fetch: missing credential fails loud, never silent no-op ----------------

def test_fetch_events_missing_client_id_fails_loud(monkeypatch):
    monkeypatch.delenv("SEATGEEK_CLIENT_ID", raising=False)
    with pytest.raises(RuntimeError):
        list(sg.fetch_events())


def test_fetch_events_capcog_missing_client_id_fails_loud(monkeypatch):
    monkeypatch.delenv("SEATGEEK_CLIENT_ID", raising=False)
    with pytest.raises(RuntimeError):
        list(sg.fetch_events_capcog())


# ---- fetch: 1-indexed pagination stops when meta.total is exhausted ----------

def test_fetch_events_paginates_until_total_exhausted(monkeypatch):
    """fetch_events must page (1-indexed) until meta.total is covered, then stop
    — never loop forever, never quit after page 1 when more remain."""
    pages_seen = []

    def fake_get(url, timeout=30):
        # Parse the page number back out of the querystring.
        import urllib.parse as up
        q = up.parse_qs(up.urlparse(url).query)
        page = int(q["page"][0])
        pages_seen.append(page)
        # total=250, per_page=100 → three pages (100,100,50).
        remaining = 250 - (page - 1) * 100
        n = max(0, min(100, remaining))
        return {
            "events": [{"id": (page - 1) * 100 + i, "title": "x"} for i in range(n)],
            "meta": {"total": 250, "page": page, "per_page": 100},
        }

    monkeypatch.setattr(sg, "_get", fake_get)
    out = list(sg.fetch_events("cid", per_page=100, max_pages=10, sleep=0))
    assert pages_seen == [1, 2, 3]  # stopped once total exhausted
    assert len(out) == 250


def test_fetch_events_capcog_windows_and_dedupes(monkeypatch):
    """The comprehensive fetch sweeps multiple time windows and de-dupes by id,
    pulling the full forward calendar without double-counting a show that appears
    in overlapping windows. Mirrors the Ticketmaster capcog windowing test."""
    calls = []

    def fake_fetch_events(client_id, *, start=None, end=None, **kw):
        calls.append((start, end))
        # Each window returns two events; id "shared" recurs in every window.
        yield {"id": f"w-{start[:10]}", "title": "unique per window"}
        yield {"id": "shared", "title": "same show seen in every window"}

    monkeypatch.setattr(sg, "fetch_events", fake_fetch_events)
    fixed_now = dt.datetime(2026, 7, 24, tzinfo=dt.timezone.utc)
    out = list(sg.fetch_events_capcog("cid", windows=3, _now=fixed_now))

    assert len(calls) == 3  # swept three windows
    ids = [e["id"] for e in out]
    assert ids.count("shared") == 1  # de-duped across windows
    assert len([i for i in ids if i.startswith("w-")]) == 3  # one unique per window
    # windows are consecutive and non-overlapping in ordering
    assert calls[0][0] < calls[1][0] < calls[2][0]
    # SeatGeek's datetime filter is naive UTC (no Z / offset).
    assert "Z" not in calls[0][0] and "+" not in calls[0][0]


# ---- normalize round-trip on an inline SeatGeek-shaped fixture ---------------

def _sg_fixture():
    return {
        "id": 6234567,
        "title": "Spoon",
        "short_title": "Spoon",
        "url": "https://seatgeek.com/spoon-tickets/6234567",
        "datetime_utc": "2026-07-25T02:00:00",  # naive UTC, no Z
        "type": "concert",
        "performers": [
            {"name": "Spoon", "primary": True, "type": "band",
             "genres": [{"name": "Indie Rock"}, {"name": "Rock"}],
             "image": "https://seatgeek.com/images/performers/spoon.jpg"},
        ],
        "venue": {"name": "Stubb's", "city": "Austin", "address": "801 Red River St",
                  "location": {"lat": 30.2686, "lon": -97.7361}},
        "stats": {"lowest_price": 35, "highest_price": 75, "average_price": 52},
    }


def test_sg_normalize_round_trip_maps_expected_fields():
    ev = normalize_seatgeek(_sg_fixture())
    assert ev is not None
    assert ev["source_provider"] == "seatgeek"
    assert ev["external_id"] == "6234567"          # id coerced to str
    assert ev["title"] == "Spoon"
    assert ev["category"] == "live-music"          # via seatgeek_domain(type=concert)
    assert ev["subsegment"] == "Indie Rock"        # primary performer's first genre
    assert ev["start_time"] == "2026-07-25T02:00:00Z"  # naive UTC made Z-explicit
    assert ev["price_min"] == 35.0 and ev["price_max"] == 75.0
    assert ev["currency"] == "USD"
    assert ev["is_free"] is False
    assert ev["venue_name"] == "Stubb's"
    assert ev["venue_city"] == "Austin"
    assert ev["venue_address"] == "801 Red River St"
    assert ev["venue_lat"] == 30.2686 and ev["venue_lng"] == -97.7361
    assert ev["performer"] == "Spoon"
    assert ev["confidence"] == "confirmed"
    assert ev["raw"]["id"] == 6234567              # raw payload preserved for audit


def test_sg_normalize_missing_id_or_title_returns_none():
    assert normalize_seatgeek({"title": "no id"}) is None
    assert normalize_seatgeek({"id": 1}) is None
