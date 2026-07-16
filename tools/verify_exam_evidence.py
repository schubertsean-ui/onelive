#!/usr/bin/env python3
"""Verify an attended golden-exam report as release evidence (design v2).

Greppable summary: `python tools/verify_exam_evidence.py <report.json>`
exits 0 only when the report (downloaded by extraction-eval.yml from the
attended dispatch run matching the PR's head SHA) shows a PASS for the
PRODUCTION-ROUTED extraction model against THIS checkout's exact prompt
(sha256). Any mismatch — failed/invalid report, a different model than
the routing table names (the dispatch input can name any model, and
evidence for a different model certifies nothing), or a prompt hash that
is not this checkout's prompt — exits 1 with a `::error::` line. Exit
codes: 0 evidence accepted / 1 rejected or unreadable (fail closed).

Runs in the SECRETLESS PR job: this script never touches the Anthropic
key and never invokes the exam runner — it only reads a finished report.
"""
from __future__ import annotations

import hashlib
import json
import sys

from ai.prompts import EXTRACTION_SYSTEM_PROMPT
from tools.model_router import STAGE_MODELS


def verify(report: dict) -> list[str]:
    """Return the list of rejection reasons (empty = evidence accepted)."""
    problems = []
    if report.get("passed") is not True:
        problems.append(f"report.passed={report.get('passed')!r} (need True)")
    routed = STAGE_MODELS["extraction"]
    if report.get("model") != routed:
        problems.append(
            f"report.model={report.get('model')!r} != production-routed {routed!r}"
        )
    want = hashlib.sha256(EXTRACTION_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    if report.get("prompt_sha256") != want:
        problems.append("report prompt_sha256 is not this checkout's prompt")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("::error::usage: verify_exam_evidence.py <exam-report.json>",
              file=sys.stderr)
        return 1
    try:
        report = json.load(open(argv[0], encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"::error::cannot read exam report ({exc}) — unreadable evidence "
              "is not evidence (fail closed).", file=sys.stderr)
        return 1
    problems = verify(report)
    if problems:
        print("::error::attended evidence rejected: " + "; ".join(problems),
              file=sys.stderr)
        return 1
    print(f"evidence verified: model={report['model']} "
          f"hallucination_rate={report['hallucination_rate']} "
          f"recall={report['recall']} asserted_facts={report['asserted_facts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
