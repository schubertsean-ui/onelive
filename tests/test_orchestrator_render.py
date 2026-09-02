"""Tests for the orchestrator's JS-shell render fallback wiring
(worker/orchestrator.py <- worker/fetch/render_fetch.py).

Fully hermetic: fetch_url and render_html are monkeypatched on the
orchestrator module (the same seams tests/test_orchestrator.py uses for
fetch), extraction/store lookups are faked in-memory, and the replay log is
redirected to tmp_path. No network, no DB, no browser.

What must hold (the wiring contract):
- A plain fetch that the sensor flags as a boilerplate-only JS shell triggers
  exactly one headless render, and the RENDERED text is what flows onward to
  the sensor/extract path.
- A render failure (missing browser, timeout, ...) NEVER kills the source or
  the run: the plain result proceeds exactly as before the fallback existed
  (i.e. the shell is sensor-rejected, decision "sensor_rejected", not
  "error"), and the replay fetch entry records why.
- The per-run budget ONELIVE_MAX_RENDERS_PER_RUN is honored: the n+1th
  shell in a run does not attempt a render; 0 disables rendering entirely;
  a malformed value fails closed (run_loop raises before touching sources).
- The replay log's fetch entry records render usage without dropping any
  existing field.
"""
import json

import pytest

from worker.ai_extract import ExtractionOutcome
import worker.orchestrator as orchestrator
from worker.fetch.render_fetch import RenderError
from worker.orchestrator import run_loop

# A page that renders as a bare "please enable JavaScript" shell — what a
# JS-widget venue calendar returns to a plain requests.get. The sensor flags
# it boilerplate-only; that flag is the render trigger.
_JS_SHELL = "Please enable JavaScript. Your browser is not supported."

# What the headless browser recovers: substantive listing text the sensor
# passes. Ends on a terminator so no other sensor check fires.
_RENDERED_PAGE = (
    "Tonight at The Mohawk: doors 8pm, The Reverberations live on the outdoor "
    "stage, plus a late set from DJ Cass. Tickets at the door, all ages."
)

# A healthy plain page — must NEVER pay for a browser.
_REAL_PAGE = (
    "Friday at Hotel Vegas: two stages, four bands, doors at 7pm sharp and "
    "no cover before 8. Full lineup and set times on the chalkboard outside."
)


class FakeAIProvider:
    """run_loop's signature requires an `ai` object; extract_candidates is
    faked below so this must never actually be called."""

    def extract_event_json(self, text, schema_json, system_prompt=None):
        raise AssertionError("extract_event_json must not be called; extract_candidates is faked")


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("ONELIVE_REPLAY_LOG_DIR", str(tmp_path / "replay"))
    monkeypatch.delenv("ONELIVE_MAX_RENDERS_PER_RUN", raising=False)
    yield


def _source(name, source_class="ticketing"):
    return {
        "source_id": f"src-{name}",
        "name": name,
        "url": f"https://example.com/{name}",
        "source_class": source_class,
    }


def _install_fakes(monkeypatch, tmp_path, *, plain_text_by_source, extracted_texts=None):
    """Fake the fetch + extract + store seams on the orchestrator module.

    plain_text_by_source: source name -> the text the PLAIN fetch returns
    (written to a real tmp file so storage_ref/_read_fetched_text behave
    exactly as production). extracted_texts, when given, collects the text
    each extract_candidates call receives — proving WHICH content flowed
    onward (plain vs rendered).
    """

    def fake_fetch_url(*, source_id, url, **kwargs):
        name = url.rsplit("/", 1)[-1]
        text = plain_text_by_source[name]
        path = tmp_path / f"plain_{name}.html"
        path.write_text(text, encoding="utf-8")
        return {
            "status": "ok",
            "url": url,
            "storage_ref": str(path),
            "content_type": "text/html",
        }

    def fake_extract_candidates(*, ai, text, source_class, source_name, source_url, sxsw_mode=False, source_id=None):
        if extracted_texts is not None:
            extracted_texts.append(text)
        return ExtractionOutcome(candidate_ids=[f"candidate-{source_name}"])

    def fake_list_candidate_source_classes(candidate_id):
        return ["ticketing"]

    def fake_load_candidate_gate_signals(candidate_id, cur=None):
        return {}, {"start_times": [], "dedupe_ambiguous": False}

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(orchestrator, "extract_candidates", fake_extract_candidates)
    monkeypatch.setattr(orchestrator, "list_candidate_source_classes", fake_list_candidate_source_classes)
    monkeypatch.setattr(orchestrator, "load_candidate_gate_signals", fake_load_candidate_gate_signals)
    monkeypatch.setattr(orchestrator, "stamp_gate_verdict",
                        lambda candidate_id, **kw: True)


def _install_render(monkeypatch, render_calls, html=None, error=None):
    """Fake orchestrator.render_html: records each attempted render, then
    returns `html` or raises `error`."""

    def fake_render_html(*, url, timeout_ms, wait_selector, user_agent):
        render_calls.append(url)
        if error is not None:
            raise error
        return html

    monkeypatch.setattr(orchestrator, "render_html", fake_render_html)


def _replay_lines(tmp_path, run_id):
    log_file = tmp_path / "replay" / f"{run_id}.jsonl"
    assert log_file.exists(), "replay log must exist for every run"
    return [json.loads(line) for line in log_file.read_text().splitlines()]


# --------------------------------------------------------------------------
# Shell detected -> render attempted, rendered content flows onward
# --------------------------------------------------------------------------

def test_shell_triggers_render_and_rendered_text_flows_to_extraction(monkeypatch, tmp_path):
    render_calls, extracted_texts = [], []
    _install_fakes(
        monkeypatch, tmp_path,
        plain_text_by_source={"shell_src": _JS_SHELL},
        extracted_texts=extracted_texts,
    )
    _install_render(monkeypatch, render_calls, html=_RENDERED_PAGE)

    report = run_loop(ai=FakeAIProvider(), sources=[_source("shell_src")])

    assert render_calls == ["https://example.com/shell_src"], "shell must trigger exactly one render"
    # The RENDERED text — not the shell — reached extraction and the gate.
    assert extracted_texts == [_RENDERED_PAGE]
    assert report.counts["sensor_rejected"] == 0
    assert report.counts["extracted"] == 1
    assert report.counts["errors"] == 0
    assert report.results[0].decision == "ready_to_promote"  # gate ran on real content; still never auto-promoted


def test_healthy_page_never_pays_for_a_render(monkeypatch, tmp_path):
    render_calls = []
    _install_fakes(monkeypatch, tmp_path, plain_text_by_source={"real_src": _REAL_PAGE})
    _install_render(monkeypatch, render_calls, error=AssertionError("render must not fire for a healthy page"))

    report = run_loop(ai=FakeAIProvider(), sources=[_source("real_src")])

    assert render_calls == []
    assert report.counts["extracted"] == 1
    assert report.results[0].decision == "ready_to_promote"


# --------------------------------------------------------------------------
# Render failure -> fail-open to the plain result, exactly as today
# --------------------------------------------------------------------------

def test_render_failure_falls_back_to_plain_result_never_kills_the_run(monkeypatch, tmp_path):
    render_calls = []
    _install_fakes(monkeypatch, tmp_path, plain_text_by_source={"shell_src": _JS_SHELL})
    _install_render(
        monkeypatch, render_calls,
        error=RenderError("the `playwright` Python package is not installed"),
    )

    report = run_loop(ai=FakeAIProvider(), sources=[_source("shell_src")])

    assert render_calls, "the render must have been attempted"
    # NOT an error: the plain shell proceeds and is sensor-rejected exactly
    # as it was before the fallback existed. No fabricated content.
    assert report.counts["errors"] == 0
    assert report.counts["sensor_rejected"] == 1
    assert report.results[0].decision == "sensor_rejected"

    # The replay fetch entry records the failed render honestly.
    fetch_steps = [r for r in _replay_lines(tmp_path, report.run_id) if r["stage"] == "fetch"]
    assert len(fetch_steps) == 1
    assert "render fallback unavailable" in fetch_steps[0]["detail"]
    assert "RenderError" in fetch_steps[0]["detail"]


def test_render_failure_on_one_source_does_not_affect_others(monkeypatch, tmp_path):
    render_calls = []
    _install_fakes(
        monkeypatch, tmp_path,
        plain_text_by_source={"shell_src": _JS_SHELL, "real_src": _REAL_PAGE},
    )
    _install_render(monkeypatch, render_calls, error=RenderError("browser binary missing"))

    report = run_loop(
        ai=FakeAIProvider(),
        sources=[_source("shell_src"), _source("real_src")],
    )

    assert report.counts["errors"] == 0
    assert report.counts["sensor_rejected"] == 1
    assert report.counts["extracted"] == 1
    real = next(r for r in report.results if r.source_name == "real_src")
    assert real.decision == "ready_to_promote"


# --------------------------------------------------------------------------
# Budget: ONELIVE_MAX_RENDERS_PER_RUN
# --------------------------------------------------------------------------

def test_render_cap_honored_nplus1th_render_not_attempted(monkeypatch, tmp_path):
    monkeypatch.setenv("ONELIVE_MAX_RENDERS_PER_RUN", "2")
    render_calls = []
    shells = {f"shell_{i}": _JS_SHELL for i in range(3)}
    _install_fakes(monkeypatch, tmp_path, plain_text_by_source=shells)
    _install_render(monkeypatch, render_calls, html=_RENDERED_PAGE)

    report = run_loop(
        ai=FakeAIProvider(),
        sources=[_source(name) for name in ("shell_0", "shell_1", "shell_2")],
    )

    # Exactly cap renders attempted; the 3rd shell got NO render...
    assert len(render_calls) == 2
    assert render_calls == [
        "https://example.com/shell_0",
        "https://example.com/shell_1",
    ]
    # ...and proceeded as a plain shell (sensor-rejected), never an error.
    assert report.counts["extracted"] == 2
    assert report.counts["sensor_rejected"] == 1
    assert report.counts["errors"] == 0
    third = next(r for r in report.results if r.source_name == "shell_2")
    assert third.decision == "sensor_rejected"


def test_default_cap_is_five(monkeypatch, tmp_path):
    # Env unset (autouse fixture deletes it): 6 shells -> exactly 5 renders.
    render_calls = []
    shells = {f"shell_{i}": _JS_SHELL for i in range(6)}
    _install_fakes(monkeypatch, tmp_path, plain_text_by_source=shells)
    _install_render(monkeypatch, render_calls, html=_RENDERED_PAGE)

    report = run_loop(ai=FakeAIProvider(), sources=[_source(f"shell_{i}") for i in range(6)])

    assert len(render_calls) == 5
    assert report.counts["extracted"] == 5
    assert report.counts["sensor_rejected"] == 1


def test_cap_zero_disables_rendering_entirely(monkeypatch, tmp_path):
    monkeypatch.setenv("ONELIVE_MAX_RENDERS_PER_RUN", "0")
    render_calls = []
    _install_fakes(monkeypatch, tmp_path, plain_text_by_source={"shell_src": _JS_SHELL})
    _install_render(monkeypatch, render_calls, html=_RENDERED_PAGE)

    report = run_loop(ai=FakeAIProvider(), sources=[_source("shell_src")])

    assert render_calls == [], "cap=0 must mean zero render attempts"
    assert report.counts["sensor_rejected"] == 1
    assert report.counts["errors"] == 0


@pytest.mark.parametrize("bad_value", ["unlimited", "-3", "5.0", "0x10"])
def test_malformed_cap_fails_closed_before_touching_sources(monkeypatch, tmp_path, bad_value):
    monkeypatch.setenv("ONELIVE_MAX_RENDERS_PER_RUN", bad_value)
    fetch_calls = []

    def fake_fetch_url(*, source_id, url, **kwargs):
        fetch_calls.append(url)
        raise AssertionError("no source may be touched when the render budget is unvalidatable")

    monkeypatch.setattr(orchestrator, "fetch_url", fake_fetch_url)

    with pytest.raises(ValueError, match="ONELIVE_MAX_RENDERS_PER_RUN"):
        run_loop(ai=FakeAIProvider(), sources=[_source("shell_src")])
    assert fetch_calls == []


# --------------------------------------------------------------------------
# Replay audit trail records render usage (fields extended, none dropped)
# --------------------------------------------------------------------------

def test_replay_fetch_entry_records_render_usage(monkeypatch, tmp_path):
    render_calls = []
    _install_fakes(monkeypatch, tmp_path, plain_text_by_source={"shell_src": _JS_SHELL})
    _install_render(monkeypatch, render_calls, html=_RENDERED_PAGE)

    report = run_loop(ai=FakeAIProvider(), sources=[_source("shell_src")])

    steps = _replay_lines(tmp_path, report.run_id)
    fetch_steps = [r for r in steps if r["stage"] == "fetch"]
    assert len(fetch_steps) == 1
    entry = fetch_steps[0]
    # Every pre-existing replay field is still present...
    for field in ("run_id", "ts", "source_id", "source_name", "stage",
                  "inputs_digest", "outputs_digest", "decision", "detail"):
        assert field in entry, f"replay entry lost field {field!r}"
    assert entry["decision"] == "ok"
    # ...and the entry records that a render happened, and why.
    assert "js-shell rendered via headless browser" in entry["detail"]
    assert "boilerplate-only" in entry["detail"]  # the sensor reason we escalated on
    # The downstream sensor step judged the RENDERED text and passed it.
    sensor_steps = [r for r in steps if r["stage"] == "sensor"]
    assert len(sensor_steps) == 1
    assert sensor_steps[0]["decision"] == "sensor_passed"


def test_replay_fetch_entry_plain_path_unchanged(monkeypatch, tmp_path):
    render_calls = []
    _install_fakes(monkeypatch, tmp_path, plain_text_by_source={"real_src": _REAL_PAGE})
    _install_render(monkeypatch, render_calls, html=_RENDERED_PAGE)

    report = run_loop(ai=FakeAIProvider(), sources=[_source("real_src")])

    fetch_steps = [r for r in _replay_lines(tmp_path, report.run_id) if r["stage"] == "fetch"]
    assert len(fetch_steps) == 1
    assert fetch_steps[0]["decision"] == "ok"
    assert fetch_steps[0]["detail"] == "ok"  # no render noise on the plain path
