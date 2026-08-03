"""Emotion Glyph engine (UI Canon §5; Master Design Brief appendix; G-EG
RATIFIED 2026-08-03 — docs/memory/decisions/
2026-08-03_frictionless-nav-geg-monitoring-ratified.md).

Greppable summary: deterministic Plutchik-coordinates -> curated-lexicon
lookup that assigns ONE emotional-weather glyph id to an act, derived ONLY
from the creator's OWN description ("no description -> no glyph"). Creator
override always beats the engine. Zero spend: the coordinate MAPPER is a
protocol (a real model provider lands later behind founder-capped spend);
everything here runs offline. Display-side art is a separate design
deliverable — this engine deals in glyph IDs + accessible text equivalents,
and nothing renders until both the art set and real creator descriptions
exist (honest gap, never a placeholder).
"""
from worker.glyph.engine import assign_glyph, apply_creator_override
from worker.glyph.lexicon import GLYPH_LEXICON, BANNED_GLYPH_IDS, glyph_for
from worker.glyph.types import (
    EmotionMapper,
    FakeEmotionMapper,
    GlyphAssignment,
    GlyphEngineError,
    PlutchikCoords,
)

__all__ = [
    "assign_glyph",
    "apply_creator_override",
    "GLYPH_LEXICON",
    "BANNED_GLYPH_IDS",
    "glyph_for",
    "EmotionMapper",
    "FakeEmotionMapper",
    "GlyphAssignment",
    "GlyphEngineError",
    "PlutchikCoords",
]
