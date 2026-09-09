from datetime import date
from worker.locale_pack.house_year import complete_house_year


def test_january_in_september_is_next_january():
    assert complete_house_year(1, 15, as_of=date(2026, 9, 8)) == "2027-01-15"


def test_missing_20xx_never_returns_none():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8), printed_years=set()) == "2026-09-08"
