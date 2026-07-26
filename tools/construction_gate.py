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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_RELPATH = os.path.join("docs", "memory", "RED_CLASSES.md")
DEFAULT_INDEX = os.path.join(REPO_ROOT, INDEX_RELPATH)
CONTRACT_RELPATH = "STATE.md"

_ROW_RE = re.compile(r"^\|\s*([a-z0-9][a-z0-9-]+)\s*\|\s*([^|]+)\|")


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
    object so hermetic tests can substitute evidence — but note that the
    two shipped probes are ALSO exercised against real git (#71 r7
    blocker: a double that encodes the behavior we wish git had proves
    only the double)."""

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
        """Update the remote-tracking ref, with an EXPLICIT refspec.

        `git fetch <remote> <branch>` only updates
        `refs/remotes/<remote>/<branch>` opportunistically — it depends
        on the remote carrying the conventional fetch refspec, which a
        bare URL or a hand-configured remote need not (#71 r7 blocker).
        Naming the destination removes the dependency entirely."""
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        try:
            subprocess.run(
                ["git", "fetch", remote,
                 f"+refs/heads/{branch}:refs/remotes/{remote}/{branch}"],
                capture_output=True, text=True, cwd=REPO_ROOT, env=env, timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return

    @staticmethod
    def local_oid(ref: str) -> str | None:
        out = _git(["rev-parse", "--verify", "--quiet", ref], allow_fail=True)
        return (out or "").strip() or None

def assert_base_fresh(base_ref: str, *, probes=None) -> str:
    """PROVE the base ref equals its remote's current tip, or fail closed.

    ONE proof, because there is only one (#71 r5-r8, class:
    false-confidence-gate — four successive attempts to establish this
    property WITHOUT contacting the remote were each shown to be a
    mechanism standing in for the property: a fetch's exit code, a
    repo-wide fetch record, a recent write to the ref, and a two-parent
    HEAD whose first parent matches — that last one reproducible offline
    by checking out a stale base and merging the feature branch). The
    conclusion the reviewer drove us to, stated plainly: staleness is a
    fact about the REMOTE, so no local artifact can settle it.

    So: read the remote's current tip, fetch once (explicit refspec) to
    converge, and compare ids. Equal is the property itself. Anything
    else — a surviving difference, or a remote we cannot reach at all —
    FAILS, because a stale base widens the diff range and lets this gate
    pass what CI correctly fails (class: stale-base-widens-range).

    Consequence, accepted rather than worked around: this gate cannot run
    without remote access. The CI review job therefore grants read-only
    remote access for the validate step alone (see
    .github/workflows/adversarial-review.yml) instead of the gate
    inventing an offline substitute. `probes` is a HERMETIC-TEST
    injection point; the shipped probes are separately exercised against
    real git. Returns the proof, for printing.
    """
    probes = probes or _GitProbes
    remote, _, branch = base_ref.partition("/")
    if not remote or not branch:
        raise SystemExit(
            f"construction_gate: FAIL — base ref {base_ref!r} is not in "
            "<remote>/<branch> form, so its freshness cannot be proven"
        )
    tip = probes.remote_tip(remote, branch)
    if tip is None:
        raise SystemExit(
            f"construction_gate: FAIL — the remote for {base_ref} is unreachable, so "
            "this gate cannot prove the base is current. There is deliberately NO "
            "offline fallback: every local signal that might stand in for the remote "
            "(a fetch's exit code, a fetch record, a recent ref write, a merge "
            "commit's first parent) is reproducible from a STALE base, and accepting "
            "one reopens stale-base-widens-range inside the gate that exists to close "
            "it. Restore network/remote access and rerun."
        )
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


def contradictory_citations(citation_text: str) -> list[str]:
    """Tokens answered MORE THAN ONCE with no supersession marker.

    PR #78 r7, class false-confidence-gate. The gate checked that every matched
    class HAS an answer and never that the answers agree, so a contract could
    carry `[S3:x] no scripted edit was applied` from round 1 and
    `[S3:x] a scripted edit destroyed the ledger` from round 6 — both added
    lines, both passing, flatly contradicting each other. Retrieval evidence
    that can say two opposite things verifies nothing.

    Multiple answers are legitimate across review rounds; SILENTLY multiple is
    not. All but the last must be explicitly marked stale, which is also the
    honest way to correct a contract: show the correction rather than rewrite
    history.
    """
    seen: dict[str, list[str]] = {}
    for line in citation_text.splitlines():
        for m in re.finditer(r"\[S3:([a-z0-9-]+)\]", line):
            seen.setdefault(m.group(1), []).append(line)
    # ORDER-INDEPENDENT: exactly one answer per token may be LIVE. Keying on
    # "all but the last" assumed corrections are appended, and they are not —
    # a contract is edited in place, so the superseded line can sit anywhere.
    # EXACTLY ONE live answer — not "at most one". The first cut only failed on
    # len(live) > 1, so `[S3:x] WITHDRAWN` alone satisfied the presence check
    # (the tag IS in the text) while leaving ZERO live retrieval evidence, and
    # the gate reported PASS. A fail-open introduced by the fix for a
    # fail-open (PR #78 r10, openai absence-only seat).
    bad = []
    for token, lines in seen.items():
        # SUPERSEDED / WITHDRAWN only. "CORRECTED" was in this list and is
        # wrong: `[S3:x] CORRECTED at r3 — <the answer>` is how a LIVE answer
        # records that it fixes an earlier one, so counting it stale left
        # several classes with zero live answers (PR #78 r10, caught by the
        # exactly-one rule the same round introduced). The two remaining words
        # mean "this line is no longer the answer"; "corrected" means "this
        # line IS the answer, and it changed".
        live = [ln for ln in lines
                if not re.search(r"\b(SUPERSEDED|WITHDRAWN)\b", ln)]
        if len(live) != 1:
            bad.append(token)
    return sorted(bad)


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

    # The diff range is resolved LAZILY, and proving the base ref current
    # is part of resolving it (#71 r9, self-caught in CI): a run whose
    # paths, content and citations are all supplied never derives anything
    # from git, so demanding remote access there made supposedly hermetic
    # tests depend on the network — they passed on a machine with a
    # reachable remote and failed in CI's plain pytest step. Freshness is
    # owed exactly when a value comes from the repository, never before.
    resolved: dict[str, str | None] = {"range": args.diff_range}

    def diff_range() -> str:
        if resolved["range"] is None:
            print(
                "construction_gate: base freshness — "
                f"{assert_base_fresh(args.base_ref)}"
            )
            # Default surface: merge-base vs the WORKING TREE (single-arg
            # git diff) — validate runs BEFORE the commit, and citations
            # written in this build must count whether or not they are
            # committed yet. An unresolvable merge-base fails closed
            # inside _git.
            resolved["range"] = (
                _git(["merge-base", args.base_ref, "HEAD"]) or ""
            ).strip()
        return resolved["range"]

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
    paths = args.paths if hermetic else changed_paths(diff_range())
    if not paths:
        print(
            f"construction_gate: zero changed paths in a RESOLVED diff range "
            f"({diff_range()}) — nothing to retrieve against"
        )
        return 0
    if args.content_file is not None:
        content = open(args.content_file, encoding="utf-8").read().lower()
    elif hermetic:
        content = ""
    else:
        content = diff_content(diff_range())

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
        citation_text = contract_added_lines(diff_range())

    uncited = [t for t in matched if citation_tag(t) not in citation_text]
    print(f"construction_gate: matched red classes: {', '.join(matched)}")
    conflicting = contradictory_citations(citation_text)
    if conflicting:
        print(
            "construction_gate: FAIL — these classes do not have EXACTLY ONE "
            "live answer in the contract: " + ", ".join(conflicting)
            + "\n  (two live answers contradict each other and verify nothing; "
            "ZERO live answers — every line marked SUPERSEDED / WITHDRAWN — satisfies the presence check while retrieving nothing, "
            "so a correction must leave a live answer behind)"
        )
        return 1
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
