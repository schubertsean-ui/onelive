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

# Any level-1..4 `Sources` heading is accepted DELIBERATELY (PR #78 r3 nit):
# the rule text says `## Sources` as the convention, and rejecting a document
# that used `### Sources` would fail it for formatting rather than for an
# unfollowable citation — which is not what this gate is for. The matched
# level is what bounds the section, so nesting still works correctly.
SOURCES_HEADING = re.compile(r"^(#{1,4})\s+Sources\b", re.IGNORECASE | re.MULTILINE)
URL_RE = re.compile(r"https?://[^\s)\]>]+")
# Bullets AND numbered citations. `1.` / `2)` are standard markdown list
# syntax; excluding them made a numbered Sources block either report "no
# entries" or silently glue every numbered line onto the preceding bullet,
# masking the missing URL and token on all of them (PR #78, gemini
# dataflow-taint seat).
# At most 3 leading spaces — CommonMark's threshold between a list item and an
# indented code block. Arbitrary `\s*` counted a four-space-indented bullet as
# a citation entry even though it renders as code (PR #78 r7).
BULLET_RE = re.compile(r"^ {0,3}(?:[-*]|\d+[.)])\s+\S")

# A VERBATIM SOURCE CAPTURE (docs/research/sources/*) is not a synthesis: it
# has no citations of its own, it IS the cited thing. R-054 and this tool's
# own finding text both offered such a file "a provenance line, not a Sources
# block" — and no code accepted one, so the documented remediation was a dead
# end that could never be satisfied (PR #78 r3, class
# unimplemented-remediation-path, found by the absence-only seat). It is a
# real branch now: one line declaring where the captured text came from and
# whether the primary was actually read, held to the SAME two requirements as
# a citation — a URL and a boundary-matched status token.
# CAPTURE-ONLY, enforced by PATH (PR #78 r4, class provenance-escape-hatch).
# The first cut accepted a PROVENANCE line from ANY document lacking a Sources
# block, which meant an enforced SYNTHESIS could delete its citations, add one
# line, and pass — the escape hatch emptying the gate it was added to complete.
# Only files under these prefixes may use it, because only they are verbatim
# captures of someone else's text rather than arguments built on sources.
CAPTURE_PATH_PREFIXES = ("docs/research/sources/",)

# NOT accepted inside an HTML comment. A `<!-- PROVENANCE: ... -->` line is
# invisible in rendered markdown, which defeats "cite it where the claim
# lives" — the reader must see the origin, not find it in the source.
PROVENANCE_RE = re.compile(r"^\s*PROVENANCE:\s*(?P<body>.+?)\s*$",
                           re.IGNORECASE | re.MULTILINE)


# INVISIBLE REGIONS, removed before anything is parsed (PR #78 r5, class
# invisible-citation-bypass). r4 rejected a `PROVENANCE:` line hidden in an
# HTML comment but left every sibling path open: an entire `## Sources` block,
# a citation bullet under a visible heading, a URL, or a status token could all
# sit inside `<!-- ... -->` or a fenced code block and satisfy the gate while
# rendering to nothing. The rule being mechanised is "cite it where the claim
# lives" — evidence a reader cannot see is not a citation, and one-off fixes
# per syntax is how the first four rounds went. Strip once, at the top, so
# every downstream check inherits the property.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# CommonMark fences: opened by 3+ backticks or tildes indented at most 3
# spaces, closed by a fence of the SAME character and AT LEAST the same
# length. A regex backreference demands an exact-length match (PR #78 r7), so
# ```` ... ``` and ``` ... ```` were both mis-handled. Line-based, because the
# rule is about line prefixes and lengths, not about a pattern.
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
# A line indented 4+ spaces is an INDENTED CODE BLOCK — rendered as code, so a
# four-space-indented `- https://… VERIFIED-READ` under a Sources heading looks
# like a citation to the parser and like code to the reader (r7 finding).
_INDENTED_CODE_RE = re.compile(r"^(?: {4}|\t)")


def visible_text(text: str) -> str:
    """What a reader of the RENDERED document actually sees.

    Removes HTML comments, fenced code blocks and indented code blocks. Doing
    this ONCE, before any parsing, is what stops the invisible-citation class
    reopening per syntax — the failure mode of r4 and r5, which each closed one
    hiding place and left its siblings.
    """
    text = _HTML_COMMENT_RE.sub(" ", text)
    out, fence = [], None
    for line in text.splitlines():
        if fence is not None:
            m = _FENCE_OPEN_RE.match(line)
            # Closing fence: same character, at least as long, nothing after it.
            if (m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence)
                    and not line[m.end():].strip()):
                fence = None
            continue                      # everything inside a fence is code
        m = _FENCE_OPEN_RE.match(line)
        if m:
            fence = m.group(1)
            continue
        if _INDENTED_CODE_RE.match(line):
            continue                      # indented code block
        out.append(line)
    return "\n".join(out)


def is_capture_path(rel_path: str) -> bool:
    return rel_path.replace("\\", "/").startswith(CAPTURE_PATH_PREFIXES)

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
# An explicit negation GOVERNING a token declares the opposite, not a status.
# Scoped by SENTENCE, not by adjacency (PR #78 r6, class
# negated-status-bypass). The first cut required the negation to sit
# immediately before the token, so "not actually VERIFIED-READ", "not really
# VERIFIED-READ" and "not currently VERIFIED-READ" all passed while saying the
# opposite of what they claimed. Enumerating the adverbs would be the
# one-instance-instead-of-the-category mistake this arc keeps making, so the
# rule is positional: look back to the last sentence boundary and reject if any
# negation word governs the token from there. A token after a `;` or `.` starts
# a fresh clause and is judged on its own — which keeps
# "not VERIFIED-READ; UNVERIFIED-SECONDARY" correctly accepted.
_NEGATION_WORD_RE = re.compile(r"\b(?:not|never|isn'?t|aren'?t|no|without|"
                               r"neither|nor|cannot|can'?t)\b", re.IGNORECASE)
# Parentheses close a clause too (gemini r7 nit): "Smith 2020 (no abstract)
# https://e.org VERIFIED-READ" is an honest entry, and reading the parenthetical
# "no" as governing the token three words later would reject it.
_CLAUSE_BREAK_RE = re.compile(r"[.;:!?()]")


def _is_negated(text_before: str) -> bool:
    """True when a negation governs the token that follows text_before."""
    breaks = list(_CLAUSE_BREAK_RE.finditer(text_before))
    clause = text_before[breaks[-1].end():] if breaks else text_before
    return bool(_NEGATION_WORD_RE.search(clause))


def status_field(line: str) -> str:
    """The part of an entry a status token may legitimately be declared in.

    URLs and markdown link TEXT are stripped first (PR #78 r3, class
    status-token-not-field): before this, `https://example.org/VERIFIED-READ`
    or a paper title containing the token satisfied the gate while declaring
    no status at all — the token has to be the author's own assertion, not a
    substring of something they are citing.
    """
    without_links = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", line)   # [text](url)
    return URL_RE.sub(" ", without_links)                        # bare urls


def declares_status(line: str) -> bool:
    """True when the entry declares a real, unnegated status token.

    EVERY match is considered, not just the first (gemini dataflow-taint seat):
    an entry like `... not VERIFIED-READ; UNVERIFIED-SECONDARY` declares an
    honest status after mentioning a negated one, and checking only the first
    match rejected it.
    """
    field = status_field(line)
    for m in _STATUS_RE.finditer(field):
        if not _is_negated(field[:m.start()]):
            return True
    return False


def _scan_provenance(rel_path: str, body: str) -> list[str]:
    """A source capture's one-line origin declaration, same bar as a citation."""
    findings = []
    if not URL_RE.search(body):
        findings.append(
            f"{rel_path}: `PROVENANCE:` line has no http(s) URL — a captured "
            f"document whose origin cannot be followed is exactly the defect "
            f"this gate exists for: {body[:80]}")
    if not declares_status(body):
        findings.append(
            f"{rel_path}: `PROVENANCE:` line declares no verification status "
            f"(one of {', '.join(STATUS_TOKENS)}) — say whether the primary "
            f"behind this capture was actually read: {body[:80]}")
    return findings


def scan_text(rel_path: str, text: str) -> list[str]:
    """Findings for one document. Pure function — unit-testable."""
    findings: list[str] = []
    text = visible_text(text)   # hidden evidence is not evidence
    m = SOURCES_HEADING.search(text)
    if not m:
        prov = PROVENANCE_RE.search(text)
        if prov and is_capture_path(rel_path):
            return _scan_provenance(rel_path, prov.group("body"))
        if prov:
            return [
                f"{rel_path}: uses a `PROVENANCE:` line, but that alternative is "
                f"only for verbatim source captures under "
                f"{', '.join(CAPTURE_PATH_PREFIXES)} — a synthesis argues FROM "
                f"sources and must expose them in a `## Sources` block. Accepting "
                f"provenance here would let any document drop its citations and "
                f"pass with one line"
            ]
        return [
            f"{rel_path}: no `## Sources` section and no `PROVENANCE:` line — a "
            "synthesis must expose the sources its claims rest on (each with a "
            "URL and a verification-status token); a verbatim source capture "
            "must instead declare ONE `PROVENANCE: <url> <STATUS-TOKEN>` line "
            "saying where the captured text came from and whether the primary "
            "was actually read"
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
    # An entry is a bullet PLUS its INDENTED continuation lines, and it CLOSES
    # at a blank line, a heading, or an unindented line (PR #78 r4, class
    # unbounded-continuation-bypass). Appending any following non-empty line
    # let a free-standing paragraph — or a paragraph after a divider — supply
    # the URL and status for a defective bullet above it, so "every entry
    # carries its own URL and status" was not actually enforced.
    entries: list[str] = []
    open_entry = False
    for ln in section.splitlines():
        if BULLET_RE.match(ln):
            entries.append(ln)
            open_entry = True
        elif not ln.strip():
            open_entry = False          # a blank line ends the entry
        elif ln.strip().startswith("#"):
            open_entry = False          # a heading is a divider, never text
        elif open_entry and ln[:1].isspace():
            entries[-1] += " " + ln.strip()
        else:
            open_entry = False          # unindented prose is not continuation
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
                f"{rel_path}: source entry has no http(s) URL — a citation "
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
    # --diff-filter=d EXCLUDES deletions. Without it, deleting an unenforced
    # research document flagged the deleted path, and adding that path to
    # ENFORCED_DOCS to satisfy this check made scan_repo fail on the missing
    # file — an unresolvable deadlock (gemini dataflow-taint seat).
    out = _git(["diff", "--name-only", "--diff-filter=d", diff_range], root)
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
        "the gate in the same commit. Add a `## Sources` block — or, for a "
        "verbatim source capture, a single `PROVENANCE: <url> <STATUS-TOKEN>` "
        "line, which this tool accepts in its place — and append the path to "
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
    total = len(list((REPO / "docs" / "research").rglob("*.md")))
    print(f"source_verification_lint: clean — {len(ENFORCED_DOCS)} of {total} "
          f"docs/research documents are CONTENT-enforced (the remainder is "
          f"R-054; the scope check covers the whole tree). Their sources carry "
          f"an http(s) URL and an explicit verification-status token, and this "
          f"change edits no unenforced research document. URLs are checked for "
          f"PRESENCE and form, never resolved; a token is checked for being "
          f"declared, never for being truthful.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
