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
<meta itemprop="name" content="Night Owls Live"/>
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
                        lambda url, timeout=15, candidate_title=None: recovered)
    from datetime import datetime, timezone
    block_text = "Night Owls Live 7:00 PM tickets: " + (
        fields.get("ticket_link") or "")
    ai_extract._shape_and_store_one(
        fields, {"_provenance": {"model": "test"}},
        source_id=None, source_name="Test Source",
        source_url="https://src.example", source_class="venue_calendar",
        text=block_text, sxsw_mode=False,
        fetched_at=datetime.now(timezone.utc))
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
    # Pin the WHOLE value, year included, at this integration seam
    # (evaluator nit, PR #189 r1) — computed through the same resolver so
    # the test is honest across real clock dates including year boundaries.
    from datetime import datetime, timezone
    from worker.datetime_normalize import resolve_yearless_claim
    expected, _ = resolve_yearless_claim("August 9 6:00 PM",
                                         datetime.now(timezone.utc))
    assert ex["start_time"] == expected and expected.endswith("T18:00:00")
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



def test_callback_refused_when_link_absent_from_source_text(monkeypatch):
    # Evaluator finding (PR #189 r1): an AI-shaped link the source never
    # published must get NO callback — otherwise a hallucinated/injected
    # link could launder an attacker-chosen date into recovered evidence.
    stored = {}
    monkeypatch.setattr(ai_extract, "create_candidate",
                        lambda **kw: stored.update(kw) or "cand-1")
    monkeypatch.setattr(ai_extract, "add_evidence", lambda **kw: None)
    calls = []
    monkeypatch.setattr(ai_extract, "recover_dates_from_url",
                        lambda url, timeout=15, candidate_title=None:
                        calls.append(url) or
                        {"start_time": "2026-08-08T19:00:00"})
    ai_extract._shape_and_store_one(
        {"title": "Night Owls", "start_time": "7:00 PM",
         "ticket_link": "https://evil.example/other-event"},
        {"_provenance": {"model": "test"}},
        source_id=None, source_name="Test Source",
        source_url="https://src.example", source_class="venue_calendar",
        text="Night Owls Live 7:00 PM at the lounge", sxsw_mode=False)
    assert calls == []  # no fetch of an unquoted link, ever
    assert stored["extracted"]["start_time"] is None


def test_callback_fetch_refuses_private_and_loopback_hosts():
    # Evaluator nit (PR #189 r1): the callback must never probe internal
    # address space, whatever a page claims its "ticket link" is.
    from worker.date_callback import _fetch
    assert _fetch("http://169.254.169.254/latest/meta-data") is None
    assert _fetch("http://127.0.0.1:8080/x") is None
    assert _fetch("http://localhost/x") is None
    assert _fetch("http://10.0.0.7/x") is None


def test_date_mention_lines_are_not_adopted_as_context():
    # Evaluator finding (PR #189 r1): "Updated August 5" is a date MENTION,
    # not a day header — adopting it would stamp wrong dates onto blocks.
    from worker.segment import segment_events
    html = """
    <html><body>
    <p>Updated August 5</p>
    <ul>
    <li class="event-card">Open Mic Night, 8:00 PM signup at the bar</li>
    <li class="event-card">Trivia Showdown, 7:00 PM weekly prizes</li>
    </ul>
    </body></html>"""
    blocks = segment_events(html, content_type="text/html")
    assert all(not b.startswith("Updated August 5") for b in blocks)



def test_year_rule_fails_closed_without_fetch_time(monkeypatch):
    # Evaluator finding (PR #189 r2): without a source-fetch reference the
    # resolver must refuse — replay/backfill must never re-date a claim off
    # this worker's clock.
    from worker.datetime_normalize import resolve_yearless_claim

    assert resolve_yearless_claim("August 9 6:00 PM", None) == (None, None)

    stored = {}
    monkeypatch.setattr(ai_extract, "create_candidate",
                        lambda **kw: stored.update(kw) or "cand-1")
    monkeypatch.setattr(ai_extract, "add_evidence", lambda **kw: None)
    monkeypatch.setattr(ai_extract, "recover_dates_from_url",
                        lambda url, timeout=15, candidate_title=None: {})
    ai_extract._shape_and_store_one(
        {"title": "Songwriter Round", "start_time": "August 9 6:00 PM"},
        {"_provenance": {"model": "test"}},
        source_id=None, source_name="Test Source",
        source_url="https://src.example", source_class="venue_calendar",
        text="Songwriter Round August 9 6:00 PM", sxsw_mode=False)
    assert stored["extracted"]["start_time"] is None  # no fetched_at: refused



def test_stale_date_context_cleared_by_section_boundary():
    # Evaluator finding (PR #189 r2): a later, unrelated section must not
    # inherit a stale day header — dateless beats wrongly dated.
    from worker.segment import segment_events

    html = """
    <html><body>
    <h2>Tuesday, August 5</h2>
    <ul>
    <li class="event-card">Discovery Day, 10:00 AM - 4:00 PM</li>
    <li class="event-card">Star Party, 7:30 PM - 9:00 PM</li>
    </ul>
    <h2>Ongoing exhibits</h2>
    <ul>
    <li class="event-card">Night Lab drop-in, 6:00 PM Thursdays</li>
    <li class="event-card">Maker hours, 5:00 PM weekdays</li>
    </ul>
    </body></html>"""
    blocks = segment_events(html, content_type="text/html")
    assert blocks[0].startswith("Tuesday, August 5\n")
    assert blocks[1].startswith("Tuesday, August 5\n")
    assert not blocks[2].startswith("Tuesday, August 5")
    assert not blocks[3].startswith("Tuesday, August 5")

    text = (
        "Saturday, August 8\n"
        "7:00 PM Doors - Night Owls on the patio\n"
        "Ongoing exhibits and standing programs\n"
        "6:00 PM Night Lab drop-in\n"
    )
    tblocks = segment_events(text)
    lab = [b for b in tblocks if "Night Lab" in b]
    assert lab and not lab[0].startswith("Saturday, August 8")


def test_link_token_guard_refuses_prefix_of_longer_url():
    # Evaluator blocker (PR #189 r3): substring matching accepted an
    # extracted ".../e/1" when the source only published ".../e/123" —
    # a hallucinated prefix-link could fetch an unrelated page. The link
    # must occur as a COMPLETE URL token.
    from worker.ai_extract import _link_source_quoted

    text = "Night Owls Live 7pm tickets: https://venue.example/e/123 tonight"
    assert not _link_source_quoted("https://venue.example/e/1", text)
    assert not _link_source_quoted("https://venue.example/e/12", text)
    assert _link_source_quoted("https://venue.example/e/123", text)
    # End-of-text and quoted forms are complete tokens.
    assert _link_source_quoted("https://v.example/x", "buy: https://v.example/x")
    assert _link_source_quoted("https://v.example/x", 'href="https://v.example/x"')
    # A URL-character neighbour on either side means a DIFFERENT URL:
    # fail closed (sentence punctuation like a trailing "." included —
    # "." legitimately continues URLs, e.g. ".html").
    assert not _link_source_quoted("https://v.example/x", "https://v.example/x.html")
    assert not _link_source_quoted("v.example/x", "https://v.example/x ")


def test_shaping_refuses_prefix_substring_link(monkeypatch):
    # The r3 laundering shape end-to-end: extracted link is a prefix of the
    # source's real URL — no callback fires, the claim stays refused.
    stored = {}
    monkeypatch.setattr(ai_extract, "create_candidate",
                        lambda **kw: stored.update(kw) or "cand-1")
    monkeypatch.setattr(ai_extract, "add_evidence", lambda **kw: None)
    calls = []
    monkeypatch.setattr(ai_extract, "recover_dates_from_url",
                        lambda url, timeout=15, candidate_title=None:
                        calls.append(url) or
                        {"start_time": "2026-08-08T19:00:00"})
    from datetime import datetime, timezone
    ai_extract._shape_and_store_one(
        {"title": "Night Owls", "start_time": "7:00 PM",
         "ticket_link": "https://venue.example/e/1"},
        {"_provenance": {"model": "test"}},
        source_id=None, source_name="Test Source",
        source_url="https://src.example", source_class="venue_calendar",
        text="Night Owls 7:00 PM tickets: https://venue.example/e/123",
        sxsw_mode=False, fetched_at=datetime.now(timezone.utc))
    assert calls == []
    assert stored["extracted"]["start_time"] is None


def test_microdata_outside_event_scope_yields_nothing(monkeypatch):
    # Evaluator blocker (PR #189 r3): a microdata startDate that is NOT
    # inside a schema.org Event itemscope (e.g. a WebPage's dateModified-ish
    # markup) must never donate a date.
    html = """
    <html><body itemscope itemtype="https://schema.org/WebPage">
    <meta itemprop="startDate" content="2026-08-10T18:00:00"/>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: html)
    assert recover_dates_from_url("https://venue.example/page") == {}

    bare = """
    <html><body>
    <meta itemprop="startDate" content="2026-08-10T18:00:00"/>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: bare)
    assert recover_dates_from_url("https://venue.example/page") == {}


def test_microdata_two_event_scopes_yield_nothing(monkeypatch):
    html = """
    <html><body>
    <div itemscope itemtype="https://schema.org/Event">
      <meta itemprop="startDate" content="2026-08-10T18:00:00"/>
    </div>
    <div itemscope itemtype="https://schema.org/Event">
      <meta itemprop="startDate" content="2026-08-11T20:00:00"/>
    </div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: html)
    assert recover_dates_from_url("https://venue.example/cal") == {}



def test_year_rule_weekday_consistency():
    # Evaluator blocker (PR #189 r3): a claim that NAMES a weekday must only
    # resolve to a year where the month/day IS that weekday. Aug 8 was a
    # Friday in 2025 and a Saturday in 2026.
    from datetime import datetime, timezone
    from worker.datetime_normalize import resolve_yearless_claim

    ref_2025 = datetime(2025, 7, 1, tzinfo=timezone.utc)
    iso, note = resolve_yearless_claim("Friday, August 8 7:00 PM", ref_2025)
    assert iso is not None and iso.startswith("2025-08-08")
    assert note["weekday_verified"].lower() == "friday"

    ref_2026 = datetime(2026, 7, 1, tzinfo=timezone.utc)
    assert resolve_yearless_claim("Friday, August 8 7:00 PM", ref_2026) == (None, None)
    iso, note = resolve_yearless_claim("Saturday, August 8 7:00 PM", ref_2026)
    assert iso is not None and iso.startswith("2026-08-08")

    # No weekday named: unchanged behavior, no weekday key in the note.
    iso, note = resolve_yearless_claim("August 8 7:00 PM", ref_2026)
    assert iso is not None and "weekday_verified" not in note



def test_microdata_dated_plus_undated_events_yield_nothing(monkeypatch):
    # Evaluator blocker (PR #189 r4): cardinality is over ALL Event scopes.
    # One dated + one undated Event is still a multi-event page —
    # attributing the dated one to the candidate would be a guess.
    html = """
    <html><body>
    <div itemscope itemtype="https://schema.org/Event">
      <meta itemprop="startDate" content="2026-08-10T18:00:00"/>
    </div>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Another Show, date TBA</span>
    </div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: html)
    assert recover_dates_from_url("https://venue.example/cal") == {}


def test_fetch_refuses_pages_larger_than_the_cap(monkeypatch):
    # Evaluator blocker (PR #189 r4): a page larger than the byte cap must
    # be REFUSED, never parsed as a truncated prefix — the prefix could
    # declare exactly one Event while the real document declares more.
    from worker.date_callback import _MAX_BYTES, _fetch

    class _FakeResp:
        def __init__(self, size):
            self._data = b"x" * size

        def read(self, n):
            return self._data[:n]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def opener_for(size):
        class _Opener:
            def open(self, req, timeout=15):
                return _FakeResp(size)
        return lambda *handlers: _Opener()

    monkeypatch.setattr(date_callback, "build_opener",
                        opener_for(_MAX_BYTES + 10))
    assert _fetch("https://venue.example/huge") is None

    monkeypatch.setattr(date_callback, "build_opener",
                        opener_for(_MAX_BYTES - 10))
    assert _fetch("https://venue.example/ok") is not None




def test_mixed_format_multi_event_page_refused(monkeypatch):
    # Evaluator blocker (PR #189 r6): one JSON-LD Event plus MULTIPLE
    # microdata Events is still a multi-event page — cardinality holds
    # across formats, and nothing is attributed.
    mixed = """
    <html><script type="application/ld+json">
    {"@type": "Event", "name": "Night Owls Live",
     "startDate": "2026-08-08T19:00:00"}
    </script>
    <body>
    <div itemscope itemtype="https://schema.org/Event">
      <meta itemprop="startDate" content="2026-08-09T20:00:00"/>
    </div>
    <div itemscope itemtype="https://schema.org/Event">
      <meta itemprop="startDate" content="2026-08-10T21:00:00"/>
    </div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: mixed)
    assert recover_dates_from_url("https://venue.example/cal") == {}





def test_source_page_declarations_are_authoritative(monkeypatch):
    # Founder ruling 2026-08-05 (decision record
    # 2026-08-05_source-site-authoritative.md): once the link is proven to
    # be the source's own, the page's declarations are AUTHORITATIVE — a
    # nameless Event or a name differing from the extracted title recovers
    # its date all the same; there is no identity cross-examination.
    nameless = """
    <html><body itemscope itemtype="https://schema.org/Event">
    <meta itemprop="startDate" content="2026-08-10T18:00:00"/>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: nameless)
    assert recover_dates_from_url("https://venue.example/page") == \
        {"start_time": "2026-08-10T18:00:00"}


def test_jsonld_precedence_when_formats_disagree(monkeypatch):
    # One Event in each format with differing values: the source is
    # authoritative and JSON-LD (the richer declaration) simply wins —
    # never a refusal (founder ruling 2026-08-05).
    page = """
    <html><script type="application/ld+json">
    {"@type": "Event", "name": "Night Owls Live",
     "startDate": "2026-08-08T19:00:00"}
    </script>
    <body><div itemscope itemtype="https://schema.org/Event">
      <meta itemprop="startDate" content="2026-08-09T19:00:00"/>
    </div></body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)
    out = recover_dates_from_url("https://venue.example/e/1")
    assert out["start_time"] == "2026-08-08T19:00:00"
