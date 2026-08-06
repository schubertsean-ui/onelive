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
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

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

# Evidence that the source stated a TIME OF DAY at all. Midnight is the
# documented default when a full date is evidenced and no time is (see the
# module docstring), so a midnight result needs no evidence — but any OTHER
# clock time must be traceable to something the source actually wrote.
_TIME_EVIDENCE = re.compile(
    r"(\d\s*:\s*\d)"          # 7:30
    r"|(\d\s*[ap]\.?m\.?)"    # 8pm / 8 p.m.
    r"|(\bnoon\b)|(\bmidnight\b)"
    r"|(\d{4}-\d{2}-\d{2}[T ]\d)",  # ISO date-time
    re.I,
)


def _year_is_stated(source: str, year: int) -> bool:
    """True when the parsed year literally appears in the source string.

    The two-probe trick above detects components the string OMITS (dateutil
    fills them from the differing defaults, so the probes disagree). It cannot
    detect components dateutil MISASSIGNS: on a date range like
    "Sept 4-27, 2026" the tokenizer takes the range's end day as the year and
    the stated year as a clock time, deterministically — so both probes agree
    and the omission guard passes a fact the source never asserted.

    Requiring the 4-digit year to appear verbatim closes that hole for the
    whole misassignment class, not just for ranges: a year we print must be a
    year the page wrote.

    Deliberate, stated tradeoff: a two-digit year ("Sept 4, 26") no longer
    stores. It is REFUSED, not lost — the raw claim is preserved under
    _provenance.unstored_datetime_claims and the candidate still reaches ops
    review, which is this module's designed fallback. Matching the two-digit
    form instead would re-open the very bug this closes, because a range's end
    day ("...4-27...") is itself a two-digit number that would satisfy it.
    """
    return re.search(rf"(?<!\d){year}(?!\d)", source) is not None


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
      "unrecognized-timezone-abbreviation", "no-full-date-evidence",
      "year-not-stated-in-source", "time-not-stated-in-source".

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
    # The date agreed across probes, so nothing was OMITTED. Two further
    # assertions catch what the probes structurally cannot see — components
    # dateutil MISASSIGNED from tokens that meant something else.
    if not _year_is_stated(s, a.year):
        return _refuse("year-not-stated-in-source")
    if (a.hour, a.minute, a.second) != (0, 0, 0) and not _TIME_EVIDENCE.search(s):
        return _refuse("time-not-stated-in-source")
    return a.isoformat(), None


def normalize_extracted_datetimes(
    shaped: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Normalize start_time/end_time on a shaped extraction IN PLACE.

    Returns {field: {raw, reason}} for every claim that could not be
    stored truthfully — the caller logs it loudly and preserves it in the
    candidate's provenance. An empty dict means nothing was discarded.
    """
    refused: Dict[str, Dict[str, str]] = {}
    for field in _DATETIME_FIELDS:
        normalized, refusal = normalize_datetime_claim(shaped.get(field))
        shaped[field] = normalized
        if refusal is not None:
            refused[field] = refusal
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
