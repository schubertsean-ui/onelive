#!/usr/bin/env python3
"""Pure-stdlib style/trust linter for this project.

Catches what a project's own trust-invariant gate does not: the generic
code-hygiene rules below. It is NOT a substitute for that gate — see
tools/README.md, "What a project must add".

Rules enforced (see docs/CODING_CONVENTIONS.md for the human-facing version):
  1. Swallowed errors: bare `except:` or `except Exception:` with a blank/pass
     body (OPERATING_RULES §1 bans this outright).
  2. `print(` used for error/status handling inside worker/ai/api/tools (should
     be `logging`, so failures are observable, not console noise).
  3. Missing module docstring in worker/ai/api/tools/*.py (every module here is
     part of the audited pipeline or its tooling and must say what it's for).
  4. TODO/FIXME/XXX left in code — the broken-window rule (OPERATING_RULES §1
     "no deferred cleanup").
`--fix` auto-fixes what is SAFELY fixable: trailing whitespace, missing final
newline, and simple import-block sorting (stdlib/third-party/local, alpha
within each group, only for a leading contiguous import block). It does NOT
touch anything that would require judgment (swallowed errors, TODOs, print).
Exit 0 = clean. Exit 1 = violations remain after any --fix pass.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys
from dataclasses import dataclass, field

REPO = pathlib.Path(__file__).resolve().parent.parent

# Directories this linter walks: the audited runtime + its tooling. TS/JS trees
# are out of scope (different toolchain). Non-existent entries cost nothing, so
# the list is wide by design — a project ADDS its own trees here and never
# removes one to quiet a finding.
LINT_DIRS = ["api", "worker", "ai", "tools", "src", "app", "lib", "libs",
             "pkg", "cmd", "scripts", "services", "packages"]

# Subset whose print()-for-errors is a real observability defect: long-running
# service code, where console output vanishes in production. CLI tools print
# by design and are excluded.
SERVICE_DIRS = ["worker", "api", "services", "app", "src"]

_MARKERS = ("TO" + "DO", "FIX" + "ME", "XXX")  # split so this rule's own
# definition line can never accidentally match itself (see check_no_todos).
TODO_RE = re.compile(r"#.*\b(" + "|".join(_MARKERS) + r")\b")
STDLIB_PREFIXES = None  # populated lazily by _is_stdlib


@dataclass
class Findings:
    violations: list[str] = field(default_factory=list)

    def add(self, msg: str) -> None:
        self.violations.append(msg)

    def ok(self) -> bool:
        return not self.violations


def _py_files(dirs: list[str]) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for d in dirs:
        out.extend((REPO / d).rglob("*.py"))
    return sorted(p for p in out if "__pycache__" not in p.parts)


# --- Rule 1: swallowed errors --------------------------------------------------
def _is_blank_body(body: list[ast.stmt]) -> bool:
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
        return True  # docstring-only body, functionally blank
    return False


def check_swallowed_errors(findings: Findings) -> None:
    for path in _py_files(LINT_DIRS):
        rel = str(path.relative_to(REPO))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            findings.add(f"{rel}: could not parse ({exc}); cannot lint.")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            is_bare = node.type is None
            is_broad_exception = (
                isinstance(node.type, ast.Name) and node.type.id == "Exception"
            )
            if (is_bare or is_broad_exception) and _is_blank_body(node.body):
                kind = "bare except:" if is_bare else "except Exception:"
                findings.add(
                    f"{rel}:{node.lineno}: {kind} with a blank/pass body swallows "
                    f"the error silently. OPERATING_RULES SS1 bans this unless the "
                    f"branch is itself logged/audited with a comment justifying it. "
                    f"Log the exception (or re-raise) instead."
                )


# --- Rule 2: print() for error handling in worker/api ------------------------
_PRINT_ERROR_HINTS = ("error", "fail", "exception", "warn", "traceback")


def check_print_for_errors(findings: Findings) -> None:
    for path in _py_files(SERVICE_DIRS):
        rel = str(path.relative_to(REPO))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"):
                continue
            # Flag prints that are inside an except handler (status/error context)
            # or whose literal text hints at error/failure reporting.
            in_except = any(
                isinstance(anc, ast.ExceptHandler)
                for anc in ast.walk(tree)
                if isinstance(anc, ast.ExceptHandler) if node in ast.walk(anc)
            )
            text_hint = False
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if any(h in arg.value.lower() for h in _PRINT_ERROR_HINTS):
                        text_hint = True
            if in_except or text_hint:
                findings.add(
                    f"{rel}:{node.lineno}: print() used for error/status reporting "
                    f"in {path.parent.name}/. Use the `logging` module so failures "
                    f"are observable (log aggregation, audit trail) instead of "
                    f"console-only output that vanishes in production."
                )


# --- Rule 3: missing module docstring -----------------------------------------
def check_module_docstrings(findings: Findings) -> None:
    for path in _py_files(LINT_DIRS):
        rel = str(path.relative_to(REPO))
        if path.name == "__init__.py":
            continue  # package markers may legitimately be empty
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError:
            continue
        if ast.get_docstring(tree) is None:
            findings.add(
                f"{rel}: missing module docstring. Every module in the linted "
                f"trees is part of the audited runtime or its tooling and must "
                f"state what it does at the top of the file."
            )


# --- Rule 4: leftover broken-window markers left in code ----------------------
def check_no_todos(findings: Findings) -> None:
    for path in _py_files(LINT_DIRS):
        rel = str(path.relative_to(REPO))
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError) as exc:
            findings.add(f"{rel}: could not read ({exc}); cannot lint.")
            continue
        for i, line in enumerate(lines, start=1):
            if TODO_RE.search(line):
                findings.add(
                    f"{rel}:{i}: TODO/FIXME/XXX left in code — broken-window rule "
                    f"(OPERATING_RULES SS1 'no deferred cleanup'). Fix now, file it "
                    f"in TODOS.md with an owner, or remove the comment."
                )


CHECKS = [
    check_swallowed_errors,
    check_print_for_errors,
    check_module_docstrings,
    check_no_todos,
]


# --- --fix: safe, mechanical fixes only ---------------------------------------
def _is_stdlib(modname: str) -> bool:
    top = modname.split(".")[0]
    return top in sys.stdlib_module_names


def _sort_leading_imports(text: str) -> str:
    """Sort a leading contiguous import block (after any module docstring) into
    stdlib / third-party / local groups, alphabetical within each group, with
    exactly one blank line between non-empty groups and exactly one blank line
    after the whole block (PEP8-style). Only touches a simple leading block --
    never reorders imports scattered through the file (that would risk
    changing behavior for conditional imports). Idempotent by construction:
    re-running on already-sorted output must be a no-op, so this rebuilds the
    separator blank lines from scratch every time rather than trying to count
    and preserve whatever separators happened to exist on disk."""
    lines = text.splitlines(keepends=True)
    i = 0
    # skip module docstring if present
    if lines and lines[0].lstrip().startswith(('"""', "'''")):
        quote = lines[0].lstrip()[:3]
        if lines[0].count(quote) >= 2 and len(lines[0].strip()) > 3:
            i = 1
        else:
            i += 1
            while i < len(lines) and quote not in lines[i]:
                i += 1
            i += 1
    start = i
    # skip blank lines right after docstring
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    end = start
    import_re = re.compile(r"^(import |from )\S")
    while end < len(lines) and (import_re.match(lines[end]) or lines[end].strip() == ""):
        end += 1
    block = lines[start:end]
    import_lines = [l for l in block if import_re.match(l)]
    if len(import_lines) < 2:
        return text  # nothing meaningful to sort
    # Exactly one blank line must separate the block from the next code line
    # (unless nothing follows). Compute this from what follows the block in
    # the ORIGINAL file, never from the block's own (about-to-be-rebuilt)
    # content -- that is what made the previous version grow an extra blank
    # line on every re-run (not idempotent).
    trailer_blank = 1 if (end < len(lines) and lines[end].strip() != "") else 0
    stdlib, thirdparty, local = [], [], []
    for l in import_lines:
        m = re.match(r"^(?:import|from)\s+([A-Za-z0-9_\.]+)", l)
        mod = m.group(1) if m else ""
        if mod.startswith(("worker", "ai", "api", "tools", "web", "mobile",
                           "src", "app", "lib", "libs", "pkg", "cmd",
                           "scripts", "services", "packages", ".")):
            local.append(l)
        elif _is_stdlib(mod):
            stdlib.append(l)
        else:
            thirdparty.append(l)
    groups = [g for g in (sorted(stdlib), sorted(thirdparty), sorted(local)) if g]
    new_block = []
    for idx, group in enumerate(groups):
        new_block.extend(group)
        if idx < len(groups) - 1:
            new_block.append("\n")  # exactly one separator blank between groups
    new_block.extend(["\n"] * trailer_blank)
    if new_block == block:
        return text  # already in sorted form; do not touch the file
    return "".join(lines[:start] + new_block + lines[end:])


def apply_fixes(path: pathlib.Path) -> bool:
    """Apply safe auto-fixes in place. Returns True if the file changed."""
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    text = original
    # trailing whitespace
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    # missing final newline
    if text and not text.endswith("\n"):
        text += "\n"
    # simple leading import sort (skip if it would break a syntactically odd file)
    try:
        ast.parse(text)
        sorted_text = _sort_leading_imports(text)
        ast.parse(sorted_text)  # never apply a sort that breaks parsing
        text = sorted_text
    except SyntaxError:
        pass
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Pure-stdlib project linter (trailing-whitespace/newline/"
                    "import-sort autofix, plus swallowed-error / print-for-errors "
                    "/ missing-docstring / TODO checks)."
    )
    ap.add_argument("--fix", action="store_true",
                     help="Auto-fix trailing whitespace, missing final newline, "
                          "and leading import-block sorting. Modifies files.")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    fixed_files: list[str] = []
    if args.fix:
        for path in _py_files(LINT_DIRS):
            if apply_fixes(path):
                fixed_files.append(str(path.relative_to(REPO)))

    findings = Findings()
    for check in CHECKS:
        check(findings)

    if fixed_files:
        print(f"lint.py --fix: auto-fixed {len(fixed_files)} file(s):")
        for f in fixed_files:
            print(f"  - {f}")

    if findings.ok():
        print("lint.py: OK — no violations "
              "(swallowed-errors, print-for-errors, docstrings, TODO/FIXME).")
        return 0

    print("lint.py: FAIL — violation(s):", file=sys.stderr)
    for v in findings.violations:
        print(f"  - {v}", file=sys.stderr)
    print(f"\n{len(findings.violations)} violation(s). Run with --fix for the "
          f"mechanical subset (whitespace/newline/import-sort); the rest need a "
          f"real code change.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
