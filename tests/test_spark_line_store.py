"""spark_line store — hermetic tests (fake cursor, no DB, no psycopg2)."""
from __future__ import annotations

import json

import pytest

from worker.descriptor.store import (
    artist_key,
    fetch_approved,
    insert_candidate,
    record_human_spark_line,
)
from worker.descriptor.types import FoundryResult, STATUS_CANDIDATE, TIER_AI_DRAFTED


class FakeCursor:
    """Records execute() calls; returns scripted rows."""

    def __init__(self, one=None, many=()):
        self.calls = []
        self._one = one
        self._many = list(many)

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


def _result(text="quiet brass, low menace, rising", tier=TIER_AI_DRAFTED,
            status=STATUS_CANDIDATE, provenance=None):
    return FoundryResult(
        text=text, tier=tier, status=status,
        provenance=provenance if provenance is not None else {"judge_score": 0.9},
    )


def test_artist_key_normalizes():
    assert artist_key("  The Meridian ") == "the meridian"
    assert artist_key("MARA QUINN") == "mara quinn"
    assert artist_key("") == ""


def test_insert_candidate_writes_candidate_status_and_wordcount():
    cur = FakeCursor(one=("sid-1",))
    sid = insert_candidate(_result(), "The Meridian", cur=cur)
    assert sid == "sid-1"
    sql, params = cur.calls[0]
    assert "insert into spark_line" in sql
    # params order: artist_key, artist_name, text, word_count, tier,
    #               attribution, status, provenance_json
    assert params[0] == "the meridian"
    assert params[1] == "The Meridian"
    assert params[3] == 5                      # word count
    assert params[6] == STATUS_CANDIDATE       # never 'approved' from here
    assert json.loads(params[7]) == {"judge_score": 0.9}


def test_insert_refuses_non_candidate_result():
    cur = FakeCursor(one=("x",))
    with pytest.raises(ValueError, match="only inserts candidates"):
        insert_candidate(_result(status="approved"), "The Meridian", cur=cur)
    assert cur.calls == []  # never touched the DB


def test_fetch_approved_filters_and_maps():
    cur = FakeCursor(many=[("the meridian", "brass. menace. amen.", "C", None)])
    out = fetch_approved(["The Meridian", "the meridian ", ""], cur=cur)
    sql, params = cur.calls[0]
    assert "status = 'approved'" in sql
    assert "any(%s)" in sql
    # de-duplicated to one normalized key
    assert params[0] == ["the meridian"]
    assert out == {"the meridian": {"text": "brass. menace. amen.", "tier": "C", "attribution": None}}


def test_fetch_approved_no_names_is_no_query():
    cur = FakeCursor()
    assert fetch_approved(["", "  "], cur=cur) == {}
    assert cur.calls == []


def test_record_human_tier_a_writes_candidate_no_model():
    cur = FakeCursor(one=("h-1",))
    sid = record_human_spark_line("Mara Quinn", "brass. menace. amen.", tier="A", cur=cur)
    assert sid == "h-1"
    _, params = cur.calls[0]
    assert params[0] == "mara quinn"
    assert params[3] == 3                 # word count
    assert params[4] == "A"               # tier
    assert params[6] == STATUS_CANDIDATE  # still gated by human take-live
    assert json.loads(params[7])["provider"] == "human"


def test_record_human_tier_b_requires_attribution():
    cur = FakeCursor(one=("x",))
    with pytest.raises(ValueError, match="attribution"):
        record_human_spark_line("Mara Quinn", "brass menace amen", tier="B", cur=cur)
    assert cur.calls == []


def test_record_human_rejects_bad_word_count():
    cur = FakeCursor(one=("x",))
    with pytest.raises(ValueError, match="words"):
        record_human_spark_line("Mara Quinn", "brass menace slow burn", tier="A", cur=cur)


def test_record_human_rejects_ai_tier():
    cur = FakeCursor(one=("x",))
    with pytest.raises(ValueError, match="tier must be 'A' or 'B'"):
        record_human_spark_line("Mara Quinn", "brass menace amen", tier="C", cur=cur)
