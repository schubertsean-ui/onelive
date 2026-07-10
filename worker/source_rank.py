"""Mechanism 2 — Source Priority Ranking Model.

Formula (per ONE_LIVE_Reconciled_Master_Spec.md sec.14):
  priority_score = credibility_weight*0.40 + access_reliability*0.20
                 + coverage_uniqueness*0.15 + update_frequency_score*0.15
                 + verification_anchor_score*0.10

The five coefficients are data-driven and *versioned* (``worker.trust_config`` /
migration 0008): every score records which formula version produced it, so a
coefficient change can be audited and rolled back.

Scale consistency (known risk area): the five sub-scores can arrive on either
the 0.0-1.0 unit scale (as stored in the source catalog) or a 0-100 scale. All
sub-scores are normalized to a common 0-100 scale *before* combining, and the
coefficients sum to 1.0, so ``priority_score`` is always on 0-100 regardless of
input scale. Mixed/out-of-range inputs fail loud rather than silently skewing.

Bands on the resulting 0-100 score (data-driven):
  P0 "Anchor truth"   85-100
  P1 "High trust"     70-84
  P2 "Corroboration"  50-69
  P3 "Weak signal"    <50

Source: extended from the Entertainment-App-Code-v1-4 reference build.
"""
from dataclasses import dataclass, asdict

from worker import trust_config

_SUBSCORES = (
    "credibility_weight",
    "access_reliability",
    "coverage_uniqueness",
    "update_frequency_score",
    "verification_anchor_score",
)


@dataclass
class SourceMetrics:
    credibility_weight: float
    access_reliability: float
    coverage_uniqueness: float
    update_frequency_score: float
    verification_anchor_score: float


@dataclass
class PriorityResult:
    score: float          # 0-100
    band: str             # P0..P3
    label: str            # human-readable band label
    formula_version: str  # which coefficient set produced `score` (for audit)


def _to_percent(value: float, scale: str, field: str) -> float:
    """Normalize a single sub-score to the 0-100 scale and validate its range."""
    if scale == "unit":
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{field}={value!r} out of range for scale='unit' (expected 0.0-1.0)"
            )
        return value * 100.0
    if scale == "percent":
        if not 0.0 <= value <= 100.0:
            raise ValueError(
                f"{field}={value!r} out of range for scale='percent' (expected 0-100)"
            )
        return value
    raise ValueError(f"unknown scale {scale!r} (expected 'unit' or 'percent')")


def compute_priority_score(
    m: SourceMetrics,
    scale: str = "unit",
    formula_version: str | None = None,
    config: dict | None = None,
) -> float:
    """Weighted priority score on 0-100.

    ``scale`` declares the input sub-score scale ('unit' = 0.0-1.0, the catalog
    default; 'percent' = 0-100). Coefficients come from the (versioned) config.
    """
    _, coeffs = trust_config.priority_formula(formula_version, config)
    total = 0.0
    for field in _SUBSCORES:
        pct = _to_percent(getattr(m, field), scale, field)
        total += pct * coeffs[field]
    return round(total, 2)


def priority_band(score: float, config: dict | None = None) -> tuple[str, str]:
    """Return (band, label) for a 0-100 score using the configured bands."""
    for row in trust_config.priority_bands(config):
        if score >= row["min_score"]:
            return row["band"], row["label"]
    raise ValueError(
        f"no priority band matched score {score!r}; "
        "trust_config.priority_bands needs a min_score<=0 band"
    )


def rank_source(
    m: SourceMetrics,
    scale: str = "unit",
    formula_version: str | None = None,
    config: dict | None = None,
) -> PriorityResult:
    """Score a source and classify it into a priority band, recording the
    formula version used so the result is auditable/rollback-able."""
    version, _ = trust_config.priority_formula(formula_version, config)
    score = compute_priority_score(m, scale=scale, formula_version=version, config=config)
    band, label = priority_band(score, config)
    return PriorityResult(score=score, band=band, label=label, formula_version=version)


def result_as_dict(r: PriorityResult) -> dict:
    """Flatten a PriorityResult for audit_log / JSON persistence."""
    return asdict(r)
