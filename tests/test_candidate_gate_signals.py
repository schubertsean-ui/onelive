"""Finding 3: worker.candidate_store._load_gate_signals reads REAL stored
extraction + evidence facts (no `_extracted_for_test` shortcut) and shapes them
for trust_gate3. These tests drive the real function with a fake DB cursor so
the load logic itself is verified without a live Postgres — proving that a
validation-error / private-RSVP / conflicting-start-time candidate produces the
signals the gate needs to refuse it.
"""
import datetime as dt

import pytest

from worker.candidate_store import _load_gate_signals


class FakeCursor:
    """Returns queued rows in call order. Each execute() pops the next result
    tuple; fetchone() returns it. Enough to exercise _load_gate_signals' two
    queries (candidate row, then the optional dedupe count)."""

    def __init__(self, results):
        self._results = list(results)
        self._last = None
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        self._last = self._results.pop(0) if self._results else None

    def fetchone(self):
        return self._last


def test_missing_candidate_raises():
    cur = FakeCursor([None])
    with pytest.raises(ValueError):
        _load_gate_signals(cur, "does-not-exist")


def test_private_rsvp_column_folds_into_extracted():
    # jsonb copy says public, authoritative column says private -> gate must see
    # private (fail-closed against a stale jsonb).
    extracted_json = {"is_private_rsvp": False, "start_time": "2026-07-11T20:00:00"}
    row = (extracted_json, dt.datetime(2026, 7, 11, 20, 0, 0), "Mohawk", True)
    cur = FakeCursor([row, (0,)])
    extracted, signals = _load_gate_signals(cur, "cid")
    assert extracted["is_private_rsvp"] is True


def test_validation_error_provenance_is_passed_through():
    extracted_json = {"_provenance": {"validation_error": True}}
    row = (extracted_json, None, None, False)
    cur = FakeCursor([row])
    extracted, signals = _load_gate_signals(cur, "cid")
    assert extracted["_provenance"]["validation_error"] is True
    # No venue/start -> no dedupe query issued.
    assert signals["dedupe_ambiguous"] is False


def test_conflicting_start_times_are_collected_distinctly():
    # Candidate column says 20:00, stored extraction says 21:30 -> two distinct
    # start-time claims the gate will read as a conflict.
    extracted_json = {"start_time": "2026-07-11T21:30:00"}
    row = (extracted_json, dt.datetime(2026, 7, 11, 20, 0, 0), "Mohawk", False)
    cur = FakeCursor([row, (0,)])
    extracted, signals = _load_gate_signals(cur, "cid")
    assert set(signals["start_times"]) == {"2026-07-11T20:00:00", "2026-07-11T21:30:00"}


def test_single_start_time_is_not_a_conflict():
    extracted_json = {"start_time": "2026-07-11T20:00:00"}
    row = (extracted_json, dt.datetime(2026, 7, 11, 20, 0, 0), "Mohawk", False)
    cur = FakeCursor([row, (0,)])
    extracted, signals = _load_gate_signals(cur, "cid")
    # Both sources agree -> one distinct value.
    assert len(set(signals["start_times"])) == 1


def test_dedupe_ambiguous_true_when_sibling_candidate_shares_slot():
    extracted_json = {"start_time": "2026-07-11T20:00:00"}
    row = (extracted_json, dt.datetime(2026, 7, 11, 20, 0, 0), "Mohawk", False)
    cur = FakeCursor([row, (2,)])  # 2 other candidates at same venue+start
    extracted, signals = _load_gate_signals(cur, "cid")
    assert signals["dedupe_ambiguous"] is True
