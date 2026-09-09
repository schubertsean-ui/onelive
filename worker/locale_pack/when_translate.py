"""Universal when-translator. Any desk's printed date → 1Live when (YYYY-MM-DD).

Not Chronicle-specific. Not a 'house' type. Year is current unless the
same page/site printed a 20xx. Do not invent a minute.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Optional

from worker.locale_pack.house_year import complete_house_year

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_ISO = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_MDY = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(20\d{2}|\d{2}))?\b")
_MON_DAY = re.compile(
    r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(\d{1,2})\b",
    re.I,
)
_YEAR = re.compile(r"\b(20\d{2})\b")


def printed_years(text: str) -> list[int]:
    return [int(y) for y in _YEAR.findall(text or "")]


def complete_year(month: int, day: int, as_of: Optional[date] = None,
                  printed: Optional[list[int]] = None) -> str:
    return complete_house_year(month, day, as_of=as_of, printed_years=printed)


def translate_when(text: Optional[str], as_of: Optional[date] = None,
                   page_text: Optional[str] = None) -> Optional[str]:
    """Turn a third-party date string into YYYY-MM-DD. None if nothing readable."""
    raw = (text or "").strip()
    if not raw:
        return None
    years = printed_years(raw) or printed_years(page_text or "")
    iso = _ISO.search(raw)
    if iso:
        y, m, d = (int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        return f"{y:04d}-{m:02d}-{d:02d}"
    mon = _MON_DAY.search(raw)
    if mon:
        return complete_year(_MONTHS[mon.group(1).lower()], int(mon.group(2)),
                             as_of=as_of, printed=years or None)
    slash = _MDY.search(raw)
    if slash:
        a, b, y = slash.group(1), slash.group(2), slash.group(3)
        month, day = int(a), int(b)
        if month > 12:
            month, day = day, month
        if y:
            year = int(y)
            if year < 100:
                year += 2000
            return f"{year:04d}-{month:02d}-{day:02d}"
        return complete_year(month, day, as_of=as_of, printed=years or None)
    return None
