"""Integration tests for worker/ai_extract.extract_candidate.

Proves the end-to-end wiring between a provider and the candidate store WITHOUT
a database, by monkeypatching the store's DB-writing functions. Locks in:
  - provider `_provenance` is PRESERVED into the stored `extracted` jsonb
    (it must survive the pydantic validation boundary, which drops unknown keys)
  - a schema-invalid extraction is FLAGGED (validation_error) and still stored
    for ops review, not silently dropped
  - the degradation audit_hook is passed only to providers that accept it
"""
import logging
import re

import pytest

import worker.ai_extract as ai_extract


@pytest.fixture
def captured(monkeypatch):
    """Capture what would be written to the DB."""
    store = {"created": None, "evidence": None, "degradations": []}

    def fake_create_candidate(**kwargs):
        store["created"] = kwargs
        return "cand-123"

    def fake_add_evidence(**kwargs):
        store["evidence"] = kwargs
        return "ev-1"

    def fake_record_degradation(payload):
        store["degradations"].append(payload)

    monkeypatch.setattr(ai_extract, "create_candidate", fake_create_candidate)
    monkeypatch.setattr(ai_extract, "add_evidence", fake_add_evidence)
    monkeypatch.setattr(ai_extract, "record_ai_degradation", fake_record_degradation)
    return store


class ProvenanceProvider:
    """Provider that returns a valid extraction stamped with provenance,
    and accepts the audit_hook/source_name kwargs (like the real Claude one)."""
    def extract_event_json(self, text, schema_json, system_prompt=None, *,
                          audit_hook=None, source_name=None):
        return {
            "title": "Night Show",
            "venue_name": "Mohawk",
            "_provenance": {"provider": "claude", "model": "claude-test"},
        }


class InvalidProvider:
    def extract_event_json(self, text, schema_json, system_prompt=None, *,
                          audit_hook=None, source_name=None):
        # artist_names must be a list; a string is schema-invalid.
        return {"title": "X", "artist_names": "not-a-list",
                "_provenance": {"provider": "claude"}}


def test_provenance_persists_into_stored_extracted(captured):
    cid = ai_extract.extract_candidate(
        ai=ProvenanceProvider(), text="Night Show at Mohawk",
        source_class="social", source_name="Do512",
        source_url="http://x", source_id="s1")
    assert cid == "cand-123"
    stored = captured["created"]["extracted"]
    assert stored["title"] == "Night Show"
    assert stored["venue_name"] == "Mohawk"
    # The provenance must have survived the pydantic boundary.
    assert stored["_provenance"]["provider"] == "claude"
    assert stored["_provenance"]["model"] == "claude-test"


def test_invalid_extraction_is_flagged_not_swallowed(captured):
    ai_extract.extract_candidate(
        ai=InvalidProvider(), text="junk",
        source_class="social", source_name="BadSrc",
        source_url="http://x", source_id="s2")
    stored = captured["created"]["extracted"]
    # Empty event fields, but explicitly TAGGED so ops can see it was malformed.
    assert stored["title"] is None
    assert stored["_provenance"]["validation_error"] is True


def test_hook_only_passed_to_capable_provider(captured):
    """A minimal stub-style provider (no audit_hook kwarg) must not error."""
    class MinimalProvider:
        def extract_event_json(self, text, schema_json, system_prompt=None):
            return None
    cid = ai_extract.extract_candidate(
        ai=MinimalProvider(), text="something",
        source_class="social", source_name="Src",
        source_url="http://x", source_id="s3")
    assert cid == "cand-123"
    # No crash, empty candidate created with default city.
    assert captured["created"]["extracted"]["city"] == "Austin"


# --------------------------------------------------------------------------
# Multi-event fan-out: segment a page -> N blocks -> N candidates + N evidence,
# each isolated. Uses a provider mock that reads per-block tokens (no network /
# AI / DB), exactly the style above.
# --------------------------------------------------------------------------

@pytest.fixture
def store(monkeypatch):
    """Capture EVERY created candidate + evidence row (fan-out records many)."""
    recs = {"created": [], "evidence": []}

    def fake_create(**kwargs):
        recs["created"].append(kwargs)
        return f"cand-{len(recs['created'])}"

    def fake_evidence(**kwargs):
        recs["evidence"].append(kwargs)
        return f"ev-{len(recs['evidence'])}"

    monkeypatch.setattr(ai_extract, "create_candidate", fake_create)
    monkeypatch.setattr(ai_extract, "add_evidence", fake_evidence)
    monkeypatch.setattr(ai_extract, "record_ai_degradation", lambda p: None)
    return recs


class BlockEventProvider:
    """Certified-extractor stand-in: reads ONE event out of the block it is
    handed (tokens ``START=`` / ``ART=`` / ``VEN=``). A block with no tokens is
    'no event found' — the real single-event extractor's empty result."""
    def extract_event_json(self, text, schema_json, system_prompt=None, *,
                           audit_hook=None, source_name=None):
        def tok(key):
            # Lookbehind so ``ART=`` does not match inside ``START=``.
            m = re.search(r"(?<![A-Za-z])" + key + r"=([^|<]+)", text)
            return m.group(1).strip() if m else None
        start, art, ven = tok("START"), tok("ART"), tok("VEN")
        if not any([start, art, ven]):
            return {"_provenance": {"provider": "claude", "model": "claude-test"}}
        return {
            "title": None,
            "start_time": start,
            "venue_name": ven,
            "artist_names": [art] if art else [],
            "_provenance": {"provider": "claude", "model": "claude-test"},
        }


class NoEventProvider:
    """Real page text, but the model finds no event (e.g. the calendar moved)."""
    def extract_event_json(self, text, schema_json, system_prompt=None, *,
                           audit_hook=None, source_name=None):
        return {"_provenance": {"provider": "claude", "model": "claude-test"}}


_MULTI_HTML = (
    "<div class='calendar'>"
    "<article class='event'>Fri Aug 1 | START=2026-08-01T20:00 | ART=Castle Creek | VEN=Mohawk</article>"
    "<article class='event'>Sat Aug 2 | START=8pm | ART=River Delta | VEN=Cedar Hall</article>"
    "</div>"
)


def test_multievent_page_fans_out_one_candidate_per_event(store):
    outcome = ai_extract.extract_candidates(
        ai=BlockEventProvider(), text=_MULTI_HTML,
        source_class="social", source_name="Do512",
        source_url="http://x", source_id="s1")
    assert len(outcome.candidate_ids) == 2
    assert outcome.source_returned_empty is False
    assert len(store["created"]) == 2
    assert len(store["evidence"]) == 2

    e0, e1 = store["created"][0]["extracted"], store["created"][1]["extracted"]
    # Per-event fields are isolated — no cross-leak of venue or artist.
    assert e0["venue_name"] == "Mohawk"
    assert e0["artist_names"] == ["Castle Creek"]
    assert e1["venue_name"] == "Cedar Hall"
    assert e1["artist_names"] == ["River Delta"]
    # Evidence quote is each event's OWN block, not the whole page.
    q0 = store["evidence"][0]["quote"]
    assert "Mohawk" in q0 and "Cedar Hall" not in q0


def test_per_event_r021_dated_stored_time_only_nulled_no_crossleak(store):
    ai_extract.extract_candidates(
        ai=BlockEventProvider(), text=_MULTI_HTML,
        source_class="social", source_name="Do512",
        source_url="http://x", source_id="s1")
    dated, time_only = store["created"][0]["extracted"], store["created"][1]["extracted"]
    # Full-date event: timestamp stored.
    assert dated["start_time"] == "2026-08-01T20:00:00"
    assert "unstored_datetime_claims" not in dated.get("_provenance", {})
    # Time-only event: NULL stored, raw claim preserved in ITS provenance only.
    assert time_only["start_time"] is None
    refused = time_only["_provenance"]["unstored_datetime_claims"]["start_time"]
    assert refused["raw"] == "8pm"


def test_single_event_page_still_one_candidate(store):
    outcome = ai_extract.extract_candidates(
        ai=BlockEventProvider(),
        text="One night only | START=2026-08-01T20:00 | ART=Solo Act | VEN=Mohawk",
        source_class="social", source_name="Src",
        source_url="http://x", source_id="s2")
    assert len(outcome.candidate_ids) == 1
    assert store["created"][0]["extracted"]["venue_name"] == "Mohawk"


def test_zero_events_from_real_text_fires_moved_signal(store, caplog):
    real_text = "This calendar page has plenty of prose but no extractable show tonight."
    with caplog.at_level(logging.WARNING):
        outcome = ai_extract.extract_candidates(
            ai=NoEventProvider(), text=real_text,
            source_class="social", source_name="MovedSrc",
            source_url="http://x", source_id="s4")
    # Never a silent drop: exactly one flagged empty candidate + the marker.
    assert outcome.source_returned_empty is True
    assert len(store["created"]) == 1
    assert store["created"][0]["extracted"]["_provenance"]["source_returned_empty"] is True
    assert ai_extract.SOURCE_MAY_HAVE_MOVED_MARKER in caplog.text


def test_backcompat_wrapper_returns_first_id(store):
    cid = ai_extract.extract_candidate(
        ai=BlockEventProvider(), text=_MULTI_HTML,
        source_class="social", source_name="Do512",
        source_url="http://x", source_id="s1")
    assert cid == "cand-1"
    # The wrapper still fans out fully (both candidates stored).
    assert len(store["created"]) == 2


def test_per_page_extraction_cap_bounds_ai_calls(monkeypatch):
    """FinOps R-043: the multi-event fan-out makes one real AI call per block, so
    the per-page cap must HARD-BOUND calls (else a single big calendar defeats the
    per-run budget). Overflow blocks are deferred, never dropped silently."""
    monkeypatch.setenv("EXTRACT_MAX_EVENTS_PER_PAGE", "3")
    # 5 event blocks; the cap is 3 → at most 3 AI calls, 2 deferred.
    monkeypatch.setattr(
        ai_extract, "segment_events",
        lambda text, **kw: [f"Show {i} at Mohawk on 2026-08-0{i}" for i in range(1, 6)],
    )
    calls = {"n": 0}

    class CountingProvider:
        def extract_event_json(self, text, schema_json, system_prompt=None, **kw):
            calls["n"] += 1
            return {"title": f"Show {calls['n']}", "venue_name": "Mohawk"}

    created = {"n": 0}
    monkeypatch.setattr(ai_extract, "create_candidate",
                        lambda **k: (created.__setitem__("n", created["n"] + 1), f"c{created['n']}")[1])
    monkeypatch.setattr(ai_extract, "add_evidence", lambda **k: "ev")

    out = ai_extract.extract_candidates(
        ai=CountingProvider(), text="a page with five shows",
        source_class="venue_calendar", source_name="Mohawk", source_url="u")

    assert calls["n"] == 3, f"expected 3 AI calls (capped), got {calls['n']} — cost fail-open"
    assert len(out.candidate_ids) == 3
