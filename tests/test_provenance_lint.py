"""Tests for tools/provenance_lint.py — the structural fix for the
KAIZEN repeat class `overstated-provenance` (catches: PR #18 r1,
PR #50 r1 x4; hardened at PR #50 r3, which caught v1 of the tool as a
false-confidence gate — one of four surfaces scanned, any R-token
accepted as "Record-bound").

Each requirement is demonstrated RED on a planted defect, including the
verbatim shape of the PR #50 r1 catch and both r3 blockers."""
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools import provenance_lint as pl

_UNREAD_SENTENCE = (
    "The egress policy blocks arxiv.org, so the primary paper was "
    "never read here."
)
_BASENAME = "MY_SCOUT_v1.md"
# A minimal RECORD.md fixture: R-024 references the scout; R-001 does not.
_RECORD_FIXTURE = (
    "| R-001 | 2026-07-13 | unrelated hold | bar | trigger | OPEN |\n"
    f"| R-024 | 2026-07-22 | scout doc {_BASENAME} built from secondary "
    "sources | bar | trigger | OPEN |\n"
)


def _doc(title: str, body: str) -> str:
    return f"# {title}\n\n{body}\n"


# ---------------- ARTIFACT RULE ----------------

def test_doc_without_unread_declaration_is_clean():
    text = _doc("Deep review of X", "We read the paper carefully. R-024.")
    assert pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE) == []


def test_pr50_shape_overclaiming_title_fails():
    # The verbatim r1 class shape: completed-review title, unread body.
    text = _doc("Epiplexity applicability review — deep paper review",
                f"{_UNREAD_SENTENCE} Recorded as R-024.")
    findings = pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE)
    assert findings and any("first heading" in f for f in findings)


def test_honest_scout_title_with_bound_record_tag_is_clean():
    text = _doc("Epiplexity secondary-source applicability scout (pre-review)",
                f"{_UNREAD_SENTENCE} Recorded as R-024.")
    assert pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE) == []


def test_overstrong_title_not_laundered_by_marker_word():
    # r3 nit: "Provisional deep review" must fail despite the marker.
    for title in ("Provisional deep review of X",
                  "Incomplete completed review of X"):
        text = _doc(title, f"{_UNREAD_SENTENCE} Recorded as R-024.")
        findings = pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE)
        assert any("overstrong" in f for f in findings), title


def test_missing_record_tag_fails_even_with_honest_title():
    text = _doc("Topic X — preliminary scout", _UNREAD_SENTENCE)
    findings = pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE)
    assert len(findings) == 1 and "R-###" in findings[0]


def test_unbound_record_tag_fails():
    # r3 blocker: R-999 (nonexistent) and R-001 (row exists but does not
    # reference this doc) are not resolution paths.
    for tag in ("R-999", "R-001"):
        text = _doc("Topic X — preliminary scout",
                    f"{_UNREAD_SENTENCE} Recorded as {tag}.")
        findings = pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE)
        assert len(findings) == 1 and "resolution path" in findings[0], tag


def test_both_defects_planted_yields_title_and_binding_findings():
    text = _doc("Completed review of topic X",
                f"{_UNREAD_SENTENCE} See R-999.")
    findings = pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE)
    assert len(findings) == 3  # no marker + overstrong + unbound tag


def test_subject_and_negation_in_separate_paragraphs_do_not_trigger():
    # Detection is paragraph-level (r5): co-occurrence within a
    # paragraph triggers; separate paragraphs do not.
    text = _doc("Review of X",
                "The primary source is the vendor filing.\n\n"
                "The mirror site was unreachable during testing.")
    assert pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE) == []


def test_negation_variants_trigger():
    for negation in ("could not be read", "couldn't be read", "is unread",
                     "was unreachable", "is egress-blocked"):
        text = _doc("Plain review title",
                    f"The primary PDF {negation}. See R-024.")
        assert pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE), negation


def test_multisentence_admission_in_one_paragraph_triggers():
    # r5 nit: same-sentence-only detection missed multi-sentence
    # admissions. Same paragraph must trigger; separate paragraphs with
    # unrelated negations must not.
    text = _doc("Plain review title",
                "Primary paper: the Smith study. Egress blocked. "
                "We never read it. See R-024.")
    assert pl.declares_unread_primary(text) is not None
    assert pl.scan_doc(text, _BASENAME, _RECORD_FIXTURE)
    apart = _doc("Review of X",
                 "The primary source is the vendor filing.\n\n"
                 "The mirror site was unreachable during testing.")
    assert pl.declares_unread_primary(apart) is None


# ---------------- SURFACE RULE ----------------

def _surface(line: str) -> list:
    return pl.scan_surface_lines(line, "docs/ONE_LIVE_CHANGE_LOG.md",
                                 [_BASENAME], _RECORD_FIXTURE)


def test_surface_mention_without_marker_or_tag_fails():
    # r3 blocker shape: a changelog line calling the scout a deep review.
    line = f"- Deep review committed: docs/strategy/{_BASENAME} covering it all."
    findings = _surface(line)
    assert len(findings) == 1 and "overstrong" in findings[0]


def test_surface_mention_with_marker_is_clean():
    line = f"- Secondary-source scout committed: docs/strategy/{_BASENAME}."
    assert _surface(line) == []


def test_surface_unbound_tags_fail():
    # r4 blocker: any-R-token acceptance recreated the false-confidence
    # hole on the bookkeeping surfaces. R-999 does not exist; R-001
    # exists but does not name the artifact — both must fail.
    for tag in ("R-999", "R-001"):
        line = f"- Deep review committed: docs/strategy/{_BASENAME}; see {tag}."
        findings = _surface(line)
        assert len(findings) == 1, tag


def test_surface_overclaim_with_genuine_bound_tag_still_fails():
    # r5 blocker: the bound tag must NOT short-circuit the overclaim
    # check — "Deep review committed: SCOUT.md; see R-024" laundered
    # through the GENUINE tag at r4. Overstrong is unconditional.
    line = f"- Deep review committed: docs/strategy/{_BASENAME}; see R-024."
    findings = _surface(line)
    assert len(findings) == 1 and "unconditional" in findings[0]


def test_surface_bound_tag_rescues_markerless_nonoverstrong_line():
    # The legitimate role of a bound tag: a resolution-record line with
    # neither marker vocabulary nor overstrong phrasing.
    line = (f"| R-024 | resolution record for {_BASENAME}, checked "
            f"against the supplied paper | RESOLVED |")
    assert _surface(line) == []


def test_surface_overstrong_not_laundered_by_marker():
    # r4 nit: "provisional completed review" may not launder bookkeeping
    # — and per r5, adding a bound tag must not save it either.
    for suffix in ("", " (R-024)"):
        line = (f"- Provisional completed review shipped: "
                f"docs/strategy/{_BASENAME}.{suffix}")
        findings = _surface(line)
        assert len(findings) == 1 and "overstrong" in findings[0], suffix


def test_surface_lines_not_mentioning_scout_are_unconstrained():
    text = "- Deep review of the completed pipeline shipped today.\n"
    assert _surface(text) == []


# ---------------- WHOLE TREE ----------------

def test_record_rows_parser():
    rows = pl.record_rows(_RECORD_FIXTURE)
    assert set(rows) == {"R-001", "R-024"} and _BASENAME in rows["R-024"]


def test_current_tree_is_clean():
    # The whole-tree invariant the validate gate enforces, proven here so
    # a regression in the corpus (or an overreaching lint change) fails
    # the suite, not just CI.
    assert pl.main() == 0


def test_original_pr50_doc_from_history_would_have_failed():
    # The lint must catch the exact artifact that created the class's
    # 4th recurrence: PR #50's original doc, reconstructed minimally
    # from its committed shape.
    text = (
        "# Epiplexity applicability review — arXiv 2601.03220 vs the "
        "OneLive pipeline\n\n"
        "Evidence-strength note: this sandbox's egress policy 403-blocks "
        "arxiv.org (and the mirror hosts), so the primary PDF could NOT "
        "be read from here. Recorded as R-024 in docs/RECORD.md.\n"
    )
    findings = pl.scan_doc(text, "ONE_LIVE_EPIPLEXITY_APPLICABILITY_REVIEW_v1.md",
                           _RECORD_FIXTURE)
    assert findings and any("first heading" in f for f in findings)
