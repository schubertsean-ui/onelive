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
candidate's extracted jsonb (under _provenance.undated_time_claims, wired
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


def normalize_datetime_claim(raw: Any) -> Tuple[Optional[str], Optional[str]]:
    """Return (normalized_iso | None, discarded_raw | None).

    - None/empty → (None, None): nothing claimed, nothing discarded.
    - Full-date-evidenced string → (ISO 8601, None).
    - Time-only / weekday-only / month-day-without-year / unparseable /
      ambiguous-numeric-date / unrecognized-timezone-abbreviation →
      (None, the raw string) so the caller can preserve the claim loudly.

    The timezone rule (PR #44 r1 nit): dateutil DROPS timezone
    abbreviations it cannot resolve ("7pm ET" parses as naive 19:00,
    which a timestamptz column would silently reinterpret — a subtly
    wrong fact). It emits UnknownTimezoneWarning when doing so; we treat
    that warning as a refusal — the claim asserted a timezone we cannot
    honor, so we store nothing rather than a shifted time.
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
            return None, s  # day/month order unknowable — refuse to guess
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            a = _duparser.parse(s, default=_PROBE_A)
            b = _duparser.parse(s, default=_PROBE_B)
        except (ValueError, OverflowError, TypeError):
            return None, s
    if any(issubclass(w.category, _UnknownTz) for w in caught):
        return None, s
    if a.date() != b.date():
        return None, s
    return a.isoformat(), None


def normalize_extracted_datetimes(shaped: Dict[str, Any]) -> Dict[str, str]:
    """Normalize start_time/end_time on a shaped extraction IN PLACE.

    Returns {field: discarded_raw} for every claim that could not be
    stored truthfully — the caller logs it loudly and preserves it in the
    candidate's provenance. An empty dict means nothing was discarded.
    """
    discarded: Dict[str, str] = {}
    for field in _DATETIME_FIELDS:
        normalized, raw = normalize_datetime_claim(shaped.get(field))
        shaped[field] = normalized
        if raw is not None:
            discarded[field] = raw
    return discarded


def preserve_discarded_claims(meta: Dict[str, Any],
                              discarded: Dict[str, str]) -> bool:
    """Attach discarded claims under meta['_provenance'].undated_time_claims.

    PR #44 r1 blocker: the previous inline version silently SKIPPED
    preservation when _provenance existed as a non-dict (setdefault
    returned the malformed value; the isinstance guard bailed) — breaking
    the central "NULL with raw preserved" contract exactly when provenance
    was already suspect. Now malformed provenance is REPLACED with a dict
    so the claims are always preserved, and the malformed original is kept
    verbatim under _provenance_malformed_original (shown, never hidden).

    Returns True when a malformed provenance was encountered, so the
    caller can log it at ERROR level with source context.
    """
    prov = meta.get("_provenance")
    malformed = prov is not None and not isinstance(prov, dict)
    if malformed:
        meta["_provenance_malformed_original"] = repr(prov)[:200]
    if not isinstance(prov, dict):
        prov = {}
    prov["undated_time_claims"] = dict(discarded)
    meta["_provenance"] = prov
    return malformed
