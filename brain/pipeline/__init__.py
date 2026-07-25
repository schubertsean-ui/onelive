"""OneLive phased agent pipeline with lossless handoffs.

The public surface: run a chain of typed phases where no load-bearing field can
silently vanish between stages, every handoff is persisted + traceable in the
knowledge-graph brain, and the measure->evaluate->change loop closes into the
graph. See brain/pipeline/runner.py and docs/strategy/ONE_LIVE_AGENT_PIPELINE_v1.md.
"""
from brain.pipeline.handoff import (
    HandoffArtifact,
    LossyHandoffError,
    emit_handoff,
    load_handoff,
    origin_fields_preserved,
    trace,
)
from brain.pipeline.runner import (
    PipelineResult,
    Stage,
    StageContext,
    StageResult,
    run_pipeline,
)

__all__ = [
    "HandoffArtifact",
    "LossyHandoffError",
    "emit_handoff",
    "load_handoff",
    "origin_fields_preserved",
    "trace",
    "PipelineResult",
    "Stage",
    "StageContext",
    "StageResult",
    "run_pipeline",
]
