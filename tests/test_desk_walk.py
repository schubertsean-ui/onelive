"""walk(public_desk) — the whole public list, page by page, or an honest reason.

Founder's ticket: "Paginate until the public list is exhausted (or write
blocked_reason per page). No login."

So the properties under test are: we follow the DESK'S OWN next links and never
invent one; a wall ends the walk and never becomes a login; every page that did
not open carries its own `blocked_reason`; and a stop is never mistakable for an
exhausted desk.
"""
from __future__ import annotations

import json
import os

import pytest

from worker.locale import pack as lp
from worker.locale.desk_walk import (
    DeskWalkError, PageFetch, continuation_control, next_page_url, walk, walk_table,
)
from worker.locale.kind_map import load_kind_map

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "desk_pages", "austin-chronicle-eventsearch")
CAPCOG = "us-tx-capcog"
HOST = "https://desk.example"


@pytest.fixture(scope="module")
def doors():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}


@pytest.fixture()
def desk(doors):
    return doors["austin-chronicle-eventsearch"]


@pytest.fixture(scope="module")
def manifest():
    with open(os.path.join(FIXTURES, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture()
def committed_pages(manifest):
    """A fetcher over the committed pages; anything else answers 404."""
    def fetch(url):
        name = (manifest["pages"] or {}).get(url)
        if not name:
            return PageFetch(url=url, status=404)
        with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
            return PageFetch(url=url, status=200, body=fh.read(), final_url=url)
    return fetch


def pages(mapping):
    """A fetcher over an inline {url: html} dict."""
    def fetch(url):
        if url not in mapping:
            return PageFetch(url=url, status=404)
        return PageFetch(url=url, status=200, body=mapping[url], final_url=url)
    return fetch


def page(body: str, *, head: str = "") -> str:
    return f"<html><head>{head}</head><body>{body}</body></html>"


CARD = ('<div class="event"><h3><a href="/e/{n}">Listing {n}</a></h3>'
        '<time datetime="2026-09-1{n}T20:00:00-05:00">Sept 1{n}</time></div>')


# --- the committed three-page walk -------------------------------------------

def test_the_walk_follows_the_desks_own_links_to_the_end(desk, committed_pages,
                                                         manifest):
    result = walk(desk, committed_pages, start_url=manifest["start_url"])
    assert [p.n for p in result.pages] == [1, 2, 3]
    assert result.stopped_because == "no_next_link"
    assert result.exhausted is True
    assert result.pages_blocked == 0


def test_page_one_declares_next_in_markup_and_page_two_says_it_in_words(
        desk, committed_pages, manifest):
    result = walk(desk, committed_pages, start_url=manifest["start_url"])
    # rel=next on page 1, a text "Next" anchor on page 2, nothing on page 3.
    assert result.pages[0].next_url.endswith("page=2")
    assert result.pages[1].next_url.endswith("page=3")
    assert result.pages[2].next_url is None


def test_more_than_one_page_of_rows_reaches_the_result(desk, committed_pages,
                                                       manifest):
    result = walk(desk, committed_pages, start_url=manifest["start_url"])
    # The point of the whole module: page 2 onward is not absent.
    first_page_only = result.pages[0].rows_seen
    assert result.count > first_page_only
    assert result.count == 17 and result.rows_seen == 18


def test_a_listing_repeated_on_a_later_page_is_counted_once(desk, committed_pages,
                                                            manifest):
    result = walk(desk, committed_pages, start_url=manifest["start_url"])
    assert result.duplicates_across_pages == 1
    urls = [r.listing_url for r in result.rows if r.listing_url]
    assert len(urls) == len(set(urls))


def test_a_date_is_only_ever_one_the_page_stated(desk, committed_pages, manifest):
    result = walk(desk, committed_pages, start_url=manifest["start_url"])
    undated = [r for r in result.rows if r.when is None]
    assert undated, "the fixtures include listings the desk printed with no date"
    for row in undated:
        assert row.when_precision is None
        # A hole on the clock is a hole. It is never filled from prose.
        assert row.when_text is None or not row.when_text.strip().startswith("2026")


def test_an_untitled_block_is_counted_not_silently_dropped(desk, committed_pages,
                                                           manifest):
    result = walk(desk, committed_pages, start_url=manifest["start_url"])
    assert result.skipped_untitled == 1


def test_the_kind_map_colours_rows_from_the_desks_own_categories(
        desk, committed_pages, manifest):
    result = walk(desk, committed_pages, start_url=manifest["start_url"],
                  kind_map=load_kind_map("austin-chronicle"))
    kinds = {r.kind for r in result.rows}
    assert {"music", "film", "market", "civic", "art"} <= kinds
    mapped = [r for r in result.rows if r.kind_source == "desk_category"]
    assert mapped and all(r.category_text for r in mapped)
    # And a category the table does not cover is reported, never guessed.
    assert "Psychogeography" in result.unmapped_categories
    for row in result.rows:
        if row.category_text == "Psychogeography":  # pragma: no cover - defensive
            pytest.fail("an unmapped category must not decide a kind")


def test_without_a_map_every_row_keeps_the_doors_declared_kind(
        desk, committed_pages, manifest):
    result = walk(desk, committed_pages, start_url=manifest["start_url"])
    assert {r.kind for r in result.rows} == {"other"}
    assert {r.kind_source for r in result.rows} == {"default"}


def test_a_map_for_another_desk_never_colours_this_one(doors, committed_pages,
                                                       manifest):
    other = doors["ut-austin-localist"]
    result = walk(other, committed_pages, start_url=manifest["start_url"],
                  kind_map=load_kind_map("austin-chronicle"))
    assert {r.kind_source for r in result.rows} <= {"default", "door_scope"}


# --- next-link discovery -----------------------------------------------------

def test_rel_next_in_the_head_is_followed():
    url, note = next_page_url(
        page("", head='<link rel="next" href="/p2">'), f"{HOST}/p1")
    assert url == f"{HOST}/p2" and note is None


def test_an_anchor_saying_next_is_followed():
    url, _ = next_page_url(page('<a href="/p2">Next</a>'), f"{HOST}/p1")
    assert url == f"{HOST}/p2"


def test_an_aria_label_saying_next_page_is_followed():
    url, _ = next_page_url(
        page('<a href="/p2" aria-label="Next page of results">&raquo;</a>'),
        f"{HOST}/p1")
    assert url == f"{HOST}/p2"


def test_a_declared_rel_next_outranks_a_text_next():
    url, _ = next_page_url(
        page('<a href="/words">Next</a><a rel="next" href="/declared">2</a>'),
        f"{HOST}/p1")
    assert url == f"{HOST}/declared"


def test_a_listing_title_containing_next_is_not_a_pagination_control():
    url, _ = next_page_url(
        page('<a href="/e/1">Next Wednesday at the hall</a>'), f"{HOST}/p1")
    assert url is None


def test_a_next_link_off_the_desks_host_is_refused_with_a_reason():
    url, note = next_page_url(
        page('<a rel="next" href="https://elsewhere.example/p2">Next</a>'),
        f"{HOST}/p1")
    assert url is None
    assert note and "leaves the desk's host" in note


def test_javascript_and_fragment_links_are_not_pages():
    url, _ = next_page_url(
        page('<a rel="next" href="#more">Next</a>'
             '<a rel="next" href="javascript:load()">Next</a>'), f"{HOST}/p1")
    assert url is None


def test_a_page_with_no_next_link_ends_the_list():
    assert next_page_url(page("<p>no pagination here</p>"), f"{HOST}/p1") == (None, None)


def test_the_walker_never_invents_a_page_address(desk):
    # A page that shows page NUMBERS but links none of them yields nothing: we
    # do not increment somebody else's query parameter to guess page 2.
    asked = []

    def fetch(url):
        asked.append(url)
        return PageFetch(url=url, status=200,
                         body=page('<nav>1 2 3 4</nav>' + CARD.format(n=1)),
                         final_url=url)

    result = walk(desk, fetch, start_url=f"{HOST}/list")
    assert asked == [f"{HOST}/list"]
    assert result.stopped_because == "no_next_link"


# --- the stops, each with its own reason -------------------------------------

def test_a_cycle_stops_the_walk(desk):
    body = page(CARD.format(n=1) + f'<a rel="next" href="{HOST}/a">Next</a>')
    result = walk(desk, pages({f"{HOST}/a": body}), start_url=f"{HOST}/a")
    assert result.stopped_because == "cycle"
    assert len(result.pages) == 1
    assert "cycle" in " ".join(result.notes)


def test_the_page_cap_is_reported_as_ours_not_as_the_desks_end(desk):
    mapping = {}
    for n in range(1, 8):
        mapping[f"{HOST}/p{n}"] = page(
            CARD.format(n=n) + f'<a rel="next" href="{HOST}/p{n + 1}">Next</a>')
    result = walk(desk, pages(mapping), start_url=f"{HOST}/p1", max_pages=3)
    assert len(result.pages) == 3
    assert result.stopped_because == "max_pages"
    assert result.exhausted is False
    assert "OUR limit, not the end of the desk" in " ".join(result.notes)


@pytest.mark.parametrize("status", [401, 402, 403, 407, 429])
def test_a_wall_ends_the_walk_and_is_never_worked_around(desk, status):
    asked = []

    def fetch(url):
        asked.append(url)
        return PageFetch(url=url, status=status)

    result = walk(desk, fetch, start_url=f"{HOST}/p1")
    assert result.stopped_because == "wall"
    assert result.pages[0].blocked_reason.startswith("class D on contact")
    assert asked == [f"{HOST}/p1"], "we knock once; we never retry a wall"


def test_a_redirect_onto_a_sign_in_page_is_a_wall(desk):
    def fetch(url):
        return PageFetch(url=url, status=200, body=page(CARD.format(n=1)),
                         final_url="https://desk.example/users/sign_in?next=/list")

    result = walk(desk, fetch, start_url=f"{HOST}/list")
    assert result.stopped_because == "wall"
    assert "login wall" in result.pages[0].blocked_reason


def test_a_wall_on_page_three_keeps_the_first_two_pages(desk):
    good = page(CARD.format(n=1) + f'<a rel="next" href="{HOST}/p2">Next</a>')
    second = page(CARD.format(n=2) + f'<a rel="next" href="{HOST}/p3">Next</a>')

    def fetch(url):
        if url == f"{HOST}/p1":
            return PageFetch(url=url, status=200, body=good, final_url=url)
        if url == f"{HOST}/p2":
            return PageFetch(url=url, status=200, body=second, final_url=url)
        return PageFetch(url=url, status=403)

    result = walk(desk, fetch, start_url=f"{HOST}/p1")
    assert result.count == 2, "rows already read survive a wall further along"
    assert result.pages_blocked == 1 and result.pages_read == 2
    assert result.exhausted is False


def test_a_404_is_triage_not_an_empty_desk(desk):
    result = walk(desk, pages({}), start_url=f"{HOST}/p1")
    assert result.stopped_because == "http_error"
    assert "triage, not 'no events here'" in result.pages[0].blocked_reason


def test_a_transport_failure_is_recorded_as_ours(desk):
    def fetch(url):
        return PageFetch(url=url, error="ProxyError: unable to connect to proxy")

    result = walk(desk, fetch, start_url=f"{HOST}/p1")
    assert result.stopped_because == "fetch_error"
    assert "ProxyError" in result.pages[0].blocked_reason
    # Our own network failing is NOT the desk refusing us: no class D here.
    assert "class D" not in result.pages[0].blocked_reason


def test_a_fetcher_that_raises_does_not_lose_the_pages_already_read(desk):
    def fetch(url):
        if url == f"{HOST}/p1":
            return PageFetch(url=url, status=200, final_url=url, body=page(
                CARD.format(n=1) + f'<a rel="next" href="{HOST}/p2">Next</a>'))
        raise RuntimeError("socket exploded")

    result = walk(desk, fetch, start_url=f"{HOST}/p1")
    assert result.count == 1
    assert result.stopped_because == "fetch_error"
    assert "socket exploded" in result.pages[1].blocked_reason


def test_an_empty_body_is_nothing_read_not_nothing_on(desk):
    def fetch(url):
        return PageFetch(url=url, status=200, body="   ", final_url=url)

    result = walk(desk, fetch, start_url=f"{HOST}/p1")
    assert result.stopped_because == "empty_page"
    assert "not 'nothing on'" in result.pages[0].blocked_reason


# --- refusals at the door ----------------------------------------------------

def test_a_wall_door_is_never_walked(doors):
    wall = next(d for d in doors.values() if d.door_type == "wall")
    with pytest.raises(DeskWalkError):
        walk(wall, pages({}))


def test_a_junk_door_is_never_walked(doors):
    junk = next(d for d in doors.values() if d.door_type == "junk")
    with pytest.raises(DeskWalkError):
        walk(junk, pages({}))


def test_walk_needs_a_door(committed_pages):
    with pytest.raises(DeskWalkError):
        walk("austin-chronicle-eventsearch", committed_pages)


def test_walk_needs_a_callable_fetcher(desk):
    with pytest.raises(DeskWalkError):
        walk(desk, "not a function")


def test_a_fetcher_that_answers_with_the_wrong_type_is_refused(desk):
    with pytest.raises(DeskWalkError):
        walk(desk, lambda url: "<html>whatever</html>")


@pytest.mark.parametrize("bad", [0, -1, "3", None])
def test_max_pages_must_be_a_positive_int(desk, committed_pages, bad):
    with pytest.raises(DeskWalkError):
        walk(desk, committed_pages, max_pages=bad)


# --- the table ---------------------------------------------------------------

def test_the_page_table_carries_a_row_per_page_with_its_reason(desk):
    def fetch(url):
        if url == f"{HOST}/p1":
            return PageFetch(url=url, status=200, final_url=url, body=page(
                CARD.format(n=1) + f'<a rel="next" href="{HOST}/p2">Next</a>'))
        return PageFetch(url=url, status=429)

    table = walk_table([walk(desk, fetch, start_url=f"{HOST}/p1")])
    lines = [ln for ln in table.splitlines() if ln.startswith("| `")]
    assert len(lines) == 2
    assert "429" in lines[1] and "class D on contact" in lines[1]


# --- a list that continues behind script --------------------------------------
#
# A "Load more" button and the last page of a list look IDENTICAL to a walker
# that follows links: no next link either way. The difference is everything —
# one is a floor, the other is the whole desk — so it is REPORTED, and the walk
# still never synthesises the address that script would have called.

@pytest.mark.parametrize("control", [
    '<button class="load-more">Load More</button>',
    '<button aria-label="Next page">&rarr;</button>',
    '<a href="#" class="more">Show more</a>',
    '<a href="javascript:void(0)">Load more</a>',
    '<a data-page="2">More results</a>',
])
def test_a_continuation_control_that_is_not_a_link_is_seen(control):
    assert continuation_control(page(control))


@pytest.mark.parametrize("body", [
    "<p>that is the end of the list</p>",
    '<a href="/x">Next Wednesday</a>',       # a listing title, not a control
    '<a href="/p2">Next</a>',                # a real link is not a control
])
def test_ordinary_pages_state_no_such_control(body):
    assert continuation_control(page(body)) is None


def test_a_control_is_never_followed_only_reported():
    # No URL is invented for it — that would be a guess about a stranger's routing.
    assert next_page_url(page('<button>Load More</button>'), f"{HOST}/p1") == (None, None)


def test_a_walk_that_ends_on_a_control_is_not_an_exhausted_desk(desk):
    one = walk(desk, pages({f"{HOST}/p1": page(
        CARD.format(n=1) + '<button class="ds-load-more">Load More</button>')}),
        start_url=f"{HOST}/p1")
    assert one.stopped_because == "next_control_not_a_link"
    assert one.exhausted is False
    assert one.count == 1                      # everything read is kept
    assert one.pages[0].blocked_reason is None  # the page opened; the LIST goes on
    assert any("load more" in n.lower() for n in one.notes)
    assert any("load more" in n.lower() for n in one.pages[0].notes)


def test_a_walk_that_runs_out_of_links_is_an_exhausted_desk(desk):
    one = walk(desk, pages({f"{HOST}/p1": page(CARD.format(n=1))}),
               start_url=f"{HOST}/p1")
    assert one.stopped_because == "no_next_link"
    assert one.exhausted is True


def test_a_real_next_link_wins_over_a_control_on_the_same_page(desk):
    # Pages carry both: a paginator AND a "load more". The link is followed.
    one = walk(desk, pages({
        f"{HOST}/p1": page(CARD.format(n=1)
                           + f'<a rel="next" href="{HOST}/p2">Next</a>'
                           + '<button>Load More</button>'),
        f"{HOST}/p2": page(CARD.format(n=2)),
    }), start_url=f"{HOST}/p1")
    assert [p.n for p in one.pages] == [1, 2]
    assert one.stopped_because == "no_next_link" and one.count == 2


# --- a next link we refused is OUR stop, not the desk's end -------------------

def test_a_next_link_off_the_host_stops_the_walk_without_claiming_the_end(desk):
    one = walk(desk, pages({f"{HOST}/p1": page(
        CARD.format(n=1)
        + '<a rel="next" href="https://elsewhere.example/p2">Next</a>')}),
        start_url=f"{HOST}/p1")
    # The page stated a next page. We declined to follow it off the desk's host.
    # Calling that `no_next_link` would put our refusal on the desk's account.
    assert one.stopped_because == "next_link_not_followed"
    assert one.exhausted is False
    assert one.count == 1
    assert any("leaves the desk's host" in n for n in one.notes)


def test_a_button_nested_inside_a_real_next_link_is_still_a_link(desk):
    one = walk(desk, pages({
        f"{HOST}/p1": page(CARD.format(n=1)
                           + f'<a href="{HOST}/p2"><button>Next</button></a>'),
        f"{HOST}/p2": page(CARD.format(n=2)),
    }), start_url=f"{HOST}/p1")
    assert [p.n for p in one.pages] == [1, 2]
    assert one.stopped_because == "no_next_link" and one.exhausted is True
