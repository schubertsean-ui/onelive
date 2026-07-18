"""Tests for trust_gate's extraction-certification re-lock (PR #36).

The compensating control for the golden-exam harness-PR exception, offline
layer: a True ratification flag is only meaningful while the committed
attended-exam certification record is a COMPLETE, well-typed, PASSED record
whose metrics pass the current thresholds AND whose harness hash matches
the current tree. Authenticity of a changed record (real run, artifact
digest, report cross-check) is the base-owned verifier's job in
.github/workflows/extraction-eval.yml — these tests pin the offline
contract, including the evaluator's PR #36 r2 finding: a bare
{harness_sha256, run_id} forgery must be REJECTED, never blessed.
"""
import importlib.util
import json
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PATH = _ROOT / "tools" / "trust_gate.py"
_spec = importlib.util.spec_from_file_location("trust_gate", _PATH)
trust_gate = importlib.util.module_from_spec(_spec)
sys.modules["trust_gate"] = trust_gate
_spec.loader.exec_module(trust_gate)

import ai.golden_exam as golden_exam
import tools.routing_data as routing_data
from ai.exam_thresholds import HALLUCINATION_MAX, RECALL_MIN, SAMPLE_FLOOR


def _valid_record(**overrides) -> dict:
    """A structurally complete PASSED record bound to the CURRENT harness.

    Metrics sit strictly inside every threshold so each failing test below
    isolates exactly one violated bar.
    """
    rec = {
        "harness_sha256": golden_exam.compute_harness_sha(),
        "run_id": "29659010747",
        "artifact_id": "8433778947",
        "artifact_zip_sha256": "ab" * 32,
        "subject_sha": "0123456789abcdef0123456789abcdef01234567",
        "model": "claude-opus-4-8",
        "verdict": "PASSED",
        "metrics": {
            "examples": 77,
            "asserted_facts": SAMPLE_FLOOR + 16,
            "hallucination_rate": HALLUCINATION_MAX / 2,
            "recall": min(1.0, RECALL_MIN + 0.1),
            "injections": 0,
            "unanswered": 0,
        },
    }
    rec.update(overrides)
    return rec


def _run(monkeypatch, tmp_path, flag, record_text):
    monkeypatch.setattr(routing_data, "EXTRACTION_THRESHOLD_RATIFIED", flag)
    rp = tmp_path / "CERTIFIED_HARNESS.json"
    if record_text is not None:
        rp.write_text(record_text, encoding="utf-8")
    findings = trust_gate.Findings()
    trust_gate.check_extraction_certification(findings, record_path=rp)
    return findings


def _run_record(monkeypatch, tmp_path, record: dict):
    return _run(monkeypatch, tmp_path, True, json.dumps(record))


def test_closed_flag_needs_no_certification(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, False, None)
    assert findings.ok()


def test_true_flag_with_no_record_fails(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, True, None)
    assert any("does not exist" in v for v in findings.violations)


def test_full_valid_record_passes(monkeypatch, tmp_path):
    findings = _run_record(monkeypatch, tmp_path, _valid_record())
    assert findings.ok(), findings.violations


def test_bare_hash_and_run_id_forgery_is_rejected(monkeypatch, tmp_path):
    """The exact PR #36 r2 evaluator fixture: a record carrying only the
    current harness hash and an arbitrary run id previously PASSED this
    gate. It must fail — no verdict, no metrics, no artifact binding."""
    findings = _run_record(
        monkeypatch, tmp_path,
        {"harness_sha256": golden_exam.compute_harness_sha(), "run_id": "12345"},
    )
    assert any("not a valid PASSED" in v for v in findings.violations)


def test_drifted_record_fails(monkeypatch, tmp_path):
    findings = _run_record(
        monkeypatch, tmp_path, _valid_record(harness_sha256="0" * 64)
    )
    assert any("DRIFTED" in v for v in findings.violations)


def test_malformed_record_fails_closed(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, True, "{not json")
    assert any("unreadable" in v for v in findings.violations)


def test_non_object_json_fails_closed(monkeypatch, tmp_path):
    """Valid JSON with the wrong top-level type must produce a controlled
    finding, not a TypeError (PR #36 r2 nit)."""
    for text in ("[]", '"a string"', "42", "null"):
        findings = _run(monkeypatch, tmp_path, True, text)
        assert any("not a JSON object" in v for v in findings.violations), text


def test_failed_verdict_is_rejected(monkeypatch, tmp_path):
    findings = _run_record(monkeypatch, tmp_path, _valid_record(verdict="FAILED"))
    assert any("only PASSED certifies" in v for v in findings.violations)


def test_hallucination_above_ceiling_is_rejected(monkeypatch, tmp_path):
    rec = _valid_record()
    rec["metrics"]["hallucination_rate"] = HALLUCINATION_MAX * 2
    findings = _run_record(monkeypatch, tmp_path, rec)
    assert any("hallucination_rate" in v for v in findings.violations)


def test_recall_below_floor_is_rejected(monkeypatch, tmp_path):
    rec = _valid_record()
    rec["metrics"]["recall"] = RECALL_MIN - 0.05
    findings = _run_record(monkeypatch, tmp_path, rec)
    assert any("recall" in v for v in findings.violations)


def test_asserted_facts_below_floor_is_rejected(monkeypatch, tmp_path):
    rec = _valid_record()
    rec["metrics"]["asserted_facts"] = SAMPLE_FLOOR - 1
    findings = _run_record(monkeypatch, tmp_path, rec)
    assert any("asserted_facts" in v for v in findings.violations)


def test_nonzero_injections_or_unanswered_are_rejected(monkeypatch, tmp_path):
    for key in ("injections", "unanswered"):
        rec = _valid_record()
        rec["metrics"][key] = 1
        findings = _run_record(monkeypatch, tmp_path, rec)
        assert any(key in v for v in findings.violations), key


def test_mistyped_fields_fail_closed_without_crashing(monkeypatch, tmp_path):
    """Wrong types anywhere = controlled rejection, never an exception:
    string counts, boolean counts, NaN rates, non-digit ids, list metrics."""
    cases = [
        _valid_record(run_id="not-a-run-id"),
        _valid_record(artifact_id=8433778947),          # int, not string
        _valid_record(subject_sha="short"),
        _valid_record(metrics=[]),
    ]
    rec = _valid_record(); rec["metrics"]["asserted_facts"] = "316"; cases.append(rec)
    rec = _valid_record(); rec["metrics"]["injections"] = False; cases.append(rec)
    rec = _valid_record(); rec["metrics"]["hallucination_rate"] = float("nan"); cases.append(rec)
    for i, case in enumerate(cases):
        findings = _run_record(monkeypatch, tmp_path, case)
        assert any("not a valid PASSED" in v for v in findings.violations), i


def test_malformed_flag_fails_loud(monkeypatch, tmp_path):
    """stage-6 r2: 'true', 1, None, or any non-bool flag is misconfig,
    never a safely-closed state."""
    for bad in ("true", 1, None, "False", 0.0):
        findings = _run(monkeypatch, tmp_path, bad, None)
        assert any("must be a literal bool" in v for v in findings.violations), bad
    # literal False stays a clean closed state
    assert _run(monkeypatch, tmp_path, False, None).ok()


def test_examples_floor_and_current_set_binding(monkeypatch, tmp_path):
    """stage-6 r2: examples must exist, be >= the 40-example floor, and
    equal the CURRENT golden set's size — set drift re-reds offline."""
    rec = _valid_record()
    del rec["metrics"]["examples"]
    assert not _run_record(monkeypatch, tmp_path, rec).ok()
    for bad in (0, 39, 76, "77", True):
        rec = _valid_record()
        rec["metrics"]["examples"] = bad
        findings = _run_record(monkeypatch, tmp_path, rec)
        assert any("examples" in v for v in findings.violations), bad
    # the real count (77, matching ai/golden/golden_set_v1.jsonl) passes
    assert _run_record(monkeypatch, tmp_path, _valid_record()).ok()
