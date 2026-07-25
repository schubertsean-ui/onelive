"""Phased agent pipeline with lossless handoffs and a closed change loop.

Founder requirement (2026-07-25): chunk the work into phases with clean handoffs
and ZERO loss — "a finder identifying to a compositor packaging it and then an
agent interpreting it and executing and measuring and evaluating and changing and
on and on." This is that pipeline, as running code, not a diagram.

Seven ordered phases, each a distinct ROLE with a typed input->output contract:

  FIND       identify raw candidate signal          (the finder)
  COMPOSE    package it into a structured record     (the compositor)
  INTERPRET  read the package, decide what it means  (the interpreter)
  EXECUTE    carry out the decided action            (the executor)
  MEASURE    quantify what the execution produced    (the measurer)
  EVALUATE   judge the measurement against a rubric  (the evaluator)
  CHANGE     adapt: emit the next finding/task       (the changer -> loops)

Two properties make this more than a for-loop:

  1. ZERO LOSS between phases (brain/pipeline/handoff.py). Every phase's output
     is persisted to the knowledge-graph brain and validated so no load-bearing
     field can silently vanish; the reader of phase N+1 loads phase N's artifact
     from the DURABLE store (not an in-memory hand-me-down), so a crash between
     phases loses nothing. `trace()` reconstructs the whole chain; the finder's
     original fields are provably recoverable at the changer.

  2. THE LOOP CLOSES. CHANGE writes a Metric (the measurement), an Evaluation
     (the verdict, against a named rubric), and a follow-up Task into the graph,
     wired with edges, and returns a fresh finding payload — so "measure ->
     evaluate -> change -> and on and on" is a real cycle the graph records, not
     a dead end.

A Stage is just a function `(StageContext) -> StageResult`; the runner owns
persistence, zero-loss validation, provenance edges, and (optionally) saving to
disk between phases. Callers supply the seven roles (or their own set) — the
DEFAULT_STAGES below are a complete, runnable OneLive example (a discovered
source becoming a promotion decision) used by the demo and the tests.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from brain.graph import Graph
from brain.pipeline.handoff import (
    HandoffArtifact,
    emit_handoff,
    load_handoff,
    origin_fields_preserved,
    trace,
)
from brain.schema import AgentRun, EdgeType, Evaluation, Metric, Task


class Stage(enum.Enum):
    """The seven ordered phases. `.order` gives their fixed sequence."""

    FIND = "find"
    COMPOSE = "compose"
    INTERPRET = "interpret"
    EXECUTE = "execute"
    MEASURE = "measure"
    EVALUATE = "evaluate"
    CHANGE = "change"

    @classmethod
    def order(cls) -> List["Stage"]:
        return [cls.FIND, cls.COMPOSE, cls.INTERPRET, cls.EXECUTE,
                cls.MEASURE, cls.EVALUATE, cls.CHANGE]


@dataclass
class StageContext:
    """What a stage function receives: the durable graph, the upstream handoff
    (None for FIND), and the stage's own AgentRun id. A stage reads its input
    from `upstream.payload` and returns a StageResult — it never touches the
    store directly, so persistence and zero-loss stay the runner's job."""

    graph: Graph
    stage: Stage
    run_id: str
    upstream: Optional[HandoffArtifact]


@dataclass
class StageResult:
    """A stage's declared output: the new payload, plus the on-the-record fate of
    any upstream field it did not pass through verbatim. `transformed` maps an
    old key to the new key that now holds its information; `consumed` maps an old
    key to the REASON it was folded away. Anything omitted from both must survive
    verbatim in `payload`, or the handoff fails closed."""

    payload: Dict
    transformed: Dict[str, str] = field(default_factory=dict)
    consumed: Dict[str, str] = field(default_factory=dict)


Stagefn = Callable[[StageContext], StageResult]


@dataclass
class PipelineResult:
    """The outcome of one full pass: the ordered handoff chain, the terminal
    artifact id, the follow-up Task id the changer opened, and the field-fate
    ledger proving every origin field is accounted for."""

    handoffs: List[HandoffArtifact]
    final_artifact_id: str
    followup_task_id: Optional[str]
    origin_field_fate: Dict[str, str]


def run_pipeline(
    graph: Graph,
    stages: List[tuple],
    *,
    pipeline_name: str = "onelive-pipeline",
    save_hook: Optional[Callable[[Graph], None]] = None,
) -> PipelineResult:
    """Run an ordered list of ``(Stage, Stagefn)`` phases with lossless handoffs.

    Each phase gets its own AgentRun (a bounded execution record), reads its
    input by LOADING the prior phase's artifact from the graph (durable handoff,
    not an in-memory pass), and emits its output through the zero-loss validator.
    `save_hook`, if given, is called after every phase with the graph — pass
    ``lambda g: store.save(g, path)`` to make each handoff crash-durable.

    Raises LossyHandoffError (from emit_handoff) the instant a phase would drop a
    load-bearing field, before that phase's artifact is written.
    """
    upstream: Optional[HandoffArtifact] = None
    handoffs: List[HandoffArtifact] = []

    for stage, fn in stages:
        run = graph.add_agent_run(AgentRun(
            agent=f"{pipeline_name}:{stage.value}",
            objective=f"{stage.value} phase of {pipeline_name}",
            status="started",
        ))
        # Durable handoff: re-load the upstream artifact from the graph by id so
        # the phase reads persisted truth, not a memory hand-me-down.
        upstream_reloaded = (
            load_handoff(graph, upstream.artifact_id) if upstream is not None else None
        )
        ctx = StageContext(graph=graph, stage=stage, run_id=run.id,
                           upstream=upstream_reloaded)
        result = fn(ctx)
        handoff = emit_handoff(
            graph,
            stage=stage.value,
            run_id=run.id,
            payload=result.payload,
            upstream=upstream_reloaded,
            transformed=result.transformed,
            consumed=result.consumed,
        )
        run.status = "succeeded"
        handoffs.append(handoff)
        upstream = handoff
        if save_hook is not None:
            save_hook(graph)

    final_id = handoffs[-1].artifact_id
    followup = _close_the_loop(graph, handoffs)
    if save_hook is not None:
        save_hook(graph)

    return PipelineResult(
        handoffs=handoffs,
        final_artifact_id=final_id,
        followup_task_id=followup,
        origin_field_fate=origin_fields_preserved(graph, final_id),
    )


def _close_the_loop(graph: Graph, handoffs: List[HandoffArtifact]) -> Optional[str]:
    """Record measure -> evaluate -> change as a real cycle in the graph.

    Reads the MEASURE and EVALUATE phase payloads (if present), writes a Metric
    node for the measurement and an Evaluation node (against its rubric) for the
    verdict, then opens a follow-up Task representing the CHANGE the changer
    proposed — wiring DEPENDS_ON edges so the next finding is provably linked to
    the evidence that motivated it. Returns the Task id (or None if the chain had
    no change payload).
    """
    by_stage = {h.stage: h for h in handoffs}
    change = by_stage.get(Stage.CHANGE.value)
    if change is None:
        return None

    measure = by_stage.get(Stage.MEASURE.value)
    evaluate = by_stage.get(Stage.EVALUATE.value)

    metric_id = None
    if measure is not None:
        m = measure.payload
        metric = graph.add_metric(Metric(
            name=str(m.get("metric_name", "measurement")),
            value=float(m.get("metric_value", 0.0)),
            unit=str(m.get("metric_unit", "")),
        ))
        metric_id = metric.id
        graph.add_edge(metric.id, measure.artifact_id, EdgeType.DERIVED_FROM)

    eval_id = None
    if evaluate is not None:
        e = evaluate.payload
        ev = graph.add_evaluation(Evaluation(
            rubric=str(e.get("rubric", "pipeline-default")),
            verdict=str(e.get("verdict", "UNKNOWN")),
            target_id=evaluate.artifact_id,
            notes=str(e.get("notes", "")),
        ))
        eval_id = ev.id

    task = graph.add_task(Task(
        description=str(change.payload.get("next_action", "follow-up change")),
        status="open",
    ))
    # The follow-up work DEPENDS_ON the change artifact, and (transitively) on the
    # measurement + evaluation that justified it — the loop, recorded.
    graph.add_edge(task.id, change.artifact_id, EdgeType.DEPENDS_ON)
    if metric_id is not None:
        graph.add_edge(task.id, metric_id, EdgeType.DEPENDS_ON)
    if eval_id is not None:
        graph.add_edge(task.id, eval_id, EdgeType.DEPENDS_ON)
    return task.id


# Re-export trace for callers that want the provenance walk.
__all__ = [
    "Stage", "StageContext", "StageResult", "Stagefn",
    "PipelineResult", "run_pipeline", "trace",
]
