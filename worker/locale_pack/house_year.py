"""Complete a house date that printed no year.

Founder 2026-09-08 09:17 PDT: yearless month+day prefers the upcoming
night. Last ~14 days stay this year. Printed 20xx on the card wins.
January in September is next January. December in January is next
December. Year never blocks publishing. Weekday is never a veto.

Vague prose is refused by the caller before this function runs.
"""
from __future__ import annotations

from datetime import date as _date, timedelta
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
        this_year = _date(today.year, month, day)
    except ValueError:
        return None
    if this_year <= today and (today - this_year) <= timedelta(days=14):
        return this_year.isoformat()
    if this_year >= today:
        return this_year.isoformat()
    try:
        return _date(today.year + 1, month, day).isoformat()
    except ValueError:
        return None
