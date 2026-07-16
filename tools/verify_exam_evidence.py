#!/usr/bin/env python3
"""Verify an attended golden-exam report as release evidence (design v3).

Greppable summary: `python tools/verify_exam_evidence.py <report.json>
--subject-sha <full-sha>` exits 0 only when the report (downloaded by
extraction-eval.yml from an attended dispatch run) INDEPENDENTLY satisfies
every exam invariant AND binds to this exact context. Independence means
the verdict is re-derived from the report's raw metrics against the
thresholds imported from ai/golden_exam — a self-attested `passed: true`
is never trusted (evaluator r10: a forged/malformed report must fail
closed). Binding means: model == the routing table's extraction model,
prompt_sha256 == THIS checkout's prompt, subject_sha == the REQUIRED
--subject-sha (there is no unbound mode). Exit codes: 0 evidence
accepted / 1 rejected or unreadable (fail closed).

Runs in the SECRETLESS PR job: this script never touches the Anthropic
key and never invokes the exam runner — it only reads a finished report.
"""
from __future__ import annotations

import hashlib
import json
import sys

from ai.golden_exam import HALLUCINATION_MAX, RECALL_MIN, SAMPLE_FLOOR
from ai.prompts import EXTRACTION_SYSTEM_PROMPT
from tools.model_router import STAGE_MODELS


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def verify(report: dict, subject_sha: str) -> list[str]:
    """Return the list of rejection reasons (empty = evidence accepted).

    Every check is derived from raw report fields — missing or mistyped
    fields are rejections, never defaults (fail closed on forged or
    malformed evidence)."""
    problems = []

    # 1. Re-derive the exam verdict from raw metrics (never trust "passed").
    expected = _num(report.get("expected_facts"))
    asserted = _num(report.get("asserted_facts"))
    rate = _num(report.get("hallucination_rate"))
    recall = _num(report.get("recall"))
    if expected is None or expected < SAMPLE_FLOOR:
        problems.append(f"expected_facts={report.get('expected_facts')!r} "
                        f"fails the set floor (>= {SAMPLE_FLOOR})")
    if asserted is None or asserted < SAMPLE_FLOOR:
        problems.append(f"asserted_facts={report.get('asserted_facts')!r} "
                        f"fails the asserted floor (>= {SAMPLE_FLOOR})")
    if rate is None or rate > HALLUCINATION_MAX:
        problems.append(f"hallucination_rate={report.get('hallucination_rate')!r} "
                        f"fails the bar (<= {HALLUCINATION_MAX})")
    if recall is None or recall < RECALL_MIN:
        problems.append(f"recall={report.get('recall')!r} fails the floor "
                        f"(>= {RECALL_MIN})")
    if report.get("unanswered") != []:
        problems.append(f"unanswered={report.get('unanswered')!r} (need [])")
    if report.get("injection_failures") != []:
        problems.append(f"injection_failures={report.get('injection_failures')!r} (need [])")
    # Consistency only — the checks above are the authority.
    if report.get("passed") is not True:
        problems.append(f"report.passed={report.get('passed')!r} (need True)")

    # 2. Bind the evidence to this exact context. No unbound mode exists.
    routed = STAGE_MODELS["extraction"]
    if report.get("model") != routed:
        problems.append(
            f"report.model={report.get('model')!r} != production-routed {routed!r}"
        )
    want = hashlib.sha256(EXTRACTION_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    if report.get("prompt_sha256") != want:
        problems.append("report prompt_sha256 is not this checkout's prompt")
    if not subject_sha:
        problems.append("no subject_sha requirement supplied — unbound "
                        "verification is not a mode")
    elif report.get("subject_sha") != subject_sha:
        problems.append(
            f"report.subject_sha={report.get('subject_sha')!r} != required "
            f"{subject_sha!r} (evidence binds to an exact commit)"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    subject_sha = None
    if "--subject-sha" in argv:
        i = argv.index("--subject-sha")
        try:
            subject_sha = argv[i + 1]
        except IndexError:
            print("::error::--subject-sha needs a value", file=sys.stderr)
            return 1
        argv = argv[:i] + argv[i + 2:]
    if len(argv) != 1 or not subject_sha:
        print("::error::usage: verify_exam_evidence.py <exam-report.json> "
              "--subject-sha <sha> (the binding is REQUIRED — unbound "
              "verification is not a mode)", file=sys.stderr)
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
    problems = verify(report, subject_sha)
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
