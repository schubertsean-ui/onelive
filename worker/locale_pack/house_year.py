"""Complete a house date that printed no year.

Founder 2026-09-08: the year is the current year unless the month is past
December. This must never block publishing.

World-class analog — listings catalog, not a reminder scheduler:

* dateutil.parser default=now fills an omitted year from today.
* Newspaper / Chronicle house style: "Tue., Sept. 8" in a 2026 issue is 2026.
* Google Calendar / Outlook / Eventbrite *quick-add* bump a past month+day
  to next year. That analog is for creating an upcoming reminder. Our walk
  is Chronicle EventSearch all-dates, which still lists last night. Bumping
  Sept 7 on Sept 8 invents 2027 and hides neighbors from Tonight.
* December wrap only: a Jan/Feb card read in December is next year; a
  Nov/Dec card read in January is last year.

Printed 20xx on the card or in the page title / h1–h3 still wins.
Vague prose and two different house dates on one card still return None.
A weekday mismatch never returns None.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Optional


def current_year(as_of: Optional[_date], month: int) -> int:
    """Year to use when the card omitted 20xx."""
    today = as_of or _date.today()
    year = today.year
    if today.month == 12 and month <= 2:
        return year + 1
    if today.month == 1 and month >= 11:
        return year - 1
    return year


def complete_house_year(
    month: int,
    day: int,
    *,
    as_of: Optional[_date],
    printed_years: Optional[set] = None,
    weekday: Optional[int] = None,
) -> Optional[str]:
    """Return YYYY-MM-DD. None only when month+day is not a calendar date."""
    years = list(printed_years or ())
    if not years:
        years = [current_year(as_of, month)]
    found = []
    matched = []
    for year in years:
        try:
            candidate = _date(year, month, day)
        except ValueError:
            continue
        if candidate not in found:
            found.append(candidate)
        if weekday is not None and candidate.weekday() == weekday:
            if candidate not in matched:
                matched.append(candidate)
    if len(matched) == 1:
        return matched[0].isoformat()
    if found:
        return found[0].isoformat()
    try:
        return _date(current_year(as_of, month), month, day).isoformat()
    except ValueError:
        return None
