"""Emotion Glyph engine — assignment + creator override, fail-closed.

Greppable summary: assign_glyph(description, mapper) returns a provenance-
stamped GlyphAssignment or None. The refusals ARE the product rules (UI Canon
§5): no description -> no glyph; mapper confidence below the floor -> no
glyph; the description must be the creator's OWN words (source_text_ref names
it — third-party scraping never enters this function's inputs by design).
apply_creator_override lets the creator replace/confirm the engine's pick
from the sanctioned lexicon — the override ALWAYS wins and is stamped as
such (override events are labeled data for the eval loop later).
"""
from __future__ import annotations

from worker.glyph.lexicon import BANNED_GLYPH_IDS, GLYPH_LEXICON, glyph_for
from worker.glyph.types import (
    EmotionMapper,
    GlyphAssignment,
    GlyphEngineError,
    MIN_MAPPER_CONFIDENCE,
    PlutchikCoords,
)

PROMPT_VERSION = "glyph-v1"


def assign_glyph(
    description: str | None,
    mapper: EmotionMapper,
    *,
    source_text_ref: str,
) -> GlyphAssignment | None:
    """Derive one glyph from the creator's own description, or honestly none.

    Returns None (never a stand-in) when: the description is absent/blank
    ("no description -> no glyph"), or the mapper's confidence is below
    MIN_MAPPER_CONFIDENCE (a wrong emotional read is worse than none).
    """
    if description is None or not description.strip():
        return None
    coords: PlutchikCoords = mapper.map(description)
    if coords.confidence < MIN_MAPPER_CONFIDENCE:
        return None
    glyph_id, aria = glyph_for(coords)
    if glyph_id in BANNED_GLYPH_IDS:
        # Unreachable while the lexicon is clean — kept as a loud tripwire so
        # a future lexicon edit can never route a rating-glyph to a listing.
        raise GlyphEngineError(f"banned glyph id reached assignment: {glyph_id}")
    return GlyphAssignment(
        glyph_id=glyph_id,
        aria_label=aria,
        plutchik=coords,
        source_text_ref=source_text_ref,
        model=mapper.name,
        prompt_version=PROMPT_VERSION,
        creator_override=False,
    )


def apply_creator_override(
    current: GlyphAssignment | None,
    override_glyph_id: str | None,
    *,
    source_text_ref: str,
) -> GlyphAssignment | None:
    """The creator's choice beats the engine, always (UI Canon §5).

    override_glyph_id None = the creator REMOVED the glyph -> None.
    A chosen id must come from the sanctioned lexicon and never the banned
    family — anything else refuses loud rather than storing an unreviewed
    symbol.
    """
    if override_glyph_id is None:
        return None
    if override_glyph_id in BANNED_GLYPH_IDS:
        raise GlyphEngineError(
            f"override refused: {override_glyph_id!r} is in the banned rating/endorsement family"
        )
    aria = GLYPH_LEXICON.get(override_glyph_id)
    if aria is None:
        raise GlyphEngineError(
            f"override refused: {override_glyph_id!r} is not in the sanctioned lexicon"
        )
    base = current.plutchik if current else PlutchikCoords(
        primary="trust", intensity="mild", confidence=1.0,
    )
    return GlyphAssignment(
        glyph_id=override_glyph_id,
        aria_label=aria,
        plutchik=base,
        source_text_ref=source_text_ref,
        model=current.model if current else "creator",
        prompt_version=current.prompt_version if current else PROMPT_VERSION,
        creator_override=True,
    )
