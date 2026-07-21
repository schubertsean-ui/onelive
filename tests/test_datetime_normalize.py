"""worker/datetime_normalize.py — R-021's fix at the extraction boundary.

The contract: a timestamp is stored ONLY when the extracted string
evidences a full calendar date; anything less (time-only, weekday-only,
month-day-without-year, garbage) becomes NULL with the raw claim returned
for loud preservation — never a fabricated date, never a lost event, never
a psycopg2 InvalidDatetimeFormat at insert time again.

The four live fixtures are the exact strings that errored real runs
29876232668 and 29877305892.
"""
import pytest

from worker.datetime_normalize import (
    normalize_datetime_claim,
    normalize_extracted_datetimes,
)

_LIVE_FAILURES = ["7:00 pm", "6pm", "06:00 PM", "8:00 a.m."]


@pytest.mark.parametrize("raw", _LIVE_FAILURES)
def test_live_failure_fixtures_become_null_with_raw_preserved(raw):
    normalized, discarded = normalize_datetime_claim(raw)
    assert normalized is None
    assert discarded == raw


@pytest.mark.parametrize("raw", [
    "Friday 7pm",          # weekday is not a date
    "July 22, 7pm",        # month+day without year: year would be a guess
    "2026",                # year alone
    "7",                   # bare number
    "TBD", "doors at dusk" # unparseable
])
def test_partial_or_garbage_dates_are_never_guessed(raw):
    normalized, discarded = normalize_datetime_claim(raw)
    assert normalized is None
    assert discarded == raw


@pytest.mark.parametrize("raw,expected_prefix", [
    ("2026-07-22T19:00:00", "2026-07-22T19:00:00"),
    ("2026-07-22 7:00 pm", "2026-07-22T19:00:00"),
    ("July 22 2026 6pm", "2026-07-22T18:00:00"),
    ("2026-07-22", "2026-07-22T00:00:00"),  # date evidenced; midnight is the
                                            # standard no-time convention
])
def test_fully_dated_claims_normalize_to_iso(raw, expected_prefix):
    normalized, discarded = normalize_datetime_claim(raw)
    assert discarded is None
    assert normalized is not None and normalized.startswith(expected_prefix)


def test_none_and_empty_are_silent_nulls():
    for raw in (None, "", "   "):
        assert normalize_datetime_claim(raw) == (None, None)


def test_shaped_dict_normalized_in_place_with_discard_report():
    shaped = {"title": "Show", "start_time": "6pm",
              "end_time": "2026-07-22T21:00:00", "venue_name": "V"}
    discarded = normalize_extracted_datetimes(shaped)
    assert shaped["start_time"] is None
    assert shaped["end_time"].startswith("2026-07-22T21:00:00")
    assert discarded == {"start_time": "6pm"}


def test_clean_extraction_reports_nothing_discarded():
    shaped = {"start_time": "2026-07-22T19:00:00", "end_time": None}
    assert normalize_extracted_datetimes(shaped) == {}
    assert shaped["start_time"].startswith("2026-07-22T19:00:00")
