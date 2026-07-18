#!/usr/bin/env python3
"""Governance-claims lint: prose may not claim a mechanism the tree lacks.

Structural fix for the KAIZEN repeat class `prose-classified-bypass`
(three catches: PR #36 r1 — the charter exception had no mechanical
classifier or compensating control; PR #36 r4 ×2 — the charter and the
merge decision note described the stage-3 re-lock and certification
record as live while stage 1 shipped neither). The class's shape is
always the same: a governance document cites a concrete artifact as its
compensating mechanism, and the artifact is not in the tree.

Mechanics: scan CLAUDE.md and docs/memory/decisions/*.md for
repo-path references (extensioned files under tools/ ai/ docs/ tests/
worker/ api/ web/ design/ or .github/workflows/). A referenced path that
does not exist in the tree must sit in a sentence carrying an explicit
staging/negation marker (stage, until, lands, arrives, pending, future,
not covered, withdrawn, superseded, historical) — text that says a
mechanism is coming is honest; text that presents an absent mechanism as
live is exactly the bypass. Exit 0 clean / 1 findings (blocking in
tools/validate).
"""
from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

PATH_RE = re.compile(
    r"(?:\.github/workflows/|(?:tools|ai|docs|tests|worker|api|web|design)/)"
    r"[A-Za-z0-9_.\-/]*\.(?:py|yml|yaml|json|jsonl|md|sql|sh|txt)"
)
# Markers that legitimately accompany a mention of a not-yet/no-longer
# present artifact. Deliberately narrow: only words that state the
# artifact is staged, conditional, or historical.
MARKERS = ("stage", "until", "lands", "arrives", "pending", "future",
           "not covered", "withdrawn", "superseded", "historical")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def governed_docs() -> list[pathlib.Path]:
    docs = [REPO / "CLAUDE.md"]
    decisions = REPO / "docs" / "memory" / "decisions"
    if decisions.is_dir():
        docs.extend(sorted(decisions.glob("*.md")))
    return [d for d in docs if d.exists()]


def scan_text(text: str, repo: pathlib.Path = REPO) -> list[str]:
    """Return findings: absent-path references without a staging marker."""
    findings = []
    for sentence in _SENTENCE_SPLIT.split(text):
        low = sentence.lower()
        marked = any(m in low for m in MARKERS)
        for m in PATH_RE.finditer(sentence):
            rel = m.group(0)
            if (repo / rel).exists():
                continue
            if marked:
                continue
            findings.append(
                f"claims '{rel}' which does not exist in the tree, in a "
                f"sentence with no staging/negation marker "
                f"({', '.join(MARKERS)}) — an absent mechanism presented "
                f"as live: \"{sentence.strip()[:160]}…\""
            )
    return findings


def main() -> int:
    findings = []
    for doc in governed_docs():
        rel = doc.relative_to(REPO)
        for f in scan_text(doc.read_text(encoding="utf-8")):
            findings.append(f"{rel}: {f}")
    if findings:
        print("governance_claims_lint: FAIL — governance prose ahead of "
              "the mechanism (class: prose-classified-bypass):",
              file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        print(f"\n{len(findings)} finding(s). Ship the mechanism in the "
              f"same change, or mark the claim as staged in the same "
              f"sentence.", file=sys.stderr)
        return 1
    print(f"governance_claims_lint: OK — {len(governed_docs())} governance "
          f"doc(s): every cited mechanism exists or is explicitly staged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
