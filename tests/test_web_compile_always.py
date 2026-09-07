"""Compile is a required gate, not a sentence.

#260 merged an unclosed fetch() because tsc/next build were not on
trust-gate (the required check) and were path-filtered everywhere else.
A later docs PR still compiled the broken file. These tests fail if
that hole is re-cut.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "web-compile.yml"
TG = ROOT / ".github" / "workflows" / "trust-gate.yml"


def test_web_compile_workflow_has_no_path_filter():
    text = WF.read_text()
    header, _, _jobs = text.partition("jobs:")
    assert "paths:" not in header, (
        "A path filter is how a broken promoted.ts shipped. "
        "This job compiles the app on every PR."
    )
    assert "npx tsc --noEmit" in text
    assert "npm run build" in text
    assert "pull_request" in header
    assert "master" in header


def test_trust_gate_typechecks_web_with_no_path_filter():
    """trust-gate is the required check. tsc here would have failed #260."""
    text = TG.read_text()
    header, _, _jobs = text.partition("jobs:")
    assert "paths:" not in header
    assert "npx tsc --noEmit" in text, (
        "A conductor sentence does not stop an unclosed fetch from merging. "
        "tsc on the required gate does."
    )
