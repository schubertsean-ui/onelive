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


# ── The OTHER half of false-confidence-gate (added PR #75 r8) ────────────
# scan_text catches an ABSENT cited artifact. These cover the half that
# escaped it 8 times in this PR alone, past this tool's own structural-fix
# marker: the artifact exists but the sentence claims more than it does.
# The shape every escape took was an UNCONDITIONAL security assertion.

def test_unscoped_absolute_claim_fails():
    findings = gcl.scan_absolute_claims(
        "The final step re-reads the script and hard-fails if the digest "
        "differs. An attacker would have to forge sha256.")
    assert len(findings) == 1
    assert "no scope in the same sentence" in findings[0]


def test_the_exact_sentences_that_escaped_are_caught():
    """Regression cases, quoted from the r6 text the r7 seats blocked on."""
    for claim in (
        "An attacker would have to forge sha256.",
        "Now genuinely base-owned at execution: immutable SHA + sha256.",
    ):
        assert gcl.scan_absolute_claims(claim), f"escaped again: {claim!r}"


def test_a_scoped_claim_is_clean():
    """Naming what the control does NOT cover is the whole point — this must
    stay cheap to comply with, or the gate produces filler."""
    assert gcl.scan_absolute_claims(
        "An attacker would have to forge sha256 to swap the file; this "
        "control says nothing about which binary computes the digest."
    ) == []


def test_quoted_superseded_history_is_clean():
    """Corrections quote the original wrong claim verbatim rather than editing
    it away; a marked quotation is honest, not a live assertion."""
    assert gcl.scan_absolute_claims(
        "Now genuinely base-owned [QUOTED, FALSE and superseded at r8]: sha256."
    ) == []


def test_ordinary_prose_is_not_flagged():
    assert gcl.scan_absolute_claims(
        "The reviewer runs from the base ref and the digest is verified."
    ) == []


def test_claim_scan_covers_the_surfaces_that_actually_escaped():
    """The escapes were in workflow comments, STATE.md and TODOS.md — none of
    which governed_docs() reads. A scan of the wrong files cannot fail."""
    scanned = {str(p) for p in gcl.claim_docs()}
    for required in ("STATE.md", "TODOS.md"):
        assert any(s.endswith(required) for s in scanned), f"{required} unscanned"
    assert any(".github/workflows/adversarial-review.yml" in s for s in scanned)


def test_the_live_tree_is_clean_on_both_halves():
    assert gcl.main() == 0
