"""AI extraction entrypoint — turns raw source text into an event_candidate row.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/ai_extract.py)
"""
from typing import Optional
import inspect
import logging

from pydantic import TypeAdapter, ValidationError

from ai.prompts import EXTRACTION_SYSTEM_PROMPT
from ai.provider import AIProvider
from worker.ai_models import AIEventExtraction
from worker.candidate_store import create_candidate, add_evidence, record_ai_degradation
from worker.gating import multi_confirm_gate




logger = logging.getLogger(__name__)

# Meta keys the provider may attach (e.g. Claude provenance). These are NOT event
# fields, so they are separated out before pydantic validation (which would drop
# them) and merged back into the stored `extracted` jsonb afterwards, so the
# audit trail — which model/prompt/when produced this candidate — persists.
_META_PREFIX = "_"


def extract_candidate(
    *,
    ai: AIProvider,
    text: str,
    source_class: str,
    source_name: str,
    source_url: str,
    sxsw_mode: bool = False,
    source_id: Optional[str] = None,
) -> str:
    schema = AIEventExtraction.model_json_schema()
    # Pass the degradation audit hook only to providers that accept it (the real
    # Claude provider does; the stub keeps the minimal protocol signature). This
    # keeps the call a true drop-in across implementations.
    extract_kwargs = {"system_prompt": EXTRACTION_SYSTEM_PROMPT}
    try:
        params = inspect.signature(ai.extract_event_json).parameters
        if "audit_hook" in params:
            extract_kwargs["audit_hook"] = record_ai_degradation
        if "source_name" in params:
            extract_kwargs["source_name"] = source_name
    except (TypeError, ValueError):
        pass
    raw = ai.extract_event_json(text, schema, **extract_kwargs) or {}

    # Separate provider meta (e.g. _provenance) from event fields. Meta must not
    # go through the pydantic model (it would be silently dropped) but MUST be
    # preserved into the stored jsonb so the extraction stays auditable.
    meta = {k: v for k, v in raw.items() if k.startswith(_META_PREFIX)}
    event_fields = {k: v for k, v in raw.items() if not k.startswith(_META_PREFIX)}

    # Validate/shape. A validation failure is NOT silently blanked: an empty
    # candidate that looks identical to "no event found" would hide a real
    # extraction bug (the silent-degradation anti-pattern banned project-wide,
    # cf. resolve_entities._fuzzy_match). We log loudly, tag the candidate as a
    # malformed extraction in its provenance, and still create a review row so
    # ops can see it rather than losing it.
    adapter = TypeAdapter(AIEventExtraction)
    try:
        shaped = adapter.validate_python(event_fields).model_dump()
    except ValidationError as exc:
        logger.error("AI extraction for source %r produced schema-invalid fields; "
                     "creating a flagged empty candidate for ops review rather than "
                     "silently dropping it. Errors: %s", source_name, exc.errors())
        shaped = AIEventExtraction().model_dump()
        meta.setdefault("_provenance", {})
        if isinstance(meta["_provenance"], dict):
            meta["_provenance"]["validation_error"] = True
    # Default city when absent OR explicitly null (setdefault alone misses the
    # null case, which is the common one when the model finds no city).
    if not shaped.get("city"):
        shaped["city"] = "Austin"
    # Re-attach provider meta so it persists in the `extracted` jsonb column.
    shaped.update(meta)

    candidate_id = create_candidate(
        source_id=source_id,
        source_name=source_name,
        source_url=source_url,
        source_class=source_class,
        raw_text=text,
        extracted=shaped,
        sxsw_mode=sxsw_mode,
    )
    # Evidence from the originating source
    add_evidence(
        candidate_id=candidate_id,
        source_class=source_class,
        source_name=source_name,
        source_url=source_url,
        quote=text[:500]
    )
    # Gate update (stored by ops enqueue hook or API; keep here minimal)
    classes = [source_class]
    gate = multi_confirm_gate(classes, sxsw_mode=sxsw_mode)
    # No direct DB write here for gate fields; API/ops can recompute.
    return candidate_id
