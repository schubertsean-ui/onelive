"""The mechanical faithfulness gate — the load-bearing trust piece.

Greppable summary: BEFORE any independent-judge (semantic) pass, every Spark
Line clears these deterministic checks: (1) word count in {3,5,7}; (2) no
marketing or trust language (the "competence shown, not told" and no-badge
rules, BRIEF:48,65, UI Canon §8); (3) `facts never invented` — every proper
noun and every number in the line must appear in the artist's OWN source
materials; (4) fail-closed on empty source (no material -> no line). This
gate catches CONCRETE fabricated facts (an invented collaborator, place,
year, genre); the independent judge catches semantic drift the mechanics
cannot see. Both must pass.
"""
from __future__ import annotations

import re

from .types import SourceMaterial, DescriptorFoundryError, VALID_WORD_COUNTS

# Marketing / trust language a tier-C Spark Line must never use. The interface
# never tells the reader something is good or verified; it shows the work
# (UI Canon §1.4, §8). Superlatives and hype are exactly what the Spark Line
# replaces with concrete sensory language.
BANNED_PHRASES = (
    # trust-claim words (no badges, ever — §8)
    "verified", "confirmed", "trusted", "official", "authentic", "legit",
    # marketing superlatives / hype
    "best", "greatest", "amazing", "incredible", "unforgettable", "must-see",
    "must see", "legendary", "iconic", "sensational", "world-class",
    "world class", "critically acclaimed", "acclaimed", "award-winning",
    "award winning", "sold out", "hottest", "epic", "phenomenal", "stunning",
    "breathtaking", "jaw-dropping", "mind-blowing", "next-level",
)

# Common function words that are allowed to appear capitalized (e.g. at the
# start of a fragment) without needing to be grounded — they are never facts.
_COMMON_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "of", "to", "for",
    "with", "from", "by", "as", "so", "no", "not", "its", "their", "his",
    "her", "our", "your", "you", "we", "it", "all", "one", "two",
}

# A "word" for grounding: letters/digits plus internal apostrophes and hyphens.
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-]*")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _grounding_set(material: SourceMaterial) -> set[str]:
    return {t.lower() for t in _tokens(material.grounding_text())}


def _has_digit(token: str) -> bool:
    return any(c.isdigit() for c in token)


def _is_proper_noun(token: str) -> bool:
    # Capitalized and not a common function word. Fragments like
    # "brass. menace. amen." carry no proper nouns and pass trivially — their
    # faithfulness to the vibe is the judge's job, not the mechanics'.
    return token[:1].isupper() and token.lower() not in _COMMON_WORDS


def assert_faithful(text: str, material: SourceMaterial) -> None:
    """Raise DescriptorFoundryError if `text` violates any mechanical rule.

    Fail-closed: an empty source corpus refuses outright — a descriptor with
    nothing to ground it is exactly what "facts never invented" forbids.
    """
    stripped = text.strip()
    if not stripped:
        raise DescriptorFoundryError("empty Spark Line")

    words = stripped.split()
    n = len(words)
    if n not in VALID_WORD_COUNTS:
        raise DescriptorFoundryError(
            f"Spark Line must be {' / '.join(map(str, VALID_WORD_COUNTS))} "
            f"words; got {n}: {text!r}"
        )

    low = stripped.lower()
    for phrase in BANNED_PHRASES:
        if re.search(r"\b" + re.escape(phrase) + r"\b", low):
            raise DescriptorFoundryError(
                f"banned marketing/trust phrase {phrase!r} in Spark Line: "
                f"{text!r} — the Spark Line shows the work, never rates it"
            )

    grounding = _grounding_set(material)
    if not grounding:
        raise DescriptorFoundryError(
            "no source material to ground a Spark Line — refusing to invent "
            "one (facts never invented)"
        )

    for tok in _tokens(stripped):
        number = _has_digit(tok)
        proper = _is_proper_noun(tok)
        if (number or proper) and tok.lower() not in grounding:
            kind = "number" if number else "proper noun"
            raise DescriptorFoundryError(
                f"ungrounded {kind} {tok!r} in Spark Line {text!r} — not "
                "present in the artist's own materials (facts never invented)"
            )


def is_faithful(text: str, material: SourceMaterial) -> bool:
    """Non-raising form, for filtering a candidate set."""
    try:
        assert_faithful(text, material)
        return True
    except DescriptorFoundryError:
        return False


# --- checklist scoring (the pairwise-knockout ordering) ----------------------
# A deterministic, model-free heuristic used ONLY to order faithful candidates
# for the knockout — the real quality bar is the independent judge. It rewards
# concrete, varied, sensory language and gentle typographic play, and it never
# reads any paid or ranking signal (there is none on this path).

def checklist_score(text: str, material: SourceMaterial) -> float:
    toks = _tokens(text)
    if not toks:
        return 0.0
    distinct_concrete = {
        t.lower() for t in toks if t.lower() not in _COMMON_WORDS
    }
    concreteness = len(distinct_concrete)
    variety = len({t.lower() for t in toks}) / len(toks)  # 1.0 if all distinct
    play = 0.5 if any(c in text for c in ".;——:!") else 0.0
    return concreteness + variety + play
