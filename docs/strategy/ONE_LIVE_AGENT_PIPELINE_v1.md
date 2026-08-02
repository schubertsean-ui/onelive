# 1Live Agent Pipeline v1 — phased work with lossless handoffs

Founder directive (2026-07-25): *"chunk the agent work into phases and having
handoffs and ensuring there is zero loss from a, for example, finder identifying
to a compositor packaging it and then an agent interpreting it and executing and
measuring and evaluating and changing and on and on."*

This is the built system, not a proposal. Code: `brain/pipeline/`. Proof:
`tests/test_pipeline_handoff.py` (10 tests). Live demo: `python -m
brain.pipeline.demo`.

## The seven phases

Each phase is a distinct role with a typed input→output contract. Work moves one
direction; nothing skips a phase.

| Phase | Role | Produces |
|---|---|---|
| **FIND** | finder | a raw candidate signal (the origin fields) |
| **COMPOSE** | compositor | a structured, packaged record |
| **INTERPRET** | interpreter | meaning: category, decision, intent |
| **EXECUTE** | executor | the carried-out action (e.g. an assembled card) |
| **MEASURE** | measurer | a quantified result (name, value, unit) |
| **EVALUATE** | evaluator | a verdict against a named rubric |
| **CHANGE** | changer | the next action — closes the loop |

A phase is just a function `(StageContext) -> StageResult`. You can supply your
own set; `brain/pipeline/default_stages.py` is a complete runnable example
(a discovered Mohawk source → a promotion decision).

## Why it can't lose information (the two failure modes, both closed)

**1. Silent field drop.** The usual way a chain leaks: each stage re-summarizes
the last, and a summary quietly omits a field. Here, every phase output carries a
`carried` set — the load-bearing keys — and a field can leave that set ONLY by:

- surviving verbatim into the next payload, or
- being **transformed** (`{old_key: new_key}`; the new key must be present), or
- being **consumed** (`{old_key: reason}` — a written reason is required).

Any carried key that just disappears raises `LossyHandoffError` and the handoff
does not happen. You cannot drop a fact by forgetting it; only by declaring where
it went. `origin_fields_preserved()` then reports, for every field the finder
emitted, exactly where it is at the far end — never "lost."

**2. In-memory hand-me-down.** The other leak: stage N+1 reads stage N's result
from memory, so a crash between them loses the handoff. Here every phase output
is **persisted to the knowledge-graph brain** as an `Artifact` node (authored by
that phase's `AgentRun`, linked `DERIVED_FROM` its upstream), and the runner
reads each phase's input by **loading the prior artifact from the durable store**,
not from memory. `save_hook` persists after every phase, so a crash resumes with
nothing lost. The tests prove the whole chain reconstructs after a reload into a
brand-new process, byte-identical, with a content hash guarding integrity.

## The loop closes

`CHANGE` doesn't dead-end. The runner writes the measurement as a `Metric`, the
verdict as an `Evaluation` (against its rubric), and the proposed change as a
follow-up `Task`, wiring `DEPENDS_ON` edges so the next finding is provably linked
to the evidence that motivated it. "Measure → evaluate → change → and on and on"
is a real cycle recorded in the graph, queryable later.

## How this composes with the swarm

A single `run_pipeline` call is one lossless conveyor. To go wide, run many
conveyors in parallel (one per discovered source / per locale) — each writes to
the same brain, so findings, metrics, and evaluations accumulate in one graph
with full provenance, and no cross-stage summary ever drops a fact. The phase
bodies are where real subagents/tools plug in; the CONTRACT they must honor —
return a payload and declare the fate of every upstream field — is what keeps the
swarm lossless.

## Files

- `brain/pipeline/handoff.py` — the zero-loss handoff mechanism + `trace` +
  `origin_fields_preserved`.
- `brain/pipeline/runner.py` — `run_pipeline`, the `Stage` phases, the loop close.
- `brain/pipeline/default_stages.py` — the seven concrete 1Live roles.
- `brain/pipeline/demo.py` — `python -m brain.pipeline.demo`.
- `tests/test_pipeline_handoff.py` — the proof (silent-drop fails closed, durable
  reload, loop closes, provenance chain connected).
