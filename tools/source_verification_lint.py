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

WHAT IS ENFORCED (mechanical, fail-closed), stated at its true width:
  (1) SCOPE CHECK — every document under docs/research/ that THIS CHANGE
      touches must be listed in ENFORCED_DOCS. This is the mechanism
      behind R-054's "each doc gains its Sources block when next edited":
      without it that trigger was prose, and the PR #78 evaluator was
      right to call an unbacked trigger a false-confidence gate.
  (2) CONTENT CHECK — each ENFORCED_DOCS document carries a `## Sources`
      section whose every entry has BOTH
        (a) an http(s) URL, and
        (b) an explicit verification-status token from STATUS_TOKENS,
            matched at token boundaries — stating whether the primary was
            actually READ, or NOT read and why.
  An UNVERIFIED entry is perfectly legal — hiding that it is unverified is
  not. The reader is never left guessing which claims were checked against
  a primary and which were not.

HONEST LIMITS, enumerated because this repo's own rule requires a control
to claim only what it does (PR #78 evaluator, class false-confidence-gate):
  - It does NOT resolve URLs. It checks that an http(s) URL is PRESENT and
    well-formed. A dead or invented link satisfies it. "Followable" here
    means "a reader has something to click", not "the target exists".
  - It does NOT check that a source says what the citing text claims.
  - It cannot detect a LYING `VERIFIED-READ` token.
  - Documents outside docs/research/ are not scanned at all.
Those remain human and independent-evaluator catches. What this removes is
the ability to ship an unfollowable citation SILENTLY, and the ability to
edit a research document without bringing it under the gate.

Exit codes (tools/README.md convention): 0 = clean, 1 = findings.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# ENFORCED SET — documents whose citations are load-bearing for canon and
# must therefore be followable TODAY. Scoped, not weakened: before this gate
# existed, NOTHING was enforced anywhere. The rest of docs/research/ carries
# the same defect (verified: every file fails this check) and is recorded as
# an OPEN Record row (R-054). Its trigger is now MECHANICAL, not a promise:
# scan_scope() fails the gate when this change edits any docs/research/*.md
# absent from this tuple, so a document cannot be touched without joining the
# gate in the same commit. The tuple widens by that route, one document per
# edit, until it covers the tree. Adding a path here can only add findings.
ENFORCED_DOCS = (
    "docs/research/2026-07-25_construction_loop_research_synthesis.md",
)

SOURCES_HEADING = re.compile(r"^(#{1,4})\s+Sources\b", re.IGNORECASE | re.MULTILINE)
URL_RE = re.compile(r"https?://[^\s)\]>]+")
# Bullets AND numbered citations. `1.` / `2)` are standard markdown list
# syntax; excluding them made a numbered Sources block either report "no
# entries" or silently glue every numbered line onto the preceding bullet,
# masking the missing URL and token on all of them (PR #78, gemini
# dataflow-taint seat).
BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+\S")

# A status token must appear on the entry line. READ means a human or agent
# actually retrieved the primary; every other token is an honest admission.
STATUS_TOKENS = (
    "VERIFIED-READ",        # primary retrieved and read
    "VERIFIED-ABSTRACT",    # abstract/landing page read, full text not
    "UNVERIFIED-BLOCKED",   # fetch refused (proxy/paywall/login)
    "UNVERIFIED-SECONDARY", # only secondary coverage seen
    "UNVERIFIED-PENDING",   # queued for verification, trigger recorded
)

# Matched at TOKEN BOUNDARIES, never as a substring. Both OpenAI seats
# blocked PR #78 on this and were right: a plain `tok in line` accepted
# `NOT-VERIFIED-READ`, `XVERIFIED-READ` and `UNVERIFIED-BLOCKEDNESS` —
# text that contains a token while declaring something else, or the
# opposite. A gate that can be satisfied by a near-miss is a gate that
# cannot fail, which is the class it exists to prevent.
# The longest tokens are tried first so `VERIFIED-READ` cannot shadow a
# longer neighbour, and `\B-` guards the hyphen-prefixed negations that a
# bare \b would let through.
_STATUS_RE = re.compile(
    r"(?<![A-Za-z0-9])(?<!-)(?:" +
    "|".join(sorted((re.escape(t) for t in STATUS_TOKENS), key=len, reverse=True)) +
    r")(?![A-Za-z0-9-])"
)
# An explicit negation immediately before a well-formed token is a
# DECLARATION OF THE OPPOSITE, not a status. "not VERIFIED-READ" must not
# satisfy the requirement to declare one.
# Anchored at the END of the text preceding the token — the negation must
# immediately govern it. (First cut used a lookahead for the token's first
# capital, which never fired because the preceding slice stops exactly
# there; caught by probing the bypass rather than by reading the regex.)
_NEGATED_STATUS_RE = re.compile(
    r"\b(?:not|never|isn'?t|no)\s+(?:yet\s+)?$", re.IGNORECASE)


def declares_status(line: str) -> bool:
    """True when the line carries a real, unnegated status token."""
    m = _STATUS_RE.search(line)
    if not m:
        return False
    before = line[max(0, m.start() - 24):m.start()]
    return not _NEGATED_STATUS_RE.search(before)


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
    # The section ends at the next heading of the SAME-OR-HIGHER level —
    # computed from the matched heading, not hard-coded. The first cut
    # truncated at any `#`..`####`, so a `## Sources` block organised with
    # `### Primary` / `### Secondary` subheadings lost every citation under
    # them and reported "no entries" — a gate silently examining nothing
    # (PR #78, gemini dataflow-taint seat; the comment claimed the correct
    # behaviour while the regex did something else).
    level = len(m.group(1))
    nxt = re.search(r"^#{1,%d}\s+\S" % level, section, re.MULTILINE)
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
        if not declares_status(line):
            findings.append(
                f"{rel_path}: source entry declares no verification status "
                f"(one of {', '.join(STATUS_TOKENS)}) — unverified is allowed, "
                f"silently unverified is not: {label}"
            )
    return findings


def _git(args: list[str], root: pathlib.Path) -> str | None:
    """Git output, or None when git cannot answer. Never a silent empty
    string: 'no changes' and 'git failed' must not look identical (§1)."""
    try:
        out = subprocess.run(["git", *args], cwd=root, capture_output=True,
                             text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def touched_research_docs(root: pathlib.Path, diff_range: str) -> list[str] | None:
    """Research documents this change touches. None = git could not answer."""
    out = _git(["diff", "--name-only", diff_range], root)
    if out is None:
        return None
    return sorted(
        p for p in (l.strip() for l in out.splitlines())
        if p.startswith("docs/research/") and p.endswith(".md")
    )


def scan_scope(root: pathlib.Path = REPO, diff_range: str = "origin/master...HEAD",
               ) -> list[str]:
    """R-054's trigger, as a MECHANISM rather than a promise.

    The row says each research document gains its Sources block "the next
    time it is edited". Both OpenAI seats blocked PR #78 because nothing
    enforced that — an unbacked trigger is a recorded remediation that can
    silently never happen. So: touch a research document, and it must join
    ENFORCED_DOCS in the same change.

    A git failure is reported, never treated as "nothing changed" — the
    project's founding anti-pattern is a failure that looks like an
    absence. A clean checkout with no diff legitimately yields no findings.
    """
    touched = touched_research_docs(root, diff_range)
    if touched is None:
        return [
            "scope check could not read the diff (git unavailable or the "
            f"range {diff_range!r} does not resolve) — reporting this rather "
            "than treating an unanswerable question as 'nothing changed'"
        ]
    enforced = set(ENFORCED_DOCS)
    return [
        f"{rel}: this change edits a research document that is NOT in "
        "ENFORCED_DOCS — R-054's trigger is that a touched document joins "
        "the gate in the same commit. Add a `## Sources` block (or, for a "
        "verbatim source capture, a provenance line) and append the path to "
        "ENFORCED_DOCS in tools/source_verification_lint.py"
        for rel in touched if rel not in enforced
    ]


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
    ap.add_argument(
        "--diff-range", default="origin/master...HEAD",
        help="range whose touched research documents must be under the gate "
             "(R-054's trigger, mechanised)")
    args = ap.parse_args(argv)
    findings = scan_repo() + scan_scope(REPO, args.diff_range)
    for f in findings:
        print(f"FINDING: {f}")
    if findings:
        print(f"source_verification_lint: {len(findings)} finding(s) — "
              "citations without a URL or a declared status, and research "
              "documents edited without joining the gate, fail closed here.",
              file=sys.stderr)
        return 1
    print("source_verification_lint: clean — every enforced document's "
          "sources carry an http(s) URL and an explicit verification-status "
          "token, and this change edits no unenforced research document. "
          "(URLs are checked for PRESENCE and form, never resolved; a token "
          "is checked for being declared, never for being truthful.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
