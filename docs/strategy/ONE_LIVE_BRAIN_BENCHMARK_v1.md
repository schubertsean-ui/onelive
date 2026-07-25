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
≥4 labeled questions (33 total across 3 scenarios):

| Category | What it proves | How the brain answers it |
|---|---|---|
| **single_fact_recall** | retrieve a stored fact + its source | 1-hop subgraph over MENTIONS edges → the attribute claim + its Source |
| **multi_hop** | answer needs ≥2 edges traversed | walk a chain of relation claims (e.g. band → venue → district → city) |
| **knowledge_update** | a fact changed over time; the CURRENT answer must win AND "what was true as of date X" | current value = the still-open validity interval; point-in-time = `claims_valid_at` over VALID intervals (bi-temporal, see below) |
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
  PASS    knowledge_update       12/12  1.0000  1.0000
  PASS    contradiction            4/4  1.0000  1.0000
  PASS    entity_resolution        4/4  1.0000  1.0000
  PASS    abstention               5/5  1.0000  1.0000
------------------------------------------------------------------------------
  overall accuracy         : 1.0000 (33/33)
  provenance citation rate : 1.0000
  abstention correctness   : 1.0000
------------------------------------------------------------------------------
brain_eval: PASS — every category met or beat its recorded baseline.
```

**What moved (bi-temporal upgrade, 2026-07-25):** knowledge_update rose from
**0.60 → 1.00** and overall from **0.9231 → 1.00**. Previously three of five
knowledge_update questions passed (current headliner/cover/door-time) and the two
point-in-time "as of date X" questions MISSED, because the substrate had no
validity intervals — it recorded THAT a fact changed (the supersede flag), not
WHEN it was true. Claims now carry a **VALID-time interval**
(`valid_from`/`valid_to`), and `Graph.claims_valid_at` / `Graph.as_of_subgraph`
return the version whose interval contained the queried instant. The category was
also expanded from 5 to 12 questions — three current-value, eight point-in-time
across a 3-era capacity fact (500 → 800 → 1000) plus the day-of lineup change, and
one "before any record" case that must correctly abstain. All 12 pass. This closes
the R-010/R-031/G-BRAIN-1D temporal gap **on our own benchmark** (not the public
LongMemEval leaderboard — see the honest caveat below).

Two extra metrics beyond accuracy:
- **provenance_citation_rate = 1.0** — every question the brain answered with a
  concrete value returned the supporting Source. Provenance is not optional here.
- **abstention_correctness = 1.0** — of all 33 questions, the brain made the right
  *answer-or-abstain* decision on every one (the two point-in-time questions that
  used to wrongly abstain now recall correctly; the "before any record" question
  correctly abstains).

## The one-way-ratchet gate

`tools/brain_eval.py` reads `brain/eval/baselines.json` (the numbers above) and
exits non-zero if **any category drops below its recorded baseline**. This is the
same mechanism as the extraction `surface_regression_exam` gate: the baseline is
a floor that only ever moves UP. The bi-temporal upgrade is the ratchet firing in
the intended direction: bi-temporal recall landed, knowledge_update rose 0.60 →
1.00, and the baseline was RAISED to 1.00 in the same change — it can never be
quietly lowered. Because the gate lives in `tools/validate` and touches the
verification tooling, it is **gate-custody**: evaluator-reviewed on the PR that
changes it (charter Agent-org rule).

**A gate that cannot fail is worthless, so we proved this one can**
(`tests/test_brain_eval.py`): (1) reversing an entity resolution drops
entity_resolution below baseline; (2) an answerer that drops one hop drops
multi_hop to 0.0; (3) an answerer that fabricates on an unanswerable question
drops abstention below baseline and tanks abstention_correctness; (4) a
TIME-BLIND answerer that ignores the validity interval (answers every "as of
date X" with today's value) drops knowledge_update below baseline. Each turns the
gate RED — including, now, the bi-temporal competency.

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

**Bi-temporal / point-in-time recall — now LED, not trailed (2026-07-25):**
- The substrate previously recorded THAT a fact was superseded, not the validity
  interval it held, so "as of date T" questions could not be served — the old
  0.60 on knowledge_update was exactly that gap (R-010 / R-031). Claims now carry
  a **VALID-time interval** (`valid_from`/`valid_to`, half-open
  `[valid_from, valid_to)`), independent of transaction time (the supersede
  bookkeeping). `Graph.claims_valid_at(entity, instant)` returns the
  currently-believed version whose interval contained `instant`; a timeless claim
  is valid always; `Graph.as_of_subgraph` returns the whole neighborhood as it
  was valid then, provenance preserved. knowledge_update measures **1.00 (12/12)**
  — the same competency the public **LongMemEval** benchmark stresses (temporal
  SOTA **Zep / Graphiti** ≈ **63.8%** there). **Read that comparison carefully:**
  our 1.00 is on our own 12-question corpus scored by exact match; it is NOT a
  LongMemEval leaderboard number and is not directly comparable (see the caveat
  below). What is true is that the *capability* — bi-temporal validity intervals,
  the thing option 1D (Graphiti + a graph DB, R-010) was going to buy — is now
  built in pure stdlib, so the internal indicator of that gap has closed.
- **Scale of traversal.** `subgraph()` / `claims_valid_at()` are breadth-first
  walks over an in-memory edge list — correct, but unindexed (R-031 part 2). Fine
  for thousands of nodes; millions would need indices. This is the remaining
  structural item behind the G-BRAIN-1D trigger; running the REAL LongMemEval
  (public dataset + budgeted LLM judge) is still a founder-crucial spend decision.

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
