"""Descriptor Foundry — the gated Spark Line generation pipeline.

Public API. See docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md §4 and the Master
Design Brief lines 65, 151-163. This package generates AI-drafted (tier C)
Spark Lines from an artist's OWN materials and VALIDATES them through the
Foundry gate (faithfulness + independent judge + golden-set regression) — that
validation is what satisfies the gate-custodied-publication invariant
("AI never publishes unvalidated", reworded 2026-08-03). Output is a
`candidate`; taking a validated line live is gate-custodied and
founder-controlled (the auto-publish switch), outside this module.
"""
from __future__ import annotations

from .foundry import (
    GENERATOR_PROMPT,
    JUDGE_THRESHOLD,
    N_CANDIDATES,
    N_WINNERS,
    PROMPT_VERSION,
    run_foundry,
)
from .gate import assert_faithful, checklist_score, is_faithful
from .golden import GOLDEN_PATH, run_golden
from .publish import (
    SparkLinePublishError,
    approve_candidate,
    reject_candidate,
)
from .types import (
    DescriptorCandidate,
    DescriptorFoundryError,
    DescriptorGenerator,
    DescriptorJudge,
    FoundryResult,
    SourceMaterial,
    STATUS_CANDIDATE,
    TIER_AI_DRAFTED,
    VALID_WORD_COUNTS,
)

__all__ = [
    "run_foundry",
    "GENERATOR_PROMPT",
    "PROMPT_VERSION",
    "N_CANDIDATES",
    "N_WINNERS",
    "JUDGE_THRESHOLD",
    "assert_faithful",
    "is_faithful",
    "checklist_score",
    "run_golden",
    "GOLDEN_PATH",
    "approve_candidate",
    "reject_candidate",
    "SparkLinePublishError",
    "SourceMaterial",
    "DescriptorCandidate",
    "FoundryResult",
    "DescriptorGenerator",
    "DescriptorJudge",
    "DescriptorFoundryError",
    "STATUS_CANDIDATE",
    "TIER_AI_DRAFTED",
    "VALID_WORD_COUNTS",
]
