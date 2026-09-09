"""Yearless house dates. Year never blocks publishing."""
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
    del weekday
    today = as_of or date.today()
    years: Set[int] = {int(y) for y in (printed_years or []) if y}
    if years:
        year = sorted(years)[0]
        found = _safe(year, month, day)
        return found.isoformat() if found else f"{year:04d}-{month:02d}-{day:02d}"
    this = _safe(today.year, month, day)
    if this is not None:
        if today - timedelta(days=14) <= this <= today:
            return this.isoformat()
        if this >= today:
            return this.isoformat()
    nxt = _safe(today.year + 1, month, day)
    return nxt.isoformat() if nxt else f"{today.year + 1:04d}-{month:02d}-{day:02d}"


def _safe(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None
