from datetime import date

from worker.locale_pack.when_translate import translate_when


def test_iso():
    assert translate_when("2026-09-09T20:00:00-05:00") == "2026-09-09"


def test_month_day_assumes_current_year():
    assert translate_when("Wed., Sept. 9", as_of=date(2026, 9, 9)) == "2026-09-09"


def test_slash_date():
    assert translate_when("9/9/26", as_of=date(2026, 9, 9)) == "2026-09-09"


def test_printed_year_on_page_wins():
    assert translate_when("Sept. 9", as_of=date(2026, 9, 9), page_text="Season 2027") == "2027-09-09"
