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
from datetime import datetime, timezone
from typing import Optional
import json
import logging
import os
import pathlib
import time

from ai.prompts import EXTRACTION_SYSTEM_PROMPT
from ai.provider import AIProvider

logger = logging.getLogger(__name__)

# Bump when EXTRACTION_SYSTEM_PROMPT changes materially, so provenance on stored
# candidates records which prompt produced them.
PROMPT_VERSION = "2026-07-15.5"

MAX_RETRIES = 3
BACKOFF_BASE_S = 1.0


def _resolve_extraction_model(explicit: Optional[str], exam_mode: bool = False) -> str:
    """Resolve the extraction model THROUGH the routing gate (single source).

    The trust invariant lives at this entry point, not only in the tool
    (evaluator findings, PR #21 rounds 1-2 — same class as the reviewer-
    slot fix in PR #14), and it gates EVERY construction path: the R-013
    block (no extraction until the golden-set gate ships and passes; bar
    ratified <=1% per R-006) is checked FIRST, so an explicit `model=`
    argument cannot bypass it — explicit selects WHICH model once
    extraction is permitted at all, never WHETHER. The flag is read from
    the live module state so the Step 6 flip (and test fixtures that
    legitimately open the gate to exercise provider mechanics) take
    effect without import-order games.

    With no explicit model, resolution delegates to resolve_model(
    "extraction"): env chain ONELIVE_MODEL_EXTRACTION > legacy
    ONELIVE_CLAUDE_MODEL > policy default, present-but-empty rejected,
    id single-sourced so a stale local default cannot drift again (the
    retired claude-3-5-sonnet-latest 404'd on the first real run).
    Explicit values fail closed on empty/whitespace — blank is
    misconfiguration, never "use the default".
    """
    import tools.model_router as _router
    if exam_mode:
        if not _exam_caller_allowed():
            raise ExtractionConfigError(
                "exam_mode may only be invoked from ai/golden_exam.py or "
                "tests/ — runtime caller verification failed (this channel "
                "bypasses the extraction ratification gate; production paths "
                "are mechanically excluded, not merely policy-excluded)."
            )
        # THE EXAM CHANNEL — deliberately narrow (R-013's own measurement
        # instrument): the golden-set runner must exercise the REAL provider
        # path against a candidate model BEFORE the gate can open, so this
        # bypasses ONLY the ratification-flag check. Constraints, all
        # enforced: an explicit model is REQUIRED (no policy fallback — the
        # exam names its candidate); blank still fails closed below; the
        # string `exam_mode=True` is allowed ONLY in ai/golden_exam.py and
        # tests/ (tools/trust_gate.py invariant), so no pipeline code can
        # reach for it; and the runner imports no candidate-store/promote
        # code, so exam output cannot touch the pipeline or DB.
        if explicit is None:
            raise ExtractionConfigError(
                "exam_mode requires an explicit candidate model — the exam "
                "names what it measures; there is no policy fallback."
            )
    elif not _router.EXTRACTION_THRESHOLD_RATIFIED:
        raise ExtractionConfigError(
            "extraction is fail-closed until the golden-set gate ships and "
            "passes (docs/RECORD.md R-013; bar ratified <=1% per R-006) — "
            "an explicit model argument does not bypass the gate."
        )
    if explicit is not None:
        if not explicit.strip():
            raise ExtractionConfigError(
                "explicit model argument is empty/whitespace — pass a real "
                "model id or pass None to use the routing policy."
            )
        return explicit.strip()
    try:
        return _router.resolve_model("extraction")
    except (KeyError, ValueError) as exc:
        raise ExtractionConfigError(str(exc)) from exc


def _exam_caller_allowed() -> bool:
    """Runtime confinement of the exam channel (evaluator, PR #25 r3+r5).

    Two conditions, both required, checked over the WHOLE call stack —
    not just the nearest frame (r5 closed the wrapper hole: production
    code calling ai.golden_exam.main() would make the nearest external
    frame look like the allowlisted runner):

    1. The first non-own frame must be the golden-exam runner or test
       code (who is directly constructing the provider).
    2. NO frame anywhere in the stack may come from this repo's worker/
       or api/ trees (who transitively initiated the call). Pipeline code
       cannot reach the exam channel even by driving the runner.

    Fail-closed: any violation gets ExtractionConfigError even if it found
    a syntactic disguise past the static trust_gate scan (defense in depth:
    this is layer 1 at runtime; the text scan — which also flags any
    golden_exam reference outside the allowlist — remains layer 2 in CI).
    """
    import inspect
    own = "claude_provider.py"
    repo_root = str(pathlib.Path(__file__).resolve().parent.parent).replace("\\", "/")
    direct_caller_ok = False
    seen_external = False
    for frame in inspect.stack():
        fn = frame.filename.replace("\\", "/")
        if fn.endswith(own):
            continue
        # Condition 2: repo pipeline frames are banned ANYWHERE in the stack.
        # Scoped to this repo's tree so site-packages paths that happen to
        # contain /api/ (SDK internals) cannot false-positive.
        if fn.startswith(repo_root + "/worker/") or fn.startswith(repo_root + "/api/"):
            return False
        if not seen_external:
            seen_external = True
            direct_caller_ok = (
                fn.endswith("ai/golden_exam.py")
                or "/tests/" in fn
                or "/_pytest/" in fn or "/pytest" in fn
            )
            if not direct_caller_ok:
                return False
    return direct_caller_ok


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
        *,
        exam_mode: bool = False,
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.exam_mode = exam_mode
        self.model = _resolve_extraction_model(model, exam_mode=exam_mode)
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
        """Extract event fields literally present in `text`.

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
                "Record only the event fields LITERALLY present in the source text. "
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
        if self.exam_mode:
            # Exam output must be unmistakable as exam output — if a row with
            # this marker ever appears in the candidate store, something has
            # violated the exam channel's no-pipeline constraint.
            data["_provenance"]["exam_mode"] = True
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
