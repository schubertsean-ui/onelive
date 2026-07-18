#!/usr/bin/env python3
"""Deterministic trust-invariant gate for OneLive CI.

This replaces the AI PR-review action with hermetic, in-repo static checks. An AI
reviewer's thoroughness varies run to run; a trust *invariant* must be enforced by
a check that gives the same answer every time. This gate is that check.

It enforces three invariants, each tied to the product's defensible core
("how does OneLive know this show is actually happening tonight?"):

  1. NO DYNAMIC SQL. Every SQL statement is either a static string with %s bound
     parameters, or composed via psycopg2.sql (SQL/Identifier/Literal). f-strings,
     %-formatting, .format(), and string concatenation into SQL are forbidden.
     Rationale: injection is a trust-and-safety hole; parameterization is
     non-negotiable, so we make it mechanically impossible to regress.

  2. ADS/TASTEMAKER CODE MUST NOT TOUCH THE GATING/PROMOTION PIPELINE. Contextual
     ads "cannot influence ranking" (migration 0004) and tastemaker content is
     kept separate from verified events. So no ads/tastemaker module may import
     worker.gating or worker.promote.

  3. AI NEVER PUBLISHES DIRECTLY. The extraction/provider layer (ai/, worker/
     ai_extract) must not import worker.promote — a gate always sits between
     extraction and publish. Extraction may call the gate; it may never promote.

Exit codes: 0 = all invariants hold; 1 = at least one violation (fail LOUDLY with
a specific, actionable message per finding — never a vague "check failed").
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys
from dataclasses import dataclass, field

REPO = pathlib.Path(__file__).resolve().parent.parent

# Directories whose .py files run SQL and must obey invariant 1.
# NOTE (2026-07-17 enumerated-list audit): kept for the focused checks
# below, but the SQL/promote invariants now ALSO sweep every production
# .py repo-wide via _all_production_py() — a future scripts/ dir is
# covered automatically, the same closure discipline as the exam scan.
SQL_DIRS = ["api", "worker", "tools"]

# Dependency/build trees excluded from repo-wide sweeps.
SKIP_PARTS = {"__pycache__", "node_modules", ".git", ".venv", "venv",
              "dist", "build", ".eggs", ".tox"}


def _all_production_py() -> list[pathlib.Path]:
    """Every .py in the repo except dependency/build trees and tests/.
    tests/ is excluded by DESIGN, not oversight: tests legitimately build
    dynamic SQL against stub cursors and import worker.promote to test
    the guard itself — the invariants govern production code."""
    return [p for p in REPO.rglob("*.py")
            if not (set(p.parts) & SKIP_PARTS)
            and p.relative_to(REPO).parts[0] != "tests"]

# Modules that constitute the gate/promotion pipeline.
PIPELINE_MODULES = ("worker.gating", "worker.promote")

# Substrings that mark a file as ads/tastemaker (invariant 2).
ADS_TASTEMAKER_MARKERS = ("ads", "tastemaker", "advertiser", "ad_campaign", "curat")

# Files allowed to import worker.promote (the only legitimate promoters).
# The orchestrator and its entrypoint are DELIBERATELY absent: the AI loop must
# never be able to publish, so if either re-acquires a worker.promote import
# this gate fails. "AI never auto-promotes" is enforced here structurally, not
# by a runtime flag.
PROMOTE_IMPORT_ALLOWLIST = {
    "api/ops_candidates.py",  # operator action: human-reviewed promote endpoint
}


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
    return [p for p in out if "__pycache__" not in p.parts]


# --- Invariant 1: no dynamic SQL ------------------------------------------------
# We detect SQL by AST: any call to `.execute(...)` whose first argument is built
# with an f-string, %-format, .format(), or string '+' is a violation. Static
# string literals and psycopg2.sql.* compositions are allowed.
_SQL_METHODS = {"execute", "executemany", "mogrify"}


class _SqlVisitor(ast.NodeVisitor):
    def __init__(self, relpath: str, findings: Findings):
        self.relpath = relpath
        self.findings = findings

    def _dynamic_reason(self, node: ast.AST) -> str | None:
        # f-string
        if isinstance(node, ast.JoinedStr):
            return "f-string"
        if isinstance(node, ast.BinOp):
            # "..." % (...)  or  "..." + x
            if isinstance(node.op, ast.Mod):
                return "%-format"
            if isinstance(node.op, ast.Add):
                return "string concatenation"
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "format":
                # allow psycopg2.sql.SQL(...).format(...) — that IS the safe path.
                if _is_psycopg_sql(f.value):
                    return None
                return ".format()"
        return None

    def visit_Call(self, node: ast.Call) -> None:
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in _SQL_METHODS and node.args:
            reason = self._dynamic_reason(node.args[0])
            if reason:
                self.findings.add(
                    f"{self.relpath}:{node.args[0].lineno}: dynamic SQL via {reason} "
                    f"passed to .{f.attr}(). Use a static string with %s bound params, "
                    f"or compose with psycopg2.sql (SQL/Identifier/Literal)."
                )
        self.generic_visit(node)


def _is_psycopg_sql(node: ast.AST) -> bool:
    """True if `node` is a psycopg2.sql.SQL(...) call (so .format() on it is safe)."""
    if isinstance(node, ast.Call):
        fn = node.func
        # sql.SQL(...) or psycopg2.sql.SQL(...)
        if isinstance(fn, ast.Attribute) and fn.attr == "SQL":
            return True
    return False


def check_no_dynamic_sql(findings: Findings) -> None:
    for path in _all_production_py():
        rel = str(path.relative_to(REPO))
        try:
            tree = ast.parse(path.read_text(), filename=rel)
        except SyntaxError as exc:
            findings.add(f"{rel}: could not parse ({exc}); cannot verify SQL safety.")
            continue
        _SqlVisitor(rel, findings).visit(tree)


# --- Import-graph invariants (2 and 3) ------------------------------------------
def _imports_of(path: pathlib.Path) -> set[str]:
    """Return the set of dotted module names imported by a file."""
    mods: set[str] = set()
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except SyntaxError:
        return mods
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            # from worker.promote import x  -> worker.promote
            mods.add(node.module)
    return mods


def check_ads_tastemaker_isolation(findings: Findings) -> None:
    for path in _all_production_py():
        rel = str(path.relative_to(REPO))
        name = path.name.lower()
        if not any(m in name for m in ADS_TASTEMAKER_MARKERS):
            continue
        for mod in _imports_of(path):
            if mod.startswith(PIPELINE_MODULES):
                findings.add(
                    f"{rel}: ads/tastemaker file imports {mod}. Contextual ads and "
                    f"tastemaker content must never touch the gating/promotion "
                    f"pipeline (ads cannot influence ranking; tastemaker stays "
                    f"separate from verified events)."
                )


def check_ai_never_promotes(findings: Findings) -> None:
    # ai/* and worker/ai_extract.py may call the gate, never promote directly.
    ai_files = list((REPO / "ai").rglob("*.py")) + [REPO / "worker" / "ai_extract.py"]
    for path in ai_files:
        if not path.exists() or "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(REPO))
        for mod in _imports_of(path):
            if mod.startswith("worker.promote"):
                findings.add(
                    f"{rel}: extraction/AI layer imports worker.promote. AI never "
                    f"publishes directly — a gate must sit between extraction and "
                    f"promote. Route through the gate, never promote from here."
                )


def check_promote_import_allowlist(findings: Findings) -> None:
    # Anything importing worker.promote must be on the allowlist, so new promoters
    # are a deliberate, reviewed decision — not something that slips in silently.
    for path in _all_production_py():
        rel = str(path.relative_to(REPO))
        if rel in PROMOTE_IMPORT_ALLOWLIST:
            continue
        for mod in _imports_of(path):
            if mod.startswith("worker.promote"):
                findings.add(
                    f"{rel}: imports worker.promote but is not on the promote "
                    f"allowlist in tools/trust_gate.py. Promotion is the publish "
                    f"step; if this file legitimately promotes, add it to the "
                    f"allowlist in the same change (deliberate, not silent)."
                )


# The exam channel (R-013's measurement instrument) may only be invoked from
# the golden-exam runner and tests — pipeline code must never construct an
# exam-mode provider (it bypasses the extraction ratification gate).
EXAM_MODE_ALLOWLIST_PREFIXES = (
    "ai/golden_exam.py",        # the exam runner — the channel's only real caller
    "tests/",                    # hermetic tests of the channel itself
    "ai/claude_provider.py",     # where the channel is defined
    "tools/trust_gate.py",       # this check's own detection string
)


def check_exam_mode_confined(findings: Findings) -> None:
    # Repo-root *.py files scan too (evaluator r7): a root-level script
    # driving the exam runner must be as visible as a worker/ one.
    # REPO-WIDE scan (r23 nit): future directories (scripts/, etc.) are
    # covered automatically; only dependency/build trees are excluded
    # (SKIP_PARTS, single-sourced — this scan INCLUDES tests/, which the
    # allowlist below then admits deliberately).
    candidates = [p for p in REPO.rglob("*.py")
                  if not (set(p.parts) & SKIP_PARTS)]
    for path in candidates:
        if "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(REPO))
        if any(rel.startswith(pref) for pref in EXAM_MODE_ALLOWLIST_PREFIXES):
            continue
        # ANY mention — not just the literal `exam_mode=True` — so
        # `exam_mode = True`, **{"exam_mode": True}, aliasing, or wrapper
        # construction cannot slip past (evaluator finding, PR #25 r1).
        # Deliberately over-broad: this guards a ratification-gate bypass,
        # and a false positive is a rename away from clean.
        text = path.read_text(encoding="utf-8", errors="replace")
        if "exam_mode" in text:
            findings.add(
                f"{rel}: references exam_mode outside the exam channel "
                f"allowlist (ai/golden_exam.py, tests/). exam_mode bypasses "
                f"the extraction ratification gate and is reserved for the "
                f"golden-set exam runner only — any reference here is a "
                f"violation, however constructed."
            )
        # Same-hole closure at the static layer (evaluator, PR #25 r5):
        # pipeline code must not import or invoke the exam RUNNER either —
        # a wrapper that drives ai.golden_exam would put the allowlisted
        # runner on the call stack without ever containing "exam_mode".
        # The runtime stack-walk allowlists repo frames (r7); this scan
        # makes the same wrapper visible in CI before it can run.
        if "golden_exam" in text:
            findings.add(
                f"{rel}: references golden_exam outside the exam channel "
                f"allowlist. Driving the exam runner from pipeline code "
                f"would reach the ratification-gate bypass transitively — "
                f"the runner may only be invoked by CI, tests, or a human "
                f"(python -m ai.golden_exam), never by pipeline code."
            )


def main() -> int:
    findings = Findings()
    check_no_dynamic_sql(findings)
    check_ads_tastemaker_isolation(findings)
    check_ai_never_promotes(findings)
    check_promote_import_allowlist(findings)
    check_exam_mode_confined(findings)

    if findings.ok():
        print("trust_gate: OK — all trust invariants hold "
              "(no dynamic SQL; ads/tastemaker isolated; AI never promotes).")
        return 0

    print("trust_gate: FAIL — trust invariant violation(s):", file=sys.stderr)
    for v in findings.violations:
        print(f"  - {v}", file=sys.stderr)
    print(f"\n{len(findings.violations)} violation(s). "
          f"These are trust-and-safety invariants; fix in-change, do not defer.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
