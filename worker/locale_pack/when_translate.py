"""Diverse printed clocks → one 1Live when.

Not a Chronicle type. Not a "house" field. A translator:
any trusted door's date string becomes ISO date or datetime.
Year is current unless that page/site printed a 20xx.
Start is enough. End is optional. Never invent 17:00.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from worker.locale_pack.house_year import complete_house_year as complete_year

_MONTH_DAY = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b",
    re.I,
)
_ISO = re.compile(r"^(20\d{2})-(\d{2})-(\d{2})(?:[T ].+)?$")
_SLASH = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(20\d{2}))?\b")
_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def printed_years(text: str) -> list[int]:
    return [int(y) for y in re.findall(r"\b(20\d{2})\b", text or "")]


def translate_when(
    text: Optional[str],
    as_of: Optional[date] = None,
    page_text: Optional[str] = None,
) -> Optional[str]:
    """Return YYYY-MM-DD when the door printed a calendar day we can read.

    Accepts ISO, Month D, Weekday Month D, M/D, M/D/YYYY.
    Does not invent a minute.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    iso = _ISO.match(raw)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
    years = printed_years(raw) or printed_years(page_text or "")
    md = _MONTH_DAY.search(raw)
    if md:
        mon, day_s = md.groups()
        return complete_year(
            _MONTHS[mon.lower()], int(day_s), as_of=as_of, printed_years=years,
        )
    sl = _SLASH.search(raw)
    if sl:
        a, b, y = sl.groups()
        month, day = int(a), int(b)
        if month > 12 and day <= 12:
            month, day = day, month
        if not 1 <= month <= 12:
            return None
        extra = [int(y)] if y else years
        return complete_year(month, day, as_of=as_of, printed_years=extra)
    return None
