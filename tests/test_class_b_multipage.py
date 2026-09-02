"""Class B multi-page follow — discovery, the wall rule, and the run report.

Two units under test, both hermetic (no network, no DB, no model):

  worker/sourcing/page_discovery.py  which same-site pages a start page offers
  tools/class_b_multipage.py         the walk over them, under the wall rule

The wall tests are the load-bearing ones. Coverage Law's class-D rule is
absolute — "do not fetch; open a claim/submit path" — so they assert what the
tool DID NOT DO (the exact set of URLs it requested), not merely what it
reported. A tool that records a wall and then keeps knocking would pass a
report-shaped assertion and violate the law.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import class_b_multipage as cbm  # noqa: E402
from worker.sourcing.page_discovery import (  # noqa: E402
    DEFAULT_MAX_COMMON_PATH_GUESSES, SKIP_LOGIN, SKIP_NOT_A_PAGE, SKIP_OFF_SITE,
    VIA_COMMON_PATH, VIA_LINK_PATH, VIA_LINK_TEXT, common_path_candidates,
    discover_event_pages,
)

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "class_b")
HOME = "https://venue.example/"


def _page(body: str, head: str = "") -> str:
    return f"<html><head>{head}</head><body>{body}</body></html>"


# --------------------------------------------------------------------------
# Discovery — the three signal tiers
# --------------------------------------------------------------------------

def test_link_text_is_the_strongest_signal_and_ranks_first():
    """The site's OWN label for its schedule outranks a path guess, because the
    cap will bite on a big site and the labelled link is the one a human would
    follow."""
    html = _page('<a href="/x9">Upcoming Shows</a><a href="/events/2026">2026</a>')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)

    assert [p.url for p in result.pages] == [
        "https://venue.example/x9", "https://venue.example/events/2026",
    ]
    assert result.pages[0].via == VIA_LINK_TEXT
    assert result.pages[1].via == VIA_LINK_PATH
    # The evidence names the deciding token, so a human can audit the call.
    assert "shows" in result.pages[0].evidence
    assert "event" in result.pages[1].evidence


def test_common_paths_are_offered_only_as_last_tier_and_are_marked_as_guesses():
    html = _page('<a href="/calendar">Calendar</a>')
    result = discover_event_pages(html, HOME, limit=10)

    assert result.pages[0].url == "https://venue.example/calendar"
    assert result.pages[0].via == VIA_LINK_TEXT
    guesses = [p for p in result.pages if p.via == VIA_COMMON_PATH]
    assert guesses, "conventional locations should still be offered"
    assert all("guess" in p.via for p in guesses)
    # The linked calendar is not ALSO guessed at — one URL, one fetch.
    assert [p.url for p in result.pages].count("https://venue.example/calendar") == 1


def test_a_page_that_links_nothing_still_gets_the_conventional_locations():
    """The Parish case: a homepage with no calendar link at all. Without the
    guesses this source contributes zero pages forever."""
    html = _page('<a href="/about">About</a><a href="/rentals">Private rentals</a>')
    result = discover_event_pages(html, HOME, limit=15)

    assert result.pages, "a link-less homepage must still offer the conventional paths"
    assert {p.via for p in result.pages} == {VIA_COMMON_PATH}


def test_guesses_are_bounded_separately_so_they_never_eat_the_page_budget():
    html = _page("<p>nothing here</p>")
    result = discover_event_pages(html, HOME, limit=15)
    assert len(result.pages) == DEFAULT_MAX_COMMON_PATH_GUESSES

    tightened = discover_event_pages(html, HOME, limit=15, max_common_path_guesses=2)
    assert len(tightened.pages) == 2


# --------------------------------------------------------------------------
# Discovery — what it structurally refuses
# --------------------------------------------------------------------------

def test_off_site_links_are_refused_even_when_they_look_like_events():
    """An off-site link is a DIFFERENT source with its own catalog row and its
    own access class. Following it here would ingest something nobody
    classified."""
    html = _page('<a href="https://www.ticketweb.com/events">Buy tickets</a>')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)

    assert result.pages == []
    assert result.skipped == [("https://www.ticketweb.com/events", SKIP_OFF_SITE)]


def test_a_sign_in_url_is_dropped_before_the_caller_can_fetch_it():
    """Coverage Law: never fetch a wall. The drop happens in discovery, so the
    fetching caller is never handed the option."""
    html = _page('<a href="/account/login?next=/events">Member events</a>')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)

    assert result.pages == []
    assert result.skipped == [
        ("https://venue.example/account/login?next=/events", SKIP_LOGIN)]


def test_file_assets_are_not_pages():
    html = _page('<a href="/2026-season-events.pdf">2026 season events</a>')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)

    assert result.pages == []
    assert result.skipped == [
        ("https://venue.example/2026-season-events.pdf", SKIP_NOT_A_PAGE)]


def test_an_ics_href_goes_to_the_feed_bucket_and_is_never_fetched_as_a_page():
    """One URL, one lane: an .ics is the structured-feed authority's business,
    so it must not also enter the page list and be fetched twice."""
    html = _page(
        '<a href="/events.ics">Events calendar</a>',
        head='<link rel="alternate" type="text/calendar" href="/events.ics">')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)

    assert result.pages == []
    assert result.ics_links == ["https://venue.example/events.ics"]


def test_the_start_url_itself_is_never_refetched():
    html = _page('<a href="/">Events</a><a href="https://venue.example">Shows</a>')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)
    assert result.pages == []


def test_www_is_folded_but_no_other_host_difference_is():
    html = _page(
        '<a href="https://venue.example/events">Events</a>'
        '<a href="https://tickets.venue.example/events">Tickets</a>')
    result = discover_event_pages(html, "https://www.venue.example/", limit=10,
                                  include_common_paths=False)

    assert [p.url for p in result.pages] == ["https://venue.example/events"]
    assert ("https://tickets.venue.example/events", SKIP_OFF_SITE) in result.skipped


def test_urls_are_de_duplicated_across_trailing_slash_fragment_and_case():
    html = _page(
        '<a href="/events">Events</a><a href="/events/">Shows</a>'
        '<a href="/events#top">Calendar</a><a href="HTTPS://VENUE.EXAMPLE/events">Lineup</a>')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)
    assert [p.url for p in result.pages] == ["https://venue.example/events"]


def test_a_query_string_is_a_different_page_and_is_kept():
    html = _page('<a href="/calendar?month=2026-09">September</a>'
                 '<a href="/calendar?month=2026-10">October</a>')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)
    assert [p.url for p in result.pages] == [
        "https://venue.example/calendar?month=2026-09",
        "https://venue.example/calendar?month=2026-10",
    ]


def test_an_icon_link_is_read_through_its_accessible_name():
    html = _page('<a href="/x" aria-label="Upcoming events"><svg/></a>')
    result = discover_event_pages(html, HOME, limit=10, include_common_paths=False)
    assert [p.url for p in result.pages] == ["https://venue.example/x"]


def test_malformed_html_yields_a_result_rather_than_a_crash():
    broken = '<a href="/events">Events<div><p>unclosed everything'
    result = discover_event_pages(broken, HOME, limit=10, include_common_paths=False)
    assert [p.url for p in result.pages] == ["https://venue.example/events"]


def test_a_zero_limit_means_no_pages_never_uncapped():
    html = _page('<a href="/events">Events</a>')
    assert discover_event_pages(html, HOME, limit=0).pages == []


def test_jsonld_is_counted_through_the_existing_authority():
    html = _page("<p>hello</p>", head=(
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Event","name":"A show",'
        '"startDate":"2026-09-12T20:00:00-05:00"}</script>'))
    result = discover_event_pages(html, HOME, limit=5, include_common_paths=False)
    assert result.jsonld_events == 1


def test_common_path_candidates_are_built_off_the_origin_not_the_start_path():
    got = common_path_candidates("https://venue.example/austin")
    assert "https://venue.example/events" in got
    assert not any("/austin/events" in u for u in got)


def test_discovery_is_deterministic():
    html = _page('<a href="/calendar">Calendar</a><a href="/shows/2026">2026</a>')
    first = discover_event_pages(html, HOME, limit=15)
    second = discover_event_pages(html, HOME, limit=15)
    assert [p.url for p in first.pages] == [p.url for p in second.pages]


# --------------------------------------------------------------------------
# The walk — the wall rule, proven by what was NOT requested
# --------------------------------------------------------------------------

class _RecordingFetcher:
    """A fetcher that answers from a dict and REMEMBERS every URL asked for."""

    def __init__(self, responses):
        self.responses = responses
        self.requested = []

    def get(self, url):
        self.requested.append(url)
        entry = self.responses.get(url)
        if entry is None:
            return cbm.FetchOutcome(url=url, status=404)
        return cbm.FetchOutcome(
            url=url,
            status=entry.get("status", 200),
            text=entry.get("text", ""),
            content_type=entry.get("content_type", "text/html"),
            final_url=entry.get("final_url"),
            error=entry.get("error"),
        )


ENTRY = {"id": "venue", "name": "Venue", "base_url": HOME,
         "access_method": "public_web", "allowed": ["public_event_pages"]}

BODY = _page(
    '<a href="/events">Events</a><a href="/calendar">Calendar</a>'
    "<p>Sept 4, 8pm The Deer. Sept 5, 9pm Golden Dawn Arkestra. "
    "Sept 11 Hikes. Sept 19 Grupo Fantasma. Doors at seven, all ages.</p>")


def test_a_wall_on_the_start_page_ends_the_source_with_no_second_request():
    fetcher = _RecordingFetcher({HOME: {"status": 403}})
    outcome = cbm.run_source(ENTRY, fetcher, max_pages=15, extract=None)

    assert outcome.source_class == "D"
    assert "403" in outcome.blocked_reason
    assert outcome.pages_followed == []
    # The law, mechanically: exactly one knock, and nothing after it.
    assert fetcher.requested == [HOME]


def test_a_sign_in_redirect_on_a_followed_page_walls_the_whole_source():
    fetcher = _RecordingFetcher({
        HOME: {"text": BODY},
        "https://venue.example/events": {
            "status": 302, "final_url": "https://venue.example/account/login"},
        "https://venue.example/calendar": {"text": BODY},
    })
    outcome = cbm.run_source(ENTRY, fetcher, max_pages=15, extract=None)

    assert outcome.source_class == "D"
    assert "login wall" in outcome.blocked_reason
    # /calendar was discovered and would have been next — it must NOT be fetched.
    assert "https://venue.example/calendar" not in fetcher.requested


def test_a_404_is_a_miss_not_a_wall_and_the_walk_continues():
    """A missing guess must never demote a legitimate public source — that would
    let one broken URL cost a venue's whole calendar."""
    fetcher = _RecordingFetcher({
        HOME: {"text": BODY},
        "https://venue.example/calendar": {"text": BODY},
    })
    outcome = cbm.run_source(ENTRY, fetcher, max_pages=15, extract=None)

    assert outcome.source_class == "B"
    assert outcome.blocked_reason == ""
    outcomes = {p.url: p.outcome for p in outcome.pages_followed}
    assert outcomes["https://venue.example/events"] == cbm.PAGE_MISSING
    assert outcomes["https://venue.example/calendar"] == cbm.PAGE_OK
    assert outcome.extract_ready == 1


def test_a_sensor_rejected_page_is_recorded_and_never_counted_as_extract_ready():
    fetcher = _RecordingFetcher({
        HOME: {"text": BODY},
        "https://venue.example/events": {"text": '<div id="cal"></div>'},
        "https://venue.example/calendar": {"text": BODY},
    })
    outcome = cbm.run_source(ENTRY, fetcher, max_pages=15, extract=None)

    outcomes = {p.url: p.outcome for p in outcome.pages_followed}
    assert outcomes["https://venue.example/events"] == cbm.PAGE_SENSOR_REJECTED
    assert outcome.extract_ready == 1


def test_the_page_budget_is_enforced_by_the_walk():
    fetcher = _RecordingFetcher({HOME: {"text": BODY}})
    outcome = cbm.run_source(ENTRY, fetcher, max_pages=3, extract=None)
    # start page + at most 3 followed pages
    assert len(fetcher.requested) == 4
    assert len(outcome.pages_followed) == 3


def test_the_dry_run_never_reaches_the_extract_path():
    """`extract=None` must not import or call the model path — that is what
    makes the default mode runnable with no DB and no key."""
    called = []
    original = cbm._extract_page
    cbm._extract_page = lambda **kw: called.append(kw) or (0, "")
    try:
        fetcher = _RecordingFetcher({HOME: {"text": BODY},
                                     "https://venue.example/events": {"text": BODY}})
        cbm.run_source(ENTRY, fetcher, max_pages=15, extract=None)
    finally:
        cbm._extract_page = original
    assert called == []


def test_extract_mode_hands_each_ready_page_to_the_existing_extract_path():
    """The tool adds no extraction of its own: it points the certified path at a
    different URL and counts what that path wrote."""
    seen = []
    original = cbm._extract_page

    def _fake(*, entry, url, text, source_class, provider):
        seen.append((url, source_class, provider))
        return 2, ""

    cbm._extract_page = _fake
    try:
        fetcher = _RecordingFetcher({HOME: {"text": BODY},
                                     "https://venue.example/events": {"text": BODY},
                                     "https://venue.example/calendar": {"text": BODY}})
        outcome = cbm.run_source(ENTRY, fetcher, max_pages=15,
                                 extract=cbm.PROVIDER_CLAUDE)
    finally:
        cbm._extract_page = original

    assert [u for u, _, _ in seen] == [
        "https://venue.example/events", "https://venue.example/calendar"]
    assert {c for _, c, _ in seen} == {"B"}
    assert {p for _, _, p in seen} == {cbm.PROVIDER_CLAUDE}
    assert outcome.candidates == 4


# --------------------------------------------------------------------------
# Extraction: the path is really called, and a refusal is really reported
# --------------------------------------------------------------------------

def test_the_two_providers_are_the_ones_that_already_exist():
    """No new extractor: `claude` is the production provider the scheduled loop
    uses, `stub` is the no-model provider worker/run_once.py already uses."""
    from ai.bedrock_provider import BedrockProvider
    from ai.claude_provider import ClaudeProvider

    assert isinstance(cbm._build_provider(cbm.PROVIDER_STUB), BedrockProvider)
    assert isinstance(cbm._build_provider(cbm.PROVIDER_CLAUDE), ClaudeProvider)


def test_a_page_that_cannot_extract_reports_file_function_error(monkeypatch):
    """The founder's format, mechanically: one line naming WHERE it died.

    Without a key the production provider refuses loudly rather than returning
    an empty extraction, and that refusal is what the run table must show
    instead of a bare zero.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    count, line = cbm._extract_page(
        entry=ENTRY, url="https://venue.example/events", text=BODY,
        source_class="B", provider=cbm.PROVIDER_CLAUDE)

    assert count == 0
    file_part, func_part, error_part = (p.strip() for p in line.split(",", 2))
    assert file_part == "ai/claude_provider.py"
    assert func_part == "_get_client"
    assert error_part.startswith("ExtractionConfigError:")


def test_an_extraction_refusal_never_kills_the_walk(monkeypatch):
    """One page that cannot extract must not cost the rest of the source."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fetcher = _RecordingFetcher({HOME: {"text": BODY},
                                 "https://venue.example/events": {"text": BODY},
                                 "https://venue.example/calendar": {"text": BODY}})
    outcome = cbm.run_source(ENTRY, fetcher, max_pages=15,
                             extract=cbm.PROVIDER_CLAUDE)

    assert outcome.candidates == 0
    assert outcome.extract_ready == 2, "both pages were still fetched and sensed"
    assert len(outcome.extract_errors) == 1, "one distinct reason, not one per page"


def test_a_zero_carries_its_reason_into_the_table(monkeypatch):
    """A bare 0 reads as \"extraction found nothing\"; it must read as why."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    outcome = cbm.SourceOutcome(
        source_id="v", name="Venue", start_url=HOME, source_class="B",
        extract_errors=["ai/claude_provider.py, _get_client, ExtractionConfigError: no key"])
    table = cbm.render_table([outcome], extract=cbm.PROVIDER_CLAUDE, fixtures=True)

    assert "| 0 |" in table
    assert "Why those are zero — file, function, error" in table
    assert "_get_client" in table


# --------------------------------------------------------------------------
# Selection, budgets, and honest reporting
# --------------------------------------------------------------------------

def test_only_class_b_entries_with_a_start_url_are_selected():
    catalog = [
        {"id": "walled", "name": "W", "base_url": "https://w.example/",
         "access_method": "oauth_api"},                                  # D
        {"id": "feed", "name": "F", "base_url": "https://f.example/",
         "access_method": "public_web_or_ics"},                          # A
        {"id": "nourl", "name": "N", "access_method": "public_web"},     # no URL
        {"id": "good", "name": "G", "base_url": "https://g.example/",
         "access_method": "public_web"},                                 # B
    ]
    assert [e["id"] for e in cbm.select_class_b(catalog, limit=10)] == ["good"]


def test_selection_honours_the_source_ceiling():
    catalog = [{"id": f"s{i}", "name": f"S{i}", "base_url": f"https://s{i}.example/",
                "access_method": "public_web"} for i in range(20)]
    assert len(cbm.select_class_b(catalog, limit=10)) == 10


@pytest.mark.parametrize("raw", ["0", "-1", "abc"])
def test_a_ceiling_of_zero_or_less_is_rejected_never_read_as_uncapped(raw):
    import argparse
    with pytest.raises(argparse.ArgumentTypeError):
        cbm._positive_int(raw)


def test_the_table_never_prints_a_zero_that_would_read_as_extraction_found_nothing():
    outcome = cbm.SourceOutcome(source_id="v", name="Venue", start_url=HOME,
                                source_class="B", extract_ready=3)
    table = cbm.render_table([outcome], extract=None, fixtures=True)

    assert "candidates (extract not run)" in table
    assert "3 extract-ready" in table
    assert "Fixture run" in table


def test_a_fixture_wall_can_never_be_written_into_the_live_claim_queue():
    """A wall seen in a fixture is not a wall a site put up."""
    with pytest.raises(SystemExit):
        cbm.main(["--fixtures", FIXTURE_DIR, "--update-claim-queue"])


def test_observed_walls_become_claim_queue_rows_with_a_human_next_step():
    outcome = cbm.SourceOutcome(
        source_id="empire", name="Empire", start_url="https://empireatx.com/",
        source_class="D", blocked_reason="HTTP 403 on first contact")
    rows = cbm.observed_class_d_rows([outcome])

    assert len(rows) == 1
    assert rows[0].origin == "observed"
    assert rows[0].why.startswith("HTTP 403")
    assert rows[0].suggested_path, "a queued wall must carry an ask a person can walk"


# --------------------------------------------------------------------------
# The committed fixture run — the PR table's own evidence
# --------------------------------------------------------------------------

def test_the_fixture_run_reproduces_the_committed_evidence(monkeypatch):
    """The PR table's numbers are machine output, not hand-copied: this test
    re-runs the walk over the committed fixtures — extraction included — and
    compares it to the committed JSON record.

    Hermetic by construction, not by hope: with ANTHROPIC_API_KEY removed the
    production provider refuses at client construction, so no model call and no
    DB write is reachable, and the recorded zero-plus-reason is deterministic
    on any machine.
    """
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    catalog = cbm.load_catalog(cbm.DEFAULT_CATALOG)
    selected = cbm.select_class_b(catalog, limit=10)

    produced = []
    for entry in selected:
        produced.append(cbm.run_source(
            entry, cbm.FixtureFetcher(FIXTURE_DIR), max_pages=15,
            extract=cbm.PROVIDER_CLAUDE))

    evidence_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "evidence", "CLASS_B_MULTIPAGE_FIXTURE_RUN.json")
    with open(evidence_path, encoding="utf-8") as handle:
        committed = json.load(handle)

    assert json.loads(cbm._as_json(produced)) == committed


def test_the_fixture_run_follows_pages_and_walls_exactly_two_sources():
    catalog = cbm.load_catalog(cbm.DEFAULT_CATALOG)
    outcomes = [cbm.run_source(e, cbm.FixtureFetcher(FIXTURE_DIR), max_pages=15,
                               extract=None)
                for e in cbm.select_class_b(catalog, limit=10)]

    walled = [o for o in outcomes if o.source_class == "D"]
    assert {o.source_id for o in walled} == {"empire_atx", "emos"}
    # The whole point of the session: pages BEYOND the homepage actually got read.
    assert sum(o.followed_ok for o in outcomes) >= 10
