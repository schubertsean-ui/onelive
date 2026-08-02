"""Descriptor Foundry — the gated Spark Line generation pipeline.

Public API. See docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md §4 and the Master
Design Brief lines 65, 151-163. This package generates AI-drafted (tier C)
Spark Lines from an artist's OWN materials and emits CANDIDATES ONLY — the
approval/publish step is separate and independently gated ("AI never
publishes" by construction).
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
