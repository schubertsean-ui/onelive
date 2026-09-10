"""Every calendar night a desk card printed.

Founder 2026-09-10: one printed night + time = one row. Same title, same
place, different date or time = different happening. Two dates on one
Chronicle card are two nights. We do not store None to avoid choosing.

Named weekdays plus \"Continues through Month Day\" fill each matching
weekday from as_of through that end date, inclusive.
"""
from __future__ import annotations

import re
from datetime import date as _date
from typing import List, Optional

_HOUSE_WD_MD_RE = re.compile(
    r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?,?\s+"
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\.?\s+(\d{1,2})\b",
    re.I,
)
_HOUSE_THROUGH_RE = re.compile(
    r"Continues through\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
    r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sept?(?:ember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)\.?\s+(\d{1,2})",
    re.I,
)
_HOUSE_WD_ONLY_RE = re.compile(
    r"\b(Mondays|Tuesdays|Wednesdays|Thursdays|Fridays|Saturdays|Sundays|"
    r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|"
    r"Mon|Tue|Wed|Thu|Fri|Sat|Sun)s?\b",
    re.I,
)
_PAGE_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_HEADING_RE = re.compile(r"<h[1-3][^>]*>(.*?)</h[1-3]>", re.I | re.S)
_INNER_TAG_RE = re.compile(r"<[^>]+>")
_HOUSE_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_HOUSE_WEEKDAYS = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
}


def _years_in_date_context(card_text: str, page_html: str) -> set:
    years = {int(y) for y in _PAGE_YEAR_RE.findall(card_text or "")}
    if years:
        return years
    blobs = []
    html = page_html or ""
    for m in _TITLE_RE.finditer(html):
        blobs.append(_INNER_TAG_RE.sub(" ", m.group(1)))
    for m in _HEADING_RE.finditer(html):
        blobs.append(_INNER_TAG_RE.sub(" ", m.group(1)))
    return {int(y) for y in _PAGE_YEAR_RE.findall(" ".join(blobs))}


def house_dates(card_text: str, page_html: str,
                as_of: Optional[_date]) -> List[str]:
    """ISO calendar nights this card printed, in print order then run order."""
    text = (card_text or "").strip()
    if not text:
        return []
    years = _years_in_date_context(text, page_html)
    if not years and as_of is not None:
        years = {as_of.year}
    if not years:
        years = {_date.today().year}
    out: List[str] = []
    seen = set()
    for hit in _HOUSE_WD_MD_RE.finditer(text):
        wd, mon, day_s = hit.groups()
        month = _HOUSE_MONTHS[mon.lower()]
        day = int(day_s)
        weekday = _HOUSE_WEEKDAYS[wd[:3].lower()]
        for year in years:
            try:
                candidate = _date(year, month, day)
            except ValueError:
                continue
            if candidate.weekday() != weekday:
                continue
            iso = candidate.isoformat()
            if iso not in seen:
                seen.add(iso)
                out.append(iso)
    through = _HOUSE_THROUGH_RE.search(text)
    if through and as_of is not None:
        tmon, tday_s = through.groups()
        year = sorted(years)[-1]
        try:
            end = _date(year, _HOUSE_MONTHS[tmon.lower()], int(tday_s))
        except ValueError:
            end = None
        named = set()
        for raw in _HOUSE_WD_ONLY_RE.findall(text):
            token = raw[:3].lower()
            if token in _HOUSE_WEEKDAYS:
                named.add(_HOUSE_WEEKDAYS[token])
        if end is not None and named:
            cur = as_of
            if hasattr(cur, "date") and not isinstance(cur, _date):
                cur = cur.date()
            while cur <= end:
                if cur.weekday() in named:
                    iso = cur.isoformat()
                    if iso not in seen:
                        seen.add(iso)
                        out.append(iso)
                cur = _date.fromordinal(cur.toordinal() + 1)
    return out
