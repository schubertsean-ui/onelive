"""The run's wall-clock budget and its page counter (R-092).

Two smoke runs on the consolidated head produced NO page count and NO
segmentation line anywhere in ~400 log lines, so multi-page ingestion was
unobservable in production. And with one cap-saturated source measured at
~200s, ~18 of them fill a 60-minute job while the scheduled cap is 30 — at
which point the runner kills the job mid-source and the RunReport is never
printed at all. A run that stops itself and SAYS how much it left is strictly
better than one that vanishes.
"""
import os
from datetime import datetime, timedelta, timezone

import pytest

from worker.orchestrator import _COUNT_KEYS, _run_deadline


def test_the_report_shape_carries_both_new_measures():
    """Declared up front so a zero is 'measured zero', not 'not tracked'."""
    assert "pages_fetched" in _COUNT_KEYS
    assert "sources_skipped_time_budget" in _COUNT_KEYS


def test_default_budget_sits_under_the_job_timeout():
    """ingest.yml declares timeout-minutes: 60. The budget must stop the loop
    BEFORE that, or it buys nothing."""
    started = datetime(2026, 8, 6, 0, 0, tzinfo=timezone.utc)
    deadline = _run_deadline(started.isoformat())
    assert deadline is not None
    margin = timedelta(minutes=60) - (deadline - started)
    assert margin >= timedelta(minutes=10), (
        "the default run budget leaves too little headroom under the 60-minute "
        f"job timeout (margin {margin})")


def test_env_override_is_honoured(monkeypatch):
    monkeypatch.setenv("INGEST_RUN_BUDGET_SECONDS", "120")
    started = datetime(2026, 8, 6, 0, 0, tzinfo=timezone.utc)
    assert _run_deadline(started.isoformat()) == started + timedelta(seconds=120)


def test_a_garbled_value_falls_back_to_the_default_rather_than_disabling(monkeypatch):
    """Fail-closed: a typo must never silently mean 'no budget'."""
    monkeypatch.setenv("INGEST_RUN_BUDGET_SECONDS", "sixty")
    started = datetime(2026, 8, 6, 0, 0, tzinfo=timezone.utc)
    deadline = _run_deadline(started.isoformat())
    assert deadline is not None and deadline > started


@pytest.mark.parametrize("raw", ["0", "-1"])
def test_budget_can_be_disabled_but_only_explicitly(monkeypatch, raw):
    """Disabling is allowed — it is how a long backfill-style dispatch runs —
    but it takes an explicit non-positive value, and the code logs what that
    costs rather than doing it quietly."""
    monkeypatch.setenv("INGEST_RUN_BUDGET_SECONDS", raw)
    assert _run_deadline(datetime.now(timezone.utc).isoformat()) is None
