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
import sys

from ai.exam_thresholds import HALLUCINATION_MAX, RECALL_MIN, SAMPLE_FLOOR


def _num(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _count(v) -> int | None:
    """Counts must be true integers (r11 nit): a float count is a malformed
    or hand-crafted report and fails closed."""
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def verify(report: dict, subject_sha: str, expect_model: str,
           expect_prompt_sha256: str) -> list[str]:
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
    if not expect_model:
        problems.append("no expected model supplied — unbound verification "
                        "is not a mode")
    elif report.get("model") != expect_model:
        problems.append(
            f"report.model={report.get('model')!r} != expected routed "
            f"{expect_model!r}"
        )
    if not expect_prompt_sha256:
        problems.append("no expected prompt hash supplied — unbound "
                        "verification is not a mode")
    elif report.get("prompt_sha256") != expect_prompt_sha256:
        problems.append("report prompt_sha256 is not the subject's prompt")
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
    if len(argv) != 1 or not (subject_sha and expect_model and expect_prompt):
        print("::error::usage: verify_exam_evidence.py <exam-report.json> "
              "--subject-sha <sha> --expect-model <id> "
              "--expect-prompt-sha256 <hex> (ALL bindings are REQUIRED — "
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
    problems = verify(report, subject_sha, expect_model, expect_prompt)
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
