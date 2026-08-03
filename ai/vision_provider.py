"""Vision AI provider — weak-signal event extraction from IMAGES.

Why this exists (founder-authorized 2026-07-29, "Yes start capturing image
only"): OneLive's text pipeline (ai/claude_provider.py + worker/ai_extract.py)
reads events out of page TEXT. But some sources put the event only inside a
picture — a gig-poster JPEG, a PDF flyer, an Instagram flyer, a calendar
rendered as a background image — and worker/fetch/render_fetch.py deliberately
BLOCKS images to stay fast, so those events are invisible today. This provider
reads the picture instead of the text. (Assessment that surfaced the gap:
docs/memory/decisions/2026-07-29_pixelrag-visual-ingestion-assessment.md.)

## Trust posture — read this before changing anything

1. **Publication is gate-custodied.** Vision output is turned into an event_candidate and
   goes through the SAME human promotion gate as text (worker/vision_extract.py
   calls worker.candidate_store, never worker.promote / worker.gating). A vision
   hallucination can at worst create a candidate a human then rejects — exactly
   the protection text extraction has. That invariant is physics here.

2. **This is a SEPARATE, UNCERTIFIED harness.** The attended golden exam
   certifies the TEXT extractor (ai/prompts.py). Vision does NOT ride that
   certification and must never claim it. It is therefore fail-closed OFF by
   default: it runs ONLY when ONELIVE_VISION_EXTRACTION_ENABLED == "1" AND a
   model is explicitly configured (ONELIVE_MODEL_VISION). It touches neither
   EXTRACTION_THRESHOLD_RATIFIED nor the certified prompt/model, so the
   extraction certification hash is unaffected.

3. **Fail loud, never fabricate** (mirrors ai/claude_provider.py, the project
   convention from worker/resolve_entities._fuzzy_match): a misconfiguration
   (no key, SDK missing, unknown model, 4xx) raises VisionConfigError; a
   transient failure (429/timeout/5xx) retries then returns None (audited);
   "the model saw no event" returns all-null. "We failed to look" and "nothing
   was there" are never conflated.

4. **Provenance marks vision output** (`_provenance.extractor = "vision"`) so a
   vision-extracted candidate is unmistakable in ops review — the compensating
   control while this harness is uncertified.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Protocol
import hashlib
import html
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

# Bump when VISION_EXTRACTION_SYSTEM_PROMPT changes materially, so provenance on
# stored candidates records which prompt produced them.
VISION_PROMPT_VERSION = "2026-07-29.1"

MAX_RETRIES = 3
BACKOFF_BASE_S = 1.0

# Media types we accept for a vision extraction. A flyer is almost always one of
# these; anything else is rejected loudly rather than sent to the model blind.
SUPPORTED_MEDIA_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/webp", "image/gif"}
)

# The image variant of ai/prompts.EXTRACTION_SYSTEM_PROMPT. DELIBERATELY its own
# constant (not an import) so the certified text prompt's hash cannot be altered
# by a change here. Same truth-first, anti-fabrication spine.
VISION_EXTRACTION_SYSTEM_PROMPT = """You are an information-extraction system \
for a truth-first live-events platform. The user gives you a single IMAGE — a \
show flyer, a gig poster, a PDF page, or a screenshot of a venue calendar.

Your ONLY job is to extract event details that are LITERALLY VISIBLE in the \
image. You are not a search engine and you have no outside knowledge of events, \
venues, or artists. If text in the image is blurry, cropped, or unreadable, \
treat it as absent.

Hard rules — follow every one:
1. NEVER invent, guess, infer, or "complete" any value. If the image does not \
explicitly show a field, return null (or an empty list for artist_names). An \
empty/null field is always correct when the information is not visible.
2. Do NOT invent or normalize times. Only return a time explicitly printed in \
the image. Do not assume a year, timezone, or AM/PM that is not shown.
3. Do NOT invent venue names. Only return a venue named in the image.
4. Do NOT invent artist/performer names. Only list performers explicitly named \
in the image. Never expand "and friends", "special guests", or "TBA".
5. Do NOT fabricate ticket or RSVP links. Only return a URL printed verbatim in \
the image.
6. Copy names and titles exactly as shown; do not translate, rename, or correct.
7. If the image shows no event at all (a logo, a menu, an unrelated photo), \
return all fields null/empty.
8. City discipline is absolute: output a city ONLY when the image names it as \
the event's location. A city word inside a proper name (a venue "Ruby Room \
Austin", a band "The Dallas Winds") or a fan greeting ("AUSTIN!!!") is NOT the \
event's city. When in any doubt, city is null.

Return only what you can actually read. A mostly-decorative poster with only a \
band name and a date should yield exactly that — a name and a date — and null \
for everything else."""


class VisionConfigError(RuntimeError):
    """Misconfiguration/structural failure that must fail loudly rather than
    degrade to a silent empty extraction (see module docstring)."""


class VisionProvider(Protocol):
    """The seam worker/vision_extract.py depends on. Kept minimal so tests can
    supply a fake with no network or model."""

    def extract_event_json_from_image(
        self,
        image_b64: str,
        media_type: str,
        schema_json: dict,
        system_prompt: Optional[str] = None,
    ) -> Optional[dict]:
        ...


def vision_extraction_enabled() -> bool:
    """Fail-closed master switch. Vision extraction runs ONLY when explicitly
    enabled — it is an uncertified harness, so OFF is the safe default and the
    value must be the exact string "1" (never truthiness), mirroring the
    boolean-exact discipline of the text extraction gate."""
    return os.getenv("ONELIVE_VISION_EXTRACTION_ENABLED", "").strip() == "1"


def resolve_vision_model(explicit: Optional[str] = None) -> str:
    """Resolve the vision model, fail-closed. Vision is OFF unless enabled AND a
    model is configured — there is deliberately NO policy default, because a
    default would let this uncertified path fire on a misconfiguration."""
    if not vision_extraction_enabled():
        raise VisionConfigError(
            "vision extraction is disabled — set ONELIVE_VISION_EXTRACTION_ENABLED=1 "
            "to enable it. It is an uncertified harness and fail-closed OFF by default."
        )
    model = (explicit or os.getenv("ONELIVE_MODEL_VISION", "")).strip()
    if not model:
        raise VisionConfigError(
            "ONELIVE_VISION_EXTRACTION_ENABLED=1 but no vision model is configured — "
            "set ONELIVE_MODEL_VISION to a vision-capable model id. There is no "
            "policy default for the uncertified vision path (fail closed)."
        )
    return model


class ClaudeVisionProvider(VisionProvider):
    """Anthropic implementation of the vision seam. Structurally mirrors
    ai/claude_provider.ClaudeProvider (retries, config-vs-transient split,
    provenance stamp) so the two extraction paths behave the same on failure."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        client=None,
        max_retries: int = MAX_RETRIES,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        # Fail-closed at construction: no ClaudeVisionProvider exists unless
        # vision is enabled and a model is set.
        self.model = resolve_vision_model(model)
        self.max_tokens = max_tokens
        self._client = client
        self.max_retries = max_retries

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise VisionConfigError(
                "ANTHROPIC_API_KEY is not set; refusing to silently return an empty "
                "vision extraction."
            )
        try:
            import anthropic  # noqa: PLC0415 — lazy: absent SDK must not break import
        except ImportError as exc:
            raise VisionConfigError(
                "The `anthropic` package is not installed (see worker/requirements.txt). "
                "Refusing to silently degrade."
            ) from exc
        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def extract_event_json_from_image(
        self,
        image_b64: str,
        media_type: str,
        schema_json: dict,
        system_prompt: Optional[str] = None,
        *,
        audit_hook=None,
        source_name: Optional[str] = None,
    ) -> Optional[dict]:
        if not image_b64 or not image_b64.strip():
            return None
        if media_type not in SUPPORTED_MEDIA_TYPES:
            # A bad media type is a config/structural error — fail loud, never
            # send the model an image it cannot read and call the null result
            # "no event".
            raise VisionConfigError(
                f"unsupported image media_type {media_type!r}; expected one of "
                f"{sorted(SUPPORTED_MEDIA_TYPES)}"
            )

        client = self._get_client()  # may raise VisionConfigError (loud)

        tool = {
            "name": "record_event_extraction",
            "description": (
                "Record only the event fields LITERALLY VISIBLE in the image. "
                "Leave any field null/empty if it is not shown."
            ),
            "input_schema": schema_json,
        }
        used_prompt = system_prompt or VISION_EXTRACTION_SYSTEM_PROMPT
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_b64,
                },
            },
            {
                "type": "text",
                "text": "Extract the event details visible in this image.",
            },
        ]

        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=used_prompt,
                    tools=[tool],
                    tool_choice={"type": "tool", "name": "record_event_extraction"},
                    messages=[{"role": "user", "content": content}],
                )
                return self._stamp(self._extract_tool_input(resp), used_prompt)
            except Exception as exc:  # noqa: BLE001 — classified below
                if self._is_config_error(exc):
                    logger.error(
                        "Claude vision extraction hit a structural/config error (%s); "
                        "refusing to silently degrade to an empty extraction.", exc
                    )
                    raise VisionConfigError(str(exc)) from exc
                last_exc = exc
                if attempt < self.max_retries:
                    sleep_s = BACKOFF_BASE_S * (2 ** (attempt - 1))
                    logger.warning(
                        "Claude vision transient error (attempt %d/%d): %s; retrying "
                        "in %.1fs", attempt, self.max_retries, exc, sleep_s
                    )
                    time.sleep(sleep_s)

        logger.error(
            "Claude vision extraction failed after %d attempts: %s; degrading to "
            "manual/evidence path.", self.max_retries, last_exc
        )
        self._audit_degradation(audit_hook, source_name, last_exc)
        return None

    # --- helpers (mirror ai/claude_provider.py) ------------------------------

    @staticmethod
    def _is_config_error(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None)
        if status is not None:
            if status == 429 or status >= 500:
                return False
            if 400 <= status < 500:
                return True
        name = type(exc).__name__.lower()
        if any(k in name for k in ("authentication", "permission", "notfound",
                                   "badrequest", "invalidrequest", "unprocessable")):
            return True
        if any(k in name for k in ("ratelimit", "timeout", "connection",
                                   "apiconnection", "internalserver", "overloaded")):
            return False
        return False

    @staticmethod
    def _extract_tool_input(resp) -> Optional[dict]:
        for block in getattr(resp, "content", []) or []:
            if getattr(block, "type", None) == "tool_use":
                data = getattr(block, "input", None)
                if isinstance(data, dict):
                    return data
                if isinstance(data, str):
                    try:
                        return json.loads(data)
                    except (ValueError, TypeError):
                        return None
        return None

    @staticmethod
    def _decode_entities(data: Optional[dict]) -> Optional[dict]:
        if data is None:
            return None
        def dec(v):
            if isinstance(v, str):
                return html.unescape(v)
            if isinstance(v, list):
                return [dec(x) for x in v]
            if isinstance(v, dict):
                return {k: dec(x) for k, x in v.items()}
            return v
        return {k: dec(v) for k, v in data.items()}

    def _stamp(self, data: Optional[dict], used_prompt: str) -> Optional[dict]:
        """Attach provenance. `extractor="vision"` is the ops-visible marker that
        this candidate came from the uncertified image path."""
        if data is None:
            return None
        data = self._decode_entities(data)
        data["_provenance"] = {
            "provider": "claude-vision",
            "extractor": "vision",
            "model": self.model,
            "prompt_version": VISION_PROMPT_VERSION,
            "prompt_sha256": hashlib.sha256(used_prompt.encode("utf-8")).hexdigest(),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        return data

    @staticmethod
    def _audit_degradation(audit_hook, source_name, exc) -> None:
        if audit_hook is None:
            return
        try:
            audit_hook({
                "source_name": source_name,
                "error": str(exc),
                "at": datetime.now(timezone.utc).isoformat(),
                "extractor": "vision",
            })
        except Exception as audit_exc:  # noqa: BLE001
            logger.warning("failed to write vision degradation audit row: %s", audit_exc)
