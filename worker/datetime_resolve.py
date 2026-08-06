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

# Forward horizon on a year-from-context resolution (evaluator #191 r3,
# attacker-smuggle lens). The 365-day window guarantees UNIQUENESS but not
# PLAUSIBILITY: with context 2026-08-05 a stale "July 4" listing has no
# in-window 2026 occurrence, so the window rolls it to 2027-07-04 and asserts
# a confident event eleven months out that the page almost certainly meant as
# last month. A no-year venue listing is a NEAR-TERM listing; past this
# horizon the roll is a guess, so we refuse instead of publishing a date the
# source never evidenced. Chosen so the legitimate wrap-around still works —
# a December page listing "January 5" resolves 16 days out, and a season
# announcement 7 months out still resolves — while the stale-listing roll
# (always ~330+ days out, by construction) always refuses.
MAX_FUTURE_DAYS = 300

# "3/4", "03/04", "3-4" — a numeric day pair with no month name. Which number
# is the month is a LOCALE convention, not something the source stated. An ISO
# date (2026-03-04) is excluded by requiring the pair not to be preceded by a
# 4-digit year, and it carries its own year so it never reaches this resolver
# as a year-less claim anyway.
_AMBIGUOUS_NUMERIC_RE = re.compile(r"(?<!\d)(?<!\d-)\d{1,2}\s*[/.\-]\s*\d{1,2}(?!\d)")

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
    # AMBIGUOUS NUMERIC FORMS ARE REFUSED, as this module's docstring has always
    # claimed and as worker/datetime_normalize already enforces
    # ('ambiguous-numeric-date'). Adversarial-review catch (2026-08-06): the
    # year-less numeric form slipped through here, so "03/04 8pm" resolved to
    # March 4 purely because dateutil defaults to a US reading — nothing in the
    # source says whether the venue meant March 4 or April 3, and the caller
    # then stores that guess as source evidence on a public card. A month NAME
    # (or an ISO form, which carries its own year and is handled elsewhere) is
    # what makes a numeric day unambiguous; without one, refuse.
    if _AMBIGUOUS_NUMERIC_RE.search(s):
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

    # Uniqueness is not plausibility: refuse a resolution that lands beyond the
    # near-term horizon, which is exactly the shape a STALE no-year listing
    # takes when the window rolls it into next year (see MAX_FUTURE_DAYS).
    if (resolved_date - context.date()).days > MAX_FUTURE_DAYS:
        return None, None

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


# RETIRED 2026-08-06: resolve_time_only_from_block.
#
# It read the date for a bare-time claim ("8:00 pm") out of the surrounding
# block's PROSE, on the rule "exactly one date in the block is this event's".
# Four adversarial-review rounds found five distinct ways that fabricates a
# public start time: a date inside a ticket URL's path slug; "tickets on sale
# August 8"; "page updated August 8"; and — the finding that ended it —
# "member presale August 8" or "box office opens August 8", i.e. any phrasing
# a blocklist has not met yet. The last review asked for a POSITIVE check that
# the date is the event's. Prose cannot supply one: that is inference, which
# is the thing R-021 exists to refuse.
#
# It was removed rather than extended because its value was MEASURED and it was
# zero — across seven smoke runs on this branch it resolved nothing, not once,
# while accumulating five fabrication paths. R-093's own trigger said to
# compare its realised yield against the callback's and retire it if the
# callback covered the same cases; that comparison has now run.
#
# The need it addressed is real and is served by EVIDENCE instead of prose:
# worker/date_callback.py fetches the event's own linked page and reads the
# date the source DECLARES in schema.org markup.
