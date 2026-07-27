"""Tests for tools/founder_ask_lint.py.

The rule (CLAUDE.md prime directive 6, founder directive 2026-07-26: *"never ask
me to do something without the specific structure defined"*): every OPEN founder
ask in docs/V1.md carries six labelled fields plus a recommendation, so the
founder is never handed a bare request or a click-path.

Proves: the real docs/V1.md passes (a live check, not a fixture); each missing
field is a separate finding; a click-path with no URL still fails because
'**Where:**' must be present as a label; RESOLVED asks are skipped as history;
prose mentions do not satisfy a field; and a file with no asks errors rather than
reporting clean.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "founder_ask_lint", _REPO_ROOT / "tools" / "founder_ask_lint.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


LINT = _load()

_FULL = """### Ask 9 — do a thing

**Options:**
1. the first way.
2. the second way.
3. the third way, which is bad because reasons.

**What:** the thing.

**Where:** <https://example.com/page>

**Exactly what to enter:** nothing to type.

**What you will see:** a page headed Example, and a green tick after clicking.

**Why this needs you:** it is a setting in your account; no API path exists.

**Time:** ~1 minute.

**Unblocks:** v1 done-criterion 1 and BAR C2.

**If you decline:** the cost is stated.

**Recommendation:** do it.
"""


def test_the_real_v1_asks_all_pass():
    # Live check against canon: a new ask landing without its structure fails here.
    text = LINT.DEFAULT_V1.read_text(encoding="utf-8")
    assert LINT._sections(text), "no asks found in docs/V1.md — check the heading regex"
    assert LINT.audit(text) == []


def test_a_fully_structured_ask_passes():
    assert LINT.audit(_FULL) == []


def test_every_missing_field_is_its_own_finding():
    bare = "### Ask 9 — do a thing\n\nJust go and do it.\n"
    findings = LINT.audit(bare)
    # six required fields + the recommendation
    assert len(findings) == len(LINT.REQUIRED_FIELDS) + 1
    assert any("Where" in f for f in findings)
    assert any("Recommendation" in f for f in findings)


def test_a_clickpath_without_a_url_still_fails():
    # The exact failure that prompted this gate: directions with no link.
    clickpath = _FULL.replace(
        "**Where:** <https://example.com/page>",
        "Go to Vercel then Settings then Deployment Protection.")
    findings = LINT.audit(clickpath)
    assert len(findings) == 1 and "Where" in findings[0]


def test_a_field_mentioned_only_in_prose_does_not_count():
    prose = _FULL.replace("**Time:** ~1 minute.",
                          "It should only take a minute of your Time: honestly.")
    findings = LINT.audit(prose)
    assert len(findings) == 1 and "Time" in findings[0]


def test_resolved_asks_are_skipped_as_history():
    resolved = "### Ask 4 — RESOLVED 2026-07-26 (the tagline)\n\nDone, no fields.\n"
    assert LINT.audit(resolved) == []
    done = "### Ask 8 — DONE by the founder\n\nNo fields needed.\n"
    assert LINT.audit(done) == []
    # SUPERSEDED counts too: folding two asks into one is the "an ask you can
    # delete beats an ask you can polish" rule working, and demanding full fields
    # on the tombstone would punish it.
    superseded = "### Ask 7 — SUPERSEDED by ask 6\n\nNothing separate to do.\n"
    assert LINT.audit(superseded) == []


def test_an_ask_that_cannot_name_what_it_moves_toward_go_live_is_a_finding():
    """Rule zero (founder, 2026-07-26): *"ALWAYS ASKING AND CONFIRMING IT GETS US
    CLOSER TO A WORLD CLASS GO LIVE."* An Unblocks field of pure intent is not a
    citation — it must name a v1 done-criterion number or a BAR row, because those
    are numbered precisely so this is checkable rather than felt."""
    vague = _FULL.replace("**Unblocks:** v1 done-criterion 1 and BAR C2.",
                          "**Unblocks:** it makes things better generally.")
    findings = LINT.audit(vague)
    assert len(findings) == 1
    assert "no v1 done-criterion number and no BAR row" in findings[0]


@pytest.mark.parametrize("citation", [
    "v1 done-criterion 1", "criterion 6", "done-criteria 2",
    "BAR C2", "bar row P1", "H7", "J11",
])
def test_each_accepted_go_live_citation_form_passes(citation):
    ok = _FULL.replace("**Unblocks:** v1 done-criterion 1 and BAR C2.",
                       f"**Unblocks:** {citation}.")
    assert LINT.audit(ok) == [], citation


def test_the_real_open_asks_each_cite_go_live_progress():
    text = LINT.DEFAULT_V1.read_text(encoding="utf-8")
    for number, heading, section in LINT._sections(text):
        if LINT._RESOLVED.search(heading):
            continue
        assert LINT.cites_golive_progress(section), \
            f"Ask {number} does not say which part of go-live it moves"


def test_a_url_plus_a_shape_without_a_walkthrough_is_a_finding():
    """The exact failure that added this field: a link and a form, but no
    statement of what the founder would SEE at each point."""
    no_walkthrough = _FULL.replace(
        "**What you will see:** a page headed Example, and a green tick after clicking.\n",
        "")
    findings = LINT.audit(no_walkthrough)
    assert len(findings) == 1 and "What you will see" in findings[0]


def test_an_em_dash_label_form_is_accepted():
    dashed = _FULL.replace("**Time:** ~1 minute.", "**Time —** ~1 minute.")
    assert LINT.audit(dashed) == []


def test_a_bulleted_label_is_accepted():
    bulleted = _FULL.replace("**Unblocks:** v1 done-criterion 1 and BAR C2.",
                             "- **Unblocks:** v1 done-criterion 1 and BAR C2.")
    assert LINT.audit(bulleted) == []


def test_two_options_padded_to_look_like_three_is_a_finding():
    """The padding failure the founder directive names explicitly."""
    two = _FULL.replace("3. the third way, which is bad because reasons.\n", "")
    findings = two and LINT.audit(two)
    assert len(findings) == 1
    assert "lists 2 enumerated option(s), needs 3" in findings[0]


def test_a_problem_with_no_options_at_all_is_a_finding():
    """The exact failure this rule exists to stop: a limitation, no ways out."""
    none = _FULL.replace("""**Options:**
1. the first way.
2. the second way.
3. the third way, which is bad because reasons.

""", "I cannot reach that host, so this cannot be verified.\n\n")
    findings = LINT.audit(none)
    assert len(findings) == 1 and "Options" in findings[0]


def test_lettered_options_are_accepted():
    lettered = _FULL.replace(
        "1. the first way.\n2. the second way.\n"
        "3. the third way, which is bad because reasons.",
        "(a) the first way.\n(b) the second way.\n(c) the third, bad, way.")
    assert LINT.audit(lettered) == []


def test_options_after_the_block_ends_do_not_count():
    """Enumerated lines under a LATER label must not pad the Options count."""
    spillover = _FULL.replace(
        "3. the third way, which is bad because reasons.\n",
        "").replace("**Time:** ~1 minute.",
                    "**Time:** ~1 minute.\n\n1. not an option\n2. also not")
    findings = LINT.audit(spillover)
    assert len(findings) == 1
    assert "lists 2 enumerated option(s)" in findings[0]


def test_count_options_is_zero_without_the_label():
    assert LINT.count_options("### Ask 9\n\n1. a\n2. b\n3. c\n") == 0


def test_the_real_v1_asks_each_offer_three_options():
    text = LINT.DEFAULT_V1.read_text(encoding="utf-8")
    for number, heading, section in LINT._sections(text):
        if LINT._RESOLVED.search(heading):
            continue
        assert LINT.count_options(section) >= LINT.MIN_OPTIONS, \
            f"Ask {number} offers fewer than {LINT.MIN_OPTIONS} options"


def test_a_file_with_no_asks_errors_rather_than_passing(tmp_path):
    # A checker that passes because it matched nothing proves nothing.
    path = tmp_path / "no_asks.md"
    path.write_text("# Nothing here\n", encoding="utf-8")
    assert LINT.main([str(path)]) == 2


def test_a_missing_file_errors(tmp_path):
    assert LINT.main([str(tmp_path / "nope.md")]) == 2


def test_main_returns_1_on_findings(tmp_path):
    path = tmp_path / "bad.md"
    path.write_text("### Ask 9 — bare\n\nno structure\n", encoding="utf-8")
    assert LINT.main([str(path)]) == 1


def test_main_returns_0_on_a_structured_file(tmp_path):
    path = tmp_path / "good.md"
    path.write_text(_FULL, encoding="utf-8")
    assert LINT.main([str(path)]) == 0


def test_the_bare_word_BAR_is_not_a_citation():
    """`CLASS:underconstrained-founder-ask-citation` (openai seat, PR #76).

    "Unblocks: BAR" passed this hard gate without naming which part of go-live the
    ask moves — a gate certifying asks that say nothing. A citation has to be
    resolvable by the reader.
    """
    for bare in ("Unblocks: BAR", "Unblocks: bar", "Unblocks: the BAR rows",
                 "Unblocks: BAR compliance"):
        assert not LINT._GOLIVE_CITATION.search(bare), bare
    # ...and every real citation form still counts, or the gate becomes noise.
    for good in ("Unblocks: BAR H7", "Unblocks: P1", "Unblocks: C2 and H7",
                 "Unblocks: v1 criterion 6", "Unblocks: done-criterion 4",
                 "Unblocks: J11"):
        assert LINT._GOLIVE_CITATION.search(good), good


def test_the_P_section_is_a_valid_citation():
    """The original character class was `[A-J]`, which excluded the P rows — and P1
    is the ten-second answer, the single most important row in docs/BAR.md. An ask
    citing it would have been rejected."""
    assert LINT._GOLIVE_CITATION.search("Unblocks: P1")
    assert LINT._GOLIVE_CITATION.search("Unblocks: P14")


# ------------------------- a heading with nothing under it is not a structure
def _ask(body: str) -> str:
    return "### Ask 9 — a test ask\n\n" + body


def test_a_field_label_with_nothing_under_it_is_a_finding():
    """`CLASS:underconstrained-founder-ask-gate` (openai/absence-only, PR #76 r2).

    The gate checked for LABEL PRESENCE only, so an ask could satisfy the founder's
    "specific structure" requirement with eight headings and no actionable content.
    Prose is not a control — the same lesson as the escape-closure gate.
    """
    for label in ("Why this needs you", "What you will see", "Time", "What",
                  "Exactly what to enter", "If you decline"):
        findings = LINT.audit(_ask(f"**{label}:**\n\n**Other:** x\n"))
        assert any(label in f and "EMPTY" in f for f in findings), (label, findings)


def test_bold_whitespace_does_not_count_as_content():
    findings = LINT.audit(_ask("**Time:** **   **\n"))
    assert any("Time" in f and "EMPTY" in f for f in findings), findings


def test_a_click_path_is_not_a_URL():
    """The founder's directive is explicit: "Always give me specific and accurate
    and working links". `**Where:** Vercel > Settings` is the banned shape."""
    findings = LINT.audit(_ask("**Where:** Vercel > Settings > Deployment\n"))
    assert any("Where" in f and "no URL" in f for f in findings), findings


def test_a_real_URL_satisfies_Where():
    findings = LINT.audit(_ask("**Where:** <https://vercel.com/x/y/settings>\n"))
    assert not any("Where" in f for f in findings), findings


def test_no_page_to_open_satisfies_Where():
    """An ask answered by replying has no URL to carry, and saying so is the
    correct answer rather than an omission — several live asks are this shape."""
    findings = LINT.audit(_ask("**Where:** nothing to open — reply here.\n"))
    assert not any("Where" in f for f in findings), findings


def test_a_short_but_complete_answer_is_accepted():
    """Calibration matters: a first attempt at this rejected `**Time:** seconds.`,
    which is a complete and honest answer. A gate that cries wolf gets routed
    around, so the floor only catches genuine emptiness."""
    findings = LINT.audit(_ask("**Time:** seconds.\n"))
    assert not any("Time" in f for f in findings), findings


def test_v1_criterion_without_a_number_is_not_a_citation():
    """The same class as the bare `BAR`, incompletely fixed: `v1 criterion` with no
    number names no part of go-live."""
    for bare in ("Unblocks: v1 criterion", "Unblocks: v1 criteria",
                 "Unblocks: v1 done-criterion"):
        assert not LINT._GOLIVE_CITATION.search(bare), bare
    assert LINT._GOLIVE_CITATION.search("Unblocks: v1 criterion 6")
    assert LINT._GOLIVE_CITATION.search("Unblocks: v1 done-criterion 4")
