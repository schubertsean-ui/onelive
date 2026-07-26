#!/usr/bin/env python3
"""Construction Loop Stage 3 gate — blocking memory retrieval (charter item 4).

Greppable summary: reads the red-class index (docs/memory/RED_CLASSES.md),
matches each class's triggers against the diff's changed PATHS AND the
diff's CONTENT (#67 r6: path-only matching missed semantic classes like
nonfinite-decimal-accepted on a generator.py change — triggers now hit
either surface), and requires a DELIBERATE citation for every matched
class: an added line in the SESSION CONTRACT (STATE.md) carrying the
canonical tag `[S3:<token>]` (#67 r6: a bare token anywhere in added
lines — a changelog entry, a code comment, the index row itself — is
incidental text, not evidence of retrieval; the tag form cannot occur by
accident and must live in the contract). The index is SELF-PROTECTED
(#67 r6): the base copy is compared against the head copy — a deleted
token or a narrowed trigger list fails closed, because per this file's
charter that is a gate-threshold relaxation (founder-crucial; a
legitimate ratified removal edits THIS evaluator-reviewed tool in the
same PR as its founder decision record). Fail-closed physics throughout:
unreadable/empty/duplicate-token index, unresolvable diff base, or an
uncited matched class all exit 1; "no matched classes" prints explicitly.
The --paths/--content-file/--citation-text-file/--base-index-file flags
exist for HERMETIC TESTS ONLY — validate never passes them, so
production always derives everything from git.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_RELPATH = os.path.join("docs", "memory", "RED_CLASSES.md")
DEFAULT_INDEX = os.path.join(REPO_ROOT, INDEX_RELPATH)
CONTRACT_RELPATH = "STATE.md"

_ROW_RE = re.compile(r"^\|\s*([a-z0-9][a-z0-9-]+)\s*\|\s*([^|]+)\|")

# How recently the repository must have synchronized with its remote for
# an ALREADY-fetched base ref to count as proven fresh. Generous by
# design: CI fetches at checkout and reaches this gate ~2-3 minutes
# later, and a slow dependency install must not turn a fresh base into a
# red gate. Tightening it is safe; loosening it past the point where a
# human's stale clone would qualify is a gate-threshold relaxation.
BASE_FRESHNESS_WINDOW_S = 30 * 60


def parse_index(text: str, origin: str) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = _ROW_RE.match(line.strip())
        if not match or match.group(1) in ("token", "---"):
            continue
        token = match.group(1)
        if token in index:
            raise SystemExit(
                f"construction_gate: FAIL — duplicate red-class token {token!r} "
                f"in {origin}; tokens are history keys and must be unique"
            )
        triggers = [t.strip().lower() for t in match.group(2).split(",") if t.strip()]
        if triggers:
            index[token] = triggers
    if not index:
        raise SystemExit(
            f"construction_gate: FAIL — red-class index parsed to zero rows "
            f"({origin}); an empty brain never passes silently"
        )
    return index


def load_index(path: str) -> dict[str, list[str]]:
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise SystemExit(f"construction_gate: FAIL — red-class index unreadable ({exc})")
    return parse_index(text, path)


def _git(args: list[str], *, allow_fail: bool = False) -> str | None:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, cwd=REPO_ROOT)
    if proc.returncode != 0:
        if allow_fail:
            return None
        raise SystemExit(
            f"construction_gate: FAIL — git {' '.join(args[:2])} failed "
            f"({proc.stderr.strip()}); an unresolvable diff base is gate "
            "misconfiguration and never passes silently (fetch the base ref)"
        )
    return proc.stdout


def _fetch_head_age_s(now: float | None = None) -> float | None:
    """Seconds since this repository last completed a fetch, or None when
    no fetch record exists. `.git/FETCH_HEAD` is written by every
    successful `git fetch`, so its mtime is a RECORD of synchronization,
    not a claim about one."""
    git_dir = (_git(["rev-parse", "--git-dir"], allow_fail=True) or "").strip()
    if not git_dir:
        return None
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(REPO_ROOT, git_dir)
    try:
        mtime = os.path.getmtime(os.path.join(git_dir, "FETCH_HEAD"))
    except OSError:
        return None
    return max(0.0, (time.time() if now is None else now) - mtime)


def assert_base_fresh(base_ref: str, *, fetch=None, age=None) -> str:
    """PROVE the base ref is synchronized with its remote, or fail closed.

    The obligation is the PROPERTY (`origin/master` reflects the remote),
    never one particular mechanism for reaching it (#71 CI-caught, class:
    false-confidence-gate). Two proofs are accepted, in order:

      1. A fetch performed HERE succeeds — synchronization now.
      2. The fetch is impossible here but the repository ALREADY
         synchronized within BASE_FRESHNESS_WINDOW_S and the base ref
         resolves. This is the CI shape: `actions/checkout` fetches the
         full history and then drops the credentials
         (`persist-credentials: false`), so the base is fresh BY
         CONSTRUCTION while a fetch from inside the job cannot
         authenticate. Demanding proof #1 there failed a base that was
         provably fresher than any fetch this gate could perform.

    Neither proof available (offline agent session, stale clone, no fetch
    record) = FAIL, unchanged: a stale base widens the diff range and
    lets this gate pass what CI correctly fails
    (class: stale-base-widens-range). `fetch` and `age` are injected
    CALLABLES, HERMETIC TESTS ONLY — callables, not values, so that
    "no fetch record" (None) stays expressible and testable rather than
    colliding with "argument not supplied". Returns the human-readable
    proof, for printing.
    """
    remote, _, branch = base_ref.partition("/")
    fetcher = fetch if fetch is not None else _run_fetch
    if remote and branch and fetcher(remote, branch):
        return f"fetched {branch} from {remote} in this run"
    age_s = (_fetch_head_age_s if age is None else age)()
    resolved = _git(["rev-parse", "--verify", "--quiet", base_ref], allow_fail=True)
    if age_s is not None and age_s <= BASE_FRESHNESS_WINDOW_S and resolved:
        return (
            f"fetch from inside this run unavailable; {base_ref} resolves and "
            f"this repository last fetched {int(age_s)}s ago "
            f"(window {BASE_FRESHNESS_WINDOW_S}s)"
        )
    raise SystemExit(
        f"construction_gate: FAIL — cannot prove {base_ref} is fresh. The fetch "
        "did not succeed here and this repository carries no fetch record inside "
        f"the {BASE_FRESHNESS_WINDOW_S}s freshness window"
        + (f" (last fetch {int(age_s)}s ago)" if age_s is not None else " (no fetch record)")
        + (f"; {base_ref} does not resolve" if not resolved else "")
        + ". A stale base widens the diff range and lets this gate pass what CI "
        "fails (class: stale-base-widens-range). Restore network/remote access "
        "and rerun; never judge against an unverifiable base."
    )


def _run_fetch(remote: str, branch: str) -> bool:
    proc = subprocess.run(
        ["git", "fetch", remote, branch],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return proc.returncode == 0


def assert_index_not_weakened(head: dict[str, list[str]], base_text: str | None) -> None:
    """#67 r6: the gate must not be silently weakenable through its own
    data. Base copy absent = bootstrap (the index is new in this PR),
    printed explicitly; otherwise every base token must survive with at
    least its base triggers."""
    if base_text is None:
        print(
            "construction_gate: index has no base copy (bootstrap PR) — "
            "self-protection begins at its merge"
        )
        return
    base = parse_index(base_text, "base copy of the index")
    for token, base_triggers in base.items():
        if token not in head:
            raise SystemExit(
                f"construction_gate: FAIL — red-class token {token!r} was REMOVED "
                "from the index; removal is a gate-threshold relaxation "
                "(founder-crucial) and never lands as a silent index edit"
            )
        missing = [t for t in base_triggers if t not in head[token]]
        if missing:
            raise SystemExit(
                f"construction_gate: FAIL — token {token!r} lost triggers "
                f"{missing}; narrowing is a gate-threshold relaxation "
                "(founder-crucial) and never lands as a silent index edit"
            )


def changed_paths(diff_range: str) -> list[str]:
    out = _git(["diff", "--name-only", diff_range])
    return [p for p in (out or "").splitlines() if p.strip()]


def diff_content(diff_range: str) -> str:
    """Matching surface #2 (#67 r6): the change's own text, so semantic
    classes (price/decimal/filter…) match even when no path names them."""
    return (_git(["diff", "--unified=0", diff_range]) or "").lower()


def contract_added_lines(diff_range: str) -> str:
    """Citation surface: ONLY lines this change ADDS to the session
    contract (r5: never cumulative history; r6: never incidental text in
    other files)."""
    out = _git(["diff", "--unified=0", diff_range, "--", CONTRACT_RELPATH]) or ""
    return "\n".join(
        line[1:] for line in out.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def match_classes(index: dict[str, list[str]], paths: list[str], content: str) -> list[str]:
    lowered_paths = [p.lower() for p in paths]
    content = content.lower()
    return sorted(
        token
        for token, triggers in index.items()
        if any(
            trigger in path for trigger in triggers for path in lowered_paths
        )
        or any(trigger in content for trigger in triggers)
    )


def citation_tag(token: str) -> str:
    return f"[S3:{token}]"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default=DEFAULT_INDEX)
    parser.add_argument(
        "--diff-range", default=None,
        help="explicit git diff range (tests); default = merge-base(base-ref, HEAD), "
        "diffed against the WORKING TREE so validate sees pre-commit citations",
    )
    parser.add_argument("--base-ref", default="origin/master")
    parser.add_argument("--paths", nargs="*", default=None, help="HERMETIC TESTS ONLY")
    parser.add_argument("--content-file", default=None, help="HERMETIC TESTS ONLY")
    parser.add_argument("--citation-text-file", default=None, help="HERMETIC TESTS ONLY")
    parser.add_argument(
        "--base-index-file", default=None,
        help="HERMETIC TESTS ONLY ('-' = simulate absent base copy)",
    )
    args = parser.parse_args(argv)

    if args.diff_range is None:
        # The base ref is only trustworthy if it is PROVEN synchronized —
        # the gate owns that proof itself now (#71 CI-caught), instead of
        # validate wrapping it in a fetch whose success it mistook for the
        # property. Hermetic tests always pass --diff-range and so never
        # reach the network.
        print(f"construction_gate: base freshness — {assert_base_fresh(args.base_ref)}")
        # Default surface: merge-base vs the WORKING TREE (single-arg git
        # diff) — validate runs BEFORE the commit, and citations written in
        # this build must count whether or not they are committed yet. An
        # unresolvable merge-base fails closed inside _git.
        merge_base = (_git(["merge-base", args.base_ref, "HEAD"]) or "").strip()
        args.diff_range = merge_base

    index = load_index(args.index)

    if args.base_index_file is not None:
        base_text = None if args.base_index_file == "-" else open(
            args.base_index_file, encoding="utf-8"
        ).read()
    else:
        base_text = _git(
            ["show", f"{args.base_ref}:{INDEX_RELPATH.replace(os.sep, '/')}"],
            allow_fail=True,
        )
    assert_index_not_weakened(index, base_text)

    hermetic = args.paths is not None
    paths = args.paths if hermetic else changed_paths(args.diff_range)
    if not paths:
        print(
            f"construction_gate: zero changed paths in a RESOLVED diff range "
            f"({args.diff_range}) — nothing to retrieve against"
        )
        return 0
    if args.content_file is not None:
        content = open(args.content_file, encoding="utf-8").read().lower()
    elif hermetic:
        content = ""
    else:
        content = diff_content(args.diff_range)

    matched = match_classes(index, paths, content)
    if not matched:
        print(
            "construction_gate: no matched red classes for this change surface "
            f"({len(paths)} paths x {len(index)} classes) — explicit result, not silence"
        )
        return 0

    if args.citation_text_file is not None:
        try:
            citation_text = open(args.citation_text_file, encoding="utf-8").read()
        except OSError as exc:
            print(f"construction_gate: FAIL — citation text unreadable ({exc})")
            return 1
    else:
        citation_text = contract_added_lines(args.diff_range)

    uncited = [t for t in matched if citation_tag(t) not in citation_text]
    print(f"construction_gate: matched red classes: {', '.join(matched)}")
    if uncited:
        print(
            "construction_gate: FAIL — the session contract's added lines lack "
            "the deliberate citation tags: "
            + ", ".join(citation_tag(t) for t in uncited)
            + f"\n  (Stage 3 is BLOCKING and binds to THE CURRENT BUILD: retrieve "
            f"docs/memory/RED_CLASSES.md, answer each matched class, and write "
            f"`[S3:<token>] <answer>` on a line added to {CONTRACT_RELPATH} in "
            "this change — a bare token in a changelog, comment, or the index "
            "row itself is incidental text, not retrieval evidence)"
        )
        return 1
    print("construction_gate: all matched classes carry [S3:…] contract citations — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
