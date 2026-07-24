"""Every gate that CLAIMS default-deny must state its honest limit.

Family fix for false-confidence-gate (5th instance, PR #61 r3 — and the
second time the false-confidence instance was itself a REPAIR gate: the
r2 layer-3 hardening claimed DEFAULT-DENY while implementing cue-word
allow-by-proximity). The family's shared signature across all five
instances is prose claiming more than the implementation delivers
("default-deny", "two-way", "package-wide"). Semantics cannot be
mechanically judged, but the claim/boundary DISCIPLINE can: any test
module that advertises "default-deny" must also carry an explicit
honest-limit statement, so the evaluator always receives a stated
guarantee boundary to attack instead of an implied blanket claim.

Honest limit of THIS gate, stated per its own rule: (a) it checks for
the PRESENCE of a boundary statement, not its correctness — a gate can
still state a wrong limit; (b) it scans SELF-DESCRIPTIONS only (module
docstring + comment lines), because a "default-deny" inside a string
literal describes the system under test (e.g. Postgres RLS assertion
messages), not the gate's own design — so a design claim buried in a
string literal escapes this scan. What it guarantees is exactly: no test
module ADVERTISES default-deny in its own description while offering the
evaluator no stated boundary to judge. Semantics stay with the evaluator
(adversarial-review.yml, every PR, no path filter).
"""

from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent

CLAIM = "default-deny"
BOUNDARY = "honest limit"


def _self_description(text: str) -> str:
    """Module docstring + comment lines — where a gate describes itself."""
    parts: list[str] = []
    try:
        doc = ast.get_docstring(ast.parse(text))
        if doc:
            parts.append(doc)
    except SyntaxError:
        parts.append(text)  # unparsable module: scan everything, fail open-loud
    parts.extend(
        line.strip() for line in text.splitlines() if line.lstrip().startswith("#")
    )
    return "\n".join(parts)


def modules_claiming_without_boundary(texts: dict[str, str]) -> list[str]:
    out: list[str] = []
    for name, text in sorted(texts.items()):
        desc = _self_description(text).lower()
        if CLAIM in desc and BOUNDARY not in text.lower():
            out.append(name)
    return out


def test_every_default_deny_claim_carries_an_honest_limit():
    texts = {p.name: p.read_text() for p in sorted(TESTS.glob("*.py"))}
    offenders = modules_claiming_without_boundary(texts)
    assert not offenders, (
        "test module(s) claim default-deny without a stated honest limit — "
        "the false-confidence-gate family's signature (an implied blanket "
        f"guarantee the evaluator cannot pin down): {offenders}"
    )


def test_gate_goes_red_on_the_r3_defect_shape():
    # The r2 layer-3 module shape: DEFAULT-DENY advertised, no boundary.
    text = "# DEFAULT-DENY: no verb list to evade\ndef stale(): ...\n"
    assert modules_claiming_without_boundary({"m.py": text}) == ["m.py"]


def test_gate_allows_claims_with_stated_boundary():
    text = "# DEFAULT-DENY …\n# Honest limit: deny-lists are incomplete.\n"
    assert modules_claiming_without_boundary({"m.py": text}) == []


def test_string_literal_mentions_are_out_of_scope():
    # An assertion message describing the SYSTEM's semantics (Postgres RLS
    # is default-deny by construction) is not the gate's own design claim.
    text = 'def t():\n    assert x, f"{t} must have NO policy (default-deny)"\n'
    assert modules_claiming_without_boundary({"m.py": text}) == []
