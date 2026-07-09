"""AI extraction entrypoint — turns raw source text into an event_candidate row.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/ai_extract.py)
"""
import os
from typing import Optional
from pydantic import TypeAdapter

from ai.provider import AIProvider
from ai.prompts import EXTRACTION_SYSTEM_PROMPT
from worker.ai_models import AIEventExtraction
from worker.candidate_store import create_candidate, add_evidence
from worker.gating import multi_confirm_gate


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
    extracted = ai.extract_event_json(text, schema, system_prompt=EXTRACTION_SYSTEM_PROMPT) or {}
    # Validate/shape
    adapter = TypeAdapter(AIEventExtraction)
    try:
        shaped = adapter.validate_python(extracted).model_dump()
    except Exception:
        shaped = AIEventExtraction().model_dump()
    shaped.setdefault("city", "Austin")

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
