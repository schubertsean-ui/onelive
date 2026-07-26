"""The scorecard: each source's status DERIVED from evidence, and its trend.

Founder directive 2026-07-26: sources scored on tried / working / remediation /
volume, with improvements tracked over time as an ongoing measure. The
registry that enumerates the sources is a separate change; this file pins the
distinctions the scoring must never collapse — chiefly that "no evidence" and
"broken" are different answers, and that delivered rows outrank any assumption
about a credential.
"""
import json
import pathlib
import re

import pytest

import tools.source_scorecard as sc
from worker.sources.taxonomy import SOURCE_CLASSES

REPO = pathlib.Path(__file__).resolve().parent.parent


# ---- the scorecard -----------------------------------------------------------

ENTRY = {"id": "s1", "name": "S1", "source_class": "venue_calendar"}


def _score(entry, rows, attempts, evidence=True):
    ev, ven, owners = sc._index_rows(rows)
    att = sc._index_attempts(attempts)
    return sc.score_source(entry, ev, ven, owners, att, evidence)


def test_no_evidence_is_UNKNOWN_not_broken():
    """'We have not measured this' and 'this is broken' are different facts with
    different remediations, and collapsing them is how a working source gets
    retired."""
    out = _score(ENTRY, [], [], evidence=False)
    assert out["status"] == sc.STATUS_UNKNOWN
    assert out["tried"] is None and out["working"] is None
    assert "No evidence" in out["remediation"]


def test_never_tried_is_distinguished_from_tried_and_failing():
    never = _score(ENTRY, [], [])
    assert never["status"] == sc.STATUS_NEVER_TRIED
    failing = _score(ENTRY, [], [{"source_name": "s1", "ok": False}])
    assert failing["status"] == sc.STATUS_TRIED_FAILING
    empty = _score(ENTRY, [], [{"source_name": "s1", "ok": True}])
    assert empty["status"] == sc.STATUS_TRIED_EMPTY


def test_a_missing_credential_is_its_own_status_with_a_founder_action():
    out = _score({**ENTRY, "needs_credential": True, "credential_present": False},
                 [], [])
    assert out["status"] == sc.STATUS_BLOCKED_CREDENTIAL
    assert "mints" in out["remediation"]


def test_delivered_rows_OUTRANK_any_assumption_about_the_credential():
    """A credentialed source with rows in the store is WORKING, full stop.

    Nothing populates `credential_present`, so it is None for every source. The
    status ladder used to test the credential FIRST and `not None` is true, so
    every credentialed source — Ticketmaster included, with live rows — scored
    BLOCKED_CREDENTIAL and was handed a 'mint the key' action for a key that
    already works.
    """
    entry = {**ENTRY, "needs_credential": True, "credential_present": None}
    out = _score(entry, [{"source_name": "s1", "venue_name": "Mohawk"}],
                 [{"source_name": "s1", "ok": True}])
    assert out["status"] == sc.STATUS_WORKING
    assert out["remediation"] == ""


def test_an_UNKNOWN_credential_state_is_not_evidence_of_a_missing_key():
    """None means 'we did not check'. Reading it as 'absent' fabricates a
    founder action; reading it as 'present' fabricates health. With no attempt
    on record the honest answer is that nobody has tried it."""
    entry = {**ENTRY, "needs_credential": True, "credential_present": None}
    assert _score(entry, [], [])["status"] == sc.STATUS_NEVER_TRIED


def test_a_credentialed_source_that_was_attempted_is_scored_on_the_attempt():
    entry = {**ENTRY, "needs_credential": True, "credential_present": None}
    out = _score(entry, [], [{"source_name": "s1", "ok": False}])
    assert out["status"] == sc.STATUS_TRIED_FAILING


def test_supplied_but_EMPTY_evidence_is_a_measurement_not_an_absence(tmp_path):
    """A database read that legitimately returns nothing must report the
    measured state. Deriving evidence-presence from file CONTENTS made a real
    zero indistinguishable from never having run — so the scorecard could never
    report a genuinely empty pipeline, the state it most needs to report."""
    rows = tmp_path / "rows.json"
    attempts = tmp_path / "attempts.json"
    rows.write_text("[]", encoding="utf-8")
    attempts.write_text("[]", encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"sources": [
        {**ENTRY, "needs_credential": False}]}), encoding="utf-8")

    assert sc.main(["--registry", str(registry), "--rows", str(rows),
                    "--attempts", str(attempts)]) == 0
    scored = sc.score_source({**ENTRY, "needs_credential": False},
                             {}, {}, {}, {}, True)
    assert scored["status"] == sc.STATUS_NEVER_TRIED, (
        "an empty-but-supplied dump must score NEVER_TRIED, not UNKNOWN")


def test_every_non_working_status_yields_a_next_action():
    """A row that says 'broken' and stops is a complaint, not a work item."""
    for status, text in sc.REMEDIATION_BY_STATUS.items():
        if status != sc.STATUS_WORKING:
            assert text, status


def test_unique_venues_credits_reach_no_other_source_provides():
    """Ranking on event volume alone would retire the four-venue first-party
    feeds the long-tail strategy depends on."""
    rows = [{"source_name": "big", "venue_name": "Shared Room"}] * 50 + [
        {"source_name": "small", "venue_name": "Shared Room"},
        {"source_name": "small", "venue_name": "Only Here"},
    ]
    big = _score({"id": "big", "name": "big", "source_class": "ticketing_api"},
                 rows, [{"source_name": "big", "ok": True}])
    small = _score({"id": "small", "name": "small", "source_class": "venue_calendar"},
                   rows, [{"source_name": "small", "ok": True}])
    assert big["events"] > small["events"]        # bigger throughput
    assert big["unique_venues"] == 0              # but no reach of its own
    assert small["unique_venues"] == 1            # this is the value it adds


def test_yield_per_attempt_surfaces_a_source_that_costs_more_than_it_returns():
    out = _score(ENTRY, [{"source_name": "s1", "venue_name": "V"}],
                 [{"source_name": "s1", "ok": True}] * 40)
    assert out["yield_per_attempt"] == 0.03


def test_trend_counts_improvements_for_every_measure():
    prev = {"stamp": "t0", "sources": [
        {"id": "a", "status": sc.STATUS_TRIED_FAILING, "events": 0, "venues": 0,
         "unique_venues": 0, "attempts_ok": 0, "yield_per_attempt": 0.0}]}
    current = [{"id": "a", "status": sc.STATUS_WORKING, "events": 10, "venues": 2,
                "unique_venues": 1, "attempts_ok": 1, "yield_per_attempt": 10.0}]
    t = sc.diff_against(prev, current)
    for measure in sc.MEASURES:
        assert t["improved"][measure] == 1, measure
    assert t["status_improved"] == 1


def test_trend_also_counts_regressions_so_decay_is_visible():
    prev = {"stamp": "t0", "sources": [
        {"id": "a", "status": sc.STATUS_WORKING, "events": 10, "venues": 2,
         "unique_venues": 1, "attempts_ok": 5, "yield_per_attempt": 2.0}]}
    current = [{"id": "a", "status": sc.STATUS_TRIED_EMPTY, "events": 0, "venues": 0,
                "unique_venues": 0, "attempts_ok": 1, "yield_per_attempt": 0.0}]
    t = sc.diff_against(prev, current)
    assert t["regressed"]["events"] == 1
    assert t["status_improved"] == 0


