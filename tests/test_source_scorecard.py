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


def _score(entry, rows, attempts, evidence=True, have_rows=None,
           have_attempts=None):
    """`evidence` keeps the old single-flag shape for the tests that predate
    per-artifact custody; have_rows/have_attempts override it where a test
    needs to say WHICH artifact was supplied (r3)."""
    ev, ven, owners = sc._index_rows(rows)
    att = sc._index_attempts(attempts)
    return sc.score_source(
        entry, ev, ven, owners, att,
        evidence if have_rows is None else have_rows,
        evidence if have_attempts is None else have_attempts)


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
                             {}, {}, {}, {}, True, True)
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




# ---- r1 evaluator findings ---------------------------------------------------

def test_evidence_that_names_NO_registry_source_is_REFUSED():
    """r1 blocker: rows and attempts whose source_name was blank — or a typo,
    a stale name, a wrong namespace — were silently skipped. That excluded real
    delivered rows from a source's score, so a working source read as
    NEVER_TRIED: the scorecard reporting the exact false status it exists to
    prevent. Worse for attempts, where a dropped row turns a source we KNOW is
    broken into one we appear never to have touched."""
    known = {"mohawk_austin": "mohawk_austin", "Mohawk": "mohawk_austin"}
    with pytest.raises(SystemExit, match="name no registry source"):
        sc._index_rows([{"source_name": "", "venue_name": "X"}], known)
    with pytest.raises(SystemExit, match="name no registry source"):
        sc._index_rows([{"source_name": "mohawk_austn"}], known)   # typo
    with pytest.raises(SystemExit, match="never-tried"):
        sc._index_attempts([{"source_name": "gone_away", "ok": False}], known)
    # bound evidence still indexes normally
    events, _v, _o = sc._index_rows([{"source_name": "mohawk_austin"}], known)
    assert events["mohawk_austin"] == 1
    # r2: evidence logged under the DISPLAY NAME must resolve to the canonical
    # id. It used to pass validation and then vanish at scoring, because
    # score_source looks up strictly by id — the same false NEVER_TRIED via a
    # different route. The r1 fix had moved the defect, not removed it.
    assert sc._index_attempts([{"source_name": "Mohawk", "ok": True}],
                              known)["mohawk_austin"]["ok"] == 1
    ev, _v, _o = sc._index_rows([{"source_name": "Mohawk"}], known)
    assert ev["mohawk_austin"] == 1, (
        "evidence named by display name must be indexed under the canonical id")


def test_a_status_REGRESSION_moves_the_trend():
    """r1 blocker: the trend had status_improved and no status_regressed, so a
    source sliding from WORKING to TRIED_FAILING moved it by zero and read as
    'nothing happened'. A one-directional trend is flattering by construction —
    and counting decay is an explicit done-criterion this contract claimed."""
    prev = {"sources": [
        {"id": "a", "status": sc.STATUS_WORKING, "events": 10},
        {"id": "b", "status": sc.STATUS_NEVER_TRIED, "events": 0}]}
    now = [{"id": "a", "status": sc.STATUS_TRIED_FAILING, "events": 0},
           {"id": "b", "status": sc.STATUS_WORKING, "events": 5}]
    t = sc.diff_against(prev, now)
    assert t["status_regressed"] == 1, t
    assert t["status_improved"] == 1, t


def test_a_top_level_JSON_ARRAY_registry_does_not_crash(tmp_path, monkeypatch):
    """`reg.get(...)` resolves the method on reg BEFORE the default expression
    is evaluated, so the isinstance fallback never ran — a top-level array
    crashed instead of being read."""
    reg_file = tmp_path / "reg.json"
    reg_file.write_text(json.dumps(
        [{"id": "x", "name": "X", "source_class": "venue_calendar"}]),
        encoding="utf-8")
    assert sc.main(["--registry", str(reg_file)]) in (0, 1)


def test_a_registry_with_NO_sources_is_REFUSED(tmp_path):
    """r2 blocker: a dict with no `sources` key became [], and the tool printed
    a cheerful "0 source(s)" scorecard and exited 0. For a tool whose entire
    job is scoring every catalogued source, zero sources is a
    misconfiguration — a wrong path, a wrong shape, or a build that produced
    nothing — never a result."""
    for payload in ({}, {"sources": []}, []):
        f = tmp_path / "reg.json"
        f.write_text(json.dumps(payload), encoding="utf-8")
        assert sc.main(["--registry", str(f)]) == 2, payload


def test_evidence_by_DISPLAY_NAME_reaches_the_score(tmp_path):
    """The end-to-end version of the r2 blocker: a delivering source logged
    under its display name must not read as NEVER_TRIED."""
    reg_file = tmp_path / "reg.json"
    reg_file.write_text(json.dumps({"sources": [
        {"id": "mohawk_austin", "name": "Mohawk",
         "source_class": "venue_calendar"}]}), encoding="utf-8")
    rows_file = tmp_path / "rows.json"
    rows_file.write_text(json.dumps(
        [{"source_name": "Mohawk", "venue_name": "Mohawk"}]), encoding="utf-8")
    assert sc.main(["--registry", str(reg_file), "--rows", str(rows_file)]) == 0


# ---- r3: one global evidence bit collapsed two independent questions --------

def test_PARTIAL_evidence_does_not_answer_the_question_it_did_not_ask():
    """r3 blocker. `have_evidence` was ONE flag set when EITHER artifact was
    supplied, so:

      --attempts only  -> absent ROW evidence read as zero delivered rows
      --rows only      -> absent ATTEMPT evidence read as never-tried

    Each is "we did not look" reported as "we looked and found nothing" — the
    exact collapse this scorecard exists to prevent, committed by the scorecard
    itself. Custody is per-artifact now."""
    entry = {"id": "s", "name": "S", "source_class": "venue_calendar",
             "needs_credential": False}
    # attempts read, rows NOT read: whether it delivered is unanswered
    r = _score(entry, [], [{"source_name": "s", "ok": False}],
               have_rows=False, have_attempts=True)
    assert r["status"] == sc.STATUS_TRIED_FAILING
    assert r["working"] is None, "an unread rows artifact is not zero rows"

    # rows read and empty, attempts NOT read: never-tried would assert about a
    # log we never opened
    r = _score(entry, [], [], have_rows=True, have_attempts=False)
    assert r["status"] == sc.STATUS_UNKNOWN, r
    assert r["tried"] is None, "an unread attempts artifact is not zero attempts"

    # rows read and NON-empty settles it whatever else is missing
    r = _score(entry, [{"source_name": "s", "venue_name": "V"}], [],
               have_rows=True, have_attempts=False)
    assert r["status"] == sc.STATUS_WORKING


def test_a_registry_entry_with_NO_id_is_REFUSED(tmp_path):
    """Evidence and trend both bind to the id, so a row without one cannot be
    scored — only printed."""
    f = tmp_path / "reg.json"
    f.write_text(json.dumps({"sources": [
        {"name": "Nameless", "source_class": "venue_calendar"}]}),
        encoding="utf-8")
    assert sc.main(["--registry", str(f)]) == 2


def test_an_AMBIGUOUS_display_name_is_REFUSED(tmp_path):
    """A later entry silently overwriting an earlier alias credits evidence to
    the wrong source — one WORKING and another NEVER_TRIED off the same rows."""
    f = tmp_path / "reg.json"
    f.write_text(json.dumps({"sources": [
        {"id": "a", "name": "Shared", "source_class": "venue_calendar"},
        {"id": "b", "name": "Shared", "source_class": "venue_calendar"}]}),
        encoding="utf-8")
    assert sc.main(["--registry", str(f)]) == 2
    # a display name colliding with another row's ID is equally ambiguous
    f.write_text(json.dumps({"sources": [
        {"id": "a", "name": "A", "source_class": "venue_calendar"},
        {"id": "b", "name": "a", "source_class": "venue_calendar"}]}),
        encoding="utf-8")
    assert sc.main(["--registry", str(f)]) == 2


def test_a_DUPLICATE_id_in_the_registry_is_REFUSED(tmp_path):
    f = tmp_path / "reg.json"
    f.write_text(json.dumps({"sources": [
        {"id": "a", "name": "A", "source_class": "venue_calendar"},
        {"id": "a", "name": "A2", "source_class": "venue_calendar"}]}),
        encoding="utf-8")
    assert sc.main(["--registry", str(f)]) == 2


def test_a_CORRUPT_previous_snapshot_fails_the_trend():
    """A duplicate in history means the trend is computed against whichever row
    won — improvement and regression counts describing the wrong baseline."""
    prev = {"sources": [{"id": "a", "status": sc.STATUS_WORKING, "events": 5},
                        {"id": "a", "status": sc.STATUS_NEVER_TRIED,
                         "events": 0}]}
    with pytest.raises(SystemExit, match="twice"):
        sc.diff_against(prev, [{"id": "a", "status": sc.STATUS_WORKING,
                                "events": 5}])
