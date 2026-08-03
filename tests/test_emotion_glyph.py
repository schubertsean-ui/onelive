"""Emotion Glyph engine tests — every refusal path is a product rule.

Covers (UI Canon §5 / brief appendix / G-EG ratification 2026-08-03):
no-description -> no glyph; low mapper confidence -> no glyph; deterministic
same-input-same-output; provenance stamped; sanctioned dyads resolve, an
unsanctioned pair falls back to the primary (never an invented blend); the
banned rating/endorsement family is absent from the lexicon and refused on
override; creator override always wins and removal wins too; every lexicon
entry carries an accessible "mood:" label that never claims quality.
"""
from __future__ import annotations

import pytest

from worker.glyph import (
    BANNED_GLYPH_IDS,
    FakeEmotionMapper,
    GLYPH_LEXICON,
    GlyphEngineError,
    PlutchikCoords,
    apply_creator_override,
    assign_glyph,
    glyph_for,
)

MAPPER = FakeEmotionMapper()
REF = "claim-flow:describe-your-sound:test"


def test_no_description_means_no_glyph():
    assert assign_glyph(None, MAPPER, source_text_ref=REF) is None
    assert assign_glyph("", MAPPER, source_text_ref=REF) is None
    assert assign_glyph("   ", MAPPER, source_text_ref=REF) is None


def test_low_confidence_mapping_assigns_nothing():
    # The fake mapper returns confidence 0.0 for text it cannot read — the
    # engine must refuse rather than guess an emotion.
    assert assign_glyph("zxqv unreadable text", MAPPER, source_text_ref=REF) is None


def test_assignment_is_deterministic_and_provenance_stamped():
    a = assign_glyph("slow and tender porch songs", MAPPER, source_text_ref=REF)
    b = assign_glyph("slow and tender porch songs", MAPPER, source_text_ref=REF)
    assert a is not None and b is not None
    assert a == b  # same words -> same glyph, always (auditable)
    assert a.glyph_id in GLYPH_LEXICON
    assert a.aria_label.startswith("mood:")
    assert a.source_text_ref == REF
    assert a.model == MAPPER.name
    assert a.creator_override is False


def test_different_emotions_map_to_different_glyphs():
    tender = assign_glyph("tender ballads", MAPPER, source_text_ref=REF)
    menace = assign_glyph("brass and menace", MAPPER, source_text_ref=REF)
    assert tender is not None and menace is not None
    assert tender.glyph_id != menace.glyph_id


def test_sanctioned_dyad_resolves_and_unsanctioned_falls_back_to_primary():
    love = glyph_for(PlutchikCoords(primary="joy", secondary="trust", intensity="base", confidence=1.0))
    assert love[0] == "twin-flames"
    # joy+disgust is not a sanctioned dyad -> the PRIMARY's own glyph, never a blend.
    fallback = glyph_for(PlutchikCoords(primary="joy", secondary="disgust", intensity="base", confidence=1.0))
    assert fallback == glyph_for(PlutchikCoords(primary="joy", intensity="base", confidence=1.0))


def test_every_primary_x_intensity_has_a_glyph_with_a_mood_label():
    from worker.glyph.types import INTENSITIES, PRIMARY_EMOTIONS
    seen: set[str] = set()
    for p in PRIMARY_EMOTIONS:
        for i in INTENSITIES:
            gid, label = glyph_for(PlutchikCoords(primary=p, intensity=i, confidence=1.0))
            assert label.startswith("mood:"), f"{gid}: aria label must describe weather, not quality"
            seen.add(gid)
    assert len(seen) == 24  # one distinct glyph per coordinate — no visible hierarchy


def test_lexicon_labels_never_claim_quality_or_rating():
    for gid, label in GLYPH_LEXICON.items():
        for banned_word in ("best", "top", "great", "verified", "confirmed", "trusted"):
            assert banned_word not in label.lower(), f"{gid}: {label!r}"


def test_banned_rating_family_is_absent_from_the_lexicon():
    assert not (set(GLYPH_LEXICON) & BANNED_GLYPH_IDS)


def test_creator_override_wins_and_is_stamped():
    engine_pick = assign_glyph("haunted organ drones", MAPPER, source_text_ref=REF)
    assert engine_pick is not None
    over = apply_creator_override(engine_pick, "blue-hour", source_text_ref=REF)
    assert over is not None
    assert over.glyph_id == "blue-hour"
    assert over.creator_override is True


def test_creator_removal_wins_too():
    engine_pick = assign_glyph("haunted organ drones", MAPPER, source_text_ref=REF)
    assert apply_creator_override(engine_pick, None, source_text_ref=REF) is None


def test_override_refuses_banned_and_unknown_ids_loudly():
    with pytest.raises(GlyphEngineError):
        apply_creator_override(None, "fire", source_text_ref=REF)
    with pytest.raises(GlyphEngineError):
        apply_creator_override(None, "not-a-real-glyph", source_text_ref=REF)


def test_coords_validate_their_own_inputs():
    with pytest.raises(GlyphEngineError):
        PlutchikCoords(primary="rage", intensity="base")
    with pytest.raises(GlyphEngineError):
        PlutchikCoords(primary="joy", intensity="extreme")
    with pytest.raises(GlyphEngineError):
        PlutchikCoords(primary="joy", intensity="base", confidence=1.5)
