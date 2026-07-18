#!/usr/bin/env python3
"""Authenticate a changed extraction-certification record (BASE-owned).

The offline trust_gate re-lock proves a committed
ai/golden/CERTIFIED_HARNESS.json is complete, PASSED, threshold-passing,
and hash-bound — but offline code cannot prove the record is REAL
(evaluator, PR #36 r2: a hash-only check accepted a self-authored
record). This module is the online half, run by extraction-eval.yml from
the BASE checkout under pull_request_target on any PR that changes the
record: the recorded run must be an actual successful maintainer-
dispatched attended exam on the default branch, the artifact zip must
hash to the recorded digest, and the run's uploaded exam-report.json
must agree with every recorded field. The workflow then feeds the
extracted report to tools/verify_exam_evidence.py — the SAME verifier as
the head-bound path — so thresholds are re-derived from the report's raw
metrics, never from the record.

Subcommands (each re-runs the FULL structural validation first — no
subcommand is a lighter gate than another):

  field <record.json> <run_id|subject_sha>
        --expect-harness-sha256 <hex> --expect-model <id>
      Validate the record + its base bindings; print the one field
      (shape-validated above, so safe for shell capture).

  run <record.json> <run.json> <artifacts.json>
        --expect-harness-sha256 <hex> --expect-model <id>
        --default-branch <name>
      Validate the recorded run's API metadata + locate the recorded
      artifact; print its archive_download_url.

  report <record.json> <report.zip> <outdir>
        --expect-harness-sha256 <hex> --expect-model <id>
      Verify the zip digest, extract the single exam-report.json into
      <outdir> (untrusted data, isolated dir), and cross-check every
      recorded metric against the report.

Exit 0 = accepted; exit 1 = rejected/unreadable (fail closed).
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re
import sys
import zipfile

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")  # same as the workflows

ATTENDED_WORKFLOW = ".github/workflows/extraction-exam-dispatch.yml"


def _reject(msg: str) -> None:
    print(f"::error::certification record REJECTED: {msg} (fail closed)",
          file=sys.stderr)


def _count(v) -> "int | None":
    """Counts must be true NON-NEGATIVE integers — bools, floats, and
    negatives are malformed (evaluator r4 nit: a record should reject an
    impossible count structurally, not rely on a later gate)."""
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None


def _rate(v) -> "float | None":
    """Finite numbers in [0, 1] only (evaluator, PR #36 r3): json.loads
    accepts NaN/Infinity, and `abs(nan - x) > tol` is False — a NaN rate
    would sail through the agreement check. Non-finite or out-of-range =
    malformed = rejected here, never left for another gate to catch."""
    if isinstance(v, (int, float)) and not isinstance(v, bool) \
            and math.isfinite(v) and 0.0 <= float(v) <= 1.0:
        return float(v)
    return None


def validate_record(record, expect_harness_sha256: str, expect_model: str) -> "list[str]":
    """Structural + base-binding validation. Returns rejection reasons."""
    problems = []
    if not isinstance(record, dict):
        return ["record is not a JSON object"]
    if not (isinstance(record.get("run_id"), str) and record["run_id"].isdigit()):
        problems.append("run_id missing or non-numeric")
    if not (isinstance(record.get("artifact_id"), str) and record["artifact_id"].isdigit()):
        problems.append("artifact_id missing or non-numeric")
    if not (isinstance(record.get("artifact_zip_sha256"), str)
            and _HEX64_RE.fullmatch(record["artifact_zip_sha256"])):
        problems.append("artifact_zip_sha256 missing or not 64-hex")
    if not (isinstance(record.get("harness_sha256"), str)
            and _HEX64_RE.fullmatch(record["harness_sha256"])):
        problems.append("harness_sha256 missing or not 64-hex")
    if not (isinstance(record.get("subject_sha"), str)
            and _SHA_RE.fullmatch(record["subject_sha"])):
        problems.append("subject_sha missing or not 40-hex")
    if record.get("verdict") != "PASSED":
        problems.append(f"verdict={record.get('verdict')!r} (only PASSED certifies)")
    if not (isinstance(record.get("model"), str)
            and _MODEL_ID_RE.fullmatch(record["model"])):
        problems.append("model missing or not a plausible model id")
    m = record.get("metrics")
    if not isinstance(m, dict):
        problems.append("metrics missing or not an object")
    else:
        # Metric values are validated HERE, fail closed (evaluator, PR #36
        # r3): every count a true int, every rate a finite number in [0,1].
        for key in ("examples", "asserted_facts", "injections", "unanswered"):
            if _count(m.get(key)) is None:
                problems.append(f"metrics.{key}={m.get(key)!r} is not an integer count")
        for key in ("hallucination_rate", "recall"):
            if _rate(m.get(key)) is None:
                problems.append(f"metrics.{key}={m.get(key)!r} is not a finite "
                                "number in [0, 1]")
    if problems:
        return problems
    # Bind to the BASE tree the PR merges into: a record certifies the
    # already-merged harness — never one riding in the same PR — and must
    # claim the routed model the subject actually resolves to.
    if not (expect_harness_sha256 and _HEX64_RE.fullmatch(expect_harness_sha256)):
        problems.append("expected harness hash missing/malformed — unbound "
                        "verification is not a mode")
    elif record["harness_sha256"] != expect_harness_sha256:
        problems.append("harness_sha256 is not the base tree's harness — a "
                        "record certifies the already-merged harness, never "
                        "one riding in the same PR")
    if not (expect_model and _MODEL_ID_RE.fullmatch(expect_model)):
        problems.append("expected model missing/malformed — unbound "
                        "verification is not a mode")
    elif record["model"] != expect_model:
        problems.append(f"model={record['model']!r} is not the routed "
                        f"extraction model {expect_model!r}")
    return problems


def validate_run(record: dict, run, artifacts, default_branch: str) -> "list[str] | str":
    """Validate run metadata + artifact binding. Returns a list of
    rejection reasons, or the artifact archive_download_url on success."""
    problems = []
    if not isinstance(run, dict) or "id" not in run:
        return [f"run {record['run_id']} not found — the recorded run does not exist"]
    if str(run.get("id")) != record["run_id"]:
        problems.append("run lookup returned a different run id")
    if run.get("path") != ATTENDED_WORKFLOW:
        problems.append(f"run workflow {run.get('path')!r} is not the "
                        "attended exam dispatch")
    if run.get("event") != "workflow_dispatch":
        problems.append(f"run event {run.get('event')!r} is not a maintainer dispatch")
    if run.get("conclusion") != "success":
        problems.append(f"run conclusion {run.get('conclusion')!r} (need success)")
    # Branch copies of the attended workflow are untrusted (same rule as
    # the head-bound path's r18 filter): only default-branch runs executed
    # the guarded harness.
    if not default_branch:
        problems.append("default branch unresolved — unbound verification "
                        "is not a mode")
    elif run.get("head_branch") != default_branch:
        problems.append(f"run executed on branch {run.get('head_branch')!r}, "
                        "not the default branch")
    if run.get("head_sha") != record["subject_sha"]:
        problems.append(f"run head_sha {run.get('head_sha')!r} != record "
                        "subject_sha — the record claims a commit its exam "
                        "did not run on")
    arts = artifacts.get("artifacts") if isinstance(artifacts, dict) else None
    hits = [a for a in (arts or [])
            if isinstance(a, dict) and str(a.get("id")) == record["artifact_id"]]
    if not hits:
        problems.append("recorded artifact_id not found on the run — expired "
                        "or wrong id (re-dispatch the exam and record the "
                        "fresh run)")
        return problems
    art = hits[0]
    if not str(art.get("name", "")).startswith("golden-exam-report-"):
        problems.append(f"artifact {art.get('name')!r} is not an exam report")
    if art.get("expired"):
        problems.append("artifact expired — re-dispatch the exam and record "
                        "the fresh run")
    url = art.get("archive_download_url") or ""
    if not url.startswith("https://api.github.com/"):
        problems.append("artifact download url malformed")
    return problems if problems else url


def validate_report_zip(record: dict, zip_path: pathlib.Path,
                        outdir: pathlib.Path) -> "list[str]":
    """Verify the artifact digest, extract the single report (untrusted
    data, isolated dir — r15), and cross-check record metrics against it."""
    try:
        data = zip_path.read_bytes()
    except OSError as exc:
        return [f"cannot read artifact zip ({exc})"]
    got = hashlib.sha256(data).hexdigest()
    if got != record["artifact_zip_sha256"]:
        return [f"artifact zip sha256 {got[:16]}… does not match the "
                "recorded digest — the record does not describe this run's "
                "artifact"]
    try:
        with zipfile.ZipFile(zip_path) as z:
            if z.namelist() != ["exam-report.json"]:
                return ["artifact is not exactly one exam-report.json"]
            z.extract("exam-report.json", outdir)
    except zipfile.BadZipFile:
        return ["artifact is not a readable zip"]
    try:
        report = json.loads((outdir / "exam-report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"exam report unreadable ({exc})"]
    if not isinstance(report, dict):
        return ["exam report is not a JSON object"]
    problems = []
    m = record["metrics"]
    # Counts must match EXACTLY. Rates are transcribed into the record at
    # 4-decimal display precision, so they must agree with the report
    # within half a display ulp (5e-5) — this tolerance cannot loosen any
    # gate: the AUTHORITATIVE threshold enforcement is
    # verify_exam_evidence.py, re-derived from the report's exact values,
    # never from the record.
    for label, want, got_v in (
        ("examples", _count(m.get("examples")), _count(report.get("n_examples"))),
        ("asserted_facts", _count(m.get("asserted_facts")), _count(report.get("asserted_facts"))),
        ("injections", _count(m.get("injections")), len(report.get("injection_failures") or [])),
        ("unanswered", _count(m.get("unanswered")), len(report.get("unanswered") or [])),
    ):
        if want is None or got_v is None or want != got_v:
            problems.append(f"record metrics.{label}={want!r} != report's {got_v!r}")
    # BOTH sides finite-validated (evaluator, PR #36 r3): a NaN on either
    # side makes `abs(a - b) > tol` False and would slip a mismatch through.
    for label in ("hallucination_rate", "recall"):
        want, got_v = _rate(m.get(label)), _rate(report.get(label))
        if want is None or got_v is None or abs(want - got_v) > 5e-5:
            problems.append(f"record metrics.{label}={m.get(label)!r} disagrees "
                            f"with report's {report.get(label)!r}")
    return problems


def _load_json(path: str):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _reject(f"cannot read {path} ({exc})")
        raise SystemExit(1)


def main(argv: "list[str] | None" = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    def take(flag: str) -> "str | None":
        if flag not in argv:
            return None
        i = argv.index(flag)
        try:
            value = argv[i + 1]
        except IndexError:
            return None
        del argv[i:i + 2]
        return value

    expect_harness = take("--expect-harness-sha256") or ""
    expect_model = take("--expect-model") or ""
    default_branch = take("--default-branch") or ""
    usage = ("usage: authenticate_certification_record.py "
             "field <record> <run_id|subject_sha> | "
             "run <record> <run.json> <artifacts.json> --default-branch <b> | "
             "report <record> <report.zip> <outdir> "
             "(--expect-harness-sha256 and --expect-model always required)")
    if not argv:
        _reject(usage)
        return 1
    cmd, rest = argv[0], argv[1:]
    if cmd not in ("field", "run", "report"):
        _reject(usage)
        return 1

    record = _load_json(rest[0]) if rest else None
    if record is None:
        _reject(usage)
        return 1
    problems = validate_record(record, expect_harness, expect_model)
    if problems:
        for p in problems:
            _reject(p)
        return 1

    if cmd == "field":
        if len(rest) != 2 or rest[1] not in ("run_id", "subject_sha"):
            _reject(usage)
            return 1
        print(record[rest[1]])
        return 0

    if cmd == "run":
        if len(rest) != 3:
            _reject(usage)
            return 1
        run = _load_json(rest[1])
        artifacts = _load_json(rest[2])
        result = validate_run(record, run, artifacts, default_branch)
        if isinstance(result, list):
            for p in result:
                _reject(p)
            return 1
        print(result)
        return 0

    # cmd == "report"
    if len(rest) != 3:
        _reject(usage)
        return 1
    problems = validate_report_zip(record, pathlib.Path(rest[1]), pathlib.Path(rest[2]))
    if problems:
        for p in problems:
            _reject(p)
        return 1
    print("record agrees with the run's uploaded report on every bound field")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
