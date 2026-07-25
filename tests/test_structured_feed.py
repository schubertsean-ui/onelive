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
import worker.importers.run_structured_import as runner
from worker.importers.structured_feed import (
    PROVIDER_ICS,
    PROVIDER_JSONLD,
    discover_feed_urls,
    import_source,
    normalize_structured,
    parse_ics,
    parse_jsonld,
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


def test_the_curated_moat_sources_are_actually_importable():
    """The local-moat rows (ranks 77-114) must be SELECTED by the importer.

    Founder catch 2026-07-25 ("Only 40?"): those 38 curated venue/org sources
    carry `structured_feed_verify` (verified first-party page, exact feed path
    unconfirmed). The selector originally accepted only tokens like
    `ics_feed_if_offered`, so every moat source was silently skipped — catalogued
    but never fetched. This pins the wiring so the moat cannot go dark again.
    """
    import importlib.util, json, pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "run_structured_import", root / "worker" / "importers" / "run_structured_import.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    catalog = json.loads((root / "sources" / "master_sources_catalog_120.json")
                         .read_text(encoding="utf-8"))
    moat = [e for e in catalog
            if isinstance(e.get("rank"), int) and 77 <= e["rank"] <= 114]
    assert moat, "expected the curated moat rows in the catalog"

    # Every moat source that is an EVENTS calendar must be selectable. The one
    # deliberate exception is the artist-identity spine (MusicBrainz), which
    # supplies artist/MBID data, not events — excluding it from an EVENTS import
    # is correct, not a gap.
    event_sources = [e for e in moat if e.get("category") != "artist_directory"]
    skipped = [e["id"] for e in event_sources if not mod._is_structured_candidate(e)]
    assert not skipped, (
        f"{len(skipped)} curated moat event source(s) would NEVER be fetched: {skipped}")

    # And the overall selectable set must be materially larger than the
    # pre-moat baseline of 18 — i.e. the moat really is in the import scope.
    selectable = [e for e in catalog if mod._is_structured_candidate(e)]
    assert len(selectable) >= 55, f"only {len(selectable)} sources selectable"


# ---- canonical feed discovery -------------------------------------------------

def test_declared_feed_link_is_tried_first():
    """A site that DECLARES its calendar via <link rel=alternate> must be
    believed before any guessing — it told us where the data is."""
    html = ('<html><head><link rel="alternate" type="text/calendar" '
            'href="/cal/all.ics"></head><body></body></html>')
    urls, _ = discover_feed_urls("https://venue.example/", html)
    assert urls[0] == "https://venue.example/cal/all.ics"


def test_platform_endpoint_detected_from_markup():
    # WordPress "The Events Calendar" exposes a REST feed at a known path.
    html = '<html><body class="tribe-events-page"></body></html>'
    urls, _ = discover_feed_urls("https://venue.example/", html)
    assert any("/wp-json/tribe/events/v1/events" in u for u in urls)


def test_conventional_calendar_paths_are_offered():
    urls, _ = discover_feed_urls("https://venue.example/", "<html></html>")
    joined = " ".join(urls)
    for expected in ("/events", "/calendar", "ical=1"):
        assert expected in joined


def test_discovery_never_re_offers_the_base_url():
    urls, _ = discover_feed_urls("https://venue.example/", "<html></html>")
    assert "https://venue.example/" not in urls


def test_relative_links_are_absolutised_against_the_source():
    html = '<link rel="alternate" type="text/calendar" href="feed/events">'
    urls, _ = discover_feed_urls("https://venue.example/whats-on/", html)
    assert "https://venue.example/whats-on/feed/events" in urls


def test_malformed_html_does_not_break_discovery():
    urls, _ = discover_feed_urls("https://venue.example/", "<html><link rel=<<>")
    assert isinstance(urls, list) and urls  # still offers the conventions


def test_import_source_falls_back_to_a_discovered_feed(monkeypatch):
    """The behaviour that fixes the 16-of-18 zero-yield: base page has no events,
    so the discovered calendar subpath is fetched and parsed."""
    import worker.importers.structured_feed as sf
    base_html = ('<html><head><link rel="alternate" type="text/calendar" '
                 'href="/events.ics"></head><body>no events here</body></html>')
    ics = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:x1\r\nSUMMARY:Jazz Trio\r\n"
           "DTSTART:20261107T020000Z\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")

    def fake_fetch(u, timeout=30):
        return ics if u.endswith("/events.ics") else base_html

    monkeypatch.setattr(sf, "fetch_url", fake_fetch)
    out = sf.import_source("https://venue.example/", source_name="venue",
                           cultural_domain="live-music")
    assert len(out) == 1 and out[0]["title"] == "Jazz Trio"
    assert out[0]["category"] == "live-music"


def test_a_dead_candidate_does_not_lose_a_later_one(monkeypatch):
    import worker.importers.structured_feed as sf
    ics = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:x2\r\nSUMMARY:Late Show\r\n"
           "DTSTART:20261107T020000Z\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")

    def fake_fetch(u, timeout=30):
        if u.rstrip("/") == "https://venue.example":
            return "<html>nothing</html>"
        if "ical=1" in u or u.endswith(".ics"):
            raise OSError("dead endpoint")
        if u.endswith("/events/feed/"):
            return ics
        return "<html>nothing</html>"

    monkeypatch.setattr(sf, "fetch_url", fake_fetch)
    out = sf.import_source("https://venue.example/", source_name="venue")
    assert len(out) == 1 and out[0]["title"] == "Late Show"


# ---- platform JSON APIs (evaluator blocker, PR #68) ---------------------------
# The endpoints were previously ADVERTISED as canonical acquisition paths while
# import_source only routed bodies to ICS/JSON-LD — so Tribe/Localist responses
# would have yielded zero while looking like coverage. These tests parse the real
# response SHAPES into events, which is the behaviour the discovery layer claims.

# A REAL Tribe payload carries BOTH the site-local wall time and the UTC variant
# (plus the event's timezone). The earlier fixture omitted the UTC fields and the
# test asserted the local time as 'Z' — canonizing a wrong-event-time bug rather
# than catching it (evaluator blocker r2, PR #68).
TRIBE_JSON = """{"events":[
 {"id":991,"title":"Wednesday Residency","url":"https://venue.example/e/991",
  "start_date":"2026-11-07 20:00:00","end_date":"2026-11-07 23:00:00",
  "utc_start_date":"2026-11-08 02:00:00","utc_end_date":"2026-11-08 05:00:00",
  "timezone":"America/Chicago",
  "venue":{"venue":"The Back Room","address":"1 Main St","city":"Austin"}}
]}"""

LOCALIST_JSON = """{"events":[
 {"event":{"id":7,"title":"Lecture: Future of Cities",
   "localist_url":"https://cal.example/event/7",
   "location_name":"Hogg Auditorium",
   "event_instances":[{"event_instance":{"start":"2026-11-07T18:00:00-06:00"}}]}}
]}"""


def test_tribe_json_parses_into_events():
    from worker.importers.structured_feed import parse_platform_json
    rows = parse_platform_json(TRIBE_JSON)
    assert len(rows) == 1
    e = rows[0]
    assert e["title"] == "Wednesday Residency"
    # 20:00 America/Chicago (CST, UTC-6 in November) == 02:00Z next day. The UTC
    # field is preferred; the local field must NEVER be stamped 'Z'.
    assert e["start_time"] == "2026-11-08T02:00:00Z"
    assert e["venue_name"] == "The Back Room"
    assert e["venue_city"] == "Austin"


def test_localist_json_parses_its_nested_shape():
    from worker.importers.structured_feed import parse_platform_json
    rows = parse_platform_json(LOCALIST_JSON)
    assert len(rows) == 1
    e = rows[0]
    assert e["title"] == "Lecture: Future of Cities"
    assert e["start_time"] == "2026-11-08T00:00:00Z"   # -06:00 -> UTC
    assert e["venue_name"] == "Hogg Auditorium"


def test_platform_json_drops_entries_with_no_title_or_start():
    from worker.importers.structured_feed import parse_platform_json
    rows = parse_platform_json('{"events":[{"id":1},{"id":2,"title":"No start"}]}')
    assert rows == []   # never fabricated


def test_non_event_json_yields_nothing_not_a_guess():
    from worker.importers.structured_feed import parse_platform_json
    assert parse_platform_json('{"items":[{"title":"x"}]}') == []
    assert parse_platform_json("not json") == []


def test_a_platform_endpoint_is_fetched_and_parsed_end_to_end(monkeypatch):
    """The behaviour blocker #3/#4 said was missing: a Tribe endpoint discovered
    from markup must actually become events, not just a URL in a list."""
    import worker.importers.structured_feed as sf
    base = '<html><body class="tribe-events-page">no inline events</body></html>'

    def fake_fetch(u, timeout=30):
        if "/wp-json/tribe/events/v1/events" in u:
            return TRIBE_JSON
        return base

    monkeypatch.setattr(sf, "fetch_url", fake_fetch)
    monkeypatch.setattr(sf, "_robots_allows", lambda u, ua="OneLiveBot": True)
    out = sf.import_source("https://venue.example/", source_name="venue",
                           cultural_domain="live-music")
    assert len(out) == 1
    assert out[0]["title"] == "Wednesday Residency"
    # Own provider token (migration 0014) — NOT conflated with jsonld, so a shape
    # drift in the Tribe reader stays attributable.
    assert out[0]["source_provider"] == "platform_json"


def test_429_is_not_retried_with_a_browser_ua(monkeypatch):
    """Rate-limiting must stay visible — swapping headers past a 429 would be a
    rate-limit bypass (evaluator blocker, PR #68)."""
    import urllib.error
    import worker.importers.structured_feed as sf
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(req.get_header("User-agent"))
        raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(sf.urllib.request, "urlopen", fake_urlopen)
    try:
        sf.fetch_url("https://venue.example/events")
        raise AssertionError("429 should propagate")
    except urllib.error.HTTPError as exc:
        assert exc.code == 429
    assert len(calls) == 1, "429 must NOT trigger a second attempt"


def test_403_is_NOT_bypassed_with_a_different_identity(monkeypatch):
    """A 403 is the site REFUSING us. Retrying under a browser profile to get the
    content anyway would hide an access denial as a successful import — the repo
    bar is fail-closed on access, no bypasses (evaluator blocker r3, PR #68)."""
    import urllib.error
    import worker.importers.structured_feed as sf
    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(req.get_header("User-agent"))
        raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(sf.urllib.request, "urlopen", fake_urlopen)
    try:
        sf.fetch_url("https://venue.example/events")
        raise AssertionError("403 must propagate, not be bypassed")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403
    assert len(calls) == 1, "403 must NOT trigger a second attempt"
    assert "Mozilla" not in (calls[0] or ""), "must not masquerade as a browser"


def test_robots_disallow_blocks_a_guessed_candidate(monkeypatch):
    """The claim "robots is honoured" is now backed by code (evaluator nit)."""
    import worker.importers.structured_feed as sf
    sf._ROBOTS_CACHE.clear()
    fetched = []

    def fake_fetch(u, timeout=30):
        fetched.append(u)
        return "<html>nothing</html>"

    monkeypatch.setattr(sf, "fetch_url", fake_fetch)
    # Base allowed, every DISCOVERED candidate disallowed — so the base is read
    # and no guessed path is probed. (Robots blocking the base itself is covered
    # by test_robots_disallow_blocks_the_BASE_url_too.)
    monkeypatch.setattr(sf, "_robots_allows",
                        lambda u, ua="OneLiveBot": u.rstrip("/") == "https://venue.example")
    out = sf.import_source("https://venue.example/", source_name="venue")
    assert out == []
    assert fetched == ["https://venue.example/"]  # base only; no candidate probed


# ---- evaluator round 2: time correctness, 429, robots, bare JSON-LD ----------

def test_local_start_without_utc_is_converted_via_the_events_timezone():
    from worker.importers.structured_feed import parse_platform_json
    rows = parse_platform_json(
        '{"events":[{"id":1,"title":"Local Only","start_date":"2026-11-07 20:00:00",'
        '"timezone":"America/Chicago"}]}')
    assert rows[0]["start_time"] == "2026-11-08T02:00:00Z"   # same instant as UTC field


def test_local_start_with_NO_timezone_is_dropped_not_guessed():
    """A confidently wrong start time is worse than a missing event."""
    from worker.importers.structured_feed import parse_platform_json
    rows = parse_platform_json(
        '{"events":[{"id":1,"title":"No TZ","start_date":"2026-11-07 20:00:00"}]}')
    assert rows == []


def test_bare_jsonld_feed_is_parsed_not_dropped():
    """Discovery accepts application/ld+json links, which serve RAW json — those
    must not be routed to the platform parser and silently lost."""
    from worker.importers.structured_feed import parse_jsonld_document
    rows = parse_jsonld_document(
        '{"@context":"https://schema.org","@type":"MusicEvent","name":"Bare Feed Show",'
        '"startDate":"2026-11-07T20:00:00-06:00"}')
    assert len(rows) == 1 and rows[0]["title"] == "Bare Feed Show"
    assert rows[0]["start_time"] == "2026-11-08T02:00:00Z"


def test_a_429_PROPAGATES_rather_than_becoming_an_empty_source(monkeypatch):
    """A rate-limit is an ACCESS FAILURE, not 'no events'. Returning [] would let
    CI record a cheerfully dry source while the host explicitly throttled us
    (evaluator blocker r4, PR #68). The runner catches this as FETCH FAILED."""
    import urllib.error
    import worker.importers.structured_feed as sf
    tried = []

    def fake_fetch(u, timeout=30):
        tried.append(u)
        if u.rstrip("/") == "https://venue.example":
            return "<html>nothing</html>"
        raise urllib.error.HTTPError(u, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(sf, "fetch_url", fake_fetch)
    monkeypatch.setattr(sf, "_robots_allows", lambda u, ua="OneLiveBot": True)
    try:
        sf.import_source("https://venue.example/", source_name="venue")
        raise AssertionError("429 must propagate, not return an empty list")
    except urllib.error.HTTPError as exc:
        assert exc.code == 429
    # base + exactly ONE candidate: the 429 ended probing immediately.
    assert len(tried) == 2, f"kept probing after a 429: {tried}"


def test_a_403_on_a_candidate_also_propagates(monkeypatch):
    """Access denials must fail closed too — not be downgraded to 'candidate did
    not serve a feed' while we keep probing (evaluator blocker r4)."""
    import urllib.error
    import worker.importers.structured_feed as sf

    def fake_fetch(u, timeout=30):
        if u.rstrip("/") == "https://venue.example":
            return "<html>nothing</html>"
        raise urllib.error.HTTPError(u, 403, "Forbidden", {}, None)

    monkeypatch.setattr(sf, "fetch_url", fake_fetch)
    monkeypatch.setattr(sf, "_robots_allows", lambda u, ua="OneLiveBot": True)
    try:
        sf.import_source("https://venue.example/", source_name="venue")
        raise AssertionError("403 must propagate")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403


def test_a_404_on_a_guessed_path_is_still_an_expected_miss(monkeypatch):
    """Not every status is an access failure — a guessed path that simply does
    not exist must keep the discovery loop going."""
    import urllib.error
    import worker.importers.structured_feed as sf
    ics = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:z\r\nSUMMARY:Found Later\r\n"
           "DTSTART:20261107T020000Z\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")

    def fake_fetch(u, timeout=30):
        if u.rstrip("/") == "https://venue.example":
            return "<html>nothing</html>"
        if u.endswith("/events/feed/"):
            return ics
        raise urllib.error.HTTPError(u, 404, "Not Found", {}, None)

    monkeypatch.setattr(sf, "fetch_url", fake_fetch)
    monkeypatch.setattr(sf, "_robots_allows", lambda u, ua="OneLiveBot": True)
    out = sf.import_source("https://venue.example/", source_name="venue")
    assert len(out) == 1 and out[0]["title"] == "Found Later"


def test_occurrence_without_an_instance_id_does_not_collide():
    """A series whose platform omits per-instance ids must still keep one row per
    showing, not collapse onto the parent id (evaluator nit r4)."""
    from worker.importers.structured_feed import parse_platform_json
    doc = ('{"events":[{"event":{"id":9,"title":"No Instance Ids",'
           '"event_instances":['
           '{"event_instance":{"start":"2026-11-07T18:00:00-06:00"}},'
           '{"event_instance":{"start":"2026-11-14T18:00:00-06:00"}}]}}]}')
    rows = parse_platform_json(doc)
    assert len(rows) == 2
    assert rows[0]["uid"] != rows[1]["uid"], "occurrences collapsed onto one id"


def test_robots_disallow_blocks_the_BASE_url_too(monkeypatch):
    """The first path reached must also respect robots (evaluator blocker r2)."""
    import worker.importers.structured_feed as sf
    tried = []
    monkeypatch.setattr(sf, "fetch_url", lambda u, timeout=30: tried.append(u) or "<html/>")
    monkeypatch.setattr(sf, "_robots_allows", lambda u, ua="OneLiveBot": False)
    assert sf.import_source("https://venue.example/", source_name="venue") == []
    assert tried == [], "base URL was fetched despite a robots Disallow"


def test_declared_and_guessed_candidates_have_separate_budgets():
    """Many declared alternates must not starve the conventional paths."""
    from worker.importers.structured_feed import discover_feed_urls
    html = "".join(
        f'<link rel="alternate" type="text/calendar" href="/d{i}.ics">' for i in range(10))
    urls, declared = discover_feed_urls("https://venue.example/", html)
    assert declared == 10
    # Conventional paths are still present in the full candidate list.
    assert any("ical=1" in u or u.endswith("/events") for u in urls)


def test_all_localist_occurrences_are_emitted_not_just_the_first():
    """Localist events carry N concrete occurrences; reading only [0] silently
    discarded every later showing (evaluator blocker r3, PR #68)."""
    from worker.importers.structured_feed import parse_platform_json
    doc = ('{"events":[{"event":{"id":7,"title":"Weekly Series",'
           '"location_name":"Hall","event_instances":['
           '{"event_instance":{"id":71,"start":"2026-11-07T18:00:00-06:00"}},'
           '{"event_instance":{"id":72,"start":"2026-11-14T18:00:00-06:00"}},'
           '{"event_instance":{"id":73,"start":"2026-11-21T18:00:00-06:00"}}]}}]}')
    rows = parse_platform_json(doc)
    assert len(rows) == 3, "later occurrences were dropped"
    # Each occurrence needs a DISTINCT id or they collide on upsert, re-losing them.
    assert [r["uid"] for r in rows] == ["71", "72", "73"]
    assert [r["start_time"] for r in rows] == [
        "2026-11-08T00:00:00Z", "2026-11-15T00:00:00Z", "2026-11-22T00:00:00Z"]


def test_unsupported_declared_feed_types_are_not_offered_as_candidates():
    """RSS/Atom were accepted with no parser behind them — a declared RSS feed
    would fetch, parse to zero, and read as 'no events' (evaluator blocker r3)."""
    from worker.importers.structured_feed import discover_feed_urls
    html = '<link rel="alternate" type="application/rss+xml" href="/feed.rss">'
    urls, declared = discover_feed_urls("https://venue.example/", html)
    assert declared == 0, "an unparseable RSS feed must not count as declared"
    assert not any("feed.rss" in u for u in urls)


def test_platform_json_keeps_its_own_provider_token():
    from worker.importers.structured_feed import _events_from_text
    rows = _events_from_text(
        '{"events":[{"id":1,"title":"T","utc_start_date":"2026-11-08 02:00:00"}]}',
        provider_hint=None, source_name="s", cultural_domain=None)
    assert rows[0]["source_provider"] == "platform_json"


def test_bare_jsonld_fallback_is_recorded_as_jsonld_not_platform():
    from worker.importers.structured_feed import _events_from_text
    rows = _events_from_text(
        '{"@type":"MusicEvent","name":"B","startDate":"2026-11-07T20:00:00-06:00"}',
        provider_hint=None, source_name="s", cultural_domain=None)
    assert rows[0]["source_provider"] == "jsonld"
