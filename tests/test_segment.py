"""Tests for worker/segment.segment_events — the deterministic page -> per-event
block splitter that lets the UNCHANGED certified single-event extractor be run
once per event. Pure/local: no network, no AI, no DB.

Pins the three heuristic tiers and the two invariants that keep it safe:
  - a 1-event page ALWAYS yields exactly 1 block == the whole original content
    (byte-identical to today's single-event path);
  - a repeated NON-event list (a nav menu) is NOT over-segmented.
"""
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


def test_html_blocks_carry_governing_date_header():
    # Founder 2026-08-05: "No one will post or announce [an] event with just a
    # time" — a calendar's day-header governs the listings under it, and
    # segmentation must not orphan it.
    html = """
    <html><body>
    <h2>Tuesday, August 5</h2>
    <ul>
    <li class="event-card">Discovery Day, 10:00 AM - 4:00 PM</li>
    <li class="event-card">Homeschool Day, 9:00 AM - 1:30 PM</li>
    </ul>
    <h2>Wednesday, August 6</h2>
    <ul>
    <li class="event-card">Star Party, 7:30 PM - 9:00 PM</li>
    <li class="event-card">Maker Night on August 6, 6:00 PM</li>
    </ul>
    </body></html>"""
    blocks = segment_events(html, content_type="text/html")
    assert blocks[0].startswith("Tuesday, August 5\n")
    assert blocks[1].startswith("Tuesday, August 5\n")
    assert blocks[2].startswith("Wednesday, August 6\n")
    # A block that already carries its own full date stays verbatim.
    assert blocks[3] == "Maker Night on August 6, 6:00 PM"


def test_text_blocks_carry_preceding_date_line():
    text = (
        "Saturday, August 8\n"
        "7:00 PM Doors - Night Owls on the patio\n"
        "9:30 PM Late set with the trio\n"
    )
    blocks = segment_events(text)
    dated = [b for b in blocks if "Night Owls" in b or "Late set" in b]
    assert all(b.startswith("Saturday, August 8\n") for b in dated)
