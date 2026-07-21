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
certified extraction-exam harness (ai/golden_exam.py HARNESS_MANIFEST),
so this boundary lives in the un-bound shaping layer instead — same
enforcement point (every candidate insert flows through it), zero
certification surface touched.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from dateutil import parser as _duparser

# Distinct defaults: any component the string does not itself supply gets
# filled differently in the two parses, so unevidenced dates are detected
# by disagreement rather than by format guessing.
_PROBE_A = datetime(2001, 1, 1)
_PROBE_B = datetime(2002, 2, 2)

_DATETIME_FIELDS = ("start_time", "end_time")


def normalize_datetime_claim(raw: Any) -> Tuple[Optional[str], Optional[str]]:
    """Return (normalized_iso | None, discarded_raw | None).

    - None/empty → (None, None): nothing claimed, nothing discarded.
    - Full-date-evidenced string → (ISO 8601, None).
    - Time-only / weekday-only / month-day-without-year / unparseable →
      (None, the raw string) so the caller can preserve the claim loudly.
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
