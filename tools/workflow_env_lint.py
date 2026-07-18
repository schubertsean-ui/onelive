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
R4 SECRET-GUARD: a secret-backed step env var consumed in shell text must
   carry a visible non-empty guard ([ -n ] / ${X:?}) at-or-before first use
   — declaration alone cannot prove the secret exists at runtime.
   Boundary: env vars inherited implicitly by child processes (never
   expanded in shell text) are the consuming program's fail-loud
   responsibility, and non-secret expression contexts (inputs.*,
   steps.*.outputs.*) owe their own runtime checks — both documented here
   deliberately rather than guessed at statically.
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
# R3: expression channels that render EMPTY when the underlying value is
# missing, used directly inside executing shell text.
_RUN_EXPR_BAN = re.compile(r"\$\{\{[^}]*\b(secrets\.|env\.|github\.token)")
_ASSIGN = re.compile(r"(?:^|;|&&|\|\|)\s*(?:export\s+)?([A-Z][A-Z0-9_]{2,})=")
_FOR_VAR = re.compile(r"\bfor\s+([A-Z][A-Z0-9_]{2,})\s+in\b")
_READ_VAR = re.compile(r"\bread\s+(?:-r\s+)?([A-Z][A-Z0-9_]{2,})\b")
# Non-empty guards that make a secret-backed var fail-loud at runtime.
_GUARD = re.compile(
    r"\[\[?\s+-[nz]\s+\"?\$\{?([A-Z][A-Z0-9_]{2,})\}?\"?|"
    r"\$\{([A-Z][A-Z0-9_]{2,}):\?"
)
_SECRET_VALUE = re.compile(r"\$\{\{[^}]*\bsecrets\.")
_GITHUB_ENV_EXPORT = re.compile(
    r"(?:echo|printf)\s+[\"']?([A-Z][A-Z0-9_]{2,})=.*?\$GITHUB_ENV"
)


def _scan_run_script(
    run_text: str, declared: set[str], must_guard: set[str]
) -> tuple[list[str], list[str], list[str], set[str]]:
    """Line-order scan of one run: script (evaluator r5/r6 — fail-closed).

    Returns (undeclared_uses, banned_expr_lines, unguarded_uses, exports).
    - Comment lines (first non-space char '#') define nothing, export
      nothing, and are never scanned.
    - A same-line definition credits a use only if a command separator
      (';', '&&', '||', '|', newline) sits between them: `X=a; echo "$X"`
      counts, but the prefix form `X=a cmd "$X"` does NOT — the shell
      expands "$X" from the PRIOR environment before cmd runs (r6).
    - Vars in must_guard (secret-backed env consumed by this script) need a
      visible non-empty guard ([ -n "$X" ] / [ -z "$X" ] / ${X:?} / test -n)
      on a line at-or-before their first use (r6: a declared-but-missing
      secret renders empty; declaration alone proves nothing at runtime).
    Known honest limits (documented, false-negative direction): an export or
    guard inside a conditional branch is credited if its line executes in
    textual order — branch execution is statically undecidable; and
    expression contexts other than secrets./env./github.token (e.g.
    inputs.*, steps.*.outputs.*) can also render empty — those channels are
    out of scope here and owe their own runtime [ -n ] checks.
    """
    defined = set(declared)
    undeclared: list[str] = []
    banned: list[str] = []
    exports: set[str] = set()
    guarded: set[str] = set()
    unguarded: list[str] = []
    _SEP = re.compile(r"[;|&\n]")
    for raw_line in run_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _RUN_EXPR_BAN.search(raw_line):
            banned.append(stripped[:80])
        line = _GH_EXPR.sub("", raw_line)
        # Guards register BEFORE uses on the same line (a guard mentions the
        # var, so it must not count as an unguarded use itself).
        for gm in _GUARD.finditer(line):
            guarded.add(gm.group(1) or gm.group(2))
        guard_spans = [gm.span() for gm in _GUARD.finditer(line)]
        defs = [(m.end(), m.group(1)) for rx in (_ASSIGN, _FOR_VAR, _READ_VAR)
                for m in rx.finditer(line)]
        for m in _SHELL_VAR.finditer(line):
            name = m.group(1)
            in_guard = any(a <= m.start() < b for a, b in guard_spans)
            covered = name in defined or any(
                dend <= m.start() and dname == name and _SEP.search(line[dend:m.start()])
                for dend, dname in defs
            )
            if not covered and not in_guard:
                if name not in undeclared:
                    undeclared.append(name)
            if (
                covered
                and not in_guard
                and name in must_guard
                and name not in guarded
                and name not in unguarded
            ):
                unguarded.append(name)
        defined |= {dname for _, dname in defs}
        for m in _GITHUB_ENV_EXPORT.finditer(line):
            exports.add(m.group(1))
    return undeclared, banned, unguarded, exports


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
            step_env_map = step.get("env") if isinstance(step.get("env"), dict) else {}
            step_env = set(step_env_map.keys())
            secret_backed = {
                k for k, v in step_env_map.items()
                if isinstance(v, str) and _SECRET_VALUE.search(v)
            }
            declared = (
                AMBIENT | workflow_env | job_env | step_env | exported
            )
            undeclared, banned, unguarded, new_exports = _scan_run_script(
                run, declared, secret_backed
            )
            for var in undeclared:
                findings.append(
                    f"{name}: job '{job_name}' step #{idx + 1} consumes "
                    f"${var} with no visible source (not in workflow/job/"
                    f"step env, not exported by an EARLIER executing line/"
                    f"step, not script-local before use, not runner-ambient) "
                    f"— an unset value would flow through silently; declare "
                    f"it or remove it"
                )
            for frag in banned:
                findings.append(
                    f"{name}: job '{job_name}' step #{idx + 1} interpolates a "
                    f"secrets./env./github.token expression directly into run: "
                    f"('{frag}') — a missing value renders as an EMPTY STRING "
                    f"with no way to fail closed; pass it via the step's env: "
                    f"block and consume it as a shell variable instead"
                )
            for var in unguarded:
                findings.append(
                    f"{name}: job '{job_name}' step #{idx + 1} consumes the "
                    f"secret-backed ${var} in shell text with no non-empty "
                    f"guard before first use — a missing secret renders as an "
                    f"empty string and this step would proceed silently; add "
                    f"[ -n \"${var}\" ] (or ${{{var}:?}}) before using it"
                )
            exported |= new_exports
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
