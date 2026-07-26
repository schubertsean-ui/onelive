#!/usr/bin/env python3
"""Change-set discipline: refuse to review what review cannot actually review.

Founder-directed 2026-07-26, after the same failure happened TWICE: PR #68 ran
22 review rounds without converging, I diagnosed it as "too large, split it" —
and then reproduced it exactly on PR #74 (11 rounds and counting at the time
of writing). Diagnosing an incident
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
FREEZE_REL = "docs/review/SCOPE_FREEZE.json"
FREEZE = REPO / FREEZE_REL

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
# A binary carries no reviewable lines but is still a file to account for.
BINARY_FILE_COST = 5

MAX_GROWTH_LINES = 600
MAX_GROWTH_FILES = 6

# Paths that cost a reviewer little per line. Generated files and lockfiles are
# not read line-by-line; counting them the same as logic would make the gate
# fire on noise and get it disabled, which is worse than not having it.
LOW_REVIEW_COST = (
    "sources/capcog_venue_targets.json",
    "sources/tabc_capcog_raw.json",
    "sources/source_registry.json",
    "sources/discovered/",
    "web/lib/capcog-boundary.json",
    "docs/export/",
)

# Lockfiles are excluded WHEREVER they sit. Matching them as path prefixes
# never fired: our only lockfile is web/package-lock.json, which starts with
# neither "package-lock.json" nor equals it, so lockfiles were counted as
# reviewable while CLAUDE.md and this docstring both said they were not.
# Evaluator finding, PR #79 r1.
LOW_REVIEW_COST_BASENAMES = (
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
)


def _is_low_review_cost(path: str) -> bool:
    """Directory entries (trailing "/") match by prefix; everything else must
    match EXACTLY. `startswith` on an exact filename also matched
    `web/lib/capcog-boundary.json.bak`, quietly excluding a file nobody
    approved. Evaluator nit, PR #79 r3."""
    if path.rsplit("/", 1)[-1] in LOW_REVIEW_COST_BASENAMES:
        return True
    return any(path.startswith(p) if p.endswith("/") else path == p
               for p in LOW_REVIEW_COST)


def _git(*args: str) -> str:
    """Run git, or STOP.

    The first version passed check=False and returned "" on failure, so a
    missing base ref, an unfetched remote or a broken repo produced an empty
    diff — which measured 0 files, 0 lines, and PASSED. A size gate that reports
    "nothing to review" when it could not look is the failure-reads-as-empty
    class inside the gate written to enforce reviewability, and the session
    contract asserted the opposite. Evaluator finding, PR #79 r1: three of four
    seats found it independently.
    """
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                          text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(
            f"change_set_gate: FAIL — `git {' '.join(args)}` exited "
            f"{proc.returncode}: {proc.stderr.strip() or '(no stderr)'}. "
            f"The change set could not be measured, which is NOT the same as "
            f"a small change set. Fetch the base ref and rerun.")
    return proc.stdout.strip()


def measure(base: str, head: str = "HEAD") -> dict:
    """Reviewable size of head against base."""
    files: list = []
    total = 0
    # Which paths were actually DELETED, read from git rather than inferred.
    deleted = {}
    for line in _git("diff", "--name-status", base, head).splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].startswith("D"):
            deleted[parts[-1]] = True
    numstat = _git("diff", "--numstat", base, head)
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        if _is_low_review_cost(path):
            continue
        if added == "-":
            # BINARY. It has no line count, but it is unquestionably a file a
            # reviewer must account for, and skipping it entirely meant a PR
            # could add unlimited binaries without touching the 25-file cap —
            # the file ceiling fail-open. Priced like a deletion: one decision,
            # not N lines. Evaluator finding, PR #79 r2.
            files.append({"path": path, "lines": BINARY_FILE_COST})
            total += BINARY_FILE_COST
            continue
        a, r = int(added), int(removed)
        # A WHOLESALE DELETION IS ONE DECISION, NOT N LINES OF READING.
        # Found by using this gate: splitting PR #74 removed ~2,500 lines and
        # the measured size went UP, so the tool punished the exact remedy it
        # exists to demand. Reviewing "should this file be gone?" is a single
        # judgement; reviewing a modification means reading both sides.
        # `a == 0 and r > 0` is NOT a deletion test: cutting 500 lines out of
        # a file that survives adds no lines either, and that IS 500 lines of
        # reading. The status letter from --name-status is the fact; numstat
        # cannot distinguish the two. Evaluator nit, PR #79 r1.
        n = DELETED_FILE_COST if deleted.get(path) else a + r
        files.append({"path": path, "lines": n})
        total += n
    files.sort(key=lambda f: -f["lines"])
    return {"base": base, "head": _git("rev-parse", head),
            "reviewable_files": len(files), "reviewable_lines": total,
            "largest": files[:10]}


def load_freeze() -> dict | None:
    """The FIRST recorded scope, or None.

    APPEND-ONLY, and that is the whole security property. A single mutable
    record made the anti-growth rule self-defeating: after a change grew, the
    author could rerun --freeze (or edit the JSON) and the new, larger scope
    became the baseline. The rule "a change under review does not grow" was
    mechanically bypassable by the very party it constrains. Evaluator finding,
    PR #79 r2 (self-weakenable-freeze-baseline).

    No tool the PR can run makes a PR-editable file tamper-proof, so the fix is
    not secrecy but VISIBILITY plus a mechanical stop: the record holds every
    freeze ever taken, growth is always measured against `rounds[0]`, and
    dropping or rewriting an earlier round fails the gate — an act that is now
    a conspicuous deletion in the diff rather than a silent overwrite.
    """
    doc = _read_freeze_doc()
    if doc is None:
        return None
    rounds = doc.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        raise SystemExit(
            f"change_set_gate: FAIL — {FREEZE} has no 'rounds' list. A scope "
            f"record that cannot be read is not an absent one.")
    first = rounds[0]
    if not isinstance(first, dict):
        raise SystemExit(
            f"change_set_gate: FAIL — {FREEZE} round 0 is not an object.")
    return first


def freeze_rounds() -> list:
    doc = _read_freeze_doc()
    return list(doc.get("rounds") or []) if doc else []


def _read_freeze_doc() -> dict | None:
    if not FREEZE.exists():
        return None
    try:
        return json.loads(FREEZE.read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        # A corrupt freeze record must not read as "no freeze recorded" — that
        # would silently disable the one rule that matters most.
        raise SystemExit(
            f"change_set_gate: FAIL — {FREEZE} could not be read as JSON "
            f"({exc}). A corrupt or unreadable scope record is not an absent "
            f"one; fix or delete it deliberately.")



def _rounds_rewritten(base: str) -> str:
    """Non-empty when a commit in this range REWROTE an existing freeze round.

    Every committed version of the record must be a prefix-extension of the one
    before it: rounds may be appended, never edited or dropped. That makes the
    realistic bypass — editing the JSON so a grown scope becomes the baseline —
    a mechanical failure rather than a silent reset.

    Stated honestly, because overstating this gate's reach is the exact defect
    it was cited for twice: this does NOT make the record tamper-proof. A force
    push that rewrites the branch can rewrite this history with it. What it
    guarantees is that a reset cannot happen QUIETLY — it must either fail here
    or appear on the PR timeline as a force push, which is a visible act a
    reviewer can see, not a number that silently changed.
    """
    # SEEDED FROM BASE, not from empty. Starting at [] meant the FIRST commit
    # in the range that touched the file established the baseline — so a single
    # commit rewriting rounds[0] relative to base passed unnoticed, and my own
    # test masked it by using two commits. The prefix rule only means anything
    # if the prefix it starts from is the one the reviewer saw.
    # Evaluator finding, PR #79 r3.
    revs = subprocess.run(
        ["git", "log", "--format=%H", "--reverse", f"{base}..HEAD",
         "--", FREEZE_REL],
        cwd=REPO, capture_output=True, text=True, check=False).stdout.split()
    previous: list = _rounds_at(base)
    # ...and the WORKING TREE is the last revision in the chain. An uncommitted
    # edit is what a person actually runs the gate against.
    revs = list(revs) + [None]
    for rev in revs:
        label = "the working tree" if rev is None else rev[:8]
        if rev is None:
            rounds = freeze_rounds()
        else:
            proc = subprocess.run(["git", "show", f"{rev}:{FREEZE_REL}"],
                                  cwd=REPO, capture_output=True, text=True,
                                  check=False)
            if proc.returncode != 0:
                continue                # deleted there; the next version wins
            try:
                rounds = (json.loads(proc.stdout) or {}).get("rounds") or []
            except ValueError:
                return f"the freeze record at {label} is not valid JSON"
        if len(rounds) < len(previous):
            return (f"{label} dropped {len(previous) - len(rounds)} "
                    f"round(s) — the record is append-only")
        for i, was in enumerate(previous):
            if rounds[i] != was:
                return (f"{label} rewrote round {i} — the baseline is "
                        f"rounds[0] and it does not move")
        previous = rounds
    return ""


def _rounds_at(rev: str) -> list:
    """The freeze rounds as of `rev`, or [] when the file is not there yet.

    A branch that INTRODUCES its freeze has no base copy, and that is the
    honest empty case: its rounds[0] is the first reviewed scope by definition.
    """
    proc = subprocess.run(["git", "show", f"{rev}:{FREEZE_REL}"], cwd=REPO,
                          capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return []
    try:
        return (json.loads(proc.stdout) or {}).get("rounds") or []
    except ValueError:
        return []



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
        rounds = freeze_rounds()
        rounds.append({
            "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "frozen_at_head": m["head"],
            "reviewable_files": m["reviewable_files"],
            "reviewable_lines": m["reviewable_lines"],
        })
        FREEZE.write_text(json.dumps({
            "_what": "The scope a reviewer was asked to review. Growth beyond "
                     "the documented tolerance means the review's subject "
                     "changed under it, which is why round counting stops "
                     "working. New work goes to a new branch.",
            "_append_only": "rounds[0] is the baseline, ALWAYS. Re-freezing "
                            "appends; it never resets. Removing or rewriting "
                            "an earlier round fails the gate, so a reset is a "
                            "visible deletion in the diff, never a silent "
                            "overwrite.",
            "rounds": rounds,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"change_set_gate: scope frozen at {m['reviewable_files']} file(s), "
              f"{m['reviewable_lines']} reviewable line(s) -> {FREEZE}")
        return 0

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
    # NOT gated on the branch name. `git rev-parse --abbrev-ref HEAD` returns
    # the literal "HEAD" on every detached checkout — which is what every CI
    # runner does — so requiring a name match silently skipped the growth check
    # in the one place it has to run. The freeze travels WITH the change (it is
    # a committed file), so its presence is the whole condition; the branch is
    # recorded for the operator, not consulted as a guard. Evaluator finding,
    # PR #79 r1, and my own contract claimed the opposite.
    if freeze:
        # A dropped or rewritten earlier round is a RESET, and a reset is the
        # bypass this record exists to stop. Compare against the base-owned
        # copy: earlier rounds must survive verbatim.
        drift = _rounds_rewritten(base)
        if drift:
            failures.append(
                f"SCOPE FREEZE HISTORY WAS REWRITTEN: {drift}\n"
                f"    The record is append-only. Re-freezing adds a round; it "
                f"never resets the baseline, because a resettable baseline "
                f"means 'this change did not grow' is a claim the author can "
                f"make true after the fact.")
        dl = m["reviewable_lines"] - freeze.get("reviewable_lines", 0)
        df = m["reviewable_files"] - freeze.get("reviewable_files", 0)
        if dl > MAX_GROWTH_LINES or df > MAX_GROWTH_FILES:
            failures.append(
                f"SCOPE GREW UNDER REVIEW by {dl:+} line(s) and {df:+} file(s) "
                f"(tolerance {MAX_GROWTH_LINES}/{MAX_GROWTH_FILES}).\n"
                f"    This is the failure that produced 22 rounds on PR #68 and "
                f"11+ on PR #74: each round reviews a bigger subject than the "
                f"last, so findings never converge and fixes from one round "
                f"create blockers in the next.\n"
                f"    Adopting a reviewer's blocker is fine. NEW WORK IS NOT, "
                f"however urgent it feels — and it always feels urgent. Open a "
                f"new branch: it costs one PR and saves a review spiral.")

    if args.json:
        print(json.dumps({**m, "failures": failures, "warnings": warnings},
                         indent=2))
        return 1 if failures else 0

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
