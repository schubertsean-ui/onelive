"""Mechanical compliance checks for design/proposals/direction-*.html.

Greppable summary: assertion-bearing tests (PR #20 evaluator round 2 —
"screenshots aren't tests") for the static design-direction comps. These
run in CI on every PR and FAIL on: missing verbatim canon copy, trust-badge
vocabulary, banned rating glyphs / native emoji, a feed uncertainty icon
that is not a real <details> control, missing light-mode implementation,
or glyphs without accessible text equivalents. They check textual
invariants a renderer can't: pixels prove rendering happened; these prove
the comps say what the canon requires and nothing it forbids.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PROPOSALS = Path(__file__).resolve().parent.parent / "design" / "proposals"
DIRECTIONS = [
    "direction-1-marquee.html",
    "direction-2-current.html",
    "direction-3-setlist.html",
]

# Verbatim canon copy (design brief §3/§4 + trust rules) — exact strings.
REQUIRED_VERBATIM = [
    "Tonight in Austin",
    "Less chaos. Real shows.",
    "Something off?",
    "Hear it",
    "— first notes",  # tier-C machine-drafted spark attribution
    "✳",  # tier-C subtle mark
]

# The brief's 8 fixed genres (§4, screen 2).
REQUIRED_GENRES = [
    "Rock", "Hip-Hop", "Jazz", "Electronic",
    "Country", "Metal", "Experimental", "Latin",
]

# Trust-display rule: competence shown, never told (brief §2).
# Checked against VISIBLE TEXT only (tags stripped), case-insensitive,
# word-boundaried so e.g. CSS class names or 'unverified' can't false-hit.
FORBIDDEN_TRUST_WORDS = ["verified", "confirmed", "trusted", "trust score"]

# Emotion Glyph lexicon bans rating/endorsement glyphs + native emoji
# (brief appendix, lexicon rule 4) and checkmark/badge characters.
FORBIDDEN_CHARS = ["🔥", "⭐", "💯", "👑", "❤️", "👍", "✓", "✔", "🛡"]


@pytest.fixture(scope="module", params=DIRECTIONS)
def direction(request) -> tuple[str, str]:
    path = PROPOSALS / request.param
    assert path.is_file(), f"missing direction file: {path}"
    return request.param, path.read_text(encoding="utf-8")


def _visible_text(html: str) -> str:
    """Strip <style> blocks, comments, and tags — approximate rendered text."""
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", html)


def test_all_three_directions_exist():
    for name in DIRECTIONS:
        assert (PROPOSALS / name).is_file(), f"brief mandates 3 directions; missing {name}"


def test_verbatim_canon_copy_present(direction):
    name, html = direction
    for phrase in REQUIRED_VERBATIM:
        assert phrase in html, f"{name}: verbatim canon copy missing: {phrase!r}"


def test_all_eight_genres_present(direction):
    name, html = direction
    for genre in REQUIRED_GENRES:
        assert genre in html, f"{name}: filter panel missing genre {genre!r}"


def test_no_trust_badge_vocabulary_in_visible_text(direction):
    name, html = direction
    text = _visible_text(html).lower()
    for word in FORBIDDEN_TRUST_WORDS:
        assert not re.search(rf"\b{re.escape(word)}\b", text), (
            f"{name}: forbidden trust vocabulary {word!r} in visible text "
            f"(brief §2: never say it, show it)"
        )


def test_no_banned_glyphs_or_native_emoji(direction):
    name, html = direction
    for ch in FORBIDDEN_CHARS:
        assert ch not in html, (
            f"{name}: banned character {ch!r} (glyph lexicon rule: no "
            f"rating/endorsement glyphs, no native emoji, no checkmarks)"
        )
    # Unicode-class sweep, not just a blacklist (evaluator round 3 nit):
    # any emoji/dingbat-range character is banned except the canon ✳ mark.
    allowed = {"✳"}
    for ch in html:
        code = ord(ch)
        in_emoji_range = (
            0x1F000 <= code <= 0x1FAFF
            or 0x2600 <= code <= 0x27BF
            or 0x2B00 <= code <= 0x2BFF
            or code in (0xFE0F, 0x200D)
        )
        assert not (in_emoji_range and ch not in allowed), (
            f"{name}: emoji-range character {ch!r} (U+{code:04X}) — comps "
            f"use self-rendered SVG glyphs only"
        )


def test_v2_founder_feedback_elements_present(direction):
    """2026-07-15 founder round: prominent genre rail, headliner venue row
    with city mini-map + distance, three-sample listening, Nearby section."""
    name, html = direction
    assert 'class="genre-rail"' in html, f"{name}: missing prominent genre rail"
    assert html.count('class="grail') >= 9, f"{name}: genre rail must carry All + 8 genres"
    assert html.count('class="venue-row"') >= 4, f"{name}: venue rows missing"
    assert html.count('class="citymap"') >= 5, (
        f"{name}: city mini-map missing (4 feed cards + detail distance)"
    )
    assert html.count("mi</span>") >= 5 or html.count(" mi<") >= 5, (
        f"{name}: distance-from-you indicators missing"
    )
    assert html.count('class="sample') >= 3, f"{name}: three listening samples required"
    assert ">Nearby<" in html, f"{name}: Nearby section missing on detail screen"
    assert "Details ›" in html, f"{name}: explicit card-tap affordance missing"


def test_feed_uncertainty_icon_is_a_real_control(direction):
    """The quiet icon must be a tappable <details> opening the sheet —
    at the point where uncertainty is shown, not only on the detail screen."""
    name, html = direction
    quiet_blocks = re.findall(
        r'<details class="sheet quiet">.*?</details>', html, flags=re.S
    )
    assert quiet_blocks, f"{name}: feed uncertainty icon is not a <details> control"
    for block in quiet_blocks:
        assert "<summary" in block and "sheet-body" in block, (
            f"{name}: uncertainty control lacks summary + dismissible sheet body"
        )


def test_uncertainty_sheets_link_real_venue_sites(direction):
    """The venue link inside an uncertainty sheet is THE corroboration
    affordance — it must be a real absolute URL, never a dead anchor
    (PR #20 evaluator round 3: a stub here is a fake corroboration link,
    and a test that doesn't inspect href passes the broken thing)."""
    name, html = direction
    sheets = re.findall(r'<div class="sheet-body">.*?</div>', html, flags=re.S)
    assert sheets, f"{name}: no uncertainty sheet bodies found"
    for sheet in sheets:
        hrefs = re.findall(r'href="([^"]*)"', sheet)
        assert hrefs, f"{name}: uncertainty sheet has no venue link at all"
        for href in hrefs:
            assert re.match(r"^https://", href), (
                f"{name}: uncertainty-sheet venue link must be a real "
                f"absolute URL, got {href!r}"
            )


def test_light_mode_is_implemented_not_promised(direction):
    name, html = direction
    assert "html.light{" in html, (
        f"{name}: light mode must be implemented (html.light overrides), "
        f"not palette prose (brief §4: light + dark themes)"
    )


def test_every_emotion_glyph_has_accessible_text(direction):
    """WCAG 2.2 non-text content: each glyph needs a text equivalent, and
    it must read as emotional weather ('mood: …'), never a rating."""
    name, html = direction
    glyph_count = html.count('class="glyph"')
    mood_labels = re.findall(r'aria-label="mood:[^"]+"', html)
    assert glyph_count >= 4, f"{name}: expected ≥4 emotion glyphs, found {glyph_count}"
    assert len(mood_labels) >= glyph_count, (
        f"{name}: {glyph_count} glyphs but only {len(mood_labels)} "
        f"'mood:' aria-labels — every glyph needs its text equivalent"
    )


def test_spark_lines_carry_attribution(direction):
    name, html = direction
    assert "— their words" in html or "— Austin Chronicle" in html, (
        f"{name}: spark lines must carry source attribution"
    )
