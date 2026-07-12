"""Extraction-accuracy scorer for offline eval of the AI provider.

`score_extraction`/`aggregate` compute the metric that governs trust for
a truth-first pipeline: the HALLUCINATION RATE — how often the model asserts a
field value that is NOT in the ground truth. This is the direct measure behind
item #41's "Definition of Done: false positives" KPI. A missed field (recall
miss) costs an ops person a little time; a hallucinated venue/time/artist that
slips into a candidate can corrupt entity resolution downstream and erode user
trust. So we count wrong values as BOTH a false positive and a false negative,
and report false positives explicitly.

Comparison is FIELD-KIND aware (see `FieldKind` / `DEFAULT_FIELD_KINDS`). A plain
`strip().lower()` compare would flag a correctly extracted `"8pm"` vs `"20:00"`
as a hallucination — poisoning the KPI that governs trust. Instead each
field is normalized according to its kind:

- TEXT      -> case/whitespace-insensitive string compare (lists as sets).
- TIME      -> canonical 24h "HH:MM" ("8pm" == "20:00" == "8:00 PM").
- DATE      -> canonical (year, month, day); missing year compares month-day.
- VENUE     -> lenient canonicalization (drop leading "the", trailing state).
- LIST_TEXT -> element-wise with PARTIAL CREDIT (3-of-4 lineup == 3 tp + 1 fn).

Normalizers are pure stdlib and deterministic. When a TIME/DATE value cannot be
parsed we DO NOT crash and DO NOT silently treat it as equal: we fall back to a
text compare and record the raw value in `ExtractionScore.unparsed_values` so a
corpus author can see exactly which spellings the normalizer is blind to.

Provenance/meta keys (prefixed with "_") are ignored.

KNOWN LIMITS (named, not hidden):
- VENUE matching is deliberately shallow canonicalization. True venue aliasing
  ("Emo's" == "Emo's East", "ACL Live at the Moody Theater" == "Moody Theater")
  requires an entity/alias table and is OUT OF SCOPE here. This normalizer will
  still mark genuine aliases as mismatches.
- TIME/DATE parsers cover the common US event spellings enumerated in the tests;
  locale-specific or free-text ("next Friday", "doors at 8, show at 9") forms are
  not parsed and fall back to text compare (and are recorded as unparsed).
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class FieldKind(Enum):
    """How a field's values are compared. Default is TEXT."""
    TEXT = auto()
    TIME = auto()
    DATE = auto()
    VENUE = auto()
    LIST_TEXT = auto()


# OneLive extraction fields -> comparison kind. Extend as the schema grows;
# anything not listed is treated as TEXT.
DEFAULT_FIELD_KINDS: Dict[str, FieldKind] = {
    "start_time": FieldKind.TIME,
    "end_time": FieldKind.TIME,
    "doors_time": FieldKind.TIME,
    "date": FieldKind.DATE,
    "event_date": FieldKind.DATE,
    "venue": FieldKind.VENUE,
    "venue_name": FieldKind.VENUE,
    "location": FieldKind.VENUE,
    "city": FieldKind.VENUE,
    "artists": FieldKind.LIST_TEXT,
    "artist_names": FieldKind.LIST_TEXT,
    "lineup": FieldKind.LIST_TEXT,
    "tags": FieldKind.LIST_TEXT,
}


# --- primitive normalizers ---------------------------------------------------
def _norm_text(v) -> Optional[str]:
    """Case/whitespace-insensitive scalar text form; None if empty/None."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip().lower()
        return s or None
    return str(v).strip().lower() or None


_TIME_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?$|^(\d{1,2}):(\d{2})$|^(\d{1,2})$")


def _parse_time(raw) -> Optional[str]:
    """Parse a common event-time spelling to canonical 24h "HH:MM", else None.

    Handles "8pm", "8 pm", "8:00 PM", "8:00pm", "7:30pm", "20:00", bare hour "8"
    (interpreted as 24h), plus "noon"/"midnight". A bare hour or "HH:MM" without
    am/pm is read as 24h. Anything else (free text, out-of-range) -> None, and
    the caller records it as unparsed and falls back to text compare.
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    if not s:
        return None
    if s in ("noon", "12 noon", "12noon"):
        return "12:00"
    if s in ("midnight", "12 midnight", "12midnight"):
        return "00:00"
    m = _TIME_RE.match(s)
    if not m:
        return None
    if m.group(3):  # 12h with am/pm
        hh = int(m.group(1))
        mm = int(m.group(2) or 0)
        ap = m.group(3)
        if not 1 <= hh <= 12:
            return None
        if ap == "a":
            hh = 0 if hh == 12 else hh
        else:  # "p"
            hh = 12 if hh == 12 else hh + 12
    elif m.group(4) is not None:  # HH:MM 24h
        hh, mm = int(m.group(4)), int(m.group(5))
    else:  # bare hour, 24h
        hh, mm = int(m.group(6)), 0
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return f"{hh:02d}:{mm:02d}"


_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}


def _parse_date(raw) -> Optional[Tuple[Optional[int], int, int]]:
    """Parse ISO/US date spellings to (year|None, month, day), else None.

    Handles "2026-03-14", "3/14/2026", "3/14", "March 14, 2026", "Mar 14".
    A 2-digit year is read as 20xx. When no year is present, year is None and
    comparison is month-day only.
    """
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    if not s:
        return None

    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m:
        return _valid_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    m = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", s)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        y = m.group(3)
        year = None
        if y is not None:
            year = int(y)
            if year < 100:
                year += 2000
        return _valid_date(year, mo, d)

    m = re.match(r"^([a-z]+)\.?\s+(\d{1,2})(?:,?\s+(\d{4}))?$", s)
    if m and m.group(1) in _MONTHS:
        mo = _MONTHS[m.group(1)]
        d = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else None
        return _valid_date(year, mo, d)

    return None


def _valid_date(year, month, day):
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return (year, month, day)


def _norm_venue(raw) -> Optional[str]:
    """Lenient venue canonicalization: casefold, drop a leading "the ", drop a
    trailing state/country after the last comma ("Austin, TX" -> "austin"),
    collapse punctuation/whitespace. See module KNOWN LIMITS: real aliasing needs
    an entity table; this will NOT unify "Emo's" and "Emo's East"."""
    if not isinstance(raw, str):
        return _norm_text(raw)
    s = raw.strip().casefold()
    if not s:
        return None
    s = re.sub(r",[^,]*$", "", s)          # drop trailing ", TX" / ", USA"
    if s.startswith("the "):
        s = s[4:]
    s = re.sub(r"[^\w\s]", " ", s)         # punctuation -> space
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def _list_set(v) -> set:
    """Normalized element set for a list-valued field."""
    if v is None:
        return set()
    if isinstance(v, (list, tuple, set, frozenset)):
        items = v
    else:
        items = [v]
    out = set()
    for x in items:
        n = _norm_text(x)
        if n is not None:
            out.add(n)
    return out


def _present(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, tuple, set, frozenset)):
        return any(_present(x) for x in v)
    return True


def _scalar_equal(pv, ev, kind: FieldKind, field_name: str,
                  unparsed: List[Tuple[str, str]]) -> bool:
    """Compare two present scalar values under `kind`. Records unparsed TIME/DATE
    raws (and falls back to text compare) rather than crashing or lying."""
    if kind is FieldKind.TIME:
        pn, en = _parse_time(pv), _parse_time(ev)
        if pn is None and isinstance(pv, str):
            unparsed.append((field_name, pv))
        if en is None and isinstance(ev, str):
            unparsed.append((field_name, ev))
        if pn is not None and en is not None:
            return pn == en
        return _norm_text(pv) == _norm_text(ev)  # fall back
    if kind is FieldKind.DATE:
        pd, ed = _parse_date(pv), _parse_date(ev)
        if pd is None and isinstance(pv, str):
            unparsed.append((field_name, pv))
        if ed is None and isinstance(ev, str):
            unparsed.append((field_name, ev))
        if pd is not None and ed is not None:
            if pd[0] is None or ed[0] is None:
                return pd[1:] == ed[1:]     # compare month-day
            return pd == ed
        return _norm_text(pv) == _norm_text(ev)  # fall back
    if kind is FieldKind.VENUE:
        return _norm_venue(pv) == _norm_venue(ev)
    # TEXT (default): list-valued TEXT compared as a set for back-compat.
    if isinstance(pv, (list, tuple)) or isinstance(ev, (list, tuple)):
        return _list_set(pv) == _list_set(ev)
    return _norm_text(pv) == _norm_text(ev)


@dataclass
class ExtractionScore:
    """Per-example score. Counts are over comparable (non-meta) fields; for
    LIST_TEXT fields the counts are over list ELEMENTS (partial credit)."""
    true_positives: int = 0     # asserted & matches ground truth
    false_positives: int = 0    # asserted a value ground truth says is absent/differs
    false_negatives: int = 0    # ground truth has a value the model missed
    true_negatives: int = 0     # both absent
    mismatched_fields: List[str] = field(default_factory=list)
    hallucinated_fields: List[str] = field(default_factory=list)
    # (field, raw value) a TIME/DATE normalizer could not parse and fell back on.
    unparsed_values: List[Tuple[str, str]] = field(default_factory=list)
    # per-field outcome, distinct labels so the debug map is not lossy:
    #   "tp"       matched
    #   "fp"       asserted a value ground truth says is ABSENT (pure hallucination)
    #   "fn"       missed a value ground truth HAS
    #   "tn"       both absent
    #   "mismatch" both present but different (counts as BOTH fp and fn)
    #   "partial"  list field with a mix of matched/extra/missing elements
    by_field: Dict[str, str] = field(default_factory=dict)

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 1.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def hallucination_rate(self) -> float:
        """Fraction of asserted fields/elements that were hallucinated (the trust
        KPI). Lower is better; 0.0 is the target for a truth-first extractor."""
        asserted = self.true_positives + self.false_positives
        return self.false_positives / asserted if asserted else 0.0

    @property
    def accuracy(self) -> float:
        """0..1 scalar: share of comparable outcomes that were correct
        (tp+tn over all). Replaces the retired `evaluate_extraction` for callers
        that need a single scalar. 1.0 when there is nothing to compare."""
        total = (self.true_positives + self.false_positives +
                 self.false_negatives + self.true_negatives)
        return (self.true_positives + self.true_negatives) / total if total else 1.0


def _score_list(s: ExtractionScore, k: str, pv, ev) -> None:
    """Element-wise partial-credit scoring for a LIST_TEXT field."""
    p_set, e_set = _list_set(pv), _list_set(ev)
    if not p_set and not e_set:
        s.true_negatives += 1
        s.by_field[k] = "tn"
        return
    tp = len(p_set & e_set)
    fp = len(p_set - e_set)
    fn = len(e_set - p_set)
    s.true_positives += tp
    s.false_positives += fp
    s.false_negatives += fn
    if fp:
        s.hallucinated_fields.append(k)
    if fp or fn:
        s.mismatched_fields.append(k)
    if fp and not tp and not fn:
        s.by_field[k] = "fp"
    elif fn and not tp and not fp:
        s.by_field[k] = "fn"
    elif tp and not fp and not fn:
        s.by_field[k] = "tp"
    else:
        s.by_field[k] = "partial"


def score_extraction(predicted: Optional[dict], expected: dict,
                     ignore_meta: bool = True,
                     field_kinds: Optional[Dict[str, FieldKind]] = None
                     ) -> ExtractionScore:
    """Score one prediction against ground truth with precision/recall/F1 and,
    critically, the hallucination rate. `predicted` may be None (total miss).

    `field_kinds` maps field name -> FieldKind for semantic comparison; unlisted
    fields default to TEXT. Passing None uses DEFAULT_FIELD_KINDS.
    """
    predicted = predicted or {}
    if field_kinds is None:
        field_kinds = DEFAULT_FIELD_KINDS
    keys = set(expected) | set(predicted)
    if ignore_meta:
        keys = {k for k in keys if not k.startswith("_")}

    s = ExtractionScore()
    for k in sorted(keys):
        kind = field_kinds.get(k, FieldKind.TEXT)
        pv, ev = predicted.get(k), expected.get(k)

        if kind is FieldKind.LIST_TEXT:
            _score_list(s, k, pv, ev)
            continue

        p_has, e_has = _present(pv), _present(ev)
        if not p_has and not e_has:
            s.true_negatives += 1
            s.by_field[k] = "tn"
        elif p_has and not e_has:
            s.false_positives += 1
            s.hallucinated_fields.append(k)
            s.by_field[k] = "fp"
        elif not p_has and e_has:
            s.false_negatives += 1
            s.by_field[k] = "fn"
        else:  # both present
            if _scalar_equal(pv, ev, kind, k, s.unparsed_values):
                s.true_positives += 1
                s.by_field[k] = "tp"
            else:
                # A wrong value is both a miss on the truth and a false assertion,
                # so it increments BOTH counters. It is labeled "mismatch" (not
                # plain "fp") so the per-field map preserves that both signals
                # fired — a pure "fp" means truth was ABSENT, which is different.
                s.false_positives += 1
                s.false_negatives += 1
                s.mismatched_fields.append(k)
                s.hallucinated_fields.append(k)
                s.by_field[k] = "mismatch"
    return s


def _micro(scores: List[ExtractionScore]) -> Tuple[float, float]:
    """Micro-averaged (f1, hallucination_rate) over a list of per-example scores."""
    tp = sum(s.true_positives for s in scores)
    fp = sum(s.false_positives for s in scores)
    fn = sum(s.false_negatives for s in scores)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    asserted = tp + fp
    hall = fp / asserted if asserted else 0.0
    return f1, hall


def _percentile(sorted_vals: List[float], pct: float) -> float:
    """Linear-interpolated percentile of an already-sorted list (pct in [0,100])."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = rank - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def aggregate(scores: List[ExtractionScore], seed: int = 12345,
              n_boot: int = 1000) -> Dict[str, object]:
    """Corpus-level metrics (micro-averaged) with bootstrap 95% CIs.

    CIs use stdlib `random` seeded with `seed` (default 12345) so results are
    fully reproducible/deterministic — a world-class eval is not flaky. With
    fewer than 2 examples a CI is undefined, so we return the point estimate as
    [x, x] rather than crash.
    """
    n = len(scores)
    tp = sum(s.true_positives for s in scores)
    fp = sum(s.false_positives for s in scores)
    fn = sum(s.false_negatives for s in scores)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    asserted = tp + fp
    hall = fp / asserted if asserted else 0.0
    n_unparsed = sum(len(s.unparsed_values) for s in scores)

    if n < 2:
        f1_ci = [round(f1, 4), round(f1, 4)]
        hall_ci = [round(hall, 4), round(hall, 4)]
    else:
        rng = random.Random(seed)
        boot_f1: List[float] = []
        boot_hall: List[float] = []
        for _ in range(n_boot):
            sample = [scores[rng.randrange(n)] for _ in range(n)]
            bf1, bh = _micro(sample)
            boot_f1.append(bf1)
            boot_hall.append(bh)
        boot_f1.sort()
        boot_hall.sort()
        f1_ci = [round(_percentile(boot_f1, 2.5), 4),
                 round(_percentile(boot_f1, 97.5), 4)]
        hall_ci = [round(_percentile(boot_hall, 2.5), 4),
                   round(_percentile(boot_hall, 97.5), 4)]

    return {
        "n_examples": n,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "hallucination_rate": round(hall, 4),
        "f1_ci95": f1_ci,
        "hallucination_rate_ci95": hall_ci,
        "n_unparsed": n_unparsed,
    }
