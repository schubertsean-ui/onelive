"""The ONE canonical brain store path.

Founder catch (2026-07-25): a lesson is only "in the brain" if the loop that
plans work actually READS the same graph the lesson was written to. Before this,
RCAs were saved to an ad-hoc file while brain/construction.py's retrieval had no
agreed location — so a recorded root cause could never surface as a red path to
avoid. One constant, imported by both sides, closes that.
"""
from __future__ import annotations

import pathlib

_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Every durable agent learning — root causes AND construction outcomes — lives
# here, so `retrieve_red_classes` / `retrieve_green_examples` see what
# `rca.analyze` wrote.
BRAIN_PATH = _ROOT / "docs" / "memory" / "brain.jsonl"


def load_brain():
    """Load the canonical brain graph (empty graph when it does not exist yet)."""
    from brain.graph import Graph
    from brain import store
    return store.load(BRAIN_PATH) if BRAIN_PATH.exists() else Graph()


def save_brain(graph) -> None:
    from brain import store
    BRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    store.save(graph, BRAIN_PATH)
