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

r4 rebuild (the evaluator caught the first version being asymmetric —
claims scanned self-descriptions while the boundary was satisfiable by
any string literal, and the scan missed nested test modules): BOTH the
claim and the boundary are now searched in the SELF-DESCRIPTION ONLY
(module docstring + comment lines), and the scan recurses the whole
tests/ tree.

Honest limit of THIS gate, stated per its own rule: (a) it checks for
the PRESENCE of a boundary statement, not its correctness — a gate can
still state a wrong limit; (b) self-description means docstring +
comment lines, so both a design claim AND a boundary buried in string
literals are invisible to it (symmetric by construction — the r4 fix);
(c) it covers tests/ recursively, not other trees. What it guarantees
is exactly: no test module ADVERTISES default-deny in its own
description without a boundary statement in that same description.
Semantics stay with the evaluator (adversarial-review.yml, every PR,
no path filter).
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
        parts.append(text)  # unparsable module: scan everything, fail loud-open
    parts.extend(
        line.strip() for line in text.splitlines() if line.lstrip().startswith("#")
    )
    return "\n".join(parts)


def modules_claiming_without_boundary(texts: dict[str, str]) -> list[str]:
    out: list[str] = []
    for name, text in sorted(texts.items()):
        desc = _self_description(text).lower()
        if CLAIM in desc and BOUNDARY not in desc:
            out.append(name)
    return out


def scan_tree(root: Path) -> list[str]:
    """Recursive scan — nested test modules are in scope (r4 blocker 2)."""
    texts = {
        str(p.relative_to(root)): p.read_text() for p in sorted(root.rglob("*.py"))
    }
    return modules_claiming_without_boundary(texts)


def test_every_default_deny_claim_carries_an_honest_limit():
    offenders = scan_tree(TESTS)
    assert not offenders, (
        "test module(s) advertise default-deny without a stated honest limit "
        "in their own description — the false-confidence-gate family's "
        f"signature: {offenders}"
    )


def test_gate_goes_red_on_the_r3_defect_shape():
    # The r2 layer-3 module shape: DEFAULT-DENY advertised, no boundary.
    text = "# DEFAULT-DENY: no verb list to evade\ndef stale(): ...\n"
    assert modules_claiming_without_boundary({"m.py": text}) == ["m.py"]


def test_gate_goes_red_on_the_r4_literal_boundary_shape():
    # r4 blocker 1: an unrelated string literal must NOT satisfy the
    # boundary — both sides read the self-description only.
    text = (
        "# DEFAULT-DENY: no verb list to evade\n"
        'def t():\n    x = "honest limit mentioned only in a literal"\n'
    )
    assert modules_claiming_without_boundary({"m.py": text}) == ["m.py"]


def test_nested_modules_are_in_scope(tmp_path):
    # r4 blocker 2: a claim in a nested module must be found.
    sub = tmp_path / "nested" / "deeper"
    sub.mkdir(parents=True)
    (sub / "test_x.py").write_text("# default-deny gate\n")
    assert scan_tree(tmp_path) == ["nested/deeper/test_x.py"]


def test_gate_allows_claims_with_stated_boundary():
    text = "# DEFAULT-DENY …\n# Honest limit: deny-lists are incomplete.\n"
    assert modules_claiming_without_boundary({"m.py": text}) == []


def test_string_literal_mentions_are_out_of_scope():
    # An assertion message describing the SYSTEM's semantics (Postgres RLS
    # is default-deny by construction) is not the gate's own design claim.
    text = 'def t():\n    assert x, f"{t} must have NO policy (default-deny)"\n'
    assert modules_claiming_without_boundary({"m.py": text}) == []
