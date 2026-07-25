"""Runnable proof that the brain does not forget: `python -m brain.demo`.

Greppable summary: builds a small OneLive-shaped knowledge graph (a Source,
a Claim about the venue "Mohawk" with the surface form "Mohawk Austin"
resolved into it, an AgentRun that PRODUCED an Artifact, and an Evaluation
against a rubric), SAVES it to a temp file, then RELOADS it in a FRESH,
empty graph and prints the recovered subgraph. The point the founder can SEE:
the second graph was built by a different object that never saw the first —
everything it knows, it read back off disk.

Run it: `python -m brain.demo`
"""
from __future__ import annotations

import pathlib
import tempfile

from brain import store
from brain.graph import Graph
from brain.schema import (
    AgentRun,
    Artifact,
    Claim,
    EdgeType,
    Entity,
    Evaluation,
    Source,
)


def build_demo_graph() -> tuple:
    """Build the small OneLive-shaped graph. Returns (graph, mohawk_entity_id)."""
    g = Graph()

    # A provenance root: where we read the fact.
    src = g.add_source(Source(
        uri="https://mohawkaustin.com/calendar",
        title="Mohawk Austin — official calendar",
        description="Venue's own event listing, fetched by the ingestion loop.",
    ))

    # The canonical venue entity, and a separate surface form seen elsewhere.
    mohawk = g.add_entity(Entity(
        name="Mohawk",
        entity_type="venue",
        aliases=["The Mohawk"],
        source_docs=[src.id],
        confidence=0.9,
    ))
    surface = g.add_entity(Entity(
        name="Mohawk Austin",
        entity_type="venue",
        aliases=[],
        source_docs=["https://example-listing.test/mohawk-austin"],
        confidence=0.7,
    ))

    # A sourced claim about the venue (Invariant 1 satisfied by src.id).
    claim = g.add_claim(Claim(
        text="Mohawk hosts a show tonight at 9pm.",
        source_id=src.id,
        confidence=0.8,
    ))
    g.add_edge(claim.id, mohawk.id, EdgeType.MENTIONS)

    # BI-TEMPORAL: the venue's capacity moved through eras. Two LIVE claims,
    # each stamped with the VALID interval it held (500 until 2026-03-01, then
    # 800). Nothing is superseded — valid time alone says which one was true
    # when. This is what lets the brain answer "what was true as of date X".
    cap_500 = g.add_claim(Claim(text="capacity=500", source_id=src.id),
                          valid_from="2026-01-01", valid_to="2026-03-01")
    g.add_edge(cap_500.id, mohawk.id, EdgeType.MENTIONS)
    cap_800 = g.add_claim(Claim(text="capacity=800", source_id=src.id),
                          valid_from="2026-03-01")  # open interval = still true
    g.add_edge(cap_800.id, mohawk.id, EdgeType.MENTIONS)

    # Resolve the surface form into the canonical entity — reversibly.
    g.resolve_entities(
        canonical=mohawk.id,
        others=[surface.id],
        rationale='"Mohawk Austin" is the same venue as "Mohawk" (same address, '
                  "same calendar); folded on name+city match.",
        confidence=0.95,
    )

    # An agent run that PRODUCED an artifact (Invariant 2 needs run + version).
    run = g.add_agent_run(AgentRun(
        agent="descriptor-foundry",
        objective="Draft a one-line descriptor for tonight's Mohawk show.",
        status="succeeded",
    ))
    artifact = g.add_artifact(Artifact(
        name="mohawk_descriptor.txt",
        authoring_run=run.id,
        version="v1",
        content="Sweaty rock on the patio — doors at 9.",
    ))

    # An evaluation against a named rubric (Invariant 3 needs a rubric).
    g.add_evaluation(Evaluation(
        rubric="descriptor-foundry-8-criterion",
        verdict="APPROVE",
        target_id=artifact.id,
        notes="Facts intact, style within brief.",
    ))

    return g, mohawk.id


def main() -> int:
    g, mohawk_id = build_demo_graph()

    print("=" * 72)
    print("ONE LIVE brain demo — the agent forgets, the graph does not.")
    print("=" * 72)
    print()
    print("Built a graph in memory:")
    print(f"  nodes:       {len(g.nodes)}")
    print(f"  edges:       {len(g.edges)}")
    print(f"  resolutions: {len(g.resolutions)} (reversible entity merges)")
    print()
    canon = g.get(mohawk_id)
    print(f"Canonical venue entity {canon.id}: name={canon.name!r}")
    print(f"  aliases retained after resolution: {canon.aliases}")
    print(f"  source_docs retained:              {canon.source_docs}")
    print()

    # Persist, then reload in a FRESH graph object that never saw the original.
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "brain.jsonl"
        store.save(g, path)
        print(f"Saved to disk: {path} ({path.stat().st_size} bytes)")
        print()
        print("--- process boundary: loading into a FRESH, empty graph ---")
        recovered = store.load(path)

    print(f"Recovered graph: {len(recovered.nodes)} nodes, "
          f"{len(recovered.edges)} edges, "
          f"{len(recovered.resolutions)} resolutions.")
    print()

    # Show the bounded neighborhood of the venue, straight from the reloaded graph.
    sg = recovered.subgraph(mohawk_id, hops=2)
    print("Recovered subgraph around the Mohawk venue (2 hops), with provenance:")
    print(sg.describe())
    print()

    # BI-TEMPORAL point-in-time recall, straight off the reloaded graph: "what
    # was the capacity as of date X, and when did it change?"
    def _cap_at(instant: str) -> str:
        hits = recovered.claims_valid_at(mohawk_id, instant, predicate="capacity")
        return hits[0].text.split("=", 1)[1] if hits else "unknown"

    print("Bi-temporal recall — Mohawk capacity as of a queried instant:")
    for instant in ("2025-12-01", "2026-02-01", "2026-05-01"):
        print(f"  as of {instant}: capacity = {_cap_at(instant)}")
    print("  (500 until 2026-03-01, then 800 — the graph remembers WHEN, "
          "not just THAT it changed.)")
    print()

    # Prove the folded surface form is STILL addressable after the reload.
    rec_canon = recovered.get(mohawk_id)
    surface_ids = [s["id"] for r in recovered.resolutions for s in r["others"]]
    print(f"Canonical after reload: name={rec_canon.name!r}, "
          f"aliases={rec_canon.aliases}")
    for sid in surface_ids:
        s = recovered.get(sid)
        print(f"  folded surface form {sid} still addressable: name={s.name!r}, "
              f"superseded={s.superseded}, canonical_id={s.canonical_id}")
    print()
    print("It did not forget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
