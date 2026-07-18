#!/usr/bin/env python3
"""workflow_env_lint — the env-contract linter for GitHub workflows (R-019).

SUMMARY: the structural fix for the `empty-env` fail-open class (4 ledger
catches: #11, #12, #14 ×2 — a gate step consuming an env var that is unset or
empty silently no-ops instead of failing). Two mechanical rules over every
workflow in .github/workflows/:

R1 UNDECLARED-ENV: every $UPPER_SNAKE shell variable a `run:` step consumes
   must have a visible source: step/job/workflow `env:`, an earlier step's
   `>> "$GITHUB_ENV"` export, an assignment/read within the script itself,
   or the ambient runner allowlist below. No visible source = the
   unset-and-silent risk = FAIL.
R2 VARS-CONTEXT-BAN: `${{ vars.* }}` is forbidden outright — GitHub renders
   an unset repo variable and a set-but-empty one identically, so a workflow
   can never fail closed on the difference (evaluator finding, PR #14 r4;
   the reviewer-model channel was removed for exactly this). Configuration
   must arrive as reviewed file content or as secrets used fail-loud.

Declaring a variable does not prove it non-empty at runtime — scripts still
own their `[ -n "$X" ]` fail-loud checks — but R1 guarantees every consumed
variable has a REVIEWABLE source (no ghost inputs), and R2 removes the one
channel where unset and empty are indistinguishable.

Exit codes: 0 = all workflows clean; 1 = findings (printed file:line-ish);
2 = a workflow failed to parse or the directory is missing (fail loud).

Usage: python tools/workflow_env_lint.py [--dir .github/workflows]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

# Runner-ambient / shell-builtin names a step may consume without declaring.
AMBIENT = {
    "CI",
    "GITHUB_ACTIONS",
    "GITHUB_ENV",
    "GITHUB_OUTPUT",
    "GITHUB_PATH",
    "GITHUB_STEP_SUMMARY",
    "GITHUB_WORKSPACE",
    "GITHUB_SHA",
    "GITHUB_REF",
    "GITHUB_REF_NAME",
    "GITHUB_HEAD_REF",
    "GITHUB_BASE_REF",
    "GITHUB_REPOSITORY",
    "GITHUB_RUN_ID",
    "GITHUB_RUN_ATTEMPT",
    "GITHUB_EVENT_NAME",
    "GITHUB_EVENT_PATH",
    "GITHUB_TOKEN",
    "GITHUB_ACTOR",
    "GITHUB_SERVER_URL",
    "GITHUB_API_URL",
    "RUNNER_OS",
    "RUNNER_TEMP",
    "RUNNER_ARCH",
    "HOME",
    "PATH",
    "PWD",
    "SHELL",
    "TMPDIR",
    "IFS",
}

_GH_EXPR = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)
_SHELL_VAR = re.compile(r"\$\{?([A-Z][A-Z0-9_]{2,})\}?")
_VARS_CONTEXT = re.compile(r"\$\{\{[^}]*\bvars\.", re.DOTALL)
# Sources that make a name script-local: assignment, export, for-loop, read.
_LOCAL_DEF = re.compile(
    r"(?m)^\s*(?:export\s+)?([A-Z][A-Z0-9_]{2,})=|"
    r"\bfor\s+([A-Z][A-Z0-9_]{2,})\s+in\b|"
    r"\bread\s+(?:-r\s+)?([A-Z][A-Z0-9_]{2,})\b"
)
_GITHUB_ENV_EXPORT = re.compile(
    r"(?m)^\s*(?:echo|printf)\s+[\"']?([A-Z][A-Z0-9_]{2,})=.*?\$GITHUB_ENV"
)


def _env_keys(mapping) -> set[str]:
    return set(mapping.keys()) if isinstance(mapping, dict) else set()


def lint_workflow_text(text: str, name: str) -> list[str]:
    """Return findings for one workflow file's text."""
    findings: list[str] = []

    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"{name}: unparseable YAML ({exc})") from exc
    if not isinstance(doc, dict):
        raise ValueError(f"{name}: not a workflow mapping")

    # R2 runs on the PARSED document re-serialized (comments dropped): a
    # comment EXPLAINING the vars. ban must not trigger the ban, but any
    # live ${{ vars.* }} in a value still does.
    if _VARS_CONTEXT.search(yaml.dump(doc)):
        findings.append(
            f"{name}: uses the `vars.` context — forbidden (unset and empty "
            f"render identically, so nothing downstream can fail closed on the "
            f"difference; ship config as reviewed file content instead)"
        )

    workflow_env = _env_keys(doc.get("env"))
    jobs = doc.get("jobs") or {}
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        job_env = _env_keys(job.get("env"))
        exported: set[str] = set()  # names earlier steps wrote to $GITHUB_ENV
        for idx, step in enumerate(job.get("steps") or []):
            if not isinstance(step, dict):
                continue
            run = step.get("run")
            if not isinstance(run, str):
                continue
            step_env = _env_keys(step.get("env"))
            script = _GH_EXPR.sub("", run)  # ${{ ... }} resolves before shell
            local = {m for g in _LOCAL_DEF.findall(script) for m in g if m}
            declared = (
                AMBIENT | workflow_env | job_env | step_env | exported | local
            )
            for var in sorted(set(_SHELL_VAR.findall(script))):
                if var not in declared:
                    findings.append(
                        f"{name}: job '{job_name}' step #{idx + 1} consumes "
                        f"${var} with no visible source (not in workflow/job/"
                        f"step env, not exported by an earlier step, not "
                        f"script-local, not runner-ambient) — an unset value "
                        f"would flow through silently; declare it or remove it"
                    )
            exported |= set(_GITHUB_ENV_EXPORT.findall(script))
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=".github/workflows")
    args = ap.parse_args(argv)

    wf_dir = Path(args.dir)
    files = sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml"))
    if not files:
        print(f"workflow_env_lint: no workflows found in {wf_dir}", file=sys.stderr)
        return 2

    findings: list[str] = []
    for f in files:
        try:
            findings.extend(lint_workflow_text(f.read_text(encoding="utf-8"), f.name))
        except ValueError as exc:
            print(f"workflow_env_lint: {exc}", file=sys.stderr)
            return 2

    if findings:
        for finding in findings:
            print(f"FINDING: {finding}", file=sys.stderr)
        print(
            f"workflow_env_lint: {len(findings)} finding(s) across "
            f"{len(files)} workflow(s) — the empty-env class fails closed here.",
            file=sys.stderr,
        )
        return 1
    print(f"workflow_env_lint: {len(files)} workflow(s) clean — every consumed env var has a visible source; no vars. context.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
