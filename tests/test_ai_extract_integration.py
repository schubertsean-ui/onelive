"""Integration tests for worker/ai_extract.extract_candidate.

Proves the end-to-end wiring between a provider and the candidate store WITHOUT
a database, by monkeypatching the store's DB-writing functions. Locks in:
  - provider `_provenance` is PRESERVED into the stored `extracted` jsonb
    (it must survive the pydantic validation boundary, which drops unknown keys)
  - a schema-invalid extraction is FLAGGED (validation_error) and still stored
    for ops review, not silently dropped
  - the degradation audit_hook is passed only to providers that accept it
"""
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
