"""Mechanism 3 — automatic source-reputation decay/growth.

On a false positive a source's weight is multiplied down (v1: x0.85, floored at
0.1); on a true positive it is nudged up (v1: x1.02, capped at 1.0). This drift
is what makes an individual source's credibility weight diverge from its type
baseline over time (see ``worker.source_credibility``), which is why the weight
model supports a per-source override.

The update rule is a *pluggable* pure function keyed by version, so a future
sample-size-aware rule (e.g. Wilson score / Bayesian) can be swapped in without
touching call sites — just register it and bump ``current_version`` in
``sources/trust_config.json``. All v1 constants are data-driven, not hardcoded.
"""
import os

import psycopg2

from worker import trust_config

DB_DSN = os.getenv("ONELIVE_DB_DSN", "dbname=onelive user=postgres password=postgres host=localhost")

# Outcome labels used across the trust substrate.
TRUE_POSITIVE = "true_positive"
FALSE_POSITIVE = "false_positive"
OUTCOMES = (TRUE_POSITIVE, FALSE_POSITIVE)


def db():
    return psycopg2.connect(DB_DSN)


# --- pluggable update rules ------------------------------------------------

def decay_growth_v1(weight: float, outcome: str, config: dict | None = None) -> float:
    """v1 reputation update: multiplicative decay/growth with floor and cap.

    false_positive -> weight * false_positive_multiplier, floored
    true_positive  -> weight * true_positive_multiplier, capped

    Constants (multipliers, floor, cap) come from the versioned config.
    """
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown outcome {outcome!r} (expected one of {OUTCOMES})")
    _, p = trust_config.reputation_params("v1", config)
    if outcome == FALSE_POSITIVE:
        return max(p["floor"], weight * p["false_positive_multiplier"])
    return min(p["cap"], weight * p["true_positive_multiplier"])


# Registry of update rules. Add future versions (e.g. "v2" Wilson-score) here;
# call sites resolve the active rule through get_decay_growth().
DECAY_GROWTH_FUNCTIONS = {
    "v1": decay_growth_v1,
}


def get_decay_growth(version: str | None = None):
    """Return the reputation update function for ``version`` (default: the
    config's current_version)."""
    ver = version or trust_config.reputation_params()[0]
    try:
        return DECAY_GROWTH_FUNCTIONS[ver]
    except KeyError:
        raise KeyError(
            f"no decay/growth function registered for version {ver!r}; "
            f"registered: {sorted(DECAY_GROWTH_FUNCTIONS)}"
        )


def apply_reputation_update(
    weight: float,
    outcome: str,
    version: str | None = None,
    config: dict | None = None,
) -> float:
    """Pure entry point: apply the active decay/growth rule to a weight."""
    return get_decay_growth(version)(weight, outcome, config)


# --- persistence -----------------------------------------------------------

def record_outcome(source_id: str, outcome: str, version: str | None = None) -> float:
    """Persist a reputation update for a source and return the new weight.

    Reads the source's current per-source credibility weight (its override),
    applies the pluggable decay/growth rule, writes it back to
    ``source_reliability.reliability_score``, and returns the new value.
    """
    new_weight_holder = {}
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into source_reliability (source_id, reliability_score)
                values (%s, %s)
                on conflict (source_id) do nothing
                """,
                (source_id, trust_config.reputation_params(version)[1]["cap"]),
            )
            cur.execute(
                "select reliability_score from source_reliability where source_id=%s",
                (source_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError("source_reliability row missing after upsert")
            current = float(row[0])
            new_weight = apply_reputation_update(current, outcome, version=version)
            cur.execute(
                """
                update source_reliability
                set reliability_score = %s, last_updated = now()
                where source_id = %s
                """,
                (new_weight, source_id),
            )
            new_weight_holder["value"] = new_weight
        conn.commit()
    return new_weight_holder["value"]


def adjust_source_reliability(source_id: str, delta: float):
    """Legacy additive adjustment (kept for callers that pass a raw delta).

    New code should prefer ``record_outcome`` with a true/false-positive label so
    the pluggable, versioned decay/growth rule is applied consistently.
    """
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                insert into source_reliability (source_id, reliability_score)
                values (%s, 0.5)
                on conflict (source_id) do nothing
                """,
                (source_id,),
            )
            cur.execute(
                """
                update source_reliability
                set reliability_score = greatest(0, least(1, reliability_score + %s)),
                    last_updated = now()
                where source_id=%s
                """,
                (delta, source_id),
            )
        conn.commit()
