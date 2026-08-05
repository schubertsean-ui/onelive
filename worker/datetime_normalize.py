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


def resolve_yearless_claim(
    raw: Any,
    reference: Optional[datetime] = None,
) -> Tuple[Optional[str], Optional[Dict[str, str]]]:
    """LAST-RESORT year resolution for a claim that is a full date except the
    year ("August 9", "Sat Aug 9 7pm"). Founder-ratified 2026-08-05 ("Yes on
    the year rule"), explicitly SUBORDINATE to callback evidence: callers try
    worker/date_callback.py first and reach here only when the source offered
    no machine-readable date to read back.

    Rule (a calendar reader's, made deterministic and auditable): resolve to
    the year that places the date within [-30, +300) days of ``reference``
    (default: now). That window is narrower than a year, so at most one
    candidate year fits — no tie to guess. Outside the window (a year-less
    date >10 months out) we still refuse.

    Returns (iso, note) on resolution — note is the provenance record
    {"raw", "resolved", "reference"} — else (None, None). Claims that are
    NOT merely year-less (time-only, unparseable, ambiguous-numeric) return
    (None, None): this function widens nothing else.
    """
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s:
        return None, None
    m = _NUMERIC_DATE.match(s)
    if m:
        first, second = int(m.group(1)), int(m.group(2))
        if first <= 12 and second <= 12 and first != second:
            return None, None  # ambiguous day/month order stays refused
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            a = _duparser.parse(s, default=_PROBE_A)
            b = _duparser.parse(s, default=_PROBE_B)
        except (ValueError, OverflowError, TypeError):
            return None, None
    if any(issubclass(w.category, _UnknownTz) for w in caught):
        return None, None
    if a.date() == b.date():
        return None, None  # fully dated — the strict path already stored it
    if (a.month, a.day, a.timetz()) != (b.month, b.day, b.timetz()):
        return None, None  # more than the year is unevidenced — stays refused
    ref = reference or datetime.now()
    resolved = None
    for year in (ref.year - 1, ref.year, ref.year + 1):
        try:
            cand = a.replace(year=year)
        except ValueError:  # Feb 29 in a non-leap candidate year
            continue
        delta = (cand.date() - ref.date()).days
        if -30 <= delta < 300:
            resolved = cand
            break
    if resolved is None:
        return None, None
    note = {"raw": s, "resolved": "year-from-fetch-date",
            "reference": ref.date().isoformat()}
    return resolved.isoformat(), note


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
