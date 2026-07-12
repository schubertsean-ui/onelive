"""Tests for the orchestrator Loop (worker/orchestrator.py).

Fully hermetic: fetch_url, extract_candidate, list_candidate_source_classes,
and promote_candidate are monkeypatched to fake, in-memory implementations —
no network, no DB. The replay log is redirected to tmp_path so no test writes
into the repo's real var/replay directory.
"""
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
    promote_side_effect_by_candidate=None,
):
    """Wire fake fetch/extract/store/promote functions into the orchestrator
    module's namespace. Each *_by_* dict is keyed by source name (fetch/text)
    or by the fake candidate_id (classes/extracted/promote).
    """
    fetch_by_source = fetch_by_source or {}
    text_by_source = text_by_source or {}
    candidate_classes_by_candidate = candidate_classes_by_candidate or {}
    extracted_by_candidate = extracted_by_candidate or {}
    promote_side_effect_by_candidate = promote_side_effect_by_candidate or {}

    written_files = {}

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

    def fake_promote_candidate(candidate_id):
        effect = promote_side_effect_by_candidate.get(candidate_id)
        if effect is not None:
            raise effect
        return f"event-{candidate_id}"

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(orchestrator, "extract_candidate", fake_extract_candidate)
    monkeypatch.setattr(orchestrator, "list_candidate_source_classes", fake_list_candidate_source_classes)
    monkeypatch.setattr(orchestrator, "promote_candidate", fake_promote_candidate)

    # extracted_for_test isn't read from candidate store in this module (see
    # orchestrator.py docstring); tests inject it via source["_extracted_for_test"].
    return extracted_by_candidate


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
    sources[0]["_extracted_for_test"] = {}
    sources[1]["_extracted_for_test"] = {}
    sources[2]["_extracted_for_test"] = {}

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

    report = run_loop(ai=FakeAIProvider(), sources=sources, promote=False)

    assert isinstance(report, RunReport)
    assert report.counts["fetched"] == 3
    assert report.counts["sensor_rejected"] == 1
    assert report.counts["extracted"] == 2
    assert report.counts["passed"] == 1     # anchor_src: PASS, promote=False -> would_promote
    assert report.counts["held"] == 1       # weak_src: single non-anchor -> HOLD
    assert report.counts["errors"] == 0
    assert len(report.results) == 3


def test_not_modified_source_is_tracked_and_skips_rest_of_loop(monkeypatch):
    sources = [_source("cached_src")]
    _install_fakes(
        monkeypatch,
        fetch_by_source={"cached_src": {"status": "not_modified"}},
    )
    report = run_loop(ai=FakeAIProvider(), sources=sources, promote=False)
    assert report.counts["not_modified"] == 1
    assert report.counts["fetched"] == 0
    assert report.results[0].decision == "not_modified"


# --------------------------------------------------------------------------
# Per-source error isolation
# --------------------------------------------------------------------------

def test_transient_error_in_one_source_does_not_abort_others(monkeypatch):
    sources = [
        _source("broken_src"),
        _source("good_src", source_class="ticketing"),
    ]
    sources[1]["_extracted_for_test"] = {}

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

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(orchestrator, "extract_candidate", fake_extract_candidate)
    monkeypatch.setattr(orchestrator, "list_candidate_source_classes", fake_list_candidate_source_classes)
    monkeypatch.setattr(orchestrator, "promote_candidate", lambda candidate_id: f"event-{candidate_id}")

    report = run_loop(ai=FakeAIProvider(), sources=sources, promote=False)

    assert report.counts["errors"] == 1
    assert report.counts["fetched"] == 1
    assert report.counts["passed"] == 1
    assert len(report.results) == 2

    broken_result = next(r for r in report.results if r.source_name == "broken_src")
    assert broken_result.decision == "error"
    assert broken_result.stage_reached == "error"
    assert "ConnectionError" in broken_result.detail

    good_result = next(r for r in report.results if r.source_name == "good_src")
    assert good_result.decision == "would_promote"


def test_error_isolation_writes_replay_step(monkeypatch, tmp_path):
    sources = [_source("broken_src")]

    def fake_fetch_url(*, source_id, url, **kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)

    report = run_loop(ai=FakeAIProvider(), sources=sources, promote=False)
    assert report.counts["errors"] == 1

    replay_dir = tmp_path / "replay"
    log_file = replay_dir / f"{report.run_id}.jsonl"
    assert log_file.exists()
    content = log_file.read_text()
    assert '"stage": "error"' in content or '"stage":"error"' in content.replace(" ", "")


# --------------------------------------------------------------------------
# promote=True path
# --------------------------------------------------------------------------

def test_promote_true_calls_promote_and_records_event(monkeypatch):
    sources = [_source("anchor_src", source_class="ticketing")]
    sources[0]["_extracted_for_test"] = {}

    _install_fakes(
        monkeypatch,
        fetch_by_source={"anchor_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"anchor_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-anchor_src": ["ticketing"]},
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources, promote=True)
    assert report.counts["passed"] == 1
    assert report.results[0].decision == "promoted"
    assert "event-candidate-anchor_src" in report.results[0].detail


def test_promote_true_duplicate_value_error_downgrades_to_escalate(monkeypatch):
    sources = [_source("dup_src", source_class="ticketing")]
    sources[0]["_extracted_for_test"] = {}

    _install_fakes(
        monkeypatch,
        fetch_by_source={"dup_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"dup_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-dup_src": ["ticketing"]},
        promote_side_effect_by_candidate={
            "candidate-dup_src": ValueError("Possible duplicate canonical events exist: [1]")
        },
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources, promote=True)

    assert report.counts["passed"] == 0
    assert report.counts["escalated"] == 1
    result = report.results[0]
    assert result.decision == "escalated"
    assert "duplicate" in result.detail.lower() or "promote raised" in result.detail.lower()


def test_promote_true_duplicate_error_never_crashes_loop(monkeypatch):
    # Same as above, but assert the run completes (does not raise) and other
    # sources after the duplicate still run.
    sources = [
        _source("dup_src", source_class="ticketing"),
        _source("clean_src", source_class="ticketing"),
    ]
    sources[0]["_extracted_for_test"] = {}
    sources[1]["_extracted_for_test"] = {}

    _install_fakes(
        monkeypatch,
        fetch_by_source={
            "dup_src": {"status": "ok", "content_type": "text/plain"},
            "clean_src": {"status": "ok", "content_type": "text/plain"},
        },
        text_by_source={
            "dup_src": "A real listing blurb with plenty of descriptive text content here.",
            "clean_src": "Another real listing blurb with plenty of descriptive text content.",
        },
        candidate_classes_by_candidate={
            "candidate-dup_src": ["ticketing"],
            "candidate-clean_src": ["ticketing"],
        },
        promote_side_effect_by_candidate={
            "candidate-dup_src": ValueError("duplicate"),
        },
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources, promote=True)
    assert report.counts["escalated"] == 1
    assert report.counts["passed"] == 1
    assert len(report.results) == 2


# --------------------------------------------------------------------------
# ESCALATE via trust_gate3 signals threaded through orchestrator
# --------------------------------------------------------------------------

def test_private_rsvp_escalates_even_with_anchor(monkeypatch):
    sources = [_source("rsvp_src", source_class="claimed_upload")]
    sources[0]["_extracted_for_test"] = {"is_private_rsvp": True}

    _install_fakes(
        monkeypatch,
        fetch_by_source={"rsvp_src": {"status": "ok", "content_type": "text/plain"}},
        text_by_source={"rsvp_src": "A real listing blurb with plenty of descriptive text content here."},
        candidate_classes_by_candidate={"candidate-rsvp_src": ["claimed_upload"]},
    )

    report = run_loop(ai=FakeAIProvider(), sources=sources, promote=True)
    assert report.counts["escalated"] == 1
    assert report.results[0].decision == "escalated"


def test_run_report_shape_has_all_declared_count_keys():
    report = run_loop(ai=FakeAIProvider(), sources=[])
    for key in ("fetched", "extracted", "passed", "escalated", "held", "sensor_rejected", "errors"):
        assert key in report.counts
    assert report.results == []
    assert report.run_id
