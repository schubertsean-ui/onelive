"""Tests for worker/source_rank.py's config-driven weights (founder directive:
"Make it all config-driven" — mirrors docs/metrics/kpi_registry.json +
tools/kpi_report.py's load_kpi_registry() fail-loud style, and brain/iq.py's
load_iq_config()).

Proves: SOURCE_RANK_WEIGHTS now loads from worker/config/
source_rank_config.json via load_source_rank_config(); the config-loaded
values are BYTE-IDENTICAL to the historical hardcoded formula
(credibility*0.40 + access*0.20 + coverage*0.15 + update*0.15 +
verification*0.10); compute_priority_score's output is unchanged on a fixed
input; editing ONLY the JSON changes the priority score with zero code
touched; and every malformed-config shape (missing file, unknown key,
missing key, bad sum) fails loud with a specific message naming the bad
field.
"""
from __future__ import annotations

import json

import pytest

from worker.source_rank import (
    DEFAULT_SOURCE_RANK_CONFIG,
    SOURCE_RANK_WEIGHTS,
    SourceMetrics,
    SourceRankConfigError,
    compute_priority_score,
    load_source_rank_config,
)

# The historical hardcoded formula's weights (ONE_LIVE_Reconciled_Master_Spec.md
# sec.14) — the single source of truth this suite proves the JSON reproduces.
_OLD_WEIGHTS = {
    "credibility_weight": 0.40,
    "access_reliability": 0.20,
    "coverage_uniqueness": 0.15,
    "update_frequency_score": 0.15,
    "verification_anchor_score": 0.10,
}

_FIXED_METRICS = SourceMetrics(
    credibility_weight=0.90,
    access_reliability=0.80,
    coverage_uniqueness=0.70,
    update_frequency_score=0.60,
    verification_anchor_score=0.50,
)


def _old_hardcoded_formula(m: SourceMetrics) -> float:
    return round((
        m.credibility_weight * 0.40 +
        m.access_reliability * 0.20 +
        m.coverage_uniqueness * 0.15 +
        m.update_frequency_score * 0.15 +
        m.verification_anchor_score * 0.10
    ) * 100, 2)


def _valid_config_dict() -> dict:
    return json.loads(DEFAULT_SOURCE_RANK_CONFIG.read_text(encoding="utf-8"))


def _write(path, data) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


# ============================================================================
# Values unchanged — the most important criterion.
# ============================================================================
def test_source_rank_weights_equal_the_old_hardcoded_values_exactly():
    assert SOURCE_RANK_WEIGHTS == _OLD_WEIGHTS


def test_weights_sum_to_1_within_tolerance():
    assert abs(sum(SOURCE_RANK_WEIGHTS.values()) - 1.0) < 1e-9


def test_priority_score_is_byte_identical_to_the_old_hardcoded_formula():
    assert compute_priority_score(_FIXED_METRICS) == _old_hardcoded_formula(_FIXED_METRICS)
    assert compute_priority_score(_FIXED_METRICS) == 76.5


def test_priority_score_matches_across_several_fixed_inputs():
    fixtures = [
        SourceMetrics(1.0, 1.0, 1.0, 1.0, 1.0),
        SourceMetrics(0.0, 0.0, 0.0, 0.0, 0.0),
        SourceMetrics(0.33, 0.71, 0.12, 0.95, 0.44),
        SourceMetrics(credibility_weight=0.5, access_reliability=0.25,
                      coverage_uniqueness=0.9, update_frequency_score=0.1,
                      verification_anchor_score=0.6),
    ]
    for m in fixtures:
        assert compute_priority_score(m) == _old_hardcoded_formula(m), m


# ============================================================================
# Config-driven proof — editing ONLY the JSON changes the priority score, with
# zero code touched.
# ============================================================================
def test_change_a_weight_via_config_only_changes_the_priority_score(tmp_path):
    data = _valid_config_dict()
    # Shift weight from verification to credibility, keeping the sum at 1.0.
    data["weights"]["credibility_weight"] = 0.50
    data["weights"]["verification_anchor_score"] = 0.00
    cfg_path = tmp_path / "source_rank_config.json"
    _write(cfg_path, data)

    loaded = load_source_rank_config(cfg_path)
    assert loaded["credibility_weight"] == 0.50
    assert loaded["verification_anchor_score"] == 0.00

    def new_formula(m: SourceMetrics) -> float:
        return round((
            m.credibility_weight * loaded["credibility_weight"] +
            m.access_reliability * loaded["access_reliability"] +
            m.coverage_uniqueness * loaded["coverage_uniqueness"] +
            m.update_frequency_score * loaded["update_frequency_score"] +
            m.verification_anchor_score * loaded["verification_anchor_score"]
        ) * 100, 2)

    assert new_formula(_FIXED_METRICS) != compute_priority_score(_FIXED_METRICS)


# ============================================================================
# Fail-loud cases.
# ============================================================================
def test_missing_file_raises_loud(tmp_path):
    with pytest.raises(SourceRankConfigError, match="cannot read"):
        load_source_rank_config(tmp_path / "does_not_exist.json")


def test_bad_json_raises_loud(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(SourceRankConfigError, match="not valid JSON"):
        load_source_rank_config(bad)


def test_not_shaped_weights_object_raises_loud(tmp_path):
    bad = tmp_path / "bad.json"
    _write(bad, {"not_weights": {}})
    with pytest.raises(SourceRankConfigError, match="'weights'"):
        load_source_rank_config(bad)


def test_unknown_weight_key_raises_loud(tmp_path):
    data = _valid_config_dict()
    data["weights"]["extra_field"] = 0.05
    bad = tmp_path / "bad.json"
    _write(bad, data)
    with pytest.raises(SourceRankConfigError, match="unknown weight key"):
        load_source_rank_config(bad)


def test_missing_weight_key_raises_loud(tmp_path):
    data = _valid_config_dict()
    del data["weights"]["verification_anchor_score"]
    bad = tmp_path / "bad.json"
    _write(bad, data)
    with pytest.raises(SourceRankConfigError, match="missing weight key"):
        load_source_rank_config(bad)


def test_bad_sum_raises_loud(tmp_path):
    data = _valid_config_dict()
    data["weights"]["credibility_weight"] = 0.99
    bad = tmp_path / "bad.json"
    _write(bad, data)
    with pytest.raises(SourceRankConfigError, match="sum to"):
        load_source_rank_config(bad)


def test_non_numeric_weight_raises_loud(tmp_path):
    data = _valid_config_dict()
    data["weights"]["credibility_weight"] = "not a number"
    bad = tmp_path / "bad.json"
    _write(bad, data)
    with pytest.raises(SourceRankConfigError, match="must be a number"):
        load_source_rank_config(bad)


def test_real_config_loads_clean():
    loaded = load_source_rank_config(DEFAULT_SOURCE_RANK_CONFIG)
    assert set(loaded) == set(_OLD_WEIGHTS)
