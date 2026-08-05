"""Date recovery by callback (worker/date_callback.py) + its wiring into the
extraction shaping seam — founder-directed 2026-08-05 ("more of a call back
position than a logic process"). Locks in:

  - JSON-LD single-Event pages yield startDate/endDate raw strings; a page
    declaring MORE than one Event yields nothing (attribution would guess).
  - Microdata itemprop content attrs are read, one occurrence per field.
  - Any fetch failure returns {} — the callback can only add, never break.
  - In shaping: callback evidence outranks the year rule; both record their
    method + basis in candidate provenance; strict normalization still
    guards everything recovered.
"""
import worker.ai_extract as ai_extract
import worker.date_callback as date_callback
from worker.date_callback import recover_dates_from_url

_ONE_EVENT = """
<html><head><script type="application/ld+json">
{"@context": "https://schema.org", "@type": "MusicEvent",
 "name": "Night Owls Live", "startDate": "2026-08-08T19:00:00-05:00",
 "endDate": "2026-08-08T22:00:00-05:00"}
</script></head><body>Night Owls Live</body></html>
"""

_TWO_EVENTS = """
<html><script type="application/ld+json">
[{"@type": "Event", "name": "A", "startDate": "2026-08-08T19:00"},
 {"@type": "Event", "name": "B", "startDate": "2026-08-09T20:00"}]
</script></html>
"""

_MICRODATA = """
<html><body itemscope itemtype="https://schema.org/Event">
<meta itemprop="startDate" content="2026-08-10T18:00:00"/>
<span>Doors 6pm</span>
</body></html>
"""


def test_single_jsonld_event_dates_recovered(monkeypatch):
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: _ONE_EVENT)
    out = recover_dates_from_url("https://venue.example/e/1")
    assert out["start_time"] == "2026-08-08T19:00:00-05:00"
    assert out["end_time"] == "2026-08-08T22:00:00-05:00"


def test_multi_event_page_yields_nothing(monkeypatch):
    # >1 Event declared: attributing one to the candidate would be a guess.
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: _TWO_EVENTS)
    assert recover_dates_from_url("https://venue.example/cal") == {}


def test_microdata_content_attr_recovered(monkeypatch):
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: _MICRODATA)
    out = recover_dates_from_url("https://venue.example/e/2")
    assert out == {"start_time": "2026-08-10T18:00:00"}


def test_fetch_failure_returns_empty(monkeypatch):
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: None)
    assert recover_dates_from_url("https://venue.example/down") == {}


def test_non_http_scheme_refused():
    assert recover_dates_from_url("file:///etc/passwd") == {}
    assert recover_dates_from_url("javascript:alert(1)") == {}


def _shape(monkeypatch, fields, recovered):
    """Run _shape_and_store_one with store + callback faked; return stored row."""
    stored = {}

    def fake_create(**kwargs):
        stored.update(kwargs)
        return "cand-1"

    monkeypatch.setattr(ai_extract, "create_candidate", fake_create)
    monkeypatch.setattr(ai_extract, "add_evidence", lambda **kw: None)
    monkeypatch.setattr(ai_extract, "recover_dates_from_url",
                        lambda url, timeout=15: recovered)
    ai_extract._shape_and_store_one(
        fields, {"_provenance": {"model": "test"}},
        source_id=None, source_name="Test Source",
        source_url="https://src.example", source_class="venue_calendar",
        text="Night Owls Live 7:00 PM", sxsw_mode=False)
    return stored


def test_shaping_prefers_callback_evidence(monkeypatch):
    stored = _shape(
        monkeypatch,
        {"title": "Night Owls Live", "start_time": "7:00 PM",
         "ticket_link": "https://venue.example/e/1"},
        {"start_time": "2026-08-08T19:00:00"},
    )
    ex = stored["extracted"]
    assert ex["start_time"] == "2026-08-08T19:00:00"
    rec = ex["_provenance"]["datetime_recovery"]["start_time"]
    assert rec["method"] == "detail-page-callback"
    assert rec["source"] == "https://venue.example/e/1"


def test_shaping_falls_back_to_year_rule(monkeypatch):
    # Callback finds nothing; the claim is a full date minus the year — the
    # founder-ratified year rule resolves it, on the record.
    stored = _shape(
        monkeypatch,
        {"title": "Songwriter Round", "start_time": "August 9 6:00 PM",
         "ticket_link": "https://venue.example/e/9"},
        {},
    )
    ex = stored["extracted"]
    assert ex["start_time"] is not None and ex["start_time"].endswith("T18:00:00")
    rec = ex["_provenance"]["datetime_recovery"]["start_time"]
    assert rec["method"] == "year-from-fetch-date"
    assert rec["reference"]  # the basis is auditable


def test_shaping_time_only_without_link_stays_refused(monkeypatch):
    stored = _shape(
        monkeypatch,
        {"title": "Trivia Night", "start_time": "8:00 PM"},
        {},
    )
    ex = stored["extracted"]
    assert ex["start_time"] is None
    claims = ex["_provenance"]["unstored_datetime_claims"]
    assert claims["start_time"]["reason"] == "no-full-date-evidence"
    assert "datetime_recovery" not in ex["_provenance"]
