"""Complete a house date that printed no year.

Printed 20xx on the card or title wins. Else prefer the upcoming
occurrence: this year if that month+day is today, still ahead, or
within the last 14 days; otherwise next year.

That is the listings-catalog prefer-future rule. Last night stays
this year so Tonight does not lose neighbors. January read in
September becomes next January. December read in January becomes
next December.

Year never blocks publishing. Vague prose is refused by the caller
before this function runs. Weekday is accepted and never a veto.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Optional

LOOKBACK_DAYS = 14


def complete_house_year(
    month: int,
    day: int,
    *,
    as_of: Optional[_date],
    printed_years: Optional[set] = None,
    weekday: Optional[int] = None,
) -> Optional[str]:
    """Return YYYY-MM-DD. None only when month+day is not a calendar date."""
    del weekday
    today = as_of or _date.today()
    years = list(printed_years or ())
    if years:
        pick = today.year if today.year in years else min(years)
        try:
            return _date(pick, month, day).isoformat()
        except ValueError:
            return None
    try:
        this_year = _date(today.year, month, day)
    except ValueError:
        return None
    if this_year >= today or (today - this_year).days <= LOOKBACK_DAYS:
        return this_year.isoformat()
    try:
        return _date(today.year + 1, month, day).isoformat()
    except ValueError:
        return this_year.isoformat()
