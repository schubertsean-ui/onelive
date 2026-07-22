"""Ops incident narratives may not describe themselves as verbatim copies.

Class fix for the overstated-provenance family (fifth catch, PR #49 r3):
docs/ops/INCIDENT_2026-07-22_cron-scheduler.md claimed it was an
"Extracted VERBATIM" copy of the R-008 row while the diff showed it was
assembled and edited — a false provenance claim on authored evidence.
An incident narrative in this repo is by nature an ASSEMBLED document
(status fragments accumulated and edited across a day); the only true
copy-fidelity record is git history, and prose must say so instead of
claiming a fidelity it does not have.

The gate: no docs/ops/INCIDENT_*.md file may contain a copy-fidelity
self-claim token. Scope is the incident-narrative surface deliberately:
other ops docs legitimately use "verbatim" as a DESIGN requirement about
copy strings (e.g. "trust copy verbatim" in the 2026-07-12 changelog) —
that is a claim about product copy, not about the doc's own provenance,
and banning the word repo-wide would be a false positive factory.
Legitimate need for exact history is served by citing commits.
"""

from __future__ import annotations

import re
from pathlib import Path

OPS = Path(__file__).resolve().parent.parent / "docs" / "ops"

_FORBIDDEN = re.compile(
    r"verbatim|byte-for-byte|byte-identical|copied exactly|"
    r"unchanged excerpt|exact copy",
    re.IGNORECASE,
)  # r4 nit: cover the class's equivalent phrasings, not just the r3 token


def offending_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if _FORBIDDEN.search(line)
    ]


def test_incident_docs_never_claim_verbatim_provenance():
    problems = {}
    for doc in sorted(OPS.glob("INCIDENT_*.md")):
        hits = offending_lines(doc.read_text(encoding="utf-8"))
        if hits:
            problems[doc.name] = hits
    assert problems == {}, (
        f"docs/ops incident narrative(s) carry copy-fidelity self-claims "
        f"{problems} — an assembled narrative may not claim copy fidelity "
        f"(overstated-provenance class, PR #49 r3); cite the git commits "
        f"that hold the exact history instead."
    )


def test_gate_goes_red_on_the_r3_defect_shape():
    assert offending_lines(
        "Extracted VERBATIM from docs/RECORD.md's R-008 row.\n"
        "preserves the full incident history unchanged.\n"
    ) == ["Extracted VERBATIM from docs/RECORD.md's R-008 row."]


def test_honest_assembly_provenance_is_allowed():
    assert (
        offending_lines(
            "Assembled and edited from the R-008 row's status fragments; "
            "the exact history lives in git (see commits a5424cd, b4f3898).\n"
        )
        == []
    )
