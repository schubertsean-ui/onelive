"""Lock the live Chronicle card shape (2026-09-08 EventSearch).

Live card: title is /event/ <a>, date is sibling text with no year,
venue is sibling /location/ <a>. Old reader saw title only → no date,
no place → hold. This test makes that regression impossible.
"""
from datetime import date

from worker.locale_pack.house_year import complete_house_year


def test_story_sessions_yearless_line_is_2026_09_10():
    assert complete_house_year(9, 10, as_of=date(2026, 9, 8)) == "2026-09-10"


def test_barbie_first_printed_night_is_2026_09_09():
    assert complete_house_year(9, 9, as_of=date(2026, 9, 8)) == "2026-09-09"


def test_yearless_never_returns_none():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8), printed_years=set()) == (
        "2026-09-08"
    )
