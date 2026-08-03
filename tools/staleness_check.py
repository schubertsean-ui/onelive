#!/usr/bin/env python3
"""Fail the build the moment STATE.md falls behind the integration branch.

SUMMARY: the disk-truth guard. STATE.md is the "always-current rollup"
(OPERATING_RULES §4). It once fell ~50 merged PRs stale. This check makes that
impossible: it fails if `origin/master` has advanced AT ALL since STATE.md was
last updated there.

WHY NOT "N commits behind" (the v1 mistake, founder-caught 2026-08-03): a
tolerance of "20 commits" is a fudge factor — it is arbitrary, and it still
LICENSES staleness up to the bound. A world-class check ties to the invariant
("STATE reflects reality"), not to a number, and tolerates ZERO un-reconciled
drift. The commit-count-behind-HEAD framing was the smell.

THE MEASURE (no magic number, immune to the squash-merge chicken-and-egg):
`drift` = the number of commits on `origin/master` strictly after the most recent
`origin/master` commit that MODIFIED `STATE.md`. In steady state every session
ends by updating STATE.md (the close ritual), so the tip of master is itself a
STATE-touching commit and drift is 0. The instant a change merges to master
WITHOUT updating STATE.md, the tip is no longer a STATE-touching commit, drift
becomes ≥1, and this check fails until STATE.md is reconciled. That is the
forcing function: "every change-set that lands on master updates STATE.md."

Measuring against STATE.md's last MODIFICATION (not a stored SHA) is what removes
the fudge factor: the squash-merge that lands a STATE update cannot name its own
not-yet-existing SHA, but it DOES modify STATE.md, so it counts as the current
point with no lag. The `reconciled_through_commit` marker is retained as the
human-readable assertion ("STATE reflects commit X") and is sanity-checked
(present, valid, a real ancestor of `origin/master`), but drift no longer depends
on the marker's exact value.

DEFAULT tolerance is 0. A tolerance is exposed (`--max-drift` / STALENESS_MAX_DRIFT)
ONLY as an operational escape hatch for a genuine parallel-merge race; RAISING it
is a disk-truth relaxation and should be justified, not a habit. Honest limit,
stated so the gate never overclaims: it detects that master moved without a STATE
update — it does not judge whether the STATE update was substantive (a whitespace
edit resets drift). Intent stays with the reviewer + the honesty rule; this gate
only makes SILENT drift impossible.

Integration ref: `origin/master`. The check attempts a best-effort `git fetch
origin master` first; `tools/validate` also refreshes it before running gates, so
CI and local runs compare against the true tip. Fail-closed (exit 2) if the ref
cannot be resolved, or the marker is missing/malformed/absent/off-history.

Exit codes (house convention — see tools/README.md):
  0  STATE.md is current (master tip is a STATE-touching commit, within tolerance)
  1  STALE — master advanced past the last STATE.md update; reconcile STATE.md
  2  INDETERMINATE — cannot resolve origin/master, or bad/absent marker (fail closed)

Usage:
    python tools/staleness_check.py [--max-drift 0] [--ref origin/master] [--state PATH]
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
DEFAULT_REF = "origin/master"

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
    """Return reconciled_through_commit from STATE.md, or raise ValueError."""
    if not state_path.exists():
        raise ValueError(f"{state_path} does not exist")
    m = _BLOCK_RE.search(state_path.read_text(encoding="utf-8"))
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
            "GROUND_TRUTH block has no 'reconciled_through_commit' field — add it "
            "(the master commit STATE.md's prose reflects)"
        )
    if not isinstance(marker, str) or not _SHA_RE.match(marker):
        raise ValueError(
            f"'reconciled_through_commit' is not a 40-hex commit sha: {marker!r}"
        )
    return marker


def _resolve_ref(ref: str) -> str | None:
    # Best-effort refresh (CI and validate also fetch); ignore failure, then
    # require the ref to resolve locally.
    if "/" in ref:
        remote, branch = ref.split("/", 1)
        _git("fetch", "--quiet", remote, branch)
    r = _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return r.stdout.strip() or None


def check(state_path: pathlib.Path, ref: str, max_drift: int) -> int:
    try:
        marker = _read_marker(state_path)
    except ValueError as e:
        print(f"[staleness_check] INDETERMINATE — {e}", file=sys.stderr)
        return 2

    tip = _resolve_ref(ref)
    if not tip:
        print(f"[staleness_check] INDETERMINATE — cannot resolve {ref} "
              "(no such ref in this clone; CI/validate fetch it — run "
              "`git fetch origin master`).", file=sys.stderr)
        return 2

    # The marker must be a REAL commit on the integration branch's history.
    if _git("cat-file", "-e", f"{marker}^{{commit}}").returncode != 0:
        print(f"[staleness_check] INDETERMINATE — reconciled_through_commit "
              f"{marker[:12]} is not in this clone (shallow?). "
              "`git fetch --unshallow`.", file=sys.stderr)
        return 2
    if _git("merge-base", "--is-ancestor", marker, tip).returncode != 0:
        print(
            f"[staleness_check] STALE — reconciled_through_commit {marker[:12]} "
            f"is not an ancestor of {ref} ({tip[:12]}); STATE.md names a commit "
            "off master's history. Reconcile STATE.md and set the marker to a "
            "current master commit.", file=sys.stderr)
        return 1

    # The real measure: has master advanced since STATE.md was last updated there?
    last_touch = _git("rev-list", "-1", tip, "--", "STATE.md").stdout.strip()
    if not last_touch:
        print(f"[staleness_check] INDETERMINATE — no commit on {ref} has ever "
              "modified STATE.md.", file=sys.stderr)
        return 2
    drift = _git("rev-list", "--count", f"{last_touch}..{tip}")
    if drift.returncode != 0:
        print(f"[staleness_check] INDETERMINATE — cannot count drift: "
              f"{drift.stderr.strip()}", file=sys.stderr)
        return 2
    n = int(drift.stdout.strip() or "0")

    if n > max_drift:
        print(
            f"[staleness_check] STALE — {ref} has advanced {n} commit(s) since "
            f"STATE.md was last updated there (last STATE.md change: "
            f"{last_touch[:12]}; tip: {tip[:12]}; tolerance: {max_drift}). "
            "Reconcile STATE.md — update the 'Where we are' rollup and set "
            "reconciled_through_commit to the current tip — before merging. "
            "Disk is truth (OPERATING_RULES §4).", file=sys.stderr)
        return 1

    print(f"[staleness_check] OK — {ref} tip {tip[:12]} is within {max_drift} of "
          f"the last STATE.md update ({last_touch[:12]}); drift={n}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Fail when STATE.md has fallen behind the integration branch "
                    "(zero-tolerance; measured as commits since STATE.md last changed).")
    p.add_argument("--max-drift", type=int,
                   default=int(os.environ.get("STALENESS_MAX_DRIFT", "0")),
                   help="commits master may advance past the last STATE.md update "
                        "before failing (default 0; raising it is a disk-truth "
                        "relaxation).")
    p.add_argument("--ref", default=DEFAULT_REF,
                   help="integration ref to measure against (default origin/master).")
    p.add_argument("--state", type=pathlib.Path, default=DEFAULT_STATE,
                   help="path to STATE.md (default: repo-root STATE.md).")
    args = p.parse_args(argv)
    if args.max_drift < 0:
        print("[staleness_check] --max-drift must be >= 0", file=sys.stderr)
        return 2
    return check(args.state, args.ref, args.max_drift)


if __name__ == "__main__":
    raise SystemExit(main())
