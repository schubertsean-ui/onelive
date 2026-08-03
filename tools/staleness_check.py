#!/usr/bin/env python3
"""Fail LOUD when STATE.md has fallen behind the merged git history.

SUMMARY: the disk-truth guard. STATE.md is the "always-current rollup" (charter
Prime Directive 2 / OPERATING_RULES §4). It went ~50 merged PRs stale over two
weeks because (a) a since-obsolete belief held STATE.md un-editable (R-023/R-065,
corrected 2026-08-03 — STATE.md is NOT in the armed-cron runtime set, so editing
it never reds trust-gate) and (b) nothing mechanically noticed the drift: the
existing session_reconcile goes UNVERIFIED without `gh`/DB, so a growing gap
between STATE.md and reality made no noise.

This check needs neither `gh` nor a DB. It reads a machine-maintained marker in
STATE.md's GROUND_TRUTH block — `reconciled_through_commit`, the newest commit
STATE.md's prose reflects — and compares it to `HEAD` using git alone:

  * the marker must be a 40-hex sha that EXISTS in this clone and is an ANCESTOR
    of HEAD (STATE cannot claim to reflect a commit that isn't in the history
    leading to HEAD);
  * the number of commits merged since the marker (`git rev-list --count
    <marker>..HEAD`) must not exceed STALENESS_MAX_COMMITS.

Past the threshold the check FAILS (exit 1) and tells you to reconcile STATE.md
and advance the marker — the forcing function that makes silent staleness
impossible to merge past. It is a TIGHTENING (a new gate that can only reject a
stale tree), not a threshold relaxation.

Fail-closed, mirroring tests/test_arming_smoke_binding.py's proven pattern: a
missing/malformed marker, or a marker commit absent from the clone (e.g. a
shallow checkout), exits 2 (INDETERMINATE = hard fail), never a silent pass. CI
checks out full history (fetch-depth 0), so the marker resolves there.

Threshold: default 20 (env override STALENESS_MAX_COMMITS). Generous enough for a
normal sprint's worth of feature PRs between reconciles, small enough to catch
the multi-week drift this guard exists to prevent. Raising it far past a sprint
is a disk-truth relaxation — a founder call.

Exit codes (house convention — see tools/README.md):
  0  STATE.md is current (marker present, ancestor of HEAD, within threshold)
  1  STATE.md is STALE (too many commits since the marker) — reconcile it
  2  INDETERMINATE (no/%malformed marker, or marker not in this clone) — fail closed

Usage:
    python tools/staleness_check.py [--max-commits N] [--state PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_STATE = ROOT / "STATE.md"
DEFAULT_MAX_COMMITS = 20

_BLOCK_RE = re.compile(
    r"<!--\s*GROUND_TRUTH:BEGIN\s*-->\s*```json\s*(?P<json>\{.*?\})\s*```",
    re.DOTALL,
)
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True, text=True, check=False,
    )


def _read_marker(state_path: pathlib.Path) -> str:
    """Return the reconciled_through_commit sha from STATE.md's GROUND_TRUTH
    block, or raise ValueError with a specific reason (fail closed)."""
    if not state_path.exists():
        raise ValueError(f"{state_path} does not exist")
    text = state_path.read_text(encoding="utf-8")
    m = _BLOCK_RE.search(text)
    if not m:
        raise ValueError(
            "no GROUND_TRUTH JSON block found in STATE.md "
            "(expected a <!-- GROUND_TRUTH:BEGIN --> ```json … ``` fence)"
        )
    try:
        block = json.loads(m.group("json"))
    except json.JSONDecodeError as e:
        raise ValueError(f"GROUND_TRUTH block is not valid JSON: {e}") from e
    marker = block.get("reconciled_through_commit")
    if not marker:
        raise ValueError(
            "GROUND_TRUTH block has no 'reconciled_through_commit' field — add "
            "it (the newest commit STATE.md's prose reflects) so staleness can "
            "be measured from git alone"
        )
    if not isinstance(marker, str) or not _SHA_RE.match(marker):
        raise ValueError(
            f"'reconciled_through_commit' is not a 40-hex commit sha: {marker!r}"
        )
    return marker


def check(state_path: pathlib.Path, max_commits: int) -> int:
    try:
        marker = _read_marker(state_path)
    except ValueError as e:
        print(f"[staleness_check] INDETERMINATE — {e}", file=sys.stderr)
        return 2

    # HEAD must resolve.
    head = _git("rev-parse", "HEAD")
    if head.returncode != 0:
        print(f"[staleness_check] INDETERMINATE — cannot resolve HEAD: "
              f"{head.stderr.strip()}", file=sys.stderr)
        return 2
    head_sha = head.stdout.strip()

    # The marker commit must exist in THIS clone (fail closed on a shallow clone
    # that lacks it — never a silent pass, per the arming-binding precedent).
    exists = _git("cat-file", "-e", f"{marker}^{{commit}}")
    if exists.returncode != 0:
        print(
            f"[staleness_check] INDETERMINATE — reconciled_through_commit "
            f"{marker[:12]} is not in this clone. Unshallow "
            "(`git fetch --unshallow`) so staleness can be verified; CI checks "
            "out full history.",
            file=sys.stderr,
        )
        return 2

    # The marker must be an ancestor of HEAD (STATE cannot reflect a commit off
    # the current history).
    anc = _git("merge-base", "--is-ancestor", marker, "HEAD")
    if anc.returncode != 0:
        print(
            f"[staleness_check] STALE — reconciled_through_commit {marker[:12]} "
            f"is not an ancestor of HEAD ({head_sha[:12]}). STATE.md points at a "
            "commit off the current branch's history; reconcile STATE.md against "
            "the real HEAD and set the marker to a current commit.",
            file=sys.stderr,
        )
        return 1

    behind = _git("rev-list", "--count", f"{marker}..HEAD")
    if behind.returncode != 0:
        print(f"[staleness_check] INDETERMINATE — cannot count commits since "
              f"the marker: {behind.stderr.strip()}", file=sys.stderr)
        return 2
    n_behind = int(behind.stdout.strip() or "0")

    if n_behind > max_commits:
        print(
            f"[staleness_check] STALE — {n_behind} commits have merged since "
            f"STATE.md was last reconciled (marker {marker[:12]}, threshold "
            f"{max_commits}). Reconcile STATE.md against the current HEAD "
            f"({head_sha[:12]}) — update the 'Where we are' rollup and set "
            "reconciled_through_commit to a current commit. "
            "Disk is truth; a stale STATE.md is a charter violation "
            "(OPERATING_RULES §4).",
            file=sys.stderr,
        )
        return 1

    print(
        f"[staleness_check] OK — STATE.md reflects {marker[:12]}; "
        f"{n_behind}/{max_commits} commits since last reconcile."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail when STATE.md has fallen behind merged git history "
                    "(git-only; needs no gh/DB).",
    )
    parser.add_argument(
        "--max-commits", type=int,
        default=int(os.environ.get("STALENESS_MAX_COMMITS", DEFAULT_MAX_COMMITS)),
        help=f"max commits STATE.md may lag HEAD (default "
             f"{DEFAULT_MAX_COMMITS}, env STALENESS_MAX_COMMITS).",
    )
    parser.add_argument(
        "--state", type=pathlib.Path, default=DEFAULT_STATE,
        help="path to STATE.md (default: repo-root STATE.md).",
    )
    args = parser.parse_args(argv)
    if args.max_commits < 1:
        print("[staleness_check] --max-commits must be >= 1", file=sys.stderr)
        return 2
    return check(args.state, args.max_commits)


if __name__ == "__main__":
    raise SystemExit(main())
