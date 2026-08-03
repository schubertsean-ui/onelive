"""Emotion Glyph engine — value types and the mapper protocol.

Greppable summary: PlutchikCoords (8 primaries x 3 intensities + an optional
secondary for sanctioned dyads), GlyphAssignment (id + coords + provenance +
creator_override), the EmotionMapper protocol (description -> coords; the
REAL model-backed mapper is a later, founder-capped build), and a
deterministic FakeEmotionMapper for offline tests. Trust posture mirrors
worker/descriptor/types.py: a rule violation raises GlyphEngineError loud;
an honest "no glyph" is None, never a stand-in (UI Canon §1.7).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Plutchik's eight primary emotions (brief appendix, step 2).
PRIMARY_EMOTIONS = (
    "joy", "trust", "fear", "surprise",
    "sadness", "disgust", "anger", "anticipation",
)

# Three intensity levels per primary (mild < base < intense).
INTENSITIES = ("mild", "base", "intense")

# Below this mapper confidence the engine assigns NOTHING — a wrong emotional
# read is worse than none (same floor philosophy as the Foundry judge).
MIN_MAPPER_CONFIDENCE = 0.6


class GlyphEngineError(ValueError):
    """A rule violation (banned glyph, unknown emotion, bad override) — loud."""


@dataclass(frozen=True)
class PlutchikCoords:
    primary: str
    intensity: str
    secondary: str | None = None  # present only for a sanctioned dyad
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.primary not in PRIMARY_EMOTIONS:
            raise GlyphEngineError(f"unknown primary emotion: {self.primary!r}")
        if self.intensity not in INTENSITIES:
            raise GlyphEngineError(f"unknown intensity: {self.intensity!r}")
        if self.secondary is not None and self.secondary not in PRIMARY_EMOTIONS:
            raise GlyphEngineError(f"unknown secondary emotion: {self.secondary!r}")
        if not (0.0 <= self.confidence <= 1.0):
            raise GlyphEngineError(f"confidence out of range: {self.confidence!r}")


@dataclass(frozen=True)
class GlyphAssignment:
    """One assigned glyph, carrying full provenance (brief appendix step 6)."""

    glyph_id: str
    aria_label: str  # WCAG non-text-content equivalent, e.g. "mood: slow-burning, tender"
    plutchik: PlutchikCoords
    source_text_ref: str  # which creator text produced it — never a third-party scrape
    model: str  # mapper identity ("fake:keyword-v1" until the real provider lands)
    prompt_version: str
    creator_override: bool = False


@runtime_checkable
class EmotionMapper(Protocol):
    """description -> PlutchikCoords. The REAL implementation calls the model
    layer (spend; founder-capped, routed via tools/model_router.py) — not built
    here. Mappers never see anything but the creator's own words."""

    name: str

    def map(self, description: str) -> PlutchikCoords: ...


# Deterministic keyword mapper for tests and offline runs — NOT a product
# heuristic (a real act's coords come from the model mapper under the same
# gate). Deliberately tiny; unknown text maps to low confidence so the engine
# refuses (fail-closed), which is itself the property under test.
_KEYWORDS: dict[str, tuple[str, str]] = {
    "tender": ("joy", "mild"),
    "euphoric": ("joy", "intense"),
    "haunted": ("fear", "base"),
    "menace": ("fear", "intense"),
    "melancholy": ("sadness", "base"),
    "furious": ("anger", "intense"),
    "wonder": ("surprise", "base"),
    "yearning": ("anticipation", "base"),
    "warm": ("trust", "base"),
}


@dataclass(frozen=True)
class FakeEmotionMapper:
    name: str = "fake:keyword-v1"

    def map(self, description: str) -> PlutchikCoords:
        text = description.lower()
        for word, (primary, intensity) in _KEYWORDS.items():
            if word in text:
                return PlutchikCoords(primary=primary, intensity=intensity, confidence=0.9)
        # Honest ignorance: a description the mapper cannot read yields low
        # confidence, and the engine assigns nothing.
        return PlutchikCoords(primary="trust", intensity="mild", confidence=0.0)
