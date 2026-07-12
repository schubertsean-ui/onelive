"""Tests for the real Claude provider and the upgraded eval harness.

No network or API key required: a FakeAnthropic client is injected. These tests
lock in the trust-critical behavior:
  - misconfiguration fails LOUDLY (mirrors _fuzzy_match's 42883 branch)
  - transient errors retry then degrade to None (safe), AND write an audit row
  - successful extraction is stamped with provenance
  - the hallucination-rate metric behaves as specified
"""
import pytest

from ai.claude_provider import ClaudeProvider, ExtractionConfigError, PROMPT_VERSION
from ai.eval_harness import score_extraction, aggregate


SCHEMA = {"type": "object", "properties": {"title": {"type": "string"}}}


# --- fakes -------------------------------------------------------------------
class _Block:
    def __init__(self, data):
        self.type = "tool_use"
        self.input = data


class _Resp:
    def __init__(self, data):
        self.content = [_Block(data)]


class FakeMessages:
    def __init__(self, behavior):
        self._behavior = behavior  # callable(attempt) -> _Resp or raises
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        return self._behavior(self.calls, kwargs)


class FakeAnthropic:
    def __init__(self, behavior):
        self.messages = FakeMessages(behavior)


class FakeHTTPError(Exception):
    def __init__(self, status_code):
        super().__init__(f"http {status_code}")
        self.status_code = status_code


class RecordingHook:
    """Stand-in for the DB-backed audit_hook: records payloads in memory."""
    def __init__(self):
        self.payloads = []

    def __call__(self, payload):
        self.payloads.append(payload)


# --- config errors fail loudly ----------------------------------------------
def test_missing_api_key_raises():
    p = ClaudeProvider(api_key=None)
    with pytest.raises(ExtractionConfigError):
        p.extract_event_json("some text", SCHEMA)


def test_structural_4xx_raises_not_degrades():
    def behavior(attempt, kwargs):
        raise FakeHTTPError(400)  # bad request / malformed schema
    p = ClaudeProvider(api_key="k", client=FakeAnthropic(behavior))
    with pytest.raises(ExtractionConfigError):
        p.extract_event_json("text", SCHEMA)
    # Must NOT have retried a structural error.
    assert p._client.messages.calls == 1


def test_auth_error_by_typename_raises():
    class AuthenticationError(Exception):
        pass
    def behavior(attempt, kwargs):
        raise AuthenticationError("bad key")
    p = ClaudeProvider(api_key="k", client=FakeAnthropic(behavior))
    with pytest.raises(ExtractionConfigError):
        p.extract_event_json("text", SCHEMA)


# --- transient errors retry then degrade safely ------------------------------
def test_rate_limit_retries_then_degrades_to_none():
    def behavior(attempt, kwargs):
        raise FakeHTTPError(429)  # always rate-limited
    p = ClaudeProvider(api_key="k", client=FakeAnthropic(behavior),
                       max_retries=3)
    p_sleep = __import__("ai.claude_provider", fromlist=["time"]).time
    p_sleep.sleep = lambda *_: None  # no real sleep in tests
    hook = RecordingHook()
    out = p.extract_event_json("text", SCHEMA, audit_hook=hook, source_name="Do512")
    assert out is None
    assert p._client.messages.calls == 3          # retried up to the cap
    # degradation must be audited, not invisible
    assert len(hook.payloads) == 1
    assert hook.payloads[0]["source_name"] == "Do512"
    assert "error" in hook.payloads[0]


def test_transient_then_success_recovers():
    def behavior(attempt, kwargs):
        if attempt == 1:
            raise FakeHTTPError(503)
        return _Resp({"title": "Show at Mohawk"})
    p = ClaudeProvider(api_key="k", client=FakeAnthropic(behavior), max_retries=3)
    __import__("ai.claude_provider", fromlist=["time"]).time.sleep = lambda *_: None
    out = p.extract_event_json("text", SCHEMA)
    assert out["title"] == "Show at Mohawk"
    assert p._client.messages.calls == 2


# --- provenance --------------------------------------------------------------
def test_success_is_stamped_with_provenance():
    def behavior(attempt, kwargs):
        return _Resp({"title": "X"})
    p = ClaudeProvider(api_key="k", model="claude-test",
                       client=FakeAnthropic(behavior))
    out = p.extract_event_json("text", SCHEMA)
    prov = out["_provenance"]
    assert prov["provider"] == "claude"
    assert prov["model"] == "claude-test"
    assert prov["prompt_version"] == PROMPT_VERSION
    assert "extracted_at" in prov


def test_empty_text_returns_none_without_calling_api():
    p = ClaudeProvider(api_key="k", client=FakeAnthropic(lambda *_: None))
    assert p.extract_event_json("   ", SCHEMA) is None
    assert p._client.messages.calls == 0


# --- eval harness: hallucination metric --------------------------------------
def test_hallucination_rate_flags_invented_field():
    predicted = {"title": "Real Show", "venue_name": "Invented Venue"}
    expected = {"title": "Real Show", "venue_name": None}
    s = score_extraction(predicted, expected)
    assert "venue_name" in s.hallucinated_fields
    assert s.false_positives == 1
    assert s.true_positives == 1
    assert s.hallucination_rate == pytest.approx(0.5)


def test_perfect_extraction_zero_hallucination():
    d = {"title": "A", "venue_name": "Mohawk", "artist_names": ["B"]}
    s = score_extraction(d, d)
    assert s.hallucination_rate == 0.0
    assert s.precision == 1.0 and s.recall == 1.0


def test_provenance_key_ignored_in_scoring():
    predicted = {"title": "A", "_provenance": {"model": "x"}}
    expected = {"title": "A"}
    s = score_extraction(predicted, expected)
    assert s.false_positives == 0  # _provenance must not count as a hallucination


def test_missed_field_is_recall_miss_not_hallucination():
    predicted = {"title": "A"}
    expected = {"title": "A", "venue_name": "Mohawk"}
    s = score_extraction(predicted, expected)
    assert s.false_negatives == 1
    assert s.false_positives == 0
    assert s.hallucination_rate == 0.0


def test_aggregate_micro_average():
    s1 = score_extraction({"title": "A"}, {"title": "A"})
    s2 = score_extraction({"title": "wrong"}, {"title": "B"})
    agg = aggregate([s1, s2])
    assert agg["n_examples"] == 2
    assert 0.0 <= agg["hallucination_rate"] <= 1.0


def test_accuracy_scalar_replaces_retired_evaluate_extraction():
    # evaluate_extraction (exact-match ratio) was retired under the Sunset Law;
    # ExtractionScore.accuracy is the one 0..1 scalar representation now.
    assert score_extraction({"a": 1}, {"a": 1}).accuracy == 1.0
    assert score_extraction({"a": 1}, {"a": 2}).accuracy == 0.0
    assert score_extraction({}, {}).accuracy == 1.0  # nothing to compare
