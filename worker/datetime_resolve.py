"""Page-context resolution of partial date claims (Contract #44, founder
directive 2026-08-05 verbatim "Get the discovered events engine fixed and
working NOW" — decision record 2026-08-05_today-density-and-duplicates.md).

THE GAP THIS CLOSES: datetime_normalize (R-021) refuses to store any claim
whose own text lacks a full calendar date — correct fail-closed policy, but
venue calendar pages (the discovered lane's backbone) print "August 8" or
"Fri Aug 8 · 7:30 PM" with the YEAR carried by the page's context, not the
event's text. Every such event stored start_time NULL, published dateless,
and could never appear in any date window: 1,363 published discovered
events, zero upcoming (db-report 31026850025). The refused claims were
preserved verbatim in provenance (the R-021 reviewers required it), so they
are resolvable NOW without re-crawling and without AI spend.

THE RULE (deterministic, stated, refuses everything else): a claim that
EVIDENCES month+day (both probes agree on month and day) but not the year
resolves against the CONTEXT TIME — when the page was fetched/the candidate
was created. A live venue calendar listing "August 8" fetched on
2026-08-05 evidences 2026-08-08: the year is the unique one that places the
date inside [context - GRACE_PAST_DAYS, context + 365 days). That is
context evidence, not fabrication, and the resolution is recorded in
provenance with its rule and context so it is auditable forever.

REFUSED, still and always (never guessed):
  * time-only / weekday-only claims ("6pm", "Friday 8pm") — no month+day
    evidence anywhere in the claim;
  * claims whose stated weekday CONTRADICTS the resolved date ("Friday,
    Aug 8" when Aug 8 of the resolved year is a Saturday) — conflicting
    evidence is an ESCALATE-shaped fact, not a coin flip;
  * ambiguous numeric dates, unparseable strings, unrecognized timezone
    abbreviations — the R-021 refusals stand unchanged;
  * month+day with no unique in-window year (only possible with a degenerate
    window; fails closed).

Timezone posture: resolved values are NAIVE ISO strings, byte-compatible
with what normalize_datetime_claim stores for fully-evidenced claims — one
convention for the whole column. The systemic naive-local-vs-UTC question
is recorded as R-081 and fixed for BOTH paths together, never only here.

Deliberately in the same UN-BOUND shaping layer as datetime_normalize —
outside the certified extraction-exam surface (whose runner pipeline code
must never reference by name; membership was verified against its manifest
before this module was written), so no certification surface is touched.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from dateutil import parser as _duparser

# The same two-default probe trick as datetime_normalize: components the
# string doesn't supply get filled differently, so what the string EVIDENCES
# is read off agreement between the two parses. Both probe years are LEAP
# years (unlike normalize's) because this resolver must be able to parse a
# "Feb 29" claim to see its month/day — a non-leap default makes it raise
# before evidence can be read (caught by this module's own test).
_PROBE_A = datetime(2004, 1, 1)
_PROBE_B = datetime(2008, 2, 2)

# How far in the past (relative to context) a resolved date may fall and
# still count as "this occurrence": venue calendars keep the current week
# visible, so a claim fetched days after the show resolves to the just-past
# date instead of jumping a year ahead and asserting a false future event.
GRACE_PAST_DAYS = 7

_WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday",
             "saturday", "sunday")
_WEEKDAY_RE = re.compile(
    r"\b(mon|tue|tues|wed|weds|thu|thur|thurs|fri|sat|sun)[a-z]*\b", re.I)
_WEEKDAY_PREFIX = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def _claimed_weekday(raw: str) -> Optional[int]:
    """The weekday the claim itself asserts (0=Monday), or None."""
    m = _WEEKDAY_RE.search(raw)
    if not m:
        return None
    return _WEEKDAY_PREFIX[m.group(1)[:3].lower()]


def resolve_partial_date_claim(
    raw: Any, context: datetime,
) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """Resolve a month+day-evidenced (year-missing) claim against context.

    Returns (naive_iso | None, resolution_record | None). The record carries
    {raw, resolved, rule, context} for provenance. Anything not resolvable
    under the stated rule returns (None, None) — the caller leaves the
    existing refusal exactly as it was.
    """
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s:
        return None, None
    try:
        a = _duparser.parse(s, default=_PROBE_A)
        b = _duparser.parse(s, default=_PROBE_B)
    except (ValueError, OverflowError, TypeError):
        return None, None
    # Resolvable class: month AND day evidenced (agree), year NOT (differs —
    # each probe kept its own default year). Anything else is either fully
    # evidenced (normalize stored it already) or under-evidenced (stay NULL).
    if not (a.month == b.month and a.day == b.day and a.year != b.year):
        return None, None
    # Times must agree too (they do whenever the claim carries one — both
    # probes default midnight otherwise); disagreement means the time came
    # from the defaults in a way we cannot trust.
    if a.time() != b.time():
        return None, None

    # Window = exactly 365 days starting at the grace floor, so any month+day
    # occurs AT MOST once inside it — uniqueness by construction, no
    # tie-breaking. (First version used [ctx-grace, ctx+365), which contains
    # a just-past date TWICE — this year's and next year's — and the test
    # caught it refusing a show from three days ago.) Feb 29 can occur zero
    # times in a non-leap span; that refuses honestly below.
    lo = (context - timedelta(days=GRACE_PAST_DAYS)).date()
    hi = lo + timedelta(days=365)
    candidates = []
    for year in (context.year - 1, context.year, context.year + 1):
        try:
            d = date(year, a.month, a.day)
        except ValueError:  # Feb 29 in a non-leap candidate year
            continue
        if lo <= d < hi:
            candidates.append(d)
    if len(candidates) != 1:
        return None, None
    resolved_date = candidates[0]

    claimed_wd = _claimed_weekday(s)
    if claimed_wd is not None and resolved_date.weekday() != claimed_wd:
        # The claim's own weekday contradicts the resolved calendar date —
        # conflicting evidence, refuse rather than pick a side.
        return None, None

    resolved = datetime.combine(resolved_date, a.time())
    return resolved.isoformat(), {
        "raw": s,
        "resolved": resolved.isoformat(),
        "rule": f"year-from-context(grace_past_days={GRACE_PAST_DAYS})",
        "context": context.isoformat(),
    }


# ── Date-from-the-event's-own-text (the live gap the smoke run exposed) ──────
# Run 31045743483's refusals were ALL bare times — "8:00 pm", "19:30" — because
# venue calendars print the date once in the block ("AUG 8 · Spoon · 8:00 pm")
# and the extractor returned only the time. resolve_partial_date_claim
# correctly refuses those: a time alone evidences no date. But the date IS
# right there in the event's own text, so reading it from the block is
# EVIDENCE, not fabrication — the same standard as everything else here.
#
# The rule, deliberately strict: the block must evidence EXACTLY ONE distinct
# calendar date. Zero → refuse (nothing to read). Two or more → refuse
# (ambiguous: a block listing several dates cannot say which is this event's).

_MONTHS = ("january|february|march|april|may|june|july|august|september|"
           "october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|sep|"
           "oct|nov|dec")
_WD = r"(?:mon|tue|tues|wed|weds|thu|thur|thurs|fri|sat|sun)[a-z]*"
# "August 8", "Aug 8, 2026", "8 August", optionally led by the weekday the
# page itself prints ("Sat, Aug 8"). The weekday is CAPTURED because a page
# that names it is stating a checkable fact: if the resolved calendar date
# lands on a different weekday, our year is wrong and we refuse rather than
# publish a date the page's own text contradicts.
_TEXT_DATE_RE = re.compile(
    rf"\b(?:(?P<wd1>{_WD})\.?,?\s+)?(?:{_MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{4}})?\b"
    rf"|\b(?:(?P<wd2>{_WD})\.?,?\s+)?\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\.?(?:,?\s+\d{{4}})?\b",
    re.I)
# ISO dates, which need no month-name.
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# A time-only claim: parses, but evidences neither month nor day.
def _is_time_only(raw: str) -> bool:
    try:
        a = _duparser.parse(raw, default=_PROBE_A)
        b = _duparser.parse(raw, default=_PROBE_B)
    except (ValueError, OverflowError, TypeError):
        return False
    return a.month != b.month or a.day != b.day


def resolve_time_only_from_block(
    raw: Any, block_text: Optional[str], context: datetime,
) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """Give a bare-time claim the date its OWN block text states.

    Returns (naive_iso | None, resolution_record | None). Refuses unless the
    claim is time-only AND the block evidences exactly one distinct date.
    Numeric-ambiguous forms ("03/04/2026") are deliberately not read from
    text at all — datetime_normalize already refuses those as unknowable, and
    reading them here would smuggle the guess back in.
    """
    if raw is None or not block_text:
        return None, None
    s = str(raw).strip()
    if not s or not _is_time_only(s):
        return None, None

    found = []  # (date_text, claimed_weekday_or_None)
    for m in _TEXT_DATE_RE.finditer(block_text):
        wd = m.group("wd1") or m.group("wd2")
        found.append((m.group(0), _WEEKDAY_PREFIX[wd[:3].lower()] if wd else None))
    for m in _ISO_DATE_RE.finditer(block_text):
        found.append((m.group(0), None))
    if not found:
        return None, None

    # Normalize every hit to a concrete date; a hit without a year takes the
    # year from context under the SAME unique-365-day-window rule above. A hit
    # whose printed weekday contradicts the resolved date is DROPPED — the
    # page contradicts itself (or our year is wrong), and neither is something
    # to publish through.
    dates = set()
    for hit, claimed_wd in found:
        resolved_date = None
        iso, _ = resolve_partial_date_claim(hit, context)
        if iso:
            resolved_date = datetime.fromisoformat(iso).date()
        else:
            try:
                p_a = _duparser.parse(hit, default=_PROBE_A)
                p_b = _duparser.parse(hit, default=_PROBE_B)
            except (ValueError, OverflowError, TypeError):
                continue
            if p_a.date() == p_b.date():  # fully evidenced, year included
                resolved_date = p_a.date()
        if resolved_date is None:
            continue
        if claimed_wd is not None and resolved_date.weekday() != claimed_wd:
            continue
        dates.add(resolved_date)
    if len(dates) != 1:
        # 0 = nothing readable; >1 = the block names several dates and cannot
        # say which is this event's. Both refuse; the claim stays NULL.
        return None, None

    the_date = dates.pop()
    try:
        t = _duparser.parse(s, default=_PROBE_A).time()
    except (ValueError, OverflowError, TypeError):
        return None, None
    resolved = datetime.combine(the_date, t)
    return resolved.isoformat(), {
        "raw": s,
        "resolved": resolved.isoformat(),
        "rule": "date-from-event-block-text(exactly-one-date-evidenced)",
        "context": context.isoformat(),
    }
