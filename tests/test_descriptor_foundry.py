"""Descriptor Foundry / Spark Line — offline, deterministic, zero-spend tests.

Every case runs with scripted fake providers; no model is ever called. Proves
the gate refuses fabrication and the pipeline emits candidate-only output that
cannot publish ("AI never publishes" by construction).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worker.descriptor import (
    DescriptorFoundryError,
    FoundryResult,
    SourceMaterial,
    STATUS_CANDIDATE,
    TIER_AI_DRAFTED,
    assert_faithful,
    is_faithful,
    run_foundry,
    run_golden,
)
from worker.descriptor.foundry import PROMPT_VERSION, _prompt_sha256


# --- scripted fake providers (deterministic, offline) ------------------------

class ScriptedGenerator:
    def __init__(self, candidates, fused=None, model_id="gen-model"):
        self.model_id = model_id
        self._candidates = list(candidates)
        self._fused = fused

    def generate_candidates(self, material, n):
        return list(self._candidates)

    def fuse(self, winners, material):
        return self._fused if self._fused is not None else winners[0]


class ScriptedJudge:
    def __init__(self, score=1.0, model_id="judge-model"):
        self.model_id = model_id
        self._score = score

    def score(self, text, material):
        return self._score


MERIDIAN = SourceMaterial(
    artist="The Meridian",
    texts=("Brass-heavy soul, all menace and amen.",),
    refs=("src://meridian/bio",),
)


# --- gate unit tests ---------------------------------------------------------

def test_gate_accepts_faithful_vibe_line():
    # A faithful line does not raise; assert_faithful returns None on accept.
    assert assert_faithful("brass. menace. amen.", MERIDIAN) is None


def test_gate_rejects_bad_word_count():
    with pytest.raises(DescriptorFoundryError, match="3 / 5 / 7"):
        assert_faithful("brass menace slow burn", MERIDIAN)  # 4 words


def test_gate_rejects_banned_marketing_language():
    with pytest.raises(DescriptorFoundryError, match="banned"):
        assert_faithful("legendary brass, menace, pure amen", MERIDIAN)


def test_gate_rejects_ungrounded_proper_noun():
    mat = SourceMaterial(artist="Copper Veins", texts=("Slow guitar, whispered vocals.",))
    with pytest.raises(DescriptorFoundryError, match="proper noun"):
        assert_faithful("Copper Veins with Berlin, aching", mat)


def test_gate_rejects_ungrounded_number():
    mat = SourceMaterial(artist="Mara Quinn", texts=("Desert-noir country songwriter.",))
    with pytest.raises(DescriptorFoundryError, match="number"):
        assert_faithful("desert-noir dust since 1998, wandering", mat)


def test_gate_accepts_grounded_proper_noun():
    mat = SourceMaterial(artist="Mara Quinn", texts=("Mara Quinn plays desert-noir country.",))
    assert assert_faithful("Mara Quinn: desert-noir dust ballads", mat) is None


def test_gate_accepts_grounded_number():
    mat = SourceMaterial(artist="Trio 44", texts=("Trio 44 plays restless free jazz.",))
    assert assert_faithful("Trio 44, restless free-jazz sprawl", mat) is None


def test_gate_fails_closed_on_empty_source():
    with pytest.raises(DescriptorFoundryError, match="no source material"):
        assert_faithful("brass menace amen", SourceMaterial(artist="", texts=()))


def test_is_faithful_is_non_raising():
    assert is_faithful("brass. menace. amen.", MERIDIAN) is True
    assert is_faithful("brass menace slow burn", MERIDIAN) is False


# --- pipeline tests ----------------------------------------------------------

HAPPY_CANDIDATES = [
    "brass. menace. amen.",          # 3, faithful
    "quiet brass, low menace, rising",  # 5, faithful
    "big amazing loud show",         # banned + bad count -> dropped
    "brass menace",                  # 2 words -> dropped
]


def test_happy_path_emits_candidate_only():
    gen = ScriptedGenerator(HAPPY_CANDIDATES)
    result = run_foundry(MERIDIAN, gen, ScriptedJudge(score=0.95))
    assert isinstance(result, FoundryResult)
    assert result.status == STATUS_CANDIDATE
    assert result.tier == TIER_AI_DRAFTED
    # The emitted text itself passes the gate.
    assert_faithful(result.text, MERIDIAN)


def test_no_material_is_honest_gap_not_error():
    gen = ScriptedGenerator(HAPPY_CANDIDATES)
    empty = SourceMaterial(artist="Nobody", texts=())
    assert run_foundry(empty, gen, ScriptedJudge()) is None


def test_all_candidates_unfaithful_returns_none():
    gen = ScriptedGenerator(["big amazing loud show", "brass menace", "legendary brass menace amen loud"])
    assert run_foundry(MERIDIAN, gen, ScriptedJudge()) is None


def test_fused_line_unfaithful_fails_loud():
    # Candidates are faithful, but fusion invents a place — that is a defect,
    # not an honest gap: it must raise, never ship.
    gen = ScriptedGenerator(HAPPY_CANDIDATES, fused="brass, menace, Berlin, cold, rising")
    with pytest.raises(DescriptorFoundryError, match="proper noun"):
        run_foundry(MERIDIAN, gen, ScriptedJudge())


def test_judge_below_threshold_is_honest_gap():
    gen = ScriptedGenerator(HAPPY_CANDIDATES)
    assert run_foundry(MERIDIAN, gen, ScriptedJudge(score=0.5)) is None


def test_non_independent_judge_is_refused():
    gen = ScriptedGenerator(HAPPY_CANDIDATES, model_id="same-model")
    with pytest.raises(DescriptorFoundryError, match="independent judge"):
        run_foundry(MERIDIAN, gen, ScriptedJudge(model_id="same-model"))


def test_provenance_is_fully_stamped():
    gen = ScriptedGenerator(HAPPY_CANDIDATES, model_id="gen-x")
    fixed = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
    result = run_foundry(MERIDIAN, gen, ScriptedJudge(score=0.9, model_id="judge-y"), now=fixed)
    p = result.provenance
    assert p["provider"] == "descriptor_foundry"
    assert p["generator_model"] == "gen-x"
    assert p["judge_model"] == "judge-y"
    assert p["prompt_version"] == PROMPT_VERSION
    assert p["prompt_sha256"] == _prompt_sha256()
    assert p["judge_score"] == 0.9
    assert p["source_refs"] == ["src://meridian/bio"]
    assert p["candidate_texts"] == HAPPY_CANDIDATES
    assert p["extracted_at"] == "2026-08-02T12:00:00+00:00"
    # Winners are a subset of the raw candidates (the knockout survivors).
    assert set(p["winner_texts"]).issubset(set(HAPPY_CANDIDATES))


# --- golden-set regression ---------------------------------------------------

def test_golden_set_matches_expected_verdicts():
    outcomes = run_golden()
    failures = [o for o in outcomes if not o.ok]
    assert not failures, "golden gate regressions: " + "; ".join(
        f"{o.case_id} expected {o.expected} got {o.actual} ({o.detail})" for o in failures
    )


def test_golden_set_covers_both_verdicts():
    outcomes = run_golden()
    verdicts = {o.expected for o in outcomes}
    assert verdicts == {"pass", "reject"}, "golden set must exercise both accept and refuse"
    assert len(outcomes) >= 8
