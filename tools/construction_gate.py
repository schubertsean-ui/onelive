#!/usr/bin/env python3
"""Construction Loop Stage 3 gate — blocking memory retrieval (charter item 4).

Greppable summary: reads the red-class index (docs/memory/RED_CLASSES.md),
matches each class's path-substring triggers against the diff's CHANGED
FILE PATHS, and requires the CURRENT CHANGE'S OWN ADDED LINES to cite
every matched class token (#67 r5: STATE.md is cumulative, so checking
the whole file let STALE historical citations satisfy the gate — the
citation surface is now the diff's added lines, which binds retrieval
evidence to THIS build, not to history). Fail-closed physics (#67 r4:
the rule ships with its mechanism, or it is aspirational documentation):
- unreadable/empty index -> exit 1 (a missing brain never passes silently);
- unresolvable diff or base ref -> exit 1 (misconfiguration is never a no-op);
- matched class token absent from the change's added lines -> exit 1;
- no matched classes -> prints exactly that (an explicit result) and exits 0.
Run by tools/validate on every diff against the base branch. Widening a
trigger list is safe; REMOVING a row or narrowing triggers is a
gate-threshold relaxation: founder-crucial. The --paths/--citation-text
overrides exist for HERMETIC TESTS ONLY — the validate wiring never
passes them, so production always derives both from git.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_INDEX = os.path.join(REPO_ROOT, "docs", "memory", "RED_CLASSES.md")

_ROW_RE = re.compile(r"^\|\s*([a-z0-9][a-z0-9-]+)\s*\|\s*([^|]+)\|")


def load_index(path: str) -> dict[str, list[str]]:
    """token -> lowercase trigger substrings. Fail closed on absence,
    unreadability, or an empty table."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise SystemExit(f"construction_gate: FAIL — red-class index unreadable ({exc})")
    index: dict[str, list[str]] = {}
    for line in text.splitlines():
        match = _ROW_RE.match(line.strip())
        if not match or match.group(1) in ("token", "---"):
            continue
        triggers = [t.strip().lower() for t in match.group(2).split(",") if t.strip()]
        if triggers:
            index[match.group(1)] = triggers
    if not index:
        raise SystemExit(
            "construction_gate: FAIL — red-class index parsed to zero rows "
            f"({path}); an empty brain never passes silently"
        )
    return index


def _git(args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=REPO_ROOT
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"construction_gate: FAIL — git {' '.join(args[:2])} failed "
            f"({proc.stderr.strip()}); an unresolvable diff base is gate "
            "misconfiguration and never passes silently (fetch the base ref)"
        )
    return proc.stdout


def changed_paths(diff_range: str) -> list[str]:
    return [p for p in _git(["diff", "--name-only", diff_range]).splitlines() if p.strip()]


def added_lines(diff_range: str) -> str:
    """The citation surface (#67 r5): ONLY lines this change ADDS — a
    token present merely in pre-existing file content is history, not
    evidence that THIS build retrieved and answered the class."""
    out = _git(["diff", "--unified=0", diff_range])
    return "\n".join(
        line[1:] for line in out.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def match_classes(index: dict[str, list[str]], paths: list[str]) -> list[str]:
    lowered = [p.lower() for p in paths]
    return sorted(
        token
        for token, triggers in index.items()
        if any(trigger in path for trigger in triggers for path in lowered)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default=DEFAULT_INDEX)
    parser.add_argument("--diff-range", default="origin/master...HEAD")
    parser.add_argument(
        "--paths", nargs="*", default=None,
        help="HERMETIC TESTS ONLY: explicit changed paths (production derives from git)",
    )
    parser.add_argument(
        "--citation-text-file", default=None,
        help="HERMETIC TESTS ONLY: file standing in for the diff's added lines",
    )
    args = parser.parse_args(argv)

    index = load_index(args.index)
    paths = args.paths if args.paths is not None else changed_paths(args.diff_range)
    if not paths:
        print(
            "construction_gate: zero changed paths in a RESOLVED diff range "
            f"({args.diff_range}) — nothing to retrieve against"
        )
        return 0
    matched = match_classes(index, paths)
    if not matched:
        print(
            "construction_gate: no matched red classes for this change surface "
            f"({len(paths)} paths x {len(index)} classes) — explicit result, not silence"
        )
        return 0
    if args.citation_text_file is not None:
        try:
            with open(args.citation_text_file, encoding="utf-8") as fh:
                citation_text = fh.read()
        except OSError as exc:
            print(f"construction_gate: FAIL — citation text unreadable ({exc})")
            return 1
    else:
        citation_text = added_lines(args.diff_range)
    uncited = [token for token in matched if token not in citation_text]
    print(f"construction_gate: matched red classes: {', '.join(matched)}")
    if uncited:
        print(
            "construction_gate: FAIL — this change's ADDED LINES do not cite: "
            + ", ".join(uncited)
            + "\n  (Stage 3 is BLOCKING and binds to THE CURRENT BUILD: retrieve "
            "docs/memory/RED_CLASSES.md, answer each matched class in this "
            "session's contract/premortem, and write the citation IN THIS "
            "CHANGE — a stale token in pre-existing history is not retrieval)"
        )
        return 1
    print("construction_gate: all matched classes cited in this change — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
