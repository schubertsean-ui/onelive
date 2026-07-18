"""Tests for tools/governance_claims_lint.py — the structural fix for the
KAIZEN repeat class `prose-classified-bypass` (3 catches: PR #36 r1, r4 ×2).

A governance doc may cite an artifact that exists, or mark a missing one
as staged/historical in the same sentence — presenting an absent
mechanism as live is the class, and it must fail."""
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools import governance_claims_lint as gcl


def test_existing_path_is_clean():
    assert gcl.scan_text("The gate is `tools/trust_gate.py` and it runs.") == []


def test_absent_path_without_marker_fails():
    findings = gcl.scan_text(
        "Compensated by tools/nonexistent_relock.py which fails the tree.")
    assert findings and "does not exist" in findings[0]


def test_absent_path_with_staging_marker_is_clean():
    assert gcl.scan_text(
        "The re-lock tools/nonexistent_relock.py lands in stage 3.") == []
    assert gcl.scan_text(
        "tools/nonexistent_relock.py is pending its first entry.") == []
    assert gcl.scan_text(
        "Historical: ai/removed_module.py was superseded.") == []


def test_marker_in_other_sentence_does_not_cover():
    findings = gcl.scan_text(
        "This arrives in stage 3. Compensated by tools/nonexistent_relock.py "
        "which fails the tree.")
    assert findings


def test_the_r4_defect_shape_fails():
    """The actual r4 charter shape: an absent record path cited as a live
    compensating control, no staging language in the sentence."""
    findings = gcl.scan_text(
        "trust_gate fails the tree when the hash differs from the committed "
        "record (ai/golden/NONEXISTENT_RECORD.json — outside the manifest).")
    assert findings and "NONEXISTENT_RECORD" in findings[0]


def test_real_governance_docs_are_clean():
    assert gcl.main() == 0
