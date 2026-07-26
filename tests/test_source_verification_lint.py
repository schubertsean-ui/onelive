"""Tests for tools/source_verification_lint.py — the mechanical half of the
founder's 2026-07-26 rule: "every claim or note or finding or result must be
independently verified. You cannot be trusted to monitor yourself."

The defect the gate exists for was real and in our own canon: the Construction
Loop's evidence document cited Klein, NASA, DORA, Aamodt & Plaza, Reflexion and
arXiv:2405.16334 with ZERO resolvable URLs, so nothing downstream of it could
be checked by anyone. These tests bind the two properties that fix it — a
citation must be FOLLOWABLE (URL) and its verification status must be DECLARED
— plus the fail-closed behaviors that stop the gate degrading into decoration.
"""
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from tools import source_verification_lint as svl


# ---------------------------------------------------------------- green cases

def test_entry_with_url_and_status_is_clean():
    assert svl.scan_text("d.md", (
        "# Doc\n\n## Sources\n"
        "- Mitchell et al. 1989 — https://doi.org/10.1002/bdm.3960020103 "
        "(UNVERIFIED-SECONDARY: publisher paywall)\n"
    )) == []


def test_url_and_status_may_span_wrapped_lines():
    """Real markdown citations wrap. A line-only parser would demand the URL
    and the token share one physical line and reject honest formatting."""
    assert svl.scan_text("d.md", (
        "## Sources\n"
        "- Devil's Advocate (EMNLP 2024 Findings), Wang et al.,\n"
        "  https://arxiv.org/abs/2405.16334\n"
        "  VERIFIED-ABSTRACT — abstract read, full PDF not retrieved.\n"
    )) == []


def test_every_status_token_is_accepted():
    for tok in svl.STATUS_TOKENS:
        assert svl.scan_text("d.md", f"## Sources\n- x https://e.org {tok}\n") == [], tok


def test_section_ends_at_the_next_heading():
    """Bullets after the Sources block belong to another section and must not
    be judged as citations — otherwise the gate manufactures findings."""
    assert svl.scan_text("d.md", (
        "## Sources\n- a https://e.org VERIFIED-READ\n"
        "\n## Notes\n- an ordinary bullet with no URL and no token\n"
    )) == []


# ------------------------------------------------------------------ red cases

def test_missing_sources_section_fails():
    findings = svl.scan_text("d.md", "# Doc\n\nClaims with no sources at all.\n")
    assert len(findings) == 1
    assert "no `## Sources` section" in findings[0]


def test_empty_sources_section_fails():
    """An empty block would otherwise satisfy the heading check — a gate that
    cannot fail is worse than no gate, because it reads as coverage."""
    findings = svl.scan_text("d.md", "## Sources\n\n(to be added)\n")
    assert findings and "no entries" in findings[0]


def test_entry_without_url_fails():
    findings = svl.scan_text("d.md", "## Sources\n- Klein, Sources of Power, 1998 VERIFIED-READ\n")
    assert len(findings) == 1
    assert "no resolvable URL" in findings[0]


def test_bare_domain_is_not_a_url():
    """This is the exact shape of the original defect: `dora.dev` looks like a
    citation and resolves to nothing a reader can click."""
    findings = svl.scan_text("d.md", "## Sources\n- DORA capability catalog — dora.dev VERIFIED-READ\n")
    assert len(findings) == 1
    assert "no resolvable URL" in findings[0]


def test_entry_without_status_token_fails():
    findings = svl.scan_text("d.md", "## Sources\n- Klein 1998 https://example.org/klein\n")
    assert len(findings) == 1
    assert "declares no verification status" in findings[0]


def test_url_and_status_both_missing_reports_both():
    findings = svl.scan_text("d.md", "## Sources\n- Klein, Sources of Power\n")
    assert len(findings) == 2


def test_near_miss_token_does_not_pass():
    """`VERIFIED` alone hides which half is true — read, or merely found?"""
    findings = svl.scan_text("d.md", "## Sources\n- x https://e.org VERIFIED\n")
    assert findings and "declares no verification status" in findings[0]


# -------------------------------------------------------------- fail-closed

def test_scan_reports_nothing_scanned_rather_than_clean(tmp_path):
    """Kernel I2: a check that examined zero inputs must never say 'clean'.
    Pointed at an empty tree, the enforced doc is absent -> two findings
    (missing doc, scanned nothing), never a green tree."""
    findings = svl.scan_repo(tmp_path)
    assert findings
    assert any("scanned ZERO documents" in f for f in findings)
    assert any("missing from the tree" in f for f in findings)


def test_enforced_docs_are_all_real_paths():
    """A typo in ENFORCED_DOCS would silently stop enforcing a document; the
    scanner reports it, and this test makes that impossible to ship."""
    for rel in svl.ENFORCED_DOCS:
        assert (_ROOT / rel).is_file(), f"{rel} listed in ENFORCED_DOCS but absent"


def test_the_live_repo_passes():
    """The enforced documents are clean right now — the gate is not landing
    pre-red, and a regression in canon's own sources fails here."""
    assert svl.scan_repo() == []


def test_the_originating_document_actually_carries_followable_sources():
    """Binds the fix, not just the gate: the construction-loop synthesis is the
    document whose unfollowable citations motivated this rule."""
    doc = _ROOT / "docs/research/2026-07-25_construction_loop_research_synthesis.md"
    text = doc.read_text(encoding="utf-8")
    assert svl.SOURCES_HEADING.search(text)
    assert len(svl.URL_RE.findall(text)) >= 4
