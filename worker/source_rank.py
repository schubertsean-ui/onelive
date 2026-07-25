"""Source priority scoring model.

Formula per ONE_LIVE_Reconciled_Master_Spec.md sec.14:
  priority_score = credibility_weight*0.40 + access_reliability*0.20
                 + coverage_uniqueness*0.15 + update_frequency_score*0.15
                 + verification_anchor_score*0.10
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/source_rank.py)

Weights (worker/config/source_rank_config.json) — the EDITABLE source of
truth for the five weights above. Mirrors brain/iq.py's load_iq_config() /
tools/kpi_report.py's load_kpi_registry(): the JSON is validated here, once,
fail-LOUD (missing file, unknown/missing weight key, or weights that don't
sum to 1.0), and NEVER silently defaulted. Changing a weight's VALUE is a pure
JSON edit; the score's shape (which five weights exist) is fixed by
SourceMetrics/compute_priority_score below.
"""
import json
import pathlib
from dataclasses import dataclass


class SourceRankConfigError(Exception):
    """worker/config/source_rank_config.json is missing, is not valid JSON,
    has an unknown or missing weight key, or its weights don't sum to 1.0
    (within 1e-9) — fail loud, never silently drop or guess at a weight."""


DEFAULT_SOURCE_RANK_CONFIG = (
    pathlib.Path(__file__).resolve().parent / "config" / "source_rank_config.json"
)

# The exact weight-key set the formula reads — no more, no less.
_EXPECTED_WEIGHT_KEYS = frozenset({
    "credibility_weight", "access_reliability", "coverage_uniqueness",
    "update_frequency_score", "verification_anchor_score",
})

# Float-safe tolerance for the "weights sum to 1.0" check — see brain/iq.py's
# load_iq_config for the same rationale (absorbs ~1e-16 float round-off only).
_WEIGHT_SUM_TOLERANCE = 1e-9


def load_source_rank_config(path: pathlib.Path = DEFAULT_SOURCE_RANK_CONFIG) -> dict:
    """Load + validate worker/config/source_rank_config.json into a
    ``{weight_key: float}`` dict.

    Fail-CLOSED, per CLAUDE.md's no-silent-deferral rule: a missing file,
    invalid JSON, an unknown or missing weight key, a non-numeric weight, or
    weights that don't sum to 1.0 (within ``_WEIGHT_SUM_TOLERANCE``) all raise
    ``SourceRankConfigError``. Nothing is ever silently skipped, defaulted, or
    "fixed" — a bad sum is reported, never rounded away, because doing so
    would silently change a computed priority score.
    """
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SourceRankConfigError(
            f"cannot read source-rank weight config at {path}: {exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SourceRankConfigError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("weights"), dict):
        raise SourceRankConfigError(
            f"{path}: expected a top-level JSON object with a 'weights' object.")
    weights_raw = data["weights"]

    actual_keys = set(weights_raw)
    unknown_keys = actual_keys - _EXPECTED_WEIGHT_KEYS
    if unknown_keys:
        raise SourceRankConfigError(
            f"{path}: unknown weight key(s): {', '.join(sorted(unknown_keys))} — "
            f"expected exactly {sorted(_EXPECTED_WEIGHT_KEYS)}.")
    missing_keys = _EXPECTED_WEIGHT_KEYS - actual_keys
    if missing_keys:
        raise SourceRankConfigError(
            f"{path}: missing weight key(s): {', '.join(sorted(missing_keys))}.")

    weights: dict = {}
    for key, value in weights_raw.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SourceRankConfigError(
                f"{path}: weight key {key!r} must be a number, got {value!r}.")
        weights[key] = float(value)
    total = sum(weights.values())
    if abs(total - 1.0) > _WEIGHT_SUM_TOLERANCE:
        raise SourceRankConfigError(
            f"{path}: weights sum to {total!r}, not 1.0 (within "
            f"{_WEIGHT_SUM_TOLERANCE}) — refusing to load a config that "
            "would silently change a computed score.")
    return weights


SOURCE_RANK_WEIGHTS = load_source_rank_config()


@dataclass
class SourceMetrics:
    credibility_weight: float
    access_reliability: float
    coverage_uniqueness: float
    update_frequency_score: float
    verification_anchor_score: float


def compute_priority_score(m: SourceMetrics) -> float:
    w = SOURCE_RANK_WEIGHTS
    return round((
        m.credibility_weight * w["credibility_weight"] +
        m.access_reliability * w["access_reliability"] +
        m.coverage_uniqueness * w["coverage_uniqueness"] +
        m.update_frequency_score * w["update_frequency_score"] +
        m.verification_anchor_score * w["verification_anchor_score"]
    ) * 100, 2)
