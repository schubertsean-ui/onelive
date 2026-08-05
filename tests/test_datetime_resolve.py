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
