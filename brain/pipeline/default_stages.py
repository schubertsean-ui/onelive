"""The seven default OneLive pipeline roles — a complete, runnable example.

A discovered source ("finder") becomes a packaged candidate ("compositor"),
interpreted into a category+promotion intent ("interpreter"), executed into a
card ("executor"), measured ("measurer"), judged ("evaluator"), and turned into
the next action ("changer"). Each role demonstrates the handoff contract,
including a deliberate TRANSFORM and a deliberate CONSUME so the zero-loss
accounting is exercised end to end — every origin field is still traceable at the
changer, none silently dropped.

These are intentionally pure/deterministic (no network, no DB, no AI call) so the
pipeline mechanics are testable in isolation; in production each role's body is
where a real subagent/tool call goes, but the CONTRACT it must honor is exactly
this — return a payload and declare the fate of every upstream field.
"""
from __future__ import annotations

from brain.pipeline.runner import Stage, StageContext, StageResult


def find(ctx: StageContext) -> StageResult:
    """FIND: identify a raw candidate signal. Origin stage — everything it emits
    becomes load-bearing for the whole chain."""
    return StageResult(payload={
        "source_name": "Mohawk Austin",
        "source_url": "https://mohawkaustin.com/",
        "raw_title": "The Black Angels — Levitation Night",
        "raw_date_text": "Fri, Nov 7",
        "discovered_by": "finder/venue-calendar-sweep",
    })


def compose(ctx: StageContext) -> StageResult:
    """COMPOSE: package the raw signal into a structured record. Carries every
    finder field forward verbatim and adds structure."""
    p = ctx.upstream.payload
    return StageResult(payload={
        **p,  # every finder field survives verbatim
        "structured": {
            "title": p["raw_title"],
            "date_text": p["raw_date_text"],
            "venue": p["source_name"],
        },
    })


def interpret(ctx: StageContext) -> StageResult:
    """INTERPRET: read the package, decide meaning. TRANSFORMS the raw title into
    a normalized performer+event and records the category decision — the raw
    field's information moves to `performer`, declared, not dropped."""
    p = ctx.upstream.payload
    payload = {k: v for k, v in p.items() if k != "raw_title"}
    payload["performer"] = "The Black Angels"
    payload["category"] = "live-music"  # Mohawk is a curated live-music venue
    payload["category_signal"] = "venue business type (curated cultural_domain)"
    return StageResult(
        payload=payload,
        transformed={"raw_title": "performer"},
    )


def execute(ctx: StageContext) -> StageResult:
    """EXECUTE: carry out the action — assemble the user-facing card. CONSUMES the
    intermediate `structured` scratch dict (its info is now in the card), with a
    recorded reason."""
    p = ctx.upstream.payload
    payload = {k: v for k, v in p.items() if k != "structured"}
    payload["card"] = {
        "title": p["performer"],
        "category": p["category"],
        "venue": p["source_name"],
    }
    payload["promotion_intent"] = "ready_for_ops_promote"
    return StageResult(
        payload=payload,
        consumed={"structured": "folded into the assembled card; not needed downstream"},
    )


def measure(ctx: StageContext) -> StageResult:
    """MEASURE: quantify what execution produced (here: card completeness)."""
    p = ctx.upstream.payload
    card = p["card"]
    completeness = sum(1 for v in card.values() if v) / len(card)
    return StageResult(payload={
        **p,
        "metric_name": "card_completeness",
        "metric_value": completeness,
        "metric_unit": "ratio",
    })


def evaluate(ctx: StageContext) -> StageResult:
    """EVALUATE: judge the measurement against a rubric."""
    p = ctx.upstream.payload
    verdict = "PASS" if p["metric_value"] >= 0.75 else "REQUEST-CHANGES"
    return StageResult(payload={
        **p,
        "rubric": "card-ready-for-promote/v1",
        "verdict": verdict,
        "notes": f"completeness={p['metric_value']:.2f}",
    })


def change(ctx: StageContext) -> StageResult:
    """CHANGE: adapt — decide the next action, closing the loop. The runner turns
    this into a Metric + Evaluation + follow-up Task in the graph."""
    p = ctx.upstream.payload
    if p["verdict"] == "PASS":
        nxt = f"queue {p['performer']!r} for ops promote at {p['source_name']}"
    else:
        nxt = f"re-find missing fields for {p['performer']!r} before promote"
    return StageResult(payload={**p, "next_action": nxt})


DEFAULT_STAGES = [
    (Stage.FIND, find),
    (Stage.COMPOSE, compose),
    (Stage.INTERPRET, interpret),
    (Stage.EXECUTE, execute),
    (Stage.MEASURE, measure),
    (Stage.EVALUATE, evaluate),
    (Stage.CHANGE, change),
]
