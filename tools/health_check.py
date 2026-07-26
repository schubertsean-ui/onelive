#!/usr/bin/env python3
"""System health check — the whole-system checkup, computed not asserted.

Greppable summary: measures the structural health of the repository against
`docs/BAR.md` and emits a markdown snapshot. Supports `--baseline <git-ref>` to
produce a BEFORE/AFTER comparison, which is how a revamp proves itself instead
of describing itself. No network, no database, no AI: every number comes from
git and the working tree, so the same command gives the same answer to anyone.

WHY THIS EXISTS (founder-directed 2026-07-26): the 2026-07-26 audit produced its
numbers by hand, in chat. Hand-computed numbers drift the moment they are quoted
— three of that audit's figures were wrong within hours, and its own independent
reviewer caught the stale copies. A metric a human retypes is a metric that lies
eventually. This tool is the durable form: the accounting becomes reproducible,
so "is the system getting better or worse" stops being a matter of recollection.

WHAT IT DELIBERATELY DOES NOT DO. It does not pass or fail. It is a thermometer,
not a gate. Wiring it into `tools/validate` as a blocking check would be a
gate-threshold change and is founder-crucial; the cadence and the escalation
rules live in `docs/HEALTH_CHECK.md`. What it DOES do is refuse to be silently
wrong: any metric it cannot compute is printed as `UNVERIFIED` with the reason,
never as a zero and never omitted. "We could not measure" must never look
identical to "the number is fine" — the project's founding anti-pattern.

Metric provenance is carried in the output: each row names the `docs/BAR.md` row
it serves, so a reader can trace a number to the standard it is evidence for.
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass, field

REPO = pathlib.Path(__file__).resolve().parent.parent

# Code-mass categories. The split is the one the audit found load-bearing:
# product vs the machinery around it vs work that is not v1 at all.
CATEGORIES: dict[str, tuple[str, ...]] = {
    "product": ("web", "api", "worker", "ai", "supabase"),
    "tests": ("tests",),
    "harness_tools": ("tools",),
    "brain": ("brain",),
    "off_mission": ("social", "ventures", "mobile"),
}
CODE_SUFFIXES = (".py", ".ts", ".tsx", ".sql", ".js", ".mjs", ".sh")

# The documents a builder must read before writing code. Kept explicit rather
# than derived, because "what binds you" is a decision, not a glob.
READ_BEFORE_CODE = (
    "CLAUDE.md",
    "docs/BAR.md",
    "docs/V1.md",
    "docs/HOW_WE_WORK.md",
)

# The set that WAS binding before the 2026-07-26 restructure. Needed because
# comparing today's CANON list against a baseline where three of its four files
# did not exist measures nothing — it reports a surface that "grew" from one
# document to four, which is the opposite of what happened. When most of the
# modern set is absent at a ref, the legacy set is measured instead and the
# output says which set it used. An apples-to-oranges comparison presented as a
# trend is worse than no comparison.
LEGACY_READ_BEFORE_CODE = (
    "CLAUDE.md",
    "docs/OPERATING_RULES.md",
    "docs/WORLD_CLASS.md",
    "docs/KAIZEN.md",
    "docs/skills/construction_loop.md",
    "docs/hats/README.md",
    "docs/skills/adversarial_review_v2.md",
)

_BAR_ROW = re.compile(r"^\|\s*([A-JP]\d+)\s*\|")
_BAR_STATUS = re.compile(r"\*\*(MET|NOT MET|NOT BUILT|UNMEASURED)[^*]*\*\*")
_RECORD_ROW = re.compile(r"^\|\s*(R-\d+)\s*\|")
_RED_CLASS_ROW = re.compile(r"^\|\s*([a-z][a-z0-9-]+)\s*\|")


class Unverified(Exception):
    """A metric could not be computed. Carried, printed, never silently zeroed."""


@dataclass
class Report:
    rows: list[tuple[str, str, str, str]] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)

    def add(self, metric: str, before: object, after: object, bar_row: str) -> None:
        self.rows.append((metric, str(before), str(after), bar_row))

    def note_unverified(self, metric: str, reason: str) -> None:
        self.unverified.append(f"{metric}: {reason}")
        self.rows.append((metric, "UNVERIFIED", "UNVERIFIED", "—"))


def _git(*args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise Unverified(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def _tracked_files(ref: str | None) -> list[str]:
    if ref is None:
        return [p for p in _git("ls-files").splitlines() if p]
    return [p for p in _git("ls-tree", "-r", "--name-only", ref).splitlines() if p]


def _read(ref: str | None, path: str) -> str:
    if ref is None:
        target = REPO / path
        if not target.is_file():
            raise Unverified(f"{path} not present in the working tree")
        return target.read_text(encoding="utf-8", errors="replace")
    return _git("show", f"{ref}:{path}")


def _line_count(ref: str | None, paths: list[str]) -> int:
    total = 0
    for path in paths:
        try:
            total += len(_read(ref, path).splitlines())
        except Unverified:
            continue
    return total


def code_mass(ref: str | None) -> dict[str, int]:
    files = _tracked_files(ref)
    out: dict[str, int] = {}
    for name, roots in CATEGORIES.items():
        selected = [
            f for f in files
            if f.endswith(CODE_SUFFIXES) and any(f == r or f.startswith(r + "/") for r in roots)
        ]
        out[name] = _line_count(ref, selected)
    return out


def prose_words(ref: str | None) -> int:
    files = [f for f in _tracked_files(ref) if f.endswith(".md")]
    total = 0
    for path in files:
        try:
            total += len(_read(ref, path).split())
        except Unverified:
            continue
    return total


def _measure_set(ref: str | None, paths: tuple[str, ...]) -> tuple[int, int]:
    words = found = 0
    for path in paths:
        try:
            words += len(_read(ref, path).split())
            found += 1
        except Unverified:
            continue
    return words, found


def read_before_code(ref: str | None) -> tuple[int, int, str]:
    """(words, document_count, which_set) of the binding pre-code reading surface.

    Picks the set that was actually binding at `ref`: if fewer than half of the
    modern CANON documents exist there, the legacy set is measured and named in
    the return value. Comparing today's four files against a baseline that had
    one of them would report growth where the truth is consolidation.
    """
    modern_words, modern_found = _measure_set(ref, READ_BEFORE_CODE)
    if modern_found * 2 >= len(READ_BEFORE_CODE):
        return modern_words, modern_found, "CANON (post-2026-07-26)"
    legacy_words, legacy_found = _measure_set(ref, LEGACY_READ_BEFORE_CODE)
    return legacy_words, legacy_found, "legacy set (pre-2026-07-26)"


def bar_status(ref: str | None) -> dict[str, int]:
    try:
        text = _read(ref, "docs/BAR.md")
    except Unverified:
        return {}
    counts = {"rows": 0, "MET": 0, "NOT MET": 0, "UNMEASURED": 0, "NOT BUILT": 0, "purpose_rows": 0}
    for line in text.splitlines():
        row = _BAR_ROW.match(line)
        if not row:
            continue
        counts["rows"] += 1
        if row.group(1).startswith("P"):
            counts["purpose_rows"] += 1
        status = _BAR_STATUS.search(line)
        if status:
            counts[status.group(1)] += 1
    return counts


def record_status(ref: str | None) -> tuple[int, int]:
    """(open, resolved) RECORD rows. The status cell is the LAST populated cell."""
    try:
        text = _read(ref, "docs/RECORD.md")
    except Unverified:
        raise
    open_n = resolved_n = 0
    for line in text.splitlines():
        if not _RECORD_ROW.match(line):
            continue
        cells = [c.strip() for c in line.split("|") if c.strip()]
        status = cells[-1] if cells else ""
        if status.upper().startswith("RESOLVED"):
            resolved_n += 1
        elif status.upper().startswith("OPEN"):
            open_n += 1
    return open_n, resolved_n


def red_class_count(ref: str | None) -> int:
    text = _read(ref, "docs/memory/RED_CLASSES.md")
    return sum(1 for line in text.splitlines() if _RED_CLASS_ROW.match(line))


def escape_count(ref: str | None) -> int:
    """Escaped defects, counted the way the Kaizen convention defines them."""
    return _read(ref, "docs/metrics/KAIZEN_LEDGER.md").count("M3-ESCAPE")


def _module_name(path: str) -> str:
    return path[:-3].replace("/", ".") if path.endswith(".py") else path


def _resolve_import_from(node: ast.ImportFrom, path: str) -> list[str]:
    """Absolute dotted name(s) an `from ... import ...` statement reaches.

    `node.level` is the number of leading dots. Level 0 is already absolute.
    Level N walks N-1 packages up from the importing file's own package, which
    is what Python does — so `from .confidence import x` in `worker/promote.py`
    resolves to `worker.confidence`, and `from ..ai_extract import y` in
    `worker/convergence/node.py` resolves to `worker.ai_extract`.

    Returns [] when the level walks above the repo root: that is a broken import
    the interpreter would reject, and inventing a name for it would be worse than
    reporting nothing.
    """
    if node.level == 0:
        base = node.module or ""
    else:
        parts = path.split("/")[:-1]      # the importing file's package parts
        if node.level > 1:
            if node.level - 1 > len(parts):
                return []                 # walks above the repo root: broken import
            parts = parts[: -(node.level - 1)]
            if not parts:
                return []
        prefix = ".".join(parts)
        if not prefix:
            return []
        base = f"{prefix}.{node.module}" if node.module else prefix
    if not base:
        return []
    # THE IMPORTED NAMES COUNT TOO. `from worker import confidence` reaches
    # `worker.confidence`, not just `worker` — and recording only the base made a
    # module imported that way look UNWIRED, a false dead-code claim on an F5
    # metric (gemini/dataflow-taint, PR #80). tests/test_convergence_isolation.py
    # already records base AND base.alias for exactly this reason; this metric did
    # not, so the same import shape meant two different things in two tools.
    names = [base]
    for alias in node.names:
        if alias.name and alias.name != "*":
            names.append(f"{base}.{alias.name}")
    return names


_ASGI_APP = re.compile(r"^app\s*=|FastAPI\(|Flask\(", re.MULTILINE)


def _is_entrypoint(path: str, source: str, workflow_text: str) -> bool:
    """True when a module is REACHED rather than imported.

    Three shapes, each calibrated against a real file in this repo rather than
    guessed:
      * a `__main__` guard — an ordinary CLI;
      * a module-level ASGI/WSGI app (`api/main.py` defines `app = FastAPI()`
        and is launched by uvicorn, so no first-party file ever imports it);
      * a script a workflow invokes by filename (`tools/sample_feed.py` is run
        by a GitHub Actions step and has no `__main__` guard).
    Missing any of these would report a live entrypoint as dead code, and a
    detector that cries wolf is one nobody reads.
    """
    if "__main__" in source:
        return True
    if _ASGI_APP.search(source):
        return True
    return path in workflow_text or pathlib.Path(path).name in workflow_text


def unwired_modules(ref: str | None) -> list[str]:
    """First-party Python modules imported by NOTHING except tests.

    This is the mechanical form of BAR row F5 ("wire it or delete it"), which
    the 2026-07-26 audit found NOT MET with no gate behind it. A module that only
    tests import is built, green, and unreachable from production — the audit's
    single most repeated finding, and previously only discoverable by hand.

    Deliberately conservative: it reports modules with zero non-test importers,
    counts a package's `__init__` as its package, and skips entrypoints (files
    with a `__main__` guard) because a script is reached by a runner, not an
    import. Over-reporting would train readers to ignore it, so where this is
    unsure it stays silent — and that limitation is stated here rather than
    discovered later.
    """
    files = [f for f in _tracked_files(ref) if f.endswith(".py")]
    workflow_text = ""
    for wf in (f for f in _tracked_files(ref) if f.startswith(".github/workflows/")):
        try:
            workflow_text += _read(ref, wf)
        except Unverified:
            continue
    first_party_roots = {"web", "api", "worker", "ai", "brain", "social", "ventures", "tools"}
    candidates: dict[str, str] = {}
    importers: dict[str, set[str]] = {}

    for path in files:
        root = path.split("/")[0]
        if root not in first_party_roots:
            continue
        try:
            source = _read(ref, path)
        except Unverified:
            continue
        module = _module_name(path)
        if not _is_entrypoint(path, source, workflow_text):
            candidates[module] = path
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                # RELATIVE IMPORTS RESOLVED. `from .confidence import x` inside
                # worker/ leaves node.module == "confidence", which matches no
                # candidate key (those are full dotted names like
                # "worker.confidence") — so a module imported only relatively
                # looked unwired. tests/test_convergence_isolation.py already
                # resolves node.level for the same reason; this metric did not.
                # (Reviewer nit, gemini seat, PR #80.)
                names = _resolve_import_from(node, path)
            else:
                continue
            for name in names:
                if not name:
                    continue
                importers.setdefault(name, set()).add(path)

    unwired = []
    for module, path in sorted(candidates.items()):
        # A module counts as imported if it, or the package it lives in, is
        # imported by any non-test first-party file.
        seen: set[str] = set()
        for key, srcs in importers.items():
            if key == module or key.startswith(module + "."):
                seen |= srcs
        package = module.rsplit(".", 1)[0]
        if module.endswith(".__init__"):
            for key, srcs in importers.items():
                if key == package or key.startswith(package + "."):
                    seen |= srcs
        production = {s for s in seen if not s.startswith("tests/") and s != path}
        if not production:
            unwired.append(path)
    return unwired


def validate_check_count(ref: str | None) -> int:
    text = _read(ref, "tools/validate")
    return sum(1 for line in text.splitlines() if line.strip().startswith("run_check "))


# The files whose change would constitute a GATE change. Deliberately an
# enumeration, not `tools/`: adding a new non-gating tool (this file, for
# instance) changes tools/ without touching a single threshold, and a metric that
# counts that as a gate change is measuring the wrong thing. Its own test caught
# exactly that on 2026-07-26 — the day after health_check.py landed in tools/.
# Adding a file here is how a new gate declares itself auditable.
GATE_FILES = (
    "tools/validate",
    "tools/trust_gate.py",
    "tools/lint.py",
    "tools/deferral_scan.py",
    "tools/adversarial_review.py",
    "tools/kaizen_trends.py",
    "tools/construction_gate.py",
    "tools/blocking_failure_check.py",
    "tools/governance_claims_lint.py",
    "tools/skip_record_binding.py",
    "ai/exam_thresholds.py",
)


def gate_files_changed(baseline: str) -> list[str]:
    """WHICH gate-defining files changed since `baseline`.

    Returning the names rather than a count is the difference between a metric you
    can act on and a number you argue with: a declared additive change (wiring a
    new advisory row into `tools/validate`) and an undeclared threshold edit both
    read as "1" but mean opposite things. The reader still judges the diff — no
    test can decide whether a change loosened a gate — but the set is the honest
    unit for that judgement.
    """
    # Compared against the WORKING TREE, not HEAD. Every other metric in this
    # tool reads the tree as it currently is, and a gate edit that is staged but
    # not yet committed is still a gate edit the reader needs to see — reporting
    # "none" until commit would make the metric quietest exactly when it matters.
    out = _git("diff", "--name-only", baseline, "--", *GATE_FILES)
    return sorted({line.strip() for line in out.splitlines() if line.strip()})


def gate_code_changed(baseline: str) -> int:
    """Count form of `gate_files_changed`, for the snapshot table."""
    return len(gate_files_changed(baseline))


def build(baseline: str | None) -> Report:
    rep = Report()
    refs: list[str | None] = [baseline, None]

    def pair(fn, *args):
        """Measure the BEFORE column (index 0) and the AFTER column (index 1).

        **The identity test that used to live here was a false-confidence bug**,
        caught by the independent reviewer (openai / absence-only, PR #76). It read
        `if ref is baseline and baseline is None` — but `refs` is
        `[baseline, None]`, so with no `--baseline` BOTH entries are `None` and
        both matched, meaning the tool skipped the *current* measurement too and
        rendered `—` across the board while still printing "All metrics computed".
        A health check that measures nothing and reports success is worse than no
        health check.

        Position, not identity: only index 0 may be skipped, and only when there
        is genuinely no baseline to compare against.
        """
        vals = []
        for index, ref in enumerate(refs):
            if index == 0 and baseline is None:
                vals.append("—")          # no baseline given: nothing to compare
                continue
            try:
                vals.append(fn(ref, *args))
            except Unverified as exc:
                vals.append(f"UNVERIFIED ({exc})")
        return vals

    masses = pair(code_mass)
    for name in CATEGORIES:
        b = masses[0][name] if isinstance(masses[0], dict) else masses[0]
        a = masses[1][name] if isinstance(masses[1], dict) else masses[1]
        rep.add(f"Code lines — {name}", b, a, "F5 / J8")

    b, a = pair(prose_words)
    rep.add("Prose words (all tracked Markdown)", b, a, "J8")

    rbc = pair(read_before_code)
    if isinstance(rbc[1], tuple):
        b_rbc = rbc[0] if isinstance(rbc[0], tuple) else ("—", "—", "—")
        rep.add("Read-before-code words", b_rbc[0], rbc[1][0], "J8")
        rep.add("Read-before-code documents", b_rbc[1], rbc[1][1], "J8")
        rep.add("  ...which binding set was measured", b_rbc[2], rbc[1][2], "J8")

    bars = pair(bar_status)
    after = bars[1] if isinstance(bars[1], dict) else {}
    before = bars[0] if isinstance(bars[0], dict) else {}
    for key, bar in (("rows", "—"), ("purpose_rows", "P1–P14"), ("MET", "—"),
                     ("NOT MET", "—"), ("UNMEASURED", "—"), ("NOT BUILT", "—")):
        # An unmeasured baseline is "—", never 0. Defaulting to 0 asserted that
        # ZERO bar rows existed before the run — a fabricated measurement, and
        # the worse kind because it renders as a plausible delta (0 -> 55 reads
        # as "we added 55 rows"). Caught by the gemini/dataflow-taint seat on
        # PR #80 as CLASS:false-confidence-gate; a sibling of the same defect in
        # `pair()` above was fixed earlier the same day, and this second site
        # survived because that fix was applied where it was found rather than
        # swept for the class.
        rep.add(f"BAR rows — {key}",
                before.get(key, "—") if before else "—",
                after.get(key, "—"), bar)

    try:
        rec_a = record_status(None)
        rec_b = record_status(baseline) if baseline else ("—", "—")
        rep.add("RECORD rows OPEN", rec_b[0], rec_a[0], "F7")
        rep.add("RECORD rows RESOLVED", rec_b[1], rec_a[1], "F7")
    except Unverified as exc:
        rep.note_unverified("RECORD rows", str(exc))

    for label, fn, bar in (("Red classes indexed", red_class_count, "J6"),
                           ("Escaped defects (M3)", escape_count, "G4"),
                           # Named for what it COUNTS. It was "validate checks",
                           # which read as the whole summary surface while the
                           # function counts `run_check ` lines only — advisory
                           # and skip rows are not included. A metric whose label
                           # over-claims its own scope is a stale number waiting
                           # to happen (reviewer nit, openai seat, PR #80).
                           ("validate blocking checks (run_check lines)",
                            validate_check_count, "—")):
        vals = pair(fn)
        rep.add(label, vals[0], vals[1], bar)

    try:
        unwired_after = unwired_modules(None)
        unwired_before = unwired_modules(baseline) if baseline else []
        rep.add("Unwired modules (prod-unreachable)",
                len(unwired_before) if baseline else "—", len(unwired_after), "F5")
    except Unverified as exc:
        rep.note_unverified("Unwired modules", str(exc))
        unwired_after = []

    if baseline:
        try:
            changed = gate_files_changed(baseline)
            rep.add("Gate/threshold files changed vs baseline", "—",
                    ", ".join(changed) if changed else "0 — none", "J5")
        except Unverified as exc:
            rep.note_unverified("Gate code diff", str(exc))

    rep.unwired_detail = unwired_after  # type: ignore[attr-defined]
    return rep


def render(rep: Report, baseline: str | None, head: str) -> str:
    lines = [
        "# System health check",
        "",
        f"Generated by `tools/health_check.py`. HEAD `{head}`"
        + (f", baseline `{baseline}`." if baseline else ", no baseline (single snapshot)."),
        "",
        "Every number is computed from git and the working tree. No network, no",
        "database, no model — the same command gives anyone the same answer.",
        "This is a thermometer, not a gate: it does not pass or fail. Cadence and",
        "escalation live in `docs/HEALTH_CHECK.md`.",
        "",
        "| Metric | Before | After | BAR row |",
        "|---|---|---|---|",
    ]
    for metric, before, after, bar in rep.rows:
        lines.append(f"| {metric} | {before} | {after} | {bar} |")
    detail = getattr(rep, "unwired_detail", [])
    if detail:
        lines += [
            "",
            f"## Unwired modules — {len(detail)} production-unreachable (BAR F5)",
            "",
            "Imported by nothing except tests. Each is built, green, and reachable",
            "from no production path. `wire it or delete it` — a module nothing can",
            "reach is not done.",
            "",
        ]
        lines += [f"- `{p}`" for p in detail]
    if rep.unverified:
        lines += ["", "## UNVERIFIED — measured nothing, and says so", ""]
        lines += [f"- {u}" for u in rep.unverified]
    else:
        # Only claim completeness when the CURRENT column actually carries
        # numbers. The reviewer's blocker was a report that said "All metrics
        # computed" over a table of em-dashes; `rep.unverified` did not catch it
        # because a skipped measurement never raised. Scoped to the after-column
        # so a legitimately absent BEFORE column (no --baseline) is not misread as
        # a failure.
        blank_after = [row[0] for row in rep.rows
                       if str(row[2]).strip() in ("—", "")]
        if blank_after:
            lines += [
                "",
                f"## INCOMPLETE — {len(blank_after)} metric(s) have no CURRENT value",
                "",
                "This report does NOT claim to have measured the system. A health "
                "check that renders placeholders and reports success is worse than "
                "no health check.",
                "",
            ]
            lines += [f"- {label}" for label in blank_after]
            lines += [""]
        else:
            lines += ["", "All metrics computed; nothing unverified.", ""]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Whole-system health check (computed, not asserted).")
    ap.add_argument("--baseline", help="git ref to compare against (e.g. a tag or SHA)")
    ap.add_argument("--out", help="write the markdown snapshot here instead of stdout")
    args = ap.parse_args(argv)

    try:
        head = _git("rev-parse", "--short", "HEAD").strip()
    except Unverified as exc:
        print(f"health_check: cannot read git HEAD — {exc}", file=sys.stderr)
        return 2

    rep = build(args.baseline)
    text = render(rep, args.baseline, head)
    if args.out:
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        print(f"health_check: wrote {args.out}")
    else:
        print(text)
    if rep.unverified:
        print(f"health_check: {len(rep.unverified)} metric(s) UNVERIFIED — "
              f"see the snapshot; a metric that could not be measured is never "
              f"reported as zero.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
