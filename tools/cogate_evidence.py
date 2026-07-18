#!/usr/bin/env python3
"""Co-gate evidence judgments for adversarial-review.yml (PR #37 r5).

Security-critical gate logic must be tested code, not shell one-liners.
Two judgments the review workflow delegates here:

refusal-only — is a FAILED golden-exam job's failure EXACTLY the
classifier's designed harness-refusal (the charter's enumerated
exception), and nothing else? Judged on three grounds together, all
mechanical:
  1. conclusion is exactly "failure" — cancelled / timed_out /
     action_required / startup_failure are incomplete evidence, never
     an allowed refusal;
  2. the job's STEP conclusions (the Actions API's ground truth, immune
     to log-text tricks): exactly one step failed, it is the classify
     step by name, and every other step is success or skipped — a
     refusal annotation accompanied by a second failing step (rejected
     record, authenticator error) can never pass, even if that second
     failure wrote no ##[error] annotation at all;
  3. the log's error annotations: non-empty, and every one (minus the
     runner's generic exit line) starts with the refusal sentence.
Raw-text failure scanning is deliberately NOT used: the runner echoes
each step's script source into the log, so words like REJECTED appear
in healthy logs as code text — step conclusions are authoritative.

surface-touched — does a changed-file list touch the co-gate's trigger
paths? Implements the accepted grammar explicitly: literal paths and
'**' suffix globs via fnmatch (which matches across '/'). Ordered '!'
exclusions are NOT supported: if the policy ever contains one, this
fails closed rather than guessing GitHub's ordered semantics.

Exit 0 with "1"/"0" on stdout; exit 1 on unreadable/unsupported input
(fail closed).
"""
from __future__ import annotations

import fnmatch
import json
import pathlib
import re
import sys

CLASSIFY_STEP = "Classify the extraction-surface diff (harness code cannot ride a prompt-swap exam)"
REFUSAL_PREFIX = ("This PR changes extraction HARNESS code that the "
                  "attended exam does not execute")
_ERROR_LINE = re.compile(r"##\[error\]")
_GENERIC_EXIT = "Process completed with exit code"


def refusal_only(job: dict, log_text: str, conclusion: str) -> bool:
    if conclusion != "failure":
        return False
    steps = job.get("steps")
    if not isinstance(steps, list) or not steps:
        return False
    failed = [s for s in steps if isinstance(s, dict)
              and s.get("conclusion") == "failure"]
    others_ok = all(
        isinstance(s, dict) and s.get("conclusion") in ("success", "skipped")
        for s in steps if s not in failed
    )
    if len(failed) != 1 or not others_ok:
        return False
    if failed[0].get("name") != CLASSIFY_STEP:
        return False
    errs = [_ERROR_LINE.split(line, 1)[1] for line in log_text.splitlines()
            if _ERROR_LINE.search(line)]
    errs = [e for e in errs if not e.startswith(_GENERIC_EXIT)]
    return bool(errs) and all(e.startswith(REFUSAL_PREFIX) for e in errs)


def surface_touched(patterns: list, files: list) -> bool:
    if not isinstance(patterns, list) or not patterns or \
            not all(isinstance(p, str) and p for p in patterns):
        raise ValueError("trigger paths missing or malformed — fail closed")
    if any(p.startswith("!") for p in patterns):
        raise ValueError("ordered '!' exclusions are not supported by this "
                         "helper — extend it with tests before using them "
                         "(fail closed)")
    return any(fnmatch.fnmatch(f, p) for f in files for p in patterns)


def main(argv: "list[str] | None" = None) -> int:
    argv = sys.argv[1:] if argv is None else argv

    def die(msg: str) -> int:
        print(f"::error::cogate_evidence: {msg} (fail closed)", file=sys.stderr)
        return 1

    if len(argv) == 4 and argv[0] == "refusal-only":
        try:
            job = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
            log_text = pathlib.Path(argv[2]).read_text(encoding="utf-8",
                                                       errors="replace")
        except (OSError, ValueError) as exc:
            return die(f"cannot read inputs ({exc})")
        if not isinstance(job, dict):
            return die("job json is not an object")
        print("1" if refusal_only(job, log_text, argv[3]) else "0")
        return 0

    if len(argv) == 3 and argv[0] == "surface-touched":
        try:
            import yaml
            wf = yaml.safe_load(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
            pats = wf[True]["pull_request_target"]["paths"]
            files = pathlib.Path(argv[2]).read_text(encoding="utf-8").split()
        except Exception as exc:  # noqa: BLE001 — every parse failure fails closed
            return die(f"cannot read policy/file list ({exc})")
        try:
            print("1" if surface_touched(pats, files) else "0")
        except ValueError as exc:
            return die(str(exc))
        return 0

    return die("usage: cogate_evidence.py refusal-only <job.json> <log> "
               "<conclusion> | surface-touched <workflow.yml> <files.txt>")


if __name__ == "__main__":
    raise SystemExit(main())
