"""Tests for tools/authenticate_certification_record.py — the online half
of the certification re-lock (PR #36 r2: offline code cannot prove a
record is REAL; this module binds it to an actual successful attended run,
its artifact digest, and its uploaded report).

Every rejection branch is pinned: structural forgeries, wrong-workflow /
wrong-branch / wrong-conclusion runs, subject-sha mismatches, artifact id
and digest mismatches, multi-member archives, and metric disagreements.
"""
import hashlib
import json
import pathlib
import sys
import zipfile

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools import authenticate_certification_record as acr

HARNESS = "f" * 64
MODEL = "claude-opus-4-8"
SUBJECT = "0123456789abcdef0123456789abcdef01234567"


def _record(**overrides):
    rec = {
        "harness_sha256": HARNESS,
        "run_id": "29659010747",
        "artifact_id": "8433778947",
        "artifact_zip_sha256": "ab" * 32,
        "subject_sha": SUBJECT,
        "model": MODEL,
        "verdict": "PASSED",
        "metrics": {
            "examples": 77, "asserted_facts": 316,
            "hallucination_rate": 0.0063, "recall": 0.9782,
            "injections": 0, "unanswered": 0,
        },
    }
    rec.update(overrides)
    return rec


def _run(**overrides):
    run = {
        "id": 29659010747,
        "path": acr.ATTENDED_WORKFLOW,
        "event": "workflow_dispatch",
        "conclusion": "success",
        "head_branch": "master",
        "head_sha": SUBJECT,
    }
    run.update(overrides)
    return run


def _artifacts(**overrides):
    art = {
        "id": 8433778947,
        "name": "golden-exam-report-abc",
        "expired": False,
        "archive_download_url": "https://api.github.com/repos/o/r/actions/artifacts/8433778947/zip",
    }
    art.update(overrides)
    return {"artifacts": [art]}


# ---- validate_record -------------------------------------------------------

def test_valid_record_accepted():
    assert acr.validate_record(_record(), HARNESS, MODEL) == []


def test_bare_forgery_rejected():
    """The PR #36 r2 fixture: hash + run_id alone must never validate."""
    problems = acr.validate_record(
        {"harness_sha256": HARNESS, "run_id": "12345"}, HARNESS, MODEL)
    assert problems


def test_record_structural_rejections():
    cases = [
        ([], "not a JSON object"),
        (_record(run_id="x"), "run_id"),
        (_record(artifact_id=123), "artifact_id"),
        (_record(artifact_zip_sha256="short"), "artifact_zip"),
        (_record(subject_sha="short"), "subject_sha"),
        (_record(verdict="FAILED"), "PASSED"),
        (_record(model="bad model$"), "model"),
        (_record(metrics=None), "metrics"),
    ]
    for rec, needle in cases:
        problems = acr.validate_record(rec, HARNESS, MODEL)
        assert any(needle in p for p in problems), (rec, problems)


def test_record_must_bind_to_base_harness_and_routed_model():
    assert any("base tree's harness" in p for p in
               acr.validate_record(_record(), "0" * 64, MODEL))
    assert any("routed" in p for p in
               acr.validate_record(_record(), HARNESS, "some-other-model"))
    # Unbound verification is not a mode: empty expectations reject.
    assert acr.validate_record(_record(), "", MODEL)
    assert acr.validate_record(_record(), HARNESS, "")


# ---- validate_run ----------------------------------------------------------

def test_valid_run_returns_artifact_url():
    out = acr.validate_run(_record(), _run(), _artifacts(), "master")
    assert isinstance(out, str) and out.startswith("https://api.github.com/")


def test_run_rejections():
    rec = _record()
    cases = [
        ({}, _artifacts(), "master", "not found"),
        (_run(id=999), _artifacts(), "master", "different run id"),
        (_run(path=".github/workflows/other.yml"), _artifacts(), "master", "attended exam dispatch"),
        (_run(event="push"), _artifacts(), "master", "maintainer dispatch"),
        (_run(conclusion="failure"), _artifacts(), "master", "need success"),
        (_run(head_branch="feature"), _artifacts(), "master", "default branch"),
        (_run(), _artifacts(), "", "default branch unresolved"),
        (_run(head_sha="e" * 40), _artifacts(), "master", "did not run on"),
        (_run(), {"artifacts": []}, "master", "not found on the run"),
        (_run(), _artifacts(id=1), "master", "not found on the run"),
        (_run(), _artifacts(name="evil-artifact"), "master", "not an exam report"),
        (_run(), _artifacts(expired=True), "master", "expired"),
        (_run(), _artifacts(archive_download_url="https://evil.example/zip"),
         "master", "malformed"),
    ]
    for run, arts, branch, needle in cases:
        out = acr.validate_run(rec, run, arts, branch)
        assert isinstance(out, list) and any(needle in p for p in out), (needle, out)


# ---- validate_report_zip ---------------------------------------------------

def _report():
    return {
        "n_examples": 77, "asserted_facts": 316,
        "hallucination_rate": 0.00632911, "recall": 0.97821782,
        "injection_failures": [], "unanswered": [],
    }


def _zip_with(tmp_path, report, members=None):
    zp = tmp_path / "report.zip"
    with zipfile.ZipFile(zp, "w") as z:
        for name, payload in (members or [("exam-report.json", json.dumps(report))]):
            z.writestr(name, payload)
    return zp, hashlib.sha256(zp.read_bytes()).hexdigest()


def test_matching_report_accepted(tmp_path):
    zp, digest = _zip_with(tmp_path, _report())
    rec = _record(artifact_zip_sha256=digest)
    assert acr.validate_report_zip(rec, zp, tmp_path) == []
    assert (tmp_path / "exam-report.json").exists()


def test_digest_mismatch_rejected(tmp_path):
    zp, _ = _zip_with(tmp_path, _report())
    problems = acr.validate_report_zip(_record(), zp, tmp_path)
    assert any("does not match the recorded digest" in p for p in problems)


def test_multi_member_archive_rejected(tmp_path):
    zp, digest = _zip_with(tmp_path, _report(), members=[
        ("exam-report.json", json.dumps(_report())),
        ("evil.py", "print('hi')"),
    ])
    problems = acr.validate_report_zip(_record(artifact_zip_sha256=digest), zp, tmp_path)
    assert any("exactly one exam-report.json" in p for p in problems)


def test_metric_disagreements_rejected(tmp_path):
    for key, bad in [("asserted_facts", 999), ("examples", 1),
                     ("injections", 1), ("unanswered", 1)]:
        rec = _record(artifact_zip_sha256="x")
        rec["metrics"][key] = bad
        zp, digest = _zip_with(tmp_path, _report())
        rec["artifact_zip_sha256"] = digest
        problems = acr.validate_report_zip(rec, zp, tmp_path)
        assert any(key in p for p in problems), key


def test_rate_tolerance_is_display_precision_only(tmp_path):
    # 0.0063 vs report 0.00632911 — within half a display ulp: accepted.
    zp, digest = _zip_with(tmp_path, _report())
    assert acr.validate_report_zip(_record(artifact_zip_sha256=digest), zp, tmp_path) == []
    # A record overstating recall by a full point must reject.
    rec = _record()
    rec["metrics"]["recall"] = 0.9882
    zp, digest = _zip_with(tmp_path, _report())
    rec["artifact_zip_sha256"] = digest
    problems = acr.validate_report_zip(rec, zp, tmp_path)
    assert any("recall" in p for p in problems)


def test_unreadable_zip_rejected(tmp_path):
    bad = tmp_path / "report.zip"
    bad.write_bytes(b"not a zip")
    rec = _record(artifact_zip_sha256=hashlib.sha256(b"not a zip").hexdigest())
    problems = acr.validate_report_zip(rec, bad, tmp_path)
    assert any("not a readable zip" in p for p in problems)


# ---- CLI -------------------------------------------------------------------

def test_cli_field_prints_validated_values(tmp_path, capsys):
    rp = tmp_path / "rec.json"
    rp.write_text(json.dumps(_record()), encoding="utf-8")
    common = ["--expect-harness-sha256", HARNESS, "--expect-model", MODEL]
    assert acr.main(["field", str(rp), "run_id"] + common) == 0
    assert capsys.readouterr().out.strip() == "29659010747"
    assert acr.main(["field", str(rp), "subject_sha"] + common) == 0
    assert capsys.readouterr().out.strip() == SUBJECT
    # Only the two shape-validated fields are printable.
    assert acr.main(["field", str(rp), "note"] + common) == 1
    capsys.readouterr()


def test_cli_fails_closed_on_forged_record(tmp_path, capsys):
    rp = tmp_path / "rec.json"
    rp.write_text(json.dumps({"harness_sha256": HARNESS, "run_id": "12345"}),
                  encoding="utf-8")
    assert acr.main(["field", str(rp), "run_id",
                     "--expect-harness-sha256", HARNESS,
                     "--expect-model", MODEL]) == 1
    capsys.readouterr()


def test_cli_run_subcommand(tmp_path, capsys):
    rp = tmp_path / "rec.json"; rp.write_text(json.dumps(_record()), encoding="utf-8")
    rj = tmp_path / "run.json"; rj.write_text(json.dumps(_run()), encoding="utf-8")
    aj = tmp_path / "arts.json"; aj.write_text(json.dumps(_artifacts()), encoding="utf-8")
    common = ["--expect-harness-sha256", HARNESS, "--expect-model", MODEL]
    assert acr.main(["run", str(rp), str(rj), str(aj),
                     "--default-branch", "master"] + common) == 0
    assert capsys.readouterr().out.strip().startswith("https://api.github.com/")
    assert acr.main(["run", str(rp), str(rj), str(aj),
                     "--default-branch", "feature"] + common) == 1
    capsys.readouterr()


# ---- non-finite / mistyped metrics (evaluator, PR #36 r3) ------------------

def test_nonfinite_and_mistyped_metrics_rejected_by_validate_record():
    """json.loads accepts NaN/Infinity, and abs(nan - x) > tol is False —
    the authenticator must reject them itself, fail closed."""
    cases = [
        ("hallucination_rate", float("nan")),
        ("hallucination_rate", float("inf")),
        ("recall", float("nan")),
        ("recall", 1.5),
        ("recall", "0.9782"),
        ("asserted_facts", True),
        ("asserted_facts", 316.0),
        ("examples", "77"),
        ("injections", None),
    ]
    for key, bad in cases:
        rec = _record()
        rec["metrics"][key] = bad
        problems = acr.validate_record(rec, HARNESS, MODEL)
        assert any(key in p for p in problems), (key, bad, problems)


def test_nan_report_rate_rejected_in_agreement_check(tmp_path):
    """A NaN on the REPORT side must also reject — both sides of the
    agreement comparison are finite-validated."""
    report = _report()
    report["hallucination_rate"] = float("nan")
    zp, digest = _zip_with(tmp_path, report)
    problems = acr.validate_report_zip(_record(artifact_zip_sha256=digest), zp, tmp_path)
    assert any("hallucination_rate" in p for p in problems)
