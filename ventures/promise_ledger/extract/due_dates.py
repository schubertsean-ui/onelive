"""Due-date parser v0 — deterministic extraction of claim deadlines (H9).

Turns promise language into (due_date, original_text) pairs per the schema
invariant that a parsed due_date must keep its non-empty original phrasing.
Deterministic stdlib code only — no LLM, no spend (Contract #8 scope). The
parser is deliberately CONSERVATIVE: it returns the LATEST day the phrase can
mean (a promise "by Q3 2027" is not broken until Q3 2027 has fully passed),
and it returns None rather than guess when the phrase is ambiguous. Precision
over recall: a wrong due date feeds a wrong "overdue" alert, which is the
product's failure mode; an unparsed phrase merely stays due_date_text-only,
which the schema fully supports.

KNOWN LIMIT (stated, not hidden): "fiscal" periods are resolved as CALENDAR
periods — mapping fiscal quarters/years to dates requires the issuer's
fiscal-calendar record, which is entity data this parser does not have. Such
phrases return fiscal=True so callers can defer resolution until the entity's
fiscal calendar is known.
"""

from __future__ import annotations

import calendar
import datetime
import re
from dataclasses import dataclass

_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_abbr) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_name) if m})

_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
_HALF_END = {1: (6, 30), 2: (12, 31)}

_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "1st": 1, "2nd": 2,
             "3rd": 3, "4th": 4}


@dataclass(frozen=True)
class ParsedDueDate:
    due_date: datetime.date      # latest day the phrase can mean
    original_text: str           # verbatim phrase (provenance of the parse)
    fiscal: bool                 # True => calendar-resolved placeholder; needs
                                 # the issuer's fiscal calendar to be exact


def _end_of_month(year: int, month: int) -> datetime.date:
    return datetime.date(year, month, calendar.monthrange(year, month)[1])


def parse_due_dates(text: str) -> list[ParsedDueDate]:
    """Find deadline phrases in re-expressed claim text. Conservative: only
    unambiguous, year-anchored forms parse; everything else is left to
    due_date_text-only records."""
    out = []
    seen_spans = []

    def claim_span(m) -> bool:
        span = m.span()
        for s in seen_spans:
            if span[0] < s[1] and s[0] < span[1]:
                return False
        seen_spans.append(span)
        return True

    # Q3 2027 / Q3 FY2027 / third quarter of (fiscal) 2027 / H1 2028
    for m in re.finditer(
            r"\b(?:(?P<qword>first|second|third|fourth|1st|2nd|3rd|4th)\s+quarter\s+of\s+"
            r"(?P<fiscal1>fiscal\s+)?(?:year\s+)?(?P<year1>20\d{2})"
            r"|Q(?P<qnum>[1-4])\s*(?P<fiscal2>FY)?\s*(?P<year2>20\d{2})"
            r"|H(?P<hnum>[12])\s*(?P<fiscal3>FY)?\s*(?P<year3>20\d{2}))\b",
            text, re.IGNORECASE):
        if not claim_span(m):
            continue
        fiscal = bool(m.group("fiscal1") or m.group("fiscal2") or m.group("fiscal3"))
        if m.group("hnum"):
            month, day = _HALF_END[int(m.group("hnum"))]
            year = int(m.group("year3"))
        else:
            q = (int(m.group("qnum")) if m.group("qnum")
                 else _ORDINALS[m.group("qword").lower()])
            month, day = _QUARTER_END[q]
            year = int(m.group("year1") or m.group("year2"))
        out.append(ParsedDueDate(datetime.date(year, month, day), m.group(0), fiscal))

    # "by/before/no later than <Month> <D>?, <YYYY>"  and  "in <Month> <YYYY>"
    for m in re.finditer(
            r"\b(?:by|before|no later than|in|during)\s+"
            r"(?P<mon>January|February|March|April|May|June|July|August|September|"
            r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"\.?\s+(?:(?P<day>\d{1,2}),?\s+)?(?P<year>20\d{2})\b",
            text, re.IGNORECASE):
        if not claim_span(m):
            continue
        month = _MONTHS[m.group("mon").lower()]
        year = int(m.group("year"))
        day = int(m.group("day")) if m.group("day") else None
        due = datetime.date(year, month, day) if day else _end_of_month(year, month)
        out.append(ParsedDueDate(due, m.group(0), False))

    # "by (the end of) <YYYY>" / "by year-end <YYYY>"
    for m in re.finditer(
            r"\b(?:by\s+(?:the\s+)?end\s+of|by\s+year-end|before\s+the\s+end\s+of)\s+"
            r"(?P<fiscal>fiscal\s+)?(?:year\s+)?(?P<year>20\d{2})\b",
            text, re.IGNORECASE):
        if not claim_span(m):
            continue
        out.append(ParsedDueDate(datetime.date(int(m.group("year")), 12, 31),
                                 m.group(0), bool(m.group("fiscal"))))

    out.sort(key=lambda p: p.due_date)
    return out
