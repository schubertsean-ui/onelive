"""Founder 2026-09-10 Chronicle list card. QA gate before the next write."""
from datetime import date

from worker.locale_pack.card_place import place_from_card_text
from worker.locale_pack.house_dates import house_occurrences

DAVE_ORR = """Dave Orr Band
Thu., Sept. 10, 6 p.m.
Hays City Store
8989 FM 150, Driftwood | Beyond Austin
MUSIC
512/722-3905
"""

JO_JAMES = """Jo James (performance & record signing)
Thu., Sept. 10, 5:30 p.m.
Waterloo Records
1105 N. Lamar, Austin | Old West Austin
MUSIC
512/474-2500
"""


def test_dave_orr_clock_is_chicago_6pm():
    rows = house_occurrences(DAVE_ORR, "", date(2026, 9, 10))
    assert rows, "card printed a night"
    assert rows[0]["when"] == "2026-09-10T18:00:00-05:00"


def test_dave_orr_place_is_hays_city_store():
    name, street = place_from_card_text(DAVE_ORR)
    assert name == "Hays City Store"
    assert street.startswith("8989 FM 150")


def test_jo_james_clock_and_waterloo():
    rows = house_occurrences(JO_JAMES, "", date(2026, 9, 10))
    assert rows[0]["when"] == "2026-09-10T17:30:00-05:00"
    name, street = place_from_card_text(JO_JAMES)
    assert name == "Waterloo Records"
    assert street.startswith("1105 N. Lamar")
