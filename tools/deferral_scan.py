#!/usr/bin/env python3
"""Deferral-language scanner — mechanical arm of docs/RECORD.md ("Recording").

Greppable summary: founder rule (2026-07-13): every "for now" / "check
later" / "revisit" / "good enough" style deferral must be RECORDED in
docs/RECORD.md, never silent. This scanner walks code comments (py/yml/sh
`#`, ts/tsx/js `//`) in the source trees and fails on any deferral phrase
that does not carry an `[R-###]` tag pointing at a register entry that
actually exists in docs/RECORD.md. Prose docs are out of scope (charter +
evaluator review cover them). Wired into `tools/validate` as a blocking
check. Exit codes per tools/README.md: 0 clean / 1 violations / 2 hard
failure (register missing/unreadable).
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RECORD = REPO / "docs" / "RECORD.md"

# Trees that hold code. Prose lives in docs/ and is deliberately not scanned.
SCAN_DIRS = ["api", "worker", "ai", "tools", "web", "tests", ".github"]
EXTRA_FILES = ["tools/validate"]  # bash, no extension
SKIP_PARTS = {"node_modules", ".next", "__pycache__", ".pytest_cache", "var"}

HASH_COMMENT_SUFFIXES = {".py", ".yml", ".yaml", ".sh", ".cfg", ".toml"}
SLASH_COMMENT_SUFFIXES = {".ts", ".tsx", ".js", ".jsx"}

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


def _registered_ids() -> set[str]:
    if not RECORD.exists():
        raise FileNotFoundError(f"{RECORD} does not exist — the register is mandatory.")
    return set(re.findall(r"\bR-(\d{3,})\b", RECORD.read_text(encoding="utf-8")))


def _comment_text(line: str, suffix: str) -> str | None:
    """Return the comment portion of a line, or None if it has no comment.

    Deliberately simple (marker anywhere on the line): a marker inside a
    string can cause a false positive, which is acceptable — tag or reword —
    while a missed real comment would be a silent-deferral hole.
    """
    marker = "#" if suffix in HASH_COMMENT_SUFFIXES else "//"
    idx = line.find(marker)
    return line[idx:] if idx != -1 else None


def scan_file(path: pathlib.Path) -> list[tuple[int, str]]:
    """Return (line_number, line) for untagged deferral comments in one file."""
    suffix = path.suffix if path.suffix else ".sh"
    if suffix not in HASH_COMMENT_SUFFIXES | SLASH_COMMENT_SUFFIXES:
        return []
    hits = []
    for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        comment = _comment_text(line, suffix)
        if comment and _PHRASE_RE.search(comment) and not _TAG_RE.search(comment):
            hits.append((n, line.strip()))
    return hits


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
                    "[R-###] tag from docs/RECORD.md."
    )
    parser.parse_args(argv)
    try:
        registered = _registered_ids()
    except (FileNotFoundError, OSError) as exc:
        print(f"deferral_scan: HARD FAIL — {exc}", file=sys.stderr)
        return 2

    violations = 0
    for path in iter_files():
        for n, line in scan_file(path):
            violations += 1
            print(f"{path.relative_to(REPO)}:{n}: untagged deferral comment — "
                  f"record it in docs/RECORD.md and tag [R-###]: {line}",
                  file=sys.stderr)
        # Tagged comments must point at a real entry — a dangling tag is a
        # silent deferral wearing a costume.
        suffix = path.suffix if path.suffix else ".sh"
        if suffix in HASH_COMMENT_SUFFIXES | SLASH_COMMENT_SUFFIXES:
            for n, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                comment = _comment_text(line, suffix)
                for tag in _TAG_RE.findall(comment or ""):
                    if tag not in registered:
                        violations += 1
                        print(f"{path.relative_to(REPO)}:{n}: tag [R-{tag}] has no "
                              "entry in docs/RECORD.md.", file=sys.stderr)
    if violations:
        print(f"deferral_scan: {violations} violation(s) — every deferral gets "
              "a Record entry, none stay silent.", file=sys.stderr)
        return 1
    print("deferral_scan: OK — no untagged deferral language in code comments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
