#!/usr/bin/env python3
"""Change-set discipline: refuse to review what review cannot actually review.

Founder-directed 2026-07-26, after the same failure happened TWICE: PR #68 ran
22 review rounds without converging, I diagnosed it as "too large, split it" —
and then reproduced it exactly on PR #74 (11 rounds). Diagnosing an incident
twice instead of encoding it is not a world-class practice; it is the absence
of one.

WHAT THE EVIDENCE SAYS
======================

Review effectiveness is not a matter of reviewer diligence. It has a measured
ceiling:

  * Google's own study of ~20k reviews (Sadowski et al., ICSE-SEIP 2018) reports
    a MEDIAN change of ~24 lines, with ~90% of changes touching fewer than 10
    files. Small changes are the mechanism, not a side effect.
  * The SmartBear/Cisco review study found defect-detection rates fall sharply
    beyond ~400 lines in a single sitting.
  * DORA/Accelerate finds small batch size and short-lived branches among the
    strongest predictors of delivery performance, and recommends merging to
    trunk at least daily.
  * Reinertsen (Principles of Product Development Flow) explains why: batch size
    drives cycle time and queue cost, and large batches raise variance as well
    as delay.

PR #74 measured 8,708 changed lines across 36 files — roughly twenty times the
point at which defect detection is known to collapse.

THE MECHANISM THAT ACTUALLY BIT US
==================================

Size alone was not the whole story. The PR GREW WHILE UNDER REVIEW:

    round ~1   20 files   2,918 lines
    round ~5   31 files   6,974 lines
    round 11   36 files   8,708 lines

Each round therefore reviewed a LARGER surface than the previous one, and
several rounds' findings were in code added during earlier rounds — including
two cases where a fix from round N created the blocker found in round N+1. A
review loop whose subject expands between iterations has no reason to converge,
and counting rounds does not help: the residual is not shrinking because the
problem is not the same problem.

So the two rules this gate enforces are SIZE and, more importantly, SCOPE
FREEZE. New urgency during review is exactly when the temptation is strongest —
"the founder needs this number now" was true every single time tonight — and it
is exactly when a new branch costs least.

STATUS: BLOCKING. Advisory limits get argued with at 2am by the person who most
wants to keep going, which is how both incidents happened. Raising a threshold
is a gate relaxation and therefore founder-crucial (CLAUDE.md).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
FREEZE = REPO / "docs" / "review" / "SCOPE_FREEZE.json"

# Derived from the research above, then relaxed for this repo's reality: a
# change here legitimately carries its tests and its Record entry, which a bare
# LOC study does not account for. These sit ABOVE the evidence-based numbers on
# purpose, and the gap is stated rather than hidden.
SOFT_LINES = 400      # the measured point where defect detection degrades
HARD_LINES = 1500     # absolute ceiling: ~4x the evidence threshold
HARD_FILES = 25

# How much a change may grow after review has begun. Not zero — adopting a
# reviewer's blocker legitimately adds lines — but bounded, because "adopting
# findings" is precisely the story that took #74 from 2,918 to 8,708.
# Flat review cost of a file removed outright. Not zero — deleting something
# is a real decision — but nowhere near its line count.
DELETED_FILE_COST = 5

MAX_GROWTH_LINES = 600
MAX_GROWTH_FILES = 6

# Paths that cost a reviewer little per line. Generated files and lockfiles are
# not read line-by-line; counting them the same as logic would make the gate
# fire on noise and get it disabled, which is worse than not having it.
LOW_REVIEW_COST = (
    "sources/capcog_venue_targets.json",
    "sources/tabc_capcog_raw.json",
    "sources/source_registry.json",
    "web/lib/capcog-boundary.json",
    "docs/export/",
    "package-lock.json",
    "pnpm-lock.yaml",
)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, check=False).stdout.strip()


def measure(base: str, head: str = "HEAD") -> dict:
    """Reviewable size of head against base."""
    files: list = []
    total = 0
    numstat = _git("diff", "--numstat", base, head)
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        if added == "-":          # binary
            continue
        if any(path.startswith(p) or path == p for p in LOW_REVIEW_COST):
            continue
        a, r = int(added), int(removed)
        # A WHOLESALE DELETION IS ONE DECISION, NOT N LINES OF READING.
        # Found by using this gate: splitting PR #74 removed ~2,500 lines and
        # the measured size went UP, so the tool punished the exact remedy it
        # exists to demand. Reviewing "should this file be gone?" is a single
        # judgement; reviewing a modification means reading both sides.
        n = DELETED_FILE_COST if a == 0 and r > 0 else a + r
        files.append({"path": path, "lines": n})
        total += n
    files.sort(key=lambda f: -f["lines"])
    return {"base": base, "head": _git("rev-parse", head),
            "reviewable_files": len(files), "reviewable_lines": total,
            "largest": files[:10]}


def load_freeze() -> dict | None:
    if not FREEZE.exists():
        return None
    try:
        return json.loads(FREEZE.read_text(encoding="utf-8"))
    except ValueError as exc:
        # A corrupt freeze record must not read as "no freeze recorded" — that
        # would silently disable the one rule that matters most.
        raise SystemExit(
            f"change_set_gate: FAIL — {FREEZE} is not valid JSON ({exc}). "
            f"A corrupt scope record is not an absent one; fix or delete it "
            f"deliberately.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--freeze", action="store_true",
                    help="record the CURRENT scope as the reviewed scope; run "
                         "this when a PR first goes out for review")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    base = _git("merge-base", args.base, "HEAD") or args.base
    m = measure(base)

    if args.freeze:
        FREEZE.parent.mkdir(parents=True, exist_ok=True)
        FREEZE.write_text(json.dumps({
            "_what": "The scope a reviewer was asked to review. Growth beyond "
                     "the documented tolerance means the review's subject "
                     "changed under it, which is why round counting stops "
                     "working. New work goes to a new branch.",
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "frozen_at_head": m["head"],
            "reviewable_files": m["reviewable_files"],
            "reviewable_lines": m["reviewable_lines"],
        }, indent=2) + "\n", encoding="utf-8")
        print(f"change_set_gate: scope frozen at {m['reviewable_files']} file(s), "
              f"{m['reviewable_lines']} reviewable line(s) -> {FREEZE}")
        return 0

    if args.json:
        print(json.dumps(m, indent=2))

    failures: list = []
    warnings: list = []

    if m["reviewable_lines"] > HARD_LINES:
        failures.append(
            f"{m['reviewable_lines']} reviewable lines exceeds the {HARD_LINES} "
            f"ceiling. Published data puts the collapse of defect detection near "
            f"{SOFT_LINES} lines, so a change this size is not being reviewed in "
            f"any meaningful sense — it is being skimmed. SPLIT IT.")
    elif m["reviewable_lines"] > SOFT_LINES:
        warnings.append(
            f"{m['reviewable_lines']} reviewable lines is past the {SOFT_LINES}-line "
            f"point where defect detection is measured to degrade. Still "
            f"reviewable, but every extra commit now costs more than it looks.")

    if m["reviewable_files"] > HARD_FILES:
        failures.append(
            f"{m['reviewable_files']} files exceeds the {HARD_FILES} ceiling "
            f"(~90% of changes at Google touch fewer than 10). SPLIT IT.")

    freeze = load_freeze()
    if freeze and freeze.get("branch") == _git("rev-parse", "--abbrev-ref", "HEAD"):
        dl = m["reviewable_lines"] - freeze.get("reviewable_lines", 0)
        df = m["reviewable_files"] - freeze.get("reviewable_files", 0)
        if dl > MAX_GROWTH_LINES or df > MAX_GROWTH_FILES:
            failures.append(
                f"SCOPE GREW UNDER REVIEW by {dl:+} line(s) and {df:+} file(s) "
                f"(tolerance {MAX_GROWTH_LINES}/{MAX_GROWTH_FILES}).\n"
                f"    This is the failure that produced 22 rounds on PR #68 and "
                f"11 on PR #74: each round reviews a bigger subject than the "
                f"last, so findings never converge and fixes from one round "
                f"create blockers in the next.\n"
                f"    Adopting a reviewer's blocker is fine. NEW WORK IS NOT, "
                f"however urgent it feels — and it always feels urgent. Open a "
                f"new branch: it costs one PR and saves a review spiral.")

    print(f"change_set_gate: {m['reviewable_files']} reviewable file(s), "
          f"{m['reviewable_lines']} reviewable line(s)")
    if freeze:
        print(f"  frozen scope: {freeze.get('reviewable_files')} file(s), "
              f"{freeze.get('reviewable_lines')} line(s) at "
              f"{str(freeze.get('frozen_at_head'))[:8]}")
    else:
        print("  no scope freeze recorded — run --freeze when this goes out "
              "for review")
    for w in warnings:
        print(f"  WARN  {w}")
    if m["largest"]:
        print("  largest files:")
        for f in m["largest"][:5]:
            print(f"    {f['lines']:>6}  {f['path']}")

    if failures:
        print("\nchange_set_gate: FAIL", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print("\n  Raising these limits is a gate-threshold relaxation and is "
              "founder-crucial (CLAUDE.md). Splitting is the intended fix.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
