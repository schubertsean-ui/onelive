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


def test_claim_scan_covers_every_prose_file_that_could_carry_a_claim():
    """DERIVED coverage, not a locked list (PR #75 r12, class
    self-weakenable-gate).

    The first version asserted the scan set contained STATE.md, TODOS.md and
    the workflows — exactly the hand-picked set the implementation had — so it
    could not fail when the round's actual false claim sat in
    templates/universal-kernel/STAGING_NOTE.md, outside both. A test that
    mirrors the implementation's blind spot certifies the blind spot.

    Now: walk the repo for prose files and assert every one is scanned. A new
    document is covered the day it is written, and a narrowing of claim_docs()
    fails here.
    """
    scanned = {p.resolve() for p in gcl.claim_docs()}
    missed = []
    for path in _ROOT.rglob("*.md"):
        rel = path.relative_to(_ROOT)
        if any(part in gcl._CLAIM_EXCLUDED_TREES for part in rel.parts):
            continue
        if str(rel).replace("\\", "/").startswith("docs/research/sources/"):
            continue  # someone else's captured text, not our claim
        if path.resolve() not in scanned:
            missed.append(str(rel))
    assert not missed, f"prose files outside the claim scan: {missed[:10]}"


def test_the_scan_reaches_the_file_that_escaped_it():
    """The concrete regression: STAGING_NOTE.md carried a false 'OneLive gates
    untouched' claim while sitting outside the scan."""
    scanned = {str(p.relative_to(_ROOT)) for p in gcl.claim_docs()}
    assert "templates/universal-kernel/STAGING_NOTE.md" in scanned


def test_a_verbatim_source_capture_is_not_our_prose_to_scope():
    """We may not rewrite a captured article to satisfy our own rule."""
    scanned = {str(p.relative_to(_ROOT)) for p in gcl.claim_docs()}
    assert not any(s.startswith("docs/research/sources/") for s in scanned)


def test_the_live_tree_is_clean_on_both_halves():
    assert gcl.main() == 0


# ── PR #75 r11: the gate against unconditional claims was itself bypassable
# by adding an adverb. Red cases proving a "scope marker" actually scopes.

def test_an_adverb_is_not_a_scope_marker():
    """`still` and `never` were accepted as scope. They bound nothing — both
    make the claim STRONGER. The absence-only seat found the gate could be
    satisfied by exactly the move it exists to prevent."""
    for unscoped in (
        "The gate still cannot be bypassed.",
        "This can never be bypassed by a pull request.",
        "The secret step is still fully closed.",
    ):
        assert gcl.scan_absolute_claims(unscoped), f"adverb passed as scope: {unscoped!r}"


def test_a_marker_that_names_what_is_not_covered_does_scope():
    """The compliant shape stays cheap, or the gate produces filler."""
    for scoped in (
        "It cannot be bypassed by swapping the file; this says nothing about PATH.",
        "An attacker would have to forge sha256, which does not cover command resolution.",
        "No PR-controlled code executes here — scoped: third-party packages are not covered.",
    ):
        assert gcl.scan_absolute_claims(scoped) == [], f"scoped text flagged: {scoped!r}"


def test_removed_markers_are_really_gone():
    """Binds the removal so a future edit cannot quietly restore the bypass."""
    for weak in ("still", "never"):
        assert weak not in gcl.SCOPE_MARKERS, (
            f"{weak!r} is back in SCOPE_MARKERS — it strengthens a claim rather "
            f"than bounding it, and re-opens the adverb bypass")
