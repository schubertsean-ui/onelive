"""Tests for the Spark Line earned-confidence auto-publish policy + store path
(founder-directed 2026-08-03 — the fix for the per-item-human-approval catch-22).

Proves: fail-closed with the flag OFF (nothing auto-publishes); a Foundry-validated
line auto-approves when the flag is ON and the independent judge cleared the bar;
below-bar or no-evidence lines go to human review. Pure policy + store path with a
fake cursor — no DB, no network.
"""
import json

import pytest

from worker.descriptor.publish_policy import (
    DEFAULT_JUDGE_THRESHOLD,
    auto_publish_spark,
    decide_spark_publish,
)
from worker.descriptor.store import insert_with_policy
from worker.descriptor.types import STATUS_CANDIDATE, FoundryResult


# ---- pure policy ----------------------------------------------------------

def test_flag_off_is_fail_closed_human_review():
    d = decide_spark_publish(judge_score=0.99, ratified=False)
    assert d.action == "human_review" and "not ratified" in d.reason


def test_validated_above_bar_auto_approves_when_ratified():
    d = decide_spark_publish(judge_score=DEFAULT_JUDGE_THRESHOLD, ratified=True)
    assert d.auto_approves


def test_below_bar_goes_to_human_even_when_ratified():
    d = decide_spark_publish(judge_score=DEFAULT_JUDGE_THRESHOLD - 0.01, ratified=True)
    assert d.action == "human_review" and "below bar" in d.reason


@pytest.mark.parametrize("bad", [None, -0.1, 1.1, "x"])
def test_missing_or_invalid_judge_score_never_auto_publishes(bad):
    # Even ratified: no valid validation evidence => never auto-publish.
    d = decide_spark_publish(judge_score=bad, ratified=True)
    assert d.action == "human_review"


def test_flag_reads_env(monkeypatch):
    monkeypatch.delenv("AUTO_PUBLISH_SPARK", raising=False)
    assert auto_publish_spark() is False
    monkeypatch.setenv("AUTO_PUBLISH_SPARK", "1")
    assert auto_publish_spark() is True
    # With the env on, the policy (ratified defaulted from the flag) auto-approves.
    assert decide_spark_publish(judge_score=0.95).auto_approves


# ---- store write path -----------------------------------------------------

class _FakeCursor:
    def __init__(self):
        self.params = None

    def execute(self, sql, params=None):
        self.params = params

    def fetchone(self):
        return ("sid-1",)


def _result(judge_score):
    return FoundryResult(
        text="Horns that start",  # 3 words — valid
        tier="C",
        status=STATUS_CANDIDATE,
        provenance={"judge_score": judge_score, "attribution": None},
    )


def _written(cur):
    # insert params: (artist_key, artist_name, text, word_count, tier,
    #                 attribution, status, provenance_json)
    status = cur.params[6]
    prov = json.loads(cur.params[7])
    return status, prov


def test_store_flag_off_writes_candidate():
    cur = _FakeCursor()
    sid, status = insert_with_policy(_result(0.99), "Khruangbin", cur=cur, ratified=False)
    assert status == STATUS_CANDIDATE
    w_status, prov = _written(cur)
    assert w_status == STATUS_CANDIDATE
    assert "approval" not in prov  # never auto-approved with the flag off


def test_store_ratified_high_score_auto_approves():
    cur = _FakeCursor()
    sid, status = insert_with_policy(_result(0.95), "Khruangbin", cur=cur, ratified=True)
    assert status == "approved"
    w_status, prov = _written(cur)
    assert w_status == "approved"
    assert prov["approval"]["auto"] is True
    assert prov["approval"]["approver"] == "descriptor_foundry:auto"
    assert prov["approval"]["judge_score"] == 0.95


def test_store_ratified_low_score_stays_candidate():
    cur = _FakeCursor()
    sid, status = insert_with_policy(_result(0.5), "Khruangbin", cur=cur, ratified=True)
    assert status == STATUS_CANDIDATE
    w_status, prov = _written(cur)
    assert w_status == STATUS_CANDIDATE
    assert "approval" not in prov


def test_store_rejects_non_candidate_input():
    bad = FoundryResult(text="x y z", tier="C", status="approved", provenance={})
    with pytest.raises(ValueError):
        insert_with_policy(bad, "A", cur=_FakeCursor(), ratified=True)
