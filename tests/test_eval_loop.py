"""Hermetic tests for the eval/Kaizen loop (Layer 4).

Gate and sensor cases need NO ai/network/DB. Extraction cases are proven to be
reported as SKIPPED (never passed) when ai is None. A sabotage test flips one
expected decision and asserts the eval then reports a failure — proving the eval
can actually fail, not vacuously pass.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ai.eval_loop import (
    DEFAULT_CORPUS,
    CorpusError,
    format_report,
    load_corpus,
    run_eval,
)

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


# --- corpus loads + schema-validates -----------------------------------------
def test_corpus_loads_and_has_min_cases(corpus):
    assert len(corpus) >= 12
    kinds = {c["kind"] for c in corpus}
    assert kinds == {"gate", "sensor", "extraction"}


def test_every_case_has_required_keys_for_its_kind(corpus):
    for c in corpus:
        assert c["id"] and c["risk_note"] and c["added"]  # self-documenting
        if c["kind"] == "gate":
            assert isinstance(c["gate_input"]["source_classes"], list)
            assert c["expected_decision"] in ("pass", "hold", "escalate")
        elif c["kind"] == "sensor":
            assert isinstance(c["source_text"], str)
            assert isinstance(c["expected_sensor_ok"], bool)
        else:
            assert isinstance(c["source_text"], str)
            assert c["expected"] is None or isinstance(c["expected"], dict)


def test_has_control_case_per_kind(corpus):
    # A clean control per kind guards the over-suppression blind spot.
    assert any(c["kind"] == "gate" and c["expected_decision"] == "pass" for c in corpus)
    assert any(c["kind"] == "sensor" and c["expected_sensor_ok"] is True for c in corpus)
    assert any(c["kind"] == "extraction" for c in corpus)


def test_spans_documented_adversarial_classes(corpus):
    ids = " ".join(c["id"] for c in corpus)
    for token in ("cancelled", "contradictory", "stale", "private-rsvp", "dedupe",
                  "truncated", "mojibake", "injection", "boilerplate",
                  "single-non-anchor", "hallucination"):
        assert token in ids, f"missing adversarial class: {token}"


# --- malformed corpus fails LOUD (not silently skipped) ----------------------
def test_malformed_json_line_fails_loud(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"id": "ok", "kind": "sensor"} not-json\n', encoding="utf-8")
    with pytest.raises(CorpusError):
        load_corpus(p)


def test_missing_required_key_fails_loud(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text(json.dumps({"id": "x", "kind": "gate", "added": "2026-07-12"}) + "\n",
                 encoding="utf-8")
    with pytest.raises(CorpusError):
        load_corpus(p)  # missing risk_note + gate_input


def test_bad_expected_decision_fails_loud(tmp_path):
    p = tmp_path / "bad.jsonl"
    case = {"id": "x", "kind": "gate", "risk_note": "r", "added": "2026-07-12",
            "gate_input": {"source_classes": ["ticketing"]},
            "expected_decision": "promote"}  # not a valid decision
    p.write_text(json.dumps(case) + "\n", encoding="utf-8")
    with pytest.raises(CorpusError):
        load_corpus(p)


# --- run_eval on the real seeded corpus (ai=None) ----------------------------
def test_all_gate_and_sensor_cases_pass(corpus):
    report = run_eval(corpus, ai=None)
    for r in report.results:
        if r.kind in ("gate", "sensor"):
            assert r.passed, f"{r.id} regressed: {r.detail}"
    assert report.gate_accuracy == 1.0
    assert report.sensor_accuracy == 1.0
    assert report.regressed is False


def test_over_suppression_zero_on_seed(corpus):
    report = run_eval(corpus, ai=None)
    assert report.over_suppression["gate"] == 0.0
    assert report.over_suppression["sensor"] == 0.0


def test_extraction_cases_skipped_not_passed_when_ai_none(corpus):
    report = run_eval(corpus, ai=None)
    extraction = [r for r in report.results if r.kind == "extraction"]
    assert extraction, "expected at least one extraction case"
    for r in extraction:
        assert r.skipped is True
        assert r.passed is False   # skipped must NEVER look like passed
    assert report.extraction_metrics == {}  # nothing scored without an ai


# --- sabotage: prove the eval can actually fail ------------------------------
def test_sabotage_flipped_expected_decision_reports_failure(corpus):
    sabotaged = copy.deepcopy(corpus)
    # Flip the clean control's expected decision from pass -> hold. The live gate
    # still returns pass, so the case must now FAIL and the eval must regress.
    flipped = False
    for c in sabotaged:
        if c["kind"] == "gate" and c["expected_decision"] == "pass":
            c["expected_decision"] = "hold"
            target = c["id"]
            flipped = True
            break
    assert flipped, "no pass-control gate case to sabotage"

    report = run_eval(sabotaged, ai=None)
    bad = [r for r in report.results if r.id == target]
    assert bad and bad[0].passed is False
    assert report.regressed is True
    assert report.gate_accuracy < 1.0


def test_over_suppression_metric_is_not_vacuous():
    # A synthetic corpus that EXPECTS pass but whose gate_input (one non-anchor
    # source) the live gate holds: the gate wrongly suppresses truth -> the
    # over_suppression metric must report 1.0. Proves the metric can be non-zero.
    synthetic = [{
        "id": "synthetic-oversuppress", "kind": "gate", "risk_note": "metric test",
        "added": "2026-07-12",
        "gate_input": {"source_classes": ["blog"]},
        "expected_decision": "pass",
    }]
    report = run_eval(synthetic, ai=None)
    assert report.over_suppression["gate"] == 1.0
    assert report.results[0].passed is False


def test_sabotage_flipped_sensor_expectation_reports_failure(corpus):
    sabotaged = copy.deepcopy(corpus)
    for c in sabotaged:
        if c["kind"] == "sensor" and c["expected_sensor_ok"] is True:
            c["expected_sensor_ok"] = False  # claim the clean control is junk
            break
    report = run_eval(sabotaged, ai=None)
    assert report.regressed is True
    assert report.sensor_accuracy < 1.0


# --- extraction scoring path exercised with a fake ai ------------------------
class _FakeAI:
    """Deterministic fake provider: echoes a fixed extraction. No network."""
    def __init__(self, payload):
        self._payload = payload

    def extract_event_json(self, text, schema_json, system_prompt=None):
        return dict(self._payload)


def test_extraction_scored_when_ai_supplied(corpus):
    # A perfect extractor on the clean extraction control scores as passed.
    control = next(c for c in corpus if c["id"] == "clean-extraction-control-001")
    ai = _FakeAI(control["expected"])
    report = run_eval([control], ai=ai)
    r = report.results[0]
    assert r.skipped is False
    assert r.passed is True
    assert report.extraction_metrics["n_examples"] == 1
    assert report.extraction_metrics["hallucination_rate"] == 0.0


def test_extraction_hallucination_is_caught_when_ai_supplied(corpus):
    # Bait case: source omits venue (expected venue=null). A provider that
    # invents a venue must be caught as a hallucination (case fails).
    bait = next(c for c in corpus if "hallucination-bait" in c["id"])
    invented = dict(bait["expected"])
    invented["venue"] = "Totally Made Up Hall"
    ai = _FakeAI(invented)
    report = run_eval([bait], ai=ai)
    assert report.results[0].passed is False
    assert report.extraction_metrics["hallucination_rate"] > 0.0


# --- CLI entrypoint -----------------------------------------------------------
def test_cli_runs_and_exits_zero_no_regression():
    proc = subprocess.run(
        [sys.executable, "-m", "ai.eval_loop"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Eval / Kaizen Loop" in proc.stdout
    assert "no regression" in proc.stdout


def test_format_report_marks_skips_distinctly(corpus):
    report = run_eval(corpus, ai=None)
    text = format_report(report)
    assert "SKIP" in text        # extraction cases visibly skipped
    assert "no regression" in text
    assert "SKIPPED (no ai provider)" in text


def test_default_corpus_path_points_at_seed_file():
    assert DEFAULT_CORPUS.name == "cases.jsonl"
    assert DEFAULT_CORPUS.exists()
