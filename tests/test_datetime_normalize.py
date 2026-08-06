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
    normalized, refusal = normalize_datetime_claim(raw)
    assert normalized is None
    assert refusal == {"raw": raw, "reason": "no-full-date-evidence"}


@pytest.mark.parametrize("raw,reason", [
    ("Friday 7pm", "no-full-date-evidence"),   # weekday is not a date
    ("July 22, 7pm", "no-full-date-evidence"), # month+day without year
    ("2026", "no-full-date-evidence"),         # year alone
    ("7", "no-full-date-evidence"),            # bare number
    ("TBD", "unparseable"), ("doors at dusk", "unparseable"),
])
def test_partial_or_garbage_dates_are_never_guessed(raw, reason):
    normalized, refusal = normalize_datetime_claim(raw)
    assert normalized is None
    assert refusal == {"raw": raw, "reason": reason}


@pytest.mark.parametrize("raw,expected_prefix", [
    ("2026-07-22T19:00:00", "2026-07-22T19:00:00"),
    ("2026-07-22 7:00 pm", "2026-07-22T19:00:00"),
    ("July 22 2026 6pm", "2026-07-22T18:00:00"),
    ("2026-07-22", "2026-07-22T00:00:00"),  # date evidenced; midnight is the
                                            # standard no-time convention
])
def test_fully_dated_claims_normalize_to_iso(raw, expected_prefix):
    normalized, refusal = normalize_datetime_claim(raw)
    assert refusal is None
    assert normalized is not None and normalized.startswith(expected_prefix)


def test_none_and_empty_are_silent_nulls():
    for raw in (None, "", "   "):
        assert normalize_datetime_claim(raw) == (None, None)


def test_shaped_dict_normalized_in_place_with_refusal_report():
    shaped = {"title": "Show", "start_time": "6pm",
              "end_time": "2026-07-22T21:00:00", "venue_name": "V"}
    refused = normalize_extracted_datetimes(shaped)
    assert shaped["start_time"] is None
    assert shaped["end_time"].startswith("2026-07-22T21:00:00")
    assert refused == {"start_time": {"raw": "6pm",
                                      "reason": "no-full-date-evidence"}}


def test_clean_extraction_reports_nothing_discarded():
    shaped = {"start_time": "2026-07-22T19:00:00", "end_time": None}
    assert normalize_extracted_datetimes(shaped) == {}
    assert shaped["start_time"].startswith("2026-07-22T19:00:00")


@pytest.mark.parametrize("raw", [
    "2026-07-22 7pm ET", "2026-07-22 7:00 pm CT", "2026-07-22 7pm PT",
    "2026-07-22 7pm CST", "2026-07-22 7pm EST",
])
def test_unrecognized_timezone_abbreviations_are_refused(raw):
    """r1 nit: dateutil DROPS unknown tz abbreviations and returns a naive
    datetime — a timestamptz column would silently reinterpret it hours
    off. The UnknownTimezoneWarning is the mechanical signal; we refuse,
    with the reason naming the tz problem (r2 nit: these are dated but
    tz-unusable, not "undated")."""
    normalized, refusal = normalize_datetime_claim(raw)
    assert normalized is None
    assert refusal == {"raw": raw,
                       "reason": "unrecognized-timezone-abbreviation"}


def test_explicit_utc_offset_is_kept_with_offset():
    normalized, refusal = normalize_datetime_claim("2026-07-22T19:00:00-05:00")
    assert refusal is None
    assert normalized == "2026-07-22T19:00:00-05:00"


@pytest.mark.parametrize("raw", ["03/04/2026", "3/4/2026 7pm", "04-03-2026"])
def test_ambiguous_numeric_dates_are_refused(raw):
    """r1 nit: '03/04/2026' is March 4 in Austin and April 3 in London —
    dateutil quietly applies the US assumption. Order unknowable: refuse."""
    normalized, refusal = normalize_datetime_claim(raw)
    assert normalized is None
    assert refusal == {"raw": raw, "reason": "ambiguous-numeric-date"}


@pytest.mark.parametrize("raw,prefix", [
    ("13/04/2026", "2026-04-13"),   # first field can't be a month
    ("03/03/2026", "2026-03-03"),   # equal fields: same date either way
    ("2026-03-04", "2026-03-04"),   # year-first ISO is unambiguous
])
def test_unambiguous_numeric_dates_are_kept(raw, prefix):
    normalized, refusal = normalize_datetime_claim(raw)
    assert refusal is None
    assert normalized.startswith(prefix)


_CLAIM = {"start_time": {"raw": "6pm", "reason": "no-full-date-evidence"}}


def test_preservation_with_clean_or_absent_provenance():
    from worker.datetime_normalize import preserve_discarded_claims
    meta = {}
    assert preserve_discarded_claims(meta, _CLAIM) is False
    assert meta["_provenance"]["unstored_datetime_claims"] == _CLAIM
    meta = {"_provenance": {"model": "x"}}
    assert preserve_discarded_claims(meta, _CLAIM) is False
    assert meta["_provenance"]["model"] == "x"  # existing keys survive
    assert meta["_provenance"]["unstored_datetime_claims"] == _CLAIM


def test_preservation_merges_existing_claims_never_overwrites():
    """r2 nit: upstream claims for OTHER fields survive; same-field
    refusals take the newest value."""
    from worker.datetime_normalize import preserve_discarded_claims
    prior = {"end_time": {"raw": "9pm", "reason": "no-full-date-evidence"}}
    meta = {"_provenance": {"unstored_datetime_claims": dict(prior)}}
    assert preserve_discarded_claims(meta, _CLAIM) is False
    merged = meta["_provenance"]["unstored_datetime_claims"]
    assert merged["end_time"] == prior["end_time"]
    assert merged["start_time"] == _CLAIM["start_time"]


@pytest.mark.parametrize("bad", ["corrupt-string", 42, ["list"], True])
def test_malformed_provenance_is_replaced_never_skipped(bad):
    """r1 BLOCKER inverted into the contract: a non-dict _provenance must
    not silently skip preservation — it is replaced, the claims land, and
    the malformed original stays visible IN FULL (r2 blocker: truncation
    is itself data loss; JSON-serializable values are kept as-is)."""
    from worker.datetime_normalize import preserve_discarded_claims
    meta = {"_provenance": bad}
    assert preserve_discarded_claims(meta, _CLAIM) is True
    assert meta["_provenance"]["unstored_datetime_claims"] == _CLAIM
    assert meta["_provenance_malformed_original"] == bad


def test_malformed_unserializable_provenance_kept_as_full_repr():
    from worker.datetime_normalize import preserve_discarded_claims
    bad = object()
    meta = {"_provenance": bad}
    assert preserve_discarded_claims(meta, _CLAIM) is True
    assert meta["_provenance_malformed_original"] == repr(bad)  # complete
