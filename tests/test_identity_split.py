"""The split law, as tests that can fail — ONE-LIVE-ENTITY-SPLIT-LAW.md §2.

A list page becomes MANY happenings or ZERO. Never one blob. Never keyed on the
list's own URL. Never split by the word "event" in a class attribute.

The three cases the ticket names are the three the law names:
  (a) two `/event/foo-1` and `/event/bar-2` links -> two rows, those listing_urls
  (b) a list page with no identity and a giant blob -> ZERO rows, `unsplit`
  (c) a test that accepts the blob as one row is a defect — the shape of (c) is
      asserted directly here, so nobody can reintroduce the mash and stay green.

Nothing here is Chronicle-specific: every host in this file is a test host, and
the patterns the reader uses are passed in as the same DATA
(`sources/identity_patterns.json` rows) a live desk would be read with.
"""
from __future__ import annotations

import json
import os

import pytest

from worker.locale import identity_patterns as ip
from worker.locale.desk_read import read
from worker.locale.pack import Door, ListingSelector

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def door(door_id="test-desk", *, url="https://desk.test/events/today",
         door_type="local_desk", kind_scope=("any",), selectors=()) -> Door:
    return Door(
        door_id=door_id, brand="Test Desk", via="Test Desk", door_type=door_type,
        url=url, public=True, intake="html", kind_scope=tuple(kind_scope),
        covers=("Travis",), blocked_reason=None, evidence="catalogued",
        locale_id="us-tx-capcog", listing_selectors=tuple(selectors),
    )


def patterns(*rows):
    return tuple(ip.IdentityPattern(
        pattern_id=f"test-{i}", host_family=host, path_re=path_re,
        grade="fixture_shape", owned=False, note="test") 
        for i, (host, path_re) in enumerate(rows))


EVENT_PATTERNS = patterns(("desk.test", r"/event/[^/]+-\d+"))


# --- (a) two permalinks -> two happenings ------------------------------------

TWO_LINKS = """<!doctype html><html><body>
<main class="feed">
  <div class="row"><h3><a href="/event/foo-1">Foo at the Hall</a></h3>
    <time datetime="2026-09-11T20:00">Fri Sep 11, 8pm</time>
    <span class="venue">The Hall</span></div>
  <div class="row"><h3><a href="/event/bar-2">Bar in the Park</a></h3>
    <time datetime="2026-09-12">Sat Sep 12</time>
    <span class="venue">The Park</span></div>
  <nav><a href="/events/today?page=2">Next</a><a href="/">Home</a></nav>
</main></body></html>"""


def test_two_permalinks_become_two_happenings_with_those_listing_urls():
    result = read(door(), TWO_LINKS, patterns=EVENT_PATTERNS)
    assert result.identity_tier == "permalink"
    assert [r.title for r in result.rows] == ["Foo at the Hall", "Bar in the Park"]
    assert [r.listing_url for r in result.rows] == [
        "https://desk.test/event/foo-1", "https://desk.test/event/bar-2"]
    assert result.identities_declared == 2


def test_the_page_furniture_is_not_a_happening():
    """The nav's next-page link and the masthead link match no pattern, so they
    are not rows. This is the whole reason tier 2 reads a committed table
    instead of "every href on the page"."""
    result = read(door(), TWO_LINKS, patterns=EVENT_PATTERNS)
    assert result.count == 2
    assert all("/event/" in (r.listing_url or "") for r in result.rows)


def test_each_row_keeps_the_fields_printed_beside_its_own_permalink():
    rows = {r.title: r for r in read(door(), TWO_LINKS, patterns=EVENT_PATTERNS).rows}
    assert rows["Foo at the Hall"].when == "2026-09-11T20:00"
    assert rows["Foo at the Hall"].place_text == "The Hall"
    assert rows["Bar in the Park"].when == "2026-09-12"
    assert rows["Bar in the Park"].place_text == "The Park"


# --- (b) no identity -> zero rows, unsplit -----------------------------------

BLOB = """<!doctype html><html><body>
<div class="eventList">
  <h2>Promoted Events</h2>
  Back To The Ranch Sat 8pm The Fixture Room ~ Late Set Sun 10pm The Annex ~
  Kids Story Hour Sun 10am The Library ~ Council Budget Hearing Mon 6pm City Hall
  <a href="/">Austin</a>
  <a href="/EventSearch?page=2">More</a>
</div></body></html>"""


def test_a_blob_with_no_identity_yields_zero_happenings_and_says_unsplit():
    result = read(door(), BLOB, patterns=EVENT_PATTERNS)
    assert result.count == 0
    assert result.unsplit is True
    assert result.identity_tier == "unsplit"
    assert any("unsplit" in note for note in result.notes)


def test_unsplit_is_never_reported_as_an_empty_desk():
    """§4: unsplit is a coverage defect on the DOOR. The note has to say that,
    because a bare `0` in a table reads as 'this desk had nothing on'."""
    notes = " ".join(read(door(), BLOB, patterns=EVENT_PATTERNS).notes)
    assert "coverage defect" in notes
    assert "never one mashed row" in notes


# --- (c) the mash itself, asserted so it cannot come back --------------------

def test_the_blob_is_not_accepted_as_one_row():
    """The defect the law was written from: 40 Chronicle pages, 1 row, titled a
    concatenation. If this ever passes with `count == 1`, the mash is back."""
    result = read(door(), BLOB, patterns=EVENT_PATTERNS)
    assert result.count != 1
    assert result.count == 0
    assert not any("Back To The Ranch" in (r.title or "") for r in result.rows)


def test_a_class_containing_the_word_event_is_not_a_splitter():
    """`<div class="eventList">` is the page's own wrapper. A substring rule
    matches it; whole-token committed selectors do not."""
    result = read(door(selectors=[ListingSelector(tag="div", class_tokens=("event",))]),
                  BLOB, patterns=EVENT_PATTERNS)
    assert result.count == 0
    assert result.unsplit is True


def test_the_list_url_is_never_the_listing_url_of_a_single_event():
    """§2 Forbidden. A structured node that names the page it sits on, or the
    site root, states no row identity — the hole is the honest answer."""
    html = ('<html><head><script type="application/ld+json">'
            + json.dumps({"@context": "https://schema.org", "@type": "Event",
                          "name": "Tonight in Town",
                          "url": "https://desk.test/events/today"})
            + '</script></head><body>x</body></html>')
    result = read(door(), html, base_url="https://desk.test/events/today",
                  patterns=EVENT_PATTERNS)
    assert result.count == 1
    assert result.rows[0].listing_url is None
    assert result.mash_blocked == 1

    root = ('<html><head><script type="application/ld+json">'
            + json.dumps({"@context": "https://schema.org", "@type": "Event",
                          "name": "Whole Site", "url": "https://desk.test"})
            + '</script></head><body>x</body></html>')
    second = read(door(), root, patterns=EVENT_PATTERNS)
    # A bare origin never even reaches the guard: the repo's one JSON-LD parser
    # already refuses a URL with no path. Both layers are asserted, because the
    # row must carry a hole no matter which one catches it.
    assert second.rows[0].listing_url is None


# --- the ladder, rung by rung ------------------------------------------------

def test_a_structured_declaration_is_read_even_when_the_html_never_prints_a_link():
    html = ('<html><head><script type="application/ld+json">'
            + json.dumps([{"@context": "https://schema.org", "@type": "Event",
                           "name": "Wind Ensemble",
                           "url": "https://desk.test/event/wind-9"},
                          {"@context": "https://schema.org", "@type": "Event",
                           "name": "Groundwater Lecture"}])
            + '</script></head><body><p>Two events this week.</p></body></html>')
    result = read(door(), html, patterns=EVENT_PATTERNS)
    assert result.identity_tier == "structured"
    assert [r.title for r in result.rows] == ["Wind Ensemble", "Groundwater Lecture"]


def test_a_structured_node_and_the_card_that_links_to_it_are_one_row():
    """The structured rung merges onto the split by ADDRESS. One card stated
    twice is one row — never two half-rows, never a doubled count."""
    html = ('<html><head><script type="application/ld+json">'
            + json.dumps({"@context": "https://schema.org", "@type": "MusicEvent",
                          "name": "Foo at the Hall",
                          "startDate": "2026-09-11T20:00:00-05:00",
                          "url": "https://desk.test/event/foo-1"})
            + '</script></head><body>'
            '<div class="row"><h3><a href="/event/foo-1">Foo at the Hall</a></h3>'
            '<span class="venue">The Hall</span></div></body></html>')
    result = read(door(), html, patterns=EVENT_PATTERNS)
    assert result.identity_tier == "structured+permalink"
    assert result.count == 1
    assert result.merged_readings == 1
    row = result.rows[0]
    # The instant comes from the structured node (the repo's JSON-LD parser
    # normalises it to UTC); the venue comes from the printed card.
    assert row.when == "2026-09-12T01:00:00Z"
    assert row.place_text == "The Hall"


def test_a_promoted_structured_event_never_swallows_the_printed_cards():
    """The ticket's acceptance bar, "rows ≈ events on the page": a desk that
    publishes ONE promoted Event above many printed cards must not become one
    row. That would be the same mash arriving through the top rung."""
    html = ('<html><head><script type="application/ld+json">'
            + json.dumps({"@context": "https://schema.org", "@type": "Event",
                          "name": "Promoted Thing",
                          "url": "https://desk.test/event/promoted-99"})
            + '</script></head><body>' + TWO_LINKS + '</body></html>')
    result = read(door(), html, patterns=EVENT_PATTERNS)
    assert result.count == 3
    assert sorted(r.title for r in result.rows) == [
        "Bar in the Park", "Foo at the Hall", "Promoted Thing"]


def test_the_desk_selector_rung_runs_only_when_nothing_declared_an_identity():
    selectors = [ListingSelector(tag="div", class_tokens=("row",))]
    result = read(door(selectors=selectors), TWO_LINKS, patterns=EVENT_PATTERNS)
    # Permalinks declared identities, so the selector rung never ran: two rows,
    # not four, and the tier says which rung split the page.
    assert result.identity_tier == "permalink"
    assert result.count == 2


def test_the_grade_of_what_split_the_page_rides_along_with_the_rows():
    """A `fixture_shape` reading splits — refusing to split until somebody has
    fetched the page would make every first read of a new desk a mash. What it
    must never do is arrive looking like a shape somebody has seen live."""
    result = read(door(), TWO_LINKS, patterns=EVENT_PATTERNS)
    assert result.identity_evidence == ["test-0 (fixture_shape)"]
    assert any("fixture_shape" in note for note in result.notes)

    selectors = [ListingSelector(tag="div", class_tokens=("row",),
                                 grade="desk_observed")]
    html = '<div class="row"><h3>One</h3></div><div class="row"><h3>Two</h3></div>'
    selected = read(door(selectors=selectors), html, patterns=EVENT_PATTERNS)
    assert selected.identity_evidence == ["div.row (desk_observed)"]


def test_the_desk_selector_rung_splits_a_page_that_declares_nothing_else():
    selectors = [ListingSelector(tag="div", class_tokens=("row",))]
    html = ('<main class="feed">'
            '<div class="row"><h3>One</h3><time datetime="2026-09-11">Sep 11</time></div>'
            '<div class="row"><h3>Two</h3><time datetime="2026-09-12">Sep 12</time></div>'
            '</main>')
    result = read(door(selectors=selectors), html, patterns=EVENT_PATTERNS)
    assert result.identity_tier == "desk_selector"
    assert [r.title for r in result.rows] == ["One", "Two"]
    assert all(r.listing_url is None for r in result.rows)


def test_a_selector_matching_a_wrapper_and_its_cards_takes_the_cards():
    """A door whose own markup nests the committed token: the outer element
    holds every listing's text, so taking it would be the mash under a
    committed name. The leaves are the rows."""
    selectors = [ListingSelector(tag="div", class_tokens=("row",))]
    html = ('<div class="row wrapper">'
            '<div class="row"><h3>One</h3></div>'
            '<div class="row"><h3>Two</h3></div>'
            '</div>')
    result = read(door(selectors=selectors), html, patterns=EVENT_PATTERNS)
    assert [r.title for r in result.rows] == ["One", "Two"]
    assert not any("One Two" in (r.title or "") for r in result.rows)


def test_identities_declared_is_the_same_number_the_report_prints():
    result = read(door(), TWO_LINKS, patterns=EVENT_PATTERNS)
    assert result.identities_declared == len(
        {r.listing_url for r in result.rows if r.listing_url})
    # ...and the NOTE quotes that same number. A note computed before the count
    # is settled would print 0 for a page that split perfectly.
    assert any("2 identity/identities declared" in n for n in result.notes)


def test_a_selector_committed_for_another_door_never_splits_this_one():
    """Tier 3 is per-door DATA. A door that committed nothing is `unsplit`, not
    'whatever the neighbouring desk's selector happens to match'."""
    html = '<div class="row"><h3>One</h3></div><div class="row"><h3>Two</h3></div>'
    assert read(door(), html, patterns=EVENT_PATTERNS).unsplit is True


def test_a_container_scoped_selector_leaves_the_site_navigation_alone():
    selectors = [ListingSelector(tag="li", container_tag="ul",
                                 container_class_tokens=("calendar",))]
    html = ('<ul class="nav"><li>Home</li><li>About</li></ul>'
            '<ul class="calendar"><li><time datetime="2026-09-06T10:00">Sat</time> '
            'Republic Square Market</li>'
            '<li><time datetime="2026-09-13T09:00">Sat</time> Trailside Market</li></ul>')
    result = read(door(selectors=selectors), html, patterns=EVENT_PATTERNS)
    assert [r.title for r in result.rows] == [
        "Republic Square Market", "Trailside Market"]


SINGLE_IDENTITY_PAGE = """<!doctype html><html><body>
<header><h1>The Desk — Events</h1><nav><a href="/">Home</a></nav></header>
<div class="content">
  <h2>Promoted Events</h2>
  Back To The Ranch Sat 8pm ~ Late Set Sun 10pm ~ Kids Story Hour Sun 10am
  <div class="card"><h3><a href="/event/only-one-1">The Only Event</a></h3>
    <time datetime="2026-09-11T20:00">Fri Sep 11</time>
    <span class="venue">The Hall</span></div>
</div></body></html>"""


def test_a_page_declaring_ONE_identity_is_read_from_its_card_not_its_wrapper():
    """A filtered page or a last page states one event link. With no second
    identity to bound the row, growing it to the outermost wrapper reads the
    page heading as part of the event's title — the mash, arriving on the pages
    nobody thinks to check (evaluator finding, PR #234). Before the fix this
    row's title was 'Promoted Events The Only Event'.
    """
    result = read(door(), SINGLE_IDENTITY_PAGE, patterns=EVENT_PATTERNS)
    assert result.count == 1
    row = result.rows[0]
    assert row.title == "The Only Event"
    assert row.place_text == "The Hall"
    assert row.when == "2026-09-11T20:00"
    assert row.listing_url == "https://desk.test/event/only-one-1"


def test_a_row_never_grows_to_hold_page_level_structure():
    """The bound is HTML's own page-level elements, not anyone's CSS: a card
    never contains a <main>, a <nav>, a page <header>/<footer>, or the <h1>."""
    html = ('<div class="wrap"><nav><a href="/x">nav</a></nav>'
            '<h2>Section heading</h2>'
            '<a href="/event/bare-7">Bare Link Event</a></div>')
    row = read(door(), html, patterns=EVENT_PATTERNS).rows[0]
    assert row.title == "Bare Link Event"
    assert "Section heading" not in (row.title or "")


def test_one_identity_stated_by_two_anchors_in_one_card_is_one_row():
    html = ('<div class="row"><a href="/event/foo-1"><img></a>'
            '<h3><a href="/event/foo-1">Foo at the Hall</a></h3>'
            '<a href="/event/foo-1">tickets</a></div>')
    result = read(door(), html, patterns=EVENT_PATTERNS)
    assert result.count == 1
    assert result.rows[0].listing_url == "https://desk.test/event/foo-1"


def test_a_fragment_is_the_same_identity_and_a_query_is_not():
    html = ('<div class="row"><a href="/event/foo-1#tickets">Foo</a></div>'
            '<div class="row"><a href="/event/foo-1">Foo</a></div>'
            '<div class="row"><a href="/event/foo-1?date=2026-09-12">Foo Later</a></div>')
    result = read(door(), html, patterns=EVENT_PATTERNS)
    assert [r.listing_url for r in result.rows] == [
        "https://desk.test/event/foo-1", "https://desk.test/event/foo-1?date=2026-09-12"]


def test_a_desk_the_table_does_not_cover_is_unsplit_not_mashed():
    """The same page on a host with no committed pattern and no committed
    selector. Zero rows and a named defect — never a blob."""
    other = door(url="https://unknown.test/events/today")
    result = read(other, TWO_LINKS, base_url="https://unknown.test/events/today",
                  patterns=EVENT_PATTERNS)
    assert result.count == 0 and result.unsplit is True


# --- the committed table itself ----------------------------------------------

def test_the_committed_table_loads_and_every_row_is_typed():
    rows = ip.load_patterns()
    assert rows, "the committed identity table must not be empty"
    for row in rows:
        assert row.grade in ip.GRADES
        assert isinstance(row.owned, bool)
        assert row.note, f"{row.pattern_id}: every row states its provenance"


def test_chronicle_event_permalinks_are_one_row_of_the_table_not_a_function():
    """§2: "Chronicle `/event/{slug}-{id}` is one row in that table, not a
    special case in the reader."""
    rows = ip.load_patterns()
    hit = ip.match(
        "https://calendar.austinchronicle.com/austin/event/some-show-1234567", rows)
    assert hit is not None and hit.host_family == "calendar.austinchronicle.com"
    assert ip.match(
        "https://calendar.austinchronicle.com/austin/EventSearch?sortType=date",
        rows) is None


def _code_only(path: str) -> str:
    """The module with every comment and string literal removed, so a host named
    in prose (the incident these rules were written from) is not confused with a
    host named in CODE."""
    import io
    import tokenize
    out = []
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    return " ".join(out).lower()


def test_no_reader_module_names_a_host():
    """The Chronicle-only function the ticket forbids cannot exist if no host
    appears in the readers' code at all. Host knowledge lives in
    `sources/identity_patterns.json` and in the locale pack — as data."""
    for name in ("desk_read.py", "desk_walk.py", "identity_patterns.py"):
        code = _code_only(os.path.join(REPO, "worker", "locale", name))
        for host in ("austinchronicle", "do512", "eventbrite", "chronicle"):
            assert host not in code, f"{name} names {host} in code, not in data"


def test_a_query_string_never_confers_identity():
    rows = patterns(("desk.test", r"/event/[^/]+-\d+"))
    assert ip.match("https://desk.test/search?next=/event/foo-1", rows) is None


def test_the_host_family_matches_subdomains_but_not_lookalikes():
    rows = patterns(("do512.test", r"/events/\d{4}/"))
    assert ip.match("https://family.do512.test/events/2026/x", rows) is not None
    assert ip.match("https://notdo512.test/events/2026/x", rows) is None


@pytest.mark.parametrize("bad,message", [
    ({"pattern_id": "x", "host_family": "h", "path_re": "([", "grade": "fixture_shape",
      "owned": False}, "does not compile"),
    ({"pattern_id": "x", "host_family": "h", "path_re": "/e/", "grade": "guessed",
      "owned": False}, "grade"),
    ({"pattern_id": "x", "host_family": "h", "path_re": "/e/", "grade": "fixture_shape"},
     "owned"),
])
def test_a_malformed_table_raises_rather_than_narrowing_coverage(bad, message, tmp_path):
    path = tmp_path / "identity_patterns.json"
    path.write_text(json.dumps({"patterns": [bad]}), encoding="utf-8")
    with pytest.raises(ip.IdentityPatternError) as exc:
        ip.load_patterns(str(path))
    assert message in str(exc.value)


def test_a_missing_table_raises_and_says_what_it_costs(tmp_path):
    with pytest.raises(ip.IdentityPatternError) as exc:
        ip.load_patterns(str(tmp_path / "absent.json"))
    assert "unsplit" in str(exc.value)


# --- the walk's counters, which are what the founder's table prints ----------

def _walk(pages, door_obj, *, start="https://desk.test/events/today"):
    from worker.locale.desk_walk import PageFetch, walk

    def fetch(url):
        page = pages.get(url)
        if page is None:
            return PageFetch(url=url, status=404, body="")
        return PageFetch(url=url, status=200, body=page, final_url=url)

    return walk(door_obj, fetch, start_url=start, patterns=EVENT_PATTERNS)


def test_the_walk_counts_unsplit_pages_rather_than_calling_the_desk_empty():
    pages = {"https://desk.test/events/today":
             TWO_LINKS.replace("</main>", '<a href="/events/today?page=2">Next</a></main>'),
             "https://desk.test/events/today?page=2": BLOB}
    one = _walk(pages, door())
    assert one.count == 2
    assert one.unsplit_n == 1
    assert one.mash_n == 0
    assert one.identity_tiers == ["permalink", "unsplit"]


def test_a_walled_page_is_counted_as_a_wall_not_as_an_empty_calendar():
    from worker.locale.desk_walk import PageFetch, walk

    def fetch(url):
        return PageFetch(url=url, status=403, body="")

    one = walk(door(), fetch, start_url="https://desk.test/events/today",
               patterns=EVENT_PATTERNS)
    assert one.count == 0
    assert one.walled_n == 1
    assert one.unread_n == 1
    assert one.unsplit_n == 0, "a page nobody read is not a page that would not split"


def test_a_proxy_403_with_no_http_status_still_counts_as_a_wall():
    """The sandbox's own denial arrives as a transport error whose text is
    truncated for display. A counter that depended on that truncation would
    print `403_n = 0` for a desk nobody could reach."""
    from worker.locale.desk_walk import PageFetch, walk

    long_url = "https://desk.test/events/today?" + "filter=x&" * 40

    def fetch(url):
        return PageFetch(
            url=url,
            error="ProxyError: HTTPSConnectionPool(host='desk.test', port=443): "
                  "Max retries exceeded with url: " + url
                  + " (Caused by ProxyError('Unable to connect to proxy', "
                    "OSError('Tunnel connection failed: 403 Forbidden')))",
            walled=True)

    one = walk(door(), fetch, start_url=long_url, patterns=EVENT_PATTERNS)
    assert one.walled_n == 1
    assert "403" not in (one.pages[0].blocked_reason or ""), (
        "this fixture only proves anything while the reason IS truncated")


def test_mash_n_is_derived_from_the_rows_the_walk_actually_produced():
    """`mash_n = 0` is the ticket's claim, so it is computed from the output —
    never read back out of the counter kept by the code that made it."""
    pages = {"https://desk.test/events/today": TWO_LINKS}
    one = _walk(pages, door())
    assert one.mash_n == 0
    assert all(r.listing_url and "/event/" in r.listing_url for r in one.rows)
