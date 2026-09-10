"""Every calendar night a desk card printed.

Founder 2026-09-10: one printed night + time = one row. Same title, same
place, different date or time = different happening. Two dates on one
Chronicle card are two nights. We do not store None to avoid choosing.

Named weekdays plus Continues through Month Day fill each matching
weekday from as_of through that end date, inclusive.

Printed 8:30 p.m. on that night is the show time. Reading it is not inventing.
A printed clock is that locale pack's clock (America/Chicago for Austin).
Naive T18:00:00 was read as UTC and printed 1:00 PM. That is a miss.
"""
from __future__ import annotations

import re
from datetime import date as _date
from datetime import datetime as _datetime
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

_PACK_TZ = ZoneInfo("America/Chicago")

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
    r"\b(Mondays|Tuesdays|Wednesdays|Thursdays|Fridays|Saturdays|Sundays)\b",
    re.I,
)
_RANGE_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(?:-|\u2013|to)\s*(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b",
    re.I,
)
_TIME_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b",
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
_NAMED = {
    "mondays": 0, "tuesdays": 1, "wednesdays": 2, "thursdays": 3,
    "fridays": 4, "saturdays": 5, "sundays": 6,
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


def _ampm_hour(h: str, m: Optional[str], ampm: str) -> Tuple[int, int]:
    hour = int(h)
    minute = int(m or 0)
    ap = ampm.lower().replace(".", "")
    if ap.startswith("a"):
        if hour == 12:
            hour = 0
    elif hour != 12:
        hour += 12
    return hour, minute


def _time_near(text: str, start: int, end: int):
    window = text[start:end]
    rng = _RANGE_RE.search(window)
    if rng:
        h1, m1, h2, m2, ap = rng.groups()
        return _ampm_hour(h1, m1, ap), _ampm_hour(h2, m2, ap)
    one = _TIME_RE.search(window)
    if one:
        return _ampm_hour(one.group(1), one.group(2), one.group(3)), None
    return None, None


def _iso(day: _date, clock) -> Tuple[str, str]:
    if not clock:
        return day.isoformat(), "date"
    hour, minute = clock
    local = _datetime(day.year, day.month, day.day, hour, minute, tzinfo=_PACK_TZ)
    return local.isoformat(), "datetime"


def house_dates(card_text: str, page_html: str,
                as_of: Optional[_date]) -> List[str]:
    """ISO calendar nights this card printed, in print order then run order."""
    return [row["date"] for row in house_occurrences(card_text, page_html, as_of)]


def house_occurrences(card_text: str, page_html: str,
                      as_of: Optional[_date]) -> List[Dict[str, object]]:
    """One row per printed night. Clock only if that night printed a time."""
    text = (card_text or "").strip()
    if not text:
        return []
    years = _years_in_date_context(text, page_html)
    if not years and as_of is not None:
        years = {as_of.year}
    if not years:
        years = {_date.today().year}
    hits = list(_HOUSE_WD_MD_RE.finditer(text))
    out: List[Dict[str, object]] = []
    seen = set()
    for i, hit in enumerate(hits):
        wd, mon, day_s = hit.groups()
        month = _HOUSE_MONTHS[mon.lower()]
        day = int(day_s)
        weekday = _HOUSE_WEEKDAYS[wd[:3].lower()]
        nxt = hits[i + 1].start() if i + 1 < len(hits) else min(len(text), hit.end() + 48)
        start_clock, end_clock = _time_near(text, hit.end(), nxt)
        for year in years:
            try:
                candidate = _date(year, month, day)
            except ValueError:
                continue
            if candidate.weekday() != weekday:
                continue
            when, prec = _iso(candidate, start_clock)
            if when in seen:
                continue
            seen.add(when)
            out.append({
                "date": candidate.isoformat(),
                "when": when,
                "when_precision": prec,
                "end_clock": end_clock,
            })
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
            token = raw.lower()
            if token in _NAMED:
                named.add(_NAMED[token])
        first_dated = hits[0].start() if hits else len(text)
        start_clock, end_clock = _time_near(text, 0, first_dated)
        if end is not None and named:
            cur = as_of if isinstance(as_of, _date) else as_of.date()
            while cur <= end:
                if cur.weekday() in named:
                    when, prec = _iso(cur, start_clock)
                    if when not in seen:
                        seen.add(when)
                        out.append({
                            "date": cur.isoformat(),
                            "when": when,
                            "when_precision": prec,
                            "end_clock": end_clock,
                        })
                cur = _date.fromordinal(cur.toordinal() + 1)
    out.sort(key=lambda row: str(row["when"]))
    return out
