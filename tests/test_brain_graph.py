"""Proof tests for the persistent knowledge-graph brain (brain/).

Greppable summary: each test PROVES one property the founder asked to see,
not a design doc — the four write invariants each raise on violation and
pass when satisfied, supersede keeps the old node addressable, entity
resolution is reversible with no data lost, subgraph returns a bounded
neighborhood with provenance, and a saved graph reloads byte-identical in a
FRESH store (the "does not forget" proof).

These are pure-logic tests: no database, no network.
"""
import pathlib

import pytest

from brain import store
from brain.graph import Graph, GraphInvariantError
from brain.schema import (
    AgentRun,
    Artifact,
    Claim,
    EdgeType,
    Entity,
    Evaluation,
    NodeType,
    Source,
    Task,
)


# --- helpers ------------------------------------------------------------------
def _graph_with_source() -> tuple:
    g = Graph()
    src = g.add_source(Source(uri="https://venue.test/cal", title="Venue calendar"))
    return g, src


# --- Invariant 1: a Claim needs a Source OR inference=True --------------------
def test_invariant1_unsourced_non_inference_claim_raises():
    g, _ = _graph_with_source()
    with pytest.raises(GraphInvariantError):
        g.add_claim(Claim(text="show tonight", source_id=None, inference=False))


def test_invariant1_claim_with_source_passes():
    g, src = _graph_with_source()
    claim = g.add_claim(Claim(text="show tonight", source_id=src.id))
    assert g.has(claim.id)
    # The provenance is also materialised as a traversable edge.
    assert (claim.id, src.id, EdgeType.DERIVED_FROM) in g.edges


def test_invariant1_inference_claim_passes_without_source():
    g, _ = _graph_with_source()
    claim = g.add_claim(Claim(text="probably a rock show", inference=True))
    assert g.has(claim.id)


def test_invariant1_claim_with_dangling_source_raises():
    g, _ = _graph_with_source()
    with pytest.raises(GraphInvariantError):
        g.add_claim(Claim(text="x", source_id="source:999"))


def test_invariant1_claim_source_must_be_a_source_node():
    g, src = _graph_with_source()
    ent = g.add_entity(Entity(name="Mohawk", entity_type="venue"))
    with pytest.raises(GraphInvariantError):
        g.add_claim(Claim(text="x", source_id=ent.id))  # points at an Entity


# --- Invariant 2: an Artifact needs an authoring AgentRun and a version -------
def test_invariant2_artifact_without_run_raises():
    g = Graph()
    with pytest.raises(GraphInvariantError):
        g.add_artifact(Artifact(name="a.txt", authoring_run=None, version="v1"))


def test_invariant2_artifact_without_version_raises():
    g = Graph()
    run = g.add_agent_run(AgentRun(agent="x", objective="y"))
    with pytest.raises(GraphInvariantError):
        g.add_artifact(Artifact(name="a.txt", authoring_run=run.id, version=""))


def test_invariant2_artifact_run_must_be_an_agent_run():
    g, src = _graph_with_source()
    with pytest.raises(GraphInvariantError):
        g.add_artifact(Artifact(name="a.txt", authoring_run=src.id, version="v1"))


def test_invariant2_valid_artifact_passes_and_links_producer():
    g = Graph()
    run = g.add_agent_run(AgentRun(agent="x", objective="y"))
    art = g.add_artifact(Artifact(name="a.txt", authoring_run=run.id, version="v1"))
    assert g.has(art.id)
    assert (run.id, art.id, EdgeType.PRODUCED) in g.edges


# --- Invariant 3: an Evaluation must identify a rubric ------------------------
def test_invariant3_evaluation_without_rubric_raises():
    g = Graph()
    with pytest.raises(GraphInvariantError):
        g.add_evaluation(Evaluation(rubric="", verdict="APPROVE"))


def test_invariant3_evaluation_with_rubric_passes():
    g = Graph()
    run = g.add_agent_run(AgentRun(agent="x", objective="y"))
    art = g.add_artifact(Artifact(name="a.txt", authoring_run=run.id, version="v1"))
    ev = g.add_evaluation(Evaluation(rubric="8-criterion", verdict="APPROVE",
                                     target_id=art.id))
    assert g.has(ev.id)
    assert (ev.id, art.id, EdgeType.EVALUATES) in g.edges


# --- Invariant 4: supersede keeps the old node addressable -------------------
def test_invariant4_supersede_keeps_old_node_and_adds_edge():
    g = Graph()
    run = g.add_agent_run(AgentRun(agent="x", objective="y"))
    v1 = g.add_artifact(Artifact(name="a.txt", authoring_run=run.id, version="v1"))
    v2 = g.add_artifact(Artifact(name="a.txt", authoring_run=run.id, version="v2"))
    g.supersede(v1.id, by=v2.id)

    # Old node is STILL in the store, flagged, and reachable by id.
    assert g.has(v1.id)
    old = g.get(v1.id)
    assert old.superseded is True
    assert old.superseded_by == v2.id
    # Both the SUPERSEDES and REVISES edges were added.
    assert (v2.id, v1.id, EdgeType.SUPERSEDES) in g.edges
    assert (v2.id, v1.id, EdgeType.REVISES) in g.edges


def test_invariant4_cannot_supersede_self():
    g = Graph()
    run = g.add_agent_run(AgentRun(agent="x", objective="y"))
    v1 = g.add_artifact(Artifact(name="a.txt", authoring_run=run.id, version="v1"))
    with pytest.raises(GraphInvariantError):
        g.supersede(v1.id, by=v1.id)


# --- Entity resolution is reversible -----------------------------------------
def test_resolve_entities_is_reversible_with_no_data_lost():
    g = Graph()
    # Two surface forms of the same venue, seen in different docs.
    canon = g.add_entity(Entity(
        name="Mohawk", entity_type="venue",
        aliases=["The Mohawk"], source_docs=["doc:a"], confidence=0.9))
    other = g.add_entity(Entity(
        name="Mohawk Austin", entity_type="venue",
        aliases=["Mohawk ATX"], source_docs=["doc:b"], confidence=0.7))

    canon_aliases_before = list(canon.aliases)
    canon_docs_before = list(canon.source_docs)

    res_id = g.resolve_entities(
        canonical=canon.id, others=[other.id],
        rationale="same venue, same address", confidence=0.95)
    assert res_id.startswith("resolution:")

    # After resolution: canonical retains BOTH surface forms as aliases + docs.
    merged = g.get(canon.id)
    assert "Mohawk Austin" in merged.aliases      # the folded name is retained
    assert "Mohawk ATX" in merged.aliases          # the folded alias is retained
    assert "The Mohawk" in merged.aliases          # canonical's own alias kept
    assert "doc:b" in merged.source_docs           # the folded doc is retained
    assert merged.resolution_rationale == "same venue, same address"
    assert merged.confidence == 0.95
    # The folded entity is superseded but STILL addressable (never deleted).
    folded = g.get(other.id)
    assert folded.superseded is True
    assert folded.canonical_id == canon.id
    assert (other.id, canon.id, EdgeType.RESOLVED_TO) in g.edges

    # Now REVERSE it — both originals come back exactly, no data lost.
    g.unresolve(canon.id)
    restored_canon = g.get(canon.id)
    assert restored_canon.aliases == canon_aliases_before
    assert restored_canon.source_docs == canon_docs_before
    restored_other = g.get(other.id)
    assert restored_other.superseded is False
    assert restored_other.canonical_id is None
    assert restored_other.name == "Mohawk Austin"
    assert restored_other.aliases == ["Mohawk ATX"]
    assert restored_other.source_docs == ["doc:b"]
    # The RESOLVED_TO edge the merge added is gone.
    assert (other.id, canon.id, EdgeType.RESOLVED_TO) not in g.edges


def test_unresolve_without_a_resolution_raises():
    g = Graph()
    ent = g.add_entity(Entity(name="Mohawk", entity_type="venue"))
    with pytest.raises(GraphInvariantError):
        g.unresolve(ent.id)


def test_resolve_requires_rationale():
    g = Graph()
    a = g.add_entity(Entity(name="A", entity_type="venue"))
    b = g.add_entity(Entity(name="B", entity_type="venue"))
    with pytest.raises(GraphInvariantError):
        g.resolve_entities(canonical=a.id, others=[b.id], rationale="", confidence=1.0)


# --- Bounded subgraph with provenance ----------------------------------------
def test_subgraph_returns_bounded_neighborhood_with_provenance():
    g = Graph()
    src = g.add_source(Source(uri="https://v.test", title="cal"))
    venue = g.add_entity(Entity(name="Mohawk", entity_type="venue"))
    claim = g.add_claim(Claim(text="show tonight", source_id=src.id))
    g.add_edge(claim.id, venue.id, EdgeType.MENTIONS)
    # A far-away node that must NOT appear within 1 hop of the venue.
    far_run = g.add_agent_run(AgentRun(agent="x", objective="y"))
    far_task = g.add_task(Task(description="unrelated", status="open"))
    g.add_edge(far_run.id, far_task.id, EdgeType.DEPENDS_ON)

    sg = g.subgraph(venue.id, hops=1)
    ids = sg.node_ids()
    assert venue.id in ids
    assert claim.id in ids          # 1 hop away via MENTIONS
    assert src.id not in ids        # 2 hops away (venue<-claim->source)
    assert far_run.id not in ids    # disconnected
    # Provenance is present: the traversed edge is in the result.
    assert any(e.edge_type == EdgeType.MENTIONS for e in sg.edges)

    # 2 hops reaches the source (the claim's provenance root).
    sg2 = g.subgraph(venue.id, hops=2)
    assert src.id in sg2.node_ids()


def test_subgraph_edge_type_filter():
    g = Graph()
    src = g.add_source(Source(uri="https://v.test", title="cal"))
    venue = g.add_entity(Entity(name="Mohawk", entity_type="venue"))
    claim = g.add_claim(Claim(text="show", source_id=src.id))
    g.add_edge(claim.id, venue.id, EdgeType.MENTIONS)
    # Filtering to DERIVED_FROM only: from the claim we reach the source, not
    # the venue (which is only connected by MENTIONS).
    sg = g.subgraph(claim.id, hops=1, edge_types=[EdgeType.DERIVED_FROM])
    ids = sg.node_ids()
    assert src.id in ids
    assert venue.id not in ids


# --- Persistence: the "does not forget" proof --------------------------------
def _build_rich_graph() -> tuple:
    g = Graph()
    src = g.add_source(Source(uri="https://mohawkaustin.com", title="Mohawk cal"))
    canon = g.add_entity(Entity(name="Mohawk", entity_type="venue",
                                aliases=["The Mohawk"], source_docs=[src.id],
                                confidence=0.9))
    surface = g.add_entity(Entity(name="Mohawk Austin", entity_type="venue",
                                  source_docs=["doc:listing"], confidence=0.7))
    claim = g.add_claim(Claim(text="show tonight 9pm", source_id=src.id))
    g.add_edge(claim.id, canon.id, EdgeType.MENTIONS)
    g.resolve_entities(canonical=canon.id, others=[surface.id],
                       rationale="same venue", confidence=0.95)
    run = g.add_agent_run(AgentRun(agent="foundry", objective="descriptor"))
    art1 = g.add_artifact(Artifact(name="d.txt", authoring_run=run.id, version="v1"))
    art2 = g.add_artifact(Artifact(name="d.txt", authoring_run=run.id, version="v2"))
    g.supersede(art1.id, by=art2.id)
    g.add_evaluation(Evaluation(rubric="8-criterion", verdict="APPROVE",
                                target_id=art2.id))
    return g, canon.id, surface.id, art1.id


def test_persistence_roundtrips_identically(tmp_path: pathlib.Path):
    g, canon_id, surface_id, superseded_art_id = _build_rich_graph()
    path = tmp_path / "brain.jsonl"
    store.save(g, path)

    # Load into a FRESH store object that never saw the original graph.
    recovered = store.load(path)

    # Serialising both must yield identical bytes — full-state identity.
    assert store.dumps(recovered) == store.dumps(g)

    # And spot-check the properties the founder cares about survive the reload:
    # superseded node still addressable + still flagged.
    assert recovered.has(superseded_art_id)
    assert recovered.get(superseded_art_id).superseded is True
    # resolution aliases retained.
    rc = recovered.get(canon_id)
    assert "Mohawk Austin" in rc.aliases
    # resolution history survived, so a reversal is still possible after reload.
    assert len(recovered.resolutions) == 1
    recovered.unresolve(canon_id)
    assert recovered.get(surface_id).superseded is False


def test_persistence_survives_a_truly_fresh_process_state(tmp_path: pathlib.Path):
    # Build, save, then throw the original away entirely and rebuild from disk.
    g, canon_id, surface_id, superseded_art_id = _build_rich_graph()
    node_count = len(g.nodes)
    edge_count = len(g.edges)
    counter = g._counter
    path = tmp_path / "brain.jsonl"
    store.save(g, path)
    del g  # the "agent" is gone

    recovered = store.load(path)
    assert len(recovered.nodes) == node_count
    assert len(recovered.edges) == edge_count
    assert recovered._counter == counter
    # A new node added after reload gets a non-colliding id (counter restored).
    new_src = recovered.add_source(Source(uri="https://new.test", title="new"))
    assert not new_src.id.endswith(f":{counter}")


def test_load_rejects_unknown_field(tmp_path: pathlib.Path):
    # A corrupt row with an unknown field must fail loud, not silently drop data.
    path = tmp_path / "bad.jsonl"
    path.write_text(
        '{"kind": "meta", "counter": 1}\n'
        '{"kind": "node", "node_type": "source", "id": "source:1", '
        '"bogus_field": 42}\n',
        encoding="utf-8")
    with pytest.raises(ValueError):
        store.load(path)


# --- schema sanity ------------------------------------------------------------
def test_node_types_carry_correct_enum():
    assert Source(uri="x").node_type == NodeType.SOURCE
    assert Entity(name="x").node_type == NodeType.ENTITY
    assert Claim(text="x", inference=True).node_type == NodeType.CLAIM
