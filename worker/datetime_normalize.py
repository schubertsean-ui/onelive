"""Datetime normalization at the extraction→store boundary (R-021, PR #43).

The live arming runs proved ~a third of sampled sources publish bare time
strings ("6pm", "06:00 PM", "8:00 a.m.") that the extractor passed through
to a timestamptz column, failing the source's whole insert — a fetchable
event LOST to a formatting detail.

The trust rule this module enforces: a timestamp is STORED only when the
extracted string evidences a full calendar date. We never fabricate one —
guessing "today"/"this year" for a time-only or month-day-only claim would
assert an unverified fact, the exact thing the pipeline exists to prevent.
Instead the structured column gets NULL, the raw claim is preserved in the
candidate's extracted jsonb (under _provenance.unstored_datetime_claims, wired
in worker/ai_extract.py), and the candidate row still reaches ops review:
no false fact asserted, no event lost.

Date-evidence detection uses the two-default parse trick: parse the string
twice with different default dates — if the results' calendar dates
differ, the string itself carried no complete date (dateutil filled the
gaps from the defaults) and we refuse to guess. Time-of-day defaults to
midnight when a full date IS evidenced but a time is not — the standard
calendar convention; the page text stays verbatim in raw_text for review.

Deliberately OUTSIDE worker/ai_models.py: that model is bound into the
certified extraction-exam harness manifest (see the exam runner module
under ai/ — its name is not written here because trust_gate rightly
forbids pipeline code from referencing the exam channel at all), so this
boundary lives in the un-bound shaping layer instead — same enforcement
point (every candidate insert flows through it), zero certification
surface touched.
"""
from __future__ import annotations

import json
import re
import warnings
from datetime import date as _date, datetime, time as _time, timedelta
from typing import Any, Dict, NamedTuple, Optional, Tuple

from dateutil import parser as _duparser

try:  # dateutil >= 2.7 names the warning; older versions lack it
    from dateutil.parser import UnknownTimezoneWarning as _UnknownTz
except ImportError:  # pragma: no cover — pinned deps include it
    class _UnknownTz(Warning):
        pass

# Distinct defaults: any component the string does not itself supply gets
# filled differently in the two parses, so unevidenced dates are detected
# by disagreement rather than by format guessing.
_PROBE_A = datetime(2001, 1, 1)
_PROBE_B = datetime(2002, 2, 2)

_DATETIME_FIELDS = ("start_time", "end_time")

# Pure-numeric day/month/year (or month/day/year) forms: when BOTH leading
# fields could be a month, the order is a locale guess — "03/04/2026" is
# March 4 in Austin and April 3 in London. We refuse to guess (PR #44 r1
# nit: dateutil silently applies the US assumption). Year-first ISO forms
# don't match (first field is 4 digits).
_NUMERIC_DATE = re.compile(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")


def normalize_datetime_claim(
    raw: Any,
) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """Return (normalized_iso | None, refusal | None) where refusal is
    {"raw": <original string>, "reason": <machine-readable code>}.

    - None/empty → (None, None): nothing claimed, nothing refused.
    - Full-date-evidenced string → (ISO 8601, None).
    - Anything we refuse to store carries its reason (r2 nit — a
      timezone-refused claim is dated but tz-unusable, not "undated"):
      "unparseable", "ambiguous-numeric-date",
      "unrecognized-timezone-abbreviation", "no-full-date-evidence".

    The timezone rule (r1 nit): dateutil DROPS timezone abbreviations it
    cannot resolve ("7pm ET" parses as naive 19:00, which a timestamptz
    column would silently reinterpret — a subtly wrong fact). It emits
    UnknownTimezoneWarning when doing so; that warning is a refusal —
    the claim asserted a timezone we cannot honor, so we store nothing
    rather than a shifted time.
    """
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s:
        return None, None

    def _refuse(reason: str) -> Tuple[None, Dict[str, str]]:
        return None, {"raw": s, "reason": reason}

    m = _NUMERIC_DATE.match(s)
    if m:
        first, second = int(m.group(1)), int(m.group(2))
        if first <= 12 and second <= 12 and first != second:
            # day/month order unknowable — refuse to guess
            return _refuse("ambiguous-numeric-date")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            a = _duparser.parse(s, default=_PROBE_A)
            b = _duparser.parse(s, default=_PROBE_B)
        except (ValueError, OverflowError, TypeError):
            return _refuse("unparseable")
    if any(issubclass(w.category, _UnknownTz) for w in caught):
        return _refuse("unrecognized-timezone-abbreviation")
    if a.date() != b.date():
        return _refuse("no-full-date-evidence")
    return a.isoformat(), None


def normalize_extracted_datetimes(
    shaped: Dict[str, Any],
    *,
    page_text: Optional[str] = None,
    block_text: Optional[str] = None,
    as_of: Optional[_date] = None,
    resolutions: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Dict[str, str]]:
    """Normalize start_time/end_time on a shaped extraction IN PLACE.

    Returns {field: {raw, reason}} for every claim that could not be
    stored truthfully — the caller logs it loudly and preserves it in the
    candidate's provenance. An empty dict means nothing was discarded.

    R-030, purely additive: pass the page/block text the claim came from
    and a refused clock may borrow a date THAT SAME PAGE states. With the
    defaults (all None) every result is byte-identical to R-021's, which
    is why the existing callers need no change to keep their behavior.
    ``resolutions`` is an optional dict the caller supplies to receive
    {field: evidence} for each date so completed, for provenance.
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


def preserve_discarded_claims(meta: Dict[str, Any],
                              refused: Dict[str, Dict[str, str]]) -> bool:
    """Attach refused claims under meta['_provenance'].unstored_datetime_claims.

    r1 blocker: the previous inline version silently SKIPPED preservation
    when _provenance existed as a non-dict — breaking the central "NULL
    with raw preserved" contract exactly when provenance was already
    suspect. Malformed provenance is REPLACED with a dict so the claims
    are always preserved, and the malformed original is kept IN FULL
    under _provenance_malformed_original (r2 blocker: no truncation —
    truncating the preserved value is itself data loss; the value is
    stored as-is when JSON-serializable, else as its complete repr).

    Existing unstored_datetime_claims entries are MERGED, not overwritten
    (r2 nit) — new refusals win per field, other fields survive.

    Returns True when a malformed provenance was encountered, so the
    caller can log it at ERROR level with source context.
    """
    prov = meta.get("_provenance")
    malformed = prov is not None and not isinstance(prov, dict)
    if malformed:
        try:
            json.dumps(prov)
            meta["_provenance_malformed_original"] = prov
        except (TypeError, ValueError):
            meta["_provenance_malformed_original"] = repr(prov)
    if not isinstance(prov, dict):
        prov = {}
    existing = prov.get("unstored_datetime_claims")
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(refused)
    prov["unstored_datetime_claims"] = merged
    meta["_provenance"] = prov
    return malformed


# ---------------------------------------------------------------------------
# R-030 — SAME-PAGE date resolution (founder ticket 2026-09-02)
#
# Run 33579093995 stored 92 of 198 candidates (46%) with start_time NULL,
# every one refused `no-full-date-evidence`: the extractor returned a bare
# clock ('9:00PM', '6:00PM', '10 am', '19:00:00') because that is all the
# LISTING LINE said. A NULL start_time can never satisfy /tonight's
# `start_time >= <from>` predicate, so those rows publish and are then
# invisible forever.
#
# The fix is NOT to guess a day. It is to read the day the page already
# published: venue calendars overwhelmingly carry the date in markup
# (<time datetime>, JSON-LD startDate, ICS DTSTART) or in a heading a few
# characters from the clock ("Sat Sep 6 • 9:00PM"), and the extractor was
# simply never shown it.
#
# The rules below are the honesty guards, and they are the whole design:
#   * evidence must come from THIS page's text — the function is pure and
#     holds no cross-page state, so a date from another URL cannot attach;
#   * the event's OWN block wins over the page ("nearby"); a page carrying
#     several distinct dates and a block carrying none is REFUSED, because
#     which listing owns which date is exactly what we cannot know;
#   * a page date that CONTRADICTS the claim (different month/day, or a
#     weekday the claim names) is refused, never overwritten;
#   * a year absent from the page is supplied ONLY when the page's own
#     weekday pins exactly one year inside a window anchored to the fetch
#     time; with no anchor (`as_of=None`) weekday pinning is OFF. There is
#     no "today", no "this year", no next-occurrence guess anywhere.
# Anything not resolved stays exactly as R-021 left it: NULL, raw + reason
# preserved, candidate still routed to ops.
# ---------------------------------------------------------------------------

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
