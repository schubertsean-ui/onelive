"""The Descriptor Foundry pipeline (UI Canon §4; BRIEF:151-163).

Six candidates -> pairwise knockout vs the checklist -> fusion-of-N synthesis
(style new, facts never) -> INDEPENDENT judge -> provenance stamp. This IS the
validation that satisfies "AI never publishes UNVALIDATED" (UI Canon §3;
kickoff: satisfied by the gate, not by not building) — no single-shot
generation ever reaches a fan. The output is a `candidate`; whether a validated
line goes live is a further, gate-custodied and founder-controlled step (the
auto-publish switch) outside this module.

Honest-gap contract: the pipeline returns None (never a fabricated stand-in)
when it cannot produce a faithful, good-enough line — no source material, no
candidate survives the faithfulness gate, or the fused line does not clear the
independent judge. It RAISES DescriptorFoundryError only for genuine trust
defects: a fused line that is itself unfaithful (that is our bug, and shipping
it would break "facts never invented"), or a non-independent judge (custody).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .gate import assert_faithful, checklist_score, is_faithful
from .types import (
    DescriptorFoundryError,
    DescriptorGenerator,
    DescriptorJudge,
    FoundryResult,
    STATUS_CANDIDATE,
    SourceMaterial,
    TIER_AI_DRAFTED,
)

# The Descriptor Foundry canon (BRIEF:151-163): six candidates.
N_CANDIDATES = 6
# How many faithful survivors feed the fusion synthesis.
N_WINNERS = 3
# The independent judge's faithfulness+quality bar a candidate must clear.
JUDGE_THRESHOLD = 0.7

PROMPT_VERSION = "spark_line_v1"
FOUNDRY_VERSION = "1"

# The instruction the generator is composed under. Its SHA is stamped into
# provenance (mirrors the worker extraction convention: prompt_sha256 catches
# silent prompt drift between version bumps).
GENERATOR_PROMPT = (
    "Compose a vivid, sensory Spark Line of EXACTLY 3, 5, or 7 words that "
    "describes the ACT'S WORK, using ONLY facts present in the supplied "
    "materials. Fragments, punctuation, and typographic play are welcome; a "
    "full sentence is not. Never use marketing or trust language. Never "
    "invent a collaborator, place, year, genre, or any fact not in the "
    "materials."
)


def _prompt_sha256() -> str:
    return hashlib.sha256(GENERATOR_PROMPT.encode("utf-8")).hexdigest()


def _knockout(candidates: list[str], material: SourceMaterial) -> list[str]:
    """Keep only faithful candidates, then order by the checklist and take the
    top N_WINNERS. Deterministic: ties break on the text itself so a run is
    reproducible."""
    faithful = [c for c in candidates if is_faithful(c, material)]
    faithful.sort(key=lambda c: (-checklist_score(c, material), c))
    return faithful[:N_WINNERS]


def run_foundry(
    material: SourceMaterial,
    generator: DescriptorGenerator,
    judge: DescriptorJudge,
    *,
    now: datetime | None = None,
) -> FoundryResult | None:
    """Run the full Foundry for one artist's materials.

    Returns a candidate FoundryResult, or None for an honest gap. `now` is
    injectable so callers/tests are reproducible.
    """
    # Custody: the judge must be a DIFFERENT model than the generator. The
    # thing that writes a line never blesses it (the gate-custody principle,
    # applied to generated copy).
    if generator.model_id == judge.model_id:
        raise DescriptorFoundryError(
            f"judge and generator share model {generator.model_id!r} — the "
            "independent judge must be a different model"
        )

    # Honest gap: nothing to compose from.
    if not material.has_material():
        return None

    raw = list(generator.generate_candidates(material, N_CANDIDATES))
    winners = _knockout(raw, material)
    if not winners:
        # Every candidate was unfaithful or mis-shaped — an honest gap, not a
        # fabricated line.
        return None

    fused = generator.fuse(winners, material).strip()

    # A fused line that is itself unfaithful is a defect in fusion, not an
    # honest gap: fail loud rather than emit it. "style new, facts never" is a
    # mechanism here, not a slogan.
    assert_faithful(fused, material)

    score = float(judge.score(fused, material))
    if score < JUDGE_THRESHOLD:
        # Faithful, yet below the judge's bar — an honest gap; a weak line is
        # worse than none.
        return None

    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    provenance = {
        # Mirror the worker extraction _provenance convention so audits read
        # the same shape across the codebase.
        "provider": "descriptor_foundry",
        "generator_model": generator.model_id,
        "judge_model": judge.model_id,
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": _prompt_sha256(),
        "foundry_version": FOUNDRY_VERSION,
        "judge_score": score,
        "source_refs": list(material.refs),
        "candidate_texts": list(raw),
        "winner_texts": list(winners),
        "extracted_at": stamp.isoformat(),
    }
    return FoundryResult(
        text=fused,
        tier=TIER_AI_DRAFTED,
        status=STATUS_CANDIDATE,
        provenance=provenance,
    )
