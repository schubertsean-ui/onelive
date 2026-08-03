"""Emotion Glyph lexicon — the curated, deterministic coordinate->glyph table.

Greppable summary: the ONLY place a Plutchik coordinate can become a glyph id
(brief appendix step 3: "deterministic glyph lookup — not free-form
generation"). 8 primaries x 3 intensities + a small sanctioned-dyad set.
Every entry carries an accessible text equivalent (WCAG non-text-content).
BANNED_GLYPH_IDS names the rating/endorsement family (fire/star/100/crown/
heart/thumbs) that must NEVER appear — a glyph must not create a visible
hierarchy between listings (discovery neutrality applies to feelings too).
Glyph ids are abstract tokens; the self-rendered SVG art set is a separate
design deliverable keyed by these ids (no art -> nothing renders — an honest
gap, never a placeholder or a native emoji).
"""
from __future__ import annotations

from worker.glyph.types import GlyphEngineError, PlutchikCoords

# The rating/endorsement family, banned by canon (UI Canon §5). Kept as data
# so the ban is testable and future edits cannot smuggle one in quietly.
BANNED_GLYPH_IDS = frozenset({
    "fire", "star", "hundred", "crown", "heart", "thumbs-up", "trophy", "medal",
})

# id -> aria label, keyed by (primary, intensity) — one glyph per coordinate,
# auditable and regression-testable. Labels describe emotional WEATHER, never
# quality ("mood: …", never "great/best/top").
_BY_COORD: dict[tuple[str, str], tuple[str, str]] = {
    ("joy", "mild"): ("ember-glow", "mood: warm, quietly glad"),
    ("joy", "base"): ("sunburst-soft", "mood: bright, uplifted"),
    ("joy", "intense"): ("fountain-light", "mood: euphoric, overflowing"),
    ("trust", "mild"): ("open-palm", "mood: easy, welcoming"),
    ("trust", "base"): ("linked-rings", "mood: warm, held"),
    ("trust", "intense"): ("rooted-oak", "mood: deeply grounded, devoted"),
    ("fear", "mild"): ("drawn-curtain", "mood: uneasy, hushed"),
    ("fear", "base"): ("moth-shadow", "mood: haunted, on edge"),
    ("fear", "intense"): ("thin-ice", "mood: menacing, breath held"),
    ("surprise", "mild"): ("raised-brow", "mood: curious, caught off guard"),
    ("surprise", "base"): ("sudden-bloom", "mood: wonder, eyes widening"),
    ("surprise", "intense"): ("split-sky", "mood: astonished, jolted awake"),
    ("sadness", "mild"): ("slow-rain", "mood: wistful, soft-hearted"),
    ("sadness", "base"): ("blue-hour", "mood: melancholy, tender ache"),
    ("sadness", "intense"): ("deep-well", "mood: grieving, heavy"),
    ("disgust", "mild"): ("turned-cheek", "mood: wry, unimpressed"),
    ("disgust", "base"): ("bitter-rind", "mood: sardonic, acid-edged"),
    ("disgust", "intense"): ("scorched-earth", "mood: caustic, confrontational"),
    ("anger", "mild"): ("struck-flint", "mood: simmering, restless"),
    ("anger", "base"): ("coiled-spring", "mood: charged, defiant"),
    ("anger", "intense"): ("storm-front", "mood: furious, cathartic"),
    ("anticipation", "mild"): ("first-light", "mood: quietly expectant"),
    ("anticipation", "base"): ("held-breath", "mood: yearning, leaning forward"),
    ("anticipation", "intense"): ("drawn-bow", "mood: electric, on the brink"),
}

# Sanctioned dyads (brief appendix step 2: "love = joy+trust", "awe =
# fear+surprise", …) — a SMALL set on purpose; an unsanctioned pair falls back
# to the primary's own glyph rather than inventing a blend.
_DYADS: dict[frozenset[str], tuple[str, str]] = {
    frozenset({"joy", "trust"}): ("twin-flames", "mood: loving, close"),
    frozenset({"fear", "surprise"}): ("cathedral-dark", "mood: awe, small before something vast"),
    frozenset({"joy", "anticipation"}): ("dawn-chorus", "mood: optimistic, alight"),
    frozenset({"sadness", "trust"}): ("shared-umbrella", "mood: tender sorrow, together"),
    frozenset({"anticipation", "fear"}): ("cliff-edge", "mood: thrill, delicious dread"),
}

# The full lexicon as an auditable mapping: glyph_id -> aria label.
GLYPH_LEXICON: dict[str, str] = {
    **{gid: label for gid, label in _BY_COORD.values()},
    **{gid: label for gid, label in _DYADS.values()},
}


def glyph_for(coords: PlutchikCoords) -> tuple[str, str]:
    """Deterministic lookup: coords -> (glyph_id, aria_label).

    A sanctioned dyad wins when a secondary is present; an unsanctioned pair
    deliberately resolves to the PRIMARY's glyph (never an invented blend).
    Raises loud if the table itself is inconsistent — that is a data defect,
    not a runtime condition to paper over.
    """
    if coords.secondary is not None:
        dyad = _DYADS.get(frozenset({coords.primary, coords.secondary}))
        if dyad is not None:
            return dyad
    entry = _BY_COORD.get((coords.primary, coords.intensity))
    if entry is None:
        raise GlyphEngineError(
            f"lexicon has no glyph for {coords.primary}/{coords.intensity} — "
            "the coordinate table is incomplete (data defect, fix the lexicon)"
        )
    return entry
