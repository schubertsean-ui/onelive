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
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ALARM_THRESHOLD = 3

# Any kebab token immediately before ×N — including short trust-critical
# tokens like `sql`/`rls`/`xss` (evaluator r4: a length floor would let short
# class names silently escape the repeat-class alarm).
_CLASS_RE = re.compile(r"([A-Za-z0-9][A-Za-z0-9-]+)\s*×\s*(\d+)")
_M4_TOKEN_RE = re.compile(r"[A-Za-z0-9-]+")
_ROW_RE = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2})")


def parse_pr_rows(ledger_text: str) -> list[dict]:
    """Extract the PR-rows table: date, pr, m1, m2, m4, m5, notes per row."""
    rows: list[dict] = []
    in_pr_rows = False
    for line in ledger_text.splitlines():
        if line.startswith("## "):
            in_pr_rows = line.strip() == "## PR rows"
            continue
        if not in_pr_rows or not _ROW_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
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


def family_addressed(family: set[str], rows: list[dict]) -> bool:
    """A family is addressed when any M4 column contains one of its tokens
    as an EXACT token (hyphen-delimited word), never as a substring —
    "not-empty-env-fixed" must not credit `empty-env` (evaluator r4: same
    loose-binding fail-open pattern r3 caught in skip_record_binding)."""
    for row in rows:
        m4_tokens = set(_M4_TOKEN_RE.findall(row["m4"]))
        if family & m4_tokens:
            return True
    return False


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
    return ledger_text.count("M3-ESCAPE")


def build_report(ledger_text: str) -> tuple[str, list[str]]:
    """Return (report_text, findings). Findings non-empty = curves violated."""
    rows = parse_pr_rows(ledger_text)
    if not rows:
        raise ValueError("no PR rows parsed from the ledger")

    findings: list[str] = []

    n_escapes = escapes(ledger_text)
    if n_escapes:
        findings.append(f"M3 ESCAPES RECORDED: {n_escapes} — the absolute goal is 0")

    counts = class_counts(rows)
    families = family_groups(list(counts))
    alarms: list[tuple[str, int]] = []
    for family in families:
        total = sum(counts[t] for t in family)
        if total >= ALARM_THRESHOLD and not family_addressed(family, rows):
            name = min(family, key=len)
            alarms.append((name, total))
            findings.append(
                f"REPEAT-CLASS ALARM: family '{name}' caught {total}x with no "
                f"structural fix marker in any M4 column — the CLASS fix is due "
                f"(threshold {ALARM_THRESHOLD}); ship the fix and name the class "
                f"token in that row's M4 column"
            )

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
        f"m3_escapes: {n_escapes} (goal: 0, absolute)",
        f"m1_rounds_to_green: {series} -> {direction}",
        f"founder_red_catches: {founder_catches} (must trend to 0 — each one means every automated layer missed it)",
        f"m4_gate_gap_rows: {m4_rows} (compounding fixes; steady > 0 is healthy)",
        "catches_per_gate (judgment->mechanical drain — watch judgment gates shrink per class):",
    ]
    for gate, n in sorted(gates.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {gate}: {n}")
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    lines.append("top_class_tokens: " + ", ".join(f"{t}×{n}" for t, n in top))
    if alarms:
        lines.append(
            "repeat_class_alarms: "
            + ", ".join(f"{name} ({total}x, UNADDRESSED)" for name, total in alarms)
        )
    else:
        lines.append("repeat_class_alarms: none — every family at/over threshold has a structural fix marker")
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
