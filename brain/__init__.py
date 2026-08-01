"""OneLive persistent knowledge-graph brain (Graph Engineering adoption).

Greppable summary: the typed, persistent world model adopted from the
"Graph Engineering — The Karpathy Loop / Anthropic Playbook" paper the
founder supplied. The thesis is one line: **the agent forgets, the graph
does not.** Where docs/memory/ holds distilled markdown a human re-reads,
this package holds a queryable typed graph that survives process death and
enforces provenance MECHANICALLY.

What lives here (see the modules for detail):

  * `schema`  — node/edge type enums + provenance-bearing dataclasses
                (Entity, Claim, Source, Artifact, AgentRun, Evaluation,
                Task, plus Commit/Metric; typed edges).
  * `graph`   — the in-memory graph store. It ENFORCES the paper's four
                write invariants: a write that violates one RAISES loudly
                (GraphInvariantError). Supersede never deletes; entity
                resolution is reversible.
  * `store`   — persistence to disk (append-only JSONL snapshot). save()/
                load() round-trip the FULL graph, including superseded
                nodes and resolution history — the "does not forget" proof.
  * `demo`    — `python -m brain.demo`: builds a small OneLive-shaped graph,
                saves it, reloads it in a FRESH process-local store, and
                prints the recovered subgraph.

This package is MEMORY. It never publishes: it must not import
worker.promote (trust invariant, enforced by tools/trust_gate.py). The
decision record for this adoption is
docs/memory/decisions/2026-07-25_graph-engineering-adoption.md.
"""
from brain.graph import Graph, GraphInvariantError
from brain.schema import (
    AgentRun,
    Artifact,
    Claim,
    Commit,
    Edge,
    EdgeType,
    Entity,
    Evaluation,
    Metric,
    NodeType,
    Source,
    Task,
)
from brain.store import load, save

__all__ = [
    "Graph",
    "GraphInvariantError",
    "NodeType",
    "EdgeType",
    "Entity",
    "Claim",
    "Source",
    "Artifact",
    "AgentRun",
    "Evaluation",
    "Task",
    "Commit",
    "Metric",
    "Edge",
    "save",
    "load",
]
