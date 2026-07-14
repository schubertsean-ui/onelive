#!/usr/bin/env python3
"""Deferral-language scanner — mechanical arm of docs/RECORD.md ("Recording").

Greppable summary: founder rule (2026-07-13): every "for now" / "check
later" / "revisit" / "good enough" style deferral must be RECORDED in
docs/RECORD.md, never silent. This scanner walks code comments (py/yml/sh
`#`, ts/tsx/js `//` and `/* */` blocks, sql `--`) in the source trees and
fails on any deferral phrase that does not carry an `[R-###]` tag pointing
at an OPEN register row — a tag aimed at a RESOLVED row (or at nothing)
also fails, so stale deferrals cannot linger in code after their trigger
fires. Prose docs are out of scope (charter + evaluator review cover them).
Wired into `tools/validate` as a blocking check. Exit codes per
tools/README.md: 0 clean / 1 violations / 2 hard failure (register
missing/unreadable/unparseable).

Contributor note on false positives: the scanner deliberately treats a
comment marker ANYWHERE on a line as starting a comment (a marker inside a
string/URL can therefore fire). That bias is chosen — a missed real comment
would be a silent-deferral hole — so when a false positive fires, reword the
string or tag the line; do not weaken the scanner.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RECORD = REPO / "docs" / "RECORD.md"

# Trees that hold code. Prose lives in docs/ and is deliberately not scanned.
SCAN_DIRS = ["api", "worker", "ai", "tools", "web", "tests", ".github", "supabase"]
EXTRA_FILES = ["tools/validate"]  # bash, no extension
SKIP_PARTS = {"node_modules", ".next", "__pycache__", ".pytest_cache", "var"}

# suffix → line-comment marker. Extensionless files (tools/validate) are bash.
COMMENT_MARKERS = {
    ".py": "#", ".yml": "#", ".yaml": "#", ".sh": "#", ".cfg": "#", ".toml": "#",
    ".ts": "//", ".tsx": "//", ".js": "//", ".jsx": "//",
    ".sql": "--",
}
# Suffixes whose languages also allow /* ... */ block comments.
BLOCK_COMMENT_SUFFIXES = {".ts", ".tsx", ".js", ".jsx"}
_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

# Deferral vocabulary. Word-ish phrases, case-insensitive, comments only.
PHRASES = (
    "for now",
    "check later",
    "fix later",
    "handle later",
    "do this later",
    "come back to",
    "revisit",
    "temporar",     # covers the adjective and the adverb
    "good enough",
    "someday",
    "eventually",
    "stopgap",
    "band-aid",
    "kludge",
    "quick hack",
    "punt on",
)
_PHRASE_RE = re.compile("|".join(re.escape(p) for p in PHRASES), re.IGNORECASE)
_TAG_RE = re.compile(r"\[R-(\d{3,})\]")
_ROW_RE = re.compile(r"^\|\s*R-(\d{3,})\s*\|")


def load_register() -> tuple[set[str], set[str]]:
    """Parse docs/RECORD.md's table rows into (open_ids, all_ids).

    Only actual `| R-### | ... | STATUS |` table rows count — an incidental
    prose mention of an id is NOT a register entry. A row is live only while
    its status cell starts with OPEN; anything else (RESOLVED, ESCALATED …)
    means code comments must stop pointing at it. A register with zero
    parseable rows is treated as a hard failure, not an empty-and-clean one.
    """
    if not RECORD.exists():
        raise FileNotFoundError(f"{RECORD} does not exist — the register is mandatory.")
    open_ids: set[str] = set()
    all_ids: set[str] = set()
    for line in RECORD.read_text(encoding="utf-8").splitlines():
        m = _ROW_RE.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rid = m.group(1)
        all_ids.add(rid)
        status = cells[-1] if cells else ""
        if status.upper().startswith("OPEN"):
            open_ids.add(rid)
    if not all_ids:
        raise ValueError(
            f"{RECORD} contains no parseable `| R-### | … |` table rows — "
            "register format broken; refusing to treat that as 'clean'."
        )
    return open_ids, all_ids


def _comment_text(line: str, marker: str) -> str | None:
    """Return the comment portion of a line, or None if it has no comment.

    Deliberately simple (marker anywhere on the line): a marker inside a
    string can cause a false positive, which is acceptable — tag or reword —
    while a missed real comment would be a silent-deferral hole.
    """
    idx = line.find(marker)
    return line[idx:] if idx != -1 else None


def comment_units(path: pathlib.Path) -> list[tuple[int, str]]:
    """Return (line_number, comment_text) units for one file.

    Line comments yield one unit per line; `/* ... */` block comments (TS/JS)
    yield one unit per block, anchored at the block's first line, so a tag
    anywhere in a block covers the whole block.
    """
    suffix = path.suffix if path.suffix else ".sh"
    marker = COMMENT_MARKERS.get(suffix)
    if marker is None:
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    units = [
        (n, comment)
        for n, line in enumerate(text.splitlines(), 1)
        if (comment := _comment_text(line, marker)) is not None
    ]
    if suffix in BLOCK_COMMENT_SUFFIXES:
        units.extend(
            (text.count("\n", 0, m.start()) + 1, m.group(0))
            for m in _BLOCK_RE.finditer(text)
        )
    return units


def iter_files() -> list[pathlib.Path]:
    files = []
    for d in SCAN_DIRS:
        root = REPO / d
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and not (set(p.parts) & SKIP_PARTS):
                files.append(p)
    files.extend(REPO / f for f in EXTRA_FILES if (REPO / f).exists())
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail on deferral-language code comments lacking an "
                    "[R-###] tag pointing at an OPEN docs/RECORD.md row."
    )
    parser.parse_args(argv)
    try:
        open_ids, all_ids = load_register()
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"deferral_scan: HARD FAIL — {exc}", file=sys.stderr)
        return 2

    violations = 0
    for path in iter_files():
        rel = path.relative_to(REPO)
        for n, comment in comment_units(path):
            tags = _TAG_RE.findall(comment)
            if _PHRASE_RE.search(comment) and not tags:
                violations += 1
                print(f"{rel}:{n}: untagged deferral comment — record it in "
                      f"docs/RECORD.md and tag [R-###]: {comment.strip()[:160]}",
                      file=sys.stderr)
            # Every tag must point at a LIVE row — a dangling tag is a silent
            # deferral wearing a costume, and a tag on a RESOLVED row is a
            # fired trigger still lingering in code.
            for tag in tags:
                if tag not in all_ids:
                    violations += 1
                    print(f"{rel}:{n}: tag [R-{tag}] has no entry in "
                          "docs/RECORD.md.", file=sys.stderr)
                elif tag not in open_ids:
                    violations += 1
                    print(f"{rel}:{n}: tag [R-{tag}] points at a non-OPEN "
                          "register row — the deferral was resolved, so remove "
                          "or reword this comment.", file=sys.stderr)
    if violations:
        print(f"deferral_scan: {violations} violation(s) — every deferral gets "
              "a live Record entry, none stay silent.", file=sys.stderr)
        return 1
    print("deferral_scan: OK — no untagged deferral language in code comments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
