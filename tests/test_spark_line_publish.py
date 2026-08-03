"""Gate-custodied Spark Line take-live — hermetic tests (fake cursor, no DB)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from worker.descriptor.publish import (
    SparkLinePublishError,
    approve_candidate,
    reject_candidate,
)


class FakeCursor:
    """Scripts one loaded row and one update rowcount."""

    def __init__(self, row, rowcount=1):
        self._row = row
        self.rowcount = rowcount
        self.updates = []

    def execute(self, sql, params=None):
        if sql.strip().lower().startswith("select"):
            self._last = self._row
        else:
            self.updates.append((sql, params))

    def fetchone(self):
        return self._row


ROW = ("s-1", "brass. menace. amen.", "candidate", {"judge_score": 0.9})
FIXED = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)


def test_approve_takes_candidate_live_and_records_approver():
    cur = FakeCursor(ROW)
    approve_candidate("s-1", expected_text="brass. menace. amen.",
                      approver="sean@schubert", cur=cur, now=FIXED)
    sql, params = cur.updates[0]
    assert "set status = %s" in sql
    assert params[0] == "approved"
    # provenance json carries the approval stamp
    import json
    prov = json.loads(params[1])
    assert prov["approval"]["approver"] == "sean@schubert"
    assert prov["approval"]["approved_at"] == "2026-08-02T12:00:00+00:00"
    assert len(prov["approval"]["approved_text_sha256"]) == 64
    # the update is guarded on status = candidate (params[3])
    assert params[3] == "candidate"


def test_ai_identity_can_never_approve():
    cur = FakeCursor(ROW)
    for who in ("descriptor_foundry", "agent", "system", "", "  "):
        with pytest.raises(SparkLinePublishError, match="not a human identity"):
            approve_candidate("s-1", expected_text="brass. menace. amen.",
                              approver=who, cur=cur)
    assert cur.updates == []  # nothing published


def test_refuses_non_candidate_row():
    cur = FakeCursor(("s-1", "brass. menace. amen.", "approved", {}))
    with pytest.raises(SparkLinePublishError, match="only a candidate"):
        approve_candidate("s-1", expected_text="brass. menace. amen.",
                          approver="sean", cur=cur)


def test_refuses_when_text_changed_since_review():
    cur = FakeCursor(ROW)
    with pytest.raises(SparkLinePublishError, match="text has changed"):
        approve_candidate("s-1", expected_text="different words entirely here",
                          approver="sean", cur=cur)
    assert cur.updates == []


def test_refuses_missing_row():
    cur = FakeCursor(None)
    with pytest.raises(SparkLinePublishError, match="no spark_line row"):
        approve_candidate("nope", expected_text="x", approver="sean", cur=cur)


def test_concurrent_change_fails_closed():
    cur = FakeCursor(ROW, rowcount=0)  # update matched nothing
    with pytest.raises(SparkLinePublishError, match="concurrent change"):
        approve_candidate("s-1", expected_text="brass. menace. amen.",
                          approver="sean", cur=cur)


def test_reject_records_reason_and_keeps_row():
    cur = FakeCursor(ROW)
    reject_candidate("s-1", approver="sean", reason="off-brand", cur=cur, now=FIXED)
    sql, params = cur.updates[0]
    assert params[0] == "rejected"
    import json
    prov = json.loads(params[1])
    assert prov["rejection"]["reason"] == "off-brand"
    assert prov["rejection"]["approver"] == "sean"


def test_reject_also_refuses_ai_identity():
    cur = FakeCursor(ROW)
    with pytest.raises(SparkLinePublishError, match="not a human identity"):
        reject_candidate("s-1", approver="descriptor_foundry", cur=cur)
    assert cur.updates == []
