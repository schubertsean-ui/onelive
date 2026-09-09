"""Yearless house dates. Year never blocks publishing.

Founder 2026-09-08 09:17 PDT:
printed 20xx wins; else prefer the upcoming occurrence;
last 14 days stay this year;
January in September = next January;
December in January = next December;
never return None for a real month+day.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, Optional, Set


def complete_house_year(
    month: int,
    day: int,
    as_of: Optional[date] = None,
    printed_years: Optional[Iterable[int]] = None,
    weekday: Optional[int] = None,
) -> str:
    del weekday  # mismatch still publishes
    today = as_of or date.today()
    years: Set[int] = {int(y) for y in (printed_years or []) if y}
    if years:
        year = sorted(years)[0]
        return _iso(year, month, day)

    this = _safe(today.year, month, day)
    if this is not None:
        if today - timedelta(days=14) <= this <= today:
            return this.isoformat()
        if this >= today:
            return this.isoformat()
    return _iso(today.year + 1, month, day)


def _safe(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _iso(year: int, month: int, day: int) -> str:
    found = _safe(year, month, day)
    if found is not None:
        return found.isoformat()
    return f"{year:04d}-{month:02d}-{day:02d}"
