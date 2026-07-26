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


# ── The OTHER half of false-confidence-gate ──────────────────────────────
#
# scan_text above catches a claim whose cited artifact is ABSENT. The class's
# other half — the artifact EXISTS but does LESS than the sentence claims —
# escaped it 8 times in PR #75 alone, past this file's own structural-fix
# marker, and false-confidence-gate is the top class in the Kaizen ledger at
# 29. Root cause: existence is checkable, semantics are not.
#
# What IS mechanically checkable is the shape every one of those escapes took:
# an UNCONDITIONAL security assertion. "An attacker would have to forge
# sha256" (they could poison PATH instead). "Now genuinely base-owned"
# (execution was, command resolution was not). A security property stated
# with no scope is the tell, because real controls close a specific half of a
# specific threat.
#
# So: an absolute claim must carry its scope IN THE SAME SENTENCE. This does
# not verify the claim — nothing here can — it forbids stating one as though
# it were total. Deliberately narrow, seeded from the phrasings that actually
# escaped rather than from imagination; over-broad prose lints produce filler,
# which is how a gate stops meaning anything.
ABSOLUTE_CLAIM_RE = re.compile(
    r"attacker would (?:have to|need to)"
    # "can NEVER be bypassed" slipped past the first form entirely — the
    # negation can be carried by the adverb instead of the modal (PR #75 r11,
    # found by writing the red case rather than by reading the regex).
    r"|\b(?:cannot|can't|could not|can never|will never|is never|are never)\s+be\s+"
    r"(?:bypassed|forged|subverted|circumvented)"
    r"|\bimpossible to\b"
    r"|\bgenuinely (?:base-owned|trusted|secure|isolated|closed)\b"
    r"|\bno longer possible\b"
    r"|\b(?:fully|completely|entirely) (?:closed|fixed|mitigated|secure)\b"
    r"|\bguarantees that\b"
    # ── Added PR #75 r10, after the class RECURRED 9x past the marker above.
    # Root cause of THAT escape: the first pattern set was seeded from r6's
    # phrasings, and r9 asserted the same kind of totality in words it did not
    # cover — "no PR input", "NO PR-CONTROLLED CODE EXECUTES IN THIS JOB",
    # a job "free of" an input. Same shape, different vocabulary. Seeded again
    # from what actually escaped; this list is explicitly NOT exhaustive, and
    # the structural half of the fix is that claims of this kind now carry
    # tests that fail when they stop being true.
    r"|\bno PR input\b"
    r"|\bno PR-controlled code\b"
    r"|\bfree of PR\b"
    r"|\buntouched by (?:anything |any )?(?:the )?PR\b",
    re.IGNORECASE,
)
# Words that turn a total claim into a bounded one, or mark the sentence as
# quoted history rather than a live assertion.
# A scope marker must BOUND the claim — name what the control does not cover,
# or what it depends on. `still` and `never` were in this list and bound
# nothing: "the gate still cannot be bypassed" and "can never be bypassed" are
# STRONGER assertions, not scoped ones, so an author could satisfy a gate
# against unconditional claims by adding an adverb (PR #75 r11, absence-only
# seat — the gate was bypassable by exactly the move it exists to stop).
# Removed. `superseded` and `false` stay: they mark a sentence as QUOTED
# history rather than a live assertion, which is a different, legitimate case.
SCOPE_MARKERS = (
    "only", "not sufficient", "says nothing", "half", "scope", "alone",
    "except", "assuming", "limit", "superseded", "false", "does not",
    "cannot check", "not exhaustive", "depends on",
)


def claim_docs() -> list[pathlib.Path]:
    """Wider than governed_docs(): the escapes were in workflow comments, the
    session contract and the TODO list, not in CLAUDE.md."""
    docs = governed_docs() + [REPO / "STATE.md", REPO / "TODOS.md"]
    for wf_dir in REPO.glob("**/.github/workflows"):
        if ".git/" in str(wf_dir):
            continue
        docs.extend(sorted(wf_dir.glob("*.yml")))
    return [d for d in docs if d.exists()]


def scan_absolute_claims(text: str) -> list[str]:
    """Findings: unconditional security claims with no scope in-sentence."""
    findings = []
    for sentence in _SENTENCE_SPLIT.split(text):
        m = ABSOLUTE_CLAIM_RE.search(sentence)
        if not m:
            continue
        if any(s in sentence.lower() for s in SCOPE_MARKERS):
            continue
        findings.append(
            f"states the security claim {m.group(0)!r} with no scope in the "
            f"same sentence — a control closes a specific half of a specific "
            f"threat; an unconditional claim is how false-confidence-gate "
            f"recurs (name what it does NOT cover): "
            f"\"{sentence.strip()[:160]}…\""
        )
    return findings


def main() -> int:
    findings = []
    for doc in governed_docs():
        rel = doc.relative_to(REPO)
        for f in scan_text(doc.read_text(encoding="utf-8")):
            findings.append(f"{rel}: {f}")
    scanned_for_claims = claim_docs()
    for doc in scanned_for_claims:
        rel = doc.relative_to(REPO)
        for f in scan_absolute_claims(doc.read_text(encoding="utf-8")):
            findings.append(f"{rel}: {f}")
    if not scanned_for_claims:
        # A scan that examined nothing must never read as clean.
        findings.append(
            "absolute-claim scan matched ZERO documents — failing closed "
            "rather than reporting a clean tree")
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
          f"doc(s): every cited mechanism exists or is explicitly staged; "
          f"{len(scanned_for_claims)} doc(s) carry no unscoped security claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
