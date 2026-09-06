"""The field tick, as tests that can fail — ONE-LIVE-ENTITY-SPLIT-LAW.md §4.

A happening whose `listing_url` is an identity permalink gets its date and place
from THAT page. Never from a guess, never from another page, never from a clock
with no day beside it.

The three cases the ticket names:
  (a) a list card with no date + an event page saying "Sat Sep 6 - 9:00PM"
      -> the row is DATED, from the event page
  (b) an event page printing a clock and no date -> the row stays NULL
  (c) a date from the LIST page must not attach to the event page's clock —
      cross-page assembly is the exact thing "same page" forbids, and it is the
      one that would look right in every table while being an instant nobody
      published

Nothing here is desk-specific: every host is a test host, the patterns are
passed in as the same DATA a live run reads from
`sources/identity_patterns.json`, and no test opens a socket.
"""
from __future__ import annotations

import os
from datetime import date

import pytest

from worker.locale import desk_follow as df
from worker.locale import identity_patterns as ip
from worker.locale.desk_read import Happening
from worker.locale.desk_walk import PageFetch

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The day the pages were fetched on. Every test that needs a weekday-pinned
#: year states it, because the module refuses to pin one without an anchor —
#: there is no "today" inside it.
AS_OF = date(2026, 9, 1)

PATTERNS = (ip.IdentityPattern(
    pattern_id="test-event", host_family="desk.test", path_re=r"/event/[^/]+-\d+",
    grade="fixture_shape", owned=False, note="test"),)


def row(title="Dominic Fike", *, when=None, when_text=None, place_text=None,
        listing_url="https://desk.test/event/dominic-fike-1",
        source_url="https://desk.test/events/today") -> Happening:
    """One happening as the LIST page left it — holes and all."""
    return Happening(
        title=title, when=when, when_text=when_text,
        when_precision=("date" if when and len(when) == 10 else
                        "datetime" if when else None),
        place_text=place_text, via="Test Desk", kind="other",
        door_id="test-desk", door_type="local_desk", locale_id="us-tx-capcog",
        source_url=source_url, listing_url=listing_url,
    )


def fetcher(pages, *, calls=None):
    """A fetcher over committed page text. Records every URL it is asked for, so
    a test can assert that a page was opened ONCE and never retried."""
    def fetch(url: str) -> PageFetch:
        if calls is not None:
            calls.append(url)
        page = pages.get(url)
        if page is None:
            return PageFetch(url=url, status=404)
        if isinstance(page, PageFetch):
            return page
        return PageFetch(url=url, status=200, body=page, final_url=url)
    return fetch


# --- (a) the event page dates the row ---------------------------------------

EVENT_PAGE_DATED = """<!doctype html><html><body>
<h1>Dominic Fike</h1>
<p class="date-line">Sat Sep 5 &bull; 9:00PM</p>
<div class="venue">Moody Amphitheater</div>
<p>Doors open early. All ages.</p>
</body></html>"""

#: The founder's example string, verbatim. Kept as its own case rather than
#: edited into the fixture above, because what it does is a REAL finding about
#: this rule and not a typo to tidy away — see the test below.
EVENT_PAGE_FOUNDER_EXAMPLE = EVENT_PAGE_DATED.replace("Sat Sep 5", "Sat Sep 6")


def test_a_list_card_with_no_date_is_dated_by_its_own_event_page():
    """(a) The list card printed a title and a link. The event page printed the
    day and the time. The row comes out dated, and says which page dated it."""
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.fetched == 1
    got = result.rows[0]
    assert got.when == "2026-09-05T21:00:00"
    assert got.when_precision == "datetime"
    assert got.detail_url == "https://desk.test/event/dominic-fike-1"
    assert got.filled_from_detail == ("when", "place_text")
    assert result.dated == 1


def test_the_day_comes_from_the_page_and_the_year_from_the_page_s_own_weekday():
    """"Sat Sep 5" states no year. The year is not assumed: it is the ONE year
    in the fetch-anchored window where Sep 5 really IS a Saturday (R-030) —
    2026 here, because 2027-09-05 is a Sunday. No "this year", no next
    occurrence."""
    assert date(2026, 9, 5).weekday() == 5
    assert date(2027, 9, 5).weekday() == 6
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when.startswith("2026-09-05")


def test_a_weekday_that_contradicts_the_day_dates_nothing():
    """The founder's example string run LITERALLY: "Sat Sep 6 - 9:00PM".

    Sep 6 2026 is a SUNDAY. A page printing "Sat Sep 6" has therefore
    contradicted itself about which day it means, and the weekday is a checksum
    rather than decoration: R-030 supplies a missing year only where exactly ONE
    year in the fetch-anchored window carries that month/day on that weekday,
    and refuses otherwise. Nothing here reaches for "the next Sep 6".

    So this string yields a HOLE, and that is the rule working: the alternative
    is publishing 2026-09-06 for a page that said Saturday, which is a wrong day
    on a public row. A page whose weekday matches (the fixture above), one that
    prints a year, or one carrying `<time datetime>`/JSON-LD all date normally.
    """
    assert date(2026, 9, 6).weekday() == 6
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_FOUNDER_EXAMPLE}),
        patterns=PATTERNS, as_of=AS_OF)
    got = result.rows[0]
    assert got.when is None
    assert got.place_text == "Moody Amphitheater"     # the place still fills
    assert any("no date" in r for r in result.reads[0].refusals)


def test_the_same_page_with_a_year_printed_dates_without_any_pinning():
    """No weekday arithmetic is involved when the page simply says the year."""
    page = EVENT_PAGE_FOUNDER_EXAMPLE.replace("Sat Sep 6", "September 6, 2026")
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": page}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when == "2026-09-06T21:00:00"


def test_with_no_fetch_day_a_weekday_only_page_cannot_pin_a_year_and_stays_null():
    """No anchor, no pinning — R-030 turns weekday resolution OFF rather than
    reaching for "this year", and so does the tick that calls it."""
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED}),
        patterns=PATTERNS, as_of=None)
    assert result.rows[0].when is None
    assert result.dated == 0


def test_the_place_comes_from_the_event_page_too():
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].place_text == "Moody Amphitheater"
    assert result.placed == 1


def test_a_structured_event_page_states_its_own_instant():
    """A page publishing schema.org is read as data first: the instant is the
    one it published, not one assembled from prose."""
    page = """<!doctype html><html><head><script type="application/ld+json">
    {"@type": "MusicEvent", "name": "Dominic Fike",
     "startDate": "2026-09-06T21:00:00-05:00",
     "location": {"@type": "Place", "name": "The Hall"}}
    </script><title>Dominic Fike</title></head>
    <body><p>Sat Sep 6 &bull; 9:00PM</p></body></html>"""
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": page}),
        patterns=PATTERNS, as_of=AS_OF)
    got = result.rows[0]
    assert got.when == "2026-09-06T21:00:00-05:00"
    assert got.place_text == "The Hall"


def test_an_ics_body_at_the_permalink_is_read_as_the_page_s_own_statement():
    page = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Dominic Fike\r\n"
            "DTSTART:20260906T210000\r\nLOCATION:The Hall\r\n"
            "END:VEVENT\r\nEND:VCALENDAR\r\n")
    read = df.field_read(page, url="https://desk.test/event/dominic-fike-1",
                         as_of=AS_OF)
    assert read.when_carrier == "ics"
    assert read.when.startswith("2026-09-06T21:00")


# --- (b) a clock with no date stays NULL -------------------------------------

EVENT_PAGE_CLOCK_ONLY = """<!doctype html><html><body>
<h1>Dominic Fike</h1>
<p class="time">Doors 9:00PM</p>
<div class="venue">Moody Amphitheater</div>
</body></html>"""


def test_an_event_page_stating_a_clock_and_no_date_leaves_the_row_null():
    """(b) A time with no day is not a moment. The row keeps its hole, the place
    is still filled, and the refusal says why in the page's own terms."""
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_CLOCK_ONLY}),
        patterns=PATTERNS, as_of=AS_OF)
    got = result.rows[0]
    assert got.when is None
    assert got.when_precision is None
    assert result.dated == 0
    assert got.place_text == "Moody Amphitheater"      # the other field still fills
    read = result.reads[0]
    assert any("clock" in r and "no date" in r for r in read.refusals), read.refusals


def test_the_clock_only_page_is_not_rescued_by_the_run_s_own_calendar():
    """The anchor day exists (as_of), and it still does not become the event's
    day. `as_of` may only PIN a year onto a date the page printed — it is never
    a date of its own."""
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_CLOCK_ONLY}),
        patterns=PATTERNS, as_of=date(2026, 9, 6))
    assert result.rows[0].when is None


# --- (c) no cross-page assembly ----------------------------------------------

def test_a_date_from_the_list_page_never_attaches_to_the_event_page_s_clock():
    """(c) The list card stated the day. The event page states only a clock.
    Joining them would produce 2026-09-06T21:00 — an instant NEITHER page
    published, and one that would look correct in every table we print.

    The row keeps exactly what the list card said, at the precision the list
    card said it, and the event page contributes no date at all.
    """
    listed = row(when="2026-09-06", when_text="Sun Sep 6")
    result = df.follow([listed], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_CLOCK_ONLY}),
        patterns=PATTERNS, as_of=AS_OF)
    got = result.rows[0]
    assert got.when == "2026-09-06"                     # unchanged
    assert got.when_precision == "date"                 # NOT upgraded to a time
    assert got.when_text == "Sun Sep 6"                 # the list's own words
    assert "when" not in got.filled_from_detail
    assert result.dated == 0
    # And the page itself is read as stating no date, so nothing downstream can
    # mistake the list's day for the event page's word.
    assert result.reads[0].when is None


def test_the_event_page_never_overwrites_a_date_the_list_page_stated():
    """Two doors disagreeing is not this tick's to settle: correcting a
    published field is `worker/listing_update.py`'s reviewed seam. The follow
    fills holes, and only holes."""
    listed = row(when="2026-09-06T20:00:00", place_text="The Other Hall")
    result = df.follow([listed], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED}),
        patterns=PATTERNS, as_of=AS_OF)
    got = result.rows[0]
    assert got.when == "2026-09-06T20:00:00"
    assert got.place_text == "The Other Hall"
    assert result.dated == 0 and result.placed == 0


def test_a_row_with_both_fields_is_not_opened_at_all():
    """It has nothing to fill, and the budget belongs to the rows that do."""
    calls = []
    listed = row(when="2026-09-06T20:00:00", place_text="The Hall")
    result = df.follow([listed], fetcher({}, calls=calls), patterns=PATTERNS,
                       as_of=AS_OF)
    assert calls == []
    assert result.eligible == 1 and result.skipped_complete == 1
    assert result.fetched == 0


def test_when_text_travels_with_the_instant_it_justifies():
    """A filled row must be COHERENT, not merely filled: the words beside the
    date are the words that produced it. A list card's prose left sitting next
    to an event page's instant is the same cross-page mixture as (c), one field
    over."""
    listed = row(when_text="this weekend")
    result = df.follow([listed], fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED}),
        patterns=PATTERNS, as_of=AS_OF)
    got = result.rows[0]
    assert got.when.startswith("2026-09-05")
    assert "this weekend" not in (got.when_text or "")
    assert "Sat Sep 5" in got.when_text


# --- cardinality: one page, one happening ------------------------------------

def test_a_page_stating_two_different_days_dates_nothing():
    """RED_CLASSES missing-cardinality-check: more than one is not a longer list
    to pick from. Which day this happening is on is exactly what is not stated,
    and the first one would be a real, well-formed, wrong date."""
    page = """<!doctype html><html><body><h1>Dominic Fike</h1>
    <time datetime="2026-09-06T21:00">Sun Sep 6</time>
    <time datetime="2026-09-07T21:00">Mon Sep 7</time>
    <div class="venue">The Hall</div></body></html>"""
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": page}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when is None
    assert any("2 different dates" in r for r in result.reads[0].refusals)


def test_zero_one_and_many_dates_are_three_different_outcomes():
    """The same class, asserted as the three-way split it actually is.

    Each fixture carries a heading because since r12 a page printing none, in
    no sectioning element, identifies no subject and states nothing at all —
    which is a different refusal from the three under test here."""
    none_stated = df.field_read(
        "<html><body><h1>A Show</h1></body></html>", url="u", as_of=AS_OF)
    one = df.field_read(
        '<html><body><h1>A Show</h1>'
        '<time datetime="2026-09-06">Sun</time></body></html>',
        url="u", as_of=AS_OF)
    many = df.field_read(
        '<html><body><h1>A Show</h1>'
        '<time datetime="2026-09-06">a</time>'
        '<time datetime="2026-09-08">b</time></body></html>', url="u", as_of=AS_OF)
    assert (none_stated.when, one.when, many.when) == (None, "2026-09-06", None)
    assert any("no date" in r for r in none_stated.refusals)
    assert any("2 different dates" in r for r in many.refusals)
    assert one.when_precision == "date"


def test_a_page_printing_two_clocks_keeps_the_day_and_holes_the_time():
    """"Doors 7pm, show 9pm" does not say which one this happening starts at.
    The day the page stated still stands — refusing the time is not refusing the
    date."""
    page = """<!doctype html><html><body><h1>A Show</h1>
    <p>Sat Sep 5 &mdash; doors 7:00PM, show 9:00PM</p>
    <div class="venue">The Hall</div></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.when == "2026-09-05"
    assert read.when_precision == "date"
    assert any("different clocks" in r for r in read.refusals)


def test_a_complete_instant_records_no_clock_complaint():
    """The live table's own defect, pinned — with the premise r14 changed.

    The rule this pins is the DIAGNOSTIC one: a row whose clock is settled has
    no clock hole, so recording `clocks-ambiguous` against it made the run
    report that 7 of 40 opened pages (17%) needed a repair their rows did not
    need, and the next ticket is chosen by whichever count is largest.

    What changed at r14 is which rows are settled. The fixture used to be
    `/event/boeing-boeing-14285657` — node 19:30, card printing "Matinees 4:45
    pm. Late show 10:15 pm." — and that row is now HOLED, because the card
    prints clocks and the node's is none of them (see
    `test_a_run_printing_other_performances_holes_the_clock` for that half and
    its cost). So the settled case is stated the way it actually is: the card's
    clocks include the node's, and the extra ones do not make a hole."""
    page = """<!doctype html><html><body>
    <script type="application/ld+json">{"@type": "Event", "name": "Boeing",
      "startDate": "2026-09-18T19:30:00-05:00"}</script>
    <h1>Boeing Boeing</h1>
    <p>Doors 7:00 pm. Curtain 7:30 pm.</p>
    <div class="venue">TexARTS</div></body></html>"""
    read = df.field_read(page, url="https://desk.test/event/boeing-2", as_of=AS_OF)
    assert read.when == "2026-09-18T19:30:00-05:00"
    assert read.when_precision == "datetime"
    assert "clocks-ambiguous" not in read.codes, read.refusals


def test_a_run_printing_other_performances_holes_the_clock():
    """The cost of r14's rule, pinned so it is a decision and not a surprise.

    `/event/boeing-boeing-14285657` prints "Matinees 4:45 pm. Late show 10:15
    pm." while its node states 19:30. Its evening curtain is in the markup and
    nowhere in the visible text, so under membership the node's clock is none of
    the card's and the time is holed while the day stands.

    That is the same answer r8 gave for DAYS, and deliberately the same rule
    rather than two: a contradiction is the card not carrying the node's answer.
    Telling "matinees" and "late show" (other performances) from "doors" and
    "show" (this one) needs a list of label words, refused on the record at r1 —
    so the honest price of never publishing a time the visible page does not
    state is holing the clock on a desk that describes a RUN. Modelling runs is
    the next ticket's work; `dated_n` falling is this one's measurement of how
    much of this desk is runs."""
    page = """<!doctype html><html><body>
    <script type="application/ld+json">{"@type": "Event", "name": "Boeing",
      "startDate": "2026-09-18T19:30:00-05:00"}</script>
    <h1>Boeing Boeing</h1>
    <p>Matinees 4:45 pm. Late show 10:15 pm.</p>
    <div class="venue">TexARTS</div></body></html>"""
    read = df.field_read(page, url="https://desk.test/event/boeing-2", as_of=AS_OF)
    assert read.when == "2026-09-18", read.when
    assert read.when_precision == "date"
    assert "card-contradicts-its-own-markup" in read.codes
    # The DAY still stands, and the venue still comes through: refusing the
    # clock is not refusing the date, and neither is refusing the node.
    assert read.place_text == "TexARTS"


def test_a_day_without_a_time_still_records_the_clock_complaint():
    """The converse, so the fix above cannot silence a real hole: the same
    contradictory prose on a page whose date carries NO time leaves the time a
    hole, and the hole keeps its reason."""
    page = """<!doctype html><html><body>
    <h1>Boeing Boeing</h1>
    <p><time datetime="2026-09-18">Fri Sep 18</time></p>
    <p>Matinees 4:45 pm. Late show 10:15 pm.</p>
    <div class="venue">TexARTS</div></body></html>"""
    read = df.field_read(page, url="https://desk.test/event/boeing-3", as_of=AS_OF)
    assert read.when == "2026-09-18"
    assert read.when_precision == "date"
    assert "clocks-ambiguous" in read.codes, read.refusals


def test_a_related_cards_venue_is_not_this_happenings_place():
    """Evaluator, PR #235 r4 second pass, openai/attacker-smuggle — reproduced
    before fixing.

    The date path got its scope, its locality and its per-node binding across
    four rounds. The place fallback still took "the one labelled venue anywhere
    in the content", so a page whose own listing carries no venue markup, beside
    a related card that does, published that card's room as this happening's:

        PRE-FIX   when=2026-09-06T21:00:00  place='The Other Room'  codes=()

    Cardinality of one, so nothing to refuse as ambiguous, and no code recorded.
    The unbound fallback has no way to say whose venue it found — so when the
    page's content also points at other happenings, one labelled venue is a coin
    flip between this row and the card beside it."""
    page = """<html><body><main>
      <article><h1>Dominic Fike</h1>
        <time datetime="2026-09-06T21:00">Sun Sep 6</time></article>
      <section class="related"><h2>You might also like</h2>
        <a href="/event/other-99">Some Other Show</a>
        <div class="venue">The Other Room</div></section>
    </main></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-06T21:00:00"      # the date path is unaffected
    assert read.place_text is None
    # r5 added the CARD boundary, which catches this one step earlier: the
    # related card's venue is outside the section holding the page's heading,
    # so it is never a candidate at all and the page labels no place of its own.
    assert "no-place" in read.codes, read.refusals


def test_the_other_happenings_rule_still_bites_on_a_page_with_no_sections():
    """A page whose heading is in no section is ONE card, so the card boundary
    cannot separate anything on it — and that is exactly where round 4's rule
    is still the only thing standing between a promo venue and the row."""
    page = """<html><body><h1>Dominic Fike</h1>
      <time datetime="2026-09-06T21:00">Sun Sep 6</time>
      <a href="/event/other-99">Some Other Show</a>
      <div class="venue">The Other Room</div>
    </body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text is None
    assert "place-among-other-happenings" in read.codes, read.refusals
    assert any("other-99" in r for r in read.refusals), read.refusals


def test_a_page_that_states_its_own_venue_still_states_it():
    """The converse. A page carrying its own venue markup is unaffected by the
    rule above — the fallback is refused only where another happening is on the
    page to be confused with."""
    page = """<html><body><main>
      <article><h1>Dominic Fike</h1>
        <time datetime="2026-09-06T21:00">Sun Sep 6</time>
        <div class="venue">The Hall</div></article>
    </main></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text == "The Hall"
    assert "place-among-other-happenings" not in read.codes


def test_this_pages_own_address_is_not_another_happening():
    """A permalink page linking to ITSELF — a share button, a canonical link, a
    breadcrumb back to the listing — names no other happening, so it must not
    cost the page its own venue."""
    page = f"""<html><body><main>
      <article><h1>Dominic Fike</h1>
        <a href="{HERE}">Permalink</a>
        <time datetime="2026-09-06T21:00">Sun Sep 6</time>
        <div class="venue">The Hall</div></article>
    </main></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text == "The Hall", read.refusals


def test_a_bound_nodes_venue_beats_a_related_card_entirely():
    """The refusal above is the UNBOUND fallback's. A structured node that
    speaks for this row states the venue on its own authority, and a related
    card on the same page cannot take it away — otherwise closing the finding
    would have cost every page that markup its venue properly."""
    page = f"""<html><head><script type="application/ld+json">
    {{"@type":"Event","name":"Dominic Fike","url":"{HERE}",
      "startDate":"2026-09-06T21:00:00-05:00",
      "location":{{"@type":"Place","name":"The Hall"}}}}</script></head>
    <body><main><article><h1>Dominic Fike</h1></article>
      <section class="related"><a href="/event/other-99">Other</a>
        <div class="venue">The Other Room</div></section>
    </main></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text == "The Hall", read.refusals


def test_two_labelled_places_name_no_place():
    page = """<!doctype html><html><body><h1>A Show</h1>
    <time datetime="2026-09-06">Sun Sep 6</time>
    <div class="venue">The Hall</div><div class="venue">The Park</div>
    </body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.place_text is None
    assert any("2 different places" in r for r in read.refusals)


def test_a_nested_location_markup_is_one_place_not_two():
    # The `<article><h1>` is scaffolding (see r12): a page with no heading and
    # no sectioning element identifies no subject and states nothing.
    page = """<!doctype html><html><body><article><h1>A Show</h1>
    <div itemprop="location">The Hall <span itemprop="address">100 Main St</span></div>
    <time datetime="2026-09-06">Sun Sep 6</time></article></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.place_text == "The Hall 100 Main St"
    assert read.place_carrier == "labelled"


# --- event scope: whose statement is this? -----------------------------------
# Evaluator, PR #235 (openai/absence-only), BLOCKING and reproduced before
# fixing: without an event-scope check, "the only date anywhere on the page" and
# "the only clock anywhere on the page" were joined into this happening's start.
# Both halves published a well-formed instant nobody stated.

FOOTER_STAMP = """<!doctype html><html><body>
<article><h1>Dominic Fike</h1>
  <p class="time">Doors 9:00PM</p>
  <div class="venue">Moody Amphitheater</div></article>
<footer><p>Last updated September 3, 2026</p></footer>
</body></html>"""

BOX_OFFICE = """<!doctype html><html><body>
<article><h1>Dominic Fike</h1>
  <p class="date-line">Sat Sep 5</p></article>
<footer><p>Box office opens 10:00AM daily</p></footer>
</body></html>"""


def test_a_page_timestamp_in_the_footer_is_not_the_shows_day():
    """Reproduced on the first implementation as `2026-09-03T21:00:00` — the
    footer's "last updated" stamp joined to the event's own doors time. The
    page never said what day the show is."""
    read = df.field_read(FOOTER_STAMP, url="u", as_of=AS_OF)
    assert read.when is None
    assert any("plumbing" in r for r in read.refusals), read.refusals
    assert read.place_text == "Moody Amphitheater"    # the place still fills


def test_a_box_office_clock_elsewhere_is_not_the_shows_time():
    """Reproduced as `2026-09-05T10:00:00` — the box office's opening hour
    published as the door time. The DAY stands: refusing the time is not
    refusing the date, and a missing minute is not a missing night."""
    read = df.field_read(BOX_OFFICE, url="u", as_of=AS_OF)
    assert read.when == "2026-09-05"
    assert read.when_precision == "date"


def test_the_clock_must_come_from_the_statement_that_gave_the_day():
    """Two blocks are two statements. One block — however it is marked up
    inside — is one.

    The `<article><h1>` is scaffolding, not the rule under test: since r12 a
    page printing NO heading and NO sectioning element identifies no subject
    and states nothing, so a fixture testing the CLOCK rule has to give the
    page a card to state its clock in. The heading-less case has its own test
    (`test_a_page_with_no_heading_and_no_sections_states_nothing`)."""
    apart = ('<html><body><article><h1>A Show</h1>'
             '<div class="date">Sat Sep 5</div>'
             '<div class="clock">9:00PM</div></article></body></html>')
    together = ('<html><body><article><h1>A Show</h1>'
                '<div><span class="date">Sat Sep 5</span> '
                '<span class="t">9:00PM</span></div></article></body></html>')
    assert df.field_read(apart, url="u", as_of=AS_OF).when == "2026-09-05"
    assert df.field_read(together, url="u", as_of=AS_OF).when == "2026-09-05T21:00:00"


def test_a_time_tag_in_the_page_chrome_dates_nothing():
    chrome = ('<html><body><nav><time datetime="2026-09-06T21:00">Sun</time></nav>'
              '<article><h1>A Show</h1></article></body></html>')
    content = ('<html><body><article><h1>A Show</h1>'
               '<time datetime="2026-09-06T21:00">Sun</time></article></body></html>')
    assert df.field_read(chrome, url="u", as_of=AS_OF).when is None
    assert df.field_read(content, url="u", as_of=AS_OF).when == "2026-09-06T21:00:00"


def test_a_structured_event_needs_no_segment_to_own_it():
    """A schema.org `Event.startDate` says WHOSE start it is, so it is event
    scoped by construction — the one carrier that needs no locality check."""
    page = """<html><head><title>A Show</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"A Show","startDate":"2026-09-06T21:00:00-05:00",
     "location":{"@type":"Place","name":"The Hall"}}</script></head>
    <body><footer>updated somewhere</footer></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.when == "2026-09-06T21:00:00-05:00"
    assert read.place_text == "The Hall"


def test_a_publishers_own_address_in_the_footer_is_not_the_venue():
    """The same defect one field over: a `<footer class="address">` holding the
    publisher's office would give every happening on that desk the desk's own
    address."""
    page = """<html><body><article><h1>A Show</h1>
    <time datetime="2026-09-06T21:00">Sun</time></article>
    <footer><div class="address">PO Box 1, Publisher HQ</div></footer></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.place_text is None
    assert read.when == "2026-09-06T21:00:00"


def test_the_scope_rule_is_structural_not_a_list_of_chrome_words():
    """"updated", "posted", "box office" are English, and an enumeration of them
    would look complete while missing the next one. The rule is HTML's own
    sectioning: nav/aside always, header/footer at page scope — the same sets
    `desk_read` already uses to keep a nav link from becoming a listing."""
    from worker.locale import desk_read
    assert df.FURNITURE_TAGS is desk_read.FURNITURE_TAGS
    assert df.SCOPED_FURNITURE_TAGS is desk_read.SCOPED_FURNITURE_TAGS
    # A card's OWN header is not page chrome — HTML scopes it to the article.
    card = ('<html><body><article><header>'
            '<time datetime="2026-09-06T21:00">Sun</time></header></article></body></html>')
    assert df.field_read(card, url="u", as_of=AS_OF).when == "2026-09-06T21:00:00"


def test_a_footer_stamp_does_not_make_a_page_that_states_its_day_ambiguous():
    """Scope is asked BEFORE cardinality, and the live run is why.

    Counting every date on the document first refuses a page that states its day
    perfectly well and prints a "last updated" stamp in its footer: two dates,
    ambiguous, hole. That is how a rule which is right about a page nobody
    publishes is still wrong about every page anybody does — 40 of 40 opened
    pages came back `dates-ambiguous` on the first live run.

    The stamp is excluded first; what is left is counted; one date remains, and
    the clock in its own sentence still joins it.
    """
    page = """<!doctype html><html><body>
    <article><h1>A Show</h1><p class="when">Sat Sep 5 &bull; 9:00PM</p>
    <div class="venue">The Hall</div></article>
    <footer><p>Last updated September 3, 2026</p></footer></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.when == "2026-09-05T21:00:00"
    assert read.place_text == "The Hall"
    assert read.codes == ()


#: A month grid, as every one of this desk's event pages prints beside the
#: listing. The live run's own words: "page states 31 different dates".
CALENDAR_WIDGET = "".join(
    f'<td><a href="/day/{d}">{d}</a> Sep {d}, 2026</td>' for d in range(1, 32))


def test_a_structured_start_date_is_not_outvoted_by_a_calendar_widget():
    """The ladder's own rule — never mix tiers — applied to fields.

    A schema.org `Event.startDate` states WHOSE start it is; the prose around it
    does not, so it is not a competing claim to be counted against it. Without
    this, an event page that declares its start perfectly well goes dateless the
    moment it also prints a month grid — which is what the first live run found
    on every page it opened.
    """
    page = f"""<html><head><script type="application/ld+json">
    {{"@type":"Event","name":"A Show","startDate":"2026-09-06T21:00:00-05:00",
      "location":{{"@type":"Place","name":"The Hall"}}}}</script></head>
    <body><article><h1>A Show</h1></article>
    <table>{CALENDAR_WIDGET}</table></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.when == "2026-09-06T21:00:00-05:00"
    assert read.when_carrier == "jsonld"
    assert read.codes == ()


def test_within_the_structured_tier_cardinality_still_bites():
    """Not a loosening: two `startDate`s BOTH claiming this address are still
    two answers to one question."""
    here = "https://desk.test/event/dominic-fike-1"
    page = f"""<html><head>
    <script type="application/ld+json">{{"@type":"Event","url":"{here}",
      "startDate":"2026-09-06T21:00:00"}}</script>
    <script type="application/ld+json">{{"@type":"Event","url":"{here}",
      "startDate":"2026-09-08T21:00:00"}}</script>
    </head><body><article><h1>A</h1></article></body></html>"""
    read = df.field_read(page, url=here, as_of=AS_OF)
    assert read.when is None
    assert "dates-ambiguous" in read.codes


def test_two_unaddressed_structured_nodes_speak_for_nobody():
    """Two Event nodes and neither names an address: the page has published two
    events and said nothing about which is its own. The lone-node allowance is
    exactly that — for ONE node."""
    page = """<html><head>
    <script type="application/ld+json">{"@type":"Event","startDate":"2026-09-06T21:00:00"}</script>
    <script type="application/ld+json">{"@type":"Event","startDate":"2026-09-08T21:00:00"}</script>
    </head><body><article><h1>A</h1></article></body></html>"""
    read = df.field_read(page, url="https://desk.test/event/a-1", as_of=AS_OF)
    assert read.when is None
    assert "structured-not-bound" in read.codes


def test_a_calendar_widget_outside_the_card_does_not_poison_the_page():
    """This test previously asserted the opposite, and the card boundary is why
    the premise changed rather than the standard.

    Its old reasoning was that the page "only prints one date among thirty-one".
    That is not what this page does. It prints ONE date in the article holding
    its own heading, beside a navigation calendar that is about no happening at
    all — and the first live run refused 40 of 40 pages on exactly this shape.
    The structured tier rescued the pages that declare a start; pages that only
    print one stayed poisoned until the card boundary (evaluator, PR #235 r5)
    said what the widget is: outside the page's card, therefore not its
    statement.

    A page whose own card is genuinely ambiguous still refuses — see below."""
    page = f"""<html><body>
    <article><h1>A Show</h1><p>Sat Sep 5 &bull; 9:00PM</p></article>
    <table>{CALENDAR_WIDGET}</table></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.when == "2026-09-05T21:00:00", read.refusals


def test_a_promo_heading_above_the_article_does_not_become_the_subject():
    """Evaluator, PR #235 r6, openai/attacker-smuggle — reproduced before fixing.

    The card boundary took the FIRST heading of any of h1/h2/h3 as the page's
    subject. A promotional block placed above the real article carries its own
    `<h2>`, date and venue — so it became the subject, and the real event
    content was pushed OUTSIDE the card:

        PRE-FIX   when=2026-12-25T20:00:00  place='The Other Room'  codes=()

    `<h1>` is the page's subject by HTML's own semantics. A subheading is not a
    subject while a subject exists."""
    page = """<html><body><main>
      <section class="promo"><h2>Some Other Show</h2>
        <p>Friday, December 25, 2026 &mdash; 8:00PM</p>
        <div class="venue">The Other Room</div></section>
      <article><h1>Dominic Fike</h1>
        <p>Saturday, September 5, 2026 &mdash; 9:00PM</p>
        <div class="venue">The Hall</div></article>
    </main></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-05T21:00:00", read.refusals
    assert read.place_text == "The Hall"


def test_a_page_whose_only_heading_is_an_h2_still_has_a_card():
    """The converse of the rule above: h2/h3 stand in for a page that prints no
    `<h1>` at all, so such a page keeps its boundary rather than losing it."""
    page = """<html><body><main>
      <article><h2>Dominic Fike</h2>
        <p>Saturday, September 5, 2026 &mdash; 9:00PM</p>
        <div class="venue">The Hall</div></article>
      <section class="promo"><p>Friday, December 25, 2026</p>
        <div class="venue">The Other Room</div></section>
    </main></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-05T21:00:00", read.refusals
    assert read.place_text == "The Hall"


def test_a_sectionless_heading_does_not_disable_the_boundary():
    """Evaluator, PR #235 r6, openai/attacker-smuggle — reproduced before fixing.

    "A page whose heading is in no section is ONE card" was a permissive
    fallback, and it disabled the boundary for the whole page: an unlinked promo
    `<section>` elsewhere in the body supplied the only date and venue.

        PRE-FIX   when=2026-12-25T20:00:00  place='The Other Room'  codes=()

    When the heading sits in no section, the card IS the page level — and a
    section is a different card."""
    page = """<html><body>
      <h1>Dominic Fike</h1><p>Tickets at the door.</p>
      <section class="promo"><p>Friday, December 25, 2026 &mdash; 8:00PM</p>
        <div class="venue">The Other Room</div></section>
    </body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when
    assert read.place_text is None


def test_a_page_with_no_heading_and_two_cards_chooses_neither():
    """Evaluator, PR #235 r9, openai/absence-only — reproduced before fixing.

    The card rule's THIRD case, and the last of its defaults to be fail-open. A
    page printing no heading at all set the subject to None, which
    `_inside_the_card` read as "exclude nothing" — so an image-headed page with
    an unrelated promo `<section>` published that section's date and venue:

        PRE-FIX   when=2026-12-25T20:00:00  place='The Other Room'  codes=()

    Not knowing what a page is about is a reason to trust it LESS, not more."""
    page = """<html><head><title>Dominic Fike</title></head><body><main>
      <article><img src="hero.jpg" alt=""><p>Tickets at the door.</p></article>
      <section class="promo"><p>Friday, December 25, 2026 &mdash; 8:00PM</p>
        <div class="venue">The Other Room</div></section>
    </main></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when
    assert read.place_text is None


def test_a_page_with_no_heading_and_one_card_still_states_its_fields():
    """The converse, and why the rule is not simply "no heading, no fields": a
    heading-less page whose content sits in ONE card is unambiguous — that card
    is the only thing the page could be about. Three existing tests failed on
    the blunter version, which is how this clause was found."""
    page = """<html><head><title>Dominic Fike</title></head><body>
      <article><img src="hero.jpg" alt="">
        <p>Saturday, September 5, 2026 &mdash; 9:00PM</p>
        <div class="venue">The Hall</div></article>
    </body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-05T21:00:00", read.refusals
    assert read.place_text == "The Hall"


def test_a_sectionless_page_still_states_its_own_day_and_venue():
    """The converse, so the clause above cannot be read as "a sectionless page
    states nothing": statements at the page level, beside the heading, are the
    page's own."""
    page = """<html><body>
      <h1>Dominic Fike</h1>
      <p>Saturday, September 5, 2026 &mdash; 9:00PM</p>
      <div class="venue">The Hall</div>
    </body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-05T21:00:00", read.refusals
    assert read.place_text == "The Hall"


def test_an_h2_subject_is_a_heading_the_identity_check_can_read():
    """Evaluator, PR #235 r6, openai/absence-only — reproduced before fixing.

    Two definitions of "the page's heading" had drifted: the card boundary
    already treated `<h2>` as a page subject, while `_headings` read only
    `<h1>`/`<title>`. So a page whose visible subject is an `<h2>` had NOTHING
    for the contradiction check to compare against, and a poisoned node
    claiming this URL while naming another show sailed through:

        PRE-FIX   when=2026-12-25T20:00:00-06:00  place='The Other Room'  codes=()
    """
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Some Other Show",
      "url":"https://desk.test/event/dominic-fike-1",
      "startDate":"2026-12-25T20:00:00-06:00",
      "location":{"@type":"Place","name":"The Other Room"}}</script></head>
    <body><article><h2>Dominic Fike</h2></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when
    assert read.place_text is None
    assert "structured-not-bound" in read.codes


def test_a_stale_title_does_not_rescue_a_node_the_heading_contradicts():
    """Evaluator, PR #235 r7, openai/absence-only — reproduced before fixing.

    `<title>` and the visible heading were fed into ONE list, and a node need
    only match ANY of them. A CMS title goes stale routinely, so a poisoned
    schema.org Event naming the STALE title matched it, contradicted nothing,
    and filled this row's holes:

        PRE-FIX   when=2026-12-25T20:00:00-06:00  place='The Other Room'
                  headings=['Some Other Show', 'Dominic Fike']

    A page that prints its own subject has said what it is about. The tab
    caption does not get a second vote."""
    page = """<html><head><title>Some Other Show</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Some Other Show",
      "url":"https://desk.test/event/dominic-fike-1",
      "startDate":"2026-12-25T20:00:00-06:00",
      "location":{"@type":"Place","name":"The Other Room"}}</script></head>
    <body><article><h1>Dominic Fike</h1></article></body></html>"""
    assert df._headings(page) == ["Dominic Fike"]
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when
    assert read.place_text is None


def test_the_title_still_speaks_for_a_page_that_prints_no_heading():
    """The converse: `<title>` is a fallback, not a reject. A page with no
    visible heading still has a name, and a node that matches it still binds —
    otherwise the fix above would hole every desk whose event page is headed by
    an image."""
    page = """<html><head><title>Dominic Fike</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Dominic Fike",
      "url":"https://desk.test/event/dominic-fike-1",
      "startDate":"2026-09-06T21:00:00-05:00",
      "location":{"@type":"Place","name":"The Hall"}}</script></head>
    <body><article><p>no heading at all</p></article></body></html>"""
    assert df._headings(page) == ["Dominic Fike"]
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-06T21:00:00-05:00", read.refusals
    assert read.place_text == "The Hall"


def test_a_heading_in_the_page_chrome_is_not_a_name_this_page_answers_to():
    """Gemini NIT, PR #235 r7 — `_headings` read a regex over raw HTML while the
    scanners suppressed plumbing, so a `<nav><h1>Browse Events</h1></nav>` was a
    name this page answered to. Reading headings from the SEGMENT SCAN removes
    the last place the heading rule was expressed twice: one walk, one
    precedence, one answer."""
    page = """<html><head><title>Dominic Fike</title></head>
    <body><nav><h1>Browse Events</h1></nav>
    <article><h1>Dominic Fike</h1>
    <p>Saturday, September 5, 2026 &mdash; 9:00PM</p></article></body></html>"""
    assert df._headings(page) == ["Dominic Fike"], df._headings(page)
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-05T21:00:00", read.refusals


def test_a_promo_subheading_is_not_a_name_this_page_answers_to():
    """A page WITH an `<h1>` does not adopt its subheadings as names. Otherwise
    the fix above would hand a poisoned node an easier target: a promotional
    `<h2>` naming another show would be a heading the node could match."""
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Some Other Show",
      "url":"https://desk.test/event/dominic-fike-1",
      "startDate":"2026-12-25T20:00:00-06:00"}</script></head>
    <body><article><h1>Dominic Fike</h1>
    <h2>Some Other Show</h2></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when


def test_a_calendar_widget_INSIDE_the_card_still_refuses():
    """The other direction, so the boundary cannot be read as "widgets are
    always ignored". Put the same grid inside the article and the page really
    has stated thirty-one days about itself — which one this happening is on is
    not stated, and picking one would be a coin flip published as a fact."""
    page = f"""<html><body>
    <article><h1>A Show</h1><p>Sat Sep 5 &bull; 9:00PM</p>
    <table>{CALENDAR_WIDGET}</table></article></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.when is None
    assert "dates-ambiguous" in read.codes


def test_two_dates_in_the_CONTENT_are_still_ambiguous():
    """The scope rule narrows WHERE a date may come from; it does not soften
    what happens when two of them come from there."""
    page = ('<html><body><article><h1>A Show</h1>'
            '<p>Sat Sep 5</p><p>Sun Sep 6</p></article></body></html>')
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.when is None
    assert "dates-ambiguous" in read.codes


def test_the_clock_is_settled_against_its_own_statement_not_the_page():
    """R-030's `block_text` is "the event's own listing block". Handing it the
    whole document instead re-admits every date the scope rule just excluded,
    and the page above loses a day and a time it stated in one sentence."""
    page = """<!doctype html><html><body>
    <article><p class="when">Sat Sep 5 &bull; 9:00PM</p></article>
    <footer><p>Last updated September 3, 2026</p></footer></body></html>"""
    assert df.field_read(page, url="u", as_of=AS_OF).when == "2026-09-05T21:00:00"


def test_plumbing_inside_plumbing_does_not_re_open_the_page():
    """Self-caught while probing the fix for this class before pushing it.

    A card's own `<footer>` nested inside the PAGE `<footer>` used to decrement
    a counter it never raised — so the rest of the page footer stopped being
    plumbing, and "Last updated September 3, 2026" came back as the show's day
    (`2026-09-03`). Whether an element OPENED plumbing is now remembered on the
    stack, and only that element closes it.
    """
    page = """<!doctype html><html><body>
    <article><h1>A Show</h1><p class="time">Doors 9:00PM</p></article>
    <footer>
      <article><footer>site links</footer></article>
      <p>Last updated September 3, 2026</p>
      <div class="address">PO Box 1</div>
    </footer></body></html>"""
    assert df.segments(page) == ["A Show", "Doors 9:00PM"]
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.when is None
    assert read.place_text is None


def test_the_fabricated_instant_cannot_reach_a_row():
    """End to end, through `follow`: the row keeps its hole rather than carrying
    a date that page never stated about it."""
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": FOOTER_STAMP}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when is None
    assert result.dated == 0
    assert result.rows[0].place_text == "Moody Amphitheater"


# --- which URLs may be opened at all -----------------------------------------

def test_an_off_origin_permalink_is_not_opened_and_the_row_is_not_dropped():
    """On-origin only, this ticket. The address stays on the row as the next
    step it always was: nothing is dropped, no door is demoted
    (RED_CLASSES: hygiene-narrows-coverage)."""
    calls = []
    off = row(listing_url="https://vendor.test/event/dominic-fike-1")
    result = df.follow([off], fetcher({}, calls=calls),
                       patterns=PATTERNS + (ip.IdentityPattern(
                           pattern_id="vendor", host_family="vendor.test",
                           path_re=r"/event/[^/]+-\d+", grade="fixture_shape",
                           owned=False, note="test"),), as_of=AS_OF)
    assert calls == []
    assert result.skipped_off_origin == 1
    assert result.rows[0] is off               # untouched, still in the catalog
    assert result.rows[0].listing_url == "https://vendor.test/event/dominic-fike-1"


def test_an_address_no_committed_pattern_claims_is_not_opened():
    """A category page, a venue's homepage, the desk's own list — none of them
    is one happening, and this tick has no business opening them."""
    calls = []
    other = row(listing_url="https://desk.test/section/music")
    result = df.follow([other], fetcher({}, calls=calls), patterns=PATTERNS,
                       as_of=AS_OF)
    assert calls == [] and result.skipped_no_identity == 1
    assert result.eligible == 0


def test_a_row_with_no_address_of_its_own_is_left_alone():
    result = df.follow([row(listing_url=None)], fetcher({}), patterns=PATTERNS,
                       as_of=AS_OF)
    assert result.eligible == 0 and result.fetched == 0
    assert result.rows[0].when is None


def test_a_redirect_off_the_origin_is_not_read():
    """A redirect to another host is a different door. Reading fields off it
    would attach a stranger's page to this happening."""
    landed = PageFetch(url="https://desk.test/event/dominic-fike-1", status=200,
                       body=EVENT_PAGE_DATED,
                       final_url="https://vendor.test/checkout/1")
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": landed}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when is None
    assert result.unread == 1
    assert any("different happening" in why for _, why in result.queued)


def test_a_same_origin_redirect_to_another_page_is_not_read_either():
    """Evaluator, PR #235 r2 (openai/absence-only). Same host is NOT enough: a
    deleted or soft-redirected permalink lands on the desk's own index, and
    reproduced before fixing that page supplied 2026-09-30 at "Front Desk" as
    this happening's date and venue. The identity gate that chose the URL has to
    hold after the redirect too, or it only ever guarded the request."""
    index = ('<html><body><article><h1>This week</h1>'
             '<time datetime="2026-09-30T19:00">Wed</time>'
             '<div class="venue">Front Desk</div></article></body></html>')
    landed = PageFetch(url="https://desk.test/event/dominic-fike-1", status=200,
                       body=index, final_url="https://desk.test/whats-on")
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": landed}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when is None
    assert result.rows[0].place_text is None
    assert result.unread == 1


def test_a_tracking_parameter_on_the_redirect_is_not_the_same_page():
    """This test asserted the OPPOSITE until r13, and the premise is what changed.

    r2 dropped the query from an address so a desk appending `?ref=calendar`
    would still read; r11 kept the query but tolerated parameters the desk ADDED,
    on the argument that an added parameter cannot change which happening was
    addressed. Both were the same mistake this ticket keeps making — correct
    about the redirect in front of me, silent one step past it. `/event/show` →
    `/event/show?date=2026-09-19` is a desk CHOOSING one night of a run for us,
    and a list page linking the run's own page rather than a night's is exactly
    how a row ends up with no query on a query-addressed desk (evaluator, PR
    #235 r13, openai/absence-only).

    Telling a tracking parameter from an identifying one needs a registry of
    parameter names — the chrome-word list refused at r1, one domain over. So
    the cost is paid the honest way: QUEUED with its reason, holes kept, nothing
    dropped and nothing guessed. No run in this ticket's evidence ever saw such
    a redirect; the `?ref=` case was always a hypothetical."""
    landed = PageFetch(url="https://desk.test/event/dominic-fike-1", status=200,
                       body=EVENT_PAGE_DATED,
                       final_url="https://desk.test/event/dominic-fike-1/?ref=cal")
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": landed}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when is None
    assert result.unread == 1
    assert any("?ref=cal" in why for _url, why in result.queued), result.queued

    # A trailing slash IS still the same address — `_identity_of` says so on the
    # way in, and this module has to agree or a desk printing both forms
    # publishes the happening twice.
    slashed = PageFetch(url="https://desk.test/event/dominic-fike-1", status=200,
                        body=EVENT_PAGE_DATED,
                        final_url="https://desk.test/event/dominic-fike-1/")
    assert df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": slashed}),
        patterns=PATTERNS, as_of=AS_OF).rows[0].when == "2026-09-05T21:00:00"

    # And r12's half still holds: the ROW's own address is the identity inside
    # `field_read`, so a node naming the canonical address speaks for the row
    # after a redirect this module accepts.
    spoken = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Dominic Fike",
     "url":"https://desk.test/event/dominic-fike-1",
     "startDate":"2026-09-05T21:00:00-05:00",
     "location":{"@type":"Place","name":"The Hall"}}</script></head>
    <body><article><h1>Dominic Fike</h1></article></body></html>"""
    node = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": PageFetch(
            url="https://desk.test/event/dominic-fike-1", status=200,
            body=spoken, final_url="https://desk.test/event/dominic-fike-1/")}),
        patterns=PATTERNS, as_of=AS_OF)
    assert node.rows[0].when == "2026-09-05T21:00:00-05:00", node.reads[0].refusals
    assert node.rows[0].place_text == "The Hall"


# --- whose event is this structured node about? -------------------------------
# Evaluator, PR #235 r2 (openai/attacker-smuggle), BLOCKING and reproduced: any
# schema.org Event on the page was treated as this happening's, so a sidebar's
# node published 2026-12-25 at "The Other Room" onto a row titled something else.

HERE = "https://desk.test/event/dominic-fike-1"
SIDEBAR_EVENT = """<html><head><script type="application/ld+json">
{"@type":"Event","name":"Some Other Show","url":"https://desk.test/event/other-99",
 "startDate":"2026-12-25T20:00:00-06:00",
 "location":{"@type":"Place","name":"The Other Room"}}</script></head>
<body><article><h1>Dominic Fike</h1></article></body></html>"""


def test_a_structured_node_naming_another_address_speaks_for_nobody_here():
    """The address it names is one the COMMITTED table calls a happening — so it
    is another row's statement, not this one's."""
    read = df.field_read(SIDEBAR_EVENT, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None
    assert read.place_text is None
    assert "structured-not-bound" in read.codes


def test_a_node_claiming_this_address_while_naming_another_show_dates_nothing():
    """Evaluator, PR #235 r5, openai/attacker-smuggle — this test previously
    asserted the defect.

    Naming this permalink is the strongest thing markup can say about whose
    page it is on, and until r5 it was accepted alone. But a node claiming to
    be about THIS address while calling itself "Some Other Show", on a page
    headed "Dominic Fike", is a desk publishing two different answers about one
    page — and there is no reading of that which dates this row."""
    page = SIDEBAR_EVENT.replace("https://desk.test/event/other-99", HERE)
    read = df.field_read(page, url=HERE, as_of=AS_OF)
    assert read.when is None, read.when
    assert read.place_text is None


def test_a_node_claiming_this_address_and_naming_this_show_speaks_for_it():
    """The converse, and the common case: the address and the name agree."""
    page = (SIDEBAR_EVENT.replace("https://desk.test/event/other-99", HERE)
            .replace('"name":"Some Other Show"', '"name":"Dominic Fike"'))
    read = df.field_read(page, url=HERE, as_of=AS_OF)
    assert read.when == "2026-12-25T20:00:00-06:00", read.refusals
    assert read.place_text == "The Other Room"


def test_a_bound_node_on_a_page_with_no_heading_still_binds():
    """ABSENCE IS NOT DISAGREEMENT. A page that prints no heading, or a node
    that carries no name, contradicts nothing — the node keeps the bind it
    earned by naming this address. Requiring positive agreement here would hole
    every desk whose event page heads with the venue or a masthead."""
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","url":"https://desk.test/event/dominic-fike-1",
     "startDate":"2026-12-25T20:00:00-06:00",
     "location":{"@type":"Place","name":"The Room"}}</script></head>
    <body><article><p>no heading anywhere</p></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF)
    assert read.when == "2026-12-25T20:00:00-06:00", read.refusals


def test_a_lone_node_naming_no_address_is_the_pages_own_event():
    """A permalink page publishing ONE Event and no address for it is publishing
    it about itself. Requiring a `url` there would hole every desk whose markup
    simply omits one."""
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Dominic Fike","startDate":"2026-09-06T21:00:00-05:00",
     "location":{"@type":"Place","name":"The Hall"}}</script></head>
    <body><article><h1>Dominic Fike</h1></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF)
    assert read.when == "2026-09-06T21:00:00-05:00"
    assert read.place_text == "The Hall"


def test_an_unbound_node_does_not_even_get_the_event_scope_exemption():
    """The first cut of this fix stopped the unbound node from WINNING its tier
    and left it holding the exemption from the plumbing/locality rules — so it
    still dated the row. A statement about another event gets neither."""
    assert df.speaks_for([{"url": "https://desk.test/event/other-99"}], HERE,
                         PATTERNS) == []
    read = df.field_read(SIDEBAR_EVENT, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None and read.when_carrier is None


def test_the_bind_reads_id_as_well_as_url():
    page = f"""<html><head><script type="application/ld+json">
    {{"@type":"Event","@id":"{HERE}","name":"Dominic Fike",
      "startDate":"2026-09-06T21:00:00-05:00"}}</script></head>
    <body><article><h1>Dominic Fike</h1></article></body></html>"""
    assert df.field_read(page, url=HERE, as_of=AS_OF).when == "2026-09-06T21:00:00-05:00"


def test_a_bound_node_beside_a_sidebar_node_still_speaks():
    """The page's own event names this address; the sidebar names its own. Only
    the first speaks here, so the sidebar's December date never competes."""
    page = f"""<html><head>
    <script type="application/ld+json">{{"@type":"Event","url":"{HERE}",
      "startDate":"2026-09-06T21:00:00-05:00",
      "location":{{"@type":"Place","name":"The Hall"}}}}</script>
    <script type="application/ld+json">{{"@type":"Event",
      "url":"https://desk.test/event/other-99",
      "startDate":"2026-12-25T20:00:00-06:00",
      "location":{{"@type":"Place","name":"The Other Room"}}}}</script>
    </head><body><article><h1>Dominic Fike</h1></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF)
    assert read.place_text == "The Hall"


# --- walls: knock once, queue, keep the happening -----------------------------

@pytest.mark.parametrize("status", [401, 402, 403, 407, 429])
def test_a_wall_is_a_hole_queued_never_a_retry_and_never_a_deletion(status):
    """The founder's rule, all five statuses: fail closed, queue it, do not
    retry, do not delete the happening."""
    calls = []
    walled = PageFetch(url="https://desk.test/event/dominic-fike-1", status=status)
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": walled}, calls=calls),
        patterns=PATTERNS, as_of=AS_OF)
    assert calls == ["https://desk.test/event/dominic-fike-1"]   # ONE knock
    assert result.walled == 1
    assert len(result.rows) == 1 and result.rows[0].title == "Dominic Fike"
    assert result.rows[0].when is None
    assert result.queued and "class D" in result.queued[0][1]


def test_a_proxy_wall_with_no_http_status_is_still_counted_as_a_wall():
    """The sandbox's own 403 arrives as a transport error with no status. A wall
    that shows up as 0 in the 403 column is exactly the number that lets a
    walled desk be reported as an empty calendar."""
    blocked = PageFetch(url="https://desk.test/event/dominic-fike-1",
                        error="ProxyError: Tunnel connection failed: 403 Forbidden",
                        walled=True)
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": blocked}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.walled == 1 and result.unread == 1
    assert result.rows[0].when is None


def test_a_404_is_triage_not_an_answer_about_the_happening():
    result = df.follow([row()], fetcher({}), patterns=PATTERNS, as_of=AS_OF)
    assert result.unread == 1
    assert any("triage" in why for _, why in result.queued)
    assert result.rows[0].title == "Dominic Fike"


def test_a_fetcher_that_raises_costs_one_page_not_the_run():
    def boom(url):
        raise RuntimeError("socket died")
    result = df.follow([row(), row("Second", listing_url="https://desk.test/event/second-2")],
                       boom, patterns=PATTERNS, as_of=AS_OF)
    assert result.unread == 2 and len(result.rows) == 2


def test_nothing_is_ever_fetched_twice():
    """No retry anywhere, and rows sharing one address share one fetch."""
    calls = []
    # Both cards NAME the show the page is headed with: since r17 a page whose
    # own heading names none of a row's title is not read for that row, and a
    # fixture about fetch de-duplication should not depend on that rule.
    same = [row(), row("Dominic Fike — second card")]
    result = df.follow(same, fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED}, calls=calls),
        patterns=PATTERNS, as_of=AS_OF)
    assert calls == ["https://desk.test/event/dominic-fike-1"]
    assert result.fetched == 1
    assert all(r.when.startswith("2026-09-05") for r in result.rows)


# --- the budget is a floor ----------------------------------------------------

def test_the_budget_bounds_the_pages_and_the_rest_are_UNASKED():
    """RED_CLASSES pagination-integrity-gap: a cap is a runaway backstop, never
    a measurement. The rows past it are not dateless — nobody asked them."""
    # Each row's title NAMES what its page is headed with: since r17 a page
    # whose heading names none of the row's title is not read for that row, and
    # a fixture about the BUDGET should not be measuring that rule instead.
    rows = [row("Dominic Fike", listing_url=f"https://desk.test/event/show-{i}")
            for i in range(5)]
    pages = {f"https://desk.test/event/show-{i}": EVENT_PAGE_DATED for i in range(5)}
    calls = []
    result = df.follow(rows, fetcher(pages, calls=calls), budget=2,
                       patterns=PATTERNS, as_of=AS_OF)
    assert len(calls) == 2
    assert result.fetched == 2 and result.not_followed == 3
    assert result.dated == 2 and result.still_null_n == 3
    assert result.budget_spent
    assert any("UNASKED" in n for n in result.notes)


def test_a_zero_budget_opens_nothing_and_says_so():
    calls = []
    result = df.follow([row()], fetcher({}, calls=calls), budget=0,
                       patterns=PATTERNS, as_of=AS_OF)
    assert calls == [] and result.not_followed == 1 and result.eligible == 1


@pytest.mark.parametrize("bad", [-1, 1.5, "40", None])
def test_a_budget_that_is_not_a_count_raises(bad):
    with pytest.raises(df.DeskFollowError):
        df.follow([row()], fetcher({}), budget=bad, patterns=PATTERNS)


def test_a_fetcher_returning_something_unclassifiable_raises():
    with pytest.raises(df.DeskFollowError):
        df.follow([row()], lambda url: "<html>", patterns=PATTERNS, as_of=AS_OF)


# --- the module holds no host knowledge --------------------------------------

def test_the_place_label_rule_has_exactly_one_definition():
    """Two definitions of "the page called this a venue" would drift into two
    different answers about the same markup."""
    from worker.locale import desk_read
    assert df.says_place is desk_read.says_place


def test_a_row_never_claims_a_field_came_from_a_page_that_did_not_state_it():
    """Evaluator NIT, PR #235 (openai/attacker-smuggle). A row names ONE detail
    page, so a field merged in from a SECOND reading's page keeps its value and
    makes no provenance claim — understating is the only safe direction, because
    the alternative says a page stated something it never did."""
    from worker.locale.desk_read import fill_holes
    kept = row(when="2026-09-05T21:00:00")
    kept = kept.__class__(**{**kept.__dict__, "detail_url": "https://desk.test/event/a-1",
                             "filled_from_detail": ("when",)})
    incoming = row(place_text="The Hall")
    incoming = incoming.__class__(**{**incoming.__dict__,
                                     "detail_url": "https://desk.test/event/b-2",
                                     "filled_from_detail": ("place_text",)})
    merged = fill_holes(kept, incoming)
    assert merged.place_text == "The Hall"                 # the value is kept
    assert merged.detail_url == "https://desk.test/event/a-1"
    assert "place_text" not in merged.filled_from_detail   # and NOT claimed

    # Same page on both sides: the claim is the union, because it is true.
    same = incoming.__class__(**{**incoming.__dict__,
                                 "detail_url": "https://desk.test/event/a-1"})
    assert set(fill_holes(kept, same).filled_from_detail) == {"when", "place_text"}


# --- the tick as the tool runs it ---------------------------------------------

def _tool():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_tool_desk_ingest", os.path.join(REPO, "tools", "desk_ingest.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _walk(rows):
    from worker.locale.desk_walk import DeskWalk, PageVisit
    one = DeskWalk(door_id="test-desk", door_type="local_desk", via="Test Desk",
                   start_url="https://desk.test/events/today", rows=list(rows))
    one.pages.append(PageVisit(n=1, url=one.start_url, status=200,
                               rows_seen=len(rows), new_rows=len(rows),
                               identity_tier="permalink"))
    one.stopped_because = "no_next_link"
    return one


def test_the_tool_puts_the_filled_rows_back_on_the_walk():
    """Everything downstream — the union, the write plan, the counts — reads the
    walk's rows. A tick that filled a hole and left it in a side result would be
    a table nobody's catalog agrees with."""
    tool = _tool()
    one = _walk([row()])
    tool.follow_walks([one], {"test-desk": fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED})},
        budget=40, as_of=AS_OF, patterns=PATTERNS)
    assert one.rows[0].when == "2026-09-05T21:00:00"
    assert one.rows[0].place_text == "Moody Amphitheater"


def test_the_founders_five_columns_are_the_five_columns():
    tool = _tool()
    one = _walk([row(), row("Second", listing_url="https://desk.test/event/second-2")])
    follows = tool.follow_walks([one], {"test-desk": fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED,
        "https://desk.test/event/second-2": EVENT_PAGE_CLOCK_ONLY})},
        budget=40, as_of=AS_OF, patterns=PATTERNS)
    table = tool.follow_table([one], follows, budget=40, patterns=PATTERNS)
    header = table.splitlines()[0]
    assert header == "| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |"
    assert "| `test-desk` | 2 | 1 | 1 | 0 | 0 |" in table
    assert "mash_n` totals **0**" in table


def test_the_table_separates_unasked_rows_from_dateless_ones():
    """The number a reader would misread first. A budget-capped run must not
    print "still_null_n" as a finding about the desk."""
    tool = _tool()
    # Titles that NAME what these pages are headed with: since r17 a page whose
    # heading names none of a row's title is not read for that row, and a
    # fixture about the BUDGET's reason table must not be measuring that.
    rows = [row("Dominic Fike", listing_url=f"https://desk.test/event/show-{i}")
            for i in range(4)]
    pages = {f"https://desk.test/event/show-{i}": EVENT_PAGE_CLOCK_ONLY
             for i in range(4)}
    one = _walk(rows)
    follows = tool.follow_walks([one], {"test-desk": fetcher(pages)}, budget=1,
                                as_of=AS_OF, patterns=PATTERNS)
    why = tool.null_reasons(one, follows["test-desk"], patterns=PATTERNS)
    assert why == {"page stated no date": 1, "page could not be read": 0,
                   "not asked (budget)": 3, "no followable address": 0}
    table = tool.follow_table([one], follows, budget=1, patterns=PATTERNS)
    assert "UNASKED" in table and "is a FLOOR" in table


def test_a_walled_page_is_counted_apart_from_a_page_that_said_nothing():
    tool = _tool()
    walled = PageFetch(url="https://desk.test/event/show-0", status=403)
    # Same scaffolding note as above: the readable page is headed "Dominic
    # Fike", so the row that opens it has to be named for it or this fixture
    # measures the r17 denial instead of the wall.
    one = _walk([row("Show 0", listing_url="https://desk.test/event/show-0"),
                 row("Dominic Fike", listing_url="https://desk.test/event/show-1")])
    follows = tool.follow_walks([one], {"test-desk": fetcher({
        "https://desk.test/event/show-0": walled,
        "https://desk.test/event/show-1": EVENT_PAGE_CLOCK_ONLY})},
        budget=40, as_of=AS_OF, patterns=PATTERNS)
    why = tool.null_reasons(one, follows["test-desk"], patterns=PATTERNS)
    assert why["page could not be read"] == 1
    assert why["page stated no date"] == 1
    assert "| `test-desk` | 2 | 0 | 2 | 1 | 0 |" in tool.follow_table(
        [one], follows, budget=40, patterns=PATTERNS)


def test_the_report_says_what_the_opened_pages_actually_said():
    """`still_null_n = 1568` is a number; "40 pages printed a clock and no date"
    is a repair. The codes are what make the second one possible."""
    tool = _tool()
    one = _walk([row("Show 0", listing_url="https://desk.test/event/show-0"),
                 row("Show 1", listing_url="https://desk.test/event/show-1")])
    follows = tool.follow_walks([one], {"test-desk": fetcher({
        "https://desk.test/event/show-0": EVENT_PAGE_CLOCK_ONLY,
        "https://desk.test/event/show-1": FOOTER_STAMP})},
        budget=40, as_of=AS_OF, patterns=PATTERNS)
    table = tool.what_the_pages_said(follows)
    # Two pages, two DIFFERENT reasons — which is the whole point: one printed a
    # clock and no date, the other stated its only date in the page footer.
    assert "`clock-without-date` | 1 | 50%" in table
    assert "`date-in-plumbing` | 1 | 50%" in table
    assert "2 event page(s) opened" in table
    # And the pages' own words, because a code counted at 100% and never quoted
    # is still not something a person can act on.
    assert "in the pages' own words" in table
    assert "a time with no day is not a moment" in table


def test_the_report_says_nothing_rather_than_zero_when_no_page_was_opened():
    tool = _tool()
    assert "nothing to count" in tool.what_the_pages_said({})


def test_the_plan_table_is_bounded_and_says_so():
    """A live walk plans over a thousand rows, and a thousand-row markdown table
    buries the counters the ticket is judged on. The cap is on PRINTING: the
    total is stated beside the sample so it can never read as the whole plan."""
    tool = _tool()

    class _W:
        def __init__(self, i):
            self.ingest_key, self.title = f"k{i}", f"Show {i}"
            self.vias, self.start_time, self.clock_hole = ["Desk"], None, "no date"
            self.extracted = {"venue_name": "The Hall"}

    table = tool.plan_table([_W(i) for i in range(30)], limit=25)
    assert "| 25 |" in table and "| 26 |" not in table
    assert "first 25 of 30 planned rows" in table
    assert "counted in every number on this page" in table


def test_the_sample_rows_say_which_page_stated_the_date():
    tool = _tool()
    one = _walk([row()])
    tool.follow_walks([one], {"test-desk": fetcher({
        "https://desk.test/event/dominic-fike-1": EVENT_PAGE_DATED})},
        budget=40, as_of=AS_OF, patterns=PATTERNS)
    table = tool.sample_rows([one])
    assert "https://desk.test/event/dominic-fike-1" in table
    assert "2026-09-05T21:00:00" in table
    assert "Moody Amphitheater" in table
    assert "when, place_text" in table


def test_the_fixture_dry_run_still_runs_and_no_follow_opens_nothing(capsys):
    """The committed-fixture path, both ways. Hermetic: no socket, no DSN."""
    tool = _tool()
    assert tool.main(["--dry-run", "--no-follow"]) == 0
    printed = capsys.readouterr().out
    assert "no event page was opened" in printed
    assert "Nothing was written" in printed
    assert tool.main(["--dry-run"]) == 0
    printed = capsys.readouterr().out
    assert "| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |" in printed


def test_a_negative_budget_is_refused_before_anything_is_walked(capsys):
    tool = _tool()
    assert tool.main(["--dry-run", "--follow-budget", "-1"]) == 2
    assert "must be zero or more" in capsys.readouterr().err


def test_a_vanity_url_for_the_same_happening_is_not_another_event():
    """The live run's own finding. Requiring the node to name the followed
    permalink refused 29 of 40 real pages, and the addresses they named were the
    desk's own vanity and submitter links for the SAME happening:

        /backtotheranch     on  /event/back-to-the-ranch-...-14329073
        /texarts_26_BB_ac   on  /event/boeing-boeing-14285657
        /events/269428      on  /event/prodigal-sun-14267156

    None of those is an address the identity table calls a happening, which is
    exactly what separates them from a sidebar's link to another PERMALINK.

    The table alone is not enough, though — see the test below. The node has to
    say it is about the thing this page is about, and here it does: it and the
    page's own heading both name Dominic Fike.
    """
    def page(url_value, printed="<p>Friday, December 25, 2026</p>"):
        return f"""<html><head><script type="application/ld+json">
        {{"@type":"Event","name":"Dominic Fike","url":"{url_value}",
          "startDate":"2026-12-25T20:00:00-06:00",
          "location":{{"@type":"Place","name":"The Room"}}}}</script></head>
        <body><article><h1>Dominic Fike</h1>
        {printed}</article></body></html>"""

    for vanity in ("https://desk.test/backtotheranch",
                   "https://desk.test/events/269428"):
        read = df.field_read(page(vanity), url=HERE, as_of=AS_OF, patterns=PATTERNS)
        assert read.when == "2026-12-25T20:00:00-06:00", vanity
        assert read.place_text == "The Room", vanity

    # And the sidebar case the evaluator found stays closed. Its page prints no
    # date of its own, so nothing here can date the row from any direction.
    read = df.field_read(page("https://desk.test/event/other-99", printed=""),
                         url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None
    assert "structured-not-bound" in read.codes
    # The refusal names the TABLE, not corroboration — this node named another
    # happening's permalink, and saying otherwise would send the next reader at
    # the wrong rule.
    assert not any("does not corroborate" in r for r in read.refusals), read.refusals

    # A sidebar node cannot borrow the page's own printed day either: the page
    # states Dec 25 in its content, and the node is still refused — what the
    # row gets is the PAGE's date, never the sidebar's venue.
    read = df.field_read(page("https://desk.test/event/other-99"), url=HERE,
                         as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text is None, read.place_text


def test_an_unrecognised_address_is_not_proof_the_node_is_ours():
    """Evaluator, PR #235 r4, openai/attacker-smuggle — reproduced before fixing.

    ABSENCE FROM THE IDENTITY TABLE IS NOT PROOF. A stale or promotional Event
    at an address the table cannot classify — a vanity URL, a ticket link, a
    partner site — passes the "not another happening" test while being about
    something else entirely. On a page whose own listing carries no structured
    markup, it is the lone node, and it published its day and its venue here.

    The node has to say it is about the thing this page is about. This one
    calls itself "Something Else" on a page headed "Dominic Fike", so it is an
    unidentified witness and the row keeps its hole."""
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Something Else","url":"https://desk.test/promo-xyz",
      "startDate":"2026-12-25T20:00:00-06:00",
      "location":{"@type":"Place","name":"The Other Room"}}</script></head>
    <body><article><h1>Dominic Fike</h1>
    <p>Tickets at the door.</p></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None
    assert read.place_text is None
    assert "structured-not-bound" in read.codes
    # The refusal says WHY, so a live run can tell this apart from a sidebar
    # naming another permalink.
    assert any("about something else" in r for r in read.refusals), read.refusals


def test_a_lone_node_naming_no_address_is_no_more_ours_for_it():
    """Evaluator, PR #235 r4 second review, BOTH openai seats — reproduced.

    Round 2 accepted "the page's lone node naming no address at all" as a
    permalink page publishing an Event about itself. It is not: a promotional
    node that simply omits `url` is exactly as unidentified as one carrying a
    vanity link, and it published its own day and venue here.

    What the node names does not decide this. What it CALLS ITSELF does."""
    page = """<html><head><title>Dominic Fike</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Some Other Show",
      "startDate":"2026-12-25T20:00:00-06:00",
      "location":{"@type":"Place","name":"The Other Room"}}</script></head>
    <body><article><h1>Dominic Fike</h1>
    <p>Tickets at the door.</p></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when
    assert read.place_text is None
    assert "structured-not-bound" in read.codes


def test_a_lone_unaddressed_node_that_names_this_page_still_speaks():
    """The converse — the shape round 2 was right about. A permalink page
    publishing one Event about itself, with no `url` on the node, still dates
    the row when it names what the page names."""
    page = """<html><head><title>Dominic Fike</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Dominic Fike",
      "startDate":"2026-09-06T21:00:00-05:00",
      "location":{"@type":"Place","name":"The Hall"}}</script></head>
    <body><article><h1>Dominic Fike</h1></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-06T21:00:00-05:00", read.refusals
    assert read.place_text == "The Hall"


def test_a_single_letter_names_nothing():
    """The name comparison allows containment either way, so it needs a floor:
    "A" is inside "A Show", inside "A Completely Different Thing", and inside
    every heading with an article in it. One token of two or more characters,
    or two tokens, is that floor."""
    page = """<html><head><title>A Completely Different Thing</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"A","startDate":"2026-09-06T21:00:00-05:00",
      "location":{"@type":"Place","name":"The Other Room"}}</script></head>
    <body><article><h1>A Completely Different Thing</h1></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when


def test_a_run_of_performances_disagreeing_about_the_day_still_binds():
    """The live shape that the first version of the identity check destroyed.

    `/event/prodigal-sun-14267156`: the node states Sep 4, the page displays
    Sep 6, and both are about Prodigal Sun — a run of performances has more than
    one date and the two statements are about different ones. Asking whether the
    page's content CORROBORATES the node's day answered the wrong question
    (agreement, not identity) and took `structured-not-bound` from 2 pages to 17
    of 40, with 14 falling through to a date they could only find in their own
    plumbing.

    The node names what the page names, so it SPEAKS for this row — its venue
    still comes through. What it does not do is settle the DAY: r8 separated
    those two questions, because identity and certainty are not the same
    (evaluator, PR #235 r8). A desk contradicting itself about which night has
    not stated one, and modelling runs is the next ticket's work."""
    page = """<html><head><title>Prodigal Sun</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Prodigal Sun","url":"https://desk.test/events/269428",
      "startDate":"2026-09-04T19:30:00-05:00",
      "location":{"@type":"Place","name":"Saengerrunde Hall"}}</script></head>
    <body><article><h1>Prodigal Sun</h1>
    <p>Next performance Sunday, September 6, 2026</p></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    # It BINDS — the node is this row's, and nothing contradicts its venue.
    assert read.place_text == "Saengerrunde Hall"
    assert "structured-not-bound" not in read.codes
    # And the day is not settled, because the page says otherwise.
    assert read.when is None, read.when
    assert "card-contradicts-its-own-markup" in read.codes


def test_a_card_listing_more_days_than_its_markup_is_not_a_contradiction():
    """Found by the first LIVE run of the r8 check, in two steps.

    That run refused 15 of 40 opened pages, and the desk's own words showed the
    rule was broader than its message: `/event/boeing-boeing-14285657` had a
    card stating three performance days and markup naming one. A card that
    lists MORE days than the markup is the desk agreeing with itself at
    different resolutions — elaboration, not contradiction — and calling it one
    made the code's own sentence untrue (RED_CLASSES: diagnostics-as-data).

    THEN the narrowed rule still refused, and the reason is the r3 class again:
    R-030 reports each date under the STRONGEST carrier that stated it, so the
    18th — printed on the card AND named in the markup — came back as `jsonld`
    and vanished from a "what the card printed" filter over the document-wide
    scan. The card's days are now read FROM THE CARD."""
    def page(card_line):
        return f"""<html><head><title>Boeing Boeing</title>
        <script type="application/ld+json">
        {{"@type":"Event","name":"Boeing Boeing",
          "url":"https://desk.test/tickets/9",
          "startDate":"2026-09-18T19:30:00-05:00",
          "location":{{"@type":"Place","name":"TexARTS"}}}}</script></head>
        <body><article><h1>Boeing Boeing</h1><p>{card_line}</p></article>
        </body></html>"""

    listed = page("September 18, 2026; September 19, 2026; September 20, 2026")
    read = df.field_read(listed, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-18T19:30:00-05:00", read.refusals
    assert "card-contradicts-its-own-markup" not in read.codes

    # And the real contradiction — the card's days do NOT include the markup's.
    omitted = page("September 19, 2026; September 20, 2026")
    read = df.field_read(omitted, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when
    assert "card-contradicts-its-own-markup" in read.codes

    # A card that states nothing contradicts nothing.
    silent = page("Tickets at the door.")
    read = df.field_read(silent, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-18T19:30:00-05:00", read.refusals


def test_a_card_clock_contradicting_the_markup_keeps_the_day_and_holes_the_time():
    """Evaluator, PR #235 r10, openai/attacker-smuggle — reproduced.

    r8 compared the two tiers' DAYS and stopped there, so a node saying 19:30
    on a card that visibly prints 8:00PM published a precise time the page's own
    statement contradicts:

        PRE-FIX   when=2026-09-18T19:30:00-05:00   codes=()

    The day is agreed, so the day stands and only the time is refused —
    refusing the clock is not refusing the date."""
    def page(card_line):
        return f"""<html><head><title>Boeing Boeing</title>
        <script type="application/ld+json">
        {{"@type":"Event","name":"Boeing Boeing",
          "url":"https://desk.test/tickets/9",
          "startDate":"2026-09-18T19:30:00-05:00",
          "location":{{"@type":"Place","name":"TexARTS"}}}}</script></head>
        <body><article><h1>Boeing Boeing</h1><p>{card_line}</p></article>
        </body></html>"""

    clash = df.field_read(page("September 18, 2026 &mdash; 8:00PM"),
                          url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert clash.when == "2026-09-18", clash.when
    assert clash.when_precision == "date"
    assert "card-contradicts-its-own-markup" in clash.codes
    assert clash.place_text == "TexARTS"      # only the CLOCK is in dispute

    agree = df.field_read(page("September 18, 2026 &mdash; 7:30PM"),
                          url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert agree.when == "2026-09-18T19:30:00-05:00", agree.refusals

    silent = df.field_read(page("September 18, 2026"),
                           url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert silent.when == "2026-09-18T19:30:00-05:00", silent.refusals


def test_a_desk_in_a_non_latin_script_can_state_its_fields():
    """Evaluator, PR #235 r10, openai/attacker-smuggle — the half they reported
    was a smuggling risk; the half nobody reported was a LOCALE REFUSED IN CODE.

    `_same_name` stripped every character outside `[0-9a-z]`, so "Кино Night"
    collapsed to "night" and matched an unrelated node called "Night". But a
    page headed "Кино" alone collapsed to the EMPTY STRING — `_same_name` could
    never be true for it, so every lone node on that page was refused and every
    bound node read as contradicting the heading. A whole desk in Cyrillic,
    Greek or any non-Latin script could not fill a single field, and "Café du
    Nord" came back as "caf du nord".

    Invisible because every test and every desk in this repo is English.
    Coverage Law forbids refusing a locale, and this refused all of them.

    The fix is an IMPORT, not a new tokenizer: `desk_union.name_key` is this
    repo's reviewed answer to the same question, and the red class it was
    hardened against (`destructive-normalization`) names "Кино Night -> night"
    and "Café -> caf" as its own worked examples. My first pass at this test
    asserted `not _same_name("Café du Nord", "Cafe du Nord")` — the defect,
    written down as the expectation, in the test meant to close it."""
    assert df._name_tokens("Кино Night") == ["кино", "night"]
    assert df._name_tokens("Ελληνικά") == ["ελληνικά"]
    # Two desks spelling one venue differently are one venue (the exact pair
    # the red class was founded on), and a leading article is not a name.
    assert df._same_name("Café du Nord", "Cafe du Nord")
    assert df._same_name("The Continental Club", "Continental Club")
    assert not df._same_name("Fixture Room", "Fixture Annex")
    # Scriptio continua: no spaces means one token, so the EXACT path is the
    # one that binds. Recorded in R-113 rather than loosened — substring
    # containment would match "Night" inside "Nightingale" for every desk.
    assert df._same_name("東京ホール", "東京ホール")
    assert not df._same_name("東京", "東京ホール")

    page = """<html><head><title>Кино</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Кино","startDate":"2026-09-18T19:30:00-05:00",
      "location":{"@type":"Place","name":"Дом"}}</script></head>
    <body><article><h1>Кино</h1></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-18T19:30:00-05:00", read.refusals
    assert read.place_text == "Дом"


def test_a_second_clock_on_the_card_does_not_walk_a_node_past_the_check():
    """Evaluator, PR #235 r11, openai/attacker-smuggle — r10's guard compared the
    node against `page_clock`, which is None the moment a card prints TWO clocks,
    and the multi-clock diagnostic is suppressed once a carrier states the whole
    instant. So "8:00PM; doors 7:00PM" beside a 19:30 node published 19:30 with
    codes=(), walking straight through the guard added one round earlier.

    Membership is the rule that covers both counts: the card's clocks are the
    times this desk says are involved, and the markup's job is to say WHICH one
    starts the show. One of them being the node's is agreement at two
    resolutions (the r8 lesson, applied to clocks); none of them being the
    node's is the desk contradicting itself."""
    def page(clocks):
        return f"""<html><body><article>
        <h1>The Show</h1>
        <script type="application/ld+json">
        {{"@type":"Event","name":"The Show",
          "startDate":"2026-09-18T19:30:00-05:00",
          "location":{{"@type":"Place","name":"The Hall"}}}}</script>
        <p>Friday, September 18, 2026 — {clocks}</p>
        </article></body></html>"""

    def read(clocks):
        return df.field_read(page(clocks), url=HERE, as_of=AS_OF,
                             patterns=PATTERNS)

    # The reported shape: two clocks, the node's is NEITHER of them.
    smuggled = read("8:00PM; doors 7:00PM")
    assert smuggled.when == "2026-09-18", smuggled.refusals
    assert "card-contradicts-its-own-markup" in smuggled.codes
    # And now the row HAS a clock hole, so the multi-clock reason records too —
    # the r10 suppression and this rule composing, rather than fighting.
    assert "clocks-ambiguous" in smuggled.codes

    # Two clocks, the node's IS one of them: the markup settled which. This is
    # coverage the old rule lost to `clocks-ambiguous` for no reason.
    settled = read("7:30PM; doors 7:00PM")
    assert settled.when == "2026-09-18T19:30:00-05:00", settled.refusals
    assert settled.codes == ()

    # The r10 single-clock arms, unchanged by the generalisation.
    assert read("8:00PM").when == "2026-09-18"
    assert read("7:30PM").when == "2026-09-18T19:30:00-05:00"
    # A card printing no clock at all contradicts nothing.
    assert read("check listings").when == "2026-09-18T19:30:00-05:00"


def test_a_query_naming_another_night_is_another_page():
    """Evaluator, PR #235 r11, openai/absence-only — `_address` dropped the query
    while `desk_read._identity_of` KEEPS it, and says why in its own docstring:
    "two desks do use `?date=` to address two instances of one series, and
    collapsing those would delete a night". Two modules, one question, opposite
    answers — `one-rule-expressed-twice`, fifth instance in this ticket.

    For such a desk every night of a run shared one address here, so both things
    this comparison guards fell open: a redirect from one night to another
    passed `same_identity`, and a node naming a different night read as speaking
    for this one. Runs are not hypothetical on this desk — they are the largest
    single cause of the refusals r8 exists for.

    The tolerance that made the query droppable in the first place (r2's `?ref=`)
    is kept, and it is now where it belongs: asymmetric, in `same_identity`. An
    ADDED parameter cannot change which happening the desk was addressing; a
    CHANGED or DROPPED one can."""
    # The comparison itself, both directions.
    assert not df.same_identity("https://d.ex/event?date=2026-09-19",
                                "https://d.ex/event?date=2026-09-18")
    assert not df.same_identity("https://d.ex/event",
                                "https://d.ex/event?date=2026-09-18")
    # Tightened at r13: an ADDED parameter is not tolerated either, because
    # `/event/show` -> `/event/show?date=…` is a desk choosing one night of a
    # run for us. See `test_a_tracking_parameter_on_the_redirect_is_not_the_
    # same_page` for the cost and why it is paid this way.
    assert not df.same_identity("https://d.ex/event?date=2026-09-18&ref=cal",
                                "https://d.ex/event?date=2026-09-18")
    assert not df.same_identity("https://d.ex/event?ref=cal",
                                "https://d.ex/event")
    assert df.same_identity("https://d.ex/event/", "https://d.ex/event")

    # A redirect from one night of a run to another is not the page we asked
    # for: the row keeps its holes and the page is queued, not read.
    night = "https://desk.test/event/dominic-fike-1?date=2026-09-18"
    other = ('<html><body><article><h1>Dominic Fike</h1>'
             '<time datetime="2026-09-19T20:00">Sat</time>'
             '<div class="venue">Second Night Hall</div></article></body></html>')
    walked = df.follow(
        [row(listing_url=night)],
        fetcher({night: PageFetch(
            url=night, status=200, body=other,
            final_url="https://desk.test/event/dominic-fike-1?date=2026-09-19")}),
        patterns=PATTERNS, as_of=AS_OF)
    assert walked.rows[0].when is None
    assert walked.rows[0].place_text is None
    assert walked.unread == 1

    # And a structured node naming another night does not speak for this one.
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Dominic Fike",
     "url":"https://desk.test/event/dominic-fike-1?date=2026-09-19",
     "startDate":"2026-09-19T20:00:00-05:00",
     "location":{"@type":"Place","name":"Second Night Hall"}}</script></head>
    <body><article><h1>Dominic Fike</h1></article></body></html>"""
    read = df.field_read(page, url=night, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.refusals
    assert read.place_text is None
    # The refusal has to SHOW which night, or a correct refusal reads like a bug.
    assert any("date=2026-09-19" in r for r in read.refusals), read.refusals


def test_an_unbound_node_sharing_the_cards_day_cannot_lend_it_a_clock():
    """Evaluator, PR #235 r12, BOTH openai seats, and the absence-only seat asked
    for this test by name: "unbound JSON-LD node shares the visible card day but
    names another happening".

    `owned_by_this_happening` had a third arm — a hit whose DAY appears among the
    days the card states is ours. A day is not a fingerprint. R-030 reports each
    date under the STRONGEST carrier that stated it, so when a card prints a bare
    "September 18, 2026" and an unrelated sidebar node names 2026-09-18T23:00,
    the document scan returns ONE hit: kind `jsonld`, carrying the SIDEBAR'S
    CLOCK. The day-match arm found that day in the card and called the hit ours:

        PRE-FIX   when=2026-09-18T23:00:00  codes=('structured-not-bound', …)

    — the other show's time published as this row's, beside a refusal saying
    none of the nodes dates this row. The behaviour and its own diagnostic
    disagreeing about one page is `diagnostics-as-data` as well as a smuggle.

    The card's own day must SURVIVE the node being refused, which is why the fix
    is not "drop the hit" alone: `card_dates()` reads the card directly, so the
    row keeps the bare day the page actually printed."""
    smuggle = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Some Other Show",
     "url":"https://desk.test/event/some-other-show-99",
     "startDate":"2026-09-18T23:00:00",
     "location":{"@type":"Place","name":"The Other Room"}}</script></head>
    <body><article><h1>Dominic Fike</h1>
    <p>Friday, September 18, 2026</p></article></body></html>"""
    read = df.field_read(smuggle, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-18", read.when
    assert read.when_precision == "date"          # the clock did NOT come with it
    assert read.when_carrier == "visible-date"    # and it is the CARD's statement
    assert "structured-not-bound" in read.codes
    assert read.place_text is None                # nor the other room

    # The converse, and it is the reason the day-match arm existed: a page whose
    # own card prints its date beside a calendar widget the document scan
    # attributes elsewhere still keeps its own day.
    plain = ("""<html><body><article><h1>A Show</h1>"""
             """<p>Sat Sep 5 &bull; 9:00PM</p></article></body></html>""")
    assert df.field_read(plain, url="u", as_of=AS_OF).when == "2026-09-05T21:00:00"


def test_a_page_with_no_heading_and_no_sections_states_nothing():
    """Evaluator, PR #235 r12, openai/attacker-smuggle — r9 closed the
    heading-less page by returning `()` ("page level only, every section
    excluded"), which is restrictive on a page built from sectioning elements
    and the OPPOSITE on a page built from `<div>`s: `<div>` is a block boundary
    and not a sectioning tag, so such a page has no top-level sections, every
    statement sits at page level, and `()` admitted all of them.

        PRE-FIX   when=2026-12-25T20:00:00  place='The Other Room'  codes=()

    Whether the boundary failed closed or open depended on the desk's markup
    STYLE, which is the worst way for a trust rule to vary. `()` now means "the
    page level IS the subject" (a heading exists, in no section — r6, tested)
    and `None` means "no subject could be identified", which admits nothing.

    THE COST IS STATED AND IT IS BOUNDED: the VISIBLE-TEXT path is refused on
    such a page, and the STRUCTURED path is untouched — a title-only div-soup
    page that publishes its own schema.org node still fills both fields, which
    the second half of this test pins."""
    promo = """<html><head><title>Dominic Fike</title></head><body>
    <div class="promo"><p>Christmas Special — December 25, 2026 8:00PM</p>
      <div class="venue">The Other Room</div></div>
    <div class="main"><p>Dominic Fike</p></div></body></html>"""
    read = df.field_read(promo, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when
    assert read.place_text is None, read.place_text

    # Bounded: the same page, with a node that speaks for this row, still reads.
    spoken = """<html><head><title>Dominic Fike</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Dominic Fike","url":"%s",
     "startDate":"2026-09-05T21:00:00-05:00",
     "location":{"@type":"Place","name":"The Hall"}}</script></head>
    <body><div class="promo"><p>Christmas Special — December 25, 2026 8:00PM</p>
      <div class="venue">The Other Room</div></div>
    <div>Dominic Fike</div></body></html>""" % HERE
    ok = df.field_read(spoken, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert ok.when == "2026-09-05T21:00:00-05:00", ok.refusals
    assert ok.place_text == "The Hall"

    # And r6's case is NOT swept up in it: a heading outside any section still
    # makes the page level the subject, so its own statements come through.
    sectionless = ("""<html><body><h1>A Show</h1>"""
                   """<p>Sat Sep 5 &bull; 9:00PM</p></body></html>""")
    assert df.field_read(sectionless, url="u", as_of=AS_OF).when \
        == "2026-09-05T21:00:00"


def test_a_same_day_clock_outside_the_card_never_becomes_this_rows_time():
    """Evaluator, PR #235 r15, openai/absence-only — asked for as a regression by
    the seat, and written because THE INVARIANT IS REAL EVEN THOUGH THE DEFECT
    IS NOT.

    The finding describes accepting a carrier "by matching only the date to the
    card". That is the day-match arm of `owned_by_this_happening`, and it was
    REMOVED at r12 for this exact class — a day is not a fingerprint. Four
    shapes of the attack were run against the reviewed head and all four already
    behaved: the card's day at `date` precision, `no-clock`, no outside clock
    adopted. The reproduction is in the evidence doc §13q.

    What was missing is not the guard but this test. "It happens to work" and
    "it is pinned" are different states, and the seat is right that only one of
    them survives the next refactor — the r5 lesson from the other direction,
    where a test that WAS present had been asserting the defect for four rounds.

    Every shape below states the same day as the card, so nothing here is caught
    by cardinality: the day agrees, and only the CLOCK is somebody else's."""
    card = '<article><h1>Dominic Fike</h1><p>September 18, 2026</p></article>'
    for label, outside in (
            ("sibling card",
             '<article><h2>Related</h2>'
             '<time datetime="2026-09-18T23:00">Late</time></article>'),
            ("aside", '<aside><time datetime="2026-09-18T23:00">Late</time></aside>'),
            ("body level", '<time datetime="2026-09-18T23:00">Late</time>'),
            ("visible prose in a sibling card",
             '<article><h2>Related</h2>'
             '<p>September 18, 2026 &mdash; 11:00PM</p></article>'),
            ("page footer", '<footer><p>September 18, 2026 at 11:00PM</p></footer>'),
    ):
        read = df.field_read(f"<html><body>{card}{outside}</body></html>",
                             url=HERE, as_of=AS_OF, patterns=PATTERNS)
        assert read.when == "2026-09-18", (label, read.when)
        assert read.when_precision == "date", label
        assert "no-clock" in read.codes, (label, read.codes)

    # A `<time>` carrier INSIDE the card is this happening's, clock and all —
    # the converse, so the rule above cannot be satisfied by reading nothing.
    inside = ('<html><body><article><h1>Dominic Fike</h1>'
              '<time datetime="2026-09-18T23:00">Late</time></article></body></html>')
    read = df.field_read(inside, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-18T23:00:00", read.refusals


def test_a_word_clock_is_a_hole_in_the_contradiction_check_and_it_is_pinned():
    """R-115, opened at r20 rather than closed, and PINNED HERE so the residual
    is visible in the suite and not only in a record.

    Evaluator PR #235 r20 (openai/absence-only): a card whose only time
    expression is a WORD — "Show at noon" — cannot contradict a structured
    clock, so a node stating 19:30 publishes beside a page visibly saying noon.

    Not closed because the reason is checked, not asserted: the ARMED
    `same_page_dates` cannot read a word clock either (this test proves it), so
    detecting one here would need a second, English-only time vocabulary beside
    the armed one — `one-rule-expressed-twice` plus the locale-refused-in-code
    defect r10 removed — and comparing would need a second clock PARSER, refused
    at r14 and r15. The founder's Must-do 1 names that file imported-never-edited.

    THE BOUND IS MEASURED HERE, NOT REASONED, which is the lesson R-112, R-113
    and R-114 each cost a round to learn: the arms below run the shape past
    every live guard and show exactly which one catches it."""
    # The armed parser's own limit — the fact the record's trigger rests on.
    from worker.same_page_dates import resolve_same_page_datetime
    iso, refusal, _ev = resolve_same_page_datetime(
        "noon", block_text="2026-09-18 noon", as_of=AS_OF)
    assert iso is None and (refusal or {}).get("reason") == "unparseable"

    node = ('<script type="application/ld+json">{"@type":"Event",'
            '"name":"Dominic Fike","url":"%s",'
            '"startDate":"2026-09-18T19:30:00-05:00"}</script>' % HERE)

    def read(card):
        return df.field_read(
            f"<html><head>{node}</head><body><article><h1>Dominic Fike</h1>"
            f"{card}</article></body></html>",
            url=HERE, as_of=AS_OF, patterns=PATTERNS)

    # THE RESIDUAL, stated as it actually behaves today.
    assert read("<p>September 18, 2026 — Show at noon</p>").when \
        == "2026-09-18T19:30:00-05:00"
    assert read("<p>Show at noon</p>").when == "2026-09-18T19:30:00-05:00"

    # AND THE GUARD THAT DOES CATCH IT: any numeric clock printed beside the
    # word brings the membership rule (r12/r14) back into play.
    beside = read("<p>September 18, 2026 — noon, 8:00PM</p>")
    assert beside.when == "2026-09-18", beside.when
    assert "card-contradicts-its-own-markup" in beside.codes


def test_a_promo_written_as_a_plain_div_is_still_another_card():
    """Evaluator, PR #235 r20, openai/attacker-smuggle — r18's sub-card rule
    excluded nested SECTIONING elements, and `<div>` is a block boundary and not
    a sectioning tag. So a promotional block written as a nested `<div>` shared
    the article's section id, counted as "the card's own level", and its date
    and venue were read as this happening's:

        PRE-FIX   when=2026-12-25T20:00:00  place='The Other Room'  codes=()

    The same fact that made r12's page-level default fail open, in the one place
    r18 did not carry it.

    The rule is now element-agnostic, which is what HTML's implied sections
    already are: A HEADING STARTS A REGION THAT RUNS UNTIL THE NEXT HEADING. A
    region headed with what the page is about is the page's; one headed "Also on
    sale" is another card's, whatever element it happens to sit in."""
    def read(inner):
        return df.field_read(
            f"<html><body><article><h1>Dominic Fike</h1>{inner}</article>"
            f"</body></html>", url=HERE, as_of=AS_OF, patterns=PATTERNS)

    promo = ('<h2>Also on sale</h2><p>December 25, 2026 8:00PM</p>'
             '<div class="venue">The Other Room</div>')
    # As a plain div — the finding.
    div = read(f'<div class="promo">{promo}</div>')
    assert div.when is None, div.when
    assert div.place_text is None, div.place_text
    # As a section — r18's case, still closed.
    section = read(f'<section class="promo">{promo}</section>')
    assert section.when is None and section.place_text is None
    # And with NO wrapper at all: an implied region needs no element.
    bare = read(promo)
    assert bare.when is None and bare.place_text is None

    # The card's own statements, in every arrangement.
    own = ('<p>Friday, September 18, 2026 8:00PM</p>'
           '<div class="venue">The Hall</div>')
    assert read(own).when == "2026-09-18T20:00:00"
    assert read(own).place_text == "The Hall"
    named = read(f'<div><h2>Dominic Fike — tickets</h2>{own}</div>')
    assert named.when == "2026-09-18T20:00:00", named.refusals
    assert named.place_text == "The Hall"


def test_a_node_naming_a_fragment_of_the_heading_does_not_claim_the_page():
    """Evaluator, PR #235 r19, openai/attacker-smuggle — and it is r15's lesson
    arriving in the place I applied it once and did not sweep for.

    `_same_name`'s loose containment served BOTH the positive bind and the
    denial, and their dangerous answers point opposite ways: a positive bind
    fails badly on a false YES (a foreign node publishes onto this row), a
    denial fails badly on a false NO (a legitimate page is refused). A page
    headed "Dominic Fike at The Other Room" carrying a lone JSON-LD Event named
    "The Other Room" passed the positive check — the node names the VENUE inside
    the heading, not the happening:

        PRE-FIX   when=2026-12-25T20:00:00-06:00  place='The Other Room'  codes=()

    A claim must now OPEN the name it claims to be, or be it exactly. That is
    r13's single-token rule, which was always the general rule and had been
    applied to one arity."""
    def page(node_name):
        return """<html><head><script type="application/ld+json">
        {"@type":"Event","name":"%s","startDate":"2026-12-25T20:00:00-06:00",
         "location":{"@type":"Place","name":"The Other Room"}}</script></head>
        <body><article><h1>Dominic Fike at The Other Room</h1></article>
        </body></html>""" % node_name

    def read(node_name):
        return df.field_read(page(node_name), url=HERE, as_of=AS_OF,
                             patterns=PATTERNS)

    assert read("The Other Room").when is None            # the venue fragment
    assert read("Dominic Fike").when == "2026-12-25T20:00:00-06:00"
    assert read("Dominic Fike at The Other Room").when == "2026-12-25T20:00:00-06:00"

    assert not df._claims_this_name("The Other Room",
                                    "Dominic Fike at The Other Room")
    assert df._claims_this_name("Dominic Fike", "Dominic Fike at The Other Room")
    assert df._claims_this_name("Gandahar", "Gandahar (1988)")

    # THE DENIAL SIDE STAYS LOOSE, and that is the whole point of the split:
    # a desk really does print "<presenter> presents <title>", and refusing it
    # would hole every such page. `_same_name` is the denial's rule.
    assert df._same_name("The Yellow Wallpaper",
                         "Trinity Street Theatre presents The Yellow Wallpaper")
    assert df._same_name("Prodigal Sun", "Prodigal Sun at Saengerrunde Hall")
    presented = """<html><body><article>
      <h1>Trinity Street Theatre presents The Yellow Wallpaper</h1>
      <p>Friday, December 25, 2026 8:00PM</p>
      <div class="venue">Trinity Street Theatre</div></article></body></html>"""
    kept = df.follow([row("The Yellow Wallpaper")], fetcher({
        "https://desk.test/event/dominic-fike-1": presented}),
        patterns=PATTERNS, as_of=AS_OF)
    assert kept.rows[0].when == "2026-12-25T20:00:00", kept.reads[0].refusals


def test_only_the_pages_own_heading_is_a_name_it_answers_to():
    """Evaluator, PR #235 r19, openai/absence-only — `_headings()` returned EVERY
    visible heading at the strongest level, and `_pick_subject()` decides which
    heading is the page's SUBJECT for the card boundary. The same question,
    answered two ways.

    So a stale page headed "Some Other Show" with a nested related
    `<h1>Dominic Fike</h1>` answered to both names: the r17 row/page check
    passed on the nested one and the stale page's date and venue filled the
    Dominic row.

        PRE-FIX   _headings(...) == ['Some Other Show', 'Dominic Fike']
                  published 2026-12-25T20:00:00 at 'The Other Room'

    A heading inside a sub-card that `_foreign_sections` excludes is that
    card's name, not this page's."""
    nested = """<html><body><article><h1>Some Other Show</h1>
      <p>Friday, December 25, 2026 8:00PM</p>
      <div class="venue">The Other Room</div>
      <section class="related"><h1>Dominic Fike</h1></section>
    </article></body></html>"""
    assert df._headings(nested, url=HERE, patterns=PATTERNS) == ["Some Other Show"]
    denied = df.follow([row("Dominic Fike")], fetcher({
        "https://desk.test/event/dominic-fike-1": nested}),
        patterns=PATTERNS, as_of=AS_OF)
    assert denied.rows[0].when is None, denied.rows[0].when
    assert denied.rows[0].place_text is None

    # The converse: the page's OWN heading is still the name it answers to, and
    # a page with several headings of the strongest level inside its own card
    # keeps them all.
    plain = ('<html><body><article><h1>Dominic Fike</h1>'
             '<p>Friday, December 25, 2026 8:00PM</p>'
             '<div class="venue">The Hall</div></article></body></html>')
    assert df._headings(plain, url=HERE, patterns=PATTERNS) == ["Dominic Fike"]
    ok = df.follow([row("Dominic Fike")], fetcher({
        "https://desk.test/event/dominic-fike-1": plain}),
        patterns=PATTERNS, as_of=AS_OF)
    assert ok.rows[0].when == "2026-12-25T20:00:00", ok.reads[0].refusals


def test_an_unlinked_sub_card_with_its_own_heading_is_not_this_happening():
    """Evaluator, PR #235 r18, openai/absence-only — and this is R-114, the
    residual opened ONE ROUND EARLIER and blocked on the next. Third time in
    this ticket (R-112 at r5, R-113 at r13, this): `deferred-trust-work` saying
    the same thing three ways — a bound is not a fix.

    R-114 claimed the sub-card test needed "a per-card DOM subtree ... which
    would let a nested block be asked whether it carries its own heading". It
    did not: both scans already record every heading with the sections
    enclosing it, so the question was answerable with data in hand and the
    record was wrong about its own trigger.

    The test is HTML's own outline rule — a sectioning element with a heading
    starts a section of the outline — plus the name check this module already
    makes twice (`_contradicts_this_page` for nodes, `_page_denies_this_row`
    for rows), now a third time one level in.

    THE COST IS REAL AND PINNED BELOW: a card's own subsection headed with a
    LABEL rather than a name ("Details", "When", "Tickets") is excluded too,
    because "Details" names nothing this page names either. A page whose only
    date sits inside such a subsection loses it — paid for never publishing a
    neighbouring show's date, and measured by the next live run, where it lands
    in `date-in-plumbing`."""
    def read(inner):
        return df.field_read(
            f"<html><body><article><h1>Dominic Fike</h1>{inner}</article>"
            f"</body></html>", url=HERE, as_of=AS_OF, patterns=PATTERNS)

    # R-114's surviving shape: the card states nothing, an unlinked nested
    # block states everything, and it is headed for a different show.
    promo = read('<section class="promo"><h2>Also on sale</h2>'
                 '<p>Christmas Special — December 25, 2026 8:00PM</p>'
                 '<div class="venue">The Other Room</div></section>')
    assert promo.when is None, promo.when
    assert promo.place_text is None, promo.place_text

    # A subsection headed with what the page is ABOUT stays the card's.
    named = read('<section><h2>Dominic Fike — tickets</h2>'
                 '<p>Friday, September 18, 2026 8:00PM</p>'
                 '<div class="venue">The Hall</div></section>')
    assert named.when == "2026-09-18T20:00:00", named.refusals
    assert named.place_text == "The Hall"

    # A subsection with NO heading is the r6 case and is unchanged: absence is
    # not disagreement here either.
    quiet = read('<section class="details">'
                 '<p>Friday, September 18, 2026 8:00PM</p>'
                 '<div class="venue">The Hall</div></section>')
    assert quiet.when == "2026-09-18T20:00:00", quiet.refusals
    assert quiet.place_text == "The Hall"

    # THE STATED COST, pinned so it is a decision and not a surprise.
    labelled = read('<section><h2>Details</h2>'
                    '<p>Friday, September 18, 2026 8:00PM</p>'
                    '<div class="venue">The Hall</div></section>')
    assert labelled.when is None, labelled.when


def test_a_page_that_calls_itself_something_else_is_not_this_rows_page():
    """Evaluator, PR #235 r17, openai/absence-only — and the seat named the shape
    exactly: every rule in this module binds a STATEMENT to the PAGE, and none
    bound the PAGE to the ROW. The identity ladder chose the address; nothing
    checked that the page which answered is about the happening the list card
    named, so a stale or recycled permalink filled a row with another show's
    fields:

        PRE-FIX   row 'Dominic Fike' -> when=2026-12-25T20:00:00
                  place='The Other Room'  codes=()

    Same rule as the node check one level up, deliberately: ABSENCE IS NOT
    DISAGREEMENT. A row with no title, or a page with no heading, denies
    nothing. Only two names that both exist and name nothing in each other are
    a denial — so a card reading "The Yellow Wallpaper" and a page headed
    "Trinity Street Theatre presents The Yellow Wallpaper" still reads.

    Asked PER ROW, not per page: two cards can share one address, and a page
    about one of them is not evidence against the other."""
    stale = """<html><body><article><h1>Some Other Show</h1>
      <p>Friday, December 25, 2026 8:00PM</p>
      <div class="venue">The Other Room</div></article></body></html>"""
    result = df.follow([row("Dominic Fike")], fetcher({
        "https://desk.test/event/dominic-fike-1": stale}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when is None, result.rows[0].when
    assert result.rows[0].place_text is None
    assert result.rows[0].filled_from_detail == ()
    # AND IT DOES NOT RECORD HAVING BEEN READ FROM THAT PAGE (r18, blocking from
    # openai/absence-only and a NIT from gemini/dataflow-taint — the same defect
    # from two seats). Keeping `detail_url` made the report file an IDENTITY
    # failure under "page stated no date" instead of "page could not be read".
    assert result.rows[0].detail_url is None
    # A hole with no reason is the `diagnostics-as-data` defect this ticket
    # opened: the run would report the row as dateless when it was never read.
    assert any("Some Other Show" in why for _u, why in result.queued), result.queued

    # A page that says MORE than the card still reads — the common shape, and
    # the reason this reuses `_same_name` rather than testing equality.
    longer = stale.replace("Some Other Show",
                           "Trinity Street Theatre presents Dominic Fike")
    fuller = df.follow([row("Dominic Fike")], fetcher({
        "https://desk.test/event/dominic-fike-1": longer}),
        patterns=PATTERNS, as_of=AS_OF)
    assert fuller.rows[0].when == "2026-12-25T20:00:00", fuller.reads[0].refusals

    # A page with no heading at all denies nothing: absence is not disagreement.
    headless = ('<html><body><article><p>Friday, December 25, 2026 8:00PM</p>'
                '<div class="venue">The Other Room</div></article></body></html>')
    quiet = df.follow([row("Dominic Fike")], fetcher({
        "https://desk.test/event/dominic-fike-1": headless}),
        patterns=PATTERNS, as_of=AS_OF)
    assert quiet.rows[0].when == "2026-12-25T20:00:00", quiet.reads[0].refusals

    # TWO cards at one address: the page is about one of them, and refusing the
    # other's row does not cost the named one its fields.
    both = df.follow([row("Dominic Fike"), row("Some Entirely Other Thing")],
                     fetcher({"https://desk.test/event/dominic-fike-1": longer}),
                     patterns=PATTERNS, as_of=AS_OF)
    assert both.rows[0].when == "2026-12-25T20:00:00"
    assert both.rows[1].when is None


def test_a_nested_card_linking_to_another_happening_is_not_this_one():
    """Evaluator, PR #235 r16, openai/attacker-smuggle — the card boundary is a
    PREFIX test, deliberately (r6: a card's own `<section class="details">` holds
    its own date), and that meant a promo card NESTED inside the main `<article>`
    after the real `<h1>` was read as this happening's:

        PRE-FIX   when=2026-12-25T20:00:00  place='The Other Room'  codes=()

    Told apart by the split ladder's own discriminator, the one r4 already uses
    for places: a card that links to ANOTHER happening's permalink — as the
    committed identity table classifies it — is that happening's card. No chrome
    words, no title match, no new data.

    Only sections nested INSIDE the card are eligible, or the article's own "see
    also" link would mark the whole article foreign and cost the page
    everything (its own arm below)."""
    page = """<html><body><article><h1>Dominic Fike</h1>%s
      <section class="promo">%s
        <p>Christmas Special — December 25, 2026 8:00PM</p>
        <div class="venue">The Other Room</div></section>
    </article></body></html>"""
    link = ('<h2><a href="https://desk.test/event/christmas-special-99">'
            'Also on sale</a></h2>')

    def read(own, promo):
        return df.field_read(page % (own, promo), url=HERE, as_of=AS_OF,
                             patterns=PATTERNS)

    # The nested promo names another happening: nothing of it is this row's.
    smuggled = read("", link)
    assert smuggled.when is None, smuggled.when
    assert smuggled.place_text is None, smuggled.place_text

    # And the card's own statement still wins where it has one — the exclusion
    # removes the promo, it does not disable the card.
    own = read("<p>Friday, September 18, 2026 8:00PM</p>", link)
    assert own.when == "2026-09-18T20:00:00", own.refusals

    # A link at the CARD'S OWN level is the card's business: a page that links
    # to another happening from its own text keeps everything it states.
    see_also = """<html><body><article><h1>Dominic Fike</h1>
      <p>Friday, September 18, 2026 8:00PM</p>
      <div class="venue">The Hall</div>
      <p>See also <a href="https://desk.test/event/christmas-special-99">the
      Christmas Special</a>.</p></article></body></html>"""
    kept = df.field_read(see_also, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert kept.when == "2026-09-18T20:00:00", kept.refusals
    # Its PLACE is refused, and by an older rule than this one: r4's
    # `place-among-other-happenings` says an unbound labelled venue on a page
    # linking to other happenings is not tied to this row. Asserting "The Hall"
    # here was my own expectation being wrong, not the code — pinned as the
    # behaviour that actually exists so the two rules stay legible together.
    assert kept.place_text is None
    assert "place-among-other-happenings" in kept.codes

    # A card's own SUBSECTION still holds its own statements (the r6 reason the
    # boundary is a prefix test at all).
    detailed = """<html><body><article><h1>Dominic Fike</h1>
      <section class="details"><p>Friday, September 18, 2026 8:00PM</p>
      <div class="venue">The Hall</div></section></article></body></html>"""
    sub = df.field_read(detailed, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert sub.when == "2026-09-18T20:00:00", sub.refusals
    assert sub.place_text == "The Hall"


def test_an_ics_snippet_inside_an_html_page_is_not_this_pages_calendar():
    """Evaluator, PR #235 r16, openai/attacker-smuggle — `event_scoped` returned
    True for every `ics` hit, on the reasoning that "a calendar file served at
    this address is this happening's". True of the case that sentence was
    written for; false of the one it guarded. `same_page_dates` runs over the
    whole DOCUMENT, so a DTSTART printed inside an HTML page — a download
    widget, an "add to calendar" block, a related event — was scoped
    unconditionally and won the tier over every card and plumbing check:

        PRE-FIX   when=2026-12-25T20:00:00  carrier='ics'  codes=()

    The test is what the BODY IS, not what a fragment inside it looks like."""
    embedded = """<html><body><article><h1>Dominic Fike</h1>
    <p>No date printed here.</p></article>
    <aside><pre>BEGIN:VCALENDAR
BEGIN:VEVENT
SUMMARY:Some Other Show
DTSTART:20261225T200000
END:VEVENT
END:VCALENDAR</pre></aside></body></html>"""
    read = df.field_read(embedded, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when

    # An actual calendar response still dates the row by construction.
    real = ("BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Dominic Fike\n"
            "DTSTART:20261225T200000\nEND:VEVENT\nEND:VCALENDAR")
    assert df.field_read(real, url=HERE, as_of=AS_OF,
                         patterns=PATTERNS).when == "2026-12-25T20:00:00"


def test_a_bare_clock_face_is_not_a_contradiction():
    """Found by reading the first LIVE run of r14's own rule — the third time in
    this ticket a check was corrected by its own diagnostics.

    That run reported `/event/boeing-boeing-14285657` as contradicting itself:
    its card prints "7:30" while its markup states 19:30. And 19:30 IS half past
    seven. A bare "7:30" states a clock FACE, not an hour of the day; anchoring
    it read 07:30 and called the desk a liar for agreeing with itself — a hole
    on a row where card and markup say the same thing, and a refusal reason that
    misdescribes the page (`diagnostics-as-data`).

    A token carrying no am/pm agrees with either reading, because the desk did
    not say which it meant. AN AMBIGUOUS STATEMENT IS NOT A CONTRADICTING ONE —
    the principle r12 stated and r14 then applied backwards. The cost is stated
    and small: a bare "9:00" no longer contradicts markup saying 21:00, which is
    exactly the case where the card has not said which it means.

    The comparison is asymmetric on purpose: the markup's instant is unambiguous
    by construction, and only the printed side can be a bare face."""
    def page(body):
        return """<html><body><article><h1>The Show</h1>
        <script type="application/ld+json">
        {"@type":"Event","name":"The Show","url":"%s",
         "startDate":"2026-09-18T19:30:00-05:00",
         "location":{"@type":"Place","name":"The Hall"}}</script>
        %s</article></body></html>""" % (HERE, body)

    def when(body):
        return df.field_read(page(body), url=HERE, as_of=AS_OF,
                             patterns=PATTERNS).when

    # The live case, and the whole run of clocks that page prints.
    assert when("<p>Curtain 7:30</p>") == "2026-09-18T19:30:00-05:00"
    assert when("<p>7:30. Late show 10:15 pm. Matinees 4:45 pm.</p>") \
        == "2026-09-18T19:30:00-05:00"
    # A bare face that does NOT match either reading still contradicts.
    assert when("<p>Curtain 8:00</p>") == "2026-09-18"
    # And a token that says which half of the day it means is compared exactly,
    # so r10's finding is untouched.
    assert when("<p>Show 8:00PM</p>") == "2026-09-18"
    assert when("<p>Curtain 7:30 pm</p>") == "2026-09-18T19:30:00-05:00"
    # The live `story-sessions` shape: the card says eight, twice; markup says
    # six. Still a contradiction, and this is what the rule is FOR.
    assert when("<p>8 pm and 8:00 pm</p>") == "2026-09-18"


def test_a_venue_block_that_contains_the_node_s_name_is_not_a_contradiction():
    """Found by the same live run, and it is r13's coverage cost arriving.

    r13 tightened `_same_name` so a lone token must OPEN the longer name. Right
    for IDENTITY — a false yes binds another happening's node — and wrong for
    the PLACE check, where a false no invents a contradiction and holes a place
    we had. `/event/boeing-boeing`'s card labels "Venue Details TexARTS 1110 S
    RR 620, …" against a node saying "TexARTS": the block CONTAINS the venue, it
    simply does not start with it, and the run refused the place.

    This repo had already written the lesson down — `destructive-normalization`
    r9: when one helper serves two callers whose dangerous answers point in
    opposite directions, they share a NAME rather than a helper. Split on the
    QUESTION. Identity asks "are these the same name"; a labelled block asks
    "does this text NAME this place"."""
    block = ("Venue Details TexARTS 1110 S RR 620, Lakeway West Austin and "
             "Lakeway tex-arts.org 2 events")
    assert df._names_within(block, "TexARTS")
    assert not df._same_name(block, "TexARTS")      # identity, still strict
    assert not df._names_within(block, "The Other Room")
    assert not df._names_within(block, "A")         # the one-token floor stands

    page = """<html><body><article><h1>Boeing Boeing</h1>
    <script type="application/ld+json">
    {"@type":"Event","name":"Boeing Boeing","url":"%s",
     "startDate":"2026-09-18T19:30:00-05:00",
     "location":{"@type":"Place","name":"TexARTS"}}</script>
    <div class="venue">Venue Details TexARTS 1110 S RR 620, Lakeway West
      Austin and Lakeway tex-arts.org 2 events</div></article></body></html>""" % HERE
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text == "TexARTS", read.refusals

    # The converse: a card naming a DIFFERENT venue still contradicts.
    other = page.replace("TexARTS 1110 S RR 620", "The Other Room 1110 S RR 620")
    clash = df.field_read(other, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert clash.place_text is None
    assert "card-contradicts-its-own-markup" in clash.codes


def test_a_card_clock_with_no_date_of_its_own_still_contradicts():
    """Evaluator, PR #235 r14, openai/absence-only — the clock comparison only
    counted tokens `resolve_same_page_datetime` could turn into a full INSTANT,
    and that needs a day. A card printing "Show 8:00PM" and no date produced
    nothing to compare, so the node's 19:30 published as settled under a page
    visibly saying eight o'clock:

        PRE-FIX   when=2026-09-18T19:30:00-05:00  codes=()

    The comment beneath that code said unreadable clocks are dropped, and
    conflated two different things: "8:00PM" is perfectly readable as a wall
    clock, it simply has no day of its own. Each printed clock is now anchored
    to the NODE'S day — scaffolding for the parser, never a claim, and the days
    are already known to agree because r8 empties both tiers when they do not.

    Anchoring rather than writing a clock regex is the point: the armed
    `same_page_dates` is the one place that knows what "doors 7 pm" means, and a
    second reader of the same thing is the class this ticket has paid for five
    times already."""
    def page(body):
        return """<html><body><article><h1>The Show</h1>
        <script type="application/ld+json">
        {"@type":"Event","name":"The Show","url":"%s",
         "startDate":"2026-09-18T19:30:00-05:00",
         "location":{"@type":"Place","name":"The Hall"}}</script>
        %s</article></body></html>""" % (HERE, body)

    def read(body):
        return df.field_read(page(body), url=HERE, as_of=AS_OF, patterns=PATTERNS)

    contradicts = read("<p>Show 8:00PM</p>")
    assert contradicts.when == "2026-09-18", contradicts.when
    assert "card-contradicts-its-own-markup" in contradicts.codes
    # The day and the venue survive: refusing a clock is not refusing the node.
    assert contradicts.place_text == "The Hall"

    # The converse — a card clock with no date that AGREES settles nothing new
    # and holes nothing.
    assert read("<p>Show 7:30PM</p>").when == "2026-09-18T19:30:00-05:00"
    # A clock the parser cannot read is still not a contradiction.
    assert read("<p>Show at noon</p>").when == "2026-09-18T19:30:00-05:00"
    # And a card printing no clock at all contradicts nothing.
    assert read("<p>Check listings</p>").when == "2026-09-18T19:30:00-05:00"


def test_one_word_must_open_the_name_it_claims_to_be():
    """Evaluator, PR #235 r13, openai/attacker-smuggle — and the finding is that
    R-113's BOUND DID NOT COVER THE HARM IT NAMED.

    That record said loose single-token containment risks "a wrong FIELD on a
    page that is otherwise the RIGHT happening". It is worse: a lone node called
    "Night" on a page headed "Jazz Night" BINDS, and supplies a date and a venue
    the page never states at all —

        PRE-FIX   when=2026-12-25T20:00:00-06:00  place='The Other Room'  codes=()

    — a whole fabricated instant, not a wrong detail. `deferred-trust-work`, the
    second time in this ticket: test the bound against the harm before writing
    the row.

    Position is the discriminator and it costs nothing this desk uses. Headings
    read `<name> <qualifier>` — never the reverse — so a lone word that OPENS the
    longer name is plausibly what it names and one buried inside it is a fragment
    of somebody else's. r10 declined a leading-token rule over "Live at the
    Continental Club" vs "Continental Club"; that is a TWO token name, and
    multi-token containment is unchanged, anywhere in the string."""
    assert not df._same_name("Night", "Jazz Night")
    assert not df._same_name("Jazz Night", "Night")        # symmetric
    assert df._same_name("Gandahar", "Gandahar 1988")      # opens the heading
    assert df._same_name("Кино", "Кино Night")             # R-113's benign shape
    assert df._same_name("Continental Club",
                         "Live at the Continental Club")   # two tokens, unchanged
    assert df._same_name("Boeing Boeing", "boeing-boeing")
    assert not df._same_name("A", "A Show")                # the r5 floor stands

    lone = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Night","startDate":"2026-12-25T20:00:00-06:00",
     "location":{"@type":"Place","name":"The Other Room"}}</script></head>
    <body><article><h1>Jazz Night</h1></article></body></html>"""
    read = df.field_read(lone, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None, read.when
    assert read.place_text is None, read.place_text

    # The converse: the same page, with the node naming what the page names.
    named = lone.replace('"name":"Night"', '"name":"Jazz Night"')
    ok = df.field_read(named, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert ok.when == "2026-12-25T20:00:00-06:00", ok.refusals
    assert ok.place_text == "The Other Room"


def test_a_placeholder_is_not_a_place():
    """Evaluator, PR #235 r13, openai/attacker-smuggle — `PLACEISH_RE` was a bare
    alternation, so any class or id CONTAINING "place" was read as the page
    labelling a venue. `class="placeholder"` and `class="replacement"` both
    match, and an empty layout div inside the event's own card became the page's
    one labelled place and was published as `place_text`.

    "place" inside "placeholder" is not the page calling anything a place. The
    test is on WORDS, with camelCase split first — `venueName` is one token to a
    regex and two words to whoever wrote it, and refusing that would trade this
    defect for a coverage hole on every desk using the convention.

    One definition, shared with `desk_read` on purpose: the list walk asks the
    same question of the same markup, and two answers would drift."""
    from worker.locale import desk_read

    for yes in ("venue", "event-venue", "eventVenue", "venue name", "the_place",
                "js-location", "whereBox", "VENUE"):
        assert desk_read.says_place(yes), yes
    for no in ("placeholder", "replacement", "displaced", "wherever",
               "locations-menu-placeholder", "", None):
        assert not desk_read.says_place(no), no

    page = """<html><body><article><h1>A Show</h1>
    <p>Saturday, September 5, 2026 &bull; 9:00PM</p>
    <div class="placeholder"></div>
    <div class="ad-replacement">Buy tickets</div></article></body></html>"""
    read = df.field_read(page, url="u", as_of=AS_OF)
    assert read.place_text is None, read.place_text
    assert read.when == "2026-09-05T21:00:00", read.refusals

    # The converse, in the same card: a real label still reads.
    labelled = page.replace('<div class="placeholder"></div>',
                            '<div class="venueName">The Hall</div>')
    assert df.field_read(labelled, url="u", as_of=AS_OF).place_text == "The Hall"


def test_a_card_agreeing_with_its_own_markup_settles_the_day():
    """The converse, and the common case: when the card and the node state the
    same day, the node's fuller answer (its clock and offset) is the row's."""
    page = """<html><head><title>Prodigal Sun</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Prodigal Sun","url":"https://desk.test/events/269428",
      "startDate":"2026-09-04T19:30:00-05:00",
      "location":{"@type":"Place","name":"Saengerrunde Hall"}}</script></head>
    <body><article><h1>Prodigal Sun</h1>
    <p>Friday, September 4, 2026</p></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-04T19:30:00-05:00", read.refusals
    assert read.place_text == "Saengerrunde Hall"
    assert "card-contradicts-its-own-markup" not in read.codes


def test_a_card_naming_a_different_venue_than_its_markup_settles_no_place():
    """The place half of the same finding: a bound node's `location` and the
    card's labelled venue naming different places is the desk contradicting
    itself about where the show is."""
    page = """<html><head><title>Prodigal Sun</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Prodigal Sun","url":"https://desk.test/events/269428",
      "startDate":"2026-09-04T19:30:00-05:00",
      "location":{"@type":"Place","name":"Saengerrunde Hall"}}</script></head>
    <body><article><h1>Prodigal Sun</h1>
    <p>Friday, September 4, 2026</p>
    <div class="venue">The Other Room</div></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text is None, read.place_text
    assert "card-contradicts-its-own-markup" in read.codes
    assert read.when == "2026-09-04T19:30:00-05:00", read.refusals


def test_a_card_printing_the_venue_with_its_address_is_not_a_contradiction():
    """The converse, and why the comparison is `_same_name` rather than
    equality: a card routinely prints the venue WITH its address where the node
    prints the name alone. Calling that a contradiction would refuse every desk
    that tells its readers where to go."""
    page = """<html><head><title>Prodigal Sun</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Prodigal Sun","url":"https://desk.test/events/269428",
      "startDate":"2026-09-04T19:30:00-05:00",
      "location":{"@type":"Place","name":"Saengerrunde Hall"}}</script></head>
    <body><article><h1>Prodigal Sun</h1>
    <p>Friday, September 4, 2026</p>
    <div class="venue">Saengerrunde Hall 1607 San Jacinto, Austin</div>
    </article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text == "Saengerrunde Hall", read.refusals
    assert "card-contradicts-its-own-markup" not in read.codes


def test_a_heading_that_says_more_than_the_node_still_names_it():
    """A desk routinely heads a page with more than the node's name. Requiring
    the two to be EQUAL would refuse the desk that describes its own page
    well."""
    page = """<html><head><title>Prodigal Sun at Saengerrunde Hall | Desk</title>
    <script type="application/ld+json">
    {"@type":"Event","name":"Prodigal Sun","url":"https://desk.test/tickets/9",
      "startDate":"2026-09-04T19:30:00-05:00"}</script></head>
    <body><article><h1>Prodigal Sun at Saengerrunde Hall</h1></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-04T19:30:00-05:00", read.refusals


def test_a_structured_day_never_borrows_a_clock_printed_elsewhere():
    """Evaluator, PR #235 r4, openai/attacker-smuggle — reproduced before fixing.

    A bound JSON-LD node states `2026-09-06` and no time. One content block on
    the page also mentions Sep 6 — the box office notice. Matching the carrier
    to a segment BY DATE made that block the statement that "gave" the day, so
    its 10:00AM became the show's start: a precise time no source stated.

    A `<script>` payload is not a sentence the page prints. It owns no segment
    and borrows no clock.

    The box-office line carries its YEAR deliberately. Written "Sep 6" it does
    not resolve to a date at all, so the segment never becomes the carrier's
    owner and the test passes without ever reaching the defect — green for a
    reason that has nothing to do with the rule (RED_CLASSES:
    false-confidence-gate). Verified against the pre-fix code, which published
    `2026-09-06T10:00:00` with `when_text='2026-09-06 10:00am'` and no refusal
    code at all."""
    page = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Dominic Fike",
      "url":"https://desk.test/event/dominic-fike-1",
      "startDate":"2026-09-06"}</script></head>
    <body><article><h1>Dominic Fike</h1>
    <p>Box office opens September 6, 2026 at 10:00AM.</p>
    <div class="venue">The Hall</div></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-06"
    assert read.when_precision == "date", read.when
    assert "clock-elsewhere" in read.codes, read.refusals
    assert read.place_text == "The Hall"


def test_a_printed_day_still_takes_the_clock_from_its_own_sentence():
    """The converse, so the fix above cannot be mistaken for "no clock ever
    combines". A day printed in the page's own text still takes the time
    printed in that same sentence — which is the founder's (a) case and the
    whole reason the same-page rule exists."""
    page = """<html><head></head>
    <body><article><h1>Dominic Fike</h1>
    <p>Sat Sep 5 &mdash; 9:00PM</p>
    <div class="venue">The Hall</div></article></body></html>"""
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when_precision == "datetime", read.refusals
    assert read.when.startswith("2026-09-05T21:00")


def test_forgetting_the_pattern_table_gets_the_STRICT_answer():
    """Without a table nothing looks like another happening's address, so every
    sidebar node would speak for the row beside it. `None` therefore means the
    COMMITTED table; `()` means "no table" on purpose."""
    import inspect
    assert inspect.signature(df.field_read).parameters["patterns"].default is None


def test_a_dropdown_inside_a_venue_block_is_not_a_second_place():
    """The live run read a restaurant-category `<select>` as one of a page's two
    places, which is how those pages went `places-ambiguous`. A picker offers
    choices; it does not say where a happening is."""
    page = ('<html><body><article>'
            '<div class="venue">The Hall'
            '<select><option>Cafe</option><option>Bakery</option></select></div>'
            '<time datetime="2026-09-06T21:00">Sun</time></article></body></html>')
    read = df.field_read(page, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.place_text == "The Hall"


# --- r3: which NODE emitted this date? ----------------------------------------
# Evaluator, PR #235 r3 (openai/attacker-smuggle), BLOCKING and reproduced: the
# bind asked whether the PAGE had some bound node, not whether THIS date came
# from one. A bound node stating no start, beside a sidebar node that states
# one, published the sidebar's day with no refusal recorded at all.

def _two_nodes(bound_start=None):
    stated = f'"startDate":"{bound_start}",' if bound_start else ""
    return f"""<html><head>
    <script type="application/ld+json">{{"@type":"Event","name":"Dominic Fike",
      "url":"{HERE}",{stated}"location":{{"@type":"Place","name":"The Hall"}}}}</script>
    <script type="application/ld+json">{{"@type":"Event","name":"Other",
      "url":"https://desk.test/event/other-99",
      "startDate":"2026-12-25T20:00:00-06:00"}}</script>
    </head><body><article><h1>Dominic Fike</h1></article></body></html>"""


def test_a_sidebar_date_is_refused_even_when_the_page_has_a_bound_node():
    """The bound node states no start. Under a page-level test the sidebar's
    2026-12-25 became this row's date, silently. The bind is per HIT now."""
    read = df.field_read(_two_nodes(), url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None
    assert "structured-hit-not-bound" in read.codes


def test_the_bound_node_still_wins_when_a_sidebar_also_states_a_date():
    """Per-hit binding is not merely stricter: it RESOLVES a page that a
    page-level test could only refuse as ambiguous."""
    read = df.field_read(_two_nodes("2026-09-06T21:00:00-05:00"), url=HERE,
                         as_of=AS_OF, patterns=PATTERNS)
    assert read.when == "2026-09-06T21:00:00-05:00"
    assert read.place_text == "The Hall"


def test_a_hit_is_matched_to_its_node_by_INSTANT_not_by_string():
    """The parser normalises a node's start to UTC while the page keeps its own
    offset, so the same moment arrives written two ways. Matching on the string
    would drop every dated page whose desk states an offset."""
    assert (df._instant_key("2026-12-26T02:00:00Z")
            == df._instant_key("2026-12-25T20:00:00-06:00"))
    assert df._instant_key("") is None
    assert df._instant_key("not a date") is None


def test_a_root_relative_address_binds_and_also_refuses():
    """Evaluator NIT, PR #235 r3 (gemini). Skipping relative addresses lost a
    real bind AND let a sidebar naming `/event/other-99` look address-less."""
    lone = f"""<html><head><script type="application/ld+json">
    {{"@type":"Event","name":"D","url":"/event/dominic-fike-1",
      "startDate":"2026-09-26T18:00:00-05:00"}}</script></head>
    <body><article><h1>D</h1></article></body></html>"""
    assert df.field_read(lone, url=HERE, as_of=AS_OF,
                         patterns=PATTERNS).when == "2026-09-26T18:00:00-05:00"

    sidebar = lone.replace('"/event/dominic-fike-1"', '"/event/other-99"')
    read = df.field_read(sidebar, url=HERE, as_of=AS_OF, patterns=PATTERNS)
    assert read.when is None
    assert "structured-not-bound" in read.codes
