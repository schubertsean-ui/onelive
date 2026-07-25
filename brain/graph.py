"""The OneLive knowledge-graph store — a tiny typed MultiDiGraph with teeth.

Greppable summary: an in-memory, pure-stdlib graph (no networkx — the
sandbox is network-blocked and CI is minimal, so we implement the small
directed multigraph we need ourselves). Its job is not just to hold nodes
and edges; it is to make the paper's FOUR write invariants physics rather
than policy. A write that violates one RAISES GraphInvariantError loudly —
fail loud, never silently store a provenance-less fact.

The four write invariants (paper §III, "the graph is honest by
construction"), each enforced in the matching add_* method:

  1. Every Claim has a Source OR is explicitly marked `inference=True`.
  2. Every Artifact has an authoring AgentRun and a version.
  3. Every Evaluation identifies a rubric.
  4. Every SUPERSEDED object remains addressable — supersede() sets a flag
     and adds REVISES/SUPERSEDES edges; it NEVER deletes. There is no
     delete path in this class at all.

Entity resolution (resolve_entities/unresolve) is REVERSIBLE and additive:
folding surface forms into a canonical entity RETAINS every alias,
source_doc, and a rationale, and records enough state to undo the merge
without rebuilding the graph. A false merge is a mistake, not a
catastrophe.

subgraph() returns a bounded neighborhood with provenance for context
construction — retrieve the connected state for a decision instead of
replaying all history (paper §V.B).

Persistence lives in brain/store.py; this module is process-local state.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable, Optional

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
    Node,
    NodeType,
    Source,
    Task,
)


class GraphInvariantError(Exception):
    """Raised when a write would violate a graph invariant.

    This is deliberately a loud, unignorable failure: the entire value of
    the graph is that it cannot hold a provenance-less fact, so an attempt
    to write one stops the world rather than being quietly dropped.
    """


@dataclass
class Subgraph:
    """A bounded neighborhood returned by Graph.subgraph().

    Carries the nodes reached (including superseded ones — they stay
    addressable) and the edges traversed, so the caller gets the connected
    state AND its provenance in one bounded object.
    """

    root: str
    hops: int
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)

    def node_ids(self) -> set:
        return {n.id for n in self.nodes}

    def describe(self) -> str:
        """A human-readable rendering — used by the demo to SHOW recovery."""
        lines = [f"subgraph(root={self.root}, hops={self.hops}): "
                 f"{len(self.nodes)} node(s), {len(self.edges)} edge(s)"]
        for n in sorted(self.nodes, key=lambda x: x.id):
            flag = " [SUPERSEDED]" if getattr(n, "superseded", False) else ""
            label = _node_label(n)
            lines.append(f"  ({n.node_type.value}) {n.id}{flag}: {label}")
        for e in sorted(self.edges, key=lambda x: (x.src, x.dst, x.edge_type.value)):
            lines.append(f"  {e.src} --{e.edge_type.value}--> {e.dst}")
        return "\n".join(lines)


def _node_label(n: Node) -> str:
    """Best short label for a node, for human-readable output."""
    for attr in ("name", "text", "title", "objective", "rubric", "description",
                 "sha", "uri"):
        val = getattr(n, attr, "")
        if val:
            return str(val)
    return n.id


# --- bi-temporal validity helpers --------------------------------------------
# ISO 8601 strings sort lexicographically in chronological order, so a plain
# string comparison is a correct instant comparison as long as the fixtures use
# a single, consistent granularity (the benchmark + tests pass fixed ISO dates,
# never a wall clock — determinism, no network, no spend).
def _instant_ok(value: object, label: str) -> None:
    if value is not None and not isinstance(value, str):
        raise GraphInvariantError(
            f"{label} must be an ISO date/datetime string or None, got {value!r} "
            f"({type(value).__name__}). Bi-temporal instants are compared as "
            f"strings; a non-string cannot be an instant."
        )


def _validate_interval(valid_from: Optional[str], valid_to: Optional[str]) -> None:
    """Fail loud on a malformed validity interval.

    Instants must be ISO strings or None, and a bounded interval must be
    non-empty: ``valid_from`` (inclusive) strictly before ``valid_to``
    (exclusive). An empty/inverted interval would contain no instant, so it is
    almost certainly a data error — we refuse it rather than store a claim that
    is valid nowhere.
    """
    _instant_ok(valid_from, "valid_from")
    _instant_ok(valid_to, "valid_to")
    if valid_from is not None and valid_to is not None and not (valid_from < valid_to):
        raise GraphInvariantError(
            f"empty/inverted validity interval: valid_from {valid_from!r} must be "
            f"strictly before valid_to {valid_to!r} (the interval is half-open "
            f"[valid_from, valid_to) and must contain at least one instant)."
        )


def _valid_at(claim, instant: str) -> bool:
    """True iff ``claim``'s half-open [valid_from, valid_to) contains ``instant``.

    A timeless claim (both bounds None) is valid at EVERY instant — the
    unchanged behavior for every claim that carries no interval.
    """
    valid_from = getattr(claim, "valid_from", None)
    valid_to = getattr(claim, "valid_to", None)
    if valid_from is not None and instant < valid_from:
        return False
    if valid_to is not None and instant >= valid_to:
        return False
    return True


class Graph:
    """A typed directed multigraph that enforces the paper's write invariants."""

    def __init__(self) -> None:
        # id -> Node (superseded nodes stay here; nothing is ever removed).
        self.nodes: dict = {}
        # edges keyed by (src, dst, EdgeType) so duplicates collapse.
        self.edges: dict = {}
        # append-only list of resolution records (for reversible merges).
        self.resolutions: list = []
        self._counter: int = 0

    # --- id + low-level insert ------------------------------------------------
    def _next_id(self, node_type: NodeType) -> str:
        self._counter += 1
        return f"{node_type.value}:{self._counter}"

    def _insert(self, node: Node) -> Node:
        if not node.id:
            node.id = self._next_id(node.node_type)
        if node.id in self.nodes:
            raise GraphInvariantError(
                f"duplicate node id {node.id!r} — ids must be unique; refusing "
                f"to overwrite an existing node (use supersede() to revise it)."
            )
        self.nodes[node.id] = node
        return node

    def get(self, node_id: str) -> Node:
        """Return a node by id (including superseded nodes). Raises if absent."""
        try:
            return self.nodes[node_id]
        except KeyError:
            raise GraphInvariantError(f"no node with id {node_id!r} in the graph.")

    def has(self, node_id: str) -> bool:
        return node_id in self.nodes

    def nodes_of_type(self, node_type: NodeType) -> list:
        return [n for n in self.nodes.values() if n.node_type == node_type]

    # --- typed adders (invariants enforced here) ------------------------------
    def add_source(self, source: Source) -> Source:
        if not isinstance(source, Source):
            raise GraphInvariantError("add_source requires a Source node.")
        return self._insert(source)

    def add_entity(self, entity: Entity) -> Entity:
        if not isinstance(entity, Entity):
            raise GraphInvariantError("add_entity requires an Entity node.")
        return self._insert(entity)

    def add_claim(self, claim: Claim, *, valid_from: Optional[str] = None,
                  valid_to: Optional[str] = None) -> Claim:
        """Invariant 1: a Claim needs a Source OR inference=True.

        Bi-temporal (backward-compatible): `valid_from`/`valid_to` set the VALID
        interval the fact held in the world. They can be passed here OR carried
        on the Claim itself — a non-None keyword OVERRIDES the claim's own value,
        while the default (None, None) leaves the claim's interval untouched, so
        every existing caller (which passes neither) still writes a TIMELESS
        claim exactly as before. The interval is validated (fail loud on an
        empty/inverted one) before the invariant-1 checks.
        """
        if not isinstance(claim, Claim):
            raise GraphInvariantError("add_claim requires a Claim node.")
        if valid_from is not None:
            claim.valid_from = valid_from
        if valid_to is not None:
            claim.valid_to = valid_to
        _validate_interval(claim.valid_from, claim.valid_to)
        if not claim.inference and not claim.source_id:
            raise GraphInvariantError(
                "INVARIANT 1 violated: a Claim must cite a source_id OR be "
                "explicitly marked inference=True. An unsourced, non-inference "
                f"claim is not admissible: {claim.text!r}."
            )
        if claim.source_id is not None:
            if not self.has(claim.source_id):
                raise GraphInvariantError(
                    f"INVARIANT 1 violated: Claim cites source_id "
                    f"{claim.source_id!r} which is not in the graph."
                )
            if self.get(claim.source_id).node_type != NodeType.SOURCE:
                raise GraphInvariantError(
                    f"INVARIANT 1 violated: Claim's source_id {claim.source_id!r} "
                    f"points at a {self.get(claim.source_id).node_type.value}, "
                    f"not a Source."
                )
        node = self._insert(claim)
        # Materialise the provenance as an edge too, so it is traversable.
        if claim.source_id is not None:
            self.add_edge(claim.id, claim.source_id, EdgeType.DERIVED_FROM)
        return node

    def add_agent_run(self, run: AgentRun) -> AgentRun:
        if not isinstance(run, AgentRun):
            raise GraphInvariantError("add_agent_run requires an AgentRun node.")
        return self._insert(run)

    def add_artifact(self, artifact: Artifact) -> Artifact:
        """Invariant 2: an Artifact needs an authoring AgentRun and a version."""
        if not isinstance(artifact, Artifact):
            raise GraphInvariantError("add_artifact requires an Artifact node.")
        if not artifact.authoring_run:
            raise GraphInvariantError(
                "INVARIANT 2 violated: an Artifact must name its authoring_run "
                f"(an AgentRun id): {artifact.name!r}."
            )
        if not self.has(artifact.authoring_run):
            raise GraphInvariantError(
                f"INVARIANT 2 violated: Artifact authoring_run "
                f"{artifact.authoring_run!r} is not in the graph."
            )
        if self.get(artifact.authoring_run).node_type != NodeType.AGENT_RUN:
            raise GraphInvariantError(
                f"INVARIANT 2 violated: Artifact authoring_run "
                f"{artifact.authoring_run!r} is not an AgentRun."
            )
        if not artifact.version:
            raise GraphInvariantError(
                "INVARIANT 2 violated: an Artifact must carry a version: "
                f"{artifact.name!r}."
            )
        node = self._insert(artifact)
        # The authoring run PRODUCED this artifact — record the edge.
        self.add_edge(artifact.authoring_run, artifact.id, EdgeType.PRODUCED)
        return node

    def add_evaluation(self, evaluation: Evaluation) -> Evaluation:
        """Invariant 3: an Evaluation must identify a rubric."""
        if not isinstance(evaluation, Evaluation):
            raise GraphInvariantError("add_evaluation requires an Evaluation node.")
        if not evaluation.rubric:
            raise GraphInvariantError(
                "INVARIANT 3 violated: an Evaluation must identify a rubric — an "
                f"ungrounded verdict is not evidence: verdict={evaluation.verdict!r}."
            )
        if evaluation.target_id is not None and not self.has(evaluation.target_id):
            raise GraphInvariantError(
                f"Evaluation target_id {evaluation.target_id!r} is not in the graph."
            )
        node = self._insert(evaluation)
        if evaluation.target_id is not None:
            self.add_edge(evaluation.id, evaluation.target_id, EdgeType.EVALUATES)
        return node

    def add_task(self, task: Task) -> Task:
        if not isinstance(task, Task):
            raise GraphInvariantError("add_task requires a Task node.")
        if task.parent_id is not None and not self.has(task.parent_id):
            raise GraphInvariantError(
                f"Task parent_id {task.parent_id!r} is not in the graph."
            )
        node = self._insert(task)
        if task.parent_id is not None:
            self.add_edge(task.parent_id, task.id, EdgeType.PARENT_OF)
        return node

    def add_commit(self, commit: Commit) -> Commit:
        if not isinstance(commit, Commit):
            raise GraphInvariantError("add_commit requires a Commit node.")
        return self._insert(commit)

    def add_metric(self, metric: Metric) -> Metric:
        if not isinstance(metric, Metric):
            raise GraphInvariantError("add_metric requires a Metric node.")
        return self._insert(metric)

    # --- edges ----------------------------------------------------------------
    def add_edge(self, src: str, dst: str, edge_type: EdgeType) -> Edge:
        """Add a typed directed edge; both endpoints must already exist."""
        if not isinstance(edge_type, EdgeType):
            raise GraphInvariantError(
                f"edge_type must be an EdgeType, got {edge_type!r}."
            )
        if not self.has(src):
            raise GraphInvariantError(f"edge source {src!r} is not in the graph.")
        if not self.has(dst):
            raise GraphInvariantError(f"edge target {dst!r} is not in the graph.")
        edge = Edge(src=src, dst=dst, edge_type=edge_type)
        self.edges[edge.key()] = edge
        return edge

    def remove_edge(self, src: str, dst: str, edge_type: EdgeType) -> None:
        """Remove an edge if present. Used only by unresolve() to undo the
        RESOLVED_TO links it added — nodes are never removed, only edges,
        and only ones a reversible operation itself created."""
        self.edges.pop((src, dst, edge_type), None)

    def edges_of(self, node_id: str) -> list:
        """Every edge touching node_id, either direction."""
        return [e for e in self.edges.values()
                if e.src == node_id or e.dst == node_id]

    # --- invariant 4: supersede without deleting ------------------------------
    def supersede(self, node_id: str, by: str) -> None:
        """Mark `node_id` as superseded by `by`, keeping the old node addressable.

        Invariant 4: this NEVER deletes. It flags the old node, records the
        successor, and adds SUPERSEDES (by -> node_id) and REVISES
        (by -> node_id) edges. get(node_id) and subgraph() still return the
        old node afterward — its history stays queryable.
        """
        old = self.get(node_id)   # raises if absent
        new = self.get(by)        # raises if absent
        if node_id == by:
            raise GraphInvariantError("a node cannot supersede itself.")
        old.superseded = True
        old.superseded_by = by
        self.add_edge(by, node_id, EdgeType.SUPERSEDES)
        self.add_edge(by, node_id, EdgeType.REVISES)
        # Invariant 4, asserted mechanically: the old node is STILL in the store.
        if node_id not in self.nodes:
            raise GraphInvariantError(
                "INVARIANT 4 violated: supersede removed a node from the store; "
                "superseded objects must remain addressable."
            )
        assert new.id == by  # successor exists; satisfies the type checker's use

    # --- reversible entity resolution ----------------------------------------
    def resolve_entities(self, canonical: str, others: Iterable[str],
                         rationale: str, confidence: float) -> str:
        """Fold surface-form entities `others` into `canonical` — REVERSIBLY.

        The paper (§IV.D/§IX.G): resolution is additive and inspectable. The
        canonical entity RETAINS every alias and source_doc of the folded
        forms, plus the `rationale` and `confidence` of the merge. The folded
        entities are marked superseded (still addressable) and linked to the
        canonical by RESOLVED_TO edges. A full pre-merge snapshot is recorded
        so unresolve() can undo the merge without rebuilding the graph.

        Returns the resolution record id.
        """
        canon = self.get(canonical)
        if canon.node_type != NodeType.ENTITY:
            raise GraphInvariantError(
                f"resolve_entities canonical {canonical!r} is not an Entity."
            )
        others = list(others)
        if not others:
            raise GraphInvariantError(
                "resolve_entities needs at least one surface form to fold in."
            )
        if not rationale:
            raise GraphInvariantError(
                "resolve_entities requires a rationale — a merge with no stated "
                "reason is not inspectable, which defeats reversibility."
            )

        # Snapshot the canonical's pre-merge provenance so unresolve restores it.
        canonical_before = {
            "aliases": list(canon.aliases),
            "source_docs": list(canon.source_docs),
            "resolution_rationale": canon.resolution_rationale,
            "confidence": canon.confidence,
        }
        others_snapshot = []
        for oid in others:
            if oid == canonical:
                raise GraphInvariantError(
                    "resolve_entities cannot fold an entity into itself."
                )
            other = self.get(oid)
            if other.node_type != NodeType.ENTITY:
                raise GraphInvariantError(
                    f"resolve_entities surface form {oid!r} is not an Entity."
                )
            if other.superseded:
                raise GraphInvariantError(
                    f"resolve_entities surface form {oid!r} is already superseded; "
                    f"unresolve it first before re-resolving."
                )
            # Full snapshot of the folded entity's state, to restore on undo.
            others_snapshot.append({
                "id": other.id,
                "name": other.name,
                "aliases": list(other.aliases),
                "source_docs": list(other.source_docs),
                "canonical_id": other.canonical_id,
                "superseded": other.superseded,
                "superseded_by": other.superseded_by,
            })

        # Perform the additive merge: retain aliases + source_docs.
        for other in (self.get(oid) for oid in others):
            _merge_unique(canon.aliases, [other.name])
            _merge_unique(canon.aliases, other.aliases)
            _merge_unique(canon.source_docs, other.source_docs)
            other.superseded = True
            other.superseded_by = canonical
            other.canonical_id = canonical
            self.add_edge(other.id, canonical, EdgeType.RESOLVED_TO)
        canon.resolution_rationale = rationale
        canon.confidence = confidence

        resolution_id = f"resolution:{len(self.resolutions) + 1}"
        self.resolutions.append({
            "resolution_id": resolution_id,
            "canonical_id": canonical,
            "rationale": rationale,
            "confidence": confidence,
            "reversed": False,
            "canonical_before": canonical_before,
            "others": others_snapshot,
        })
        return resolution_id

    def unresolve(self, canonical_id: str) -> str:
        """Reverse the most recent live resolution into `canonical_id`.

        Restores the canonical's pre-merge aliases/source_docs/rationale/
        confidence, un-supersedes every folded entity back to its exact
        pre-merge state, and removes the RESOLVED_TO edges the merge added.
        No node is ever lost — the folded entities were superseded, never
        deleted, so this brings them fully back. Returns the resolution id
        that was reversed.
        """
        record = None
        for rec in reversed(self.resolutions):
            if rec["canonical_id"] == canonical_id and not rec["reversed"]:
                record = rec
                break
        if record is None:
            raise GraphInvariantError(
                f"no live resolution to reverse for canonical {canonical_id!r}."
            )
        canon = self.get(canonical_id)
        before = record["canonical_before"]
        canon.aliases = list(before["aliases"])
        canon.source_docs = list(before["source_docs"])
        canon.resolution_rationale = before["resolution_rationale"]
        canon.confidence = before["confidence"]
        for snap in record["others"]:
            other = self.get(snap["id"])
            other.name = snap["name"]
            other.aliases = list(snap["aliases"])
            other.source_docs = list(snap["source_docs"])
            other.canonical_id = snap["canonical_id"]
            other.superseded = snap["superseded"]
            other.superseded_by = snap["superseded_by"]
            self.remove_edge(snap["id"], canonical_id, EdgeType.RESOLVED_TO)
        record["reversed"] = True
        return record["resolution_id"]

    # --- bi-temporal point-in-time reads -------------------------------------
    def claims_valid_at(self, entity_id: str, instant: str, *,
                        predicate: Optional[str] = None) -> list:
        """Currently-believed Claims MENTIONING `entity_id` VALID at `instant`.

        The bi-temporal "as of" read: the TRANSACTION axis is fixed to "what we
        believe now" — a superseded (retracted/corrected) claim is NEVER
        returned, so only the currently-believed version speaks for its era —
        and the VALID axis is filtered to claims whose half-open
        ``[valid_from, valid_to)`` contains `instant`. A TIMELESS claim (no
        interval) is valid at every instant, so it always qualifies (unchanged
        behavior). This is what lets the brain answer "what was true as of date
        X" — the R-010/R-031/G-BRAIN-1D temporal gap.

        `predicate`, when given, keeps only ATTRIBUTE claims whose text begins
        with ``"<predicate>="`` — the ``predicate=value`` reader convention the
        eval harness and benchmark share (brain/eval/). Deterministic: results
        come back in ascending node-id order, so the same corpus always yields
        the same list.
        """
        if not self.has(entity_id):
            raise GraphInvariantError(
                f"claims_valid_at entity {entity_id!r} is not in the graph.")
        _instant_ok(instant, "instant")
        if instant is None:
            raise GraphInvariantError(
                "claims_valid_at requires a concrete ISO instant to query at; "
                "None is not an instant.")
        prefix = f"{predicate}=" if predicate is not None else None
        hits: dict = {}
        for e in self.edges.values():
            if e.edge_type != EdgeType.MENTIONS:
                continue
            # Benchmark convention is (claim --MENTIONS--> entity); accept either
            # orientation defensively and identify the claim endpoint.
            if e.dst == entity_id:
                claim_id = e.src
            elif e.src == entity_id:
                claim_id = e.dst
            else:
                continue
            node = self.nodes.get(claim_id)
            if node is None or node.node_type != NodeType.CLAIM:
                continue
            if node.superseded:
                continue  # transaction axis: retracted versions do not speak
            if not _valid_at(node, instant):
                continue  # valid axis: outside its [valid_from, valid_to)
            if prefix is not None and not node.text.startswith(prefix):
                continue
            hits[node.id] = node
        return [hits[nid] for nid in sorted(hits)]

    # --- bounded context construction ----------------------------------------
    def subgraph(self, node_id: str, hops: int,
                 edge_types: Optional[Iterable[EdgeType]] = None,
                 *, as_of: Optional[str] = None) -> Subgraph:
        """Return the bounded neighborhood of `node_id` within `hops` edges.

        Traverses edges in BOTH directions (a claim's source and the
        evaluation that judged it are both "connected state"), optionally
        filtered to `edge_types`. Superseded nodes ARE included by default —
        they remain part of the provenance. This is the paper's §V.B
        context-construction primitive: retrieve the connected state for a
        decision rather than replaying all history.

        `as_of` (bi-temporal): when set to an ISO instant, the neighborhood is
        the one that was VALID then — a CLAIM node is admitted only if it is
        currently-believed (not superseded) AND valid at `as_of`; a claim
        outside its validity is excluded and cannot bridge the traversal.
        NON-claim nodes (entities, sources, runs, ...) are always admitted, so
        provenance is preserved — the Source behind a valid claim still comes
        back. `as_of=None` (the default) reproduces the exact prior behavior.
        """
        if not self.has(node_id):
            raise GraphInvariantError(f"subgraph root {node_id!r} is not in the graph.")
        if hops < 0:
            raise GraphInvariantError("subgraph hops must be >= 0.")
        if as_of is not None:
            _instant_ok(as_of, "as_of")
        # Claims excluded by the bi-temporal filter (empty when as_of is None):
        # they neither appear nor bridge traversal.
        excluded: set = set()
        if as_of is not None:
            for n in self.nodes.values():
                if n.node_type == NodeType.CLAIM and (
                        n.superseded or not _valid_at(n, as_of)):
                    excluded.add(n.id)
            if node_id in excluded:
                raise GraphInvariantError(
                    f"subgraph root {node_id!r} is a Claim that is not valid at "
                    f"as_of {as_of!r}; cannot root an as-of view on it.")
        allowed = set(edge_types) if edge_types is not None else None
        reached = {node_id}
        used_edges: dict = {}
        frontier = {node_id}
        for _ in range(hops):
            nxt = set()
            for e in self.edges.values():
                if allowed is not None and e.edge_type not in allowed:
                    continue
                if e.src in excluded or e.dst in excluded:
                    continue
                if e.src in frontier and e.dst not in reached:
                    nxt.add(e.dst)
                if e.dst in frontier and e.src not in reached:
                    nxt.add(e.src)
                if e.src in reached and e.dst in reached:
                    used_edges[e.key()] = e
                elif e.src in frontier or e.dst in frontier:
                    used_edges[e.key()] = e
            if not nxt:
                break
            reached |= nxt
            frontier = nxt
        # Final pass: keep every edge fully inside the reached set (and allowed).
        for e in self.edges.values():
            if allowed is not None and e.edge_type not in allowed:
                continue
            if e.src in excluded or e.dst in excluded:
                continue
            if e.src in reached and e.dst in reached:
                used_edges[e.key()] = e
        return Subgraph(
            root=node_id,
            hops=hops,
            nodes=[self.nodes[nid] for nid in reached],
            edges=list(used_edges.values()),
        )

    def as_of_subgraph(self, node_id: str, instant: str, hops: int,
                       edge_types: Optional[Iterable[EdgeType]] = None) -> Subgraph:
        """The bounded neighborhood of `node_id` as it was VALID at `instant`.

        Thin, explicit alias for ``subgraph(node_id, hops, edge_types,
        as_of=instant)`` — provided as a named primitive so callers can ask for
        a point-in-time view without threading a keyword. Provenance is
        preserved (see subgraph's `as_of`).
        """
        return self.subgraph(node_id, hops, edge_types, as_of=instant)

    # --- convenience ----------------------------------------------------------
    def copy(self) -> "Graph":
        """A deep-ish copy (nodes/edges/resolutions), for tests and what-ifs."""
        g = Graph()
        g._counter = self._counter
        for nid, node in self.nodes.items():
            g.nodes[nid] = replace(node)
        g.edges = dict(self.edges)
        g.resolutions = [dict(r) for r in self.resolutions]
        return g


def _merge_unique(target: list, incoming: Iterable) -> None:
    """Append items from `incoming` not already in `target`, preserving order."""
    for item in incoming:
        if item and item not in target:
            target.append(item)
