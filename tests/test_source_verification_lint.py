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
    assert "no http(s) URL" in findings[0]


def test_bare_domain_is_not_a_url():
    """This is the exact shape of the original defect: `dora.dev` looks like a
    citation and resolves to nothing a reader can click."""
    findings = svl.scan_text("d.md", "## Sources\n- DORA capability catalog — dora.dev VERIFIED-READ\n")
    assert len(findings) == 1
    assert "no http(s) URL" in findings[0]


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


# ── PR #78 evaluator findings — every one of these is a real bypass or bug
# the four-seat panel caught, kept as a red case so it cannot return. ──────

def test_status_token_substring_bypasses_are_closed():
    """Both OpenAI seats: `tok in line` accepted text that CONTAINS a token
    while declaring something else — or the opposite of it."""
    for bad in ("NOT-VERIFIED-READ", "XVERIFIED-READ", "UNVERIFIED-BLOCKEDNESS",
                "VERIFIED-READING", "UNVERIFIED-BLOCKED-EXTRA"):
        findings = svl.scan_text("d.md", f"## Sources\n- x https://e.org {bad}\n")
        assert findings and "declares no verification status" in findings[0], bad


def test_a_negated_status_does_not_count_as_declaring_one():
    """A negation GOVERNING the token declares the opposite of a read primary.

    Adjacency is not the rule (PR #78 r6, class negated-status-bypass): the
    first cut required the negation immediately before the token, so an
    intervening adverb walked straight through it. Scoping by clause instead
    of enumerating adverbs is the same derive-don't-list correction this arc
    kept needing."""
    for bad in ("not VERIFIED-READ", "never VERIFIED-READ", "not yet VERIFIED-READ",
                "not actually VERIFIED-READ", "not really VERIFIED-READ",
                "not currently VERIFIED-READ", "never fully VERIFIED-READ",
                "without being VERIFIED-READ", "is not in any sense VERIFIED-READ"):
        assert not svl.declares_status(f"- x https://e.org {bad}"), bad


def test_a_negation_does_not_leak_across_a_clause_boundary():
    """An honest entry that mentions a negated status and THEN declares a real
    one must still pass — over-rejection would push authors to omit context."""
    for good in ("not VERIFIED-READ; UNVERIFIED-SECONDARY",
                 "not VERIFIED-READ. UNVERIFIED-BLOCKED",
                 "status: UNVERIFIED-SECONDARY"):
        assert svl.declares_status(f"- x https://e.org {good}"), good


def test_punctuation_around_a_real_token_still_counts():
    """Boundary tightening must not make honest formatting fail."""
    for good in ("(VERIFIED-READ)", "VERIFIED-READ.", "— UNVERIFIED-BLOCKED;"):
        assert svl.declares_status(f"- x https://e.org {good}"), good


def test_subheadings_inside_sources_do_not_truncate_the_section():
    """gemini dataflow-taint: the comment claimed same-or-higher level while
    the regex cut at ANY heading, so a `## Sources` block organised with
    `### Primary` lost every citation under it and reported 'no entries' —
    a gate silently examining nothing."""
    text = ("## Sources\n"
            "### Primary\n- a https://e.org/a VERIFIED-READ\n"
            "### Secondary\n- b https://e.org/b UNVERIFIED-SECONDARY\n"
            "## Next section\n- unrelated bullet\n")
    assert svl.scan_text("d.md", text) == []
    # ...and a bad entry under a subheading is still caught, proving the
    # section is genuinely being read rather than skipped.
    bad = text.replace("- b https://e.org/b UNVERIFIED-SECONDARY", "- b (no url, no token)")
    assert len(svl.scan_text("d.md", bad)) == 2


def test_numbered_citations_are_entries():
    """gemini dataflow-taint: numbered lists are standard markdown; excluding
    them either false-failed or glued lines onto the previous bullet, masking
    missing URLs and tokens on every one of them."""
    assert svl.scan_text("d.md", "## Sources\n1. a https://e.org/a VERIFIED-READ\n2) b https://e.org/b UNVERIFIED-BLOCKED\n") == []
    findings = svl.scan_text("d.md", "## Sources\n1. a https://e.org/a VERIFIED-READ\n2. b with no url or token\n")
    assert len(findings) == 2, "a numbered entry's defects must be its own"


# ── R-054's trigger as a MECHANISM (both OpenAI seats: an unbacked
# "next time it is edited" trigger is a remediation that can silently
# never happen). ──────────────────────────────────────────────────────────

def test_touching_an_unenforced_research_doc_fails_the_gate(tmp_path, monkeypatch):
    import subprocess
    repo = tmp_path / "r"; (repo / "docs/research").mkdir(parents=True)
    def git(*a): subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
    git("init", "-q", "-b", "master")
    git("config", "user.email", "t@t"); git("config", "user.name", "t")
    (repo / "docs/research/old.md").write_text("seed\n")
    git("add", "-A"); git("commit", "-qm", "seed")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          capture_output=True, text=True).stdout.strip()
    (repo / "docs/research/new.md").write_text("a new synthesis\n")
    (repo / "docs/research/old.md").write_text("edited\n")
    git("add", "-A"); git("commit", "-qm", "touch two research docs")

    findings = svl.scan_scope(repo, f"{base}...HEAD")
    touched = {f.split(":")[0] for f in findings}
    assert touched == {"docs/research/new.md", "docs/research/old.md"}
    assert all("NOT in ENFORCED_DOCS" in f for f in findings)

    # ...and a document already under the gate is not re-flagged.
    monkeypatch.setattr(svl, "ENFORCED_DOCS", ("docs/research/old.md",))
    assert {f.split(":")[0] for f in svl.scan_scope(repo, f"{base}...HEAD")} == {"docs/research/new.md"}


def test_scope_check_reports_an_unanswerable_diff_rather_than_passing(tmp_path):
    """§1: a failure must never look identical to 'there was nothing to do'."""
    findings = svl.scan_scope(tmp_path, "origin/master...HEAD")
    assert findings and "could not read the diff" in findings[0]


def test_scope_check_is_silent_when_no_research_doc_is_touched(tmp_path):
    import subprocess
    repo = tmp_path / "r"; repo.mkdir()
    def git(*a): subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
    git("init", "-q", "-b", "master")
    git("config", "user.email", "t@t"); git("config", "user.name", "t")
    (repo / "a.py").write_text("x = 1\n"); git("add", "-A"); git("commit", "-qm", "seed")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          capture_output=True, text=True).stdout.strip()
    (repo / "a.py").write_text("x = 2\n"); git("add", "-A"); git("commit", "-qm", "edit")
    assert svl.scan_scope(repo, f"{base}...HEAD") == []


# ── PR #78 r3 findings — each is a real bypass or dead end the panel found,
# kept as a red case. Probed directly, not reasoned about. ────────────────

def test_a_status_token_inside_a_url_does_not_count():
    """openai attacker-smuggle: `https://example.org/VERIFIED-READ` satisfied
    the gate while declaring no status at all. The token must be the author's
    own assertion, not a substring of the thing being cited."""
    findings = svl.scan_text("d.md", "## Sources\n- x https://example.org/VERIFIED-READ\n")
    assert findings and "declares no verification status" in findings[0]


def test_a_status_token_inside_markdown_link_text_does_not_count():
    findings = svl.scan_text("d.md", "## Sources\n- [VERIFIED-READ paper](https://e.org)\n")
    assert findings and "declares no verification status" in findings[0]


def test_a_real_status_alongside_a_url_that_contains_one_still_passes():
    """Stripping must not break the honest case."""
    assert svl.scan_text(
        "d.md", "## Sources\n- x https://example.org/VERIFIED-READ — UNVERIFIED-SECONDARY\n") == []


def test_every_status_match_is_considered_not_only_the_first():
    """gemini dataflow-taint: an entry mentioning a negated status and THEN
    declaring an honest one was rejected, because only the first match was
    inspected."""
    assert svl.declares_status("- x https://e.org not VERIFIED-READ; UNVERIFIED-SECONDARY")


def test_a_heading_after_a_bullet_is_not_continuation_text():
    """gemini dataflow-taint: gluing a heading onto the previous bullet let the
    heading's URL or token satisfy a bullet that had neither."""
    findings = svl.scan_text(
        "d.md", "## Sources\n- a bare claim with nothing\n### https://e.org VERIFIED-READ\n")
    assert len(findings) == 2, findings


def test_deleting_an_unenforced_research_doc_does_not_deadlock_the_gate(tmp_path):
    """gemini dataflow-taint: a deleted path was flagged as touched, and adding
    it to ENFORCED_DOCS to satisfy that made scan_repo fail on the missing
    file — an unresolvable gate deadlock."""
    import subprocess
    repo = tmp_path / "r"; (repo / "docs/research").mkdir(parents=True)
    def git(*a): subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
    git("init", "-q", "-b", "master")
    git("config", "user.email", "t@t"); git("config", "user.name", "t")
    (repo / "docs/research/gone.md").write_text("seed\n")
    git("add", "-A"); git("commit", "-qm", "seed")
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          capture_output=True, text=True).stdout.strip()
    (repo / "docs/research/gone.md").unlink()
    git("add", "-A"); git("commit", "-qm", "delete it")
    assert svl.scan_scope(repo, f"{base}...HEAD") == []


# ── the provenance branch: a remediation that can actually be satisfied ──

CAPTURE = "docs/research/sources/some_capture.md"


def test_a_source_capture_may_declare_provenance_instead_of_sources():
    """openai absence-only (r3): R-054 and the tool's finding text offered
    verbatim source captures 'a provenance line, not a Sources block', and no
    code accepted one — a remediation that could never be met."""
    assert svl.scan_text(
        CAPTURE, "# Captured article\n\nPROVENANCE: https://e.org/a UNVERIFIED-BLOCKED\n") == []


def test_a_synthesis_may_not_use_the_provenance_escape_hatch():
    """openai r4, class provenance-escape-hatch — THE misuse case. Path-agnostic
    acceptance let an enforced synthesis delete its Sources block, add one
    provenance line, and pass: the escape hatch emptying the gate it completes.
    A green-only test for an escape hatch codifies the bypass as intended."""
    findings = svl.scan_text(
        "docs/research/2026-07-25_some_synthesis.md",
        "# Synthesis\n\nPROVENANCE: https://e.org/a VERIFIED-READ\n")
    assert findings and "only for verbatim source captures" in findings[0]


def test_provenance_hidden_in_an_html_comment_is_not_accepted():
    """It renders invisibly, which defeats 'cite it where the claim lives'."""
    findings = svl.scan_text(CAPTURE, "<!-- PROVENANCE: https://e.org/a VERIFIED-READ -->\n")
    assert findings, "an invisible provenance declaration must not satisfy the gate"


def test_a_provenance_line_is_held_to_the_same_bar_as_a_citation():
    """Otherwise it becomes the escape hatch that empties the gate."""
    assert any("no http(s) URL" in f for f in
               svl.scan_text(CAPTURE, "PROVENANCE: somewhere VERIFIED-READ\n"))
    assert any("declares no verification status" in f for f in
               svl.scan_text(CAPTURE, "PROVENANCE: https://e.org/a\n"))
    assert len(svl.scan_text(CAPTURE, "PROVENANCE: nothing useful\n")) == 2


# ── continuation may not absorb arbitrary following text (r4) ────────────

def test_a_paragraph_after_a_defective_bullet_does_not_rescue_it():
    """openai attacker-smuggle r4, class unbounded-continuation-bypass: an
    unindented paragraph — with or without a divider before it — was glued to
    the previous bullet and supplied its URL and status."""
    for filler in ("", "### Divider\n"):
        text = ("## Sources\n- a bare claim with nothing\n" + filler +
                "https://e.org/a VERIFIED-READ\n")
        findings = svl.scan_text("d.md", text)
        assert len(findings) == 2, (filler, findings)


def test_a_blank_line_closes_an_entry():
    text = "## Sources\n- a bare claim\n\n  https://e.org/a VERIFIED-READ\n"
    assert len(svl.scan_text("d.md", text)) == 2


def test_genuine_indented_wrapping_still_works():
    """The tightening must not break honest multi-line citations."""
    assert svl.scan_text("d.md", (
        "## Sources\n- Devil's Advocate, Wang et al.,\n"
        "  https://arxiv.org/abs/2405.16334\n"
        "  UNVERIFIED-SECONDARY — abstract via search only.\n")) == []


def test_the_no_sources_finding_names_both_accepted_shapes():
    """A finding that names an impossible remedy is a dead end; this one has
    to point at something the tool will actually accept."""
    findings = svl.scan_text("d.md", "# Doc\n\nNo sources, no provenance.\n")
    assert len(findings) == 1
    assert "PROVENANCE:" in findings[0] and "Sources" in findings[0]


# ── Hidden evidence is not evidence (PR #78 r5, class
# invisible-citation-bypass). r4 closed only the hidden-PROVENANCE case; every
# sibling path stayed open. These bind the property for each syntax that can
# render to nothing, so a future parser change cannot reopen one of them.

def test_a_sources_block_hidden_in_an_html_comment_does_not_count():
    assert svl.scan_text("d.md", "<!--\n## Sources\n- x https://e.org VERIFIED-READ\n-->\n")


def test_a_citation_bullet_hidden_under_a_visible_heading_does_not_count():
    """The heading renders; the entry does not. The gate must see what the
    READER sees, not what the file contains."""
    findings = svl.scan_text("d.md", "## Sources\n<!--\n- x https://e.org VERIFIED-READ\n-->\n")
    assert findings and "no entries" in findings[0]


def test_a_url_hidden_in_a_comment_does_not_satisfy_the_url_requirement():
    findings = svl.scan_text("d.md", "## Sources\n- x <!-- https://e.org --> VERIFIED-READ\n")
    assert findings and "no http(s) URL" in findings[0]


def test_a_status_token_hidden_in_a_comment_does_not_declare_a_status():
    findings = svl.scan_text("d.md", "## Sources\n- x https://e.org <!-- VERIFIED-READ -->\n")
    assert findings and "declares no verification status" in findings[0]


def test_a_fenced_code_block_cannot_carry_the_citations():
    """Fenced blocks render as literal code, not as the document's sources."""
    for fence in ("```", "~~~"):
        text = f"{fence}\n## Sources\n- x https://e.org VERIFIED-READ\n{fence}\n"
        assert svl.scan_text("d.md", text), fence


def test_a_multiline_comment_cannot_carry_a_provenance_line():
    """r4 rejected the single-line form only."""
    assert svl.scan_text(CAPTURE, "<!--\nPROVENANCE: https://e.org/a VERIFIED-READ\n-->\n")


def test_visible_citations_are_unaffected_by_the_stripping():
    """The tightening must not break honest documents — including ones that
    legitimately contain a code fence elsewhere."""
    assert svl.scan_text("d.md", (
        "# Doc\n\n```\nsome example code\n```\n\n"
        "## Sources\n- x https://e.org VERIFIED-READ\n")) == []


# ── CommonMark hiding places the r5 stripper still missed (PR #78 r7) ─────

def test_a_longer_closing_fence_still_closes_the_block():
    """CommonMark allows the closing fence to be LONGER than the opening one.
    A regex backreference demands an exact-length match, so these were
    mis-handled — and a mis-handled fence is a place to hide a citation."""
    for opener, closer in (("```", "````"), ("````", "````"), ("~~~", "~~~~~")):
        text = f"{opener}\n## Sources\n- x https://e.org VERIFIED-READ\n{closer}\n"
        assert svl.scan_text("d.md", text), (opener, closer)


def test_an_indented_code_block_cannot_carry_a_citation():
    """Four spaces (or a tab) renders as code. The parser saw a bullet; the
    reader sees a code listing."""
    for indent in ("    ", "\t"):
        text = f"## Sources\n\n{indent}- x https://e.org VERIFIED-READ\n"
        assert svl.scan_text("d.md", text), repr(indent)


def test_ordinary_wrapped_continuation_survives_the_code_rule():
    """The list-vs-code threshold must not break honest two-space wrapping."""
    assert svl.scan_text("d.md", (
        "## Sources\n- Devil's Advocate, Wang et al.,\n"
        "  https://arxiv.org/abs/2405.16334\n"
        "  UNVERIFIED-SECONDARY — abstract only.\n")) == []


def test_a_parenthetical_negation_does_not_govern_a_later_token():
    """gemini r7 nit: "(no abstract)" is description, not a status denial."""
    assert svl.declares_status("- Smith 2020 (no abstract) https://e.org VERIFIED-READ")
    assert svl.declares_status("- Smith (not peer reviewed) https://e.org UNVERIFIED-SECONDARY")


# ── FALSE REJECTION is a defect too (PR #78 r8, gemini dataflow-taint). A gate
# that forces authors to mangle real citation text to pass is broken in the
# other direction, and pushes people to omit context rather than fix it.

def test_negation_words_inside_a_title_do_not_deny_the_status():
    """"Parsing without Regrets" and "No Silver Bullet" are WORKS BEING CITED,
    not the author denying a verification status."""
    for good in ('- Author, "Parsing without Regrets", https://e.org VERIFIED-READ',
                 '- Smith, "No Silver Bullet", https://e.org VERIFIED-READ',
                 '- Lee, “Neither Here Nor There”, https://e.org UNVERIFIED-BLOCKED'):
        assert svl.declares_status(good), good


def test_issue_metadata_does_not_deny_the_status():
    """`Vol 12, No 4` is a citation's own metadata."""
    assert svl.declares_status("- Brown, Vol 12, No 4, https://e.org VERIFIED-READ")


def test_a_four_space_wrapped_continuation_is_not_treated_as_code():
    """CommonMark: an indented code block cannot interrupt a list item, so a
    four-space wrapped citation line is continuation, not code. Stripping it
    unconditionally deleted evidence before it was ever parsed."""
    assert svl.scan_text("d.md", (
        "## Sources\n- Wang et al.,\n    https://arxiv.org/abs/2405.16334\n"
        "    UNVERIFIED-SECONDARY — abstract only.\n")) == []


def test_the_indented_code_bypass_stays_closed():
    """The fix above must not reopen r7: a four-space bullet with no open list
    item before it is still code, not a citation."""
    assert svl.scan_text("d.md", "## Sources\n\n    - x https://e.org VERIFIED-READ\n")


# ── The list-item state machine, both directions (PR #78 r9). Getting the
# transitions wrong breaks the gate as a bypass AND as a false rejection, and
# r8 got two transitions wrong at once. One test per transition.

def test_mixed_two_and_four_space_indentation_is_all_continuation():
    """r8 reset the state on any non-bullet line, so a 2-space wrapped line
    closed the item and the 4-space line after it was DROPPED as code — real
    citation evidence deleted before the parser ever saw it."""
    assert svl.scan_text("d.md", (
        "## Sources\n- Wang et al.,\n  https://arxiv.org/abs/2405.16334\n"
        "    VERIFIED-ABSTRACT — abstract only.\n")) == []


def test_a_blank_line_closes_the_list_item():
    """r8 left the item open across blank lines, so an indented code block
    after a bullet was kept as continuation — a hiding place."""
    assert svl.scan_text("d.md", "## Sources\n- a bare claim\n\n    https://e.org VERIFIED-READ\n")


def test_an_unindented_line_closes_the_list_item():
    assert svl.scan_text("d.md", (
        "## Sources\n- a bare claim\nprose at column zero\n"
        "    https://e.org VERIFIED-READ\n"))


def test_indentation_of_one_to_three_spaces_keeps_the_item_open():
    assert svl.scan_text("d.md", (
        "## Sources\n- Wang,\n   https://e.org\n    VERIFIED-READ\n")) == []
