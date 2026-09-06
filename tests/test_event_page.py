"""Ticket C — a same-host event page states its own night and place, or neither.

The founder's five test cases are the five section headings below:

  (a) a page with a date and a venue -> both filled
  (b) a clock with no date -> `when` stays NULL
  (c) a date on the LIST page must not copy onto the event page's row
  (d) a 403 -> a hole, queued, never a mash
  (e) same-host only, and one knock

Everything else here guards the same rules one layer out: a related-events rail,
a page footer carrying the newspaper's own address, an off-host redirect.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from worker.locale.desk_read import Happening
from worker.locale.desk_walk import PageFetch
from worker.locale.event_page import (
    EventPageError, FollowRun, apply, follow, follow_table, read_event_page,
)

DESK = "https://desk.test"


def row(listing_url="https://desk.test/event/foo-1", *, title="Foo at the Hall",
        when=None, when_text=None, place_text=None,
        source_url="https://desk.test/events/today") -> Happening:
    return Happening(
        title=title, when=when, when_text=when_text,
        when_precision=("date" if when and len(when) == 10 else
                        ("datetime" if when else None)),
        place_text=place_text, via="Test Desk", kind="other",
        door_id="test-desk", door_type="local_desk", locale_id="us-tx-capcog",
        source_url=source_url, listing_url=listing_url,
    )


def fetcher(pages, *, walls=(), raises=None):
    """A fetch(url) -> PageFetch over a dict of committed pages."""
    def fetch(url: str) -> PageFetch:
        if raises and url in raises:
            raise raises[url]
        if url in walls:
            return PageFetch(url=url, status=walls[url], body="",
                             final_url=url, error=f"HTTP {walls[url]}")
        if url not in pages:
            return PageFetch(url=url, status=404, body="", final_url=url,
                             error="HTTP 404")
        body, final = pages[url] if isinstance(pages[url], tuple) else (pages[url], url)
        return PageFetch(url=url, status=200, body=body, final_url=final)
    return fetch


# --- (a) a page with a date and a venue -> both filled ------------------------

DATED_AND_PLACED = """<!doctype html><html><body>
<header><a href="/">Test Desk</a></header>
<main>
  <article>
    <h1>Foo at the Hall</h1>
    <time datetime="2026-09-11T20:00">Fri Sep 11, 8pm</time>
    <div class="venue">The Hall, 123 Red River</div>
  </article>
</main>
<footer><address>Test Desk, 900 Newspaper Row</address></footer>
</body></html>"""


def test_a_page_stating_a_date_and_a_venue_fills_both():
    st = read_event_page(DATED_AND_PLACED, f"{DESK}/event/foo-1")
    assert st.when == "2026-09-11T20:00"
    assert st.when_precision == "datetime"
    assert st.when_source == "time_datetime"
    assert st.place_text == "The Hall, 123 Red River"
    assert st.place_source == "printed_venue_line"

    filled, visit = apply(row(), st)
    assert filled.when == "2026-09-11T20:00"
    assert filled.place_text == "The Hall, 123 Red River"
    assert visit.filled_when and visit.filled_place


JSONLD_PAGE = """<!doctype html><html><body>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"MusicEvent","name":"Foo at the Hall",
 "url":"https://desk.test/event/foo-1","startDate":"2026-09-11T20:00:00-05:00",
 "location":{"@type":"Place","name":"The Hall",
             "address":"123 Red River, Austin, TX"}}
</script>
<h1>Foo at the Hall</h1></body></html>"""


def test_a_page_stating_schema_org_fills_from_its_own_event():
    st = read_event_page(JSONLD_PAGE, f"{DESK}/event/foo-1")
    assert st.when_source == "jsonld_startDate"
    assert st.when and st.when.startswith("2026-09-12T01:00")  # -05:00 -> UTC Z
    assert st.place_source == "jsonld_location"
    assert "The Hall" in st.place_text


def test_the_newspapers_own_footer_address_is_not_the_venue():
    """A page-level `<footer><address>` is the DESK's office. Publishing it as
    the venue would send a friend to a newsroom."""
    page = """<!doctype html><html><body>
    <main><article><h1>Foo</h1>
      <time datetime="2026-09-11">Sep 11</time></article></main>
    <footer class="location"><address>Test Desk, 900 Newspaper Row</address></footer>
    </body></html>"""
    st = read_event_page(page, f"{DESK}/event/foo-1")
    assert st.when == "2026-09-11"
    assert st.place_text is None, "the desk's own address was published as a venue"


def test_no_place_stated_is_a_hole_never_the_locales_city():
    page = """<!doctype html><html><body><main><article><h1>Foo</h1>
    <time datetime="2026-09-11">Sep 11</time></article></main></body></html>"""
    st = read_event_page(page, f"{DESK}/event/foo-1")
    assert st.place_text is None
    assert st.placed is False
    filled, visit = apply(row(), st)
    assert filled.place_text is None
    assert visit.filled_place is False


# --- (b) a clock with no date -> `when` stays NULL -----------------------------

CLOCK_ONLY = """<!doctype html><html><body><main><article>
<h1>Foo at the Hall</h1>
<time datetime="20:00">Doors 8pm</time>
<div class="venue">The Hall</div>
</article></main></body></html>"""


def test_b_a_clock_with_no_date_leaves_when_null():
    st = read_event_page(CLOCK_ONLY, f"{DESK}/event/foo-1")
    assert st.when is None, "a time of day was coerced into a night"
    assert st.when_precision is None
    assert st.clock_only is True
    assert st.place_text == "The Hall"   # the place still fills; only the night is a hole

    filled, visit = apply(row(), st)
    assert filled.when is None
    assert visit.filled_when is False
    assert visit.filled_place is True


def test_prose_is_never_parsed_into_a_night():
    page = """<!doctype html><html><body><main><article><h1>Foo</h1>
    <p class="dateline">This Friday, Labor Day weekend</p>
    <div class="venue">The Hall</div></article></main></body></html>"""
    st = read_event_page(page, f"{DESK}/event/foo-1")
    assert st.when is None
    assert st.clock_only is False


def test_two_different_dates_are_declined_not_chosen_between():
    page = """<!doctype html><html><body><main><article><h1>Foo</h1>
    <time datetime="2026-09-11">Sep 11</time>
    <time datetime="2026-10-02">Oct 2</time>
    </article></main></body></html>"""
    st = read_event_page(page, f"{DESK}/event/foo-1")
    assert st.when is None
    assert st.ambiguous_dates == ("2026-09-11", "2026-10-02")


def test_a_start_and_an_end_on_one_night_are_one_night():
    page = """<!doctype html><html><body><main><article><h1>Foo</h1>
    <time class="event-start" datetime="2026-09-11T20:00">8pm</time>
    <time class="event-end" datetime="2026-09-11T23:00">11pm</time>
    </article></main></body></html>"""
    st = read_event_page(page, f"{DESK}/event/foo-1")
    assert st.when == "2026-09-11T20:00", "the end time was taken as the start"


def test_a_calendar_class_is_not_an_end_time():
    """`calendar` contains the letters e-n-d. A substring test spells an end
    time out of it and drops the only date the page stated."""
    page = """<!doctype html><html><body><main><article><h1>Foo</h1>
    <time class="calendar-date" datetime="2026-09-11T20:00">8pm</time>
    </article></main></body></html>"""
    st = read_event_page(page, f"{DESK}/event/foo-1")
    assert st.when == "2026-09-11T20:00"


# --- (c) a LIST page's date must not copy onto the event page's row -----------

UNDATED_EVENT_PAGE = """<!doctype html><html><body><main><article>
<h1>Foo at the Hall</h1>
<p>Tickets at the door.</p>
<div class="venue">The Hall</div>
</article></main></body></html>"""


def test_c_a_date_from_the_list_page_does_not_become_the_event_pages_statement():
    """The founder's case: the list card printed a night; this page prints none.
    The page's own statement must carry no date at all."""
    st = read_event_page(UNDATED_EVENT_PAGE, f"{DESK}/event/foo-1")
    assert st.when is None, "the event page reported a night it never stated"
    assert st.when_source is None

    listed = row(when="2026-09-11T20:00", when_text="Fri Sep 11, 8pm")
    filled, visit = apply(listed, st)
    # The row keeps what the LIST stated — that is the list's claim, unchanged —
    # and nothing was filled from this page.
    assert filled.when == "2026-09-11T20:00"
    assert visit.filled_when is False
    assert visit.dated is False, "the table would print this page as dated"


def test_c_a_related_events_rail_never_dates_this_page():
    """The other mouth of the same rule: a neighbouring listing's `<time>` on
    THIS page belongs to that listing."""
    page = """<!doctype html><html><body>
    <main><article><h1>Foo at the Hall</h1>
      <div class="venue">The Hall</div></article>
      <section class="related">
        <div class="card"><a href="/event/bar-2">Bar in the Park</a>
          <time datetime="2026-12-25T19:00">Dec 25</time></div>
      </section>
    </main></body></html>"""
    st = read_event_page(page, f"{DESK}/event/foo-1")
    assert st.when is None, "a neighbour's night was published as this page's"
    assert st.foreign_candidates >= 1
    assert st.place_text == "The Hall"


def test_c_a_jsonld_event_addressed_to_another_page_is_not_read_as_this_one():
    page = """<!doctype html><html><body>
    <script type="application/ld+json">
    {"@context":"https://schema.org","@type":"Event","name":"Bar in the Park",
     "url":"https://desk.test/event/bar-2","startDate":"2026-12-25T19:00:00Z",
     "location":{"@type":"Place","name":"The Park"}}
    </script>
    <h1>Foo at the Hall</h1></body></html>"""
    st = read_event_page(page, f"{DESK}/event/foo-1")
    assert st.when is None
    assert st.place_text is None
    assert any("another address" in n for n in st.notes)


def test_a_contested_night_is_taken_away_from_the_row():
    """Founder ruling 2026-09-06. The list says one night, the page says
    another: neither wins. This test FAILS on the old "keep the list's date"
    behaviour, which left `when` at the list's value."""
    listed = row(when="2026-09-11T20:00", when_text="Fri Sep 11, 8pm")
    st = read_event_page(DATED_AND_PLACED.replace("2026-09-11T20:00",
                                                  "2026-10-02T20:00"),
                         f"{DESK}/event/foo-1")
    filled, visit = apply(listed, st)
    assert visit.when_conflict is True
    assert filled.when is None, "a contested night stayed on the row"
    assert filled.when_precision is None
    assert filled.when_text is None, (
        "the contested night survived as printed text — any surface that "
        "renders when_text would still show a night the desk contradicts")
    # Neither side's claim was adopted...
    assert filled.when != "2026-10-02T20:00"
    # ...and neither is lost: the disagreement stays auditable on the visit.
    assert visit.listed_when == "2026-09-11T20:00"
    assert visit.page_when == "2026-10-02T20:00"


def test_a_contested_night_is_not_counted_as_a_fill():
    listed = row(when="2026-09-11T20:00")
    st = read_event_page(DATED_AND_PLACED.replace("2026-09-11T20:00",
                                                  "2026-10-02T20:00"),
                         f"{DESK}/event/foo-1")
    run = FollowRun()
    filled, visit = apply(listed, st)
    run.visits.append(visit)
    assert run.filled_when_n == 0
    assert run.nulled_when_n == 1


def test_hole_fill_still_stands_when_the_list_stated_no_night():
    """The other half of the ruling: a night the list never stated is TAKEN
    from the page. Nulling a contested night must not turn into nulling
    everything."""
    listed = row(when=None)
    st = read_event_page(DATED_AND_PLACED, f"{DESK}/event/foo-1")
    filled, visit = apply(listed, st)
    assert filled.when == "2026-09-11T20:00"
    assert visit.filled_when is True
    assert visit.when_conflict is False


def test_agreement_written_two_ways_never_nulls_the_night():
    """The instant test guards the new rule too: if one moment written two ways
    read as a disagreement, this rule would DELETE nights the desk agreed on."""
    listed = row(when="2026-09-12T01:00:00Z")
    page_html = DATED_AND_PLACED.replace("2026-09-11T20:00", "2026-09-11T20:00:00-05:00")
    st = read_event_page(page_html, f"{DESK}/event/foo-1")
    filled, visit = apply(listed, st)
    assert visit.when_conflict is False
    assert filled.when == "2026-09-12T01:00:00Z", "an agreed night was deleted"


def test_one_moment_written_two_ways_is_not_a_disagreement():
    """`2026-09-11T20:00-05:00` and `2026-09-12T01:00:00Z` are one instant. The
    string (or date-prefix) test reports a conflict that does not exist and
    would print a page as disagreeing with the list that quoted it — the defect
    PR #229 r8 fixed on the union path."""
    listed = row(when="2026-09-12T01:00:00Z")
    page_html = DATED_AND_PLACED.replace("2026-09-11T20:00", "2026-09-11T20:00:00-05:00")
    st = read_event_page(page_html, f"{DESK}/event/foo-1")
    _filled, visit = apply(listed, st)
    assert visit.when_conflict is False, "one moment was read as two"


def test_a_page_adding_the_street_to_the_listed_venue_is_not_a_disagreement():
    """"The Hall" and "The Hall, 123 Red River" are one venue described twice."""
    listed = row(place_text="The Hall")
    st = read_event_page(DATED_AND_PLACED, f"{DESK}/event/foo-1")
    assert st.place_text == "The Hall, 123 Red River"
    _filled, visit = apply(listed, st)
    assert visit.place_conflict is False, "an elaboration was read as a disagreement"


def test_a_different_venue_is_still_a_disagreement():
    listed = row(place_text="The Park")
    st = read_event_page(DATED_AND_PLACED, f"{DESK}/event/foo-1")
    _filled, visit = apply(listed, st)
    assert visit.place_conflict is True


def test_a_shared_word_is_not_a_shared_venue():
    """Plain containment reads "Hall" and "Town Hall Annex" as one place. They
    are two venues in most towns."""
    listed = row(place_text="Hall")
    page_html = DATED_AND_PLACED.replace("The Hall, 123 Red River", "Town Hall Annex")
    st = read_event_page(page_html, f"{DESK}/event/foo-1")
    _filled, visit = apply(listed, st)
    assert visit.place_conflict is True


def test_a_naive_time_is_never_given_a_timezone_we_were_not_told():
    """A page stating `2026-09-11T20:00` did not say which zone. Assuming one
    to make it agree with an aware statement is inventing the fact under test."""
    listed = row(when="2026-09-12T01:00:00Z")
    st = read_event_page(DATED_AND_PLACED, f"{DESK}/event/foo-1")
    assert st.when == "2026-09-11T20:00"
    _filled, visit = apply(listed, st)
    assert visit.when_conflict is True


def test_a_genuinely_different_night_is_still_a_disagreement():
    listed = row(when="2026-09-12T01:00:00Z")
    page_html = DATED_AND_PLACED.replace("2026-09-11T20:00", "2026-10-02T20:00:00-05:00")
    st = read_event_page(page_html, f"{DESK}/event/foo-1")
    _filled, visit = apply(listed, st)
    assert visit.when_conflict is True


# --- (d) a 403 is a hole, queued, never a mash --------------------------------

def test_d_a_403_is_a_hole_with_a_reason_and_is_queued():
    rows = [row("https://desk.test/event/foo-1")]
    run = follow(rows, fetcher({}, walls={"https://desk.test/event/foo-1": 403}))
    visit = run.visits[0]
    assert visit.blocked is True
    assert visit.walled is True
    assert visit.queued is True, "a wall was not queued for the human claim path"
    assert "403" in visit.blocked_reason
    # The row survives, unchanged and unmashed.
    assert len(run.rows) == 1
    assert run.rows[0].when is None
    assert run.rows[0].place_text is None
    assert run.dated_n == 0 and run.blocked_n == 1


def test_d_each_page_is_knocked_on_once_and_never_retried():
    """One knock per page. The `seen` set, not the wall, is what stops a second
    knock — a page is fetched at most once in a run however often it appears."""
    knocks = []

    def counting_fetch(url: str) -> PageFetch:
        knocks.append(url)
        return PageFetch(url=url, status=403, body="", final_url=url,
                         error="HTTP 403 Forbidden")

    rows = [row("https://desk.test/event/e-1")] * 4
    run = follow(rows, counting_fetch)
    assert knocks == ["https://desk.test/event/e-1"]
    assert run.visits[0].walled and run.visits[0].queued


def test_d_a_run_of_walls_closes_the_host_and_the_stop_is_reported_as_ours():
    knocks = []

    def counting_fetch(url: str) -> PageFetch:
        knocks.append(url)
        return PageFetch(url=url, status=403, body="", final_url=url,
                         error="HTTP 403 Forbidden")

    rows = [row(f"https://desk.test/event/e-{i}") for i in range(6)]
    run = follow(rows, counting_fetch, wall_streak_limit=3)
    assert len(knocks) == 3, f"knocked {len(knocks)} times on a closed door"
    # The three we met are walls; the three we declined to open are OURS, and
    # must never be counted as the desk's refusal.
    assert run.walled_n == 3
    assert run.not_knocked_n == 3
    assert "OUR stop" in run.visits[5].blocked_reason
    assert any("not empty" in n for n in run.notes)


def test_d_one_walled_listing_does_not_blank_the_rest_of_the_desk():
    """A members-only show behind an open desk is ONE hole. Reading it as the
    desk's answer would drop rows the desk published — the coverage direction
    ONE-LIVE-COVERAGE-LAW forbids."""
    def mixed_fetch(url: str) -> PageFetch:
        if url.endswith("members-only"):
            return PageFetch(url=url, status=403, body="", final_url=url,
                             error="HTTP 403 Forbidden")
        return PageFetch(url=url, status=200, body=DATED_AND_PLACED, final_url=url)

    rows = [row("https://desk.test/event/members-only")] + [
        row(f"https://desk.test/event/open-{i}") for i in range(4)]
    run = follow(rows, mixed_fetch)
    assert run.walled_n == 1
    assert run.not_knocked_n == 0
    assert run.dated_n == 4, "an open desk was blanked by one walled listing"
    assert run.filled_when_n == 4


def test_d_a_403_never_produces_a_mashed_row():
    """The failure this replaces: a blocked page filling the row from whatever
    else was in hand."""
    rows = [row("https://desk.test/event/foo-1", when=None, place_text=None)]
    run = follow(rows, fetcher({"https://desk.test/event/other": DATED_AND_PLACED},
                               walls={"https://desk.test/event/foo-1": 403}))
    assert run.rows[0].when is None and run.rows[0].place_text is None
    assert run.filled_when_n == 0 and run.filled_place_n == 0


def test_a_404_is_a_hole_and_is_not_a_wall():
    run = follow([row()], fetcher({}))
    assert run.visits[0].blocked is True
    assert run.visits[0].walled is False
    assert run.visits[0].queued is False


def test_a_fetcher_that_raises_is_one_pages_news():
    run = follow([row()], fetcher({}, raises={
        "https://desk.test/event/foo-1": RuntimeError("Tunnel connection failed: 403 Forbidden")}))
    assert run.visits[0].walled is True
    assert run.visits[0].queued is True
    assert len(run.rows) == 1


# --- (e) same host only --------------------------------------------------------

def test_e_an_off_host_permalink_is_never_fetched():
    knocks = []

    def counting_fetch(url: str) -> PageFetch:
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATED_AND_PLACED, final_url=url)

    rows = [row("https://ticketvendor.test/event/foo-1")]
    run = follow(rows, counting_fetch)
    assert knocks == [], "an off-host page was fetched"
    assert run.visits[0].off_host is True
    assert run.off_host_n == 1
    assert run.rows[0].when is None


def test_e_a_redirect_off_host_is_not_read():
    pages = {"https://desk.test/event/foo-1":
             (DATED_AND_PLACED, "https://ticketvendor.test/checkout/1")}
    run = follow([row()], fetcher(pages))
    assert run.visits[0].off_host is True
    assert run.rows[0].when is None, "another publisher's page filled this row"


# --- the ICS rung --------------------------------------------------------------

ICS_PAGE = """<!doctype html><html><head>
<link rel="alternate" type="text/calendar" href="/event/foo-1.ics">
</head><body><main><article><h1>Foo at the Hall</h1>
<div class="venue">The Hall</div></article></main></body></html>"""

ICS_BODY = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Foo at the Hall
DTSTART:20260911T200000Z
LOCATION:The Hall
UID:foo-1
END:VEVENT
END:VCALENDAR"""


def test_an_ics_the_page_advertises_states_the_night():
    pages = {"https://desk.test/event/foo-1": ICS_PAGE,
             "https://desk.test/event/foo-1.ics": ICS_BODY}
    run = follow([row()], fetcher(pages))
    assert run.rows[0].when == "2026-09-11T20:00:00Z"
    assert run.visits[0].statement.when_source == "ics"


def test_an_off_host_calendar_file_is_not_fetched():
    page = ICS_PAGE.replace('href="/event/foo-1.ics"',
                            'href="https://calendars.test/foo-1.ics"')
    pages = {"https://desk.test/event/foo-1": page,
             "https://calendars.test/foo-1.ics": ICS_BODY}
    run = follow([row()], fetcher(pages))
    assert run.rows[0].when is None
    assert any("leaves the desk's host" in n for n in run.visits[0].statement.notes)


def test_the_ics_rung_does_not_run_when_the_page_already_stated_a_night():
    fetched = []

    def counting_fetch(url: str) -> PageFetch:
        fetched.append(url)
        body = DATED_AND_PLACED.replace(
            "<main>", '<link rel="alternate" type="text/calendar" href="/x.ics"><main>')
        return PageFetch(url=url, status=200, body=body, final_url=url)

    run = follow([row()], counting_fetch)
    assert fetched == ["https://desk.test/event/foo-1"]
    assert run.rows[0].when == "2026-09-11T20:00"


# --- the table and the seams ---------------------------------------------------

def test_the_table_prints_the_founders_four_columns():
    pages = {"https://desk.test/event/foo-1": DATED_AND_PLACED,
             "https://desk.test/event/bar-2": CLOCK_ONLY}
    rows = [row("https://desk.test/event/foo-1"),
            row("https://desk.test/event/bar-2"),
            row("https://desk.test/event/gone-3")]
    table = follow_table(follow(rows, fetcher(pages)))
    assert "| url | dated? | place? | blocked reason |" in table
    lines = table.splitlines()
    assert "yes (2026-09-11T20:00)" in lines[2]
    assert "no (clock only)" in lines[3]
    assert "HTTP 404" in lines[4]


def test_read_event_page_refuses_without_the_url_it_came_from():
    with pytest.raises(EventPageError):
        read_event_page(DATED_AND_PLACED, "")


def test_follow_refuses_a_fetcher_that_is_not_one():
    with pytest.raises(EventPageError):
        follow([row()], "not a fetcher")


def test_follow_refuses_a_fetch_that_does_not_return_a_pagefetch():
    with pytest.raises(EventPageError):
        follow([row()], lambda url: {"status": 200, "body": "<html></html>"})


def test_a_row_with_no_permalink_is_left_exactly_as_it_was():
    original = row(listing_url=None)
    run = follow([original], fetcher({}))
    assert run.visits == []
    assert run.rows == [original]


def test_one_permalink_is_followed_once_however_often_it_repeats():
    knocks = []

    def counting_fetch(url: str) -> PageFetch:
        knocks.append(url)
        return PageFetch(url=url, status=200, body=DATED_AND_PLACED, final_url=url)

    rows = [row("https://desk.test/event/foo-1"),
            row("https://desk.test/event/foo-1#tickets")]
    follow(rows, counting_fetch)
    assert len(knocks) == 1


# --- the committed fixtures and the tool that prints the founder's table -------

def test_the_committed_event_page_fixtures_cover_both_desks_permalinks():
    """The artifact has to be re-derivable. This pins that the committed event
    pages still answer the permalinks the LIST fixtures produce — if Ticket B's
    fixtures change shape, this goes red instead of the table quietly filling
    with 404s that would read as the desks publishing nothing."""
    from tools.event_page_table import (
        DEFAULT_DOORS, DEFAULT_LIMIT, collect, event_fixture_fetcher,
    )

    for door_id in DEFAULT_DOORS:
        _fetch, manifest = event_fixture_fetcher(door_id)
        assert manifest.get("note"), f"{door_id} fixtures state no provenance note"

    runs, _notes = collect(DEFAULT_DOORS, limit=DEFAULT_LIMIT, min_interval_s=0)
    visits = [v for _door, run in runs for v in run.visits]
    assert len(visits) == DEFAULT_LIMIT, (
        f"the artifact is {len(visits)} permalinks, not {DEFAULT_LIMIT}")
    unknown = [v.listing_url for v in visits
               if v.blocked_reason and "404" in v.blocked_reason]
    assert not unknown, f"no committed event page for {unknown}"


def test_the_fixture_table_states_that_it_is_a_fixture_run():
    """A fixture count that can be read as a live measurement is the one way
    this artifact could mislead."""
    from tools.event_page_table import event_fixture_fetcher, render, rows_for

    rows, _ = rows_for("austin-chronicle-eventsearch", real=False, timeout_s=5,
                       min_interval_s=0, max_pages=5)
    fetch, _manifest = event_fixture_fetcher("austin-chronicle-eventsearch")
    table = render([("austin-chronicle-eventsearch", follow(rows, fetch, limit=5))],
                   mode="FIXTURE", limit=5)
    assert "FIXTURE" in table
    assert "not from a live desk" in table
    assert "| # | url | dated? | place? | blocked reason |" in table


def test_a_walled_fixture_page_prints_its_reason_not_a_blank():
    from tools.event_page_table import event_fixture_fetcher

    fetch, manifest = event_fixture_fetcher("austin-chronicle-eventsearch")
    walled_url = next(iter(manifest["walls"]))
    run = follow([row(walled_url, source_url="https://desk.example/EventSearch")],
                 fetch)
    assert run.visits[0].walled and run.visits[0].queued
    assert "403" in run.visits[0].blocked_reason
    assert run.rows[0].when is None and run.rows[0].place_text is None


def test_the_table_separates_what_the_page_said_from_what_the_row_carries():
    """After the contested-night ruling these are two different numbers, and
    printing only the page's would overstate what a friend would see."""
    def mixed_fetch(url: str) -> PageFetch:
        if url.endswith("clash"):
            return PageFetch(url=url, status=200, final_url=url,
                             body=DATED_AND_PLACED.replace("2026-09-11T20:00",
                                                           "2026-10-02T20:00"))
        return PageFetch(url=url, status=200, body=DATED_AND_PLACED, final_url=url)

    rows = [row("https://desk.test/event/clash", when="2026-09-11T20:00"),
            row("https://desk.test/event/agrees", when="2026-09-11T20:00")]
    run = follow(rows, mixed_fetch)
    assert run.dated_n == 2, "both pages stated a night"
    assert run.rows_dated_n == 1, "the contested row still carries a night"
    assert run.nulled_when_n == 1


# --- the calendar file is judged like any other page (evaluator, PR #237) ------

THIRD_PARTY_ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Somebody Else's Event
DTSTART:20991231T235900Z
END:VEVENT
END:VCALENDAR"""


def _ics_answer(**kwargs):
    """A fetcher whose event page advertises a same-host .ics, and whose .ics
    answers however the test says."""
    def fetch(url: str) -> PageFetch:
        if url == "https://desk.test/event/foo-1":
            return PageFetch(url=url, status=200, body=ICS_PAGE, final_url=url)
        if url == "https://desk.test/event/foo-1.ics":
            return PageFetch(url=url, **kwargs)
        return PageFetch(url=url, status=404, final_url=url, error="HTTP 404")
    return fetch


def test_a_calendar_file_that_redirects_off_host_is_not_this_pages_statement():
    """The pre-fetch same-host check judges the ADVERTISED address; the
    redirect happens after it. Without the landing check a third party's
    DTSTART fills `when` as if the event page stated it."""
    run = follow([row()], _ics_answer(
        status=200, body=THIRD_PARTY_ICS,
        final_url="https://calendars.thirdparty.test/x.ics"))
    assert run.rows[0].when is None, "a stranger's calendar dated this row"
    assert run.visits[0].statement.when_source is None
    assert any("redirected off the desk's host" in n
               for n in run.visits[0].statement.notes)


def test_a_calendar_file_that_answers_a_wall_is_not_parsed():
    run = follow([row()], _ics_answer(
        status=403, body=THIRD_PARTY_ICS,
        final_url="https://desk.test/event/foo-1.ics"))
    assert run.rows[0].when is None
    assert any("closed door" in n for n in run.visits[0].statement.notes)


def test_a_calendar_file_that_answers_an_error_page_is_not_parsed():
    """A 500 that still returns a body — checking only `error` parses it."""
    run = follow([row()], _ics_answer(
        status=500, body=THIRD_PARTY_ICS,
        final_url="https://desk.test/event/foo-1.ics"))
    assert run.rows[0].when is None
    assert any("HTTP 500" in n for n in run.visits[0].statement.notes)


def test_a_same_host_calendar_that_lands_where_it_said_still_works():
    """The fix must refuse strangers, not calendars."""
    run = follow([row()], fetcher({
        "https://desk.test/event/foo-1": ICS_PAGE,
        "https://desk.test/event/foo-1.ics": ICS_BODY}))
    assert run.rows[0].when == "2026-09-11T20:00:00Z"
    assert run.visits[0].statement.when_source == "ics"
