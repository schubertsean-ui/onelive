"""Tests for the orchestrator Loop (worker/orchestrator.py).

Fully hermetic: fetch_url, extract_candidate, list_candidate_source_classes,
and load_candidate_gate_signals are monkeypatched to fake, in-memory
implementations — no network, no DB. The replay log is redirected to tmp_path
so no test writes into the repo's real var/replay directory.

The orchestrator NEVER promotes (promotion is an authenticated ops action), so
there is deliberately no promote_candidate fake here: a PASS candidate is left
"ready_to_promote" and these tests assert that it is NOT auto-published.
"""
import ast
import os

import pytest

import worker.orchestrator as orchestrator
from worker.orchestrator import GateDecision, RunReport, run_loop


class FakeAIProvider:
    """Minimal stand-in for AIProvider; orchestrator never calls this
    directly (extract_candidate is monkeypatched below), but run_loop's
    signature requires an `ai` object, so this documents the contract."""

    def extract_event_json(self, text, schema_json, system_prompt=None):
        raise AssertionError("extract_event_json should not be called; extract_candidate is faked in tests")


@pytest.fixture(autouse=True)
def redirect_replay_log(tmp_path, monkeypatch):
    monkeypatch.setenv("ONELIVE_REPLAY_LOG_DIR", str(tmp_path / "replay"))
    yield


def _source(name, source_class="social", url=None, source_id=None):
    return {
        "source_id": source_id or f"src-{name}",
        "name": name,
        "url": url or f"https://example.com/{name}",
        "source_class": source_class,
    }


def _install_fakes(
    monkeypatch,
    *,
    fetch_by_source=None,
    text_by_source=None,
    candidate_classes_by_candidate=None,
    extracted_by_candidate=None,
    evidence_signals_by_candidate=None,
):
    """Wire fake fetch/extract/store functions into the orchestrator module's
    namespace. Each *_by_* dict is keyed by source name (fetch/text) or by the
    fake candidate_id (classes/extracted/evidence_signals).

    extracted_by_candidate / evidence_signals_by_candidate stand in for the REAL
    DB read the orchestrator now performs via load_candidate_gate_signals — the
    orchestrator looks the signals up BY CANDIDATE ID, never from a per-source
    "_extracted_for_test" shortcut, so these fakes prove the stored-signal wiring.
    """
    fetch_by_source = fetch_by_source or {}
    text_by_source = text_by_source or {}
    candidate_classes_by_candidate = candidate_classes_by_candidate or {}
    extracted_by_candidate = extracted_by_candidate or {}
    evidence_signals_by_candidate = evidence_signals_by_candidate or {}

    written_files = {}
    stamped = []  # (candidate_id, status, gate_reason, required_next) records

    def fake_fetch_url(*, source_id, url, **kwargs):
        # Find the source name embedded in the url (our _source() helper
        # builds predictable urls) to look up the canned fetch result.
        name = url.rsplit("/", 1)[-1]
        result = fetch_by_source.get(name)
        if result is None:
            raise AssertionError(f"no fake fetch result registered for source url {url!r}")
        if result.get("status") == "ok":
            text = text_by_source.get(name, "")
            path = written_files.setdefault(name, str(pytest_tmp_file(name, text)))
            result = dict(result)
            result["storage_ref"] = path
        return result

    def fake_extract_candidate(*, ai, text, source_class, source_name, source_url, sxsw_mode=False, source_id=None):
        return f"candidate-{source_name}"

    def fake_list_candidate_source_classes(candidate_id):
        return candidate_classes_by_candidate.get(candidate_id, [])

    def fake_load_candidate_gate_signals(candidate_id, cur=None):
        extracted = extracted_by_candidate.get(candidate_id, {})
        evidence_signals = evidence_signals_by_candidate.get(
            candidate_id, {"start_times": [], "dedupe_ambiguous": False}
        )
        return extracted, evidence_signals

    def fake_stamp_gate_verdict(candidate_id, *, status, gate_reason,
                                required_next, expected_status, cur=None):
        assert expected_status == "needs_review"  # gate3 stamps only fresh rows
        stamped.append((candidate_id, status, gate_reason, required_next))
        return True

    monkeypatch.setattr(orchestrator, "stamp_gate_verdict", fake_stamp_gate_verdict)
    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(orchestrator, "extract_candidate", fake_extract_candidate)
    monkeypatch.setattr(orchestrator, "list_candidate_source_classes", fake_list_candidate_source_classes)
    monkeypatch.setattr(orchestrator, "load_candidate_gate_signals", fake_load_candidate_gate_signals)
    return stamped


def pytest_tmp_file(name, text):
    import tempfile

    fd, path = tempfile.mkstemp(prefix=f"onelive_test_{name}_")
    with os.fdopen(fd, "wb") as f:
        f.write(text.encode("utf-8"))
    return path


# --------------------------------------------------------------------------
# Happy path / counts
# --------------------------------------------------------------------------

def test_three_source_run_produces_correct_counts(monkeypatch):
    sources = [
        _source("anchor_src", source_class="ticketing"),
        _source("weak_src", source_class="social"),
        _source("junk_src", source_class="blog"),
    ]

    _install_fakes(
        monkeypatch,
        fetch_by_source={
            "anchor_src": {"status": "ok", "content_type": "text/plain"},
            "weak_src": {"status": "ok", "content_type": "text/plain"},
            "junk_src": {"status": "ok", "content_type": "text/plain"},
        },
        text_by_source={
            "anchor_src": "A real listing blurb with plenty of descriptive text content here.",
            "weak_src": "Another real listing blurb with plenty of descriptive text content.",
            "junk_src": "x",  # too short -> sensor rejects
        },
        candidate_classes_by_candidate={
            "candidate-anchor_src": ["ticketing"],
            "candidate-weak_src": ["social"],
        },
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources)

    assert isinstance(report, RunReport)
    assert report.counts["fetched"] == 3
    assert report.counts["sensor_rejected"] == 1
    assert report.counts["extracted"] == 2
    assert report.counts["passed"] == 1     # anchor_src: PASS -> ready_to_promote (never auto-published)
    assert report.counts["held"] == 1       # weak_src: single non-anchor -> HOLD
    assert report.counts["errors"] == 0
    assert len(report.results) == 3

    anchor = next(r for r in report.results if r.source_name == "anchor_src")
    assert anchor.decision == "ready_to_promote"


def test_not_modified_source_is_tracked_and_skips_rest_of_loop(monkeypatch):
    sources = [_source("cached_src")]
    _install_fakes(
        monkeypatch,
        fetch_by_source={"cached_src": {"status": "not_modified"}},
    )
    report = run_loop(ai=FakeAIProvider(), sources=sources)
    assert report.counts["not_modified"] == 1
    assert report.counts["fetched"] == 0
    assert report.results[0].decision == "not_modified"


# --------------------------------------------------------------------------
# The foundational invariant: the loop NEVER auto-promotes
# --------------------------------------------------------------------------

def test_pass_candidate_is_left_unpromoted_for_ops(monkeypatch):
    # A single anchor (ticketing) source is promotable by count and clean, so
    # the gate returns PASS. Before this fix the loop would auto-promote it; now
    # it must be LEFT for an authenticated ops action — never auto-published.
    sources = [_source("anchor_src", source_class="ticketing")]
    _install_fakes(
        monkeypatch,
        fetch_by_source={"anchor_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"anchor_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-anchor_src": ["ticketing"]},
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources)

    assert report.counts["passed"] == 1
    result = report.results[0]
    assert result.decision == "ready_to_promote"
    assert result.stage_reached == "gate3"  # stopped at the gate, never reached a promote stage
    assert "ops" in result.detail.lower()


def test_orchestrator_never_imports_or_calls_promote():
    # Structural guarantee: the module cannot auto-publish because it does not
    # import worker.promote at all and exposes no promote symbol. "AI never
    # auto-promotes" is enforced by the ABSENCE of the call path, not a flag.
    assert not hasattr(orchestrator, "promote_candidate")

    tree = ast.parse(open(orchestrator.__file__).read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not any(m.startswith("worker.promote") for m in imported)


def test_run_loop_has_no_promote_parameter():
    import inspect

    assert "promote" not in inspect.signature(run_loop).parameters


# --------------------------------------------------------------------------
# Per-source error isolation
# --------------------------------------------------------------------------

def test_transient_error_in_one_source_does_not_abort_others(monkeypatch):
    sources = [
        _source("broken_src"),
        _source("good_src", source_class="ticketing"),
    ]

    def fake_fetch_url(*, source_id, url, **kwargs):
        if "broken_src" in url:
            raise ConnectionError("simulated transient network failure")
        return {"status": "ok", "content_type": "text/plain", "storage_ref": pytest_tmp_file(
            "good_src", "A perfectly fine real listing blurb with enough text content."
        )}

    def fake_extract_candidate(*, ai, text, source_class, source_name, source_url, sxsw_mode=False, source_id=None):
        return f"candidate-{source_name}"

    def fake_list_candidate_source_classes(candidate_id):
        return ["ticketing"] if "good_src" in candidate_id else []

    def fake_load_candidate_gate_signals(candidate_id, cur=None):
        return {}, {"start_times": [], "dedupe_ambiguous": False}

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(orchestrator, "extract_candidate", fake_extract_candidate)
    monkeypatch.setattr(orchestrator, "list_candidate_source_classes", fake_list_candidate_source_classes)
    monkeypatch.setattr(orchestrator, "load_candidate_gate_signals", fake_load_candidate_gate_signals)
    monkeypatch.setattr(orchestrator, "stamp_gate_verdict",
                        lambda candidate_id, **kw: True)

    report = run_loop(ai=FakeAIProvider(), sources=sources)

    assert report.counts["errors"] == 1
    assert report.counts["fetched"] == 1
    assert report.counts["passed"] == 1
    assert len(report.results) == 2

    broken_result = next(r for r in report.results if r.source_name == "broken_src")
    assert broken_result.decision == "error"
    assert broken_result.stage_reached == "error"
    assert "ConnectionError" in broken_result.detail

    good_result = next(r for r in report.results if r.source_name == "good_src")
    assert good_result.decision == "ready_to_promote"


def test_error_isolation_writes_replay_step(monkeypatch, tmp_path):
    sources = [_source("broken_src")]

    def fake_fetch_url(*, source_id, url, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)

    report = run_loop(ai=FakeAIProvider(), sources=sources)
    assert report.counts["errors"] == 1

    replay_dir = tmp_path / "replay"
    log_file = replay_dir / f"{report.run_id}.jsonl"
    assert log_file.exists()
    content = log_file.read_text()
    assert '"stage": "error"' in content or '"stage":"error"' in content.replace(" ", "")


# --------------------------------------------------------------------------
# Finding 3: REAL stored extraction/evidence signals gate the decision.
# No "_extracted_for_test" shortcut — signals are looked up by candidate id via
# the (faked) load_candidate_gate_signals seam the real code reads the DB with.
# A promotable-by-count anchor MUST NOT reach PASS when the stored signals are
# unsafe.
# --------------------------------------------------------------------------

def test_private_rsvp_from_stored_extraction_escalates_even_with_anchor(monkeypatch):
    sources = [_source("rsvp_src", source_class="claimed_upload")]
    _install_fakes(
        monkeypatch,
        fetch_by_source={"rsvp_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"rsvp_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-rsvp_src": ["claimed_upload"]},
        extracted_by_candidate={"candidate-rsvp_src": {"is_private_rsvp": True}},
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources)
    assert report.counts["passed"] == 0
    assert report.counts["escalated"] == 1
    assert report.results[0].decision == "escalated"


def test_validation_error_provenance_from_stored_extraction_escalates(monkeypatch):
    sources = [_source("bad_src", source_class="ticketing")]
    _install_fakes(
        monkeypatch,
        fetch_by_source={"bad_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"bad_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-bad_src": ["ticketing"]},
        extracted_by_candidate={"candidate-bad_src": {"_provenance": {"validation_error": True}}},
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources)
    assert report.counts["passed"] == 0
    assert report.counts["escalated"] == 1
    assert "validation_error" in report.results[0].detail


def test_conflicting_start_times_from_stored_evidence_escalates(monkeypatch):
    sources = [_source("conflict_src", source_class="ticketing")]
    _install_fakes(
        monkeypatch,
        fetch_by_source={"conflict_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"conflict_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-conflict_src": ["ticketing"]},
        evidence_signals_by_candidate={
            "candidate-conflict_src": {
                "start_times": ["2026-07-11T20:00:00", "2026-07-11T21:30:00"],
                "dedupe_ambiguous": False,
            }
        },
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources)
    assert report.counts["passed"] == 0
    assert report.counts["escalated"] == 1
    assert "conflicting start_time" in report.results[0].detail


def test_dedupe_ambiguous_from_stored_evidence_escalates(monkeypatch):
    sources = [_source("dupe_src", source_class="festival_feed")]
    _install_fakes(
        monkeypatch,
        fetch_by_source={"dupe_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"dupe_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-dupe_src": ["festival_feed"]},
        evidence_signals_by_candidate={
            "candidate-dupe_src": {"start_times": [], "dedupe_ambiguous": True}
        },
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources)
    assert report.counts["passed"] == 0
    assert report.counts["escalated"] == 1


def test_run_report_shape_has_all_declared_count_keys():
    report = run_loop(ai=FakeAIProvider(), sources=[])
    for key in ("fetched", "extracted", "passed", "escalated", "held", "sensor_rejected", "errors"):
        assert key in report.counts
    assert report.results == []
    assert report.run_id


# GateDecision re-exported for callers/tests that want the enum from here.
def test_gate_decision_enum_is_exported():
    assert GateDecision.PASS.value == "pass"


# --------------------------------------------------------------------------
# Gate-verdict persistence (2026-08-05): the verdict must land on the ROW,
# not only in the replay log — the stranded-backlog diagnosis.
# --------------------------------------------------------------------------
def test_pass_candidate_row_is_stamped_ready_to_promote(monkeypatch):
    sources = [_source("anchor_src", source_class="ticketing")]
    stamped = _install_fakes(
        monkeypatch,
        fetch_by_source={"anchor_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"anchor_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-anchor_src": ["ticketing"]},
    )
    run_loop(ai=FakeAIProvider(), sources=sources)
    assert [(cid, status) for cid, status, _, _ in stamped] == [
        ("candidate-anchor_src", "ready_to_promote")
    ]


def test_hold_candidate_row_is_stamped_needs_more_confirmation(monkeypatch):
    sources = [_source("weak_src", source_class="blog")]
    stamped = _install_fakes(
        monkeypatch,
        fetch_by_source={"weak_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"weak_src": "Another real listing blurb with plenty of descriptive text content."},
        candidate_classes_by_candidate={"candidate-weak_src": ["blog"]},
    )
    run_loop(ai=FakeAIProvider(), sources=sources)
    (cid, status, reason, required_next) = stamped[0]
    assert status == "needs_more_confirmation"
    assert "Insufficient corroboration" in reason
    assert required_next  # the human-actionable next step travels with the row


def test_escalate_candidate_row_stays_needs_review_with_reason(monkeypatch):
    sources = [_source("private_src", source_class="ticketing")]
    stamped = _install_fakes(
        monkeypatch,
        fetch_by_source={"private_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"private_src": "A private RSVP listing blurb with plenty of descriptive text content."},
        candidate_classes_by_candidate={"candidate-private_src": ["ticketing"]},
        extracted_by_candidate={"candidate-private_src": {"is_private_rsvp": True}},
    )
    run_loop(ai=FakeAIProvider(), sources=sources)
    (cid, status, reason, required_next) = stamped[0]
    assert status == "needs_review"
    assert reason  # escalation reason recorded so the sweep can skip it
    assert "escalated" in required_next
