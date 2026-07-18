"""Tests for trust_gate's extraction-certification re-lock (PR #36).

The compensating control for the golden-exam harness-PR exception: a True
ratification flag is only meaningful while the committed attended-exam
certification record matches the CURRENT harness hash. Every branch of the
check is pinned: closed flag, missing record, match, drift, malformed.
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


def _run(monkeypatch, tmp_path, flag, record):
    monkeypatch.setattr(routing_data, "EXTRACTION_THRESHOLD_RATIFIED", flag)
    rp = tmp_path / "CERTIFIED_HARNESS.json"
    if record is not None:
        rp.write_text(record, encoding="utf-8")
    findings = trust_gate.Findings()
    trust_gate.check_extraction_certification(findings, record_path=rp)
    return findings


def test_closed_flag_needs_no_certification(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, False, None)
    assert findings.ok()


def test_true_flag_with_no_record_fails(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, True, None)
    assert any("does not exist" in v for v in findings.violations)


def test_matching_record_passes(monkeypatch, tmp_path):
    current = golden_exam.compute_harness_sha()
    findings = _run(
        monkeypatch, tmp_path, True,
        json.dumps({"harness_sha256": current, "run_id": "12345"}),
    )
    assert findings.ok()


def test_drifted_record_fails(monkeypatch, tmp_path):
    findings = _run(
        monkeypatch, tmp_path, True,
        json.dumps({"harness_sha256": "0" * 64, "run_id": "12345"}),
    )
    assert any("DRIFTED" in v for v in findings.violations)


def test_malformed_record_fails_closed(monkeypatch, tmp_path):
    findings = _run(monkeypatch, tmp_path, True, "{not json")
    assert any("unreadable" in v for v in findings.violations)


def test_missing_fields_fail_closed(monkeypatch, tmp_path):
    findings = _run(
        monkeypatch, tmp_path, True, json.dumps({"harness_sha256": "x" * 64})
    )
    assert any("unreadable" in v or "missing required" in v for v in findings.violations)
