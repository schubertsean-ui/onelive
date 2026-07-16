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
    # Checked against VISIBLE text (round-5 nit): copy hidden in comments
    # or header prose must not satisfy canon-copy requirements.
    name, html = direction
    text = _visible_text(html)
    for phrase in REQUIRED_VERBATIM:
        assert phrase in text, f"{name}: verbatim canon copy missing from visible text: {phrase!r}"


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
    # Stated rule (round 4 nit): ICONOGRAPHY is SVG-only; plain typographic
    # marks (▸ ← ↗ › · —) are punctuation, not icons — they sit outside the
    # emoji ranges below and are deliberately permitted.
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
    assert sheets, f"{name}: no sheet bodies found"
    corroboration_sheets = [s for s in sheets if "double-check" in s]
    assert corroboration_sheets, f"{name}: no uncertainty (corroboration) sheets found"
    for sheet in corroboration_sheets:
        hrefs = re.findall(r'href="([^"]*)"', sheet)
        assert hrefs, f"{name}: uncertainty sheet has no venue link at all"
        for href in hrefs:
            assert re.match(r"^https://", href), (
                f"{name}: uncertainty-sheet venue link must be a real "
                f"absolute URL, got {href!r}"
            )
    # No sheet of any kind may contain a dead anchor.
    for sheet in sheets:
        assert 'href="#"' not in sheet, f"{name}: dead anchor inside a trust sheet"


VOID_ELEMENTS = {"meta", "br", "img", "input", "hr", "link", "path", "circle"}


def test_html_is_well_formed(direction):
    """Parser-based structural validity (round 7: the malformed SETLIST
    button proved regex assertions can bless broken DOM). Every non-void
    open tag must be closed by ITS OWN tag name, properly nested."""
    from html.parser import HTMLParser

    name, html = direction

    class BalanceChecker(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack: list[tuple[str, int]] = []
            self.errors: list[str] = []

        def handle_starttag(self, tag, attrs):
            if tag not in VOID_ELEMENTS:
                self.stack.append((tag, self.getpos()[0]))

        def handle_startendtag(self, tag, attrs):
            pass  # self-closing (svg primitives) — nothing to balance

        def handle_endtag(self, tag):
            if tag in VOID_ELEMENTS:
                return
            if not self.stack:
                self.errors.append(f"line {self.getpos()[0]}: </{tag}> with nothing open")
                return
            open_tag, open_line = self.stack.pop()
            if open_tag != tag:
                self.errors.append(
                    f"line {self.getpos()[0]}: </{tag}> closes <{open_tag}> "
                    f"opened at line {open_line} — malformed markup"
                )

    checker = BalanceChecker()
    checker.feed(html)
    leftovers = [f"<{t}> (line {l}) never closed" for t, l in checker.stack if t != "html"]
    assert not checker.errors and not leftovers, (
        f"{name}: malformed HTML: {checker.errors + leftovers}"
    )


def test_no_dead_anchors_or_false_affordances_anywhere(direction):
    """Rounds 6–7: the bar is global and semantic. Zero href="#"; zero fake
    ARIA roles; zero control-styled spans — every visible affordance is
    backed by a real element: <button type="button">, <a href="https…"> or
    an intra-document <a href="#…">, <input>, or <details>."""
    name, html = direction
    assert 'href="#"' not in html, f"{name}: dead anchor present"
    for fake_role in ('role="button"', 'role="tab"', 'role="navigation"',
                      'role="link"', 'role="tablist"', 'role="searchbox"'):
        assert fake_role not in html, (
            f"{name}: {fake_role} — ARIA roles may not claim semantics the "
            f"element doesn't actually have (role=group/img are the only "
            f"sanctioned non-implicit roles in these comps)"
        )
    for cls in ("tab", "grail", "fopt", "apply", "clear", "d-btn", "play-btn",
                "filter-entry", "open-hint", "link", "search", "back"):
        assert not re.search(rf'<(span|div) class="{cls}[" ]', html), (
            f"{name}: affordance class {cls!r} on a dead <span>/<div> — must "
            f"be a real button/anchor/input"
        )
    # every button is explicitly type=button (no accidental submit at Step 9)
    untyped = re.findall(r"<button (?![^>]*type=)", html)
    assert not untyped, f"{name}: {len(untyped)} button(s) missing type=\"button\""
    # 'Details ›' and '← Tonight' must be real links navigating to real ids
    hints = re.findall(r'<a class="open-hint" href="(#[a-z-]+)"', html)
    assert len(hints) >= 4, f"{name}: card navigation must be real anchors"
    backs = re.findall(r'<a class="back" href="(#[a-z-]+)"', html)
    assert backs, f"{name}: back affordance must be a real anchor"
    for target in set(hints + backs):
        assert f'id="{target[1:]}"' in html, (
            f"{name}: navigation targets {target} but no such id exists"
        )
    # search is a real input; every ↗ outbound affordance is a real https link
    assert '<input class="search" type="search"' in html, f"{name}: search is not an <input>"
    for m in re.finditer(r"<(\w+)[^>]*>[^<]*↗", html):
        assert m.group(1) == "a", f"{name}: ↗ affordance on <{m.group(1)}>, not an anchor"


def test_nearby_chips_are_working_deep_links(direction):
    """Founder directive 2026-07-15 ('Make this happen: Nearby'), Tier 1 of
    docs/memory/decisions/2026-07-15_nearby-tiered-data-source.md: the
    Nearby chips are real maps deep links anchored to the venue address,
    and 'More venues' routes to OneLive's own feed."""
    name, html = direction
    maps_links = re.findall(
        r'<a class="fopt" href="(https://www\.google\.com/maps/search/[^"]+)"', html
    )
    assert len(maps_links) >= 3, (
        f"{name}: Nearby needs ≥3 working maps deep links, found {len(maps_links)}"
    )
    for href in maps_links:
        assert "near" in href and "Austin" in href, (
            f"{name}: nearby link not anchored to the venue address: {href}"
        )
    assert '<a class="fopt" href="#tonight-feed">More venues tonight</a>' in html, (
        f"{name}: 'More venues' must route to OneLive's own feed"
    )


def test_touch_targets_meet_44px_claim(direction):
    """Round 10: the comps claim ≥44px touch targets; the suite must be
    able to fail on a undersized control. Static check: every interactive
    class's CSS rule must declare min-height (or fixed size) ≥44px."""
    name, html = direction
    css = re.search(r"<style\b.*?</style>", html, flags=re.S).group(0)
    interactive = ["tab", "grail", "fopt", "apply", "clear", "d-btn",
                   "hear", "sample", "back", "filter-entry", "search"]
    for cls in interactive:
        rules = re.findall(rf"[.\w]*\.{cls}\{{([^}}]*)\}}", css)
        assert rules, f"{name}: no CSS rule found for interactive class .{cls}"
        sized = any(
            re.search(r"min-height:\s*(4[4-9]|[5-9]\d)px", r) or
            re.search(r"height:\s*(4[4-9]|[5-9]\d)px", r)
            for r in rules
        )
        assert sized, f"{name}: .{cls} has no ≥44px target sizing — claim violated"
    # play button + quiet-icon summary are sized via explicit width/height
    assert re.search(r"\.play-btn\{[^}]*width:44px;height:44px", css), (
        f"{name}: play button not 44px"
    )
    assert re.search(r"details\.quiet>summary\{[^}]*width:44px;height:44px", css), (
        f"{name}: uncertainty icon summary not 44px"
    )
    # open-hint links get a 44px hit area
    assert re.search(r"a\.open-hint\{[^}]*min-height:44px", css), (
        f"{name}: Details › link lacks 44px hit area"
    )


def test_fixture_labeling_visible_in_frames(direction):
    """Round 6 nit: real venues + fictional artists must be labeled as
    fixture content inside the frames, not only in README prose."""
    name, html = direction
    assert _visible_text(html).count("fixture data") >= 3, (
        f"{name}: every screen frame must carry a visible fixture-data label"
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
    """Attributions must be honest: the artist's own words, the tier-C
    machine-draft mark, or a CLEARLY-fictional fixture critic. Attributing
    invented copy to a real outlet is fabricated provenance (evaluator
    round 5) — the same defect class as a fake corroboration link."""
    name, html = direction
    assert "— their words" in html, f"{name}: artist-own-words attribution missing"
    text = _visible_text(html)
    for real_outlet in ("Austin Chronicle", "Chronicle", "Statesman", "KUTX"):
        assert real_outlet not in text, (
            f"{name}: real outlet {real_outlet!r} attributed for fixture "
            f"content — fabricated provenance is banned even in comps"
        )
    critic_attrs = re.findall(r"— a local critic \(fixture\)", html)
    assert critic_attrs, (
        f"{name}: the named-critic spark-line pattern must be demonstrated "
        f"with a clearly-fictional attribution"
    )


def test_something_off_is_a_real_control_not_a_dead_anchor(direction):
    """'Something off?' is the correction/dispute entry point — a trust
    affordance, not a utility link. It must never be a dead anchor
    (evaluator round 5)."""
    name, html = direction
    assert 'class="something-off" href="#"' not in html and not re.search(
        r'<a[^>]*href="#"[^>]*>\s*Something off\?', html
    ), f"{name}: 'Something off?' is a dead anchor — trust paths don't stub"
    wraps = re.findall(
        r'<details class="sheet something-off-wrap">.*?</details>', html, flags=re.S
    )
    assert wraps, f"{name}: 'Something off?' must be an operable disclosure control"
    for w in wraps:
        assert "sheet-body" in w and "human" in w, (
            f"{name}: correction sheet must explain the human-review path"
        )
