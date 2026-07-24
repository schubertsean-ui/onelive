"""Network-free unit tests for worker/importers/ticketmaster.py — URL
construction, fail-loud on a missing key, and pagination/termination bounds
(deep-paging cap, totalPages, empty page). `_get` is stubbed, so no live API.
"""
import pytest

import worker.importers.ticketmaster as tm


def test_missing_key_fails_loud(monkeypatch):
    monkeypatch.delenv("TICKETMASTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        list(tm.fetch_events(""))


def test_url_construction(monkeypatch):
    seen = []

    def fake_get(url, timeout=30):
        seen.append(url)
        return {"_embedded": {"events": []}}  # empty → stop after one page

    monkeypatch.setattr(tm, "_get", fake_get)
    list(tm.fetch_events("KEY123", latlong="30.0,-97.0", radius=42, size=25))
    assert len(seen) == 1
    u = seen[0]
    assert "apikey=KEY123" in u
    assert ("latlong=30.0%2C-97.0" in u) or ("latlong=30.0,-97.0" in u)
    assert "radius=42" in u and "size=25" in u and "page=0" in u
    assert "sort=date%2Casc" in u or "sort=date,asc" in u


def test_pagination_stops_on_empty(monkeypatch):
    pages = [
        {"_embedded": {"events": [{"id": "1"}, {"id": "2"}]}, "page": {"totalPages": 5}},
        {"_embedded": {"events": [{"id": "3"}]}, "page": {"totalPages": 5}},
        {"_embedded": {"events": []}, "page": {"totalPages": 5}},
    ]
    calls = {"n": 0}

    def fake_get(url, timeout=30):
        i = calls["n"]
        calls["n"] += 1
        return pages[i]

    monkeypatch.setattr(tm, "_get", fake_get)
    monkeypatch.setattr(tm.time, "sleep", lambda *_a, **_k: None)
    got = list(tm.fetch_events("K", size=100, max_pages=10))
    assert [e["id"] for e in got] == ["1", "2", "3"]
    assert calls["n"] == 3  # stopped on the empty page


def test_pagination_respects_total_pages(monkeypatch):
    monkeypatch.setattr(tm, "_get",
                        lambda url, timeout=30: {"_embedded": {"events": [{"id": "1"}]},
                                                 "page": {"totalPages": 1}})
    got = list(tm.fetch_events("K", size=100, max_pages=10))
    assert [e["id"] for e in got] == ["1"]  # page 1 >= totalPages 1 → stop


def test_deep_paging_cap(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, timeout=30):
        calls["n"] += 1
        return {"_embedded": {"events": [{"id": str(calls["n"])}]},
                "page": {"totalPages": 999}}

    monkeypatch.setattr(tm, "_get", fake_get)
    monkeypatch.setattr(tm.time, "sleep", lambda *_a, **_k: None)
    list(tm.fetch_events("K", size=500, max_pages=99))
    # size*page < 1000: page0 (0) and page1 (500) allowed; page2 (1000) stops.
    assert calls["n"] == 2


def test_empty_first_page_yields_nothing(monkeypatch):
    monkeypatch.setattr(tm, "_get", lambda url, timeout=30: {})
    assert list(tm.fetch_events("K")) == []
