"""Tests for worker/segment.segment_events — the deterministic page -> per-event
block splitter that lets the UNCHANGED certified single-event extractor be run
once per event. Pure/local: no network, no AI, no DB.

Pins the five steps — (a) JSON-LD, (b) microdata, (c) a COMMITTED desk selector,
(d) line-initial date anchors, (e) the whole page — and the invariants that keep
them safe:
  - a 1-event page ALWAYS yields exactly 1 block == the whole original content
    (byte-identical to today's single-event path);
  - a repeated NON-event list (a nav menu, a product grid) is NOT over-segmented;
  - NOTHING splits a page on a class NAME it was not told about (2026-09-05).
"""
import os

import pytest

from worker.locale.kind_map import desk_selectors_for_door
from worker.segment import MAX_BLOCKS, segment_events

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "desk_pages")


# ---- (a)/(b) what the PAGE declares ------------------------------------------

def test_repeated_articles_each_dated_split_into_blocks():
    """Each listing opens its own line with its own date, so the ANCHOR split
    (d) separates them. It is not the `<article>` tag that does it: the bare
    structural strategies were deleted with the class guess (2026-09-05)."""
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
    """Same: dated lines, split by (d). A bare `<li>` is not a listing card."""
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


# ---- the guess that was deleted (2026-09-05) ---------------------------------
#
# Until this date, any <div>/<li>/<section> whose class CONTAINED "event",
# "card", "listing", "show", "gig" or "happening" opened a block. Substring, on
# every page in the world. These four tests are the founder's own examples and
# the first two FAIL on the commit before this one.

def test_product_tiles_are_not_events_even_when_they_mention_a_day():
    """A shop's product grid is `<div class="card">` and says "Monday" — the old
    substring guess turned it into three events, each costing one certified
    extraction call and each able to become a candidate row."""
    html = (
        '<div class="grid">'
        '<div class="card"><h3>Wide-brim sun hat</h3><p>$18 — restocked Monday</p></div>'
        '<div class="card"><h3>Enamel pin set</h3><p>$12 — ships Tuesday</p></div>'
        '<div class="card"><h3>Canvas tote</h3><p>$24 — new for August</p></div>'
        "</div>"
    )
    assert segment_events(html, content_type="text/html") == [html]


def test_showcase_listing_nav_and_eventual_are_not_cards():
    """Three class names that CONTAIN one of the old words and describe nothing
    that happens: `showcase` ⊃ show, `listing-nav` ⊃ listing, `eventual` ⊃
    event. Whole tokens are what a committed selector matches, so none of these
    is a card to anything now."""
    html = (
        '<section class="page">'
        '<div class="showcase"><h3>Our room</h3><p>Photos from last August</p></div>'
        '<div class="listing-nav"><h3>Browse by night</h3>'
        "<p>Sorted every Friday and Saturday</p></div>"
        '<div class="eventual"><h3>Coming later</h3><p>Plans for September</p></div>'
        "</section>"
    )
    assert segment_events(html, content_type="text/html") == [html]


def test_nav_tiles_with_no_dates_are_not_events():
    """The plain case, kept as a guard: no dates, no split, whole page."""
    html = (
        '<div class="cards">'
        '<div class="card">Shop</div><div class="card">About</div>'
        '<div class="card">Gift cards</div><div class="card">Contact</div>'
        "</div>"
    )
    assert segment_events(html, content_type="text/html") == [html]


# ---- (c) a card shape COMMITTED for one desk ---------------------------------

#: A desk page whose cards state their clock MID-LINE, so the anchor split (d)
#: cannot fire on it. Every assertion below is then about the selector alone.
DS_PAGE = (
    '<main class="ds-feed">'
    '<div class="ds-listing event-card"><h3>One</h3>'
    "<p>Doors at 8pm, Sat Sept 12</p></div>"
    '<div class="ds-listing event-card"><h3>Two</h3>'
    "<p>Doors at 9pm, Sat Sept 12</p></div>"
    '<nav class="ds-listing-nav">Next</nav>'
    "</main>"
)


def test_a_desk_with_no_selector_and_no_jsonld_gets_no_cards():
    """The founder's rule, verbatim: "If a desk has no selector and no JSON-LD,
    it uses (d) or (e). It does not get a guessed card." These cards even carry
    a real desk's class names — but nobody committed them FOR THIS PAGE's desk,
    so they are markup, not a declaration."""
    assert segment_events(DS_PAGE, content_type="text/html") == [DS_PAGE]


def test_a_committed_desk_selector_splits_that_desks_cards():
    blocks = segment_events(DS_PAGE, content_type="text/html",
                            desk_selectors=[("div", ["ds-listing", "event-card"])])
    assert len(blocks) == 2
    assert any("One" in b for b in blocks) and any("Two" in b for b in blocks)
    # The nav shares one token and is not a card.
    assert not any("Next" in b for b in blocks)


def test_every_class_token_in_a_selector_is_required():
    """A selector is a statement about one desk's card, not about one word."""
    html = (
        '<div><div class="ds-listing">One, doors at 8pm</div>'
        '<div class="ds-listing">Two, doors at 9pm</div></div>'
    )
    assert segment_events(html, content_type="text/html",
                          desk_selectors=[("div", ["ds-listing", "event-card"])]) == [html]


def test_a_selector_matches_whole_tokens_only():
    html = (
        '<div><div class="event-cards-off">One, doors at 8pm</div>'
        '<div class="event-cards-off">Two, doors at 9pm</div></div>'
    )
    assert segment_events(html, content_type="text/html",
                          desk_selectors=[("div", ["event-card"])]) == [html]


def test_a_selector_naming_the_wrong_tag_does_not_match():
    assert segment_events(DS_PAGE, content_type="text/html",
                          desk_selectors=[("li", ["ds-listing", "event-card"])]) == [DS_PAGE]


def test_a_selector_with_no_class_token_is_refused_loudly():
    """It would match every element of its tag — the guess with extra steps.
    Refused at load in the kind map, and refused here too, so a value handed in
    directly cannot do what the data file may not."""
    with pytest.raises(ValueError):
        segment_events(DS_PAGE, content_type="text/html", desk_selectors=[("div", [])])


def test_what_the_page_declares_outranks_the_desks_selector():
    """Order is (a) then (b) then (c): the page's own JSON-LD wins over a
    selector we committed about it."""
    html = (
        "<html><head><script type=\"application/ld+json\">"
        '[{"@type":"Event","name":"Declared One","startDate":"2026-09-12T20:00:00-05:00"},'
        '{"@type":"Event","name":"Declared Two","startDate":"2026-09-12T21:00:00-05:00"}]'
        "</script></head><body>" + DS_PAGE + "</body></html>"
    )
    blocks = segment_events(html, content_type="text/html",
                            desk_selectors=[("div", ["ds-listing", "event-card"])])
    assert len(blocks) == 2
    assert all("Declared" in b for b in blocks)


def test_a_presenters_own_page_types_its_cards_after_the_presenter():
    """The founder's 2026-09-04 ruling: an official presenter's own page is a
    trusted door and its per-item declaration is usable identity. Such a page
    types its cards `schema.org/Person`, not `.../Event` — until 2026-09-05 they
    were captured by the class guess, so the microdata step takes a second pass
    over items of ANY schema.org type rather than let the deletion drop a
    ratified behaviour. Still a DECLARATION by the page, never a class name."""
    html = (
        "<html><body><h1>Castle Creek — upcoming</h1>"
        '<article itemscope itemtype="https://schema.org/Person">'
        "<h2>Wren Hall</h2><p>Fri Aug 1, 8pm</p></article>"
        '<article itemscope itemtype="https://schema.org/Person">'
        "<h2>Tin Roof</h2><p>Sat Aug 2, 9pm</p></article>"
        "</body></html>"
    )
    blocks = segment_events(html, content_type="text/html")
    assert len(blocks) == 2
    assert any("Wren Hall" in b for b in blocks)
    assert any("Tin Roof" in b for b in blocks)


def test_the_second_microdata_pass_still_needs_a_dated_majority():
    """A shop's microdata Products with no dates are not listings. The bar that
    has always bounded the microdata path bounds the wider pass too."""
    html = (
        "<div>"
        '<div itemscope itemtype="https://schema.org/Product">Sun hat — $18</div>'
        '<div itemscope itemtype="https://schema.org/Product">Tote — $24</div>'
        '<div itemscope itemtype="https://schema.org/Product">Mug — $12</div>'
        "</div>"
    )
    assert segment_events(html, content_type="text/html") == [html]


def test_an_event_item_inside_a_page_level_item_is_still_found():
    """Order inside the microdata step: Event-typed items are captured FIRST, so
    a page wrapped in its own `schema.org/WebPage` item does not swallow them."""
    html = (
        '<body itemscope itemtype="https://schema.org/WebPage">'
        '<div itemscope itemtype="https://schema.org/MusicEvent">'
        "Fri 9/5 — Nova Line at The Grand</div>"
        '<div itemscope itemtype="https://schema.org/MusicEvent">'
        "Sat 9/6 — Slow Tide at The Grand</div>"
        "</body>"
    )
    blocks = segment_events(html, content_type="text/html")
    assert len(blocks) == 2
    assert not any("Nova Line" in b and "Slow Tide" in b for b in blocks)


def test_two_schema_org_events_on_one_page_are_two_blocks():
    """The founder's third case, stated in both spellings a page uses."""
    microdata = (
        "<div>"
        '<div itemscope itemtype="https://schema.org/MusicEvent">'
        "Fri 9/5 — Nova Line at The Grand</div>"
        '<div itemscope itemtype="https://schema.org/TheaterEvent">'
        "Sat 9/6 — Slow Tide at The Grand</div>"
        "</div>"
    )
    assert len(segment_events(microdata, content_type="text/html")) == 2
    jsonld = (
        "<html><head><script type=\"application/ld+json\">"
        '{"@context":"https://schema.org","@graph":['
        '{"@type":"Event","name":"Nova Line","startDate":"2026-09-05T20:00:00-05:00"},'
        '{"@type":"MusicEvent","name":"Slow Tide","startDate":"2026-09-06T20:00:00-05:00"}]}'
        "</script></head><body>Calendar</body></html>"
    )
    assert len(segment_events(jsonld, content_type="text/html")) == 2


# ---- the two desks we have walked --------------------------------------------
#
# These counts are the ones the committed shape fixtures produced BEFORE the
# guess was deleted (measured on the parent commit, 2026-09-05). They are
# FIXTURE counts, not live-desk counts: nobody here has loaded either desk
# (CONNECT 403 from this sandbox, 2026-09-04). Their job is to prove the
# deletion cost these two desks nothing.

@pytest.mark.parametrize("door,per_page", [
    ("austin-chronicle-eventsearch", [8, 7, 4]),
    ("do512-today", [7, 6, 5]),
])
def test_walked_desks_keep_the_block_counts_they_had_before_the_guess_died(door, per_page):
    selectors = desk_selectors_for_door(door)
    assert selectors, f"{door} has no committed listing selector"
    got = []
    for name in sorted(os.listdir(os.path.join(FIXTURES, door))):
        if not name.startswith("page-"):
            continue
        with open(os.path.join(FIXTURES, door, name), encoding="utf-8") as fh:
            page = fh.read()
        got.append(len(segment_events(page, content_type="text/html",
                                      desk_selectors=selectors)))
    assert got == per_page


@pytest.mark.parametrize("door,per_page", [
    ("austin-chronicle-eventsearch", [6, 6, 3]),
    ("do512-today", [6, 5, 5]),
])
def test_those_same_pages_without_their_selector_fall_to_the_anchor_split(door, per_page):
    """The counts above are EARNED by the committed selector, not inherited from
    the guess. Hand the same pages to no selector at all and step (d) reads what
    the TEXT states — fewer blocks, because a card whose date is not at the head
    of a line has no anchor to be cut at. Pinned so that deleting a selector can
    never look like a no-op."""
    got = []
    for name in sorted(os.listdir(os.path.join(FIXTURES, door))):
        if not name.startswith("page-"):
            continue
        with open(os.path.join(FIXTURES, door, name), encoding="utf-8") as fh:
            page = fh.read()
        got.append(len(segment_events(page, content_type="text/html")))
    assert got == per_page
    assert sum(got) < sum([8, 7, 4] if "chronicle" in door else [7, 6, 5])
