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
