"""Founder 2026-09-08: current year, December wrap, year never blocks."""
from datetime import date

from worker.locale_pack.house_year import complete_house_year, current_year


def test_september_card_on_september_8_is_this_year():
    # Tue., Sept. 8 2026 is a Tuesday.
    assert complete_house_year(
        9, 8, as_of=date(2026, 9, 8), weekday=1
    ) == "2026-09-08"


def test_missing_20xx_never_returns_none():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8), printed_years=set()) == (
        "2026-09-08"
    )


def test_january_in_september_stays_this_year():
    # Catalog analog: all-dates EventSearch still lists January nights.
    assert complete_house_year(1, 5, as_of=date(2026, 9, 8)) == "2026-01-05"


def test_december_wraps_january_to_next_year():
    assert current_year(date(2026, 12, 31), 1) == 2027
    assert complete_house_year(1, 1, as_of=date(2026, 12, 31)) == "2027-01-01"


def test_january_wraps_december_to_last_year():
    assert current_year(date(2027, 1, 2), 12) == 2026
    assert complete_house_year(12, 31, as_of=date(2027, 1, 2)) == "2026-12-31"


def test_printed_year_wins():
    assert complete_house_year(
        9, 8, as_of=date(2026, 9, 8), printed_years={2025}
    ) == "2025-09-08"


def test_weekday_mismatch_still_publishes():
    # Sept 8 2026 is Tuesday (1). Card printed Monday (0). Still this year.
    assert complete_house_year(
        9, 8, as_of=date(2026, 9, 8), weekday=0
    ) == "2026-09-08"
