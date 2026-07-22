#!/usr/bin/env python3
"""Provenance lint: a research doc that admits its primary source went
unread may not present itself as a completed review — on ANY surface.

Structural fix for the KAIZEN repeat class `overstated-provenance`
(catches: PR #18 r1 — search-index reads presented as primary-source
pricing; PR #50 r1 ×4 — a secondary-source synthesis shipped titled and
changelogged as a completed "deep review" of a paper the sandbox's
egress policy made unreadable). The class's shape is always the same:
the body of a research artifact honestly records that the primary
source was unreachable, while its title/framing — or a bookkeeping
surface describing it — claims the stronger thing.

Mechanics (hardened at PR #50 r3, which caught the v1 of this tool as a
false-confidence gate — it scanned one of the four r1 surfaces and
accepted any R-token as "Record-bound"):

1. ARTIFACT RULE — scan docs/research/**/*.md and docs/strategy/**/*.md.
   A file whose prose declares an unread/unreachable primary source
   (subject "primary paper/source/PDF/text/material" and an
   unread/blocked negation in the same sentence) must:
   (a) self-identify in its FIRST heading with a scout/pre-review-class
       marker, AND carry no overstrong frame token there ("deep
       review", "completed review", ...) — a caveat word cannot launder
       an overstrong title (r3 nit);
   (b) cite an R-### tag that BINDS: the row must exist in
       docs/RECORD.md's table and its text must reference this doc's
       basename (r3 blocker: a bare R-token, R-999, or an unrelated row
       is not a resolution path).
2. SURFACE RULE (r3 blocker: the r1 catch had four surfaces) — every
   line in docs/ONE_LIVE_CHANGE_LOG.md, docs/RECORD.md, TODOS.md, and
   STATE.md that references an unread-primary artifact's filename must
   carry an honest-frame marker word or an R-### tag on that same line,
   so bookkeeping cannot describe a scout as a completed review while
   validate stays green.

Exit 0 clean / 1 findings (blocking in tools/validate). Widening or
relaxing these rules is a gate change: evaluator-mandatory, relaxation
founder-crucial.
"""
from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

SCAN_DIRS = ("docs/research", "docs/strategy")
SURFACE_FILES = ("docs/ONE_LIVE_CHANGE_LOG.md", "docs/RECORD.md",
                 "TODOS.md", "STATE.md")
RECORD_PATH = "docs/RECORD.md"

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
# Frame tokens too strong for an unread-primary artifact's title even
# WITH a marker word present (r3 nit: "# Provisional deep review" must
# not pass).
OVERSTRONG_TITLE = ("deep review", "completed review", "definitive",
                    "comprehensive review", "full review")
# Line-level markers that keep a bookkeeping mention honest.
LINE_MARKERS = TITLE_MARKERS + ("unread", "unfulfilled", "pre-decision",
                                "not the completed")
_RECORD_TAG_RE = re.compile(r"\bR-\d{3}\b")
_RECORD_ROW_RE = re.compile(r"^\|\s*(R-\d{3})\s*\|(.*)$")
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


def record_rows(record_text: str) -> dict[str, str]:
    """Parse docs/RECORD.md table rows into {row_id: full_row_text}."""
    rows: dict[str, str] = {}
    for line in record_text.splitlines():
        m = _RECORD_ROW_RE.match(line.strip())
        if m:
            rows[m.group(1)] = line
    return rows


def scan_doc(text: str, basename: str, record_text: str) -> list[str]:
    """ARTIFACT RULE findings for one document's text."""
    sentence = declares_unread_primary(text)
    if sentence is None:
        return []
    findings = []
    title = first_heading(text)
    title_low = title.lower()
    has_marker = any(mk in title_low for mk in TITLE_MARKERS)
    overstrong = [tok for tok in OVERSTRONG_TITLE if tok in title_low]
    if not has_marker:
        findings.append(
            f"declares an unread primary source (\"{sentence[:120]}…\") but "
            f"its first heading (\"{title[:100]}\") carries none of the "
            f"honest-frame markers {TITLE_MARKERS} — the title claims more "
            f"than the body's provenance supports"
        )
    if overstrong:
        findings.append(
            f"declares an unread primary source but its first heading "
            f"(\"{title[:100]}\") carries the overstrong frame token(s) "
            f"{overstrong} — a marker word cannot launder a "
            f"completed-review frame; retitle"
        )
    cited = set(_RECORD_TAG_RE.findall(text))
    if not cited:
        findings.append(
            "declares an unread primary source but cites no R-### Record "
            "tag — the gap must bind to a docs/RECORD.md row with an "
            "objective resolution trigger"
        )
    else:
        rows = record_rows(record_text)
        bound = [t for t in cited if t in rows and basename in rows[t]]
        if not bound:
            findings.append(
                f"declares an unread primary source and cites {sorted(cited)}, "
                f"but no cited tag resolves to a docs/RECORD.md row that "
                f"references this file ({basename}) — a bare or unrelated "
                f"R-token is not a resolution path"
            )
    return findings


def scan_surface_lines(surface_text: str, surface_name: str,
                       scout_basenames: list[str]) -> list[str]:
    """SURFACE RULE findings: mentions of scout docs must stay honest."""
    findings = []
    for lineno, line in enumerate(surface_text.splitlines(), start=1):
        low = line.lower()
        for base in scout_basenames:
            if base.lower() not in low:
                continue
            # Markers must appear OUTSIDE the filename itself — a scout
            # named *_SCOUT_v1.md would otherwise mark every mention of
            # itself and make this rule vacuous (caught red-handed by
            # this rule's own test fixture).
            stripped = low.replace(base.lower(), "")
            if any(mk in stripped for mk in LINE_MARKERS):
                continue
            if _RECORD_TAG_RE.search(line):
                continue
            findings.append(
                f"{surface_name}:{lineno} references unread-primary "
                f"artifact {base} without an honest-frame marker "
                f"{LINE_MARKERS} or R-### tag on the line — bookkeeping "
                f"may not describe a scout more strongly than its "
                f"provenance"
            )
    return findings


def main() -> int:
    record_path = REPO / RECORD_PATH
    record_text = (record_path.read_text(encoding="utf-8")
                   if record_path.exists() else "")
    findings: list[str] = []
    scout_basenames: list[str] = []
    for doc in scanned_docs():
        rel = doc.relative_to(REPO)
        text = doc.read_text(encoding="utf-8")
        doc_findings = scan_doc(text, doc.name, record_text)
        if declares_unread_primary(text) is not None:
            scout_basenames.append(doc.name)
        findings.extend(f"{rel}: {f}" for f in doc_findings)
    if scout_basenames:
        for surface in SURFACE_FILES:
            path = REPO / surface
            if not path.exists():
                continue
            findings.extend(scan_surface_lines(
                path.read_text(encoding="utf-8"), surface, scout_basenames))
    if findings:
        print("provenance_lint: FAIL — research framing ahead of its "
              "evidence (class: overstated-provenance):", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        print(f"\n{len(findings)} finding(s). Retitle/reword to the honest "
              f"frame and bind the gap to a docs/RECORD.md row that names "
              f"the artifact, in the same commit.", file=sys.stderr)
        return 1
    print(f"provenance_lint: OK — {len(scanned_docs())} research/strategy "
          f"doc(s), {len(scout_basenames)} unread-primary artifact(s), "
          f"{len(SURFACE_FILES)} bookkeeping surface(s): every declaration "
          f"is honestly framed, Record-bound, and honestly referenced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
