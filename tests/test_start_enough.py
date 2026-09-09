"""Start is enough. End/duration is optional. Year never blocks."""
from datetime import date

from worker.locale_pack.house_year import complete_house_year
from worker.locale_pack.ticket_a_apply import fill_house_date


def test_yearless_september_in_september_is_this_year():
    assert complete_house_year(9, 9, as_of=date(2026, 9, 9)) == "2026-09-09"


def test_yearless_january_in_september_is_next_year():
    assert complete_house_year(1, 15, as_of=date(2026, 9, 9)) == "2027-01-15"


def test_printed_year_wins():
    assert complete_house_year(9, 9, as_of=date(2026, 9, 9), printed_years=[2027]) == "2027-09-09"


def test_house_text_fills_start():
    assert fill_house_date("Mon., Sept. 9", as_of=date(2026, 9, 9)) == "2026-09-09"
