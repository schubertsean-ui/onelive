"""Real Claude (Anthropic) AI provider for weak-signal event extraction.

Implements the `AIProvider` protocol (ai/provider.py) as a drop-in replacement
for the stub `BedrockProvider` — no caller changes required for the happy path.

Per CLAUDE.md: the Claude API is used ONLY for weak-signal extraction from raw
fetched text, NEVER to auto-publish. Publishing still passes through the
multi-confirm gate (worker/gating.py). The extraction prompt (ai/prompts.py) is
strict and anti-hallucination by design.

## Failure semantics — the trust decision (mirrors migration 0006's _fuzzy_match)

`worker/resolve_entities.py::_fuzzy_match` established the project convention for
"silent degradation is a trust hole": a genuine transient miss soft-falls-back,
but a *misconfiguration* (SQLSTATE 42883) fails LOUDLY rather than masquerading as
a normal empty result. This provider applies the same split, because in a
truth-first pipeline "the model found no event" and "we failed to even look" must
never be indistinguishable:

- **Configuration / structural failure** (no API key, SDK missing, unknown model,
  the API rejecting our request/schema with a 4xx that isn't rate-limiting) ->
  **raise `ExtractionConfigError`**. These are deploy bugs; returning None here
  would let a broken config render as empty event listings. The orchestrator is
  expected to catch this, route the source to manual review, and audit it — never
  swallow it.
- **Genuinely transient failure** (429 rate limit, timeout, 5xx) -> retry with
  exponential backoff; if still failing, **return None AND write a structured
  `audit_log` row** (action='ai_extraction_degraded') if a cursor is available, so
  the degradation is observable, not invisible. None routes the candidate to the
  evidence/manual path — never fabricated data.
- **Model genuinely found nothing** -> return the extraction (all-null fields) or
  None. This is the truthful answer.

The audit row on the transient path is the extra guarantee beyond the 0006
precedent: even though "transient failure" and "genuinely empty" can both surface
as None to the caller, only one of them leaves an audit trail, so ops can always
tell "we failed to look" apart from "nothing was there".

## Provenance

Every successful extraction is stamped with `_provenance` (model id, prompt
version, UTC timestamp) so an AI-extracted candidate can be re-verified and
recalled if a model version regresses — required by CLAUDE.md's "every stage
independently auditable".
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from ai.provider import AIProvider
from ai.prompts import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Bump when EXTRACTION_SYSTEM_PROMPT changes materially, so provenance on stored
# candidates records which prompt produced them.
PROMPT_VERSION = "2026-07-10.1"

DEFAULT_MODEL = "claude-3-5-sonnet-latest"
MAX_RETRIES = 3
BACKOFF_BASE_S = 1.0


class ExtractionConfigError(RuntimeError):
    """Raised for misconfiguration/structural failures that must fail loudly
    rather than degrade to a silent empty extraction (see module docstring)."""


class ClaudeProvider(AIProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        client=None,
        max_retries: int = MAX_RETRIES,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model or os.getenv("ONELIVE_CLAUDE_MODEL", DEFAULT_MODEL)
        self.max_tokens = max_tokens
        self._client = client
        self.max_retries = max_retries

    def _get_client(self):
        """Build the Anthropic client. Raises ExtractionConfigError if it cannot
        be built — a missing key or missing SDK is a deploy misconfiguration, not
        a transient miss, so it must be loud."""
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ExtractionConfigError(
                "ANTHROPIC_API_KEY is not set; refusing to silently return an empty "
                "extraction. Configure the key or use the stub provider explicitly.")
        try:
            import anthropic
        except ImportError as exc:
            raise ExtractionConfigError(
                "The `anthropic` package is not installed (see worker/requirements.txt). "
                "Refusing to silently degrade.") from exc
        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def extract_event_json(
        self,
        text: str,
        schema_json: dict,
        system_prompt: Optional[str] = None,
        *,
        audit_hook=None,
        source_name: Optional[str] = None,
    ) -> Optional[dict]:
        """Extract event fields present verbatim in `text`.

        Optional keyword-only `audit_hook(payload: dict)` lets the transient-
        failure path record an observable degradation event WITHOUT this module
        knowing anything about the database (the DB layer owns persistence). Both
        args default to None so this stays a drop-in for the stub's signature.
        """
        if not text or not text.strip():
            return None

        client = self._get_client()  # may raise ExtractionConfigError (loud)

        tool = {
            "name": "record_event_extraction",
            "description": (
                "Record only the event fields present VERBATIM in the source text. "
                "Leave any field null/empty if it is not explicitly stated."),
            "input_schema": schema_json,
        }

        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=system_prompt or EXTRACTION_SYSTEM_PROMPT,
                    tools=[tool],
                    tool_choice={"type": "tool", "name": "record_event_extraction"},
                    messages=[{"role": "user", "content": text}],
                )
                return self._stamp(self._extract_tool_input(resp))
            except Exception as exc:  # noqa: BLE001 — classified below
                if self._is_config_error(exc):
                    # Structural failure (e.g. unknown model, malformed schema):
                    # fail loudly, exactly like _fuzzy_match's 42883 branch.
                    logger.error(
                        "Claude extraction hit a structural/config error (%s); "
                        "refusing to silently degrade to an empty extraction.", exc)
                    raise ExtractionConfigError(str(exc)) from exc
                # Transient (429 / timeout / 5xx): back off and retry.
                last_exc = exc
                if attempt < self.max_retries:
                    sleep_s = BACKOFF_BASE_S * (2 ** (attempt - 1))
                    logger.warning(
                        "Claude extraction transient error (attempt %d/%d): %s; "
                        "retrying in %.1fs", attempt, self.max_retries, exc, sleep_s)
                    time.sleep(sleep_s)

        # Exhausted retries on a transient error -> safe degrade, but AUDITED so
        # it is never invisibly conflated with "no event in the text".
        logger.error("Claude extraction failed after %d attempts: %s; degrading to "
                     "manual/evidence path.", self.max_retries, last_exc)
        self._audit_degradation(audit_hook, source_name, last_exc)
        return None

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _is_config_error(exc: Exception) -> bool:
        """Classify structural/config errors (fail loudly) vs transient (retry).

        Uses HTTP status when the SDK exposes it: 429 and 5xx are transient;
        other 4xx (400 bad schema, 401/403 auth, 404 unknown model) are structural.
        Falls back to exception-type name heuristics when status is absent.
        """
        status = getattr(exc, "status_code", None)
        if status is not None:
            if status == 429 or status >= 500:
                return False  # transient
            if 400 <= status < 500:
                return True   # structural
        name = type(exc).__name__.lower()
        if any(k in name for k in ("authentication", "permission", "notfound",
                                   "badrequest", "invalidrequest", "unprocessable")):
            return True
        if any(k in name for k in ("ratelimit", "timeout", "connection",
                                   "apiconnection", "internalserver", "overloaded")):
            return False
        return False  # unknown -> treat as transient (retry then safe-degrade)

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

    def _stamp(self, data: Optional[dict]) -> Optional[dict]:
        """Attach extraction provenance so the candidate is re-verifiable."""
        if data is None:
            return None
        data = dict(data)
        data["_provenance"] = {
            "provider": "claude",
            "model": self.model,
            "prompt_version": PROMPT_VERSION,
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
            })
        except Exception as audit_exc:  # noqa: BLE001
            # Auditing must never mask the original degradation.
            logger.warning("failed to write ai_extraction_degraded audit row: %s",
                           audit_exc)
