"""resolve_partial_date_claim — the stated rule, every branch pinned.

The resolver may ONLY resolve month+day-evidenced claims against context;
everything else returns (None, None) so the R-021 refusal stands untouched.
"""
from datetime import datetime

from worker.datetime_resolve import resolve_partial_date_claim

CTX = datetime(2026, 8, 5, 19, 0, 0)  # the founder's actual evening


def test_month_day_resolves_to_context_year():
    iso, rec = resolve_partial_date_claim("Aug 8 7:30 PM", CTX)
    assert iso == "2026-08-08T19:30:00"
    assert rec["raw"] == "Aug 8 7:30 PM"
    assert "year-from-context" in rec["rule"]
    assert rec["context"] == CTX.isoformat()


def test_recent_past_within_grace_stays_this_year():
    iso, _ = resolve_partial_date_claim("August 2, 9pm", CTX)
    assert iso == "2026-08-02T21:00:00"  # 3 days past — the just-past show


def test_past_beyond_grace_rolls_to_next_year():
    iso, _ = resolve_partial_date_claim("July 20", CTX)
    assert iso == "2027-07-20T00:00:00"


def test_december_fetch_january_claim_crosses_year_boundary():
    iso, _ = resolve_partial_date_claim("Jan 2, 8pm", datetime(2026, 12, 28))
    assert iso == "2027-01-02T20:00:00"


def test_matching_weekday_confirms():
    # Aug 8 2026 IS a Saturday.
    iso, _ = resolve_partial_date_claim("Saturday, Aug 8, 7pm", CTX)
    assert iso == "2026-08-08T19:00:00"


def test_conflicting_weekday_refuses():
    # Aug 8 2026 is NOT a Friday — conflicting evidence, no coin flips.
    iso, rec = resolve_partial_date_claim("Friday, Aug 8, 7pm", CTX)
    assert iso is None and rec is None


def test_time_only_and_weekday_only_stay_refused():
    assert resolve_partial_date_claim("6pm", CTX) == (None, None)
    assert resolve_partial_date_claim("Friday 8pm", CTX) == (None, None)


def test_fully_dated_claim_is_not_this_resolvers_job():
    # normalize_datetime_claim already stores these; the resolver must not
    # double-claim them (month+day+year all evidenced → probes agree on year).
    assert resolve_partial_date_claim("Aug 8 2026 7pm", CTX) == (None, None)


def test_unparseable_and_empty_refuse():
    assert resolve_partial_date_claim("doors at dusk", CTX) == (None, None)
    assert resolve_partial_date_claim("", CTX) == (None, None)
    assert resolve_partial_date_claim(None, CTX) == (None, None)


def test_feb_29_resolves_only_into_a_leap_year():
    # Context late 2027: Feb 29 next occurs 2028 — within the 365-day window.
    iso, _ = resolve_partial_date_claim("Feb 29", datetime(2027, 12, 1))
    assert iso == "2028-02-29T00:00:00"
    # Context early 2026: Feb 29 2026 doesn't exist; 2027 doesn't either —
    # no candidate in window → refuse rather than shift the date.
    assert resolve_partial_date_claim("Feb 29", datetime(2026, 3, 15)) == (None, None)


# ── date-from-the-event's-own-block-text ─────────────────────────────────────
# The live gap: smoke run 31045743483's refusals were ALL bare times, because
# venue calendars print the date once in the block and the extractor returned
# only "8:00 pm". The date is in the block; reading it is evidence.

from worker.datetime_resolve import resolve_time_only_from_block as _from_block


def test_bare_time_takes_the_single_date_its_block_states():
    block = "AUG 8 · Spoon with special guests · Doors 7:00 pm · Show 8:00 pm · $35"
    iso, rec = _from_block("8:00 pm", block, CTX)
    assert iso == "2026-08-08T20:00:00"
    assert rec["rule"].startswith("date-from-event-block-text")


def test_iso_date_in_block_works_too():
    iso, _ = _from_block("19:30", "Event on 2026-08-09 at the Mohawk", CTX)
    assert iso == "2026-08-09T19:30:00"


def test_block_with_no_date_refuses():
    assert _from_block("8:00 pm", "Spoon · Doors 7pm · $35", CTX) == (None, None)


def test_block_naming_TWO_different_dates_refuses():
    # A block listing several dates cannot say which is this event's.
    block = "Summer series: August 8 and August 15 · 8:00 pm"
    assert _from_block("8:00 pm", block, CTX) == (None, None)


def test_same_date_written_twice_still_resolves():
    block = "Sat, August 8 · doors 7 · August 8 show 8:00 pm"
    iso, _ = _from_block("8:00 pm", block, CTX)
    assert iso == "2026-08-08T20:00:00"


def test_a_claim_that_is_not_time_only_is_left_to_the_other_resolver():
    # "Aug 8 7:30 PM" carries its own month+day — this function must not touch it.
    assert _from_block("Aug 8 7:30 PM", "August 8 · show", CTX) == (None, None)


def test_missing_block_text_refuses():
    assert _from_block("8:00 pm", None, CTX) == (None, None)
    assert _from_block("8:00 pm", "", CTX) == (None, None)


def test_block_weekday_that_matches_confirms_the_date():
    # Aug 8 2026 IS a Saturday — the page's own weekday agrees, so resolve.
    iso, _ = _from_block("8:00 pm", "Sat, Aug 8 · Spoon · 8:00 pm", CTX)
    assert iso == "2026-08-08T20:00:00"


def test_block_weekday_that_contradicts_the_date_refuses():
    # Aug 8 2026 is a Saturday, not a Friday: the block contradicts itself
    # (or our context year is wrong). Either way, publish nothing.
    assert _from_block("8:00 pm", "Fri, Aug 8 · Spoon · 8:00 pm", CTX) == (None, None)
