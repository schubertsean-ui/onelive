"""read(public_desk) — a desk row exists because a desk printed it.

The rules under test are the founder's three: `when` only if the page states it,
unknown kind = other, via = desk. Plus the gate this path REPLACES: a happening
must not need an identity, or a clock, in order to exist (ONE-LIVE-TRUST.md).
"""
from __future__ import annotations

import os

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
    html = ('<ul><li><time datetime="next friday">Next Friday</time> '
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
    rows = read(doors["kutx-concert-calendar"], fixture("desk_listing.html")).rows
    assert {r.kind for r in rows} == {"music"}


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
