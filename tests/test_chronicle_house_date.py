"""Chronicle house date + sibling card — founder 2026-09-08.

Year is the current year. Year never blocks. A list card that prints
Tue., Sept. 8 next to the /event/ permalink and a /location/ venue
must yield a night and a place.
"""
from __future__ import annotations

from datetime import date

import pytest

from worker.locale_pack import pack as lp
from worker.locale_pack.desk_read import read
from worker.locale_pack.house_year import complete_house_year

CAPCOG = "us-tx-capcog"


@pytest.fixture(scope="module")
def desk():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}["austin-chronicle-eventsearch"]


def test_yearless_weekday_house_date_is_current_year(desk):
    html = """<!doctype html><html><head><title>Events</title></head><body>
    <div>
      <a href=\"/event/jutes-14327001\">Jutes, Mothica, wilt</a>
      <span>Tue., Sept. 8</span>
      <a href=\"/location/emos-austin-11830001\">Emo's Austin</a>
    </div>
    </body></html>"""
    result = read(desk, html, base_url=desk.url, as_of=date(2026, 9, 8))
    assert result.count >= 1
    row = result.rows[0]
    assert row.when == "2026-09-08"
    assert "Emo" in (row.place_text or "")


def test_yearless_month_day_without_weekday_is_current_year(desk):
    html = """<!doctype html><html><head><title>Events</title></head><body>
    <div>
      <a href=\"/event/meltt-14327002\">Meltt, Low Hum</a>
      <span>Sept. 8</span>
      <a href=\"/location/antones-11830002\">Antone's Nightclub</a>
    </div>
    </body></html>"""
    result = read(desk, html, base_url=desk.url, as_of=date(2026, 9, 8))
    assert result.rows[0].when == "2026-09-08"


def test_tickets_sibling_does_not_drop_date_or_venue(desk):
    """A tickets link in the same parent used to collapse the row to the title."""
    html = """<!doctype html><html><head><title>Events</title></head><body>
    <div class=\"listing\">
      <a href=\"/event/parker-jazz-14327003\">Parker Jazz Club House Band</a>
      <span>Tue., Sept. 8</span>
      <a href=\"/location/parker-jazz-club-11830003\">Parker Jazz Club</a>
      <a href=\"https://tickets.example/e/123\">Get Tickets</a>
    </div>
    </body></html>"""
    result = read(desk, html, base_url=desk.url, as_of=date(2026, 9, 8))
    assert result.count >= 1
    row = result.rows[0]
    assert row.when == "2026-09-08"
    assert "Parker" in (row.place_text or "")


def test_complete_house_year_never_returns_none_for_sept_8():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8), printed_years=set()) == (
        "2026-09-08"
    )
