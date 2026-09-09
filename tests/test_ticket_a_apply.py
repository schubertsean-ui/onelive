from datetime import date
from types import SimpleNamespace

from worker.locale_pack.ticket_a_apply import apply_to_write, fill_house_date


def test_september_eighth_is_this_year():
    assert fill_house_date("Mon., Sept. 8", as_of=date(2026, 9, 8)) == "2026-09-08"


def test_january_in_september_is_next_year():
    assert fill_house_date("Jan. 15", as_of=date(2026, 9, 8)) == "2027-01-15"


def test_date_hold_is_cleared_when_titled():
    w = SimpleNamespace(
        title="Jutes, Mothica, wilt",
        hold_reason="no desk stated a date",
        extracted={"title": "Jutes, Mothica, wilt"},
    )
    assert apply_to_write(w).hold_reason is None
