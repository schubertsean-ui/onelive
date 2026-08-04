"""Cross-source triangulation — assemble the corroboration that earns confidence.

This is the missing half of the earned-confidence model (founder 2026-07-31:
"confidence scoring based on our ability to TRIANGULATE an AI find against other
potential sources"). `worker/confidence.py::derive_confidence` already maps a set
of corroborating source classes to a 4-state confidence — but nothing *assembled*
that set. This module does: given one AI-extracted event (the target) and a POOL
of events drawn from OTHER, INDEPENDENT sources (licensed ticketing rows, other
first-party feeds, other candidates), it decides which pool events describe the
SAME real-world event and returns the distinct corroborating source classes.

Design invariants (this module NEVER publishes and NEVER fabricates):
  * PURE — no DB, no network, no side effects; every input is passed in, so the
    matching logic is exhaustively unit-testable (mirrors publish_policy.py).
  * POSITIVE corroboration only. Triangulation raises confidence via agreement;
    it does NOT infer `disputed`. `disputed` stays an explicit moderation state
    (two different shows in two rooms at one venue+time is normal, not a
    contradiction), so we never manufacture a dispute from a title mismatch.
  * A source corroborates ITSELF trivially, so a source is only counted once and
    the target's own source cannot inflate the count (dedupe by source identity).
  * Never fabricated: a missing venue/title/start makes an event unmatchable
    (it corroborates nothing) rather than matching loosely.

The output (a list of distinct source classes) is exactly what `derive_confidence`
and `worker.publish_policy.decide_publish` already consume — so triangulation
plugs in with no new confidence logic and no gate change.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from worker.confidence import derive_confidence

# Tokens too generic to carry venue/title identity — dropped before matching so
# "The Mohawk" and "Mohawk Austin" resolve to the same venue and two shows aren't
# fused just because both say "live at austin".
_STOPWORDS = frozenset({
    "the", "a", "an", "at", "in", "on", "of", "and", "&", "austin", "tx", "texas",
    "live", "presents", "presented", "by", "with", "feat", "featuring", "ft",
    "event", "show", "tickets", "concert", "night",
})

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokens(s: Optional[str]) -> frozenset[str]:
    # Only a real string carries tokens. A non-string (an int/bool from an
    # unparsed raw JSON field) is not lowered/tokenized — it simply matches
    # nothing, never raises.
    if not isinstance(s, str) or not s:
        return frozenset()
    return frozenset(
        t for t in _WORD_RE.findall(s.lower())
        if t not in _STOPWORDS and len(t) > 1
    )


def _norm_venue(s: Optional[str]) -> frozenset[str]:
    """Venue identity as a significant-token set (order/punctuation/stopword
    independent)."""
    return _tokens(s)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def _to_naive_utc(dt: _dt.datetime) -> _dt.datetime:
    """Reduce a datetime to a tz-naive UTC-comparable instant. A tz-AWARE value is
    first CONVERTED to UTC, then its tzinfo dropped — never stripped in place,
    which would silently reinterpret a local wall-clock time as UTC and shift the
    real instant (e.g. 20:00-05:00 must become 01:00 UTC, not stay 20:00). A naive
    value is treated as already-UTC (the codebase's normalized form)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(_dt.timezone.utc)
    return dt.replace(tzinfo=None)


def _parse_dt(value: Any) -> Optional[_dt.datetime]:
    """Parse an ISO string (tolerating a trailing 'Z', an explicit offset, or a
    bare date) or accept a datetime/date as-is. Returns a tz-naive UTC-comparable
    datetime (offsets converted to UTC first — see _to_naive_utc), or None when
    unparseable — an event with no usable start is simply unmatchable, never
    matched by guesswork."""
    if value is None:
        return None
    if isinstance(value, _dt.datetime):
        return _to_naive_utc(value)
    if isinstance(value, _dt.date):
        return _dt.datetime(value.year, value.month, value.day)
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    iso = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        return _to_naive_utc(_dt.datetime.fromisoformat(iso))
    except ValueError:
        try:
            return _dt.datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _minutes_apart(a: Optional[_dt.datetime], b: Optional[_dt.datetime]) -> Optional[float]:
    if a is None or b is None:
        return None
    return abs((a - b).total_seconds()) / 60.0


# Matching thresholds. Deliberately conservative: two records must plausibly be
# the SAME show (same venue, same start slot, overlapping title) before one is
# counted as corroboration for the other. Tunable, documented, single source.
VENUE_JACCARD_MIN = 0.5      # venue name token overlap
TITLE_JACCARD_MIN = 0.34     # title token overlap
START_TOLERANCE_MIN = 90     # a listing and a ticketing row rarely share the exact minute


def same_event(a: dict, b: dict, *, start_tolerance_min: int = START_TOLERANCE_MIN,
               venue_jaccard_min: float = VENUE_JACCARD_MIN,
               title_jaccard_min: float = TITLE_JACCARD_MIN) -> bool:
    """True when two event records plausibly describe the SAME real-world event:
    same venue (token overlap), start within tolerance, and overlapping title.
    An event missing venue, title, or a parseable start is unmatchable (returns
    False) — never matched on partial data."""
    av, bv = _norm_venue(a.get("venue_name")), _norm_venue(b.get("venue_name"))
    if _jaccard(av, bv) < venue_jaccard_min:
        return False
    delta = _minutes_apart(_parse_dt(a.get("start_time")), _parse_dt(b.get("start_time")))
    if delta is None or delta > start_tolerance_min:
        return False
    at, bt = _tokens(a.get("title")), _tokens(b.get("title"))
    return _jaccard(at, bt) >= title_jaccard_min


def _source_identity(event: dict) -> Optional[str]:
    """A stable per-source identity so one source cannot corroborate itself
    twice. Prefer an explicit source id, then the provider/source name."""
    for key in ("source_id", "source_provider", "source_name", "source"):
        v = event.get(key)
        if v:
            return str(v)
    return None


def _source_class(event: dict) -> Optional[str]:
    """The class used by the confidence model (anchor vs non-anchor)."""
    for key in ("source_class", "source_provider", "source"):
        v = event.get(key)
        if v:
            return str(v)
    return None


@dataclass(frozen=True)
class Corroboration:
    """The corroboration a target event earned from an independent pool.

    `source_classes` is the distinct set (target's own + each independent
    corroborator's), ready to hand to derive_confidence. `matches` is how many
    distinct OTHER sources agreed — the audit trail for why confidence moved.
    """
    source_classes: tuple[str, ...]
    matches: int


def corroborate(target: dict, pool: Iterable[dict]) -> Corroboration:
    """Return the distinct corroborating source classes for `target` from `pool`.

    A pool event counts only if (a) it is the SAME event (same_event) and (b) it
    comes from a DIFFERENT source than the target and than every already-counted
    corroborator — so N ticketing rows for one show from one provider count once,
    and the target never corroborates itself. The target's own source class is
    always included (it is one real source), so the result fed to
    derive_confidence reflects "the target plus everyone who independently agrees."
    """
    target_identity = _source_identity(target)
    classes: list[str] = []
    seen_sources: set[str] = set()

    tc = _source_class(target)
    if tc:
        classes.append(tc)
    if target_identity:
        seen_sources.add(target_identity)

    matches = 0
    for other in pool:
        oid = _source_identity(other)
        if oid is None or oid in seen_sources:
            continue  # same source as target or an already-counted corroborator
        if not same_event(target, other):
            continue
        seen_sources.add(oid)
        matches += 1
        oc = _source_class(other)
        if oc:
            classes.append(oc)

    # Distinct, order-stable.
    distinct: list[str] = []
    for c in classes:
        if c not in distinct:
            distinct.append(c)
    return Corroboration(source_classes=tuple(distinct), matches=matches)


def triangulated_confidence(target: dict, pool: Iterable[dict], *,
                            sxsw_mode: bool = False) -> str:
    """The 4-state confidence `target` earns after triangulation against `pool`.

    Assembles the corroborating source classes (this module's job) and hands them
    to the EXISTING derive_confidence (no new confidence logic): an anchor among
    the corroborators → 'confirmed'; enough independent agreement → 'confirmed'
    (founder ruling 2026-08-04: the corroborated tier earns the anchor's label);
    a single uncorroborated source → 'unverified'. Never returns 'disputed' —
    triangulation only corroborates; disputes are an explicit moderation state.
    """
    corr = corroborate(target, pool)
    return derive_confidence(list(corr.source_classes), sxsw_mode=sxsw_mode)
