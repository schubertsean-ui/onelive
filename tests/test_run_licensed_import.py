"""Tests for worker/importers/run_licensed_import.py fail-loud behavior — invalid
--max-pages and zero-event imports must NOT exit green. Network/DB-free.
"""
import worker.importers.run_licensed_import as r


def test_max_pages_below_one_fails_closed():
    assert r.main(["--max-pages", "0"]) == 2
    assert r.main(["--max-pages", "-3"]) == 2


def test_zero_events_fails_loud(monkeypatch):
    monkeypatch.setenv("TICKETMASTER_API_KEY", "K")
    monkeypatch.setattr(r, "fetch_events_capcog", lambda *a, **k: iter([]))
    assert r.main(["--max-pages", "2", "--dry-run"]) == 3


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.delenv("TICKETMASTER_API_KEY", raising=False)
    assert r.main(["--max-pages", "2"]) == 2


def test_dry_run_with_events_succeeds_without_db(monkeypatch):
    monkeypatch.setenv("TICKETMASTER_API_KEY", "K")
    monkeypatch.setattr(r, "fetch_events_capcog", lambda *a, **k: iter([{"id": "1"}]))
    monkeypatch.setattr(r, "normalize_ticketmaster", lambda e: {"category": "live-music"})
    assert r.main(["--max-pages", "2", "--dry-run"]) == 0
