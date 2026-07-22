"""Tests for tools/provenance_lint.py — the structural fix for the
KAIZEN repeat class `overstated-provenance` (catches: PR #18 r1,
PR #50 r1 x4).

A research/strategy doc that admits its primary source went unread must
carry the honest frame in its FIRST heading (scout/pre-review-class
marker) and bind the gap to an R-### Record tag. The class's shape —
title claims a completed review while the body confesses the primary
was unreadable — must fail. Each requirement is demonstrated RED on a
planted defect, including the verbatim shape of the PR #50 r1 catch."""
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools import provenance_lint as pl

_UNREAD_SENTENCE = (
    "The egress policy blocks arxiv.org, so the primary paper was "
    "never read here."
)


def test_doc_without_unread_declaration_is_clean():
    text = "# Deep review of X\n\nWe read the paper carefully. R-001."
    assert pl.scan_text(text) == []


def test_pr50_shape_overclaiming_title_fails():
    # The verbatim class shape: completed-review title, unread-primary body.
    text = (
        "# Epiplexity applicability review — deep review of the paper\n\n"
        f"{_UNREAD_SENTENCE} Recorded as R-024.\n"
    )
    findings = pl.scan_text(text)
    assert len(findings) == 1
    assert "first heading" in findings[0]


def test_honest_scout_title_with_record_tag_is_clean():
    text = (
        "# Epiplexity secondary-source applicability scout (pre-review)\n\n"
        f"{_UNREAD_SENTENCE} Recorded as R-024.\n"
    )
    assert pl.scan_text(text) == []


def test_missing_record_tag_fails_even_with_honest_title():
    text = (
        "# Topic X — preliminary scout\n\n"
        f"{_UNREAD_SENTENCE}\n"
    )
    findings = pl.scan_text(text)
    assert len(findings) == 1
    assert "R-###" in findings[0]


def test_both_defects_planted_yields_both_findings():
    text = f"# Completed review of topic X\n\n{_UNREAD_SENTENCE}\n"
    assert len(pl.scan_text(text)) == 2


def test_subject_and_negation_in_different_sentences_do_not_trigger():
    # "primary source" mentioned; unreachability said about something else.
    text = (
        "# Review of X\n\nThe primary source is the vendor filing. The "
        "mirror site was unreachable during testing.\n"
    )
    assert pl.scan_text(text) == []


def test_negation_variants_trigger():
    for negation in (
        "could not be read",
        "couldn't be read",
        "is unread",
        "was unreachable",
        "is egress-blocked",
    ):
        text = f"# Plain review title\n\nThe primary PDF {negation}.\n"
        assert pl.scan_text(text), negation


def test_current_tree_is_clean():
    # The whole-tree invariant the validate gate enforces, proven here so
    # a regression in the corpus (or an overreaching lint change) fails
    # the suite, not just CI.
    assert pl.main() == 0


def test_original_pr50_doc_from_history_would_have_failed():
    # The lint must catch the exact artifact that created the class's
    # 4th recurrence: PR #50's original doc, reconstructed minimally
    # from its committed shape (completed-review title + the
    # evidence-strength note admitting the unread primary + R-024 tag).
    text = (
        "# Epiplexity applicability review — arXiv 2601.03220 vs the "
        "OneLive pipeline\n\n"
        "Evidence-strength note: this sandbox's egress policy 403-blocks "
        "arxiv.org (and the mirror hosts), so the primary PDF could NOT "
        "be read from here. Recorded as R-024 in docs/RECORD.md.\n"
    )
    findings = pl.scan_text(text)
    assert len(findings) == 1 and "first heading" in findings[0]
