"""Tests for worker/segment.segment_events — the deterministic page -> per-event
block splitter that lets the UNCHANGED certified single-event extractor be run
once per event. Pure/local: no network, no AI, no DB.

Pins the three heuristic tiers and the two invariants that keep it safe:
  - a 1-event page ALWAYS yields exactly 1 block == the whole original content
    (byte-identical to today's single-event path);
  - a repeated NON-event list (a nav menu) is NOT over-segmented.
"""
import logging

from worker import segment
from worker.segment import MAX_BLOCKS, segment_events


# ---- (a) HTML with repeated dated items --------------------------------------

def test_repeated_articles_each_dated_split_into_blocks():
    html = """
    <div class="calendar">
      <article class="event">Fri Aug 1, 8pm — Castle Creek at Mohawk. tix https://t.example/cc</article>
      <article class="event">Sat Aug 2, 9pm — River Delta at Cedar Hall.</article>
      <article class="event">Sun Aug 3, 7pm — Tin Sparrow at Parlor.</article>
    </div>
    """
    blocks = segment_events(html, content_type="text/html")
    assert len(blocks) == 3
    assert any("Castle Creek" in b and "Mohawk" in b for b in blocks)
    assert any("River Delta" in b and "Cedar Hall" in b for b in blocks)
    # Isolation: no block carries another block's venue.
    castle = next(b for b in blocks if "Castle Creek" in b)
    assert "Cedar Hall" not in castle and "Parlor" not in castle


def test_repeated_list_items_each_dated_split():
    html = (
        "<ul><li>Mon 7/1 8pm Aurora Skye</li>"
        "<li>Tue 7/2 8pm Blue Harbor</li>"
        "<li>Wed 7/3 9pm Copper Field</li></ul>"
    )
    blocks = segment_events(html)
    assert len(blocks) == 3


def test_schema_org_microdata_events_split():
    html = """
    <div>
      <div itemscope itemtype="https://schema.org/MusicEvent">
        Fri 9/5 — Nova Line at The Grand
      </div>
      <div itemscope itemtype="https://schema.org/Event">
        Sat 9/6 — Slow Tide at The Grand
      </div>
    </div>
    """
    blocks = segment_events(html)
    assert len(blocks) == 2
    assert any("Nova Line" in b for b in blocks)
    assert any("Slow Tide" in b for b in blocks)


def test_nav_menu_list_is_not_oversegmented():
    """A repeated <li> list with NO dates is a menu, not a calendar — it must
    fall back to a single whole-content block, never fabricate events."""
    html = "<ul><li>Home</li><li>About</li><li>Shows</li><li>Contact</li></ul>"
    blocks = segment_events(html)
    assert blocks == [html]


# ---- (b) plain text with date anchors ----------------------------------------

def test_plain_text_date_anchors_split():
    text = (
        "Mohawk Austin — August shows\n"
        "Fri 8/1 8pm — Castle Creek\n"
        "Sat 8/2 9pm — River Delta\n"
        "Sun 8/3 7pm — Tin Sparrow\n"
    )
    blocks = segment_events(text)
    assert len(blocks) == 3
    # The shared preamble rides with the FIRST event, not dropped.
    assert "Mohawk Austin" in blocks[0]
    assert "Castle Creek" in blocks[0]
    assert "River Delta" in blocks[1]
    assert "Tin Sparrow" in blocks[2]
    # No cross-leak between later blocks.
    assert "Castle Creek" not in blocks[1]


def test_plain_text_weekday_anchors_split():
    text = (
        "Thursday: The Larks live at Sunset Room\n"
        "Friday: Ember & Ash at Sunset Room\n"
    )
    blocks = segment_events(text)
    assert len(blocks) == 2


# ---- (c) single-event / fallback: exactly 1 whole-content block --------------

def test_single_event_text_is_one_block_unchanged():
    text = "Night Show at Mohawk on Fri 8/1, 8pm. Castle Creek headlines."
    blocks = segment_events(text)
    assert blocks == [text]


def test_single_event_html_returns_whole_original():
    html = "<div class='event'>Only Show — Fri 8/1 8pm at Mohawk, Castle Creek</div>"
    blocks = segment_events(html)
    # One dated item is not a repeated set -> fall back to the whole content.
    assert blocks == [html]


def test_empty_and_whitespace_pages():
    assert segment_events("") == [""]
    assert segment_events("   \n\t ") == ["   \n\t "]
    assert segment_events(None) == []


def test_block_cap_is_enforced():
    text = "\n".join(f"Aug {i} 8pm — Act {i}" for i in range(1, MAX_BLOCKS + 50))
    blocks = segment_events(text)
    assert len(blocks) == MAX_BLOCKS


def test_no_fabrication_block_text_is_substring_of_source():
    """Every returned block must be text drawn from the source — never
    invented. (Whitespace is normalized, so compare on collapsed tokens.)"""
    text = (
        "Fri 8/1 8pm — Castle Creek\n"
        "Sat 8/2 9pm — River Delta\n"
    )
    for b in segment_events(text):
        for token in b.split():
            assert token in text


# ── the runaway guard must not be the work bound (2026-07-26) ───────────────
# Live run 30216970817 logged "495 blocks exceeds MAX_BLOCKS=200; truncating"
# on a real venue calendar. Segmentation dropped 295 events SILENTLY, before
# worker/ai_extract.py's accounted per-page cap (which DEFERS, R-043) ever
# ran. Segmentation makes no AI call, so the tight bound bought no spend
# safety — it only lost data, and lost most of it on the richest sources.

def test_the_block_guard_sits_far_above_a_real_calendar():
    """A 495-block page must survive segmentation intact so the CALLER's
    accounted cap can defer the overflow instead of it being dropped."""
    from worker.segment import MAX_BLOCKS
    assert MAX_BLOCKS >= 1000, (
        "MAX_BLOCKS is a runaway guard, not a work bound — the per-page "
        "extraction cap governs per-run work and DEFERS its overflow. A low "
        "guard silently drops the tail of large calendars.")


def test_over_guard_is_reported_as_DROPPED_not_as_deferred(caplog):
    """The wording matters: this path loses data permanently, unlike the
    caller's cap. It must not read like the recoverable case."""
    import logging

    from worker.segment import MAX_BLOCKS, _cap

    blocks = [f"event block {i} with enough text to count" for i in range(MAX_BLOCKS + 5)]
    with caplog.at_level(logging.ERROR, logger="worker.segment"):
        kept = _cap(blocks)
    assert len(kept) == MAX_BLOCKS
    msg = caplog.text
    assert "DROPPED" in msg and "not deferred" in msg
    assert "recoverable" in msg


def test_under_the_guard_nothing_is_dropped_or_logged(caplog):
    import logging

    from worker.segment import _cap

    blocks = [f"block {i}" for i in range(50)]
    with caplog.at_level(logging.WARNING, logger="worker.segment"):
        assert _cap(blocks) == blocks
    assert caplog.text == ""


# ── Per-block PROMPT-SIZE bound (MAX_BLOCK_CHARS) ────────────────────────────
# #73 r21 blocker, and the lens was right: the three r20 tests covered only the
# block-COUNT runaway guard, so raising MAX_BLOCK_CHARS from 40_000 to 10_000_000
# left all 14 of them green (mutation-verified before writing these). The
# per-block ceiling is the half that actually fixes the live
# "prompt is too long: 1092868 tokens > 1000000 maximum" failure, and it had no
# test at all. These bind it through the PUBLIC entry point so the property is
# asserted on what callers get, not on a helper's internals.

def _oversized_page(paragraphs: int = 400, para_chars: int = 500) -> str:
    """A no-anchor page far over the ceiling, built from real paragraph seams so
    the paragraph-boundary path (not just the hard-split fallback) is exercised."""
    return "\n\n".join(
        f"Event {i}: doors 8pm at the venue. " + ("filler text " * (para_chars // 12))
        for i in range(paragraphs)
    )


def test_no_returned_block_ever_exceeds_the_prompt_size_ceiling():
    """THE property. Fails if MAX_BLOCK_CHARS is raised, if _split_oversized is
    removed, or if a call site stops routing through it."""
    page = _oversized_page()
    assert len(page) > segment.MAX_BLOCK_CHARS * 3, "fixture must exceed the ceiling"
    blocks = segment.segment_events(page)
    assert blocks, "an oversized page must still yield blocks"
    oversized = [len(b) for b in blocks if len(b) > segment.MAX_BLOCK_CHARS]
    assert not oversized, (
        f"{len(oversized)} block(s) exceed MAX_BLOCK_CHARS="
        f"{segment.MAX_BLOCK_CHARS}: {oversized} — an over-ceiling block fails "
        "the provider outright, which is the exact live failure this bound fixes"
    )


def test_splitting_preserves_every_event_line_rather_than_truncating():
    """Truncation is the data-loss class this module already had once. Every
    paragraph's identifying text must survive somewhere in the output."""
    page = _oversized_page(paragraphs=300)
    blocks = segment.segment_events(page)
    joined = "\n\n".join(blocks)
    missing = [i for i in range(300) if f"Event {i}:" not in joined]
    assert not missing, (
        f"{len(missing)} event line(s) lost by splitting (first few: "
        f"{missing[:5]}) — splitting must never drop content")


def test_a_single_paragraph_over_the_ceiling_is_hard_split_not_dropped():
    """The `while` fallback: one paragraph with no internal seam still has to be
    bounded, and its content still has to survive."""
    marker = "UNIQUEMARKER-END-OF-GIANT-PARAGRAPH"
    page = ("a" * (segment.MAX_BLOCK_CHARS * 2 + 500)) + marker
    blocks = segment.segment_events(page)
    assert blocks
    assert all(len(b) <= segment.MAX_BLOCK_CHARS for b in blocks), (
        "a seamless oversized paragraph must be hard-split, not passed through")
    assert any(marker in b for b in blocks), (
        "the tail of a hard-split paragraph must survive — better a seam "
        "mid-paragraph than a lost event")


def test_content_under_the_ceiling_is_not_split_at_all():
    """The bound must not fire on ordinary pages — a spurious split would
    multiply AI calls against the accounted per-page cap."""
    page = "\n\n".join(f"Event {i}: doors 8pm." for i in range(5))
    assert len(page) < segment.MAX_BLOCK_CHARS
    before = segment.segment_events(page)
    assert before == segment._split_oversized(before), (
        "under-ceiling blocks must pass through _split_oversized unchanged")


def test_the_split_is_logged_with_a_count_never_an_unqualified_claim(caplog):
    """The log line is operator-facing evidence (it is what proved this fix live
    in run 30218828785), so it must state the resulting block count and must not
    claim 'nothing dropped' when a seam fragment was in fact shed."""
    with caplog.at_level(logging.WARNING, logger="worker.segment"):
        segment.segment_events(_oversized_page(paragraphs=200))
    split_lines = [r.getMessage() for r in caplog.records
                   if "exceeds MAX_BLOCK_CHARS" in r.getMessage()]
    assert split_lines, "an over-ceiling split must be logged, never silent"
    for line in split_lines:
        assert "SPLIT into" in line
        assert "truncat" not in line.lower(), (
            "the split path must never describe itself as truncation")

    # And the precise-claim half: a shed fragment is REPORTED, not glossed.
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="worker.segment"):
        segment._split_oversized(["z" * (segment.MAX_BLOCK_CHARS + 3)])
    shed_lines = [r.getMessage() for r in caplog.records
                  if "exceeds MAX_BLOCK_CHARS" in r.getMessage()]
    assert shed_lines
    assert "seam fragment(s) shed" in shed_lines[0], (
        "when a sub-minimum fragment is discarded the log must say so with a "
        f"count; got: {shed_lines[0]!r}")
