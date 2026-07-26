#!/usr/bin/env python3
"""M9 reviewer scorecard — measures the adversarial reviewer itself (v2).

Greppable summary: founder-directed 2026-07-25 ("We also need to put a
metric measure on the reviewer to ensure it is also getting better").
Derives, MECHANICALLY from the Kaizen ledger (never hand-copied —
retyped-evidence class), per reviewed-PR arc: rounds-to-green (M1),
ROUND-1 RECALL (share of the arc's distinct classes first surfaced in
round 1 — rising is the reviewer improving), SIBLING-MISS count (a class
token recurring in a later round of the same arc: someone — builder or
reviewer — missed the enumeration; falling toward zero), and NOVELTY
DECAY (new-class share per round; churn shows as low novelty with
continuing rounds). Escapes stay kaizen_trends' hard-gate concern (zero
absolute) — not duplicated here. ADVISORY in validate: a scorecard is
instrumentation, not a gate; its findings feed the weekly digest and the
lens-pruning decision, and any threshold it might one day enforce is a
gate change (evaluator-mandatory, founder-crucial if relaxing).
Fail-loud parsing: a malformed ledger row raises (second consumer
enforcing the no-raw-pipes rule).
"""
from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(REPO_ROOT, "docs", "metrics", "KAIZEN_LEDGER.md")

_ROUND_ROW = re.compile(r"^\|\s*[\d-]+\s*\|\s*#(\d+)\s*\(in flight: r(\d+)[^)]*\)\s*\|")
_MERGED_ROW = re.compile(r"^\|\s*[\d-]+\s*\|\s*#(\d+)\s*\(MERGED[^)]*\)\s*\|\s*(\d+)\s*\|")
# Ledger schema: | Date | PR | M1 | M2 | M4 | M5 | Notes | → 9 split parts.
_LEDGER_PARTS = 9

# Class tokens are recorded as `token ×n` — the count is MANDATORY by the
# ledger convention (kaizen_trends relies on it too), so an uncounted
# `CLASS:` mention is deliberately NOT a scorecard input (#71 r3 nit:
# contract stated here, next to the pattern that depends on it).
# SCOPE, stated (#71 r4 nit): M9 counts only HYPHENATED kebab tokens —
# the convention adopted 2026-07-18. Legacy single-word tokens (e.g.
# `contradictions`) predate it and are deliberately EXCLUDED, because
# single words cannot be distinguished from ordinary prose without false
# positives. Consequence, stated rather than hidden: M9 undercounts
# pre-convention arcs; kaizen_trends carries the same caveat in its own
# note, and its class counts remain the authority for that era.
_CLASS_TOKEN = re.compile(r"\b([a-z][a-z0-9]*(?:-[a-z0-9]+)+)\s*×\s*\d+")


def parse_arcs(text: str) -> tuple[dict[int, dict[int, set[str]]], dict[int, int]]:
    """ledger text -> ({pr: {round: class-token set}}, {pr: merged M1}).
    FAIL-LOUD: a round row whose cell count differs from the ledger schema
    raises — extra raw pipes shift which cell is read as M2, so a lenient
    parse would silently score the wrong data (#71 r3)."""
    arcs: dict[int, dict[int, set[str]]] = {}
    merged: dict[int, int] = {}
    for line in text.splitlines():
        line = line.strip()
        m = _ROUND_ROW.match(line)
        if m:
            pr, rnd = int(m.group(1)), int(m.group(2))
            # EXACT cell count (#71 r3 blocker): a floor check accepted
            # rows with extra raw pipes, silently shifting which cell is
            # read as M2 (or dropping tokens). The ledger schema is 7
            # content cells → 9 parts with the leading/trailing empties.
            cells = [c.strip() for c in line.split("|")]
            if len(cells) != _LEDGER_PARTS:
                raise ValueError(
                    f"malformed ledger round row ({len(cells)} parts, need "
                    f"{_LEDGER_PARTS} — escape raw pipes): {line[:120]}")
            tokens = set(_CLASS_TOKEN.findall(cells[4]))
            arcs.setdefault(pr, {}).setdefault(rnd, set()).update(tokens)
            continue
        m = _MERGED_ROW.match(line)
        if m:
            merged[int(m.group(1))] = int(m.group(2))
    return arcs, merged


def scorecard(arcs: dict[int, dict[int, set[str]]], merged: dict[int, int]) -> dict:
    """Per-PR M9 metrics. Empty/degenerate arcs are explicit results,
    never division errors (nonfinite/zero guards stated)."""
    out: dict[int, dict] = {}
    for pr, rounds in sorted(arcs.items()):
        all_tokens: set[str] = set()
        seen_before: set[str] = set()
        sibling_misses = 0
        novelty: list[tuple[int, int, int]] = []  # (round, new, total)
        for rnd in sorted(rounds):
            tokens = rounds[rnd]
            new = tokens - seen_before
            sibling_misses += len(tokens & seen_before)
            novelty.append((rnd, len(new), len(tokens)))
            seen_before |= tokens
            all_tokens |= tokens
        # ROUND 1 means round 1 (#71 r3 blocker): using "earliest recorded
        # round" would score an arc whose r1 went unrecorded as if its
        # first surviving round were the exhaustive first pass. An arc
        # with no r1 row reports None — an explicit unmeasurable, never a
        # flattering substitute.
        round_one = rounds.get(1)
        recall = (
            (len(round_one & all_tokens) / len(all_tokens))
            if (round_one is not None and all_tokens)
            else None
        )
        # LABEL HONESTY (#71 r8 nit): this counts every recorded round,
        # INCLUDING seed rows (r0) that carry no classed findings — so
        # the printed field says "rounds-recorded", not
        # "rounds-with-classes", which it never was.
        out[pr] = {
            "rounds_recorded": len(rounds),
            "m1_merged": merged.get(pr),
            "distinct_classes": len(all_tokens),
            "round1_recall": recall,
            "sibling_misses": sibling_misses,
            "novelty": novelty,
        }
    return out


def main() -> int:
    try:
        with open(LEDGER, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"reviewer_scorecard: FAIL — ledger unreadable ({exc})", file=sys.stderr)
        return 1
    try:
        arcs, merged = parse_arcs(text)
    except ValueError as exc:
        print(f"reviewer_scorecard: FAIL — {exc}", file=sys.stderr)
        return 1
    if not arcs:
        print("reviewer_scorecard: no per-round arcs recorded yet — explicit "
              "empty result, not silence")
        return 0
    print("reviewer_scorecard (M9) — per reviewed-PR arc:")
    for pr, row in scorecard(arcs, merged).items():
        recall = ("n/a (no r1 row or no classed findings)"
                  if row["round1_recall"] is None
                  else f"{row['round1_recall']:.0%}")
        m1 = row["m1_merged"] if row["m1_merged"] is not None else "in flight"
        print(f"  #{pr}: M1={m1} · rounds-recorded={row['rounds_recorded']} · "
              f"distinct-classes={row['distinct_classes']} · round1-recall={recall} · "
              f"sibling-misses={row['sibling_misses']}")
        for rnd, new, total in row["novelty"]:
            print(f"      r{rnd}: {new} new / {total} classed findings")
    print("reviewer_scorecard: directions — round1-recall RISING, sibling-misses "
          "FALLING to 0; low novelty with continuing rounds = churn signal. "
          "Escapes remain kaizen_trends' hard gate (zero absolute).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
