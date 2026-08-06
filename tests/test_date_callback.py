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
[{"@type": "Event", "name": "Night Owls Live", "startDate": "2026-08-08T19:00"},
 {"@type": "Event", "name": "Trivia Showdown", "startDate": "2026-08-09T20:00"}]
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
    out = recover_dates_from_url("https://venue.example/e/1", candidate_title="Night Owls Live")
    assert out["start_time"] == "2026-08-08T19:00:00-05:00"
    assert out["end_time"] == "2026-08-08T22:00:00-05:00"



def test_microdata_content_attr_recovered(monkeypatch):
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: _MICRODATA)
    out = recover_dates_from_url("https://venue.example/e/2", candidate_title="Night Owls Live")
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
    assert recover_dates_from_url("https://venue.example/page", candidate_title="Night Owls Live") == {}

    bare = """
    <html><body>
    <meta itemprop="startDate" content="2026-08-10T18:00:00"/>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: bare)
    assert recover_dates_from_url("https://venue.example/page", candidate_title="Night Owls Live") == {}



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
    assert recover_dates_from_url("https://venue.example/page", candidate_title="Night Owls Live") == \
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
    out = recover_dates_from_url("https://venue.example/e/1", candidate_title="Night Owls Live")
    assert out["start_time"] == "2026-08-08T19:00:00"

def test_multi_event_page_title_selects_the_match(monkeypatch):
    # Founder ruling 2026-08-05 (follow-up, verbatim in the decision
    # record): a page listing multiple events — a venue calendar — must
    # not be skipped. The candidate's title selects its match and takes
    # THAT event's date.
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: _TWO_EVENTS)
    out = recover_dates_from_url("https://venue.example/cal",
                                 candidate_title="Night Owls Live")
    assert out == {"start_time": "2026-08-08T19:00"}
    out = recover_dates_from_url("https://venue.example/cal",
                                 candidate_title="Trivia Showdown")
    assert out == {"start_time": "2026-08-09T20:00"}


def test_multi_event_page_without_a_unique_match_contributes_nothing(monkeypatch):
    # No title, no shared words, or a tie: the page stays unattributable
    # and the claim just stays as-is — never a wrong event's date.
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: _TWO_EVENTS)
    assert recover_dates_from_url("https://venue.example/cal") == {}
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Completely Unrelated") == {}


def test_multi_event_microdata_calendar_selects_by_name(monkeypatch):
    cal = """
    <html><body>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Night Owls Live</span>
      <meta itemprop="startDate" content="2026-08-10T18:00:00"/>
    </div>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Trivia Showdown</span>
      <meta itemprop="startDate" content="2026-08-11T19:00:00"/>
    </div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: cal)
    out = recover_dates_from_url("https://venue.example/cal",
                                 candidate_title="Trivia Showdown")
    assert out == {"start_time": "2026-08-11T19:00:00"}

def test_multi_event_selection_ignores_generic_words(monkeypatch):
    # Evaluator blocker (PR #189, multi-event attribution): "Kids Night" and
    # "Trivia Night" share only the generic word "night" — selecting on that
    # would assign the WRONG event's date. Generic event words carry no
    # identifying signal and are dropped from both sides before scoring.
    cal = """
    <html><script type="application/ld+json">
    [{"@type": "Event", "name": "Trivia Night", "startDate": "2026-08-08T19:00"},
     {"@type": "Event", "name": "Karaoke Night", "startDate": "2026-08-09T20:00"}]
    </script></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: cal)
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Kids Night") == {}
    # A distinctive word still selects cleanly.
    out = recover_dates_from_url("https://venue.example/cal",
                                 candidate_title="Karaoke Night")
    assert out == {"start_time": "2026-08-09T20:00"}

def test_generic_words_are_stripped_of_punctuation(monkeypatch):
    # Adversarial pre-review catch (2026-08-05): a bare split leaves "Night:"
    # as its own token, which is NOT in the generic set and would score like
    # a distinctive word — defeating the generic-word filter entirely.
    from worker.date_callback import _title_tokens

    assert _title_tokens("Trivia Night:") == {"trivia"}
    assert _title_tokens("Kids' Night!") == {"kids"}
    assert _title_tokens("(Live) — Music.") == set()

    cal = """
    <html><script type="application/ld+json">
    [{"@type": "Event", "name": "Trivia Night:", "startDate": "2026-08-08T19:00"},
     {"@type": "Event", "name": "Karaoke Night!", "startDate": "2026-08-09T20:00"}]
    </script></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: cal)
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Kids Night") == {}

def test_cross_format_cardinality_blocks_the_wrong_event(monkeypatch):
    # Adversarial pre-review BLOCKER (2026-08-05), reproduced end-to-end:
    # counting Events per FORMAT let a page with two JSON-LD Events plus one
    # microdata Event refuse the JSON-LD pass, then hand over the lone
    # microdata Event's date UNMATCHED — an August 6 PM show stored as
    # Dec 31, 9 PM. Cardinality is now measured over the whole page.
    page = """
    <html><script type="application/ld+json">
    [{"@type": "Event", "name": "Trivia Night", "startDate": "2026-08-08T19:00"},
     {"@type": "Event", "name": "Karaoke Night", "startDate": "2026-08-09T20:00"}]
    </script>
    <body><div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">New Year's Eve Bash</span>
      <meta itemprop="startDate" content="2026-12-31T21:00:00"/>
    </div></body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Kids Night") == {}
    # The mirror: one JSON-LD "featured" Event beside a microdata calendar.
    mirror = """
    <html><script type="application/ld+json">
    {"@type": "Event", "name": "Featured Show", "startDate": "2027-03-01T20:00"}
    </script>
    <body>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Bluegrass Junction</span>
      <meta itemprop="startDate" content="2026-08-08T19:00:00"/></div>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Sinatra Tribute</span>
      <meta itemprop="startDate" content="2026-08-09T19:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: mirror)
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Kids Night") == {}
    # …and the right event is still selectable on that same page.
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Bluegrass Junction") == \
        {"start_time": "2026-08-08T19:00:00"}


def test_no_impossible_start_end_splice(monkeypatch):
    # The same per-format bug could splice one event's start onto another's
    # end — an end_time four months BEFORE the start. One event set means
    # start and end always come from the same declaration.
    page = """
    <html><script type="application/ld+json">
    {"@type": "Event", "name": "Night Owls Live", "endDate": "2026-12-31T23:00"}
    </script>
    <body><div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Totally Different Gala</span>
      <meta itemprop="startDate" content="2026-08-09T19:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)
    out = recover_dates_from_url("https://venue.example/cal",
                                 candidate_title="Night Owls Live")
    assert "start_time" not in out  # never another event's start


def test_every_schema_event_subtype_is_recognized(monkeypatch):
    # Adversarial pre-review BLOCKER: a hardcoded six-subtype list made a
    # cinema's ScreeningEvent calendar look like a ONE-event page (wrong
    # date handed over) AND suppressed legitimate recovery on
    # SportsEvent/ExhibitionEvent/ChildrensEvent/FoodEvent/LiteraryEvent…
    from worker.date_callback import _is_event_itemtype

    for t in ("https://schema.org/ScreeningEvent", "https://schema.org/SportsEvent",
              "https://schema.org/ExhibitionEvent", "https://schema.org/ChildrensEvent",
              "https://schema.org/FoodEvent", "https://schema.org/SocialEvent",
              "https://schema.org/LiteraryEvent", "https://schema.org/EducationEvent",
              "https://schema.org/BusinessEvent", "http://schema.org/MusicEvent",
              "https://schema.org/Festival", "Event"):
        assert _is_event_itemtype(t), t
    for t in ("https://schema.org/Place", "https://schema.org/Organization",
              "https://schema.org/Movie", ""):
        assert not _is_event_itemtype(t), t

    cinema = """
    <html><body>
    <div itemscope itemtype="https://schema.org/ScreeningEvent">
      <span itemprop="name">Dune Part Three</span>
      <meta itemprop="startDate" content="2026-08-08T19:00:00"/></div>
    <div itemscope itemtype="https://schema.org/ScreeningEvent">
      <span itemprop="name">The Long Goodbye 35mm</span>
      <meta itemprop="startDate" content="2026-08-10T21:00:00"/></div>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Members Preview Party</span>
      <meta itemprop="startDate" content="2026-09-01T18:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: cinema)
    # The screenings are now VISIBLE, so the page is correctly multi-event…
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Kids Night") == {}
    # …and a real screening is recoverable, which the old whitelist blocked.
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Dune Part Three") == \
        {"start_time": "2026-08-08T19:00:00"}


def test_jsonld_festival_is_not_invisible_to_the_jsonld_path(monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05, seats openai/attacker-smuggle +
    openai/absence-only): the JSON-LD reader accepted only @type names ending
    in "event", so a schema.org Festival was invisible to it while the
    microdata reader saw Festival fine. A page declaring the candidate as a
    JSON-LD Festival plus an unrelated microdata Event therefore looked
    SINGLE-event — and the single-event shortcut is authoritative, so the
    unrelated event's date was recovered and published for the festival.
    """
    page = """
    <html><head><script type="application/ld+json">
    {"@type": "Festival", "name": "Blanton Block Party",
     "startDate": "2026-08-15T18:00:00"}
    </script></head><body>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Curator Talk: Impressionism</span>
      <meta itemprop="startDate" content="2026-11-02T14:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)

    # The festival is visible, so this is a TWO-event page: the unrelated
    # curator talk can no longer be handed over as the only declaration.
    assert recover_dates_from_url(
        "https://museum.example/whats-on",
        candidate_title="Blanton Block Party") == {
            "start_time": "2026-08-15T18:00:00"}
    # And an unmatchable title recovers nothing rather than guessing.
    assert recover_dates_from_url("https://museum.example/whats-on",
                                  candidate_title="Members Mixer") == {}

    from worker.date_callback import _is_event_itemtype
    for t in ("Festival", "https://schema.org/Festival", "MusicFestival",
              "https://schema.org/FoodFestival"):
        assert _is_event_itemtype(t), t


def test_unnamed_declaration_never_overrides_a_named_one_it_contradicts(
        monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05): _dedupe_declarations merged
    EVERY unnamed declaration into the page's single named one regardless of
    dates, and _merge lets JSON-LD win — so a named microdata candidate plus
    an unrelated NAMELESS JSON-LD event published the nameless event's date as
    the candidate's own source-authoritative date.
    """
    page = """
    <html><head><script type="application/ld+json">
    {"@type": "Event", "startDate": "2027-03-14T09:00:00",
     "endDate": "2027-03-14T17:00:00"}
    </script></head><body>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Cactus Cafe: Slaid Cleaves</span>
      <meta itemprop="startDate" content="2026-08-09T20:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)

    got = recover_dates_from_url("https://venue.example/e/slaid",
                                 candidate_title="Cactus Cafe: Slaid Cleaves")
    assert got == {"start_time": "2026-08-09T20:00:00"}, (
        "the nameless JSON-LD event's 2027 date must not become this "
        f"candidate's date; got {got}")
    assert "2027" not in str(got)


def test_unnamed_repeat_of_the_same_event_still_merges(monkeypatch):
    """The case the contradiction check must NOT break: one event marked in
    JSON-LD and repeated in bare microdata is ONE event, and the page still
    recovers. (Attribution by title is now required even for a single declared
    Event — adversarial-review 2026-08-06 — so this passes the candidate title
    exactly as live extraction does.)"""
    page = """
    <html><head><script type="application/ld+json">
    {"@type": "MusicEvent", "name": "Hotel Vegas: Night Two",
     "startDate": "2026-08-11T21:00:00", "endDate": "2026-08-12T02:00:00"}
    </script></head><body>
    <div itemscope itemtype="https://schema.org/Event">
      <meta itemprop="startDate" content="2026-08-11T21:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)
    assert recover_dates_from_url("https://venue.example/n2", candidate_title="Hotel Vegas: Night Two") == {
        "start_time": "2026-08-11T21:00:00",
        "end_time": "2026-08-12T02:00:00"}


def test_several_named_events_plus_a_stray_unnamed_one(monkeypatch):
    """The named-wins rule must not quietly re-open the multi-event hole.

    With MORE than one named declaration the page is genuinely multi-event,
    so the single-named merge does not apply at all and the title has to
    select — while the stray unnamed event (here a far-future one that would
    be obvious in production) contributes to nothing.
    """
    page = """
    <html><head><script type="application/ld+json">
    [{"@type":"Event","name":"Blues Night","startDate":"2026-08-20T20:00:00"},
     {"@type":"Event","startDate":"2029-01-01T00:00:00",
      "endDate":"2029-01-02T00:00:00"}]
    </script></head><body>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Comedy Showcase</span>
      <meta itemprop="startDate" content="2026-08-21T19:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)

    assert recover_dates_from_url("https://v.example/c",
                                  candidate_title="Blues Night") == {
        "start_time": "2026-08-20T20:00:00"}
    assert recover_dates_from_url("https://v.example/c",
                                  candidate_title="Comedy Showcase") == {
        "start_time": "2026-08-21T19:00:00"}
    # No match, and no title at all, both refuse rather than pick.
    assert recover_dates_from_url("https://v.example/c",
                                  candidate_title="Karaoke") == {}
    assert recover_dates_from_url("https://v.example/c") == {}


def test_two_different_events_at_the_same_hour_do_not_collapse(monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05): start_time alone was treated as
    identity, so two DIFFERENT named events at the same hour collapsed into one
    and the survivor inherited the other's end_time. A 7pm early show and a 7pm
    screening in the other room is ordinary programming, not a corner case.
    """
    page = """
    <html><head><script type="application/ld+json">
    [{"@type":"MusicEvent","name":"Early Set: Ruby Fields",
      "startDate":"2026-08-22T19:00:00","endDate":"2026-08-22T20:30:00"},
     {"@type":"ScreeningEvent","name":"Nosferatu on 35mm",
      "startDate":"2026-08-22T19:00:00","endDate":"2026-08-22T23:45:00"}]
    </script></head><body></body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)

    got = recover_dates_from_url("https://venue.example/cal",
                                 candidate_title="Early Set: Ruby Fields")
    assert got == {"start_time": "2026-08-22T19:00:00",
                   "end_time": "2026-08-22T20:30:00"}, (
        f"the set must not inherit the film's 23:45 end; got {got}")

    got = recover_dates_from_url("https://venue.example/cal",
                                 candidate_title="Nosferatu on 35mm")
    assert got["end_time"] == "2026-08-22T23:45:00"


def test_declarations_sharing_no_field_are_not_treated_as_agreeing(monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05): _dates_agree ran all() over an
    EMPTY shared-field set, which is vacuously True — so a named declaration
    with only a start and an unrelated nameless one with only an end "agreed",
    and the merge spliced a different event's end onto the candidate.
    """
    page = """
    <html><head><script type="application/ld+json">
    {"@type":"Event","endDate":"2031-06-30T23:00:00"}
    </script></head><body>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Tuesday Residency</span>
      <meta itemprop="startDate" content="2026-08-25T20:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)

    got = recover_dates_from_url("https://venue.example/e/res",
                                 candidate_title="Tuesday Residency")
    assert got == {"start_time": "2026-08-25T20:00:00"}, (
        f"a nameless declaration sharing NO field must contribute nothing; got {got}")
    assert "end_time" not in got


def test_a_shared_first_name_is_not_an_identification(monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05): any unique positive token
    overlap won the selection, so "John Smith Trio" selected "John Doe Band"
    off a shared "john" — and the wrong act's date was stored as the
    candidate's own source-authoritative date."""
    page = """
    <html><head><script type="application/ld+json">
    [{"@type":"MusicEvent","name":"John Doe Band","startDate":"2026-09-04T21:00:00"},
     {"@type":"MusicEvent","name":"Marfa Tapes","startDate":"2026-09-05T20:00:00"}]
    </script></head><body></body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="John Smith Trio") == {}, (
        "one shared first name must not carry a three-word title")


def test_real_partial_matches_still_attribute(monkeypatch):
    """The strength floor must not become a new way to lose events: the
    ordinary partial matches a venue calendar actually produces still win."""
    page = """
    <html><head><script type="application/ld+json">
    [{"@type":"MusicEvent","name":"Ruby Fields (Late Show)",
      "startDate":"2026-09-10T22:30:00"},
     {"@type":"MusicEvent","name":"An Evening with Patti Smith",
      "startDate":"2026-09-11T20:00:00"},
     {"@type":"MusicEvent","name":"Levitation 2026 Kickoff",
      "startDate":"2026-09-12T19:00:00"}]
    </script></head><body></body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)
    for title, want in (("Ruby Fields", "2026-09-10T22:30:00"),
                        ("Patti Smith", "2026-09-11T20:00:00"),
                        ("Levitation", "2026-09-12T19:00:00")):
        got = recover_dates_from_url("https://venue.example/cal",
                                     candidate_title=title)
        assert got == {"start_time": want}, f"{title} -> {got}"


def test_a_nameless_event_at_the_same_hour_lends_no_end_time(monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05, r4): a nameless declaration
    sharing only start_time was treated as the same event and allowed to fill
    the named candidate's missing endDate — so the candidate wore an unrelated
    event's end time. _dates_agree could never have caught it: end_time was
    not a field they BOTH carried, so it was never compared. A shared hour is
    a coincidence a busy venue produces nightly, not an identification.
    """
    page = """
    <html><head><script type="application/ld+json">
    {"@type":"Event","startDate":"2026-08-28T20:00:00",
     "endDate":"2026-08-29T02:00:00"}
    </script></head><body>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Songwriter Round</span>
      <meta itemprop="startDate" content="2026-08-28T20:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)

    got = recover_dates_from_url("https://venue.example/e/round",
                                 candidate_title="Songwriter Round")
    assert got == {"start_time": "2026-08-28T20:00:00"}, (
        f"the 2am end belongs to whatever else started at 8; got {got}")
    assert "end_time" not in got


def test_a_recurring_event_does_not_collapse_into_one(monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05, r6): a shared NAME merged two
    declarations unconditionally, but recurring events are the normal case on
    a venue calendar — "Trivia Night" every Tuesday is many events with one
    name. Collapsing them made a genuinely multi-event page look single-event,
    and the single-event shortcut then published one occurrence's date for
    another.
    """
    page = """
    <html><head><script type="application/ld+json">
    [{"@type":"Event","name":"Open Mic","startDate":"2026-09-04T19:00:00"},
     {"@type":"Event","name":"Open Mic","startDate":"2026-09-11T19:00:00"}]
    </script></head><body></body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)

    # Two occurrences, one name: which one is the candidate's is unknowable
    # from the title alone, so nothing is recovered rather than a coin flip.
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Open Mic") == {}
    assert recover_dates_from_url("https://venue.example/cal") == {}


def test_the_same_event_in_two_notations_still_collapses(monkeypatch):
    """The recurrence check must not break the case it guards: one event
    declared twice, agreeing on dates, is still ONE event and still recovers.
    (Title attribution is required even for one declared Event since
    adversarial-review 2026-08-06, so the candidate title is supplied here
    exactly as live extraction supplies it.)"""
    page = """
    <html><head><script type="application/ld+json">
    {"@type":"Event","name":"Open Mic","startDate":"2026-09-04T19:00:00",
     "endDate":"2026-09-04T22:00:00"}
    </script></head><body>
    <div itemscope itemtype="https://schema.org/Event">
      <span itemprop="name">Open Mic</span>
      <meta itemprop="startDate" content="2026-09-04T19:00:00"/></div>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)
    assert recover_dates_from_url("https://venue.example/e/mic", candidate_title="Open Mic") == {
        "start_time": "2026-09-04T19:00:00",
        "end_time": "2026-09-04T22:00:00"}


def test_a_two_word_title_must_match_in_full(monkeypatch):
    """Adversarial-review BLOCKER (2026-08-05, r6): half of two tokens is one,
    so "Patti Smith" could select "John Smith Band" off a shared surname — the
    same class as the r3 catch, which the half-rule only closed for titles of
    three tokens or more."""
    page = """
    <html><head><script type="application/ld+json">
    [{"@type":"MusicEvent","name":"John Smith Band","startDate":"2026-09-04T21:00:00"},
     {"@type":"MusicEvent","name":"Marfa Tapes","startDate":"2026-09-05T20:00:00"}]
    </script></head><body></body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page)
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Patti Smith") == {}, (
        "a shared surname must not carry a two-word title")

    # …and the full match still attributes.
    page2 = page.replace("John Smith Band", "Patti Smith Live")
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: page2)
    assert recover_dates_from_url("https://venue.example/cal",
                                  candidate_title="Patti Smith") == {
        "start_time": "2026-09-04T21:00:00"}


def test_unattributable_block_cannot_take_a_neighbours_date(monkeypatch):
    """Adversarial-review catch (2026-08-06, attacker-smuggle lens).

    The source-quoted-link guard proves a URL appears in the extraction BLOCK.
    When the segmenter cannot confidently split a page it returns ONE block
    holding the whole document, so every link on the page satisfies that guard
    — and an extraction mistake can attach a NEIGHBOURING event's genuine,
    source-published link. That page declares exactly one Event, the old rule
    accepted it unmatched, and the neighbour's date became this candidate's
    source-evidenced time on a confirmed first-party card.

    Authority and attribution are different questions. Where the block IS the
    candidate's, the founder's ruling stands untouched (next test)."""
    other_event = """
    <html><head><script type="application/ld+json">
    {"@type":"Event","name":"Trivia Showdown","startDate":"2026-09-30T19:00:00"}
    </script></head><body></body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: other_event)
    assert recover_dates_from_url(
        "https://venue.example/e/trivia",
        candidate_title="Night Owls Live",
        require_attribution=True) == {}


def test_the_founders_ruling_survives_for_an_attributable_block(monkeypatch):
    """The premise of the ruling is that the link came from THIS candidate's
    own block. Where that holds, a single declared Event is the candidate's —
    no identity cross-examination, and a NAMELESS Event recovers too."""
    nameless = """
    <html><body itemscope itemtype="https://schema.org/Event">
    <meta itemprop="startDate" content="2026-08-10T18:00:00"/>
    </body></html>"""
    monkeypatch.setattr(date_callback, "_fetch", lambda url, timeout=15: nameless)
    assert recover_dates_from_url(
        "https://venue.example/page",
        candidate_title="Night Owls Live") == {"start_time": "2026-08-10T18:00:00"}
