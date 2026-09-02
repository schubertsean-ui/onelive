"""R-030 — a listing's time may borrow a date the SAME PAGE states.

Run 33579093995 stored 92 of its 198 candidates (46%) with `start_time`
NULL, every one refused `no-full-date-evidence`: the extractor was handed
a bare clock ('9:00PM', '6:00PM', '10 am', '19:00:00') because that is all
the listing line said. A NULL can never satisfy /tonight's
`start_time >= <from>` predicate, so those rows publish and are then
invisible forever.

The fix is NOT to guess a day. It is to read the day the page already
published: venue calendars overwhelmingly carry the date in markup
(<time datetime>, JSON-LD startDate, ICS DTSTART) or in a heading a few
characters from the clock ("Sat Sep 6 • 9:00PM"), and the extractor was
simply never shown it.

The rules below are the honesty guards, and they are the whole design:
  * evidence must come from THIS page's text — the resolver is pure and
    holds no cross-page state, so a date from another URL cannot attach;
  * the event's OWN block wins over the page ("nearby"); a page carrying
    several distinct dates and a block carrying none is REFUSED, because
    which listing owns which date is exactly what we cannot know;
  * a page date that CONTRADICTS the claim (different month/day, or a
    weekday the claim names) is refused, never overwritten;
  * a year absent from the page is supplied ONLY when the page's own
    weekday pins exactly one year inside a window anchored to the fetch
    time; with no anchor (`as_of=None`) weekday pinning is OFF. There is
    no "today", no "this year", no next-occurrence guess anywhere.
Anything not resolved stays exactly as R-021 left it: NULL, raw + reason
preserved, candidate still routed to ops.

WHY THIS IS ITS OWN MODULE, and not more of worker/datetime_normalize.py:
keeping the new rule in its own file means R-021's normalizer — the
narrowest, most-depended-on piece of the date contract — stays
byte-identical, so a defect found here can be reverted by unwiring one
import rather than by unpicking a merged function.

WIRED as of PR #211 (founder-authorized): worker/ai_extract.py calls
normalize_extracted_datetimes_with_page() on the live extract path,
offering each listing block as the "same page" scope first and the whole
fetched page second. That import puts this file inside the ARMED CRON's
computed runtime closure (tools/arming_runtime.runtime_files()), which is
why PR #211 carries a fresh smoke run re-binding
docs/evidence/ARMING_SMOKE_RUN.json — exactly as this docstring predicted
while the engine was still parked.

The R-021 primitives below are IMPORTED rather than re-implemented, on
purpose: the date rule and its two probe dates must have exactly one
definition, or the two copies drift and the refusals stop agreeing.
"""
from __future__ import annotations

import json
import re
import warnings
from datetime import date as _date, datetime, time as _time, timedelta
from typing import Any, Dict, NamedTuple, Optional, Tuple

from worker.datetime_normalize import (
    _DATETIME_FIELDS,
    _PROBE_A,
    _PROBE_B,
    _duparser,
    normalize_datetime_claim,
)

# Probes for TIME-of-day evidence. Distinct from _PROBE_A/_PROBE_B, whose
# midnight defaults are load-bearing for the date rule ("a full date with
# no clock is midnight"): detecting whether the STRING carried a clock
# needs defaults whose times differ, or every dateless string would look
# like it evidenced 00:00.
_TPROBE_A = datetime(2001, 1, 1, 3, 4, 5)
_TPROBE_B = datetime(2002, 2, 2, 6, 7, 8)

# How far around the page's fetch time a weekday-pinned date may land. A
# calendar page still lists the last few days; it does not list last year.
_PIN_BACK_DAYS = 7
_PIN_FORWARD_DAYS = 365

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_WEEKDAYS = {
    "mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2,
    "weds": 2, "wednesday": 2, "thu": 3, "thur": 3, "thurs": 3,
    "thursday": 3, "fri": 4, "friday": 4, "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}
_MONTH_ALT = "|".join(sorted(_MONTHS, key=len, reverse=True))
_WEEKDAY_ALT = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))
_ORD = r"(?:st|nd|rd|th)?"

# Machine-readable same-page date carriers, highest trust first.
_JSONLD_RE = re.compile(
    r"<script[^>]*type\s*=\s*[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL)
_TIME_TAG_RE = re.compile(
    r"<time\b[^>]*\bdatetime\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_ICS_DTSTART_RE = re.compile(
    r"^DTSTART[^:\r\n]*:[ \t]*([0-9TZ:+\-]+)[ \t]*$", re.IGNORECASE | re.MULTILINE)

# Visible-text dates. WITH a year = a complete date on its own. WITHOUT a
# year = month+day that only a page-stated weekday may complete.
_VISIBLE_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_VISIBLE_MDY_RE = re.compile(
    rf"\b({_MONTH_ALT})\.?\s+(\d{{1,2}}){_ORD},?\s+(\d{{4}})\b", re.IGNORECASE)
_VISIBLE_DMY_RE = re.compile(
    rf"\b(\d{{1,2}}){_ORD}\s+({_MONTH_ALT})\.?,?\s+(\d{{4}})\b", re.IGNORECASE)
_VISIBLE_WD_MD_RE = re.compile(
    rf"\b({_WEEKDAY_ALT})\.?,?\s+({_MONTH_ALT})\.?\s+(\d{{1,2}}){_ORD}\b"
    rf"(?!\s*,?\s*\d{{4}})", re.IGNORECASE)
_VISIBLE_WD_DM_RE = re.compile(
    rf"\b({_WEEKDAY_ALT})\.?,?\s+(\d{{1,2}}){_ORD}\s+({_MONTH_ALT})\.?\b"
    rf"(?!\s*,?\s*\d{{4}})", re.IGNORECASE)

_CLAIM_WEEKDAY_RE = re.compile(rf"\b({_WEEKDAY_ALT})\b", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


class SamePageDate(NamedTuple):
    """One date this page states, and where on the page it was stated."""
    date: _date
    kind: str   # jsonld | time-tag | ics | visible-date | visible-weekday
    raw: str


def _visible_text(text: str) -> str:
    """Tag-stripped page text. Script/style bodies go first so a JSON-LD
    payload's own ISO dates are not double-counted as visible prose."""
    return _TAG_RE.sub(" ", _SCRIPT_STYLE_RE.sub(" ", text))


def _date_of_full_claim(raw: str) -> Optional[_date]:
    """The calendar date of a string that evidences one on its own, else
    None. Reuses the R-021 rule verbatim — nothing is admitted here that
    the existing gate would refuse."""
    iso, _refusal = normalize_datetime_claim(raw)
    if iso is None:
        return None
    try:
        return datetime.fromisoformat(iso).date()
    except ValueError:  # pragma: no cover — isoformat round-trips
        return None


def _pin_year_by_weekday(month: int, day: int, weekday: int,
                         as_of: Optional[_date]) -> Optional[_date]:
    """The one date in the fetch-anchored window with this month/day AND
    this weekday. None when there is no anchor, no match, or more than
    one — the page has then not actually said which day it means."""
    if as_of is None:
        return None
    start = as_of - timedelta(days=_PIN_BACK_DAYS)
    end = as_of + timedelta(days=_PIN_FORWARD_DAYS)
    hits = []
    for year in range(start.year, end.year + 1):
        try:
            cand = _date(year, month, day)
        except ValueError:      # Feb 29 in a common year
            continue
        if start <= cand <= end and cand.weekday() == weekday:
            hits.append(cand)
    return hits[0] if len(hits) == 1 else None


def _jsonld_start_dates(text: str) -> list:
    """startDate values from every JSON-LD block on the page. Malformed
    JSON is SKIPPED, never fatal — a broken analytics blob must not cost
    the page its real dates."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key.lower() in ("startdate", "start_date") and isinstance(
                        value, (str, int, float)):
                    found.append(str(value))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for blob in _JSONLD_RE.findall(text):
        try:
            walk(json.loads(blob))
        except (ValueError, TypeError):
            continue
    return found


def same_page_dates(text: Optional[str],
                    *, as_of: Optional[_date] = None) -> list:
    """Every distinct date THIS text states, highest-trust carrier first.

    Order is machine-readable (JSON-LD, <time datetime>, ICS DTSTART)
    before visible prose, and full dates before weekday-pinned ones, so
    the ``kind`` reported for a date is the strongest carrier that stated
    it. Duplicates collapse: a page whose markup and prose agree states
    ONE date, not two, and must not read as ambiguous.
    """
    if not text or not text.strip():
        return []
    out = []
    seen = set()

    def add(value: Optional[_date], kind: str, raw: str) -> None:
        if value is not None and value not in seen:
            seen.add(value)
            out.append(SamePageDate(value, kind, raw))

    for raw in _jsonld_start_dates(text):
        add(_date_of_full_claim(raw), "jsonld", raw)
    for raw in _TIME_TAG_RE.findall(text):
        add(_date_of_full_claim(raw), "time-tag", raw)
    for raw in _ICS_DTSTART_RE.findall(text):
        add(_date_of_full_claim(raw), "ics", raw)

    visible = _visible_text(text)
    for y, m, d in _VISIBLE_ISO_RE.findall(visible):
        try:
            add(_date(int(y), int(m), int(d)), "visible-date", f"{y}-{m}-{d}")
        except ValueError:
            continue
    for mon, day, year in _VISIBLE_MDY_RE.findall(visible):
        try:
            add(_date(int(year), _MONTHS[mon.lower()], int(day)),
                "visible-date", f"{mon} {day}, {year}")
        except ValueError:
            continue
    for day, mon, year in _VISIBLE_DMY_RE.findall(visible):
        try:
            add(_date(int(year), _MONTHS[mon.lower()], int(day)),
                "visible-date", f"{day} {mon} {year}")
        except ValueError:
            continue
    for wd, mon, day in _VISIBLE_WD_MD_RE.findall(visible):
        add(_pin_year_by_weekday(_MONTHS[mon.lower()], int(day),
                                 _WEEKDAYS[wd.lower()], as_of),
            "visible-weekday", f"{wd} {mon} {day}")
    for wd, day, mon in _VISIBLE_WD_DM_RE.findall(visible):
        add(_pin_year_by_weekday(_MONTHS[mon.lower()], int(day),
                                 _WEEKDAYS[wd.lower()], as_of),
            "visible-weekday", f"{wd} {day} {mon}")
    return out


# Refusals a same-page date may lift. `ambiguous-numeric-date` and
# `unrecognized-timezone-abbreviation` are NOT here on purpose: those two
# refuse the claim's OWN date/timezone, and no amount of page evidence
# makes "03/04/2026" stop meaning two different days.
_RESCUABLE_REASONS = frozenset({"no-full-date-evidence", "unparseable"})

# Fallback clock reader for claims dateutil cannot parse at all
# ("Sat Sep 6 • 9:00PM"). EXACTLY ONE clock must appear: a string holding
# two ("Doors 7pm, show 8pm") does not tell us which one it is claiming,
# and picking either would be a guess.
_CLOCK_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?\s*([ap])\.?m\.?\b"
    r"|\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b",
    re.IGNORECASE)


def _claim_clock(s: str):
    """The time-of-day the CLAIM ITSELF states, or None.

    Primary reader is the same two-probe trick the date rule uses, keyed
    on the HOUR: dateutil fills every field the string omitted from the
    default, so "9:00PM" comes back with the default's seconds and "10 am"
    with the default's minutes. Agreement on the hour is therefore what
    proves the string carried a clock; minutes and seconds that disagree
    were never stated and read 0 — the same midnight convention R-021
    already applies to a dateless full date.
    """
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        try:
            a = _duparser.parse(s, default=_TPROBE_A)
            b = _duparser.parse(s, default=_TPROBE_B)
        except (ValueError, OverflowError, TypeError):
            a = b = None
    if a is not None and b is not None and a.hour == b.hour:
        tz = a.tzinfo if a.utcoffset() == b.utcoffset() else None
        return _time(a.hour,
                     a.minute if a.minute == b.minute else 0,
                     a.second if a.second == b.second else 0,
                     tzinfo=tz)
    matches = _CLOCK_RE.findall(s)
    if len(matches) != 1:
        return None
    h12, m12, s12, mer, h24, m24, s24 = matches[0]
    if mer:
        hour = int(h12) % 12 + (12 if mer.lower() == "p" else 0)
        return _time(hour, int(m12 or 0), int(s12 or 0))
    return _time(int(h24), int(m24), int(s24 or 0))


def _claim_month_day(s: str):
    """The (month, day) the claim itself states, or None — read off the
    R-021 probes, so it is the same evidence standard as everywhere else."""
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        try:
            a = _duparser.parse(s, default=_PROBE_A)
            b = _duparser.parse(s, default=_PROBE_B)
        except (ValueError, OverflowError, TypeError):
            return None
    if a.month == b.month and a.day == b.day:
        return a.month, a.day
    return None


def _claim_weekday(s: str) -> Optional[int]:
    found = {_WEEKDAYS[w.lower()] for w in _CLAIM_WEEKDAY_RE.findall(s)}
    return found.pop() if len(found) == 1 else None


def resolve_same_page_datetime(
    raw: Any,
    *,
    page_text: Optional[str] = None,
    block_text: Optional[str] = None,
    as_of: Optional[_date] = None,
) -> Tuple[Optional[str], Optional[Dict[str, str]], Optional[Dict[str, str]]]:
    """R-021's rule, plus R-030: a refused clock may borrow the date THIS
    PAGE states.

    Returns (iso | None, refusal | None, evidence | None). ``evidence``
    is present only when a same-page date completed the claim, and names
    the scope, carrier and exact string it came from so ops can audit the
    stored date back to the page that published it.

    ``block_text`` is the event's own listing block and is consulted
    FIRST — that is what "nearby" means on a calendar page listing thirty
    shows. ``page_text`` is the fallback for a single-event page. Both are
    plain arguments: this function keeps no state between calls, so a date
    from a different URL has no path in.
    """
    iso, refusal = normalize_datetime_claim(raw)
    if iso is not None or refusal is None:
        return iso, refusal, None
    if refusal["reason"] not in _RESCUABLE_REASONS:
        return None, refusal, None
    if not (page_text or block_text):
        return None, refusal, None

    claim = refusal["raw"]
    clock = _claim_clock(claim)
    if clock is None:
        # No time in the claim either — a page date alone would invent
        # the whole timestamp. This is where "2026", "7" and "TBD" stop.
        return None, refusal, None

    claim_md = _claim_month_day(claim)
    claim_wd = _claim_weekday(claim)

    def _consistent(cand: _date) -> bool:
        if claim_md is not None and (cand.month, cand.day) != claim_md:
            return False
        if claim_wd is not None and cand.weekday() != claim_wd:
            return False
        return True

    for scope, text in (("block", block_text), ("page", page_text)):
        candidates = same_page_dates(text, as_of=as_of)
        if not candidates:
            continue
        usable = [c for c in candidates if _consistent(c.date)]
        if not usable:
            # This scope states dates and every one of them disagrees with
            # what the claim itself says. Reaching past it to a wider scope
            # would be shopping for a date, so stop here.
            return None, {"raw": claim,
                          "reason": "same-page-date-contradicts-claim"}, None
        if len({c.date for c in usable}) > 1:
            return None, {"raw": claim,
                          "reason": "ambiguous-same-page-dates"}, None
        hit = usable[0]
        return (datetime.combine(hit.date, clock).isoformat(), None,
                {"date": hit.date.isoformat(), "kind": hit.kind,
                 "scope": scope, "raw": hit.raw, "claim": claim})

    # The page says nothing about a day. R-021's answer stands: NULL.
    return None, refusal, None


def normalize_extracted_datetimes_with_page(
    shaped: Dict[str, Any],
    *,
    page_text: Optional[str] = None,
    block_text: Optional[str] = None,
    as_of: Optional[_date] = None,
    resolutions: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Dict[str, str]]:
    """The page-aware sibling of datetime_normalize.normalize_extracted_datetimes.

    Same signature and same return value — {field: {raw, reason}} for every
    claim that could not be stored truthfully — so the wiring PR swaps one
    call and nothing downstream changes shape. With all-None page arguments
    every result is byte-identical to R-021's, which is what the
    backward-compatibility test pins. ``resolutions`` is an optional dict
    the caller supplies to receive {field: evidence} for each date a page
    completed, for provenance.
    """
    refused: Dict[str, Dict[str, str]] = {}
    for field in _DATETIME_FIELDS:
        normalized, refusal, evidence = resolve_same_page_datetime(
            shaped.get(field), page_text=page_text, block_text=block_text,
            as_of=as_of)
        shaped[field] = normalized
        if refusal is not None:
            refused[field] = refusal
        if evidence is not None and resolutions is not None:
            resolutions[field] = evidence
    return refused
