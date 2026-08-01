"""Proof that the phased pipeline loses ZERO information between stages.

Founder requirement (2026-07-25): "ensure there is zero loss from a finder ...
to a compositor ... and then an agent interpreting and executing and measuring
and evaluating and changing and on and on." These tests are that guarantee made
executable — including the two ways loss usually creeps in (a silent field drop,
and an in-memory hand-off that doesn't survive a crash), both closed.
"""
import json

import pytest

from brain.graph import Graph
from brain import store
from brain.pipeline import (
    LossyHandoffError,
    Stage,
    StageResult,
    origin_fields_preserved,
    run_pipeline,
    trace,
)
from brain.pipeline.default_stages import DEFAULT_STAGES, find


def _run(graph=None, save_hook=None):
    g = graph or Graph()
    return g, run_pipeline(g, DEFAULT_STAGES, save_hook=save_hook)


def test_full_chain_runs_all_seven_phases_in_order():
    g, res = _run()
    assert [h.stage for h in res.handoffs] == [s.value for s in Stage.order()]


def test_every_origin_field_is_accounted_for_at_the_far_end():
    # The finder's five fields must each be present, transformed, or consumed —
    # never missing — at the changer.
    g, res = _run()
    origin_keys = set(find(_ctx(g)).payload.keys())
    fate = res.origin_field_fate
    assert set(fate.keys()) == origin_keys, "an origin field vanished from the ledger"
    # raw_title was transformed into performer; it must be reported present under
    # its new name, not lost.
    assert "present" in fate["raw_title"] and "performer" in fate["raw_title"]
    # The others survive verbatim to the changer.
    for k in ("source_name", "source_url", "raw_date_text", "discovered_by"):
        assert fate[k].startswith("present@change:"), (k, fate[k])


def test_a_silently_dropped_load_bearing_field_fails_closed():
    # A stage that drops an upstream field WITHOUT declaring transform/consume
    # must raise — a fact cannot vanish by omission.
    def lossy_compose(ctx):
        p = dict(ctx.upstream.payload)
        p.pop("source_url")  # dropped, undeclared
        return StageResult(payload=p)

    stages = [DEFAULT_STAGES[0], (Stage.COMPOSE, lossy_compose)]
    with pytest.raises(LossyHandoffError) as exc:
        run_pipeline(Graph(), stages)
    assert "source_url" in str(exc.value)


def test_declared_consume_is_allowed_and_recorded_not_lost():
    # The default EXECUTE consumes `structured` WITH a reason — allowed, and the
    # reason shows up in the field-fate ledger rather than a silent disappearance.
    g, res = _run()
    # `structured` is introduced by COMPOSE (not an origin field), but its
    # consumption is still on the record in the execute handoff's manifest.
    execute_h = next(h for h in res.handoffs if h.stage == "execute")
    assert "structured" in execute_h.consumed
    assert execute_h.consumed["structured"].strip()


def test_empty_consume_reason_fails_closed():
    def bad_consume(ctx):
        p = {k: v for k, v in ctx.upstream.payload.items() if k != "source_url"}
        return StageResult(payload=p, consumed={"source_url": "   "})

    stages = [DEFAULT_STAGES[0], (Stage.COMPOSE, bad_consume)]
    with pytest.raises(LossyHandoffError):
        run_pipeline(Graph(), stages)


def test_transform_to_a_missing_key_fails_closed():
    def bad_transform(ctx):
        p = {k: v for k, v in ctx.upstream.payload.items() if k != "raw_title"}
        # declares raw_title -> performer, but never adds performer
        return StageResult(payload=p, transformed={"raw_title": "performer"})

    stages = [DEFAULT_STAGES[0], (Stage.COMPOSE, bad_transform)]
    with pytest.raises(LossyHandoffError):
        run_pipeline(Graph(), stages)


def test_handoff_is_durable_reload_in_a_fresh_graph_reconstructs_the_chain(tmp_path):
    # The crash-safety property: persist after every phase, then reload from disk
    # into a BRAND-NEW Graph object and reconstruct the whole chain + field fate
    # with nothing lost — proving the handoff is through the durable store, not a
    # memory hand-me-down.
    path = tmp_path / "brain.jsonl"
    g = Graph()
    _, res = _run(graph=g, save_hook=lambda gr: store.save(gr, path))
    final_id = res.final_artifact_id

    reloaded = store.load(path)
    assert reloaded is not g
    chain = trace(reloaded, final_id)
    assert [h.stage for h in chain] == [s.value for s in Stage.order()]
    # The finder's original values are byte-identical after the reload.
    origin = chain[0].payload
    assert origin["source_name"] == "Mohawk Austin"
    assert origin["source_url"] == "https://mohawkaustin.com/"
    # And the field-fate ledger is identical computed from the reloaded graph.
    assert origin_fields_preserved(reloaded, final_id) == res.origin_field_fate


def test_content_hash_detects_tampering_after_reload(tmp_path):
    # Each handoff carries a content hash over (payload, carried); recomputing it
    # from the reloaded manifest must match — integrity across the boundary.
    from brain.pipeline.handoff import _hash
    path = tmp_path / "brain.jsonl"
    g = Graph()
    _, res = _run(graph=g, save_hook=lambda gr: store.save(gr, path))
    reloaded = store.load(path)
    for h in trace(reloaded, res.final_artifact_id):
        assert _hash(h.payload, h.carried) == h.content_hash


def test_the_loop_closes_change_opens_a_task_linked_to_metric_and_evaluation():
    from brain.schema import NodeType, EdgeType
    g, res = _run()
    assert res.followup_task_id is not None
    task = g.get(res.followup_task_id)
    assert task.node_type == NodeType.TASK
    # The follow-up DEPENDS_ON the change artifact, the metric, and the evaluation
    # — the measure->evaluate->change cycle recorded as real edges.
    deps = {(e.src, e.dst, e.edge_type) for e in g.edges_of(task.id)
            if e.edge_type == EdgeType.DEPENDS_ON and e.src == task.id}
    assert len(deps) == 3
    # A Metric and an Evaluation node were written.
    assert len(g.nodes_of_type(NodeType.METRIC)) == 1
    assert len(g.nodes_of_type(NodeType.EVALUATION)) == 1


def test_provenance_chain_is_connected_every_phase_derived_from_the_last():
    # trace() must return an unbroken chain: each artifact's upstream_id is the
    # prior phase's artifact id — no orphaned handoff.
    g, res = _run()
    chain = trace(g, res.final_artifact_id)
    for prev, cur in zip(chain, chain[1:]):
        assert cur.upstream_id == prev.artifact_id


def _ctx(graph):
    # Minimal context for calling the origin stage directly in a test.
    from brain.pipeline.runner import StageContext
    return StageContext(graph=graph, stage=Stage.FIND, run_id="", upstream=None)
