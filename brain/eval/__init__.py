"""Memory eval harness for the OneLive brain — measured, not asserted.

This package MEASURES the quality of the knowledge-graph brain (``brain/``) on
a labeled, deterministic benchmark and reports real numbers, so "world-class
brain" is a measured fact rather than a claim. It reads only the public
``brain/`` API and never modifies the graph engine.

  * ``benchmark`` — the labeled corpus + gold-answer questions (6 standard
    agent-memory categories).
  * ``harness``   — the runner + deterministic scorer (no LLM, no network, no
    spend) returning a structured :class:`~brain.eval.harness.MemoryEvalReport`.

CLI: ``python tools/brain_eval.py``. Write-up + SOTA positioning:
``docs/strategy/ONE_LIVE_BRAIN_BENCHMARK_v1.md``.
"""
from brain.eval.benchmark import BENCHMARK, CATEGORIES, Scenario, all_questions
from brain.eval.harness import (
    Answer,
    BrainAnswerer,
    CategoryScore,
    MemoryEvalReport,
    QuestionResult,
    run_benchmark,
    score_answer,
)

__all__ = [
    "BENCHMARK",
    "CATEGORIES",
    "Scenario",
    "all_questions",
    "Answer",
    "BrainAnswerer",
    "CategoryScore",
    "MemoryEvalReport",
    "QuestionResult",
    "run_benchmark",
    "score_answer",
]
