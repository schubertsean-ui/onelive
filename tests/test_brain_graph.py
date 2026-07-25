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


# --- Bi-temporal VALID time: "what was true as of date X" --------------------
def _bitemporal_capacity_graph() -> tuple:
    """A venue whose capacity moved through eras: 500 until 2026-03-01, then
    800 until 2026-06-01, then 1000 (still true). Three LIVE claims, no
    supersede — valid time alone distinguishes the eras."""
    g = Graph()
    src = g.add_source(Source(uri="https://permit.test", title="permit history"))
    venue = g.add_entity(Entity(name="Mohawk", entity_type="venue"))

    def cap(value, vf, vt):
        c = g.add_claim(Claim(text=f"capacity={value}", source_id=src.id),
                        valid_from=vf, valid_to=vt)
        g.add_edge(c.id, venue.id, EdgeType.MENTIONS)
        return c

    c500 = cap("500", "2026-01-01", "2026-03-01")
    c800 = cap("800", "2026-03-01", "2026-06-01")
    c1000 = cap("1000", "2026-06-01", None)
    return g, venue.id, src.id, (c500, c800, c1000)


def _value_at(g, entity_id, instant):
    claims = g.claims_valid_at(entity_id, instant, predicate="capacity")
    assert len(claims) == 1, f"expected exactly one valid claim at {instant}"
    return claims[0].text.split("=", 1)[1]


def test_as_of_returns_the_historically_correct_value():
    g, venue_id, _, _ = _bitemporal_capacity_graph()
    # Each instant lands in a different era — this is the point-in-time recall
    # the old substrate could not serve (R-010/R-031).
    assert _value_at(g, venue_id, "2026-02-01") == "500"
    assert _value_at(g, venue_id, "2026-04-01") == "800"
    assert _value_at(g, venue_id, "2026-07-01") == "1000"
    # Half-open [valid_from, valid_to): the boundary belongs to the NEXT era.
    assert _value_at(g, venue_id, "2026-03-01") == "800"
    assert _value_at(g, venue_id, "2026-06-01") == "1000"
    # Before any recorded era: nothing was valid → the brain must not fabricate.
    assert g.claims_valid_at(venue_id, "2025-12-01", predicate="capacity") == []


def test_a_superseded_in_valid_time_fact_is_retrieved_for_its_era():
    # A fact valid for a bounded era stays retrievable for that era forever, even
    # as later eras are added — retrieval is by VALID time, not "latest".
    g, venue_id, _, (c500, c800, c1000) = _bitemporal_capacity_graph()
    assert _value_at(g, venue_id, "2026-02-15") == "500"   # the earliest era
    # The current (open-interval) fact is the still-true one.
    open_claims = [c for c in g.claims_valid_at(venue_id, "2026-09-01",
                                                predicate="capacity")]
    assert [c.id for c in open_claims] == [c1000.id]


def test_claims_valid_at_honors_supersession():
    # Bi-temporal TRANSACTION axis: if the era-500 claim is CORRECTED (superseded
    # by a re-measured value for the same era), the retracted version is not
    # returned for its era — only the currently-believed one.
    g, venue_id, src_id, (c500, c800, c1000) = _bitemporal_capacity_graph()
    corrected = g.add_claim(Claim(text="capacity=550", source_id=src_id),
                            valid_from="2026-01-01", valid_to="2026-03-01")
    g.add_edge(corrected.id, venue_id, EdgeType.MENTIONS)
    g.supersede(c500.id, by=corrected.id)
    # The queried instant is in the era-1 interval; only the corrected value
    # speaks for it (the superseded 500 is excluded).
    assert _value_at(g, venue_id, "2026-02-01") == "550"


def test_timeless_claim_is_always_valid():
    # A claim with no interval is valid at EVERY instant (unchanged behavior).
    g, src = _graph_with_source()
    venue = g.add_entity(Entity(name="Mohawk", entity_type="venue"))
    c = g.add_claim(Claim(text="genre=rock", source_id=src.id))  # timeless
    g.add_edge(c.id, venue.id, EdgeType.MENTIONS)
    for instant in ("1999-01-01", "2026-07-01", "2500-12-31"):
        got = g.claims_valid_at(venue.id, instant, predicate="genre")
        assert [x.id for x in got] == [c.id]


def test_as_of_subgraph_filters_by_validity_and_preserves_provenance():
    g, venue_id, src_id, (c500, c800, c1000) = _bitemporal_capacity_graph()
    # As-of 2026-02-01: only the era-1 claim is valid; its Source is still
    # reachable (provenance preserved), and the other eras' claims are absent.
    sg = g.as_of_subgraph(venue_id, "2026-02-01", hops=2)
    ids = sg.node_ids()
    assert c500.id in ids
    assert c800.id not in ids
    assert c1000.id not in ids
    assert src_id in ids  # the valid claim's provenance root survives
    # A later instant swaps which claim appears — the neighborhood is temporal.
    sg2 = g.as_of_subgraph(venue_id, "2026-07-01", hops=2)
    ids2 = sg2.node_ids()
    assert c1000.id in ids2
    assert c500.id not in ids2


def test_add_claim_bitemporal_params_and_backward_compat():
    g, src = _graph_with_source()
    # 1) kwargs on add_claim set the interval.
    c1 = g.add_claim(Claim(text="capacity=500", source_id=src.id),
                     valid_from="2026-01-01", valid_to="2026-03-01")
    assert c1.valid_from == "2026-01-01" and c1.valid_to == "2026-03-01"
    # 2) interval carried on the Claim itself also works.
    c2 = g.add_claim(Claim(text="capacity=800", source_id=src.id,
                           valid_from="2026-03-01"))
    assert c2.valid_from == "2026-03-01" and c2.valid_to is None
    # 3) existing callers pass neither → a TIMELESS claim, exactly as before.
    c3 = g.add_claim(Claim(text="genre=rock", source_id=src.id))
    assert c3.valid_from is None and c3.valid_to is None
    # 4) an empty/inverted interval is rejected loud (invariant, fail-closed).
    with pytest.raises(GraphInvariantError):
        g.add_claim(Claim(text="capacity=1", source_id=src.id),
                    valid_from="2026-06-01", valid_to="2026-01-01")


def test_write_invariants_still_hold_with_valid_intervals():
    # Adding validity does NOT weaken invariant 1: an unsourced, non-inference
    # claim is still refused even with a perfectly good interval.
    g, _ = _graph_with_source()
    with pytest.raises(GraphInvariantError):
        g.add_claim(Claim(text="capacity=500", source_id=None, inference=False),
                    valid_from="2026-01-01", valid_to="2026-03-01")
    # An inference claim with an interval is admissible (invariant 1 satisfied).
    ok = g.add_claim(Claim(text="capacity~=500", inference=True),
                     valid_from="2026-01-01", valid_to="2026-03-01")
    assert g.has(ok.id)


def test_persistence_roundtrips_bitemporal_claims(tmp_path: pathlib.Path):
    g, venue_id, src_id, (c500, c800, c1000) = _bitemporal_capacity_graph()
    path = tmp_path / "bitemporal.jsonl"
    store.save(g, path)
    recovered = store.load(path)
    # Full-state identity, including the valid_from/valid_to fields.
    assert store.dumps(recovered) == store.dumps(g)
    # And the point-in-time read still works after a fresh reload.
    got = recovered.claims_valid_at(venue_id, "2026-04-01", predicate="capacity")
    assert len(got) == 1 and got[0].text == "capacity=800"
    rc = recovered.get(c500.id)
    assert rc.valid_from == "2026-01-01" and rc.valid_to == "2026-03-01"


# --- schema sanity ------------------------------------------------------------
def test_node_types_carry_correct_enum():
    assert Source(uri="x").node_type == NodeType.SOURCE
    assert Entity(name="x").node_type == NodeType.ENTITY
    assert Claim(text="x", inference=True).node_type == NodeType.CLAIM
