"""The Chronicle desk's rows are its own /event doors, not a CSS card.

Founder, 2026-09-05: "Event identity for Austin Chronicle is not a CSS card.
List door: .../austin/EventSearch?sortType=date&v=g  Event door:
.../event/{slug}-{id}".

WHY THIS FILE EXISTS. The committed shape fixtures next door say of themselves:
"SYNTHETIC shape fixtures ... NOT a saved copy of any live page ... every
title, venue and date here is invented." The reader was green against those and
collapsed the real page: dry run 33989221309 read 40 live pages and returned
ONE row, keyed `url:https://www.austinchronicle.com` with eleven headlines
concatenated into its title and forty venues into its place.

So the markup below is not invented. Its SHAPE is what the desk's own bytes
showed a runner on 2026-09-05 (capture run 33989889096): each listing sits in
an `li` holding exactly one /event/ link, inside a `ul`/`div` wrapper holding
nine of them, inside a column holding ninety-one — and the wrapper classes
really do contain the word "event" (`fdn-event-promo-block`), which is why the
class tier matched a wrapper and swallowed the page. The URLs and titles are
the ones the desk served, verbatim from that run's digest, including the card
that links its image and its title to the SAME event.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.locale.desk_read import DeskReadError, read  # noqa: E402
from worker.locale.pack import load_pack  # noqa: E402

DOOR = "austin-chronicle-eventsearch"
BASE = "https://calendar.austinchronicle.com/austin/EventSearch?sortType=date&v=g"


@pytest.fixture()
def door():
    return {d.door_id: d for d in load_pack("us-tx-capcog").doors}[DOOR]


@pytest.fixture()
def do512_door():
    return {d.door_id: d for d in load_pack("us-tx-capcog").doors}["do512-today"]


#: The live page's shape, with the desk's own URLs and titles. The outer
#: wrappers carry "event" in their class exactly as the live page does.
LIVE_SHAPE = """
<div class="ev-grid-layout ev-clamp@m">
  <div class="ev-grid-col fdn-grid-main-single fdn-primary">
    <div class="ZoneA EventSearchDynamic uk-root fdn-margin-vert EventPromo">
      <div class="fdn-event-promo-block">
        <div class="fdn-event-promo-wrapper uk-position-relative">
          <ul class="uk-slider-items uk-child-width-1-2">
            <li>
              <a href="https://calendar.austinchronicle.com/event/boeing-boeing-14285657">Boeing Boeing</a>
              <div class="venue">Hyde Park Theatre 511 W. 43rd, Austin Midtown</div>
            </li>
            <li>
              <a href="https://calendar.austinchronicle.com/event/austin-film-festival-14316417">Austin Film Festival</a>
              <div class="venue">Galaxy Highland 10 6700 Middle Fiskville, Austin Midtown</div>
            </li>
            <li>
              <a href="https://calendar.austinchronicle.com/event/back-to-the-ranch-the-lbj-bbq-returns-14329073">Back To The Ranch: The LBJ BBQ Returns</a>
              <div class="venue">Lyndon B. Johnson National Historical Park 1048 Park Road #49, Stonewall</div>
            </li>
            <li>
              <a href="https://calendar.austinchronicle.com/event/come-from-away-14277307"><img src="/i/come-from-away.jpg"></a>
              <a href="https://calendar.austinchronicle.com/event/come-from-away-14277307">Come From Away</a>
              <div class="venue">Bass Concert Hall 2350 Robert Dedman, Austin Campus</div>
              <time datetime="2026-09-11">Fri, Sept 11</time>
            </li>
            <li>
              <a href="/event/gestures-of-care-14275737">Gestures of Care</a>
              <a href="https://www.austinchronicle.com">The Austin Chronicle</a>
              <div class="venue">Ivester Contemporary 916 Springdale #107, Austin East</div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</div>
"""


def test_the_live_page_becomes_one_row_per_listing_not_one_row(door):
    """The defect, pinned: 40 pages in, one blob out."""
    result = read(door, LIVE_SHAPE, base_url=BASE)
    assert len(result.rows) == 5, [r.title for r in result.rows]
    assert "HTML rows selected by the listing_link tier" in result.notes


def test_every_row_is_keyed_on_the_desks_own_event_door(door):
    result = read(door, LIVE_SHAPE, base_url=BASE)
    urls = [r.listing_url for r in result.rows]
    assert urls == [
        "https://calendar.austinchronicle.com/event/boeing-boeing-14285657",
        "https://calendar.austinchronicle.com/event/austin-film-festival-14316417",
        "https://calendar.austinchronicle.com/event/back-to-the-ranch-the-lbj-bbq-returns-14329073",
        "https://calendar.austinchronicle.com/event/come-from-away-14277307",
        "https://calendar.austinchronicle.com/event/gestures-of-care-14275737",
    ]
    # The news home is not a listing and must never become one — it is the key
    # the broken reader actually produced on the live desk.
    assert "https://www.austinchronicle.com" not in urls


def test_titles_are_the_listings_own_titles_not_a_page_of_headlines(door):
    result = read(door, LIVE_SHAPE, base_url=BASE)
    titles = [r.title for r in result.rows]
    assert titles == [
        "Boeing Boeing",
        "Austin Film Festival",
        "Back To The Ranch: The LBJ BBQ Returns",
        "Come From Away",
        "Gestures of Care",
    ]
    for title in titles:
        # The blob row concatenated eleven of these into one string.
        assert "Boeing Boeing Austin Film Festival" not in title


def test_a_card_linking_image_and_title_to_one_event_is_one_row(door):
    """Containment is counted in DISTINCT urls; counting anchors would return
    two half-rows for this card."""
    result = read(door, LIVE_SHAPE, base_url=BASE)
    come_from_away = [r for r in result.rows if r.title == "Come From Away"]
    assert len(come_from_away) == 1
    # And the whole card was claimed, so its venue and its date came with it.
    assert "Bass Concert Hall" in (come_from_away[0].place_text or "")
    assert come_from_away[0].when == "2026-09-11"


def test_the_listing_url_is_the_event_door_not_the_first_link_in_the_card(door):
    """The last card links the masthead as well. A row's identity is the door
    it was selected for, never whichever link the card prints first."""
    result = read(door, LIVE_SHAPE, base_url=BASE)
    row = [r for r in result.rows if r.title == "Gestures of Care"][0]
    assert row.listing_url == (
        "https://calendar.austinchronicle.com/event/gestures-of-care-14275737")


def test_each_row_carries_its_own_place_not_every_venue_on_the_page(door):
    result = read(door, LIVE_SHAPE, base_url=BASE)
    boeing = [r for r in result.rows if r.title == "Boeing Boeing"][0]
    assert boeing.place_text == "Hyde Park Theatre 511 W. 43rd, Austin Midtown"
    assert "Galaxy Highland" not in (boeing.place_text or "")


def test_a_door_that_declares_no_pattern_reads_exactly_as_before(do512_door):
    """The tier is opt-in per door: Do512 declares nothing, so nothing about
    its reading changes."""
    assert do512_door.listing_url_pattern is None
    page = """<div class="event-card"><h3>A Show</h3>
              <div class="venue">Mohawk</div></div>"""
    result = read(do512_door, page, base_url="https://do512.com/events/today")
    assert [r.title for r in result.rows] == ["A Show"]
    assert "HTML rows selected by the class tier" in result.notes


def test_a_page_with_no_matching_link_falls_through_to_the_older_tiers(door):
    """This tier never turns a readable page into an empty desk."""
    page = """<div class="event-card"><h3>Something Else</h3>
              <div class="venue">Somewhere</div></div>"""
    result = read(door, page, base_url=BASE)
    assert [r.title for r in result.rows] == ["Something Else"]
    assert "HTML rows selected by the class tier" in result.notes


def test_an_unusable_pattern_fails_loudly_rather_than_swallowing_the_page(door):
    from dataclasses import replace
    broken = replace(door, listing_url_pattern="event/[")
    with pytest.raises(DeskReadError):
        read(broken, LIVE_SHAPE, base_url=BASE)
