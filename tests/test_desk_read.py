"""read(public_desk) — a desk row exists because a desk printed it.

The rules under test are the founder's three: `when` only if the page states it,
unknown kind = other, via = desk. Plus the gate this path REPLACES: a happening
must not need an identity, or a clock, in order to exist (ONE-LIVE-TRUST.md).
"""
from __future__ import annotations

import os
from dataclasses import replace

import pytest

from worker.importers.structured_feed import normalize_structured, parse_jsonld
from worker.locale import pack as lp
from worker.locale.desk_read import DeskReadError, Happening, read

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "locale_desks")
CAPCOG = "us-tx-capcog"


def fixture(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def doors():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}


@pytest.fixture()
def desk(doors):
    return doors["austin-chronicle-eventsearch"]


# --- the four page shapes read ----------------------------------------------

def test_a_desk_list_yields_one_row_per_listing(desk):
    result = read(desk, fixture("desk_listing.html"))
    titles = [r.title for r in result.rows]
    assert titles == [
        "Hot Luck Block Party",
        "Blanton Late Night",
        "East Side Artisan Market",
        "County Line Fiddle Contest",
        "Lockhart Lecture Series: Caldwell County Water",
    ]
    assert result.skipped_untitled == 0


def test_a_json_ld_calendar_is_read_through_the_repos_one_json_ld_parser(doors):
    result = read(doors["ut-austin-localist"], fixture("civic_jsonld.html"))
    assert [r.title for r in result.rows] == [
        "Open Rehearsal: Wind Ensemble",
        "Public Lecture: Groundwater in the Hill Country",
        "Farmers Market on the Plaza",
    ]


def test_a_microdata_marketplace_page_is_read(doors):
    result = read(doors["do512-today"], fixture("marketplace_microdata.html"))
    assert [r.title for r in result.rows] == [
        "Sun June at Mohawk", "Trivia Night", "Late Show Improv"]


def test_an_official_list_of_dated_items_is_read(doors):
    result = read(doors["visit-austin-events"], fixture("official_list.html"))
    assert result.count == 4
    assert result.dated == 4


def test_a_wrapper_div_does_not_swallow_the_listings(desk):
    """The listings sit inside `<div class="results">`; an outermost-wins reader
    returns that wrapper as ONE row. Five rows means the tiers still see them."""
    assert read(desk, fixture("desk_listing.html")).count == 5


# --- no invented dates -------------------------------------------------------

def test_a_machine_date_is_taken_verbatim_from_the_pages_own_attribute(desk):
    row = read(desk, fixture("desk_listing.html")).rows[0]
    assert row.when == "2026-09-05T18:00"
    assert row.when_precision == "datetime"


def test_a_date_with_no_clock_stays_a_date_and_is_not_given_a_time(desk):
    row = read(desk, fixture("desk_listing.html")).rows[1]
    assert row.when == "2026-09-11"
    assert row.when_precision == "date"


def test_prose_is_carried_as_text_and_never_parsed_into_an_instant(desk):
    row = read(desk, fixture("desk_listing.html")).rows[2]
    assert row.when is None, "\"Every Sunday this fall\" is not a date we may state"
    assert row.when_text == "Every Sunday this fall"
    assert row.when_precision is None


def test_a_listing_with_no_date_at_all_still_exists(desk):
    row = read(desk, fixture("desk_listing.html")).rows[3]
    assert row.title == "County Line Fiddle Contest"
    assert row.when is None and row.when_text is None


def test_a_json_ld_event_with_no_start_date_still_exists(doors):
    result = read(doors["ut-austin-localist"], fixture("civic_jsonld.html"))
    undated = [r for r in result.rows if r.when is None]
    assert [r.title for r in undated] == ["Farmers Market on the Plaza"]


def test_a_non_iso_datetime_attribute_is_not_coerced(doors, tmp_path):
    # The `<ul class="calendar">` is this door's COMMITTED listing selector
    # (its locale-pack row). Before the split law a bare `<ul><li>` split too,
    # by a "row-shaped tag containing a <time>" guess — that guess is gone, and
    # a page declaring no identity is now `unsplit` with zero rows
    # (ONE-LIVE-ENTITY-SPLIT-LAW.md §2). Nothing about the DATE rule changed.
    html = ('<ul class="calendar"><li><time datetime="next friday">Next Friday</time> '
            'Porch Concert</li></ul>')
    row = read(doors["visit-austin-events"], html).rows[0]
    assert row.when is None
    assert row.when_text == "Next Friday"


# --- existence never waits on an identity (the gate this path replaces) ------

def test_a_row_with_no_address_of_its_own_still_exists(doors):
    result = read(doors["visit-austin-events"], fixture("official_list.html"))
    assert all(r.listing_url is None for r in result.rows)
    assert result.count == 4


def test_a_row_that_states_its_own_address_records_it_without_requiring_it(desk):
    row = read(desk, fixture("desk_listing.html")).rows[0]
    assert row.listing_url.endswith("/e/12841/hot-luck-block-party")


def test_the_licensed_normalizer_would_delete_a_row_this_path_keeps():
    """The concrete gate replaced (ticket item 4).

    `normalize_structured` "Returns None when there is no stable id or no
    title" — for an event stating neither a uid/url nor a start, that None is an
    EXISTENCE answer given by an IDENTITY test, which ONE-LIVE-TRUST.md forbids.
    The desk path reuses the PARSER and stops before the normalizer.
    """
    html = fixture("civic_jsonld.html")
    parsed = parse_jsonld(html)
    undated = [e for e in parsed if not e.get("start_time")]
    assert undated, "fixture must contain an event stating no start"
    for raw in undated:
        assert normalize_structured(
            raw, provider="jsonld", source_name="desk") is None, (
            "this test is meaningless if the normalizer keeps the row")


def test_the_desk_path_keeps_exactly_that_row(doors):
    result = read(doors["ut-austin-localist"], fixture("civic_jsonld.html"))
    kept = [r.title for r in result.rows if r.when is None]
    assert "Farmers Market on the Plaza" in kept


# --- kind, via, locale -------------------------------------------------------

def test_a_general_desk_states_no_kind_so_its_rows_are_other(desk):
    assert {r.kind for r in read(desk, fixture("desk_listing.html")).rows} == {
        lp.KIND_OTHER}


def test_a_single_kind_door_states_that_kind_for_its_rows(doors):
    # Read through a page that declares its own identities (JSON-LD), because a
    # listing SELECTOR is committed per door and this door commits none — the
    # split law will not let one desk's selector colour another desk's pages.
    rows = read(doors["kutx-concert-calendar"], fixture("civic_jsonld.html")).rows
    assert rows and {r.kind for r in rows} == {"music"}


def test_kind_is_never_read_out_of_a_title(desk):
    """The fixture names a lecture and a market; a general desk still says
    `other`, because guessing a category from a title weights categories."""
    rows = read(desk, fixture("desk_listing.html")).rows
    lecture = next(r for r in rows if "Lecture" in r.title)
    market = next(r for r in rows if "Market" in r.title)
    assert lecture.kind == lp.KIND_OTHER and market.kind == lp.KIND_OTHER


def test_via_is_the_desk_and_the_locale_rides_along(desk):
    for row in read(desk, fixture("desk_listing.html")).rows:
        assert row.via == desk.via == "Austin Chronicle"
        assert row.door_id == desk.door_id
        assert row.locale_id == CAPCOG
        assert row.source_url == desk.url


def test_place_text_is_the_text_the_page_printed(desk):
    row = read(desk, fixture("desk_listing.html")).rows[0]
    assert row.place_text == "Fair Market, 1100 E 5th St"


# --- the door gate, and honest emptiness ------------------------------------

@pytest.mark.parametrize("door_id", ["facebook-events", "instagram-venue-posts",
                                     "nextdoor-austin"])
def test_a_wall_is_never_read(doors, door_id):
    with pytest.raises(DeskReadError) as exc:
        read(doors[door_id], "<html>anything</html>")
    assert doors[door_id].door_id in str(exc.value)


def test_a_copy_farm_is_never_read_as_a_listing(doors):
    with pytest.raises(DeskReadError):
        read(doors["allevents-austin"], fixture("desk_listing.html"))


def test_a_credentialed_marketplace_is_not_read_as_a_public_desk(doors):
    with pytest.raises(DeskReadError) as exc:
        read(doors["ticketmaster-discovery"], "<html></html>")
    assert "api_key" in str(exc.value)


def test_an_empty_body_reports_nothing_read_rather_than_nothing_on(desk):
    result = read(desk, "")
    assert result.count == 0
    assert any("not 'nothing on'" in n for n in result.notes)


def test_a_page_with_no_listings_yields_no_rows_and_does_not_raise(desk):
    result = read(desk, "<html><body><p>Closed for the season.</p></body></html>")
    assert result.rows == []


def test_the_same_event_in_json_ld_and_html_is_returned_once(doors):
    html = (
        '<html><head><script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Event","name":"Porch Concert",'
        '"startDate":"2026-09-05T19:00:00Z"}'
        '</script></head><body><ul><li class="event">'
        '<h3>Porch Concert</h3><time datetime="2026-09-05T19:00:00Z">Sep 5</time>'
        '</li></ul></body></html>')
    result = read(doors["visit-austin-events"], html)
    assert [r.title for r in result.rows] == ["Porch Concert"]


def test_a_read_returns_happening_rows(desk):
    result = read(desk, fixture("desk_listing.html"))
    assert all(isinstance(r, Happening) for r in result.rows)
    assert result.count == len(result.rows)


def test_read_refuses_anything_that_is_not_a_door(desk):
    with pytest.raises(DeskReadError):
        read("austin-chronicle-eventsearch", "<html></html>")


# --- the card's own category, mapped into OUR kinds --------------------------
# (Session Contract #62 — the founder's "kind mapped from THEIR category or
# other". The mapping is data; these tests pin what the READER does with it.)

def test_a_heading_outranks_a_cards_other_anchors_for_the_title(desk):
    """A card's category link is an anchor too. Reading anchors first
    concatenated the category onto the title ("Brass Band Live Music")."""
    html = ('<div class="event"><h3><a href="/e/1">Brass Band</a></h3>'
            '<a rel="category tag" href="/s?section=music">Live Music</a></div>')
    result = read(desk, html, base_url="https://desk.example/list")
    assert [r.title for r in result.rows] == ["Brass Band"]


def test_a_stated_category_decides_the_kind(desk):
    from worker.locale.kind_map import load_kind_map
    html = ('<div class="event"><h3><a href="/e/1">Brass Band</a></h3>'
            '<a rel="category tag" href="/s?section=music">Live Music</a></div>')
    result = read(desk, html, base_url="https://desk.example/list",
                  kind_map=load_kind_map("austin-chronicle"))
    row = result.rows[0]
    assert (row.kind, row.kind_source, row.category_text) == (
        "music", "desk_category", "Live Music")


def test_an_unmapped_category_leaves_the_kind_alone_and_is_reported(desk):
    from worker.locale.kind_map import load_kind_map
    html = ('<div class="event"><h3><a href="/e/1">A Happening</a></h3>'
            '<a rel="category tag" href="/s?section=x">Psychogeography</a></div>')
    result = read(desk, html, base_url="https://desk.example/list",
                  kind_map=load_kind_map("austin-chronicle"))
    row = result.rows[0]
    assert (row.kind, row.kind_source, row.category_text) == ("other", "default", None)
    assert result.unmapped_categories == ["Psychogeography"]


def test_a_kind_is_never_read_out_of_a_title(desk):
    from worker.locale.kind_map import load_kind_map
    html = ('<div class="event"><h3><a href="/e/1">Comedy Night: Live Music '
            'Farmers Market</a></h3></div>')
    result = read(desk, html, base_url="https://desk.example/list",
                  kind_map=load_kind_map("austin-chronicle"))
    assert result.rows[0].kind == "other"


def test_a_mapping_for_another_door_is_refused_with_a_note(doors):
    from worker.locale.kind_map import load_kind_map
    other = doors["ut-austin-localist"]
    result = read(other, fixture("civic_jsonld.html"),
                  kind_map=load_kind_map("austin-chronicle"))
    assert all(r.kind_source != "desk_category" for r in result.rows)
    assert any("does not claim this door" in n for n in result.notes)


def test_one_card_read_two_ways_is_one_row(desk):
    """A desk states a listing in JSON-LD and prints it in HTML. The two
    readings disagree on the FORM of the date; keying on the date text split one
    card into two rows and inflated every count downstream."""
    html = (
        '<html><head><script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Event","name":"One Card",'
        '"startDate":"2026-09-11T20:00:00-05:00","url":"https://desk.example/e/1"}'
        '</script></head><body>'
        '<div class="event"><h3><a href="https://desk.example/e/1">One Card</a></h3>'
        '<span class="venue">Shape Hall</span>'
        '<a rel="category tag" href="/s?section=music">Live Music</a></div>'
        '</body></html>')
    from worker.locale.kind_map import load_kind_map
    result = read(desk, html, base_url="https://desk.example/list",
                  kind_map=load_kind_map("austin-chronicle"))
    assert result.count == 1 and result.merged_readings == 1
    row = result.rows[0]
    # The structured reading's instant AND the printed reading's category and
    # venue end up on one row — holes filled, nothing overwritten.
    assert row.when is not None
    assert row.kind == "music" and row.place_text == "Shape Hall"


def test_filling_holes_never_overwrites_something_already_stated():
    from worker.locale.desk_read import fill_holes
    kept = Happening(
        title="A", when="2026-09-11T20:00:00-05:00", when_text="Fri 8pm",
        when_precision="datetime", place_text="Shape Hall", via="Desk",
        kind="music", door_id="d", door_type="local_desk", locale_id="l",
        source_url="https://desk.example/list", listing_url="https://desk.example/e/1",
        category_text="Live Music", kind_source="desk_category")
    incoming = replace(kept, when="2099-01-01T00:00:00Z", place_text="Elsewhere",
                       kind="film", category_text="Movies")
    merged = fill_holes(kept, incoming)
    assert merged.when == kept.when
    assert merged.place_text == "Shape Hall"
    assert merged.kind == "music" and merged.category_text == "Live Music"


def test_a_default_kind_never_displaces_a_desks_own_word():
    from worker.locale.desk_read import fill_holes
    defaulted = Happening(
        title="A", when=None, when_text=None, when_precision=None, place_text=None,
        via="Desk", kind="other", door_id="d", door_type="local_desk", locale_id="l",
        source_url="https://desk.example/list", listing_url=None,
        category_text=None, kind_source="default")
    stated = replace(defaulted, kind="film", category_text="Movies",
                     kind_source="desk_category")
    assert fill_holes(defaulted, stated).kind == "film"
    assert fill_holes(stated, defaulted).kind == "film"


def test_row_key_prefers_the_cards_own_address():
    from worker.locale.desk_read import row_key
    assert row_key("A", "2026-09-11T20:00:00-05:00", None, "https://d/e/1") == \
        row_key("A", "2026-09-12T01:00:00Z", None, "https://d/e/1")


def test_row_key_falls_back_to_title_when_no_address_is_stated():
    from worker.locale.desk_read import row_key
    assert row_key("A", None, None, None) == row_key("A", None, None, "")
    assert row_key("A", None, None, None) != row_key("B", None, None, None)
