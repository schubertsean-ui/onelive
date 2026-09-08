"""Founder 2026-09-08 — validators must accept this rule.

A trusted desk (Chronicle) that printed a title publishes.
Year is the current year unless the month is past December.
Year never blocks. Missing minute or place is a hole on the card.
Views may filter. The catalog keeps the row.
"""
from datetime import date

from worker.locale_pack.house_year import complete_house_year


def test_yearless_september_card_is_this_year():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8)) == "2026-09-08"


def test_january_in_september_stays_this_year():
    assert complete_house_year(1, 15, as_of=date(2026, 9, 8)) == "2026-01-15"


def test_missing_20xx_is_not_none():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8), printed_years=set())


def test_weekday_mismatch_still_returns_a_date():
    assert complete_house_year(9, 8, as_of=date(2026, 9, 8), weekday=0) == "2026-09-08"
