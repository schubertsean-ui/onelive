"""Vision extraction tests — fully offline (fake provider, injected store seams).

Covers the trust-critical behaviour: fail-closed OFF by default, AI-never-
fabricate on the empty/invalid paths, and routing through the candidate/gate
store (never the promote path).
"""
import base64

import pytest

from ai.vision_provider import (
    ClaudeVisionProvider,
    VisionConfigError,
    resolve_vision_model,
    vision_extraction_enabled,
)
import worker.vision_extract as ve


ONE_PX_PNG_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode("ascii")


def _enable(monkeypatch, model="claude-vision-test"):
    monkeypatch.setenv("ONELIVE_VISION_EXTRACTION_ENABLED", "1")
    monkeypatch.setenv("ONELIVE_MODEL_VISION", model)


class _FakeVision:
    """A VisionProvider that returns a scripted extraction, no network."""

    def __init__(self, result):
        self._result = result
        self.calls = []

    def extract_event_json_from_image(self, image_b64, media_type, schema_json,
                                      system_prompt=None):
        self.calls.append((image_b64, media_type))
        return self._result


class _Store:
    """Captures create_candidate / add_evidence calls in place of the DB."""

    def __init__(self):
        self.created = []
        self.evidence = []

    def create(self, **kwargs):
        self.created.append(kwargs)
        return f"cand-{len(self.created)}"

    def add(self, **kwargs):
        self.evidence.append(kwargs)


# --- fail-closed master switch ------------------------------------------------

def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ONELIVE_VISION_EXTRACTION_ENABLED", raising=False)
    assert vision_extraction_enabled() is False


def test_enabled_only_on_exact_1(monkeypatch):
    for val in ("0", "true", "yes", "", " 1 x"):
        monkeypatch.setenv("ONELIVE_VISION_EXTRACTION_ENABLED", val)
        assert vision_extraction_enabled() is False
    monkeypatch.setenv("ONELIVE_VISION_EXTRACTION_ENABLED", "1")
    assert vision_extraction_enabled() is True


def test_extract_raises_when_disabled(monkeypatch):
    monkeypatch.delenv("ONELIVE_VISION_EXTRACTION_ENABLED", raising=False)
    store = _Store()
    with pytest.raises(VisionConfigError):
        ve.extract_candidate_from_image(
            vision=_FakeVision({"title": "X"}), image_b64=ONE_PX_PNG_B64,
            media_type="image/png", source_class="flyer", source_name="s",
            source_url="http://x", _create=store.create, _add=store.add,
        )
    assert store.created == []  # nothing stored on the fail-closed path


def test_resolve_vision_model_fails_closed(monkeypatch):
    monkeypatch.delenv("ONELIVE_VISION_EXTRACTION_ENABLED", raising=False)
    with pytest.raises(VisionConfigError):
        resolve_vision_model()
    # enabled but no model -> still fail closed (no policy default)
    monkeypatch.setenv("ONELIVE_VISION_EXTRACTION_ENABLED", "1")
    monkeypatch.delenv("ONELIVE_MODEL_VISION", raising=False)
    with pytest.raises(VisionConfigError):
        resolve_vision_model()
    monkeypatch.setenv("ONELIVE_MODEL_VISION", "m")
    assert resolve_vision_model() == "m"


# --- happy path ---------------------------------------------------------------

def test_valid_event_creates_candidate_through_the_store(monkeypatch):
    _enable(monkeypatch)
    store = _Store()
    result = {
        "title": "The Slow Burn Tour",
        "artist_names": ["Mara Quinn"],
        "venue_name": "Ruby Room Austin",
        "_provenance": {"provider": "claude-vision", "extractor": "vision"},
    }
    outcome = ve.extract_candidate_from_image(
        vision=_FakeVision(result), image_b64=ONE_PX_PNG_B64, media_type="image/png",
        source_class="flyer", source_name="Ruby Room", source_url="http://ruby",
        _create=store.create, _add=store.add,
    )
    assert outcome.image_had_no_event is False
    assert len(store.created) == 1
    stored = store.created[0]
    assert stored["extracted"]["title"] == "The Slow Burn Tour"
    assert stored["extracted"]["artist_names"] == ["Mara Quinn"]
    # marked as vision-extracted for ops
    assert stored["extracted"]["_provenance"]["extractor"] == "vision"
    # one evidence row was written (routed through the gate store)
    assert len(store.evidence) == 1


# --- no fabrication: empty and invalid paths ----------------------------------

def test_missing_city_stays_null_never_fabricated_austin(monkeypatch):
    # adversarial-review #92: the vision path must NOT invent a city. A flyer
    # with no location text yields city=None, never "Austin" (truth-first, and
    # correct for the Austin->Lexington multi-city plan).
    _enable(monkeypatch)
    store = _Store()
    ve.extract_candidate_from_image(
        vision=_FakeVision({"title": "Neon Harbor", "artist_names": ["Neon Harbor"]}),
        image_b64=ONE_PX_PNG_B64, media_type="image/png", source_class="flyer",
        source_name="s", source_url="http://x", _create=store.create, _add=store.add,
    )
    assert store.created[0]["extracted"]["city"] is None


def test_supplied_extractor_provenance_is_overwritten_to_vision(monkeypatch):
    # adversarial-review #92: a model/caller-supplied `_provenance.extractor`
    # must NOT survive and disguise a vision candidate as certified-text.
    _enable(monkeypatch)
    store = _Store()
    spoofed = {"title": "X", "artist_names": ["A"],
               "_provenance": {"extractor": "text", "provider": "spoof"}}
    ve.extract_candidate_from_image(
        vision=_FakeVision(spoofed), image_b64=ONE_PX_PNG_B64, media_type="image/png",
        source_class="flyer", source_name="s", source_url="http://x",
        _create=store.create, _add=store.add,
    )
    assert store.created[0]["extracted"]["_provenance"]["extractor"] == "vision"


def test_provider_none_result_raises_never_false_no_event(monkeypatch):
    # adversarial-review #92 (both openai seats): a None result from the
    # provider = "we failed to look" (transient failure / blank input), NOT
    # "the image had no event". It must fail LOUD and record NO candidate —
    # never a false image_had_no_event row that could bury a real event.
    _enable(monkeypatch)
    store = _Store()
    with pytest.raises(ve.VisionExtractionError):
        ve.extract_candidate_from_image(
            vision=_FakeVision(None), image_b64=ONE_PX_PNG_B64,
            media_type="image/png", source_class="flyer", source_name="s",
            source_url="http://x", _create=store.create, _add=store.add,
        )
    assert store.created == []  # no false "no event" candidate on a failed read


def test_image_with_no_event_flags_empty_candidate(monkeypatch):
    _enable(monkeypatch)
    store = _Store()
    outcome = ve.extract_candidate_from_image(
        vision=_FakeVision({}), image_b64=ONE_PX_PNG_B64, media_type="image/png",
        source_class="flyer", source_name="s", source_url="http://x",
        _create=store.create, _add=store.add,
    )
    assert outcome.image_had_no_event is True
    assert len(store.created) == 1  # never silently dropped
    prov = store.created[0]["extracted"]["_provenance"]
    assert prov["image_had_no_event"] is True
    assert prov["extractor"] == "vision"
    # no fabricated fields
    assert store.created[0]["extracted"]["title"] is None


def test_schema_invalid_extraction_flags_not_blanks(monkeypatch):
    _enable(monkeypatch)
    store = _Store()
    # artist_names must be a list; a string is schema-invalid.
    bad = {"title": "X", "artist_names": "not-a-list",
           "_provenance": {"extractor": "vision"}}
    outcome = ve.extract_candidate_from_image(
        vision=_FakeVision(bad), image_b64=ONE_PX_PNG_B64, media_type="image/png",
        source_class="flyer", source_name="s", source_url="http://x",
        _create=store.create, _add=store.add,
    )
    # Non-empty fields present -> treated as an event attempt, not "no event".
    assert outcome.image_had_no_event is False
    prov = store.created[0]["extracted"]["_provenance"]
    assert prov["validation_error"] is True  # flagged, not silently blanked


def test_never_imports_the_promote_path():
    # Trust invariant: the extraction module must not reach the publish path.
    import worker.vision_extract as mod
    src = mod.__file__
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()
    assert "import worker.promote" not in text
    assert "from worker.promote" not in text
    assert "import worker.gating" not in text
    assert "from worker.gating" not in text


# --- provider: fail loud, never fabricate -------------------------------------

def test_provider_rejects_unsupported_media_type(monkeypatch):
    _enable(monkeypatch)
    prov = ClaudeVisionProvider(api_key="k", client=object())
    with pytest.raises(VisionConfigError):
        prov.extract_event_json_from_image(ONE_PX_PNG_B64, "image/tiff", {})


def test_provider_stamps_vision_provenance(monkeypatch):
    _enable(monkeypatch, model="claude-vision-x")

    class _Block:
        type = "tool_use"
        input = {"title": "Neon Harbor"}

    class _Resp:
        content = [_Block()]

    class _Client:
        class messages:
            @staticmethod
            def create(**kwargs):
                return _Resp()

    prov = ClaudeVisionProvider(api_key="k", client=_Client())
    out = prov.extract_event_json_from_image(ONE_PX_PNG_B64, "image/png", {})
    assert out["title"] == "Neon Harbor"
    assert out["_provenance"]["provider"] == "claude-vision"
    assert out["_provenance"]["extractor"] == "vision"
    assert out["_provenance"]["model"] == "claude-vision-x"
    assert "prompt_sha256" in out["_provenance"]


def test_provider_config_error_is_loud_not_none(monkeypatch):
    _enable(monkeypatch)

    class _Boom:
        status_code = 404  # unknown model -> structural

        def __str__(self):
            return "not found"

    class _Client:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise type("NotFoundError", (Exception,), {
                    "status_code": 404})("unknown model")

    prov = ClaudeVisionProvider(api_key="k", client=_Client())
    with pytest.raises(VisionConfigError):
        prov.extract_event_json_from_image(ONE_PX_PNG_B64, "image/png", {})
