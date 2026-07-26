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


class _GitProbes:
    """The real evidence sources for base-ref freshness. Injected as one
    object so hermetic tests replace evidence, never patch globals."""

    @staticmethod
    def remote_tip(remote: str, branch: str) -> str | None:
        """The remote's CURRENT oid for the branch, or None when the
        remote is unreachable (no credentials / offline). Read-only and
        non-interactive: a credential prompt would hang the job, so the
        terminal prompt is disabled and the call is time-boxed."""
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        try:
            proc = subprocess.run(
                ["git", "ls-remote", "--exit-code", remote, f"refs/heads/{branch}"],
                capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        first = proc.stdout.split("\n", 1)[0].split("\t")[0].strip()
        return first or None

    @staticmethod
    def fetch(remote: str, branch: str) -> None:
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        try:
            subprocess.run(
                ["git", "fetch", remote, branch],
                capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return

    @staticmethod
    def local_oid(ref: str) -> str | None:
        out = _git(["rev-parse", "--verify", "--quiet", ref], allow_fail=True)
        return (out or "").strip() or None

    @staticmethod
    def ref_update_age_s(ref: str, now: float | None = None) -> float | None:
        """Seconds since THIS remote-tracking ref was itself last written,
        or None when no such record exists.

        Deliberately ref-SPECIFIC (#71 r6 blocker): `.git/FETCH_HEAD`
        records that *some* fetch happened, which a recent unrelated
        fetch satisfies while the base ref stays stale. Two ref-scoped
        records are read and the FRESHER wins: the ref's own reflog
        (written whenever git updates it) and, for repositories with
        reflogs disabled, the loose ref file's mtime. Both describe this
        ref and nothing else."""
        now = time.time() if now is None else now
        ages: list[float] = []
        out = _git(["reflog", "show", "--date=unix", "-n", "1", ref], allow_fail=True)
        match = re.search(r"@\{(\d+)", out or "")
        if match:
            ages.append(max(0.0, now - int(match.group(1))))
        git_dir = (_git(["rev-parse", "--git-dir"], allow_fail=True) or "").strip()
        if git_dir:
            if not os.path.isabs(git_dir):
                git_dir = os.path.join(REPO_ROOT, git_dir)
            try:
                ages.append(max(0.0, now - os.path.getmtime(
                    os.path.join(git_dir, *ref.split("/"))
                    if ref.startswith("refs/")
                    else os.path.join(git_dir, "refs", "remotes", *ref.split("/"))
                )))
            except OSError:
                pass
        return min(ages) if ages else None


def assert_base_fresh(base_ref: str, *, probes=None) -> str:
    """PROVE the base ref reflects its remote, or fail closed.

    The obligation is the PROPERTY, and neither a command's exit code nor
    a repo-wide fetch record is that property (#71 r5/r6, class:
    false-confidence-gate — this gate got it wrong twice, each time by
    substituting a MECHANISM for the thing the mechanism was supposed to
    establish). Two proofs, in order:

      1. DIRECT: the remote is reachable, so its current tip is read and
         COMPARED against the local base ref (one fetch is attempted to
         converge them first). Equal oids are the property itself; a
         surviving difference FAILS. A fetch that "succeeded" while
         leaving the base ref behind no longer passes anything.
      2. REF-SCOPED RECORD: the remote is unreachable, but THIS ref
         resolves and THIS ref was itself written within
         BASE_FRESHNESS_WINDOW_S. That is the CI shape and only the CI
         shape: `actions/checkout` fetches the full history, creating
         `origin/master` right there, and then drops the credentials
         (`persist-credentials: false`), so nothing inside the job can
         reach the remote while the ref is fresher than any fetch this
         gate could perform. HONEST LIMIT, stated rather than implied:
         this bounds staleness by the window, it does not prove the
         remote has not moved since — which is why it is the fallback,
         is ref-scoped rather than repo-wide, and never applies when
         proof 1 is available.

    Neither proof (offline session, stale clone, no ref record) = FAIL:
    a stale base widens the diff range and lets this gate pass what CI
    correctly fails (class: stale-base-widens-range). `probes` is a
    HERMETIC-TEST injection point. Returns the proof, for printing.
    """
    probes = probes or _GitProbes
    remote, _, branch = base_ref.partition("/")
    if not remote or not branch:
        raise SystemExit(
            f"construction_gate: FAIL — base ref {base_ref!r} is not in "
            "<remote>/<branch> form, so its freshness cannot be proven"
        )
    tip = probes.remote_tip(remote, branch)
    if tip is not None:
        local = probes.local_oid(base_ref)
        if local != tip:
            probes.fetch(remote, branch)
            local = probes.local_oid(base_ref)
        if local == tip:
            return f"{base_ref} == remote tip {tip[:12]} (compared against ls-remote)"
        raise SystemExit(
            f"construction_gate: FAIL — {base_ref} is {local or 'unresolvable'} but "
            f"the remote's {branch} is {tip}; a fetch did not converge them, so the "
            "base is STALE and every range derived from it is wider than CI's "
            "(class: stale-base-widens-range). Resolve the base ref and rerun."
        )
    age_s = probes.ref_update_age_s(base_ref)
    local = probes.local_oid(base_ref)
    if local and age_s is not None and age_s <= BASE_FRESHNESS_WINDOW_S:
        return (
            f"remote unreachable from here; {base_ref} resolves ({local[:12]}) and "
            f"was itself written {int(age_s)}s ago (window {BASE_FRESHNESS_WINDOW_S}s)"
        )
    raise SystemExit(
        f"construction_gate: FAIL — cannot prove {base_ref} reflects its remote. The "
        "remote is unreachable from here and "
        + (f"this ref was last written {int(age_s)}s ago, outside the "
           f"{BASE_FRESHNESS_WINDOW_S}s window" if age_s is not None
           else "this ref carries no update record")
        + ("" if local else f"; {base_ref} does not resolve")
        + ". A stale base widens the diff range and lets this gate pass what CI "
        "fails (class: stale-base-widens-range). Restore network/remote access "
        "and rerun; never judge against an unverifiable base."
    )


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
