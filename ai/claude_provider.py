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
import hashlib
import html
import json
import logging
import os
import time

from ai.prompts import EXTRACTION_SYSTEM_PROMPT
from ai.provider import AIProvider

logger = logging.getLogger(__name__)

# Bump when EXTRACTION_SYSTEM_PROMPT changes materially, so provenance on stored
# candidates records which prompt produced them.
PROMPT_VERSION = "2026-07-17.10"

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
        if not _exam_entrypoint_allowed():
            raise ExtractionConfigError(
                "exam_mode is only available inside the exam program "
                "(python -m ai.golden_exam) — this process's entrypoint "
                "is not it. The channel bypasses the "
                "extraction ratification gate; production processes are "
                "excluded by WHAT the process is, not by what its code "
                "looks like."
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
    elif _router.EXTRACTION_THRESHOLD_RATIFIED is not True:
        # Exactly boolean True — never truthiness (r26 blocker): this is a
        # fail-closed auth gate, and a misconfigured value like the STRING
        # "False" or "yes" is truthy. Anything but the bool True (including
        # any truthy non-bool) is a closed gate, loudly.
        raise ExtractionConfigError(
            "extraction is fail-closed until the golden-set gate ships and "
            "passes (docs/RECORD.md R-013; bar ratified <=1% per R-006) — "
            "an explicit model argument does not bypass the gate, and the "
            "ratification flag opens it only as the exact boolean True."
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


def _exam_entrypoint_allowed() -> bool:
    """Runtime confinement of the exam channel — a PROCESS-ENTRYPOINT
    boundary (evaluator r8 replaced the earlier stack-filename walk, which
    was spoofable via compile(..., filename=...)).

    Authorization is a property of how this PROCESS was started, not of
    the shape of the calling code. Exactly ONE entrypoint qualifies: the
    exam program itself — `python -m ai.golden_exam` makes the
    interpreter's __main__ module spec literally "ai.golden_exam". A
    worker/Celery/uvicorn/cron process can never satisfy this without
    re-exec-ing AS the exam program — at which point it is not sneaking
    past the gate, it IS the gate's instrument.
    (Tests of this channel simulate this same entrypoint by monkeypatching
    __main__.__spec__ — there is deliberately NO test-runner escape hatch
    here; evaluator r11 removed the PYTEST_CURRENT_TEST branch as a
    production-spoofable env-var backdoor.)

    Filename spoofing (compile with a forged filename, wrappers, import
    games) does nothing to this signal. Threat model, stated honestly:
    CPython offers no in-process capability sealing — code that is ALREADY
    hostile inside this process could setattr the ratification flag itself
    and would never need this channel. This boundary therefore targets
    what is real: ACCIDENTAL production use (a worker constructing an
    exam-mode provider fails loudly, whatever its code looks like), with
    adversarial code held instead by the layers that actually bind it —
    the trust_gate CI scans on every PR, the mandatory evaluator review,
    and the pipeline invariant that no AI output reaches the public feed
    without the human promotion gate.
    """
    import __main__
    spec_name = getattr(getattr(__main__, "__spec__", None), "name", "") or ""
    return spec_name == "ai.golden_exam"


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
                return self._stamp(self._extract_tool_input(resp),
                                   used_prompt=system_prompt or EXTRACTION_SYSTEM_PROMPT)
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

    @staticmethod
    def _decode_entities(data: Optional[dict]) -> Optional[dict]:
        """Normalize HTML-entity escaping in model output, deterministically.

        Models sometimes HTML-escape string values ('&' -> '&amp;') even
        when the source text is plain (observed: claude-opus-4-8, exam
        cycle 8, g002/g030). Encoding artifacts are not content; a single
        html.unescape pass at the provider boundary fixes every field the
        same way — deterministic code over prompt instructions.

        URLs included, deliberately (evaluator r12 nit, documented): the
        verbatim-links rule targets INVENTED links, not encodings — a
        query string the model returns as 'a=1&amp;b=2' is the same URL
        the source wrote as 'a=1&b=2', and query-string ampersands are
        exactly where this artifact appears most. Unescaping is applied
        once, so already-plain text is a no-op."""
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

    @staticmethod
    def _drop_redundant_title(data: Optional[dict]) -> Optional[dict]:
        """Null a title that merely duplicates an artist or the venue.

        Every model tier tested (exam cycles 3-9) sometimes promotes the
        headline act or venue to `title` — the industry prior that every
        listing has a title. A title equal to an artist/venue name carries
        zero information the other fields don't already assert, and would
        render as a duplicated line on the event card (design brief: the
        artist is its own line). Deterministic and case-insensitive; a
        DISTINCT title is never touched."""
        if not data or not isinstance(data.get("title"), str):
            return data
        t = data["title"].strip().casefold()
        names = [a for a in (data.get("artist_names") or []) if isinstance(a, str)]
        if isinstance(data.get("venue_name"), str):
            names.append(data["venue_name"])
        if any(t == n.strip().casefold() for n in names):
            data = dict(data)
            # Auditability (r19 nit): normalization is never silent — the
            # pre-normalized value rides along in provenance debug.
            data["_normalized"] = {"dropped_redundant_title": data["title"]}
            data["title"] = None
        return data

    def _stamp(self, data: Optional[dict], used_prompt: Optional[str] = None) -> Optional[dict]:
        """Attach extraction provenance so the candidate is re-verifiable.

        `used_prompt` is the system prompt that actually produced this
        output (r15 nit: exam runs can inject a subject prompt via
        --prompt-file, and provenance must hash what RAN, not what this
        checkout's ai/prompts.py happens to contain)."""
        if data is None:
            return None
        data = self._decode_entities(data)
        data = self._drop_redundant_title(data)
        data["_provenance"] = {
            "provider": "claude",
            "model": self.model,
            "prompt_version": PROMPT_VERSION,
            # Content hash catches silent prompt drift BETWEEN version bumps
            # (po harvest, friction entry #2; evaluator r7 concurred): the
            # version says what we intended, the hash says what actually ran.
            "prompt_sha256": hashlib.sha256(
                (used_prompt or EXTRACTION_SYSTEM_PROMPT).encode("utf-8")).hexdigest(),
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
