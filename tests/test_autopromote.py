"""Hermetic tests for worker/autopromote.py — the ratified earned-confidence
auto-promote pass (docs/memory/decisions/2026-07-25_auto-publish-earned-
confidence-ratification.md).

No network, no DB: a fake connection records every SQL call + bound params
(the tests/test_licensed_store.py pattern), promote_candidate is faked at the
autopromote module seam, and load_candidate_gate_signals is faked the same way
tests/test_orchestrator.py fakes it — the pass still runs the REAL
worker.trust_gate3.evaluate_gate and the REAL worker.publish_policy.decide_publish,
so these tests prove the wiring end to end, not a mock of the policy.

What must hold:
  * Flag off → the entire pass is a no-op: nothing read, nothing promoted.
  * Publish path: fresh gate PASS + ratified → promote_candidate is called
    and the outcome/audit record it.
  * Human-review paths (escalate, unreliable source, gate drift) leave the
    candidate's status untouched and record the reason.
  * Per-candidate exceptions are isolated: recorded, never marked promoted,
    and the pass continues to the next candidate.
  * Structural invariant: worker/orchestrator.py imports neither
    worker.autopromote nor worker.promote, and worker/autopromote.py is on
    trust_gate's promote-import allowlist (deliberate, not silent).
"""
import ast
import pathlib

import pytest

import worker.autopromote as autopromote
from worker.autopromote import AutopromoteReport, run_autopromote, stamp_backlog

REPO = pathlib.Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fakes: a scripted cursor/connection that answers the pass's real SQL shapes
# and records every execute + commit/rollback for assertions.
# ---------------------------------------------------------------------------

class _FakeCursor:
    def __init__(self, conn):
        self._conn = conn
        self._result = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self._conn.calls.append((" ".join(sql.split()), params))
        flat = " ".join(sql.split()).lower()
        if "from event_candidate" in flat and "status='ready_to_promote'" in flat:
            self._result = self._conn.candidate_rows[: params[0]]
        elif "from event_candidate" in flat and "gate_reason is null" in flat:
            self._result = self._conn.stamp_rows[: params[0]]
        elif "update event_candidate" in flat:
            self._result = []
            # CAS semantics: params[3] is candidate_id; the fake honors a
            # per-candidate stale set so tests can simulate a row that moved
            # between the sweep's select and the guarded update.
            self.rowcount = 0 if params[3] in self._conn.stale_candidates else 1
        elif "from candidate_evidence" in flat:
            self._result = [(c,) for c in self._conn.classes_by_candidate.get(params[0], [])]
        elif "from source_reliability" in flat:
            score = self._conn.reliability_by_source.get(params[0])
            self._result = [] if score is None else [(score,)]
        elif "insert into audit_log" in flat:
            self._result = []
        else:
            raise AssertionError(f"unscripted SQL reached the fake cursor: {flat!r}")

    def fetchall(self):
        return list(self._result)

    def fetchone(self):
        return self._result[0] if self._result else None


class _FakeConn:
    """Records SQL, commits, and rollbacks. candidate_rows are the
    (candidate_id, source_id, sxsw_mode) tuples the selection query returns."""

    def __init__(self, candidate_rows=None, classes_by_candidate=None,
                 reliability_by_source=None, stamp_rows=None):
        self.candidate_rows = candidate_rows or []
        self.stamp_rows = stamp_rows or []  # (candidate_id, sxsw_mode) for the sweep
        self.stale_candidates = set()  # ids whose guarded update matches 0 rows
        self.classes_by_candidate = classes_by_candidate or {}
        self.reliability_by_source = reliability_by_source or {}
        self.calls = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return _FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _RefuseAllConn:
    """A connection that fails the test if ANY DB access happens."""

    def cursor(self):
        raise AssertionError("flag-off pass must not touch the database")

    def commit(self):
        raise AssertionError("flag-off pass must not commit")


@pytest.fixture
def ratified(monkeypatch):
    monkeypatch.setenv("AUTO_PUBLISH_RATIFIED", "1")


def _fake_signals(monkeypatch, signals_by_candidate):
    """Fake the load_candidate_gate_signals seam (the same seam the
    orchestrator tests fake) with per-candidate (extracted, evidence_signals)."""

    def fake(candidate_id, cur=None):
        return signals_by_candidate.get(
            candidate_id, ({}, {"start_times": [], "dedupe_ambiguous": False})
        )

    monkeypatch.setattr(autopromote, "load_candidate_gate_signals", fake)


def _fake_promote(monkeypatch, *, raises_for=()):
    """Fake promote_candidate at the autopromote seam; records calls and can
    raise for chosen candidate ids to exercise isolation."""
    calls = []

    def fake(candidate_id):
        calls.append(candidate_id)
        if candidate_id in raises_for:
            raise ValueError(f"promotion refused: simulated for {candidate_id}")
        return f"event-for-{candidate_id}"

    monkeypatch.setattr(autopromote, "promote_candidate", fake)
    return calls


def _audit_actions(conn):
    return [(sql, params) for sql, params in conn.calls if "insert into audit_log" in sql.lower()]


def _status_updates(conn):
    return [sql for sql, _ in conn.calls if "update event_candidate" in sql.lower()]


# ---------------------------------------------------------------------------
# Fail-closed: flag off → total no-op
# ---------------------------------------------------------------------------

def test_flag_off_is_a_total_noop(monkeypatch):
    monkeypatch.delenv("AUTO_PUBLISH_RATIFIED", raising=False)
    promoted = _fake_promote(monkeypatch)
    report = run_autopromote(_RefuseAllConn(), limit=10)
    assert isinstance(report, AutopromoteReport)
    assert report.enabled is False
    assert report.counts == {"examined": 0, "promoted": 0, "human_review": 0, "errors": 0}
    assert report.outcomes == []
    assert promoted == []


def test_flag_off_logs_loudly(monkeypatch, caplog):
    monkeypatch.delenv("AUTO_PUBLISH_RATIFIED", raising=False)
    with caplog.at_level("WARNING"):
        run_autopromote(_RefuseAllConn(), limit=1)
    assert any("NO-OP" in r.message for r in caplog.records)


@pytest.mark.parametrize("bad_limit", [0, -3, "5", None, True])
def test_invalid_limit_fails_closed_before_any_work(monkeypatch, bad_limit):
    # limit is validated BEFORE the flag check / any DB access: a misconfigured
    # ceiling must raise even when the flag is off, never silently run.
    monkeypatch.delenv("AUTO_PUBLISH_RATIFIED", raising=False)
    with pytest.raises(ValueError):
        run_autopromote(_RefuseAllConn(), limit=bad_limit)


# ---------------------------------------------------------------------------
# Publish path: fresh PASS + ratified → promote_candidate
# ---------------------------------------------------------------------------

def test_pass_candidate_is_promoted_via_promote_candidate(monkeypatch, ratified):
    conn = _FakeConn(
        candidate_rows=[("cand-1", "src-1", False)],
        classes_by_candidate={"cand-1": ["ticketing"]},   # anchor → gate PASS
        reliability_by_source={"src-1": 0.9},
    )
    _fake_signals(monkeypatch, {})
    promoted = _fake_promote(monkeypatch)

    report = run_autopromote(conn, limit=5)

    assert promoted == ["cand-1"]
    assert report.enabled is True
    assert report.counts == {"examined": 1, "promoted": 1, "human_review": 0, "errors": 0}
    outcome = report.outcomes[0]
    assert outcome.action == "promoted" and outcome.event_id == "event-for-cand-1"
    # The publish decision is audited as a system action, and this module
    # itself never rewrites candidate status (promote_candidate owns that).
    audits = _audit_actions(conn)
    assert len(audits) == 1 and audits[0][1][0] == "autopromote_publish"
    assert _status_updates(conn) == []
    assert conn.commits == 1


def test_selection_query_is_bounded_and_targets_ready_to_promote(monkeypatch, ratified):
    conn = _FakeConn(candidate_rows=[])
    _fake_promote(monkeypatch)
    run_autopromote(conn, limit=7)
    sql, params = conn.calls[0]
    assert "status='ready_to_promote'" in sql
    assert "limit %s" in sql and params == (7,)


# ---------------------------------------------------------------------------
# Human-review paths: reason recorded, status untouched, promote never called
# ---------------------------------------------------------------------------

def test_escalate_candidate_left_for_human_review(monkeypatch, ratified):
    conn = _FakeConn(
        candidate_rows=[("cand-rsvp", "src-1", False)],
        classes_by_candidate={"cand-rsvp": ["ticketing"]},
        reliability_by_source={"src-1": 0.9},
    )
    # Private/RSVP in the stored extraction → fresh gate ESCALATE.
    _fake_signals(monkeypatch, {
        "cand-rsvp": ({"is_private_rsvp": True}, {"start_times": [], "dedupe_ambiguous": False}),
    })
    promoted = _fake_promote(monkeypatch)

    report = run_autopromote(conn, limit=5)

    assert promoted == []
    assert report.counts["human_review"] == 1 and report.counts["promoted"] == 0
    outcome = report.outcomes[0]
    assert outcome.action == "human_review" and "ESCALATE" in outcome.detail
    audits = _audit_actions(conn)
    assert len(audits) == 1 and audits[0][1][0] == "autopromote_skip"
    assert _status_updates(conn) == []


def test_unreliable_source_left_for_human_review(monkeypatch, ratified):
    conn = _FakeConn(
        candidate_rows=[("cand-u", "src-bad", False)],
        classes_by_candidate={"cand-u": ["ticketing"]},
        reliability_by_source={"src-bad": 0.10},  # below the 0.35 threshold
    )
    _fake_signals(monkeypatch, {})
    promoted = _fake_promote(monkeypatch)

    report = run_autopromote(conn, limit=5)

    assert promoted == []
    assert report.outcomes[0].action == "human_review"
    assert "unreliable" in report.outcomes[0].detail


def test_gate_drift_to_hold_is_not_force_published(monkeypatch, ratified):
    # decide_publish would publish a HOLD at 'unverified', but this pass's
    # population is gate-passed candidates and promote_candidate publishes
    # only PASS — a drifted candidate goes to a human, never past the guard.
    conn = _FakeConn(
        candidate_rows=[("cand-drift", "src-1", False)],
        classes_by_candidate={"cand-drift": ["local_media"]},  # single non-anchor → HOLD
        reliability_by_source={"src-1": 0.9},
    )
    _fake_signals(monkeypatch, {})
    promoted = _fake_promote(monkeypatch)

    report = run_autopromote(conn, limit=5)

    assert promoted == []
    outcome = report.outcomes[0]
    assert outcome.action == "human_review"
    assert "hold" in outcome.detail and "human review" in outcome.detail


def test_ungraded_source_uses_start_score_and_publishes_on_pass(monkeypatch, ratified):
    # No source_reliability row → the documented 0.5 start score (above the
    # threshold): ungraded is NOT the founder's graded-unreliable exception.
    conn = _FakeConn(
        candidate_rows=[("cand-new", "src-new", False)],
        classes_by_candidate={"cand-new": ["ticketing"]},
        reliability_by_source={},
    )
    _fake_signals(monkeypatch, {})
    promoted = _fake_promote(monkeypatch)
    report = run_autopromote(conn, limit=5)
    assert promoted == ["cand-new"]
    assert report.counts["promoted"] == 1


# ---------------------------------------------------------------------------
# Per-candidate isolation
# ---------------------------------------------------------------------------

def test_one_failing_candidate_never_marks_promoted_and_pass_continues(monkeypatch, ratified):
    conn = _FakeConn(
        candidate_rows=[("cand-bad", "src-1", False), ("cand-good", "src-1", False)],
        classes_by_candidate={"cand-bad": ["ticketing"], "cand-good": ["ticketing"]},
        reliability_by_source={"src-1": 0.9},
    )
    _fake_signals(monkeypatch, {})
    promoted = _fake_promote(monkeypatch, raises_for={"cand-bad"})

    report = run_autopromote(conn, limit=5)

    # Both were attempted; the failure is isolated and recorded, the good one
    # still publishes, and the failed one is never reported as promoted.
    assert promoted == ["cand-bad", "cand-good"]
    assert report.counts == {"examined": 2, "promoted": 1, "human_review": 0, "errors": 1}
    bad = next(o for o in report.outcomes if o.candidate_id == "cand-bad")
    assert bad.action == "error" and bad.event_id is None and "ValueError" in bad.detail
    good = next(o for o in report.outcomes if o.candidate_id == "cand-good")
    assert good.action == "promoted"
    # The failed candidate's transaction was rolled back and its failure audited.
    assert conn.rollbacks == 1
    error_audits = [p for _, p in _audit_actions(conn) if p[0] == "autopromote_error"]
    assert len(error_audits) == 1 and error_audits[0][1] == "cand-bad"


def test_signal_load_failure_is_isolated_too(monkeypatch, ratified):
    conn = _FakeConn(
        candidate_rows=[("cand-x", "src-1", False), ("cand-y", "src-1", False)],
        classes_by_candidate={"cand-x": ["ticketing"], "cand-y": ["ticketing"]},
        reliability_by_source={"src-1": 0.9},
    )

    def exploding_signals(candidate_id, cur=None):
        if candidate_id == "cand-x":
            raise RuntimeError("simulated stored-signal read failure")
        return {}, {"start_times": [], "dedupe_ambiguous": False}

    monkeypatch.setattr(autopromote, "load_candidate_gate_signals", exploding_signals)
    promoted = _fake_promote(monkeypatch)

    report = run_autopromote(conn, limit=5)
    assert promoted == ["cand-y"]
    assert report.counts["errors"] == 1 and report.counts["promoted"] == 1


# ---------------------------------------------------------------------------
# Structural trust invariants
# ---------------------------------------------------------------------------

def _imports_of(path: pathlib.Path) -> set:
    tree = ast.parse(path.read_text())
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def test_orchestrator_does_not_import_autopromote_or_promote():
    # The AI-extraction loop must stay structurally unable to reach the
    # promote path — directly (worker.promote) or through this new engine
    # (worker.autopromote). Enforced by absence, not by a flag.
    imported = _imports_of(REPO / "worker" / "orchestrator.py")
    assert not any(m.startswith("worker.autopromote") for m in imported)
    assert not any(m.startswith("worker.promote") for m in imported)


def test_run_once_entrypoint_does_not_import_autopromote():
    # The scheduled extraction entrypoint must not gain a publish side effect:
    # autopromote runs only through its own entrypoint (worker/run_autopromote.py).
    imported = _imports_of(REPO / "worker" / "run_once.py")
    assert not any(m.startswith("worker.autopromote") for m in imported)
    assert not any(m.startswith("worker.promote") for m in imported)


def test_autopromote_is_on_the_promote_import_allowlist():
    # The deliberate, reviewed pattern the guard demands (and the 2026-07-25
    # ratification record names): the new promoter is allowlisted explicitly,
    # and the orchestrator/its entrypoint remain absent.
    import tools.trust_gate as trust_gate

    assert "worker/autopromote.py" in trust_gate.PROMOTE_IMPORT_ALLOWLIST
    assert "worker/orchestrator.py" not in trust_gate.PROMOTE_IMPORT_ALLOWLIST
    assert "worker/run_once.py" not in trust_gate.PROMOTE_IMPORT_ALLOWLIST


def test_cli_entrypoint_requires_real_and_limit(monkeypatch, capsys):
    # --limit is mandatory and --real is required to do anything: the publish
    # entrypoint never starts by accident.
    import worker.run_autopromote as cli

    with pytest.raises(SystemExit):
        monkeypatch.setattr("sys.argv", ["run_autopromote.py"])
        cli.main()  # argparse exits: --limit is required

    with pytest.raises(SystemExit):
        monkeypatch.setattr("sys.argv", ["run_autopromote.py", "--limit", "5"])
        cli.main()  # argparse exits: --stamp-limit is required too

    monkeypatch.setattr("sys.argv", ["run_autopromote.py", "--limit", "5",
                                     "--stamp-limit", "100"])
    assert cli.main() == 2  # no --real → refuse, exit 2

    with pytest.raises(SystemExit):
        monkeypatch.setattr("sys.argv", ["run_autopromote.py", "--real", "--limit", "0"])
        cli.main()  # zero ceiling rejected by the argparse type (fail-closed)


# ---------------------------------------------------------------------------
# Gate-stamp sweep (2026-08-05): the never-stamped backlog gets the SAME gate
# verdicts persisted with the SAME column contract as the human ops action.
# ---------------------------------------------------------------------------

def _fake_load_gate_signals(monkeypatch, by_candidate):
    def fake(cur, candidate_id):
        return by_candidate.get(candidate_id, ({}, {"start_times": [], "dedupe_ambiguous": False}))
    monkeypatch.setattr(autopromote, "_load_gate_signals", fake)


def _stamp_updates(conn):
    return [(sql, params) for sql, params in conn.calls
            if "update event_candidate" in sql.lower()]


def test_stamp_sweep_targets_never_stamped_population(monkeypatch):
    conn = _FakeConn(stamp_rows=[])
    stamp_backlog(conn, limit=42)
    sql, params = conn.calls[0]
    flat = sql.lower()
    assert "status='needs_review'" in flat and "gate_reason is null" in flat
    assert "limit %s" in flat and params == (42,)


def test_stamp_anchor_candidate_becomes_ready_to_promote(monkeypatch):
    conn = _FakeConn(stamp_rows=[("c1", False)],
                     classes_by_candidate={"c1": ["ticketing"]})
    _fake_load_gate_signals(monkeypatch, {})
    report = stamp_backlog(conn, limit=10)
    assert report.counts == {"examined": 1, "stamped_ready": 1,
                             "stamped_hold": 0, "escalated": 0,
                             "skipped_stale": 0, "errors": 0}
    ((sql, params),) = _stamp_updates(conn)
    assert params[0] == "ready_to_promote" and params[3] == "c1"
    assert any("gate_stamp" in str(params) for _sql, params in _audit_actions(conn))


def test_stamp_single_weak_source_becomes_needs_more_confirmation(monkeypatch):
    conn = _FakeConn(stamp_rows=[("c2", False)],
                     classes_by_candidate={"c2": ["blog"]})
    _fake_load_gate_signals(monkeypatch, {})
    report = stamp_backlog(conn, limit=10)
    assert report.counts["stamped_hold"] == 1
    ((sql, params),) = _stamp_updates(conn)
    assert params[0] == "needs_more_confirmation"
    assert params[2]  # required_next carries the human-actionable step


def test_stamp_escalate_keeps_needs_review_and_records_reason(monkeypatch):
    conn = _FakeConn(stamp_rows=[("c3", False)],
                     classes_by_candidate={"c3": ["ticketing"]})
    _fake_load_gate_signals(monkeypatch, {
        "c3": ({"is_private_rsvp": True}, {"start_times": [], "dedupe_ambiguous": False}),
    })
    report = stamp_backlog(conn, limit=10)
    assert report.counts["escalated"] == 1
    ((sql, params),) = _stamp_updates(conn)
    assert params[0] == "needs_review"
    assert params[1]  # gate_reason set -> leaves the sweep population


def test_stamp_limit_zero_or_negative_is_rejected():
    conn = _FakeConn()
    for bad in (0, -5):
        with pytest.raises(ValueError):
            stamp_backlog(conn, limit=bad)
    assert conn.calls == []  # fail-closed before any DB work


def test_stamp_failure_is_isolated_and_counted(monkeypatch):
    conn = _FakeConn(stamp_rows=[("bad", False), ("good", False)],
                     classes_by_candidate={"good": ["ticketing"]})
    def fake(cur, candidate_id):
        if candidate_id == "bad":
            raise RuntimeError("simulated signal-load failure")
        return {}, {"start_times": [], "dedupe_ambiguous": False}
    monkeypatch.setattr(autopromote, "_load_gate_signals", fake)
    report = stamp_backlog(conn, limit=10)
    assert report.counts["errors"] == 1
    assert report.counts["stamped_ready"] == 1
    assert conn.rollbacks == 1


def test_stamp_skips_row_that_moved_mid_sweep_and_keeps_newer_state(monkeypatch):
    # Compare-and-swap (evaluator finding r2): a candidate that ops/dispute
    # moved between the sweep's select and the guarded update must be SKIPPED
    # (0 rows matched), counted, and never audited as stamped.
    conn = _FakeConn(stamp_rows=[("moved", False), ("fresh", False)],
                     classes_by_candidate={"moved": ["ticketing"],
                                           "fresh": ["ticketing"]})
    conn.stale_candidates = {"moved"}
    _fake_load_gate_signals(monkeypatch, {})
    report = stamp_backlog(conn, limit=10)
    assert report.counts["skipped_stale"] == 1
    assert report.counts["stamped_ready"] == 1
    assert conn.rollbacks == 1  # the missed CAS rolls back, sweep continues
    audited = [p for _s, p in _audit_actions(conn)]
    assert not any("moved" in str(p) for p in audited)
    assert any("fresh" in str(p) for p in audited)


def test_stamp_update_reasserts_selection_predicate_in_sql(monkeypatch):
    conn = _FakeConn(stamp_rows=[("c1", False)],
                     classes_by_candidate={"c1": ["ticketing"]})
    _fake_load_gate_signals(monkeypatch, {})
    stamp_backlog(conn, limit=10)
    ((sql, _params),) = _stamp_updates(conn)
    flat = " ".join(sql.split()).lower()
    assert "status='needs_review'" in flat and "gate_reason is null" in flat
