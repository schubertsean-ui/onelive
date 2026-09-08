"""Complete a house date that printed no year.

Founder 2026-09-08: year is the current year unless the month is past
December. Year never blocks publishing. Analog is a listings catalog
(Chronicle / TimeOut / dateutil default=today), not Google Calendar
next-occurrence. January read in September stays this year.

Printed 20xx on the card or title wins. Weekday is accepted and never
a veto. Vague prose is refused by the caller before this function runs.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Optional


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
        return _date(today.year, month, day).isoformat()
    except ValueError:
        return None
