#!/usr/bin/env python3
"""Verify an attended golden-exam report as release evidence (design v4).

Greppable summary: `python tools/verify_exam_evidence.py <report.json>
--subject-sha <sha> --expect-model <id> --expect-prompt-sha256 <hex>`
exits 0 only when the report (downloaded by extraction-eval.yml from an
attended dispatch run) INDEPENDENTLY satisfies every exam invariant AND
binds to all three REQUIRED expectations. Independence: the verdict is
re-derived from raw metrics against thresholds imported from
ai/exam_thresholds (pure data) — self-attested `passed: true` is never trusted (r10).
Trust placement (r12): in CI this script runs from the BASE checkout,
never the PR's, and imports nothing whose value the subject controls —
the expectations are lifted from the subject commit as inert data by the
AST extractors and passed in as arguments. Exit codes: 0 evidence
accepted / 1 rejected or unreadable (fail closed).

Runs in the SECRETLESS PR job: this script never touches the Anthropic
key and never invokes the exam runner — it only reads a finished report.
"""
from __future__ import annotations

import json
import math
import re
import sys

# Entry-point script: put the repo root on the path so package imports
# work under direct invocation (python3 tools/<name>.py — how CI calls it).
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from ai.exam_thresholds import EXAM_PACKAGES, HALLUCINATION_MAX, RECALL_MIN, SAMPLE_FLOOR

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")   # same as the workflows

_REQUIREMENTS = pathlib.Path(__file__).resolve().parent.parent / "worker" / "requirements.txt"
_PIN_RE = re.compile(r"^([A-Za-z0-9._-]+)==([A-Za-z0-9._!+-]+)$")


def _pinned_versions(names: tuple) -> dict:
    """Exact '=='-pins for `names` from worker/requirements.txt (this
    checkout's — BASE's in CI, same trust placement as the thresholds
    import above). A missing file, missing entry, or non-exact pin maps
    to None, which can never match a recorded version — unpinned exam
    dependencies are unverifiable and fail closed (r24)."""
    pins = {n: None for n in names}
    try:
        lines = _REQUIREMENTS.read_text(encoding="utf-8").splitlines()
    except OSError:
        return pins
    lower_to_name = {n.lower(): n for n in names}
    for line in lines:
        m = _PIN_RE.fullmatch(line.split("#", 1)[0].strip())
        if m and m.group(1).lower() in lower_to_name:
            pins[lower_to_name[m.group(1).lower()]] = m.group(2)
    return pins


def _num(v) -> float | None:
    """Finite numbers only (r17 blocker): json.load accepts NaN/Infinity,
    and `nan > max` / `nan < min` are both False — a NaN metric would sail
    through threshold comparisons. Non-finite = malformed = rejected."""
    if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
        return float(v)
    return None


def _count(v) -> int | None:
    """Counts must be true integers (r11 nit): a float count is a malformed
    or hand-crafted report and fails closed."""
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def verify(report: dict, subject_sha: str, expect_model: str,
           expect_prompt_sha256: str, expect_golden_sha256: str,
           expect_harness_sha256: str) -> list[str]:
    """Return the list of rejection reasons (empty = evidence accepted).

    Every check is derived from raw report fields — missing or mistyped
    fields are rejections, never defaults (fail closed on forged or
    malformed evidence). The EXPECTATIONS (model, prompt hash, subject
    SHA) are explicit REQUIRED arguments: this module runs as trusted
    BASE code in CI (evaluator r12 — the trust decision must not execute
    subject-controlled code), so it must not import anything whose value
    the subject controls; the caller lifts expectations from the subject
    commit as inert data (AST extractors) and passes them in."""
    problems = []

    # 1. Re-derive the exam verdict from raw metrics (never trust "passed").
    expected = _count(report.get("expected_facts"))
    asserted = _count(report.get("asserted_facts"))
    rate = _num(report.get("hallucination_rate"))
    recall = _num(report.get("recall"))
    if expected is None or expected < SAMPLE_FLOOR:
        problems.append(f"expected_facts={report.get('expected_facts')!r} "
                        f"fails the set floor (>= {SAMPLE_FLOOR})")
    if asserted is None or asserted < SAMPLE_FLOOR:
        problems.append(f"asserted_facts={report.get('asserted_facts')!r} "
                        f"fails the asserted floor (>= {SAMPLE_FLOOR})")
    # Rates are proportions (r21 blocker): anything outside [0, 1] is a
    # forged/malformed report, not a very good or very bad score —
    # hallucination_rate=-1 or recall=999 must reject, never impress.
    if rate is None or not (0.0 <= rate <= 1.0) or rate > HALLUCINATION_MAX:
        problems.append(f"hallucination_rate={report.get('hallucination_rate')!r} "
                        f"out of range or fails the bar (<= {HALLUCINATION_MAX})")
    if recall is None or not (0.0 <= recall <= 1.0) or recall < RECALL_MIN:
        problems.append(f"recall={report.get('recall')!r} out of range or "
                        f"fails the floor (>= {RECALL_MIN})")
    if report.get("unanswered") != []:
        problems.append(f"unanswered={report.get('unanswered')!r} (need [])")
    if report.get("injection_failures") != []:
        problems.append(f"injection_failures={report.get('injection_failures')!r} (need [])")
    # Consistency only — the checks above are the authority.
    if report.get("passed") is not True:
        problems.append(f"report.passed={report.get('passed')!r} (need True)")

    # 2. Bind the evidence to this exact context. No unbound mode exists.
    if not expect_model or not _MODEL_ID_RE.fullmatch(expect_model):
        problems.append("expected model missing or not a plausible model id — "
                        "unbound/malformed verification is not a mode")
    elif report.get("model") != expect_model:
        problems.append(
            f"report.model={report.get('model')!r} != expected routed "
            f"{expect_model!r}"
        )
    if not expect_prompt_sha256 or not _HEX64_RE.fullmatch(expect_prompt_sha256):
        problems.append("expected prompt hash missing or not 64 lowercase hex "
                        "chars — unbound/malformed verification is not a mode")
    elif report.get("prompt_sha256") != expect_prompt_sha256:
        problems.append("report prompt_sha256 is not the subject's prompt")
    for label, want, got in (
        ("golden set", expect_golden_sha256, report.get("golden_sha256")),
        ("harness", expect_harness_sha256, report.get("harness_sha256")),
    ):
        if not want or not _HEX64_RE.fullmatch(want):
            problems.append(f"expected {label} hash missing/malformed — "
                            "unbound verification is not a mode")
        elif got != want:
            problems.append(f"report {label} hash {str(got)[:12]!r}… is not the "
                            f"current harness's — evidence measured a different "
                            f"exam (r22: old metrics never certify the current set)")
    if not subject_sha or not _SHA_RE.fullmatch(subject_sha):
        problems.append("subject_sha requirement missing or not a full "
                        "40-char lowercase SHA — unbound/malformed "
                        "verification is not a mode")
    elif report.get("subject_sha") != subject_sha:
        problems.append(
            f"report.subject_sha={report.get('subject_sha')!r} != required "
            f"{subject_sha!r} (evidence binds to an exact commit)"
        )

    # 3. Dependency binding (r24 blocker): the harness hash covers the
    # dependency PINS (worker/requirements.txt bytes); this check closes
    # the loop on what was actually INSTALLED when the evidence was
    # minted. Every exam-relevant package must carry an exact pin here
    # and the report's recorded version must equal it — evidence minted
    # under a different dependency set certifies nothing.
    pkgs = report.get("packages")
    if not isinstance(pkgs, dict):
        problems.append(f"packages={pkgs!r} (need the runner's recorded "
                        "dict of installed exam-package versions)")
    else:
        pins = _pinned_versions(EXAM_PACKAGES)
        for name in EXAM_PACKAGES:
            if pins[name] is None:
                problems.append(f"worker/requirements.txt has no exact "
                                f"'=='-pin for {name} — unpinned exam "
                                f"dependencies are unverifiable (fail closed)")
            elif pkgs.get(name) != pins[name]:
                problems.append(f"report packages[{name!r}]="
                                f"{pkgs.get(name)!r} != pinned "
                                f"{pins[name]!r} — evidence was minted "
                                f"under a different dependency set")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    def take(flag: str) -> str | None:
        if flag not in argv:
            return None
        i = argv.index(flag)
        try:
            value = argv[i + 1]
        except IndexError:
            return None
        del argv[i:i + 2]
        return value

    subject_sha = take("--subject-sha")
    expect_model = take("--expect-model")
    expect_prompt = take("--expect-prompt-sha256")
    expect_golden = take("--expect-golden-sha256")
    expect_harness = take("--expect-harness-sha256")
    if len(argv) != 1 or not (subject_sha and expect_model and expect_prompt
                              and expect_golden and expect_harness):
        print("::error::usage: verify_exam_evidence.py <exam-report.json> "
              "--subject-sha <sha> --expect-model <id> "
              "--expect-prompt-sha256 <hex> --expect-golden-sha256 <hex> "
              "--expect-harness-sha256 <hex> (ALL bindings are REQUIRED — "
              "unbound verification is not a mode)", file=sys.stderr)
        return 1
    try:
        report = json.load(open(argv[0], encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"::error::cannot read exam report ({exc}) — unreadable evidence "
              "is not evidence (fail closed).", file=sys.stderr)
        return 1
    if not isinstance(report, dict):
        print("::error::exam report is not a JSON object (fail closed).",
              file=sys.stderr)
        return 1
    problems = verify(report, subject_sha, expect_model, expect_prompt,
                      expect_golden, expect_harness)
    if problems:
        for p in problems:
            print(f"::error::exam evidence REJECTED: {p}", file=sys.stderr)
        return 1
    print("exam evidence accepted: invariants re-derived from raw metrics; "
          f"bound to model={report['model']} subject_sha={report['subject_sha']} "
          f"prompt_sha256={report['prompt_sha256'][:12]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
