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


def test_past_beyond_grace_refuses_rather_than_rolling_a_year_ahead():
    """CHANGED at evaluator #191 r3 (attacker-smuggle lens), and the previous
    expectation here WAS the defect: this asserted that "July 20" read on
    2026-08-05 resolves to 2027-07-20. The 365-day window makes that the only
    in-window occurrence, so it is unique — but uniqueness is not evidence. A
    venue page listing a bare "July 20" two weeks after July 20 means the date
    that just passed, and publishing a confident event eleven months out is a
    fabrication the source never supports. Past MAX_FUTURE_DAYS: refuse."""
    assert resolve_partial_date_claim("July 20", CTX) == (None, None)


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


# ── Evaluator #191 r3 findings, each pinned by the case that proved it ───────


def test_stale_no_year_listing_is_refused_not_rolled_into_next_year():
    """attacker-smuggle lens: with context 2026-08-05 a "July 4" listing has
    no in-window 2026 occurrence, so the uniqueness window rolled it to
    2027-07-04 — asserting a confident event eleven months out from a page
    that meant last month. Past the horizon the roll is a guess: refuse."""
    assert resolve_partial_date_claim("July 4 8:00 pm", CTX) == (None, None)


def test_the_legitimate_year_wrap_still_resolves():
    """The horizon must not break the case it shares a shape with: a December
    page listing "January 5" is a real near-term event 16 days out."""
    dec = datetime(2026, 12, 20, 19, 0, 0)
    iso, _ = resolve_partial_date_claim("January 5 8:00 pm", dec)
    assert iso == "2027-01-05T20:00:00"


def test_ambiguous_numeric_dates_are_refused_as_the_docstring_always_claimed():
    """Adversarial-review catch (2026-08-06, absence-only lens): this module's
    docstring says ambiguous numeric dates stay refused and
    datetime_normalize enforces exactly that ('ambiguous-numeric-date'), but
    the YEAR-LESS numeric form slipped through here. "03/04 8pm" resolved to
    March 4 purely because dateutil defaults to a US reading — the source
    never said whether it meant March 4 or April 3, and the caller stores the
    guess as source evidence on a public card."""
    feb = datetime(2026, 2, 1, 19, 0, 0)
    for claim in ("03/04 8pm", "3/4 8pm", "04/03 8pm", "3-4 8pm"):
        assert resolve_partial_date_claim(claim, feb) == (None, None), claim


def test_a_month_NAME_still_disambiguates_and_resolves():
    """The refusal must cost only the genuinely ambiguous case: a month name
    is what makes a numeric day unambiguous."""
    feb = datetime(2026, 2, 1, 19, 0, 0)
    assert resolve_partial_date_claim("March 4 8pm", feb)[0] == "2026-03-04T20:00:00"
    assert resolve_partial_date_claim("8 March 8pm", feb)[0] == "2026-03-08T20:00:00"
