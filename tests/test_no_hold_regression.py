"""Preempt: old date/place/year holds must not return."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = (ROOT / "worker/locale_pack/desk_publish.py").read_text(encoding="utf-8")
READ = (ROOT / "worker/locale_pack/desk_read.py").read_text(encoding="utf-8")
FEED = (ROOT / "web/lib/feed.ts").read_text(encoding="utf-8")


def test_no_del_as_of():
    assert "del as_of" not in READ


def test_no_yearless_return_none():
    assert "if not years:\n        return None" not in READ


def test_no_date_hold_phrase():
    assert "held until a desk states one" not in PUBLISH


def test_today_does_not_hide_missing_date():
    assert "date-TBA only shows under" not in FEED
