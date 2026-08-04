"""Pure-function tests for the Eventbrite discovery lane (founder paths 1+2).

No network anywhere: the extraction regexes, catalog eligibility filter, and
API-payload parsing are the logic that decides WHAT we collect and FROM WHOM —
so they are pinned here, while the fetch shells stay thin.
"""
import json

from tools.harvest_eventbrite_links import eligible_sources, extract_links
from tools.resolve_eventbrite_event_orgs import organizer_of
from tools.search_discover_eventbrite import extract_orgs


# ---- harvest: catalog eligibility (the per-source access contract) ----------

def test_eligible_requires_public_access_grant():
    catalog = [
        {"id": "mohawk", "base_url": "https://mohawkaustin.com/",
         "allowed": ["public_calendar_pages"]},
        {"id": "partner_only", "base_url": "https://x.example/",
         "allowed": ["partner_feed"]},
        {"id": "no_url", "allowed": ["public_pages"]},
    ]
    ids = [s["id"] for s in eligible_sources(catalog)]
    assert ids == ["mohawk"]


def test_eligible_never_includes_eventbrite_itself():
    # The whole point of path 1: eventbrite.com said no to datacenter fetches,
    # so the harvester must be structurally unable to fetch it.
    catalog = [{"id": "eventbrite_api",
                "base_url": "https://www.eventbrite.com/platform/api",
                "allowed": ["public_event_pages"]}]
    assert eligible_sources(catalog) == []


# ---- harvest: link extraction ------------------------------------------------

def test_extract_organizer_and_event_links():
    html = (
        '<a href="https://www.eventbrite.com/o/mohawk-presents-12345678">EB</a>'
        '<a href="//eventbrite.com/e/spoon-live-tickets-987654321012">tix</a>'
        '<a href="https://example.com/not-eventbrite/o/fake-999999">no</a>'
    )
    orgs, events = extract_links(html)
    assert orgs == {"12345678": "mohawk presents"}
    assert events == {"987654321012"}


def test_extract_ignores_short_ids_and_dedupes():
    html = (
        '<a href="https://www.eventbrite.com/o/x-123">too short</a>'
        '<a href="https://www.eventbrite.com/o/first-name-11223344">1</a>'
        '<a href="https://www.eventbrite.com/o/other-name-11223344">2</a>'
    )
    orgs, events = extract_links(html)
    # First slug wins; one id, once.
    assert orgs == {"11223344": "first name"}
    assert events == set()


# ---- resolve: official-API payload parsing -----------------------------------

def test_organizer_of_reads_expanded_payload():
    ev = {"id": "987654321012",
          "organizer": {"id": "12345678", "name": "Mohawk Presents"}}
    cand = organizer_of(ev)
    assert cand == {"org_id": "12345678", "name": "Mohawk Presents",
                    "via_event": "987654321012"}


def test_organizer_of_missing_or_empty_is_none_never_guessed():
    assert organizer_of({"id": "1"}) is None
    assert organizer_of({"id": "1", "organizer": {"name": "x"}}) is None


# ---- search: API-result extraction --------------------------------------------

def test_extract_orgs_from_search_payload():
    payload = {"items": [
        {"link": "https://www.eventbrite.com/o/austin-parks-foundation-8827437011",
         "snippet": "Austin Parks Foundation events"},
        {"link": "https://www.eventbrite.com/e/some-show-tickets-111",
         "snippet": "not an organizer link"},
    ]}
    orgs = extract_orgs(payload)
    assert orgs == {"8827437011": "austin parks foundation"}


def test_extract_orgs_reads_ids_anywhere_in_payload_but_never_fabricates():
    # Ids may appear in snippets/metatags too; junk digits without the /o/
    # shape must never count.
    payload = {"items": [{"snippet":
        "see eventbrite.com/o/red-river-cultural-district-17280985999 tonight",
        "link": "https://news.example/article-20260804"}]}
    assert extract_orgs(payload) == {"17280985999": "red river cultural district"}
    assert extract_orgs({"items": [{"link": "https://news.example/93939393939"}]}) == {}


def test_search_payload_roundtrips_json():
    # extract_orgs serializes the payload — prove non-ASCII survives.
    payload = {"items": [{"link":
        "https://www.eventbrite.com/o/caf%C3%A9-nights-44556677"}]}
    orgs = extract_orgs(payload)
    assert list(orgs) == ["44556677"]
    json.dumps(orgs)
