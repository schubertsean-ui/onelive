"""Ingest must import before it walks.

Run 22 died after 14 minutes: ticket_a_apply asked for complete_year,
house_year only exported complete_house_year. This test is that check.
"""
from worker.locale_pack.house_year import complete_house_year, complete_year
from worker.locale_pack.ticket_a_apply import (
    apply_to_write,
    apply_to_writes,
    fill_house_date,
    fill_printed_date,
)
from worker.locale_pack.when_translate import translate_when
from worker.locale_pack.existence import hold_reason


def test_year_completers_are_the_same_function():
    assert complete_year is complete_house_year
    assert complete_year(9, 9) == complete_house_year(9, 9)


def test_printed_date_alias():
    assert fill_printed_date is fill_house_date


def test_apply_and_translator_import():
    assert callable(apply_to_write)
    assert callable(apply_to_writes)
    assert callable(translate_when)
    assert callable(hold_reason)
