#!/usr/bin/env python3
"""workflow_env_lint — the env-contract linter for GitHub workflows (R-019).

SUMMARY: the structural fix for the `empty-env` fail-open class (4 ledger
catches: #11, #12, #14 ×2 — a gate step consuming an env var that is unset or
empty silently no-ops instead of failing). Two mechanical rules over every
workflow in .github/workflows/:

R1 UNDECLARED-ENV: every UPPERCASE shell variable a `run:` step consumes
   (scope: UPPER_SNAKE names, the workflow/env convention — lowercase
   script locals are out of scope by design, stated explicitly per r8)
   must have a visible source: step/job/workflow `env:`, an earlier step's
   `>> "$GITHUB_ENV"` export, an assignment/read within the script itself,
   or the ambient runner allowlist below. No visible source = the
   unset-and-silent risk = FAIL.
R4 EXPRESSION-GUARD: an env var whose value is ANY GitHub expression that
   can render empty on misconfig (secrets/env/inputs/needs/steps/event
   fields — everything except a safelist of always-present github.*
   platform fields), when consumed in shell text, must
   carry a visible TERMINATING non-empty guard — ${X:?}, or a -n test
   with an abort (exit/return) on the same line; a non-terminating -n
   probe never counts, -z never counts — at-or-before first use, at ANY
   env declaration scope (workflow, job, or step)
   — declaration alone cannot prove the secret exists at runtime.
   Boundary: env vars inherited implicitly by child processes (never
   expanded in shell text) are the consuming program's fail-loud
   responsibility — the ONLY remaining out-of-scope channel after r13/r14
   closed env-value and direct-run expressions.
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
    "RANDOM",
    "SECONDS",
    "LINENO",
    "HOSTNAME",
    "OSTYPE",
    "REPLY",
}

_GH_EXPR = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)
_SHELL_VAR = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
_VARS_CONTEXT = re.compile(r"\$\{\{(?:(?!\}\}).)*\bvars\s*[.\[]", re.DOTALL)
# R3: expression channels that render EMPTY when the underlying value is
# missing, used directly inside executing shell text.
# R3 (generalized at r14): ANY GitHub expression directly inside run: is
# banned unless it is a safelisted always-present platform field — every
# other context can render "" (and un-quoted interpolation is also GitHub's
# documented script-injection surface). Route values through env: where R4
# enforces the terminating guard.
_ANY_EXPR_FULL = re.compile(r"\$\{\{.*?\}\}", re.DOTALL)
_ASSIGN = re.compile(r"(?:^|;)\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=")
_FOR_VAR = re.compile(r"\bfor\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\b")
_READ_VAR = re.compile(r"\bread\s+(?:-r\s+)?([A-Za-z_][A-Za-z0-9_]*)\b")
# Non-empty guards that make a secret-backed var fail-loud at runtime.
# ${X:?} always aborts. A -n test ([ / [[ / test) counts ONLY when the same
# line carries an abort token (exit/return) after it — a non-terminating
# probe like `[ -n "$X" ] || true` or a bare `if [ -n "$X" ]; then ...; fi`
# lets an empty secret flow into later commands (evaluator r8). -z NEVER
# counts (it succeeds when empty — evaluator r7).
_GUARD_PARAM = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*):\?")
# Structural -n test on the UNQUOTED view: the var lives in a double-quoted
# span there, so the name is recovered from the code view at the gap.
# The gap after -n includes the blanked (quoted) variable region — the
# var itself reads as spaces in the unquoted view, so the gap must not be
# eaten by whitespace matching; the name is recovered from the code view.
_NTEST_STRUCT = re.compile(r"(?:\[\[?|test)\s+-n(\s[^\]|&;]*)")
# The abort must be a COMMAND in the || branch, not a word inside another
# command's arguments (evaluator r11: `|| echo exit 1` terminates nothing).
# Accepted: `|| exit`, `|| return`, `|| { exit ... }`,
# `|| { anything; exit ... }` — exit/return at brace-start or after `;`.
_TERMINATES = re.compile(
    r"\s*\]{0,2}\s*\|\|\s*"
    r"(?:exit\b|\{\s*exit\b|\{[^}]*?;\s*exit\b)"
)
_SECRET_VALUE = re.compile(r"\$\{\{(?:(?!\}\}).)*\bsecrets\s*[.\[]", re.DOTALL)
# Expression-backed env values that can render EMPTY on misconfig require
# the terminating guard (evaluator r13: not just secrets — env./inputs./
# needs./steps./github.event.inputs all render "" when missing). The ONLY
# exemption is a safelist of platform fields GitHub always populates.
_ALWAYS_PRESENT = re.compile(
    r"^\$\{\{\s*github\.(?:repository|repository_owner|sha|ref|ref_name|"
    r"run_id|run_number|run_attempt|actor|job|workflow|event_name|"
    r"server_url|api_url|graphql_url|workspace)\s*\}\}$"
)
_ANY_EXPR = re.compile(r"\$\{\{")
_EXPORT_CMD = re.compile(r"(?:echo|printf)\b")
_EXPORT_FULL = re.compile(
    r"(?:echo|printf)\s+[\"']?([A-Za-z_][A-Za-z0-9_]*)=.*?\$\{?GITHUB_ENV\}?"
)
_IF_OPEN = re.compile(r"\b(?:if|case)\b")
_IF_CLOSE = re.compile(r"\b(?:fi|esac)\b")
_COND_CONT = re.compile(r"&&|\|\|")


def _cmd_pos(unq: str, pos: int) -> bool:
    """True when pos starts a command in the unquoted view: line start or
    after ';', '{'. Everything else — after '&&', '||', '|', '(', or as an
    argument to another word (e.g. `echo [ -n ...`) — does NOT count
    (evaluator r10: inert arguments and conditional continuations must never
    credit guards, definitions, or exports)."""
    before = unq[:pos].rstrip()
    while before.endswith("!"):
        before = before[:-1].rstrip()
    if not before:
        return True
    if before[-1] in ";{":
        return True
    # Shell keywords that take a command next (negation handled above).
    return bool(re.search(r"\b(?:if|elif|while|until|then|else|do)$", before))


def _line_views(raw_line: str) -> tuple[str, str]:
    """Return (code, code_unquoted) with POSITIONS PRESERVED (blanked spans
    become spaces), per evaluator r9:
    - code: inline unquoted comments blanked (a `# ...` tail is not shell),
      single-quoted spans blanked (nothing expands in single quotes),
      double-quoted content KEPT ("$X" is a real expansion).
    - code_unquoted: additionally blanks double-quoted spans — used for ALL
      STRUCTURE matching (definitions, guard skeletons, export commands,
      if/fi tracking) so quoted text can never masquerade as executed shell.
    Escape handling inside quotes is not modeled (documented limit,
    false-positive direction: a weird quoted string may produce a spurious
    finding, never a silent pass).
    """
    code: list[str] = []
    unq: list[str] = []
    in_s = in_d = False
    prev_ws = True
    for ch in raw_line:
        if in_s:
            code.append(" ")
            unq.append(" ")
            if ch == "'":
                in_s = False
            prev_ws = False
            continue
        if in_d:
            code.append(ch)
            unq.append(" ")
            if ch == '"':
                in_d = False
                code[-1] = '"'
            prev_ws = False
            continue
        if ch == "'":
            in_s = True
            code.append(" ")
            unq.append(" ")
            prev_ws = False
            continue
        if ch == '"':
            in_d = True
            code.append('"')
            unq.append(" ")
            prev_ws = False
            continue
        if ch == "#" and prev_ws:
            pad = " " * (len(raw_line) - len(code))
            return "".join(code) + pad, "".join(unq) + pad
        code.append(ch)
        unq.append(ch)
        prev_ws = ch.isspace()
    return "".join(code), "".join(unq)


def _standalone_assignment(raw: str, value_start: int) -> bool:
    """True when the assignment at value_start is standalone (persists in
    the shell) rather than a `X=v cmd` prefix (child-process-only). The
    value extent is parsed on the RAW line with a quote+paren automaton so
    `X="$(cmd "$Y" | z)"` reads as one value — the position-preserving
    views cannot model quote re-nesting inside command substitution
    (evaluator r16)."""
    i = value_start
    sq = dq = False
    depth = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and not sq:
            i += 2
            continue
        if sq:
            if ch == "'":
                sq = False
        elif ch == "'" and not dq:
            sq = True
        elif ch == '"':
            dq = not dq
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif not dq and depth == 0 and (ch.isspace() or ch in ";&|#"):
            break
        i += 1
    rest = raw[i:].lstrip()
    return not rest or rest[0] in ";&|#"


def _scan_run_script(
    run_text: str, declared: set[str], must_guard: set[str]
) -> tuple[list[str], list[str], list[str], set[str]]:
    """Line-order scan of one run: script (evaluator r5–r10 — fail-closed).

    Returns (undeclared_uses, banned_expr_lines, unguarded_uses, exports).
    Execution-semantics rules (r10):
    - Structure (definitions, guard skeletons, export commands, if/case
      tracking) is matched on the UNQUOTED view at COMMAND POSITION only —
      quoted text, command arguments, and `&&`/`||` continuations never
      credit anything.
    - Lines inside if/elif/else/fi or case/esac regions credit NO
      definitions, exports, or guards (branch execution is statically
      undecidable — fail closed); uses there are still checked.
    - Guards must abort on the FAILURE branch: ${X:?} (aborts wherever it
      expands), or a command-position -n test followed by `|| exit`/
      `|| { ...; exit; }`. A var mention inside a -n/:? test is a probe,
      not a consuming use.
    - Definitions credit later uses (or same-line uses after a `;`); the
      prefix form `X=a cmd "$X"` expands the PRIOR value and never counts.
    Documented remaining limits (false-negative direction, each requiring a
    deliberate construction: loop bodies (`for`/`while`) credit textually;
    a `for X in <empty>` leaves X unset. Runtime [ -n ] checks stay the
    guard for those paths.
    """
    defined = set(declared)
    undeclared: list[str] = []
    banned: list[str] = []
    exports: set[str] = set()
    guarded: set[str] = set()
    unguarded: list[str] = []
    _SEP = re.compile(r"[;|&\n]")
    _FUNC_OPEN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(\)\s*\{")
    _TERMINATOR = re.compile(r"\bexit\b")
    cond_depth = 0
    func_depth = 0
    script_dead = False  # set after an unconditional command-position exit
    for raw_line in run_text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for em in _ANY_EXPR_FULL.finditer(raw_line):
            if not _ALWAYS_PRESENT.match(em.group(0).strip()):
                banned.append(stripped[:80])
                break
        code_view, unq_view = _line_views(raw_line)
        line = _GH_EXPR.sub(lambda m: " " * len(m.group(0)), code_view)
        unq = _GH_EXPR.sub(lambda m: " " * len(m.group(0)), unq_view)

        # Conditional-region tracking (unquoted, command-position openers).
        opens = sum(1 for m in _IF_OPEN.finditer(unq) if _cmd_pos(unq, m.start()))
        closes = sum(1 for m in _IF_CLOSE.finditer(unq))
        # Function bodies are code that may never run (evaluator r11):
        # tracked like conditionals, approximately — `name() {` opens, a
        # bare `}` line closes (false-positive direction on exotic layouts).
        # A one-line function (`api() { ...; }`) opens and closes on the
        # same line: no lasting region (its line still credits nothing).
        fopens = sum(
            1 for m in _FUNC_OPEN.finditer(unq) if "}" not in unq[m.end():]
        )
        same_line_funcs = sum(
            1 for m in _FUNC_OPEN.finditer(unq) if "}" in unq[m.end():]
        )
        in_cond = (
            cond_depth > 0 or func_depth > 0 or opens > 0 or fopens > 0
            or same_line_funcs > 0 or script_dead
        )
        cond_depth = max(0, cond_depth + opens - closes)
        func_depth = max(0, func_depth + fopens - (1 if unq.strip() == "}" else 0))

        # Guard skeletons + probe spans (structure on unq; names from code).
        # ${X:?} credit requires EXECUTION (evaluator r15): an escaped \${X:?}
        # never expands, and a && / || continuation before it means the
        # expansion sits on a branch that may never run — neither credits.
        line_guards: list[tuple[int, str]] = []
        guard_spans: list[tuple[int, int]] = []
        for m in _GUARD_PARAM.finditer(line):
            if m.start() > 0 and line[m.start() - 1] == "\\":
                continue  # escaped: literal text, never expands
            guard_spans.append(m.span())
            if not in_cond and not _COND_CONT.search(unq[: m.start()]):
                line_guards.append((m.start(), m.group(1)))
        for m in _NTEST_STRUCT.finditer(unq):
            if not _cmd_pos(unq, m.start()):
                continue
            gap_start, gap_end = m.span(1)
            vm = _SHELL_VAR.search(line[gap_start:gap_end])
            if not vm:
                continue
            name = vm.group(1)
            guard_spans.append((m.start(), gap_end + 2))
            if not in_cond and _TERMINATES.match(unq, m.end()):
                line_guards.append((m.start(), name))

        # Definitions: command-position anchors only, never in conditionals.
        defs: list[tuple[int, str]] = []
        if not in_cond:
            for m in _ASSIGN.finditer(unq):
                # Standalone assignments only (evaluator r16): the prefix
                # form `X=abc cmd` sets X for THAT child process, not for
                # the shell — it must never credit later lines. Standalone
                # means: after the value (parsed with $()/() depth so
                # `X=$(mktemp -d)` stays one value; quoted values are
                # already blanked to spaces) comes a separator, a comment,
                # or the end of the line — not another command word.
                if not _standalone_assignment(raw_line, m.end()):
                    continue  # prefix form — affects only the child process
                defs.append((m.end(), m.group(1)))
            # for/read define only as COMMANDS, never as words inside another
            # command's arguments (r11: `echo read MY_TOKEN` defines nothing).
            for rx in (_FOR_VAR, _READ_VAR):
                for m in rx.finditer(unq):
                    if _cmd_pos(unq, m.start()):
                        defs.append((m.end(), m.group(1)))

        for m in _SHELL_VAR.finditer(line):
            if m.start() > 0 and line[m.start() - 1] == "\\":
                continue  # \$X is literal text, not an expansion
            name = m.group(1)
            in_guard = any(a <= m.start() < b for a, b in guard_spans)
            covered = name in defined or any(
                dend <= m.start() and dname == name and _SEP.search(line[dend:m.start()])
                for dend, dname in defs
            )
            if not covered and not in_guard:
                if name not in undeclared:
                    undeclared.append(name)
            guarded_here = name in guarded or any(
                gpos <= m.start() and gname == name for gpos, gname in line_guards
            )
            if (
                covered
                and not in_guard
                and name in must_guard
                and not guarded_here
                and name not in unguarded
            ):
                unguarded.append(name)
        defined |= {dname for _, dname in defs}
        guarded |= {gname for _, gname in line_guards}

        # Exports: command-position echo/printf, outside conditionals, with
        # the KEY= and $GITHUB_ENV verified on the code view at that anchor.
        if not in_cond:
            for m in _EXPORT_CMD.finditer(unq):
                if not _cmd_pos(unq, m.start()):
                    continue
                em = _EXPORT_FULL.match(line, m.start())
                if em:
                    exports.add(em.group(1))

        # An UNCONDITIONAL command-position exit/return ends execution: every
        # later line is dead code and credits nothing (evaluator r12 — an
        # export after `exit 0` never runs). Conditional aborts (after ||,
        # inside if-blocks) do not set this — cmd_pos excludes them.
        if not in_cond and any(
            _cmd_pos(unq, m.start()) for m in _TERMINATOR.finditer(unq)
        ):
            script_dead = True
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

    workflow_env_map = doc.get("env") if isinstance(doc.get("env"), dict) else {}
    workflow_env = set(workflow_env_map.keys())

    def _secret_keys(mapping) -> set[str]:
        # Guard duty for ANY expression-backed value that can render empty:
        # secrets, env, inputs, needs, steps outputs, event fields — all of
        # them produce "" on misconfig with no shell-visible difference.
        # Only safelisted always-present github.* fields are exempt.
        return {
            k for k, v in (mapping or {}).items()
            if isinstance(v, str)
            and _ANY_EXPR.search(v)
            and not _ALWAYS_PRESENT.match(v.strip())
        }

    jobs = doc.get("jobs") or {}
    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        job_env_map = job.get("env") if isinstance(job.get("env"), dict) else {}
        job_env = set(job_env_map.keys())
        exported: set[str] = set()  # names earlier steps wrote to $GITHUB_ENV
        for idx, step in enumerate(job.get("steps") or []):
            if not isinstance(step, dict):
                continue
            run = step.get("run")
            if not isinstance(run, str):
                continue
            step_env_map = step.get("env") if isinstance(step.get("env"), dict) else {}
            step_env = set(step_env_map.keys())
            # Secret-backed at ANY declaration scope needs the guard
            # (evaluator r7: a workflow/job-level secret env renders just as
            # empty when the secret is missing).
            secret_backed = (
                _secret_keys(workflow_env_map)
                | _secret_keys(job_env_map)
                | _secret_keys(step_env_map)
            )
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
                    f"GitHub expression directly into run: ('{frag}') — a "
                    f"missing value renders as an EMPTY STRING (and direct "
                    f"interpolation is the script-injection surface); pass it "
                    f"via the step's env: block with a terminating guard, or "
                    f"use a safelisted always-present github.* field"
                )
            for var in unguarded:
                findings.append(
                    f"{name}: job '{job_name}' step #{idx + 1} consumes the "
                    f"expression-backed ${var} in shell text with no non-empty "
                    f"guard before first use — a missing/misconfigured value renders as an "
                    f"empty string and this step would proceed silently; add a "
                    f"TERMINATING guard before first use: : \"${{{var}:?}}\" or "
                    f"[ -n \"${var}\" ] || exit 1 (a bare probe does not count)"
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
