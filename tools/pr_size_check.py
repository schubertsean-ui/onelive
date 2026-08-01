#!/usr/bin/env python3
"""Warn EARLY when a branch's diff is outgrowing what the evaluator can review.

Founder directive (2026-07-25): after PR #59 reached 1.26 MB against the
adversarial reviewer's 800 KB cap, the independent review REFUSED to run — a
whole session's work had accumulated into one PR and the mandatory review could
not happen at all. Splitting it after the fact is high-risk churn; the fix is to
see it coming.

WHAT THIS DOES. Measures the branch diff against the integration branch, EXACTLY
as .github/workflows/adversarial-review.yml builds it (same exclusions), and
compares it to the cap that workflow passes to tools/adversarial_review.py. It
reports a percentage and, past a warning threshold, tells you to split BEFORE the
cap is hit — while splitting is still cheap (a few commits, not 45).

The cap is READ from the workflow file, never hardcoded, so it cannot drift.

Exit codes:
  0  under the warning threshold (or the cap/range cannot be determined)
  1  at/over the CAP — the evaluator will refuse to review this PR
  0  over the WARNING threshold but under the cap (prints loudly; advisory by
     design, so it never blocks a legitimate large-but-reviewable change)

Usage:
    python tools/pr_size_check.py [--base origin/master] [--warn-pct 70]
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_WORKFLOW = _ROOT / ".github" / "workflows" / "adversarial-review.yml"

# Kept in sync with the workflow's diff construction by reading it below; this is
# the fallback when the workflow cannot be parsed.
_FALLBACK_EXCLUDES = ["**/package-lock.json"]


def evaluator_cap_bytes() -> int | None:
    """The --max-diff-bytes the adversarial-review workflow actually passes."""
    try:
        text = _WORKFLOW.read_text(encoding="utf-8")
    except OSError:
        return None
    m = re.search(r"--max-diff-bytes\s+(\d+)", text)
    return int(m.group(1)) if m else None


def workflow_excludes() -> list:
    """The ':(exclude)…' pathspecs the workflow removes from the review diff."""
    try:
        text = _WORKFLOW.read_text(encoding="utf-8")
    except OSError:
        return list(_FALLBACK_EXCLUDES)
    found = re.findall(r"':\(exclude\)([^']+)'", text)
    return found or list(_FALLBACK_EXCLUDES)


def diff_bytes(base: str) -> int | None:
    args = ["git", "diff", f"{base}...HEAD", "--", "."]
    args += [f":(exclude){p}" for p in workflow_excludes()]
    try:
        proc = subprocess.run(args, cwd=str(_ROOT), capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return len(proc.stdout)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="origin/master",
                    help="integration branch to diff against (default origin/master)")
    ap.add_argument("--warn-pct", type=float, default=70.0,
                    help="warn once the diff reaches this %% of the cap (default 70)")
    args = ap.parse_args(argv)

    cap = evaluator_cap_bytes()
    size = diff_bytes(args.base)
    if cap is None or size is None:
        # Never fail the session on an undeterminable measurement — say so plainly.
        print("pr_size_check: SKIPPED — could not determine the evaluator cap or "
              f"diff vs {args.base} (missing ref in a shallow clone?).")
        return 0

    pct = 100.0 * size / cap
    kb, capkb = size / 1024, cap / 1024
    if size >= cap:
        print(f"pr_size_check: OVER CAP — branch diff is {kb:.0f} KB vs the "
              f"evaluator's {capkb:.0f} KB cap ({pct:.0f}%).", file=sys.stderr)
        print("  The independent review will REFUSE to run (it will not review a "
              "truncated diff), so the mandatory evaluator pass cannot happen.",
              file=sys.stderr)
        print("  Split this branch into reviewable PRs. Splitting AFTER the fact "
              "is high-risk churn — that is why this check exists.", file=sys.stderr)
        return 1
    if pct >= args.warn_pct:
        print(f"pr_size_check: WARNING — branch diff is {kb:.0f} KB, {pct:.0f}% of "
              f"the evaluator's {capkb:.0f} KB cap.")
        print("  Land what is finished as its own PR NOW, while splitting is still "
              "cheap. Past 100% the evaluator refuses to review at all.")
        return 0
    print(f"pr_size_check: OK — branch diff {kb:.0f} KB, {pct:.0f}% of the "
          f"{capkb:.0f} KB evaluator cap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
