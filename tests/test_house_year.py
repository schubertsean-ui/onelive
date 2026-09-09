"""House-date year: prefer upcoming. Year never blocks."""
from datetime import date

from worker.locale_pack.house_year import complete_house_year


def test_today_stays_this_year():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8)) == "2026-09-08"


def test_yesterday_stays_this_year():
    assert complete_house_year(9, 7, as_of=date(2026, 9, 8)) == "2026-09-07"


def test_january_in_september_is_next_january():
    assert complete_house_year(1, 15, as_of=date(2026, 9, 8)) == "2027-01-15"


def test_december_in_january_is_next_december():
    assert complete_house_year(12, 12, as_of=date(2027, 1, 15)) == "2027-12-12"


def test_printed_year_wins():
    assert complete_house_year(
        9, 8, as_of=date(2026, 9, 8), printed_years={2027}
    ) == "2027-09-08"


def test_weekday_mismatch_still_publishes():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8), weekday=0) == "2026-09-08"


def test_missing_20xx_never_returns_none():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8), printed_years=set()) == (
        "2026-09-08"
    )
