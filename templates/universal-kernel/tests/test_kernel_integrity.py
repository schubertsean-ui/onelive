"""The kernel's own structure must hold — the template's first real gate.

This ships with the template so a fresh instantiation has a test suite that
can actually FAIL, not an empty directory that fakes green (kernel I2: a
gate that cannot fail proves nothing). It checks the things a project would
silently break while customizing: dropping an invariant from the charter,
deleting an overlay binding, or stripping the KERNEL header off a doc so
nobody can tell inherited text from project text.

Honest limit: this is a STRUCTURE check, not a semantics check. It proves
the invariants and bindings are PRESENT and labeled; it cannot prove they
are honored. Honoring them is what the independent evaluator and the
project's own gates in tools/project_checks.d/ are for.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The seven kernel invariant classes. A project may add to these via
# OVERLAY.md binding 2; it may never drop one.
INVARIANTS = [
    "I1 — Generation never self-certifies",
    "I2 — Gates fail closed",
    "I3 — Verifier independence",
    "I4 — Adverse findings are shown, never hidden",
    "I5 — No incentive contamination",
    "I6 — No silent deferrals",
    "I7 — Escalation is an enumerated, closed list",
]

# The eight overlay bindings, by their heading number.
BINDING_HEADINGS = [f"## {n}." for n in range(1, 9)]

KERNEL_DOCS = [
    "docs/OPERATING_RULES.md",
    "docs/KAIZEN.md",
    "docs/SESSION_START.md",
    "docs/CODING_CONVENTIONS.md",
    "docs/TESTS.md",
    "docs/hats/README.md",
    "docs/memory/README.md",
    "docs/session_arcs/README.md",
]


def test_charter_carries_every_invariant_class():
    charter = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    missing = [i for i in INVARIANTS if i not in charter]
    assert not missing, (
        "CLAUDE.md is missing kernel invariant class(es) — an overlay may add "
        f"constraints but never drop one: {missing}"
    )


def test_overlay_carries_every_binding():
    overlay = (ROOT / "OVERLAY.md").read_text(encoding="utf-8")
    missing = [h for h in BINDING_HEADINGS if h not in overlay]
    assert not missing, (
        f"OVERLAY.md is missing binding section(s) {missing} — an unfilled "
        "binding is a visible gap; a deleted one is an invisible gap."
    )


def test_every_kernel_doc_declares_itself_kernel():
    """Inherited text must be distinguishable from project text on sight."""
    offenders = []
    for rel in KERNEL_DOCS:
        p = ROOT / rel
        if not p.exists():
            offenders.append(f"{rel}: MISSING")
            continue
        head = p.read_text(encoding="utf-8")[:1200].upper()
        if "KERNEL" not in head:
            offenders.append(f"{rel}: no KERNEL declaration in its header")
    assert not offenders, (
        "kernel docs must announce themselves as inherited text so a reader "
        f"never confuses kernel with overlay: {offenders}"
    )


def test_escalation_list_names_gate_threshold_relaxations():
    """The single most load-bearing escalation item, spelled out.

    Every other rule in the model degrades gracefully under pressure. This
    one may not: an agent that can lower a bar can pass any bar.
    """
    charter = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "gate-threshold relaxations" in charter
    assert "never an agent decision" in charter


def test_the_gate_can_actually_fail():
    """Prove this file is not decorative (kernel I2, applied to itself)."""
    fake_charter = "I1 — Generation never self-certifies\n"  # missing I2–I7
    missing = [i for i in INVARIANTS if i not in fake_charter]
    assert len(missing) == 6, "the invariant check must red on a stripped charter"
