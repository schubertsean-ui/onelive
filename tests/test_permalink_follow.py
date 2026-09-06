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
    """The live table's own defect, pinned.

    This is the shape of `/event/boeing-boeing-14285657`: a schema.org node
    states the whole instant, and the prose elsewhere on the page prints three
    different clocks. The row has a time. There is no clock hole. Recording
    `clocks-ambiguous` anyway made the run report that 7 of 40 opened pages
    (17%) needed a clock repair when their rows were already complete — and
    the next ticket is chosen by whichever count is largest."""
    page = """<!doctype html><html><body>
    <script type="application/ld+json">{"@type": "Event", "name": "Boeing",
      "startDate": "2026-09-18T19:30:00-05:00"}</script>
    <h1>Boeing Boeing</h1>
    <p>Matinees 4:45 pm. Late show 10:15 pm.</p>
    <div class="venue">TexARTS</div></body></html>"""
    read = df.field_read(page, url="https://desk.test/event/boeing-2", as_of=AS_OF)
    assert read.when == "2026-09-18T19:30:00-05:00"
    assert read.when_precision == "datetime"
    assert "clocks-ambiguous" not in read.codes, read.refusals


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


def test_a_tracking_parameter_on_the_redirect_is_the_same_page():
    """A desk that appends its own `?ref=` has sent us where we asked. Refusing
    that would hole a page we actually read.

    Extended at r12 (gemini/spec-vs-contract NIT): the row's OWN address is the
    identity inside `field_read`, not the landed one. Passing `landed` was
    harmless while `_address` dropped the query and became a coverage loss the
    moment r11 stopped — a node naming the canonical address stopped matching
    on any desk that redirects with a tracking parameter."""
    landed = PageFetch(url="https://desk.test/event/dominic-fike-1", status=200,
                       body=EVENT_PAGE_DATED,
                       final_url="https://desk.test/event/dominic-fike-1/?ref=cal")
    result = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": landed}),
        patterns=PATTERNS, as_of=AS_OF)
    assert result.rows[0].when == "2026-09-05T21:00:00"

    # And a node naming the CANONICAL address still speaks for the row after
    # that redirect — the half r11 broke without noticing.
    spoken = """<html><head><script type="application/ld+json">
    {"@type":"Event","name":"Dominic Fike",
     "url":"https://desk.test/event/dominic-fike-1",
     "startDate":"2026-09-05T21:00:00-05:00",
     "location":{"@type":"Place","name":"The Hall"}}</script></head>
    <body><article><h1>Dominic Fike</h1></article></body></html>"""
    redirected = df.follow([row()], fetcher({
        "https://desk.test/event/dominic-fike-1": PageFetch(
            url="https://desk.test/event/dominic-fike-1", status=200,
            body=spoken,
            final_url="https://desk.test/event/dominic-fike-1?ref=cal")}),
        patterns=PATTERNS, as_of=AS_OF)
    assert redirected.rows[0].when == "2026-09-05T21:00:00-05:00", \
        redirected.reads[0].refusals
    assert redirected.rows[0].place_text == "The Hall"


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
    same = [row(), row("Same show, second card")]
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
    rows = [row(f"Show {i}", listing_url=f"https://desk.test/event/show-{i}")
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
    assert df.PLACEISH_RE is desk_read.PLACEISH_RE


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
    rows = [row(f"Show {i}", listing_url=f"https://desk.test/event/show-{i}")
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
    one = _walk([row("Show 0", listing_url="https://desk.test/event/show-0"),
                 row("Show 1", listing_url="https://desk.test/event/show-1")])
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
    assert df.same_identity("https://d.ex/event?date=2026-09-18&ref=cal",
                            "https://d.ex/event?date=2026-09-18")
    assert df.same_identity("https://d.ex/event?ref=cal", "https://d.ex/event")
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
