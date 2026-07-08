"""Source priority scoring model.

Formula per ONE_LIVE_Reconciled_Master_Spec.md sec.14:
  priority_score = credibility_weight*0.40 + access_reliability*0.20
                 + coverage_uniqueness*0.15 + update_frequency_score*0.15
                 + verification_anchor_score*0.10
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/source_rank.py)
"""
from dataclasses import dataclass


@dataclass
class SourceMetrics:
    credibility_weight: float
    access_reliability: float
    coverage_uniqueness: float
    update_frequency_score: float
    verification_anchor_score: float


def compute_priority_score(m: SourceMetrics) -> float:
    return round((
        m.credibility_weight * 0.40 +
        m.access_reliability * 0.20 +
        m.coverage_uniqueness * 0.15 +
        m.update_frequency_score * 0.15 +
        m.verification_anchor_score * 0.10
    ) * 100, 2)
