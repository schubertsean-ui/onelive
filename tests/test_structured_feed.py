"""Unit tests for the deterministic structured first-party feed importer
(worker/importers/structured_feed.py + run_structured_import.py). NO network, NO
DB — inline ICS / HTML fixtures and monkeypatch only, so the full parse →
normalize path is proven WITHOUT reaching any live calendar.

Covers: RFC-5545 line folding, DTSTART TZID→UTC 'Z' conversion, all-day
(VALUE=DATE) keeping the date with a null time, title-based classification, the
JSON-LD @graph Event/non-Event filter and field mapping (name/startDate/offers/
location), the "no title / no id → skipped, never fabricated" invariant, @type
list/single/array tolerance, and the runner's fail-loud selection behavior.
"""
import json as _json

import worker.importers.run_structured_import as runner
from worker.importers.structured_feed import (
    PROVIDER_ICS,
    PROVIDER_JSONLD,
    PROVIDER_LOCALIST,
    discover_ics_links,
    import_localist,
    import_source,
    localist_events_url,
    normalize_structured,
    parse_ics,
    parse_jsonld,
    parse_localist,
)

# ---- ICS fixtures ------------------------------------------------------------

# Two VEVENTs. The first is TIMED with a TZID (America/Chicago, CDT = UTC-5 in
# July) and uses RFC-5545 line folding on the long SUMMARY (the continuation line
# begins with a single space). The second is ALL-DAY (VALUE=DATE, bare date).
ICS_FIXTURE = (
    "BEGIN:VCALENDAR\r\n"
    "VERSION:2.0\r\n"
    "PRODID:-//Test Venue//Calendar//EN\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:evt-timed-001@testvenue.org\r\n"
    "SUMMARY:Austin Symphony: Beethoven's Ninth with a very long title that\r\n"
    "  folds across two lines\r\n"
    "DTSTART;TZID=America/Chicago:20260725T200000\r\n"
    "DTEND;TZID=America/Chicago:20260725T223000\r\n"
    "LOCATION:Bass Concert Hall\\, Austin\r\n"
    "URL:https://testvenue.org/events/beethoven-ninth\r\n"
    "DESCRIPTION:An evening of classical music.\r\n"
    "END:VEVENT\r\n"
    "BEGIN:VEVENT\r\n"
    "UID:evt-allday-002@testvenue.org\r\n"
    "SUMMARY:Museum Free Day\r\n"
    "DTSTART;VALUE=DATE:20260801\r\n"
    "DTEND;VALUE=DATE:20260802\r\n"
    "LOCATION:Blanton Museum of Art\r\n"
    "END:VEVENT\r\n"
    "END:VCALENDAR\r\n"
)


def test_ics_parses_two_events_with_folding():
    events = parse_ics(ICS_FIXTURE)
    assert len(events) == 2
    timed, allday = events
    # Folded SUMMARY reassembled into one logical value (continuation stripped of
    # exactly one leading space).
    assert timed["title"] == (
        "Austin Symphony: Beethoven's Ninth with a very long title that folds "
        "across two lines")
    # ICS \, escape unescaped in LOCATION.
    assert timed["venue_name"] == "Bass Concert Hall, Austin"
    assert allday["title"] == "Museum Free Day"


def test_ics_tzid_converts_to_utc_z():
    timed = parse_ics(ICS_FIXTURE)[0]
    # America/Chicago 2026-07-25 20:00 CDT (UTC-5) -> 2026-07-26 01:00 UTC.
    assert timed["start_time"] == "2026-07-26T01:00:00Z"
    assert timed["end_time"] == "2026-07-26T03:30:00Z"
    assert timed["all_day"] is False


def test_ics_all_day_keeps_date_nulls_time():
    allday = parse_ics(ICS_FIXTURE)[1]
    # An all-day date is kept as a bare date — NO fabricated midnight-UTC instant,
    # NO trailing 'Z' (the source asserted a day, not an instant).
    assert allday["start_time"] == "2026-08-01"
    assert allday["all_day"] is True
    assert "T" not in allday["start_time"] and "Z" not in allday["start_time"]


def test_ics_normalize_shape_and_classification():
    events = parse_ics(ICS_FIXTURE)
    n = normalize_structured(events[0], provider=PROVIDER_ICS, source_name="test_venue")
    assert n is not None
    assert n["source_provider"] == "ics"
    assert n["external_id"] == "evt-timed-001@testvenue.org"  # stable from UID
    assert n["title"].startswith("Austin Symphony")
    # No cultural_domain hint → deterministic classify_from_title on the real
    # title ("symphony" → performing-arts).
    assert n["category"] == "performing-arts"
    assert n["confidence"] == "confirmed"
    assert n["start_time"] == "2026-07-26T01:00:00Z"
    assert n["venue_name"] == "Bass Concert Hall, Austin"
    assert n["ticket_url"] == "https://testvenue.org/events/beethoven-ninth"
    # A calendar row carries no performer/coords — honest nulls, not fabricated.
    assert n["performer"] is None and n["venue_lat"] is None


def test_ics_cultural_domain_hint_overrides_classifier():
    events = parse_ics(ICS_FIXTURE)
    n = normalize_structured(events[1], provider=PROVIDER_ICS, source_name="blanton",
                             cultural_domain="visual-arts")
    assert n["category"] == "visual-arts"  # catalog hint wins
    assert n["subsegment"] is None
    assert n["start_time"] == "2026-08-01"


def test_ics_skips_vevent_without_summary_or_dtstart():
    # No SUMMARY, and a separate VEVENT with no DTSTART: both must be SKIPPED
    # (never fabricated into an event with an invented title/time).
    ics = (
        "BEGIN:VCALENDAR\r\n"
        "BEGIN:VEVENT\r\nUID:a\r\nDTSTART:20260901T180000Z\r\nEND:VEVENT\r\n"  # no SUMMARY
        "BEGIN:VEVENT\r\nUID:b\r\nSUMMARY:Has title but no start\r\nEND:VEVENT\r\n"  # no DTSTART
        "BEGIN:VEVENT\r\nUID:c\r\nSUMMARY:Good One\r\nDTSTART:20260901T180000Z\r\nEND:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    events = parse_ics(ics)
    assert [e["title"] for e in events] == ["Good One"]
    assert events[0]["start_time"] == "2026-09-01T18:00:00Z"  # UTC 'Z' passed through


# ---- JSON-LD fixtures --------------------------------------------------------

# An HTML page with a single ld+json <script> whose @graph holds one Event
# (a MusicEvent subtype) and one non-Event (an Organization) — only the Event is
# kept and mapped.
HTML_JSONLD = """<!doctype html>
<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "name": "Test Presenter",
      "url": "https://presenter.example"
    },
    {
      "@type": "MusicEvent",
      "@id": "https://presenter.example/e/spoon-live",
      "name": "Spoon Live at the Theater",
      "startDate": "2026-07-25T20:00:00-05:00",
      "endDate": "2026-07-25T23:00:00-05:00",
      "url": "https://presenter.example/e/spoon-live",
      "image": "https://presenter.example/img/spoon.jpg",
      "location": {
        "@type": "Place",
        "name": "The Grand Theater",
        "address": {
          "@type": "PostalAddress",
          "streetAddress": "100 Congress Ave",
          "addressLocality": "Austin"
        }
      },
      "offers": {
        "@type": "AggregateOffer",
        "lowPrice": "35.00",
        "highPrice": "75.00",
        "priceCurrency": "USD"
      }
    }
  ]
}
</script>
</head><body>Nothing else.</body></html>
"""


def test_jsonld_keeps_only_event_and_maps_fields():
    events = parse_jsonld(HTML_JSONLD)
    assert len(events) == 1  # the Organization node dropped
    e = events[0]
    assert e["title"] == "Spoon Live at the Theater"          # name -> title
    assert e["start_time"] == "2026-07-26T01:00:00Z"          # -05:00 -> UTC 'Z'
    assert e["end_time"] == "2026-07-26T04:00:00Z"
    assert e["venue_name"] == "The Grand Theater"             # location.name
    assert e["venue_city"] == "Austin"                        # address.addressLocality
    assert e["venue_address"] == "100 Congress Ave"
    assert e["price_min"] == 35.0 and e["price_max"] == 75.0  # offers
    assert e["currency"] == "USD"
    assert e["image_url"] == "https://presenter.example/img/spoon.jpg"


def test_jsonld_normalize_shape():
    e = parse_jsonld(HTML_JSONLD)[0]
    n = normalize_structured(e, provider=PROVIDER_JSONLD, source_name="presenter")
    assert n["source_provider"] == "jsonld"
    assert n["external_id"] == "https://presenter.example/e/spoon-live"  # @id
    # The event's OWN @type wins over the title: this is a MusicEvent (a Spoon
    # concert), so the category is live-music — NOT 'theater' from the title's
    # "...at the Theater" (the old title-only logic was fooled by the venue word).
    # "You know it's a band, so you know the category" (founder 2026-07-25).
    assert n["category"] == "live-music"  # from @type=MusicEvent, not the title
    assert n["price_min"] == 35.0 and n["is_free"] is False
    assert n["confidence"] == "confirmed"


def test_jsonld_type_tolerance_list_single_and_array():
    # (a) @type as a LIST including an Event subtype.
    list_type = """<script type="application/ld+json">
    {"@type": ["Thing", "TheaterEvent"], "name": "Typed As List",
     "startDate": "2026-08-10T19:00:00Z"}</script>"""
    # (b) a SINGLE top-level object (not wrapped in a list or @graph).
    single = """<script type="application/ld+json">
    {"@type": "Event", "name": "Single Object", "startDate": "2026-08-11"}</script>"""
    # (c) a top-level ARRAY of objects, mixing an Event and a non-Event.
    array = """<script type="application/ld+json">
    [{"@type": "WebPage", "name": "not an event"},
     {"@type": "ComedyEvent", "name": "In An Array", "startDate": "2026-08-12T20:00:00Z"}]</script>"""

    assert [e["title"] for e in parse_jsonld(list_type)] == ["Typed As List"]
    single_ev = parse_jsonld(single)
    assert [e["title"] for e in single_ev] == ["Single Object"]
    # startDate is a bare date → all-day, kept as a date with a null time.
    assert single_ev[0]["start_time"] == "2026-08-11" and single_ev[0]["all_day"] is True
    assert [e["title"] for e in parse_jsonld(array)] == ["In An Array"]


def test_jsonld_missing_name_normalizes_to_none_not_fabricated():
    # An Event node with a startDate but NO name: parse keeps it, but normalize
    # returns None (no title → not published), never an invented title.
    html = """<script type="application/ld+json">
    {"@type": "Event", "startDate": "2026-08-13T20:00:00Z",
     "url": "https://x.example/e/1"}</script>"""
    events = parse_jsonld(html)
    assert len(events) == 1 and events[0]["title"] is None
    assert normalize_structured(events[0], provider=PROVIDER_JSONLD,
                                source_name="x") is None


def test_normalize_no_stable_id_returns_none():
    # No uid, no url, and (deliberately) no start → nothing stable to key on.
    raw = {"title": "Untethered", "start_time": None}
    assert normalize_structured(raw, provider=PROVIDER_ICS, source_name="s") is None
    # But title + start alone yields a deterministic hashed id (stable, not random).
    raw2 = {"title": "Anchored", "start_time": "2026-08-01T00:00:00Z"}
    n = normalize_structured(raw2, provider=PROVIDER_ICS, source_name="s")
    assert n is not None and n["external_id"].startswith("ics:")


def test_normalize_rejects_unknown_provider():
    import pytest
    with pytest.raises(ValueError):
        normalize_structured({"title": "x", "uid": "1"}, provider="ticketmaster",
                             source_name="s")


# ---- import_source auto-detect (monkeypatched fetch, no network) -------------

def test_import_source_autodetects_ics(monkeypatch):
    monkeypatch.setattr("worker.importers.structured_feed.fetch_url",
                        lambda url, **kw: ICS_FIXTURE)
    out = import_source("https://x/ics", source_name="test_venue")
    assert len(out) == 2
    assert all(n["source_provider"] == "ics" for n in out)


def test_import_source_autodetects_jsonld(monkeypatch):
    monkeypatch.setattr("worker.importers.structured_feed.fetch_url",
                        lambda url, **kw: HTML_JSONLD)
    out = import_source("https://x/page", source_name="presenter",
                        cultural_domain="live-music")
    assert len(out) == 1
    assert out[0]["source_provider"] == "jsonld"
    assert out[0]["category"] == "live-music"  # hint honored end-to-end


# ---- ICS-feed auto-discovery (the "16 of 18 sources yield zero" fix) ----------

# A calendar INDEX page that renders its event list client-side: it carries NO
# schema.org Event JSON-LD, but it advertises the same schedule as an iCalendar
# feed three ways — the standard <link rel="alternate" type="text/calendar">, a
# webcal: subscribe link, and a visible ".ics" download link (relative).
HTML_NO_JSONLD_WITH_ICS = """<!doctype html>
<html><head>
  <title>Mohawk — Upcoming Shows</title>
  <link rel="alternate" type="text/calendar" href="/events/feed.ics">
</head><body>
  <div id="calendar-app"><!-- events rendered by JS, no server-side markup --></div>
  <a href="webcal://mohawkaustin.com/subscribe.ics">Subscribe</a>
  <a href="https://mohawkaustin.com/download/shows.ics?token=x">Download .ics</a>
  <a href="mailto:box@mohawkaustin.com">Email us</a>
</body></html>"""


def test_discover_ics_links_orders_and_resolves():
    links = discover_ics_links(HTML_NO_JSONLD_WITH_ICS, "https://mohawkaustin.com/")
    # <link rel=alternate> first (resolved relative → absolute), then webcal:
    # rewritten to https:, then the .ics href. mailto: dropped.
    assert links == [
        "https://mohawkaustin.com/events/feed.ics",
        "https://mohawkaustin.com/subscribe.ics",
        "https://mohawkaustin.com/download/shows.ics?token=x",
    ]


def test_discover_ics_links_empty_when_no_feed():
    assert discover_ics_links("<html><body>no calendar here</body></html>",
                              "https://x/") == []


def test_import_source_falls_back_to_advertised_ics(monkeypatch):
    """An HTML calendar page with no JSON-LD must not report zero: import_source
    finds the advertised .ics feed and parses it. This is the exact failure mode
    that left 16 of 18 first-party 'cultural' sources empty on the live feed."""
    fetched: list[str] = []

    def fake_fetch(url, **kw):
        fetched.append(url)
        if url.endswith(".ics"):
            return ICS_FIXTURE            # the advertised feed serves real events
        return HTML_NO_JSONLD_WITH_ICS    # the index page has no JSON-LD

    monkeypatch.setattr("worker.importers.structured_feed.fetch_url", fake_fetch)
    out = import_source("https://mohawkaustin.com/", source_name="mohawk_austin")
    assert len(out) == 2                                  # from ICS_FIXTURE
    assert all(n["source_provider"] == "ics" for n in out)  # provenance is the feed
    # The page was fetched first; the highest-priority feed (<link>) was used and
    # no further feed URLs were fetched once it yielded events.
    assert fetched[0] == "https://mohawkaustin.com/"
    assert fetched[1] == "https://mohawkaustin.com/events/feed.ics"
    assert len(fetched) == 2


def test_import_source_ics_fallback_skips_dead_feed(monkeypatch):
    """A first advertised feed that 404s is skipped (logged, not fatal) and the
    next advertised feed is tried."""
    def fake_fetch(url, **kw):
        if url.endswith("feed.ics"):
            raise OSError("HTTP Error 404: Not Found")
        if url.endswith(".ics"):
            return ICS_FIXTURE
        return HTML_NO_JSONLD_WITH_ICS

    monkeypatch.setattr("worker.importers.structured_feed.fetch_url", fake_fetch)
    out = import_source("https://mohawkaustin.com/", source_name="mohawk_austin")
    assert len(out) == 2  # recovered from the second advertised feed


def test_import_source_no_jsonld_no_feed_returns_empty(monkeypatch):
    """No JSON-LD and no advertised feed → honestly empty (the runner logs it and,
    only if EVERY source is empty, fails loud). Never fabricated, never raised."""
    monkeypatch.setattr("worker.importers.structured_feed.fetch_url",
                        lambda url, **kw: "<html><body>rendered client-side</body></html>")
    assert import_source("https://x/", source_name="empty_src") == []


def test_import_source_prefers_jsonld_over_ics_fallback(monkeypatch):
    """When the page DOES carry JSON-LD events, those are used and no ICS feed is
    fetched — the fallback is only for the zero-JSON-LD case."""
    html_with_both = HTML_JSONLD.replace(
        "</head>", '<link rel="alternate" type="text/calendar" href="/f.ics"></head>')
    fetched: list[str] = []

    def fake_fetch(url, **kw):
        fetched.append(url)
        return html_with_both

    monkeypatch.setattr("worker.importers.structured_feed.fetch_url", fake_fetch)
    out = import_source("https://presenter.example/", source_name="presenter",
                        cultural_domain="live-music")
    assert len(out) == 1 and out[0]["source_provider"] == "jsonld"
    assert fetched == ["https://presenter.example/"]  # ICS feed never fetched


# ---- runner selection + fail-loud (no network, no DB) ------------------------

def test_runner_selects_only_structured_candidates():
    catalog = [
        {"id": "tm", "base_url": "https://tm", "access_method": "api_key",
         "allowed": ["api_access"]},
        {"id": "lib", "base_url": "https://lib", "access_method": "public_web_or_feed",
         "allowed": ["feed_if_offered"]},
        {"id": "loc", "base_url": "https://loc", "access_method": "localist_feed",
         "allowed": ["localist_json_feed"]},
        {"id": "noURL", "base_url": None, "access_method": "public_web_or_ics",
         "allowed": ["ics_feed_if_offered"]},
    ]
    picks = {e["id"] for e in runner._select(catalog, only=set(), limit=None)}
    assert picks == {"lib", "loc"}  # api excluded; null base_url excluded


def test_runner_every_source_zero_fails_loud(monkeypatch, tmp_path):
    catalog = [{"id": "lib", "base_url": "https://lib",
                "access_method": "public_web_or_feed", "allowed": ["feed_if_offered"],
                "cultural_domain": "library"}]
    p = tmp_path / "cat.json"
    import json as _json
    p.write_text(_json.dumps(catalog))
    monkeypatch.setattr(runner, "import_source", lambda *a, **k: [])
    assert runner.main(["--catalog", str(p), "--dry-run"]) == 3  # all-zero → loud


def test_runner_one_zero_source_tolerated(monkeypatch, tmp_path):
    catalog = [
        {"id": "lib", "base_url": "https://lib", "access_method": "public_web_or_feed",
         "allowed": ["feed_if_offered"], "cultural_domain": "library"},
        {"id": "loc", "base_url": "https://loc", "access_method": "localist_feed",
         "allowed": ["localist_json_feed"], "cultural_domain": "ideas"},
    ]
    p = tmp_path / "cat.json"
    import json as _json
    p.write_text(_json.dumps(catalog))

    def fake_import(url, *, source_name, cultural_domain=None):
        if source_name == "lib":
            return []  # one empty source — tolerated
        return [{"category": "ideas", "source_provider": "jsonld", "venue_name": "V",
                 "venue_city": None, "venue_address": None}]

    monkeypatch.setattr(runner, "import_source", fake_import)
    assert runner.main(["--catalog", str(p), "--dry-run"]) == 0  # the other landed


def test_runner_missing_catalog_fails_closed():
    assert runner.main(["--catalog", "/no/such/catalog.json", "--dry-run"]) == 2


def test_runner_real_catalog_has_structured_candidates():
    # The shipped catalog must actually select the institutional first-party
    # sources (ranks 42-59) — proves the selection predicate isn't vacuous.
    import json as _json
    catalog = _json.loads(runner.DEFAULT_CATALOG.read_text())
    picks = {e["id"] for e in runner._select(catalog, only=set(), limit=None)}
    assert "ut_austin_localist" in picks   # localist_json_feed
    assert "austin_public_library" in picks  # feed_if_offered
    assert "bookpeople" in picks            # ics_feed_if_offered
    assert "ticketmaster_discovery" not in picks  # api_key, not structured


def test_event_type_beats_a_misleading_title_and_venue():
    # Founder 2026-07-25: "if you know a venue is hosting a lecture, or a band,
    # comedian or comedy event then you know the category." The event's declared
    # @type is the authority — above a title keyword and above the venue's domain.
    # A comedian at a music-tagged venue is COMEDY, not live-music.
    comedy = {"title": "An Evening with a Comic", "start_time": "2026-11-07T02:00:00Z",
              "_raw_props": {"@type": "ComedyEvent", "@id": "x1"}}
    n = normalize_structured(comedy, provider=PROVIDER_JSONLD, source_name="Mohawk",
                             cultural_domain="live-music")
    assert n["category"] == "comedy"

    # A lecture (EducationEvent) at an UNTAGGED multi-purpose room is 'ideas',
    # read from the event — the case venue-tagging alone could never get right.
    lecture = {"title": "The Future of Cities", "start_time": "2026-11-07T02:00:00Z",
               "_raw_props": {"@type": "EducationEvent", "@id": "x2"}}
    n2 = normalize_structured(lecture, provider=PROVIDER_JSONLD, source_name="Paramount",
                              cultural_domain=None)
    assert n2["category"] == "ideas"

    # A bare 'Event' (no subtype) carries no category signal → falls through to
    # the venue's curated domain, never fabricated from the generic type.
    generic = {"title": "Something", "start_time": "2026-11-07T02:00:00Z",
               "_raw_props": {"@type": "Event", "@id": "x3"}}
    n3 = normalize_structured(generic, provider=PROVIDER_JSONLD, source_name="Mohawk",
                              cultural_domain="live-music")
    assert n3["category"] == "live-music"


# ---- Localist calendar-platform JSON API (the calendar_platform pathway) ------

def _localist_body(events, total=None):
    """Build a Localist /api/2/events response body around a list of event dicts."""
    return _json.dumps({
        "events": [{"event": e} for e in events],
        "page": {"current": 1, "size": 100, "total": total if total is not None else len(events)},
    })


_LOCALIST_EVENT = {
    "id": 55123,
    "title": "Distinguished Lecture: The Physics of Music",
    "localist_url": "https://events.txst.edu/event/distinguished_lecture",
    "photo_url": "https://events.txst.edu/photos/55123.jpg",
    "location_name": "Performing Arts Center",
    "address": "601 University Dr",
    "allday": False,
    "event_instances": [
        {"event_instance": {"id": 1, "start": "2026-07-25T19:00:00-05:00",
                            "end": "2026-07-25T21:00:00-05:00"}},
    ],
    "geo": {"latitude": "29.8899", "longitude": "-97.9389", "city": "San Marcos",
            "street": "601 University Dr"},
}


def test_localist_events_url_derivation():
    assert localist_events_url("https://events.txst.edu/") == \
        "https://events.txst.edu/api/2/events?days=365&pp=100&page=1"
    assert localist_events_url("https://calendar.utexas.edu/anything", page=3) == \
        "https://calendar.utexas.edu/api/2/events?days=365&pp=100&page=3"


def test_localist_events_url_rejects_bad_base():
    import pytest
    with pytest.raises(ValueError):
        localist_events_url("not-a-url")


def test_parse_localist_maps_fields_including_geo():
    raws = parse_localist(_localist_body([_LOCALIST_EVENT]))
    assert len(raws) == 1
    r = raws[0]
    assert r["title"] == "Distinguished Lecture: The Physics of Music"
    assert r["start_time"] == "2026-07-26T00:00:00Z"   # 19:00 -05:00 → 00:00Z next day
    assert r["end_time"] == "2026-07-26T02:00:00Z"
    assert r["venue_name"] == "Performing Arts Center"
    assert r["venue_city"] == "San Marcos"
    assert r["venue_address"] == "601 University Dr"
    assert r["venue_lat"] == 29.8899 and r["venue_lng"] == -97.9389
    assert r["url"].endswith("/event/distinguished_lecture")
    assert r["uid"] == "localist:55123"


def test_parse_localist_normalizes_end_to_end_keeping_coords():
    raws = parse_localist(_localist_body([_LOCALIST_EVENT]))
    n = normalize_structured(raws[0], provider=PROVIDER_LOCALIST,
                             source_name="txstate_events", cultural_domain="ideas")
    assert n is not None
    assert n["source_provider"] == "localist"
    assert n["external_id"] == "localist:55123"
    assert n["confidence"] == "confirmed"            # first-party anchor by construction
    assert n["category"] == "ideas"                  # venue cultural_domain hint honored
    assert n["venue_lat"] == 29.8899 and n["venue_lng"] == -97.9389  # coords preserved
    assert n["venue_city"] == "San Marcos"


def test_parse_localist_skips_untitled_and_non_event_wrappers():
    body = _localist_body([{"id": 1}, {"id": 2, "title": "Real Event",
                                       "event_instances": [
                                           {"event_instance": {"start": "2026-08-01T18:00:00-05:00"}}]}])
    raws = parse_localist(body)
    titles = [r["title"] for r in raws if r["title"]]
    assert titles == ["Real Event"]  # the id-only (untitled) event is dropped, never fabricated


def test_parse_localist_non_json_raises_valueerror():
    import pytest
    with pytest.raises(ValueError):
        parse_localist("<html>not localist</html>")


def test_import_localist_paginates_and_dedupes(monkeypatch):
    """import_localist pages until a short page, de-duping a show that recurs
    across pages, and stops cleanly."""
    pages = {
        1: _localist_body([dict(_LOCALIST_EVENT, id=i) for i in range(100)], total=150),
        2: _localist_body([dict(_LOCALIST_EVENT, id=i) for i in range(90, 140)], total=150),
    }

    def fake_fetch(url, **kw):
        import urllib.parse as up
        page = int(up.parse_qs(up.urlparse(url).query)["page"][0])
        return pages[page]

    monkeypatch.setattr("worker.importers.structured_feed.fetch_url", fake_fetch)
    out = import_localist("https://events.txst.edu/", source_name="txstate_events")
    ids = {n["external_id"] for n in out}
    assert len(ids) == len(out)          # de-duped by external_id (ids 90..99 overlap)
    assert len(out) == 140               # 100 + 40 new, page 2 short → stop
    assert all(n["source_provider"] == "localist" for n in out)


def test_import_localist_clean_skip_on_non_localist(monkeypatch):
    """A non-Localist host: /api/2/events 404s (OSError) or returns HTML
    (ValueError) → [] with no raise."""
    monkeypatch.setattr("worker.importers.structured_feed.fetch_url",
                        lambda url, **kw: (_ for _ in ()).throw(OSError("404")))
    assert import_localist("https://example.com/", source_name="x") == []

    monkeypatch.setattr("worker.importers.structured_feed.fetch_url",
                        lambda url, **kw: "<html>not localist</html>")
    assert import_localist("https://example.com/", source_name="x") == []


def test_import_source_tier3_localist_fallback(monkeypatch):
    """A Localist-backed calendar page: no JSON-LD, no advertised ICS feed, so
    import_source falls through to the Localist API and returns its events."""
    def fake_fetch(url, **kw):
        if "/api/2/events" in url:
            return _localist_body([_LOCALIST_EVENT])
        return "<html><body>rendered client-side, no jsonld, no ics link</body></html>"

    monkeypatch.setattr("worker.importers.structured_feed.fetch_url", fake_fetch)
    out = import_source("https://events.txst.edu/", source_name="txstate_events",
                        cultural_domain="ideas")
    assert len(out) == 1
    assert out[0]["source_provider"] == "localist"
    assert out[0]["venue_city"] == "San Marcos"
