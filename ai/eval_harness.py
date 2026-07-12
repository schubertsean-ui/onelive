"""Extraction-accuracy scorer for offline eval of the AI provider.

Original `evaluate_extraction` (exact-match ratio) is retained for backward
compatibility. The richer `score_extraction` adds the metric that actually
governs trust for a truth-first pipeline: the HALLUCINATION RATE — how often the
model asserts a field value that is NOT in the ground truth. This is the direct
measure behind item #41's "Definition of Done: false positives" KPI.

Rationale: a missed field (recall miss) costs an ops person a little time; a
hallucinated venue/time/artist that slips into a candidate can corrupt entity
resolution downstream and erode user trust. So we weight and report false
positives explicitly, not just overall accuracy.

Fields are compared after light normalization (case, surrounding whitespace) so
"The Mohawk" vs "the mohawk " is not counted as an error. Provenance/meta keys
(prefixed with "_") are ignored. Times are NOT semantically normalized here — the
prompt forbids the model from reformatting times, so a differing time string is a
genuine discrepancy worth surfacing.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def _norm(v):
    """Normalize a scalar for comparison; lists compared as normalized sets."""
    if v is None:
        return None
    if isinstance(v, str):
        s = v.strip().lower()
        return s or None
    if isinstance(v, (list, tuple)):
        return frozenset(_norm(x) for x in v if _norm(x) is not None)
    return v


def _present(v) -> bool:
    return _norm(v) not in (None, frozenset())


# --- backward-compatible exact-match scorer (unchanged behavior) -------------
def evaluate_extraction(predicted: dict, expected: dict) -> float:
    if not expected:
        return 0.0
    score = 0
    total = len(expected)
    for k, v in expected.items():
        if predicted.get(k) == v:
            score += 1
    return score / max(1, total)


@dataclass
class ExtractionScore:
    """Per-example score. Counts are over comparable (non-meta) fields."""
    true_positives: int = 0     # asserted & matches ground truth
    false_positives: int = 0    # asserted a value ground truth says is absent/differs
    false_negatives: int = 0    # ground truth has a value the model missed
    true_negatives: int = 0     # both absent
    mismatched_fields: List[str] = field(default_factory=list)
    hallucinated_fields: List[str] = field(default_factory=list)

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
        """Fraction of asserted fields that were hallucinated (the trust KPI).
        Lower is better; 0.0 is the target for a truth-first extractor."""
        asserted = self.true_positives + self.false_positives
        return self.false_positives / asserted if asserted else 0.0


def score_extraction(predicted: Optional[dict], expected: dict,
                     ignore_meta: bool = True) -> ExtractionScore:
    """Score one prediction against ground truth with precision/recall/F1 and,
    critically, the hallucination rate. `predicted` may be None (total miss)."""
    predicted = predicted or {}
    keys = set(expected) | set(predicted)
    if ignore_meta:
        keys = {k for k in keys if not k.startswith("_")}

    s = ExtractionScore()
    for k in sorted(keys):
        pv, ev = predicted.get(k), expected.get(k)
        p_has, e_has = _present(pv), _present(ev)
        if not p_has and not e_has:
            s.true_negatives += 1
        elif p_has and not e_has:
            s.false_positives += 1
            s.hallucinated_fields.append(k)   # asserted something not in ground truth
        elif not p_has and e_has:
            s.false_negatives += 1
        else:  # both present
            if _norm(pv) == _norm(ev):
                s.true_positives += 1
            else:
                # A wrong value is both a miss on the truth and a false assertion.
                s.false_positives += 1
                s.false_negatives += 1
                s.mismatched_fields.append(k)
                s.hallucinated_fields.append(k)
    return s


def aggregate(scores: List[ExtractionScore]) -> Dict[str, float]:
    """Corpus-level metrics across many examples (micro-averaged)."""
    tp = sum(s.true_positives for s in scores)
    fp = sum(s.false_positives for s in scores)
    fn = sum(s.false_negatives for s in scores)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    asserted = tp + fp
    return {
        "n_examples": len(scores),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "hallucination_rate": round(fp / asserted, 4) if asserted else 0.0,
    }
