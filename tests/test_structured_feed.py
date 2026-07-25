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
    assert n["category"] == "theater"  # classify_from_title on "...at the Theater"
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
