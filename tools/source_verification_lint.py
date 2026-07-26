#!/usr/bin/env python3
"""Source-verification lint: research may not cite what nobody can check.

Founder directive 2026-07-26 (verbatim in the decision record): "you must
commit to canon that every claim or note or finding or result must be
independently verified. You cannot be trusted to monitor yourself."

The defect this exists for is concrete and was found in our own canon: the
Construction Loop's evidence artifact
(docs/research/2026-07-25_construction_loop_research_synthesis.md) cited
Klein, NASA, DORA, Aamodt & Plaza, Reflexion and arXiv:2405.16334 while
containing ZERO resolvable URLs — bare domains and paper titles only. Every
downstream claim of "research-grounded" therefore rested on citations a
reader could not follow, and no gate noticed. Self-attestation is not
verification; a citation nobody can resolve is a claim, not evidence.

WHAT IS ENFORCED (mechanical, fail-closed):
  Every document under the scanned research/strategy trees must carry a
  `## Sources` section, and every entry in it must have BOTH
    (a) a resolvable http(s) URL, and
    (b) an explicit verification-status token from STATUS_TOKENS —
        stating whether the primary was actually READ, or NOT read and
        why (blocked, paywalled, secondary-only).
  An UNVERIFIED entry is perfectly legal — hiding that it is unverified is
  not. The point is that the reader is never left guessing which claims
  were checked against a primary and which were not.

HONEST LIMIT, stated per this repo's own rule: this gate checks that
sources are RESOLVABLE and their verification status is DECLARED. It
cannot check that a cited source says what the citing text claims, nor
that a READ token is truthful — a lying token is a lie a human or the
independent evaluator must catch. What it removes is the ability to ship
unfollowable citations silently, which is exactly what happened here.

Exit codes (tools/README.md convention): 0 = clean, 1 = findings.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# ENFORCED SET — documents whose citations are load-bearing for canon and
# must therefore be followable TODAY. Scoped, not weakened: before this gate
# existed, NOTHING was enforced anywhere. The rest of docs/research/ carries
# the same defect (verified: every file fails this check) and is recorded as
# an OPEN Record row with an objective trigger — each doc gains its Sources
# block when it is next touched, and this list widens to the whole tree when
# that row closes. Adding a path here can only add findings.
ENFORCED_DOCS = (
    "docs/research/2026-07-25_construction_loop_research_synthesis.md",
)

SOURCES_HEADING = re.compile(r"^#{1,4}\s+Sources\b", re.IGNORECASE | re.MULTILINE)
URL_RE = re.compile(r"https?://[^\s)\]>]+")
BULLET_RE = re.compile(r"^\s*[-*]\s+\S")

# A status token must appear on the entry line. READ means a human or agent
# actually retrieved the primary; every other token is an honest admission.
STATUS_TOKENS = (
    "VERIFIED-READ",        # primary retrieved and read
    "VERIFIED-ABSTRACT",    # abstract/landing page read, full text not
    "UNVERIFIED-BLOCKED",   # fetch refused (proxy/paywall/login)
    "UNVERIFIED-SECONDARY", # only secondary coverage seen
    "UNVERIFIED-PENDING",   # queued for verification, trigger recorded
)


def scan_text(rel_path: str, text: str) -> list[str]:
    """Findings for one document. Pure function — unit-testable."""
    findings: list[str] = []
    m = SOURCES_HEADING.search(text)
    if not m:
        return [
            f"{rel_path}: no `## Sources` section — every research document "
            "must expose the sources its claims rest on, each with a URL and "
            "a verification-status token"
        ]

    section = text[m.end():]
    # The section ends at the next heading of the same-or-higher level.
    nxt = re.search(r"^#{1,4}\s+\S", section, re.MULTILINE)
    if nxt:
        section = section[: nxt.start()]

    # An entry is a bullet line PLUS its wrapped continuation lines — real
    # markdown citations span several lines, and a line-only parser would
    # demand the URL and status token share one physical line.
    entries: list[str] = []
    for ln in section.splitlines():
        if BULLET_RE.match(ln):
            entries.append(ln)
        elif entries and ln.strip():
            entries[-1] += " " + ln.strip()
    if not entries:
        findings.append(
            f"{rel_path}: `## Sources` section has no entries — an empty "
            "sources block is a gate that cannot fail"
        )
        return findings

    for line in entries:
        stripped = line.strip()
        label = (stripped[:70] + "…") if len(stripped) > 70 else stripped
        if not URL_RE.search(line):
            findings.append(
                f"{rel_path}: source entry has no resolvable URL — a citation "
                f"a reader cannot follow is a claim, not evidence: {label}"
            )
        if not any(tok in line for tok in STATUS_TOKENS):
            findings.append(
                f"{rel_path}: source entry declares no verification status "
                f"(one of {', '.join(STATUS_TOKENS)}) — unverified is allowed, "
                f"silently unverified is not: {label}"
            )
    return findings


def scan_repo(root: pathlib.Path = REPO) -> list[str]:
    findings: list[str] = []
    scanned = 0
    for rel in ENFORCED_DOCS:
        path = root / rel
        if not path.is_file():
            # An enforced doc that vanished is a finding, never a free pass.
            findings.append(
                f"{rel}: listed in ENFORCED_DOCS but missing from the tree — "
                "fix the path or remove it deliberately; a silently absent "
                "enforced document is an unnoticed hole"
            )
            continue
        scanned += 1
        findings.extend(scan_text(rel, path.read_text(encoding="utf-8")))
    if scanned == 0:
        # A scan that examined nothing must never report "clean" (kernel I2).
        findings.append(
            "source_verification_lint: scanned ZERO documents — ENFORCED_DOCS "
            "matched nothing; failing closed rather than reporting a clean tree"
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args(argv)
    findings = scan_repo()
    for f in findings:
        print(f"FINDING: {f}")
    if findings:
        print(f"source_verification_lint: {len(findings)} finding(s) — "
              "unfollowable or status-less citations fail closed here.",
              file=sys.stderr)
        return 1
    print("source_verification_lint: clean — every research source is "
          "resolvable and declares whether its primary was actually read.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
