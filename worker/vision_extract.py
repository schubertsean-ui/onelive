"""Vision extraction entrypoint — turns an IMAGE into an event_candidate row.

Founder-authorized 2026-07-29 ("Yes start capturing image only"). This is the
image counterpart of worker/ai_extract.py: it runs the vision provider
(ai/vision_provider.py) on one image (a flyer, poster, PDF page, or page
screenshot) and creates a candidate + evidence row through the SAME gate path
the text extractor uses. It imports worker.candidate_store ONLY — never
worker.promote / worker.gating — so the trust invariant holds by construction:
AI never publishes; a vision-extracted event still passes the human promotion
gate exactly like a text-extracted one.

Non-fabrication discipline is copied verbatim from ai_extract._shape_and_store_one
(the project convention against silent degradation): a schema-invalid extraction
is NOT blanked into something that looks like "no event found" — it is logged
loudly, tagged in provenance, and still recorded as a flagged candidate so ops
sees it. Datetime truth boundary R-021 applies unchanged.

Fail-closed OFF by default: extract_candidate_from_image raises VisionConfigError
unless ONELIVE_VISION_EXTRACTION_ENABLED=1 — the uncertified harness cannot fire
on a misconfiguration.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple
import copy
import logging

from pydantic import TypeAdapter, ValidationError

from ai.vision_provider import (
    VISION_EXTRACTION_SYSTEM_PROMPT,
    VisionConfigError,
    VisionProvider,
    vision_extraction_enabled,
)
from worker.ai_models import AIEventExtraction
from worker.candidate_store import create_candidate, add_evidence
from worker.datetime_normalize import (
    normalize_extracted_datetimes,
    preserve_discarded_claims,
)

logger = logging.getLogger(__name__)

_META_PREFIX = "_"

# Greppable marker: a page/image the model read but found NO event in. Ops grep
# for this to spot a flyer we mis-targeted or a decorative image with no event.
VISION_ZERO_EVENTS_MARKER = "VISION_EXTRACT_ZERO_EVENTS_IN_IMAGE"


class VisionExtractionError(RuntimeError):
    """A vision extraction produced NO result (provider degradation after
    retries, or blank input). Raised — never swallowed — so a failed read is a
    loud failure the caller's per-source isolation records, never a false
    'image had no event' candidate (the banned silent-degradation anti-pattern)."""


@dataclass
class VisionExtractionOutcome:
    """Result of extracting one image into a candidate.

    - ``candidate_id``: the candidate created (always exactly one — a real event
      or, when the image yielded nothing, a flagged empty candidate for ops, so
      the source is never silently dropped).
    - ``image_had_no_event``: True when the model read the image but found no
      event (a logo, menu, or unrelated photo) — the flagged-empty case.
    """
    candidate_id: str
    image_had_no_event: bool = False


def _split_meta(d: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    meta = {k: v for k, v in d.items() if k.startswith(_META_PREFIX)}
    fields = {k: v for k, v in d.items() if not k.startswith(_META_PREFIX)}
    return meta, fields


def extract_candidate_from_image(
    *,
    vision: VisionProvider,
    image_b64: str,
    media_type: str,
    source_class: str,
    source_name: str,
    source_url: str,
    sxsw_mode: bool = False,
    source_id: Optional[str] = None,
    _create: Callable[..., str] = create_candidate,
    _add: Callable[..., Any] = add_evidence,
) -> VisionExtractionOutcome:
    """Extract the event visible in one image and store it as a candidate.

    Fail-closed: raises :class:`VisionConfigError` unless vision extraction is
    explicitly enabled. Always records exactly one candidate (a flagged empty
    one when the image had no event), so an image is never silently dropped.

    The ``_create`` / ``_add`` seams keep the store/gate routing unit-testable
    without a live DB; production callers use the real defaults.
    """
    if not vision_extraction_enabled():
        raise VisionConfigError(
            "extract_candidate_from_image called while vision extraction is disabled — "
            "set ONELIVE_VISION_EXTRACTION_ENABLED=1. Fail-closed by design."
        )

    schema = AIEventExtraction.model_json_schema()
    raw = vision.extract_event_json_from_image(
        image_b64, media_type, schema, VISION_EXTRACTION_SYSTEM_PROMPT
    )
    if raw is None:
        # None = "the provider could NOT read this image" (a transient failure
        # after retries, or blank/empty input) — it is NEVER "the image had no
        # event". Conflating the two is the banned silent-degradation
        # anti-pattern (ai/claude_provider.py keeps None and {} distinct for
        # exactly this reason): a false `image_had_no_event` candidate would
        # assert we looked and saw nothing when we never successfully looked,
        # and could bury a real image-only event under a fake "empty" row. Fail
        # LOUD so the caller's per-source isolation records it, mirroring
        # worker/fetch/render_fetch.RenderError. Only a dict the provider
        # actually returns (empty or not) can mean "no event". (adversarial-
        # review #92, both openai seats.)
        raise VisionExtractionError(
            f"vision provider returned no result for source {source_name!r} "
            f"({source_url}): a failed or blank read, not a 'no event' finding — "
            "refusing to record a false image_had_no_event candidate."
        )
    meta, fields = _split_meta(raw)

    image_had_no_event = not any(v for v in fields.values())
    if image_had_no_event:
        logger.warning(
            "%s: source %r (%s) — the vision model read the image but found NO "
            "event (decorative image, logo, or unreadable). Recording a flagged "
            "empty candidate for ops rather than dropping it.",
            VISION_ZERO_EVENTS_MARKER, source_name, source_url,
        )
        prov = meta.get("_provenance")
        meta["_provenance"] = dict(prov) if isinstance(prov, dict) else {}
        meta["_provenance"]["image_had_no_event"] = True
        # AUTHORITATIVELY stamp the vision marker — never setdefault. A caller-
        # or model-supplied `_provenance.extractor` must NOT be able to survive
        # and disguise a vision candidate as certified-text extraction; ops rely
        # on this marker to tell the uncertified image path apart.
        meta["_provenance"]["extractor"] = "vision"

    candidate_id = _shape_and_store_one(
        fields,
        meta,
        source_id=source_id,
        source_name=source_name,
        source_url=source_url,
        source_class=source_class,
        media_type=media_type,
        sxsw_mode=sxsw_mode,
        _create=_create,
        _add=_add,
    )
    return VisionExtractionOutcome(
        candidate_id=candidate_id, image_had_no_event=image_had_no_event
    )


def _shape_and_store_one(
    event_fields: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    source_id: Optional[str],
    source_name: str,
    source_url: str,
    source_class: str,
    media_type: str,
    sxsw_mode: bool,
    _create: Callable[..., str],
    _add: Callable[..., Any],
) -> str:
    """Validate, R-021-normalize, and persist ONE vision event as candidate +
    evidence. Copies ai_extract._shape_and_store_one's anti-silent-degradation
    discipline so the two extraction paths never diverge on failure handling."""
    meta = copy.deepcopy(meta)
    # Every vision candidate is marked so ops can distinguish the uncertified
    # image path from the certified text path.
    prov = meta.get("_provenance")
    meta["_provenance"] = dict(prov) if isinstance(prov, dict) else {}
    # AUTHORITATIVE, not setdefault (adversarial-review #92, openai seats): a
    # model- or caller-supplied `_provenance.extractor` must never survive and
    # mislabel a vision candidate as certified-text extraction.
    meta["_provenance"]["extractor"] = "vision"

    adapter = TypeAdapter(AIEventExtraction)
    try:
        shaped = adapter.validate_python(event_fields).model_dump()
    except ValidationError as exc:
        logger.error(
            "Vision extraction for source %r produced schema-invalid fields; "
            "creating a flagged empty candidate for ops review rather than "
            "silently dropping it. Errors: %s", source_name, exc.errors()
        )
        shaped = AIEventExtraction().model_dump()
        meta["_provenance"]["validation_error"] = True

    # Truth-first (adversarial-review #92, openai seats + the vision prompt's
    # own rule 8): NEVER fabricate a city. Unlike the legacy text path, the
    # vision extractor leaves city NULL when the image does not evidence it —
    # inventing "Austin" would assert a location the flyer may not show and,
    # for the Austin->Lexington multi-city plan, would mislabel out-of-region
    # flyers. An absent city is the honest answer; ops (and the human promote
    # gate) see null, never a guessed place.

    # R-021: store a timestamp only when a full calendar date is evidenced;
    # time-only claims become NULL with the raw claim preserved in provenance.
    discarded_times = normalize_extracted_datetimes(shaped)
    if discarded_times:
        logger.warning(
            "vision source %r: datetime claim(s) refused (stored as NULL, raw + "
            "reason preserved in provenance): %s", source_name, discarded_times
        )
        if preserve_discarded_claims(meta, discarded_times):
            logger.error(
                "vision source %r: _provenance was malformed (non-dict) — replaced "
                "so the unstored datetime claims stay preserved; original kept "
                "under _provenance_malformed_original.", source_name
            )

    shaped.update(meta)

    candidate_id = _create(
        source_id=source_id,
        source_name=source_name,
        source_url=source_url,
        source_class=source_class,
        # The image itself is the raw material; there is no source text. Record a
        # short, honest marker instead of an empty string so the audit trail says
        # WHAT produced this candidate.
        raw_text=f"[vision extraction from image: {media_type}]",
        extracted=shaped,
        sxsw_mode=sxsw_mode,
    )
    _add(
        candidate_id=candidate_id,
        source_class=source_class,
        source_name=source_name,
        source_url=source_url,
        quote=f"[image evidence: {media_type} @ {source_url}]"[:500],
    )
    return candidate_id
