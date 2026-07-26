#!/usr/bin/env python3
"""kaizen_trends — compute the Kaizen trend report from the ledger, mechanically.

SUMMARY: the measurement layer the Kaizen model requires (founder direction
2026-07-18: everything trends toward zero/perfect, and the trend itself must
be computed, not asserted). Parses docs/metrics/KAIZEN_LEDGER.md and emits a
machine-stamped trend report:

  - M3 escapes            — must be 0, always (hard finding if not).
  - Repeat classes        — class families caught >= ALARM_THRESHOLD times
                            with no structural fix marker in any M4 column
                            (finding: the class fix is DUE — the rule the
                            evaluator enforced by judgment on PR #35 r2,
                            now mechanical).
  - M1 rounds-to-green    — direction (falling = improving).
  - Founder(Red) catches  — count; must trend to 0 (a founder catch means
                            every automated layer missed it).
  - Catches per gate      — the judgment->mechanical drain, visible.
  - M4 gate-gap fixes     — cumulative (compounding improvement).

Conventions this tool relies on (documented in docs/KAIZEN.md):
  - M2 classes are kebab-case tokens immediately before an "×N" count.
    REUSE THE EXACT TOKEN for a repeat — matching is exact-token plus
    containment families (e.g. `empty-env` groups with `fail-open-empty-env`).
  - A class family counts as ADDRESSED when any row's M4 (gate-gaps) column
    contains one of its tokens.
  - An M3 escape row must carry the literal token `M3-ESCAPE`.

Exit codes: 0 = all curves clean; 1 = findings (escape recorded, or an
unaddressed repeat family at/over threshold); 2 = ledger missing/unparseable
(fail loud, never fail open).

Usage: python tools/kaizen_trends.py [--ledger docs/metrics/KAIZEN_LEDGER.md]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

ALARM_THRESHOLD = 3
# Single-segment class tokens that are REAL classes (declared registry —
# docs/KAIZEN.md): trust-critical shorts the r4 fix must keep counting.
# Any OTHER single English word before ×N is prose over-capture (r18: the
# merged PR #18 rows counted "provenance job ×5" as class `job`) and never
# alarms on its own — multi-segment kebab tokens always count.
SHORT_TOKEN_REGISTRY = {"sql", "rls", "xss", "auth", "csrf", "ssrf", "race", "leak"}

# Any kebab token immediately before ×N — including short trust-critical
# tokens like `sql`/`rls`/`xss` (evaluator r4: a length floor would let short
# class names silently escape the repeat-class alarm).
_CLASS_RE = re.compile(r"([A-Za-z0-9][A-Za-z0-9-]+)\s*×\s*(\d+)")
_M4_TOKEN_RE = re.compile(r"[A-Za-z0-9-]+")
_ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})")


_CODE_SPAN = re.compile(r"`[^`]*`")
_PIPE_MASK = "\x00PIPE\x00"


def parse_pr_rows(ledger_text: str) -> list[dict]:
    """Extract the PR-rows table: date, pr, m1, m2, m4, m5, notes per row.

    Markdown pipes inside `code spans` are cell CONTENT, not separators
    (evaluator r16: rows quoting shell like `|| exit` silently shifted
    columns under a naive split, corrupting class tokens and M4 markers).
    A row that still does not split into exactly 7 cells is MALFORMED and
    raises — the meter must never compute trends from misread columns.
    """
    rows: list[dict] = []
    in_pr_rows = False
    for line in ledger_text.splitlines():
        if line.startswith("## "):
            in_pr_rows = line.strip() == "## PR rows"
            continue
        if not in_pr_rows or not _ROW_RE.match(line):
            continue
        masked = _CODE_SPAN.sub(lambda m: m.group(0).replace("|", _PIPE_MASK), line)
        cells = [
            c.strip().replace(_PIPE_MASK, "|")
            for c in masked.strip().strip("|").split("|")
        ]
        if len(cells) != 7:
            raise ValueError(
                f"malformed ledger row ({len(cells)} cells after code-span "
                f"masking, need 7) — escape raw pipes or backtick shell "
                f"snippets: {line[:100]}"
            )
        rows.append(
            {
                "date": cells[0],
                "pr": cells[1],
                "m1": cells[2],
                "m2": cells[3],
                "m4": cells[4],
                "m5": cells[5],
                "notes": cells[6],
            }
        )
    return rows


def class_counts(rows: list[dict]) -> dict[str, int]:
    """Total ×N count per exact class token across all M2 columns."""
    counts: dict[str, int] = {}
    for row in rows:
        for token, n in _CLASS_RE.findall(row["m2"]):
            counts[token] = counts.get(token, 0) + int(n)
    return counts


def _related(a: str, b: str) -> bool:
    """Containment familying, hyphen-aware: `empty-env` ⊂ `fail-open-empty-env`
    → same family. Single-segment tokens (e.g. `gap`, `sql`) are too generic
    to claim family over compounds — they match exactly only, so a bare `gap`
    never absorbs `coverage-gap` while `sql` still counts its own repeats."""
    if a == b:
        return True
    if "-" not in a or "-" not in b:
        return False
    return a in b or b in a


def family_groups(tokens: list[str]) -> list[set[str]]:
    """Group tokens into containment families (see _related)."""
    groups: list[set[str]] = []
    for tok in tokens:
        merged: set[str] | None = None
        for group in groups:
            if any(_related(tok, other) for other in group):
                if merged is None:
                    group.add(tok)
                    merged = group
                else:
                    merged |= group
                    group.clear()
        groups = [g for g in groups if g]
        if merged is None:
            groups.append({tok})
    return groups


def family_marker_last_row(family: set[str], rows: list[dict]) -> int | None:
    """Index of the LAST row whose M4 column names a family token exactly
    (hyphen-delimited word, never substring — evaluator r4). None = no
    structural fix marker exists."""
    last: int | None = None
    for i, row in enumerate(rows):
        m4_tokens = set(_M4_TOKEN_RE.findall(row["m4"]))
        if family & m4_tokens:
            last = i
    return last


def family_row_counts(family: set[str], rows: list[dict]) -> list[tuple[int, int]]:
    """(row_index, catch_count) for every row catching a family token."""
    out: list[tuple[int, int]] = []
    for i, row in enumerate(rows):
        n = sum(
            int(cnt)
            for tok, cnt in _CLASS_RE.findall(row["m2"])
            if tok in family
        )
        if n:
            out.append((i, n))
    return out


def family_alarm(family: set[str], rows: list[dict], threshold: int) -> str | None:
    """Epoch-aware repeat-class alarm (evaluator r6: a fix marker is credit
    for catches AT-OR-BEFORE its row only, never a permanent waiver).

    - No marker: alarm when total catches >= threshold (fix is due).
    - Marker exists: any catch in a row AFTER the last marker row alarms
      IMMEDIATELY — a recurrence after a claimed structural fix means the
      fix escaped, the exact condition the meter must surface loudest.
    Returns the alarm description, or None.
    """
    counts = family_row_counts(family, rows)
    if not counts:
        return None
    name = min(family, key=len)
    if all("-" not in t and t not in SHORT_TOKEN_REGISTRY for t in family):
        return None  # prose over-capture, never a class (registry misses are added there)
    last_marker = family_marker_last_row(family, rows)
    if last_marker is None:
        total = sum(n for _, n in counts)
        if total >= threshold:
            return (
                f"family '{name}' caught {total}x with no structural fix "
                f"marker in any M4 column — the CLASS fix is due (threshold "
                f"{threshold}); ship the fix and name the class token in "
                f"that row's M4 column"
            )
        return None
    post = sum(n for i, n in counts if i > last_marker)
    if post:
        return (
            f"family '{name}' RECURRED {post}x AFTER its structural fix "
            f"marker (ledger row {last_marker + 1}) — the fix escaped; "
            f"root-cause it, harden the fix, and add a NEW M4 marker row"
        )
    return None


def m1_series(rows: list[dict]) -> list[int]:
    out = []
    for row in rows:
        m = re.fullmatch(r"(\d+)\+?", row["m1"])
        if m:
            out.append(int(m.group(1)))
    return out


def m1_direction(series: list[int]) -> str:
    if len(series) < 4:
        return "insufficient data"
    half = len(series) // 2
    early, late = series[:half], series[half:]
    a, b = sum(early) / len(early), sum(late) / len(late)
    if b < a:
        return f"FALLING (improving): mean {a:.1f} -> {b:.1f}"
    if b > a:
        return f"RISING (regressing): mean {a:.1f} -> {b:.1f}"
    return f"FLAT: mean {a:.1f}"


def gate_counts(rows: list[dict]) -> dict[str, int]:
    """Rough catch attribution: the label before ':' in each M2 segment."""
    counts: dict[str, int] = {}
    for row in rows:
        for segment in re.split(r"[;]", row["m2"]):
            m = re.match(r"\s*([A-Za-z_()-]+(?:\s+r\d+)?)\s*:", segment)
            if not m:
                continue
            gate = re.sub(r"\s+r\d+$", "", m.group(1)).strip()
            n = sum(int(x) for _, x in _CLASS_RE.findall(segment))
            if n:
                counts[gate] = counts.get(gate, 0) + n
    return counts


def escapes(ledger_text: str) -> int:
    """Total escapes ever recorded. NEVER decreases — history is permanent."""
    return ledger_text.count("M3-ESCAPE")


# A "Gate-gap closed" cell that names nothing.
_EMPTY_CELL = frozenset({"", "-", "—", "–", "none", "n/a", "na", "tbd", "todo",
                         "pending", "not yet", "nothing"})

# A cell must CITE SOMETHING THAT EXISTS, not merely be non-empty.
#
# The first version of this gate treated any non-placeholder text as a closed gap.
# The openai/attacker-smuggle seat blocked it on PR #80 as
# `CLASS:unvalidated-escape-closure`, and the finding is correct: writing `fixed`
# in that column turned the hard M3 alarm green while nothing mechanical had
# shipped. That is a gate whose pass condition is prose — the worst possible
# property for the one alarm guarding an absolute-zero target, because the escape
# it is meant to keep open is closed by typing.
#
# So a closure must cite a repo path that is really on disk, or a RECORD.md row
# that really exists. A machine still cannot judge whether the named test is
# ADEQUATE — that stays the reviewer's job, and this docstring does not pretend
# otherwise — but it can insist the citation refers to something real, which is
# the difference between "a reviewer can check this" and "a reviewer must take my
# word for it".
_PATH_CITATION = re.compile(
    r"`([A-Za-z0-9_./-]+\.(?:py|ts|tsx|yml|yaml|sql|sh|md))`"
    r"|(?<![\w/])((?:tests|tools|worker|api|ai|web|brain|social|ventures"
    r"|\.github)/[A-Za-z0-9_./-]+\.(?:py|ts|tsx|yml|yaml|sql|sh|md))")
_RECORD_CITATION = re.compile(r"\bR-(\d{3})\b")


def _escape_table(ledger_text: str) -> list[str]:
    """The data rows of the '## M3 escapes' table, in order."""
    start = ledger_text.find("## M3 escapes")
    if start == -1:
        return []
    rest = ledger_text[start:]
    end = re.search(r"^## ", rest[3:], re.MULTILINE)
    section = rest[:end.start() + 3] if end else rest
    rows = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "M3-ESCAPE" not in stripped:
            continue
        rows.append(stripped)
    return rows


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolves_inside(root: Path, candidate: str) -> bool:
    """Whether `candidate` names an existing file INSIDE `root`.

    `(root / candidate).exists()` was not enough, and the gap was a real bypass of
    this gate: `Path("/repo") / "/tmp/x.py"` discards `/repo` entirely and returns
    `/tmp/x.py`, so a citation naming ANY absolute path to an existing file on the
    host — `/usr/.../six.py` — closed an M3 escape. `..` traversal is the same
    hole with extra steps. Found by the gemini/dataflow-taint seat on PR #80, in
    the check written one round earlier to stop prose closing that alarm.

    Absolute paths are rejected outright rather than reinterpreted as relative: a
    citation in this ledger means "a file in this repository", and silently
    re-rooting someone's absolute path would be guessing at intent.
    """
    if pathlib.PurePosixPath(candidate).is_absolute() or candidate.startswith("/"):
        return False
    try:
        target = (root / candidate).resolve()
    except (OSError, RuntimeError, ValueError):
        return False
    if not target.is_file():
        return False
    return target == root or root in target.parents


def _cited_mechanisms(cell: str, root: Path | None = None) -> list[str]:
    """The citations in a 'Gate-gap closed' cell that RESOLVE to something real.

    Two accepted forms, both verifiable without judgement:
      * a repo-relative file path (backticked, or bare under a known source root)
        that exists on disk;
      * an `R-###` row that is actually present in docs/RECORD.md.

    Returns the resolved citations; an empty list means the cell claims a closure
    it cannot point at.
    """
    root = (root or _repo_root()).resolve()
    found: list[str] = []
    for backticked, bare in _PATH_CITATION.findall(cell):
        candidate = backticked or bare
        if candidate and _resolves_inside(root, candidate):
            found.append(candidate)
    rows = _RECORD_CITATION.findall(cell)
    if rows:
        try:
            record = (root / "docs" / "RECORD.md").read_text(encoding="utf-8")
        except OSError:
            record = ""
        found.extend(f"R-{n}" for n in rows if f"R-{n}" in record)
    return found


def open_escapes(ledger_text: str,
                 cited_mechanisms: Callable[[str], list[str]] | None = None,
                 ) -> list[str]:
    """Escapes whose 'Gate-gap closed' column names NO shipped mechanism.

    **Founder-ratified 2026-07-26 ("option a").** An escape is permanent history,
    so a gate keyed to the raw count is red forever — and a permanently red gate
    is not a strict gate, it is an ignored one, and it creates a standing
    incentive not to record escapes at all. That would destroy the measure the
    alarm exists to protect.

    So the blocking condition moves from "any escape ever recorded" to "any
    escape whose gap is still open." **The M3 target is untouched — still 0,
    absolute — and the count still prints on every run.** This is exactly the
    semantics ``family_alarm`` already applies to the repeat-class alarm (a fix
    marker is credit for catches at-or-before its row, and a recurrence after it
    alarms immediately), ratified by the independent evaluator at r6 of an
    earlier PR. The M3 counter was the one meter in this file that never got it.

    Returns the offending row texts so the report can name them, not a count.

    ``cited_mechanisms`` is injectable so the citation check is testable without
    writing files; by default it resolves against this repo's working tree.
    """
    unclosed = []
    resolve = cited_mechanisms if cited_mechanisms is not None else _cited_mechanisms
    for row in _escape_table(ledger_text):
        cells = [c.strip() for c in row.strip("|").split("|")]
        # Columns: Date | What escaped | Where found | Root cause | Gate-gap closed
        # Indexed from the FRONT, not with cells[-1]: appending a sixth column
        # would silently move a negative index onto the new column and grade the
        # wrong cell (reviewer nit, gemini seat, PR #80).
        if len(cells) < 5:
            # A malformed row cannot be shown to have a closed gap — fail closed.
            unclosed.append(row)
            continue
        cell = cells[4]
        if cell.lower() in _EMPTY_CELL:
            unclosed.append(row)
            continue
        if not resolve(cell):
            unclosed.append(row)
    return unclosed


def build_report(ledger_text: str) -> tuple[str, list[str]]:
    """Return (report_text, findings). Findings non-empty = curves violated."""
    rows = parse_pr_rows(ledger_text)
    if not rows:
        raise ValueError("no PR rows parsed from the ledger")

    findings: list[str] = []

    n_escapes = escapes(ledger_text)
    unclosed = open_escapes(ledger_text)
    if unclosed:
        # Founder-ratified 2026-07-26 (option a): an OPEN escape blocks. A closed
        # one stays counted and visible but no longer reds the gate forever.
        findings.append(
            f"M3 ESCAPE WITH AN OPEN GATE GAP: {len(unclosed)} of {n_escapes} "
            f"recorded escape(s) name no shipped mechanism in their 'Gate-gap "
            f"closed' column — the absolute goal is 0 escapes, and an escape with "
            f"no mechanism WILL happen again. Ship the gate, then name it in that "
            f"column. First offender: {unclosed[0][:140]}")

    counts = class_counts(rows)
    families = family_groups(list(counts))
    alarms: list[str] = []
    for family in families:
        alarm = family_alarm(family, rows, ALARM_THRESHOLD)
        if alarm:
            alarms.append(alarm)
            findings.append(f"REPEAT-CLASS ALARM: {alarm}")

    series = m1_series(rows)
    direction = m1_direction(series)

    gates = gate_counts(rows)
    founder_catches = sum(n for g, n in gates.items() if "founder" in g.lower())

    m4_rows = sum(1 for r in rows if r["m4"] not in ("", "—", "-"))

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip() or "unknown"
    except OSError:
        head = "unknown"

    lines = [
        "---- KAIZEN TREND REPORT (machine-generated by tools/kaizen_trends.py) ----",
        f"generated_at: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"git_head: {head}",
        f"ledger_rows: {len(rows)}",
        # BOTH numbers, always. The all-time count is permanent history and must
        # never be able to go down; the open count is what blocks. Printing only
        # one of them is how this measure would quietly lose its meaning.
        f"m3_escapes: {n_escapes} (all-time, goal: 0, absolute — never decreases)",
        f"m3_escapes_open: {len(unclosed)} (gate gap not yet closed — this is what blocks)",
        f"m1_rounds_to_green: {series} -> {direction}",
        f"founder_red_catches: {founder_catches} (must trend to 0 — each one means every automated layer missed it)",
        f"m4_gate_gap_rows: {m4_rows} (compounding fixes; steady > 0 is healthy)",
        "catches_per_gate (judgment->mechanical drain — watch judgment gates shrink per class):",
    ]
    for gate, n in sorted(gates.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {gate}: {n}")
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    lines.append("note: class counts rely on the kebab-token convention adopted 2026-07-18 — rows written before it may undercount (e.g. empty-env shows 2 here vs 4 in R-019's prose history); treat pre-convention numbers as floors, not history")
    lines.append("top_class_tokens: " + ", ".join(f"{t}×{n}" for t, n in top))
    if alarms:
        lines.append("repeat_class_alarms:")
        for alarm in alarms:
            lines.append(f"  {alarm}")
    else:
        lines.append("repeat_class_alarms: none — thresholds respected and no post-fix recurrences")
    lines.append(f"result: {'FINDINGS' if findings else 'CLEAN'}")
    lines.append("--------------------------------------------------------------------------")
    return "\n".join(lines), findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ledger", default="docs/metrics/KAIZEN_LEDGER.md")
    args = ap.parse_args(argv)

    try:
        text = Path(args.ledger).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"kaizen_trends: cannot read {args.ledger}: {exc}", file=sys.stderr)
        return 2

    try:
        report, findings = build_report(text)
    except ValueError as exc:
        print(f"kaizen_trends: {exc}", file=sys.stderr)
        return 2

    print(report)
    if findings:
        for f in findings:
            print(f"FINDING: {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
