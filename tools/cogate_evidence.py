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
paths? Implements ONLY the grammar the policy actually uses (r6: never
hand arbitrary patterns to fnmatch and hope it matches GitHub): literal
paths (no wildcard characters) and '<dir>/**' suffix globs. ANY other
pattern — ordered '!' exclusions, mid-path wildcards, extglobs — fails
closed; extend this helper with tests before the policy may use them.

candidate-valid — is an Actions job/run pair the base-owned
golden-exam verifier for this PR? Workflow path + event + head SHAs +
MANDATORY PR membership (r7: an empty pull_requests list is missing
identity, not an acceptable quirk — fail closed and re-run the co-gate).

log-bindings — does the fetched job log prove the run executed against
the CURRENT base and this head? The runner echoes each step's env into
the log; the base-owned verifier declares BASE_SHA and HEAD_SHA there,
so every `BASE_SHA: <sha>` echo must equal the current merge^1 and
every `HEAD_SHA: <sha>` echo must equal the PR head, with at least one
of each present (r7: this replaces the r6 run_started_at timestamp,
which was a heuristic — a run can start after a commit's timestamp yet
still be minted against another base; the env echo IS the base the run
used).

Exit 0 with "1"/"0" on stdout; exit 1 on unreadable/unsupported input
(fail closed).
"""
from __future__ import annotations

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


_WILDCARDS = set("*?[!]")


def _match_pattern(pattern: str, f: str) -> bool:
    """Exactly two accepted forms; anything else raises (fail closed)."""
    if pattern.endswith("/**") and not (_WILDCARDS & set(pattern[:-3])):
        prefix = pattern[:-3]
        return f == prefix or f.startswith(prefix + "/")
    if not (_WILDCARDS & set(pattern)):
        return f == pattern
    raise ValueError(f"unsupported paths pattern {pattern!r} — only literal "
                     "paths and '<dir>/**' are implemented; extend "
                     "tools/cogate_evidence.py with tests before the policy "
                     "may use this form (fail closed)")


def _validate_pattern(pattern: str) -> None:
    """Raise unless the pattern is one of the two accepted forms."""
    if pattern.endswith("/**") and not (_WILDCARDS & set(pattern[:-3])):
        return
    if not (_WILDCARDS & set(pattern)):
        return
    raise ValueError(f"unsupported paths pattern {pattern!r} — only literal "
                     "paths and '<dir>/**' are implemented; extend "
                     "tools/cogate_evidence.py with tests before the policy "
                     "may use this form (fail closed)")


INELIGIBLE_MARKER = "EXCEPTION-INELIGIBLE"


def refusal_ineligible(log_text: str) -> bool:
    """True when the classifier's refusal printed the canonical
    EXCEPTION-INELIGIBLE marker (stage-6 r4: a record change riding a
    refusal, or an unreadable manifest). The review step fails closed on
    it — eligibility is mechanics, not evaluator memory. Injection of
    the marker via subject-controlled text can only force REJECTION,
    never acceptance (monotone fail-closed)."""
    return INELIGIBLE_MARKER in log_text


def surface_touched(patterns: list, files: list) -> bool:
    if not isinstance(patterns, list) or not patterns or \
            not all(isinstance(p, str) and p for p in patterns):
        raise ValueError("trigger paths missing or malformed — fail closed")
    # Validation is INDEPENDENT of the changed-file list (r9: with no
    # changed files the per-file loop never ran, so a malformed policy
    # silently returned False instead of failing loud on misconfig).
    for p in patterns:
        _validate_pattern(p)
    return any(_match_pattern(p, f) for p in patterns for f in files)


def candidate_valid(job: dict, run: dict, head_sha: str, pr_number: int) -> bool:
    if not (isinstance(job, dict) and isinstance(run, dict)):
        return False
    if run.get("path") != ".github/workflows/extraction-eval.yml":
        return False
    if run.get("event") != "pull_request_target":
        return False
    if not head_sha or job.get("head_sha") != head_sha or \
            run.get("head_sha") != head_sha:
        return False
    # MANDATORY PR membership (r7): an empty or absent pull_requests list
    # is missing identity — fail closed, never "API quirk". The remedy is
    # re-running the co-gate, which regenerates a bound run.
    prs = run.get("pull_requests")
    if not (isinstance(prs, list) and prs):
        return False
    return any(isinstance(pr, dict) and pr.get("number") == pr_number
               for pr in prs)


_ENV_ECHO = re.compile(r"^\S+\s+(BASE_SHA|HEAD_SHA): ([0-9a-f]{40})\s*$")


def log_bindings(log_text: str, base_sha: str, head_sha: str) -> bool:
    """The run's env echoes are the base+head it executed with (r7),
    parsed ONLY from runner-anchored regions (r9: never bare substring
    over the whole log). Anchoring: the runner prints each step's env
    inside its `##[group]Run …` … `##[endgroup]` block; step OUTPUT —
    the only place subject-influenced text (filenames, record contents)
    can appear in the base-owned job — prints AFTER the endgroup, so
    echoes are only collected between those markers, and only in the
    exact runner format (timestamp token, name, 40-hex, nothing else).
    Two further properties close spoofing: the golden-exam job runs
    base-owned code under pull_request_target, so no subject code
    executes in it at all; and acceptance requires EVERY collected echo
    to match — genuine echoes cannot be removed from a wrong-base log,
    so injection can only ADD mismatches, i.e. force rejection, never
    acceptance. At least one echo of each name must exist."""
    if not (isinstance(base_sha, str) and re.fullmatch(r"[0-9a-f]{40}", base_sha)
            and isinstance(head_sha, str) and re.fullmatch(r"[0-9a-f]{40}", head_sha)):
        return False
    expected = {"BASE_SHA": base_sha, "HEAD_SHA": head_sha}
    found = {"BASE_SHA": [], "HEAD_SHA": []}
    in_group = False
    for line in log_text.splitlines():
        if "##[group]Run " in line:
            in_group = True
        elif "##[endgroup]" in line:
            in_group = False
        elif in_group:
            m = _ENV_ECHO.match(line)
            if m:
                found[m.group(1)].append(m.group(2))
    return all(found[k] and all(v == expected[k] for v in found[k])
               for k in expected)


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

    if len(argv) == 5 and argv[0] == "candidate-valid":
        try:
            job = json.loads(pathlib.Path(argv[1]).read_text(encoding="utf-8"))
            run = json.loads(pathlib.Path(argv[2]).read_text(encoding="utf-8"))
            pr_number = int(argv[4])
        except (OSError, ValueError) as exc:
            return die(f"cannot read candidate inputs ({exc})")
        print("1" if candidate_valid(job, run, argv[3], pr_number) else "0")
        return 0

    if len(argv) == 4 and argv[0] == "log-bindings":
        try:
            log_text = pathlib.Path(argv[1]).read_text(encoding="utf-8",
                                                       errors="replace")
        except OSError as exc:
            return die(f"cannot read log ({exc})")
        print("1" if log_bindings(log_text, argv[2], argv[3]) else "0")
        return 0

    if len(argv) == 2 and argv[0] == "refusal-ineligible":
        try:
            log_text = pathlib.Path(argv[1]).read_text(encoding="utf-8",
                                                       errors="replace")
        except OSError as exc:
            return die(f"cannot read log ({exc})")
        print("1" if refusal_ineligible(log_text) else "0")
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
               "<conclusion> | surface-touched <workflow.yml> <files.txt> | "
               "candidate-valid <job.json> <run.json> <head_sha> <pr_number> | "
               "log-bindings <log> <base_sha> <head_sha>")


if __name__ == "__main__":
    raise SystemExit(main())
