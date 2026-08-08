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


# ---------------------------------------------------------------------------
# Misassignment class (R-081). The two-probe trick detects components the
# string OMITS; it is structurally blind to components dateutil MISASSIGNS.
# On a date range the tokenizer takes the range's END DAY as the year and the
# STATED year as a clock time — deterministically, so both probes agree and
# the omission guard passes a fact the source never wrote. Every one of these
# stored a fabricated date with NO refusal raised before the fix.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,was_fabricated", [
    ("Sept 4-27, 2026", "2027-09-04T20:26:00"),      # year 2027 + invented 20:26
    ("September 4-27, 2026", "2027-09-04T20:26:00"),
    ("SEPT 04-27", "2027-09-04T00:00:00"),
    ("Sept 4-5, 2026", "2005-09-04T20:26:00"),       # lands 21 years in the PAST
    ("Dec 26-31, 2026", "2031-12-26T20:26:00"),
])
def test_date_ranges_never_fabricate_a_year(raw, was_fabricated):
    """The defect: a multi-day run (theatre, festival, exhibition) silently
    became a single wrong date. 'Sept 4-5, 2026' -> 2005 is the worst shape —
    a past date disappears from the feed rather than displaying wrongly, so
    the failure is invisible from the outside."""
    normalized, refusal = normalize_datetime_claim(raw)
    assert normalized is None, (
        f"{raw!r} stored {normalized!r} — the source never wrote that year"
    )
    assert refusal == {"raw": raw, "reason": "year-not-stated-in-source"}
    assert normalized != was_fabricated


def test_two_digit_year_refuses_rather_than_inferring_a_century():
    """Stated tradeoff, not an oversight: matching the abbreviated form would
    re-open the range bug, because a range's end day is itself a two-digit
    number. The claim is refused, never lost — it is preserved under
    _provenance.unstored_datetime_claims and still reaches ops review."""
    normalized, refusal = normalize_datetime_claim("Sept 4, 26")
    assert normalized is None
    assert refusal["reason"] == "year-not-stated-in-source"


def test_clock_time_must_be_traceable_to_the_source():
    """Second, independent guard: midnight is the documented default when a
    full date is evidenced and no time is, so it needs no evidence — but any
    OTHER clock time must come from something the page actually wrote."""
    from worker.datetime_normalize import _TIME_EVIDENCE
    assert _TIME_EVIDENCE.search("7:30 PM")
    assert _TIME_EVIDENCE.search("8pm")
    assert _TIME_EVIDENCE.search("2026-09-04T20:00:00")
    assert not _TIME_EVIDENCE.search("Sept 4-27, 2026")


@pytest.mark.parametrize("raw,expected", [
    ("2026-09-04T20:00:00-05:00", "2026-09-04T20:00:00-05:00"),  # ISO + offset
    ("Sept 4, 2026", "2026-09-04T00:00:00"),                     # midnight default
    ("September 4 2026 8pm", "2026-09-04T20:00:00"),
    ("Sept 4, 2026 7:30 PM", "2026-09-04T19:30:00"),
    ("Fri Sep 4 2026", "2026-09-04T00:00:00"),                   # weekday prefix
    ("2026-09-04", "2026-09-04T00:00:00"),
    ("2026-09-04 19:30", "2026-09-04T19:30:00"),
    ("Sat, 04 Sep 2026 20:00:00 -0500", "2026-09-04T20:00:00-05:00"),  # RFC 2822
])
def test_legitimately_dated_strings_still_store(raw, expected):
    """The guards must not cost capture. Every form a real listing writes when
    it DOES state a full date keeps storing exactly as before."""
    normalized, refusal = normalize_datetime_claim(raw)
    assert refusal is None, f"{raw!r} was refused: {refusal}"
    assert normalized == expected
