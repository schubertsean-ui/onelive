"""Descriptor Foundry — shared types and the provider protocols.

Greppable summary: the Spark Line (UI Canon §4; Master Design Brief 65,
151-163) is a 3/5/7-word vivid descriptor of an act's WORK, AI-drafted at
tier C ONLY from the artist's OWN materials, and it is a SEPARATE trust
category from verified event facts — it never touches the event
extraction -> candidate -> gate -> promote path. This module holds the
value types and the two provider protocols the Foundry pipeline composes.

Trust posture (mirrors social/carousel/generator.py): a trust or format
violation raises DescriptorFoundryError and MUST propagate loud; an honest
"we cannot make one" (no source material, no candidate survives) is None,
never a fabricated stand-in (calm/honest-gaps law, UI Canon §1.7). The
invariant this pipeline upholds is gate-custodied publication ("AI never
publishes unvalidated"): its
output is gated by the Foundry (faithfulness + independent judge + golden-set
regression) BEFORE it can be shown; going live remains gate-custodied and
founder-controlled.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence, runtime_checkable

# The Spark Line is 3, 5, or 7 words — terse by construction (UI Canon §4).
VALID_WORD_COUNTS = (3, 5, 7)

# The Spark Line is VALIDATED here by the Foundry gate (faithfulness gate +
# independent judge + golden-set regression). That validation is what satisfies
# the gate-custodied-publication invariant ("AI never publishes unvalidated" —
# UI Canon §3; kickoff: satisfied
# by the gate, NOT by not building). Whether a validated line actually goes live
# to users is a further, gate-custodied and FOUNDER-CONTROLLED step (the
# auto-publish switch) outside this module — so status starts at `candidate`.
STATUS_CANDIDATE = "candidate"

# AI-drafted Spark Lines are tier C (UI Canon §4). Tiers A (artist's own
# words) and B (named critic) are HUMAN-sourced and do not flow through this
# generative pipeline — they are recorded directly with their attribution.
TIER_AI_DRAFTED = "C"


class DescriptorFoundryError(Exception):
    """A trust or format violation in Spark Line generation.

    Raised when the pipeline would otherwise emit something unfaithful,
    mis-shaped, or when its own custody preconditions are violated (e.g. a
    non-independent judge). Must propagate loud — never swallowed into a
    silently-empty descriptor.
    """


@dataclass(frozen=True)
class SourceMaterial:
    """The artist's OWN public materials a Spark Line may be composed from.

    `facts never invented` means every concrete factual token (proper noun,
    number) in a generated line must trace back to text present here. No
    third-party scraping, no inference — the same faithfulness discipline the
    Emotion Glyph holds to ("no description -> no glyph", §5).
    """

    artist: str
    # The artist's own words: bio lines, self-description, consented materials.
    texts: tuple[str, ...] = ()
    # Provenance: the source ids / urls the texts came from (audit trail).
    refs: tuple[str, ...] = ()

    def grounding_text(self) -> str:
        """The full corpus a line's facts are checked against — the artist's
        name plus every supplied text."""
        return " ".join((self.artist, *self.texts))

    def has_material(self) -> bool:
        """True only if there is real artist text to compose from. An artist
        name alone is not enough to draft a descriptor from (an honest gap,
        not an error)."""
        return any(t.strip() for t in self.texts)


@dataclass(frozen=True)
class DescriptorCandidate:
    """One generated candidate line, with the generation 'voice' that made it
    (provenance only — never a ranking input)."""

    text: str
    origin: str = ""


@dataclass(frozen=True)
class FoundryResult:
    """A gated Spark Line CANDIDATE awaiting the separate approval step.

    `status` is always STATUS_CANDIDATE from this module; `provenance` carries
    the full audit trail (source refs, prompt hash, both model ids, judge
    score, the raw candidate set) so any later review is fully traceable.
    """

    text: str
    tier: str
    status: str
    provenance: dict = field(default_factory=dict)


@runtime_checkable
class DescriptorGenerator(Protocol):
    """Generates and fuses candidate lines. `model_id` is stamped into
    provenance and used to enforce judge independence."""

    model_id: str

    def generate_candidates(
        self, material: SourceMaterial, n: int
    ) -> Sequence[str]:
        ...

    def fuse(self, winners: Sequence[str], material: SourceMaterial) -> str:
        """Fusion-of-N synthesis: combine the winning candidates' STYLE into
        one line, inventing no new facts (UI Canon §4; BRIEF:151-163)."""
        ...


@runtime_checkable
class DescriptorJudge(Protocol):
    """The INDEPENDENT judge — a different model than the generator (custody:
    the thing that writes a line never gets to bless it). Returns a
    faithfulness+quality score in [0.0, 1.0]."""

    model_id: str

    def score(self, text: str, material: SourceMaterial) -> float:
        ...
