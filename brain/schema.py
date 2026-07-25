"""Typed node/edge schema for the OneLive knowledge-graph brain.

Greppable summary: the enums + dataclasses that give the graph its types.
Every node carries `id`, a `node_type`, `created_at`, and the supersede
bookkeeping (`superseded` / `superseded_by`) so an old node stays
addressable after it is revised. Beyond that, each node type carries the
PROVENANCE fields the paper requires — the whole point of the graph is that
an output can be traced back to its source, its authoring run, its rubric.

Node types (paper §III): Entity, Claim, Source, Artifact, AgentRun,
Evaluation, Task — plus Commit and Metric for the build-loop record.

Edge types (paper §III): MENTIONS, SUPPORTS, CONTRADICTS, DERIVED_FROM,
PRODUCED, EVALUATES, REVISES, SUPERSEDES, DEPENDS_ON, PARENT_OF,
RESOLVED_TO.

These dataclasses hold data only. The write invariants that make a Claim
require a Source, an Artifact require an AgentRun+version, and an Evaluation
require a rubric are enforced in brain/graph.py at write time — a dataclass
can be constructed in isolation, but it cannot ENTER the graph in violation.
"""
from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Optional


class NodeType(enum.Enum):
    """The kinds of node the graph stores."""

    ENTITY = "entity"
    CLAIM = "claim"
    SOURCE = "source"
    ARTIFACT = "artifact"
    AGENT_RUN = "agent_run"
    EVALUATION = "evaluation"
    TASK = "task"
    COMMIT = "commit"
    METRIC = "metric"


class EdgeType(enum.Enum):
    """The typed, directed relationships the graph stores.

    Direction convention is stated per edge so traversal stays legible:
      MENTIONS      (src, dst): src text mentions dst entity.
      SUPPORTS      (src, dst): src claim/source supports dst claim.
      CONTRADICTS   (src, dst): src claim/source contradicts dst claim.
      DERIVED_FROM  (src, dst): src was derived from dst.
      PRODUCED      (src, dst): src agent_run produced dst artifact.
      EVALUATES     (src, dst): src evaluation evaluates dst.
      REVISES       (src, dst): src revises (is a newer version of) dst.
      SUPERSEDES    (src, dst): src supersedes dst (dst stays addressable).
      DEPENDS_ON    (src, dst): src depends on dst.
      PARENT_OF     (src, dst): src task is the parent of dst task.
      RESOLVED_TO   (src, dst): src surface-form entity resolved to dst canonical.
    """

    MENTIONS = "mentions"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    DERIVED_FROM = "derived_from"
    PRODUCED = "produced"
    EVALUATES = "evaluates"
    REVISES = "revises"
    SUPERSEDES = "supersedes"
    DEPENDS_ON = "depends_on"
    PARENT_OF = "parent_of"
    RESOLVED_TO = "resolved_to"


def _now() -> float:
    """Wall-clock creation stamp. Stored on disk so it survives a reload."""
    return time.time()


@dataclass
class Node:
    """Common fields every node carries.

    Subclasses add their own provenance fields. `id` is assigned by the
    graph at add time when left blank. `superseded`/`superseded_by` are the
    invariant-4 bookkeeping: supersede FLAGS a node and links the successor,
    it never removes the node from the store.
    """

    id: str = ""
    node_type: NodeType = NodeType.ENTITY
    created_at: float = field(default_factory=_now)
    superseded: bool = False
    superseded_by: Optional[str] = None


@dataclass
class Entity(Node):
    """A real-world thing (venue, artist, ...) the graph knows about.

    Provenance per the paper's entity-resolution section (§IV.D/§IX.G):
    `aliases` retains every surface form folded in, `source_docs` retains
    where each was seen, `resolution_rationale` says WHY a merge happened,
    and `confidence` says how sure. Retaining all of this is what makes a
    resolution reversible — see Graph.resolve_entities / Graph.unresolve.
    """

    name: str = ""
    entity_type: str = ""  # e.g. "venue", "artist"
    canonical_id: Optional[str] = None  # set on surface-forms that were resolved away
    aliases: list = field(default_factory=list)
    source_docs: list = field(default_factory=list)
    resolution_rationale: str = ""
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.node_type = NodeType.ENTITY


@dataclass
class Source(Node):
    """A provenance root: a fetched document, page, or feed record."""

    uri: str = ""
    title: str = ""
    description: str = ""

    def __post_init__(self) -> None:
        self.node_type = NodeType.SOURCE


@dataclass
class Claim(Node):
    """A stated fact about the world.

    Invariant 1: a claim must be backed by a `source_id` OR be explicitly
    marked `inference=True`. An unsourced, non-inference claim cannot enter
    the graph (Graph.add_claim raises). `confidence` can later feed the
    shadow-only Subjective Logic substrate (worker/convergence) — the seam
    is noted, not wired.

    BI-TEMPORAL time (paper §IV.D "recurrence / temporal validity"; closes the
    R-010/R-031/G-BRAIN-1D point-in-time gap). A claim carries TWO independent
    time axes:

      * VALID time — WHEN the fact was true IN THE WORLD — is
        `valid_from`/`valid_to` (ISO date or datetime strings, or None). The
        interval is half-open ``[valid_from, valid_to)``: `valid_from` is
        inclusive, `valid_to` is exclusive. `None` on either end means "open"
        (unbounded past / still true). A claim with BOTH None is TIMELESS —
        valid at every instant — which is the default, so every pre-existing
        claim keeps its exact behavior.
      * TRANSACTION time — WHEN WE RECORDED or superseded the claim — is the
        existing `created_at` stamp plus the `superseded`/`superseded_by`
        bookkeeping. An "as of" read fixes transaction time to "what we believe
        now" (superseded versions excluded) and filters the valid axis to the
        queried instant — see Graph.claims_valid_at / Graph.as_of_subgraph.

    So "Mohawk's capacity was 500 until 2026-03-01, then 800" is two live
    claims — one ``valid_to='2026-03-01'`` (500), one ``valid_from='2026-03-01'``
    (800) — and ``as_of('2026-02-01')`` returns 500 while the current value is
    800. Nothing is superseded: both are believed, each true for its era.
    """

    text: str = ""
    source_id: Optional[str] = None
    inference: bool = False
    confidence: float = 1.0
    valid_from: Optional[str] = None  # inclusive ISO instant; None = open past
    valid_to: Optional[str] = None    # exclusive ISO instant; None = still true

    def __post_init__(self) -> None:
        self.node_type = NodeType.CLAIM


@dataclass
class AgentRun(Node):
    """A bounded execution record: one run of one agent toward an objective."""

    agent: str = ""
    objective: str = ""
    status: str = ""  # e.g. "started", "succeeded", "failed"
    started_at: Optional[float] = None
    ended_at: Optional[float] = None

    def __post_init__(self) -> None:
        self.node_type = NodeType.AGENT_RUN


@dataclass
class Artifact(Node):
    """Something an agent produced (a file, a diff, a report).

    Invariant 2: an artifact must name its `authoring_run` (an AgentRun id)
    and carry a `version`. An artifact with no author or no version cannot
    enter the graph (Graph.add_artifact raises).
    """

    name: str = ""
    authoring_run: Optional[str] = None
    version: str = ""
    content: str = ""

    def __post_init__(self) -> None:
        self.node_type = NodeType.ARTIFACT


@dataclass
class Evaluation(Node):
    """A verdict from an evaluator against a named rubric.

    Invariant 3: an evaluation must identify a `rubric`. A verdict with no
    rubric cannot enter the graph (Graph.add_evaluation raises) — an
    ungrounded judgement is not evidence.
    """

    rubric: str = ""
    verdict: str = ""  # e.g. "APPROVE", "REQUEST-CHANGES", "PASS", "FAIL"
    target_id: Optional[str] = None
    notes: str = ""

    def __post_init__(self) -> None:
        self.node_type = NodeType.EVALUATION


@dataclass
class Task(Node):
    """A unit of intended work; may have a parent (PARENT_OF edge)."""

    description: str = ""
    status: str = ""  # e.g. "open", "done", "blocked"
    parent_id: Optional[str] = None

    def __post_init__(self) -> None:
        self.node_type = NodeType.TASK


@dataclass
class Commit(Node):
    """A version-control commit in the build record."""

    sha: str = ""
    message: str = ""

    def __post_init__(self) -> None:
        self.node_type = NodeType.COMMIT


@dataclass
class Metric(Node):
    """A measured number in the build/eval record."""

    name: str = ""
    value: float = 0.0
    unit: str = ""

    def __post_init__(self) -> None:
        self.node_type = NodeType.METRIC


@dataclass
class Edge:
    """A typed, directed relationship between two node ids."""

    src: str
    dst: str
    edge_type: EdgeType

    def key(self) -> tuple:
        """Identity of an edge for dedupe: (src, dst, type)."""
        return (self.src, self.dst, self.edge_type)


# Map NodeType -> dataclass, used by the store to reconstruct on load.
NODE_CLASSES = {
    NodeType.ENTITY: Entity,
    NodeType.SOURCE: Source,
    NodeType.CLAIM: Claim,
    NodeType.AGENT_RUN: AgentRun,
    NodeType.ARTIFACT: Artifact,
    NodeType.EVALUATION: Evaluation,
    NodeType.TASK: Task,
    NodeType.COMMIT: Commit,
    NodeType.METRIC: Metric,
}
