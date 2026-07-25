# ONE LIVE — Brain Benchmark v1 (measured, not asserted)

**What this is (plain language):** a labeled test that MEASURES how good the
OneLive "brain" (`brain/` — the persistent knowledge graph) is at the things a
memory system has to do, and reports real numbers. Before this, "world-class
brain" was a claim. Now it is a measurement anyone can reproduce in under a
second, for free, with no AI and no internet.

- Run it: `python tools/brain_eval.py`
- The harness: `brain/eval/` (`benchmark.py` = the corpus + questions,
  `harness.py` = the runner + scorer).
- The gate: wired into `tools/validate` as `brain_eval` (a one-way ratchet).
- The tests that prove it can fail: `tests/test_brain_eval.py`.

## Why a benchmark, and why these six categories

A memory that is never measured drifts. The six categories below are the
standard competencies the agent-memory literature tests. We cover each with
≥4 labeled questions (26 total across 3 scenarios):

| Category | What it proves | How the brain answers it |
|---|---|---|
| **single_fact_recall** | retrieve a stored fact + its source | 1-hop subgraph over MENTIONS edges → the attribute claim + its Source |
| **multi_hop** | answer needs ≥2 edges traversed | walk a chain of relation claims (e.g. band → venue → district → city) |
| **knowledge_update** | a fact changed over time; the CURRENT answer must win | supersede-aware retrieval (only live claims) — plus point-in-time probes (see the gap below) |
| **contradiction** | two sources disagree → surface BOTH, flag disputed, never silently pick one | collect live claims for the predicate; ≥2 values or a CONTRADICTS edge ⇒ disputed |
| **entity_resolution** | a question using an ALIAS reaches the canonical entity's facts | route the surface form through the RESOLVED_TO / canonical link, then recall |
| **abstention** | a question the corpus does NOT answer ⇒ say "unknown", never fabricate | the read helpers return a value only when a matching claim exists; else abstain |

**No LLM judge.** The scorer is deterministic: exact / structured match against
a gold label. Facts are encoded in claim text with a fixed machine convention
(`predicate=value` for attributes, `rel:predicate@subject` for relations) so the
answer can be read back structurally — but the *answering* is real graph
traversal, so a brain that loses an edge, a supersede flag, or a resolution link
scores strictly worse. That property is what lets the gate fail (proven below).

## The current measured scores (2026-07-25, this brain, pasted verbatim)

```
==============================================================================
 OneLive · brain memory eval (brain/eval/) · deterministic scorer
 no LLM · no network · no spend — these numbers are a measured fact
==============================================================================
  STATUS  CATEGORY               SCORE     ACC    BASE
  ------- -------------------- ------- ------- -------
  PASS    single_fact_recall       4/4  1.0000  1.0000
  PASS    multi_hop                4/4  1.0000  1.0000
  PASS    knowledge_update         3/5  0.6000  0.6000
  PASS    contradiction            4/4  1.0000  1.0000
  PASS    entity_resolution        4/4  1.0000  1.0000
  PASS    abstention               5/5  1.0000  1.0000
------------------------------------------------------------------------------
  overall accuracy         : 0.9231 (24/26)
  provenance citation rate : 1.0000
  abstention correctness   : 0.9231
------------------------------------------------------------------------------
brain_eval: PASS — every category met or beat its recorded baseline.
```

Read this honestly: **five of six categories are perfect; knowledge_update is
0.60, and that number is real, not inflated.** Three of its five questions
("what is the current headliner/cover/door-time?") pass because the supersede
flag lets the brain return the live fact over the old one. The other two ("as of
the early listing on 2026-07-01, who was the headliner?") MISS — and they are in
the benchmark on purpose (see the gap section). The overall 0.9231 and the 0.60
temporal line are the founder-facing truth.

Two extra metrics beyond accuracy:
- **provenance_citation_rate = 1.0** — every question the brain answered with a
  concrete value returned the supporting Source. Provenance is not optional here.
- **abstention_correctness = 0.9231** — of all 26 questions, the brain made the
  right *answer-or-abstain* decision on 24. The two it got wrong are the two
  point-in-time questions, where it abstains but ideally should recall.

## The one-way-ratchet gate

`tools/brain_eval.py` reads `brain/eval/baselines.json` (the numbers above) and
exits non-zero if **any category drops below its recorded baseline**. This is the
same mechanism as the extraction `surface_regression_exam` gate: the baseline is
a floor that only ever moves UP. When the brain gets better (e.g. bi-temporal
recall lands and knowledge_update rises), you re-run the eval and RAISE that
baseline in the same PR — you can never quietly lower it. Because the gate lives
in `tools/validate` and touches the verification tooling, it is **gate-custody**:
evaluator-reviewed on the PR that adds it (charter Agent-org rule).

**A gate that cannot fail is worthless, so we proved this one can**
(`tests/test_brain_eval.py`): (1) reversing an entity resolution drops
entity_resolution to 0.25; (2) an answerer that drops one hop drops multi_hop to
0.0; (3) an answerer that fabricates on an unanswerable question drops abstention
below baseline and tanks abstention_correctness. Each turns the gate RED.

## Where the brain leads, and where it trails — against SOTA

**Where OneLive's brain genuinely leads** (measured 1.0 here, and structural):
- **Provenance is mechanical, not best-effort.** Every recalled fact carries its
  Source (citation rate 1.0). The graph's four write invariants
  (`brain/graph.py`) make an unsourced claim *unstorable* — most memory systems
  treat provenance as metadata you hope is present.
- **Contradiction is surfaced, never silently resolved.** disputed-shown is a
  trust invariant; the brain returns BOTH sides. Many RAG/memory stacks pick one.
- **Entity resolution is reversible.** A wrong merge is undone with `unresolve()`
  and loses no data — a false merge is a mistake, not a catastrophe.

**Where it trails — honestly (docs/RECORD.md R-010 / R-031):**
- **Bi-temporal / point-in-time recall.** The substrate records THAT a fact was
  superseded, not the validity interval it held. So "as of date T" questions
  cannot be served — the measured 0.60 on knowledge_update is exactly that gap.
  This is the same competency the public **LongMemEval** benchmark stresses,
  where the temporal-memory SOTA (**Zep / Graphiti**) sits around **63.8%**. We
  deliberately did not buy that capability yet (option 1D: Graphiti + a graph DB
  — R-010). The plan to close it is the standing **G-BRAIN-1D** trigger: add
  bi-temporal validity intervals when pgvector temporal-recall failures are
  logged (T2) or relationship queries outgrow flat storage (T3); new
  infrastructure spend at that point is founder-crucial. When it lands, the
  knowledge_update baseline rises from 0.60 toward 1.0 in the same PR.
- **Scale of traversal.** `subgraph()` is a breadth-first walk over an in-memory
  edge list — correct, but unindexed (R-031 part 2). Fine for thousands of
  nodes; millions would need indices.

## The honest caveat: this is OUR benchmark, not the public leaderboard

This is a **deterministic, self-authored** benchmark of OneLive-shaped memory —
26 labeled questions we wrote, scored by exact match. It is the right tool for a
free, reproducible **regression gate** that runs on every `validate`. It is **not**
the public **LongMemEval** leaderboard: that uses a large public dataset of long
multi-session chat histories and an **LLM judge**, and running it costs real model
spend and needs the dataset downloaded. The ~63.8% Zep/Graphiti figure above is
LongMemEval's, cited for positioning — our 0.60 temporal line is measured on our
own corpus and is **not** directly comparable as a leaderboard number; it is an
internal indicator of the same underlying gap.

**Path to run the real thing when credentialed:** obtain the LongMemEval dataset,
add an adapter that ingests each session's turns into a fresh brain, answer its
questions through the same `brain/eval` read surface, and score with a budgeted
LLM judge (routed via `tools/model_router.py`, spend logged). That is a
founder-crucial spend decision (new dataset + model cost), so it is staged behind
the G-BRAIN-1D trigger alongside the bi-temporal build it would validate — not
done here, and recorded as R-041 so it is not silently deferred.
