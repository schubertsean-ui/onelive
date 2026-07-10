"""Mechanism 1 — source-credibility weighting (0.0-1.0 scale).

Each source type has a default credibility weight (venue_calendar/venue_claim/
artist_claim = 1.0 down to anonymous = 0.2). An individual source may override
its type baseline — necessary because the reputation decay/growth mechanism
(``worker.source_reliability``) drifts individual sources away from their type
default over time.

The aggregated weight across the sources backing an event maps to a confidence
state via configurable thresholds (>=1.8 likely, >=1.0 unverified, <1.0
disputed). This is the *weight-based* confidence signal; it is complementary to
the evidence-class multi-confirm signal in ``worker.confidence.derive_confidence``
and both resolve to the same canonical 4-state model.

Every numeric constant is loaded from ``worker.trust_config`` (data-driven), not
hardcoded here.
"""
from typing import Iterable

from worker import trust_config
from worker.confidence import is_valid_confidence


def type_default_weight(source_type: str, config: dict | None = None) -> float:
    """Baseline credibility weight for a source type.

    Unknown types fall back to the configurable ``default_source_type_weight``
    (the anonymous baseline) rather than raising, so a newly-added source type
    degrades safely to low trust instead of breaking ingestion.
    """
    weights = trust_config.source_type_weights(config)
    if source_type in weights:
        return weights[source_type]
    return trust_config.default_source_type_weight(config)


def effective_weight(
    source_type: str,
    override: float | None = None,
    config: dict | None = None,
) -> float:
    """Credibility weight for an individual source.

    Uses the per-source ``override`` when provided (this is where decayed/grown
    reputation lives), otherwise the source type's default. Result is clamped to
    the valid [0.0, 1.0] credibility scale.
    """
    weight = override if override is not None else type_default_weight(source_type, config)
    return _clamp_unit(float(weight))


def aggregate_weight(
    weights: Iterable[float],
) -> float:
    """Sum the effective weights of the sources backing a single event."""
    return float(sum(weights))


def derive_confidence_from_weight(total_weight: float, config: dict | None = None) -> str:
    """Map an aggregated source weight to a 4-state confidence value.

    Walks the configured thresholds high→low and returns the first state whose
    ``min_weight`` the total meets. With v1 defaults: >=1.8 → likely,
    >=1.0 → unverified, otherwise → disputed. Never silently drops below the
    lowest threshold — the final band (min_weight 0.0) always matches.
    """
    for row in trust_config.confidence_weight_thresholds(config):
        if total_weight >= row["min_weight"]:
            state = row["state"]
            if not is_valid_confidence(state):
                raise ValueError(f"config maps weight to invalid confidence state: {state!r}")
            return state
    # Should be unreachable given a 0.0-floored threshold, but fail loud if the
    # config was edited to remove the catch-all band.
    raise ValueError(
        f"no confidence threshold matched weight {total_weight!r}; "
        "trust_config.confidence_weight_thresholds needs a min_weight<=0 band"
    )


def _clamp_unit(x: float) -> float:
    return max(0.0, min(1.0, x))
