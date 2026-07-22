#!/usr/bin/env python3
"""Provenance lint: a research doc that admits its primary source went
unread may not present itself as a completed review.

Structural fix for the KAIZEN repeat class `overstated-provenance`
(catches: PR #18 r1 — search-index reads presented as primary-source
pricing; PR #50 r1 ×4 — a secondary-source synthesis shipped titled and
changelogged as a completed "deep review" of a paper the sandbox's
egress policy made unreadable). The class's shape is always the same:
the body of a research artifact honestly records that the primary
source was unreachable, while its title/framing claims the stronger
thing — readers meet the frame before the caveat.

Mechanics: scan docs/research/**/*.md and docs/strategy/**/*.md. A file
whose prose declares an unread/unreachable primary source (subject
"primary paper/source/PDF/text/material" and an unread/blocked negation
in the same sentence) must (a) self-identify in its FIRST heading with
a scout/pre-review-class marker, so the honest frame is the title, and
(b) carry a live [R-###]-style Record tag binding the gap to its
resolution trigger. Exit 0 clean / 1 findings (blocking in
tools/validate). Widening beyond these two requirements (or relaxing
them) is a gate change: evaluator-mandatory, relaxation founder-crucial.
"""
from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

SCAN_DIRS = ("docs/research", "docs/strategy")

_SUBJECT_RE = re.compile(
    r"primary\s+(?:paper|source|sources|pdf|text|material)s?", re.IGNORECASE
)
_NEGATION_RE = re.compile(
    r"never\s+read|not\s+read(?:able)?|unread|could(?:\s+not|n't)\s+be\s+read"
    r"|unreachable|egress[- ]?(?:block|polic)|was\s+not\s+available"
    r"|never\s+retriev|could\s+not\s+be\s+fetch",
    re.IGNORECASE,
)
# Markers that make the honest frame the TITLE, not a buried caveat.
TITLE_MARKERS = ("scout", "pre-review", "preliminary", "provisional",
                 "secondary-source", "incomplete")
_RECORD_TAG_RE = re.compile(r"\bR-\d{3}\b")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def scanned_docs() -> list[pathlib.Path]:
    docs: list[pathlib.Path] = []
    for d in SCAN_DIRS:
        root = REPO / d
        if root.is_dir():
            docs.extend(sorted(root.rglob("*.md")))
    return docs


def declares_unread_primary(text: str) -> str | None:
    """Return the declaring sentence if the doc records an unread primary."""
    for sentence in _SENTENCE_SPLIT.split(text):
        if _SUBJECT_RE.search(sentence) and _NEGATION_RE.search(sentence):
            return sentence.strip()
    return None


def first_heading(text: str) -> str:
    m = _HEADING_RE.search(text)
    return m.group(1) if m else ""


def scan_text(text: str) -> list[str]:
    """Return findings for one document's text."""
    sentence = declares_unread_primary(text)
    if sentence is None:
        return []
    findings = []
    title = first_heading(text)
    if not any(mk in title.lower() for mk in TITLE_MARKERS):
        findings.append(
            f"declares an unread primary source (\"{sentence[:120]}…\") but "
            f"its first heading (\"{title[:100]}\") carries none of the "
            f"honest-frame markers {TITLE_MARKERS} — the title claims more "
            f"than the body's provenance supports"
        )
    if not _RECORD_TAG_RE.search(text):
        findings.append(
            "declares an unread primary source but cites no R-### Record "
            "tag — the gap must bind to a live docs/RECORD.md row with an "
            "objective resolution trigger"
        )
    return findings


def main() -> int:
    findings = []
    for doc in scanned_docs():
        rel = doc.relative_to(REPO)
        for f in scan_text(doc.read_text(encoding="utf-8")):
            findings.append(f"{rel}: {f}")
    if findings:
        print("provenance_lint: FAIL — research framing ahead of its "
              "evidence (class: overstated-provenance):", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        print(f"\n{len(findings)} finding(s). Retitle the doc as a "
              f"scout/pre-review (honest frame in the first heading) and "
              f"bind the gap to a Record row in the same commit.",
              file=sys.stderr)
        return 1
    print(f"provenance_lint: OK — {len(scanned_docs())} research/strategy "
          f"doc(s): every unread-primary declaration is honestly framed "
          f"and Record-bound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
