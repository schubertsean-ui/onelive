Adopted the "Graph Engineering — The Karpathy Loop / Anthropic Playbook" paper as OneLive's persistent knowledge-graph brain (new `brain/` package): a typed, on-disk world model that survives process death and enforces provenance mechanically. The one-line thesis we bought: **the agent forgets, the graph does not.**

## Why this exists (plain language)

Until now the build agent's only memory was Markdown files in `docs/memory/`.
Those are great for a human to re-read, but a program cannot *ask questions*
of them ("what sourced this claim?", "which run produced this file?", "is
'Mohawk Austin' the same venue as 'Mohawk'?"). The paper's core move is to
store the agent's knowledge as a **graph of typed things and typed
relationships**, on disk, where every important fact can be traced back to
where it came from.

We built a small, self-contained version of exactly that. It is stdlib-only
Python (no new libraries, nothing to install, works in our network-blocked
sandbox), it is memory (it never publishes — that is a trust invariant, and
`tools/trust_gate.py` enforces that `brain/` cannot import the publish path),
and it comes with passing tests and a runnable demo (`python -m brain.demo`)
that proves it does not forget.

## What we adopted, section by section

- **Routing / classify-first (paper §II).** Already built — OneLive routes
  work to the cheapest capable model via `tools/model_router.py` and
  `docs/MODEL_ROUTING.md`, and classifies extraction surface in
  `tools/classify_extraction_surface.py`. Nothing new needed here.

- **The persistent knowledge graph (paper §III, "the graph is honest by
  construction").** This is the new work. `brain/schema.py` defines the node
  types (Entity, Claim, Source, Artifact, AgentRun, Evaluation, Task, plus
  Commit and Metric) and the typed edges (MENTIONS, SUPPORTS, CONTRADICTS,
  DERIVED_FROM, PRODUCED, EVALUATES, REVISES, SUPERSEDES, DEPENDS_ON,
  PARENT_OF, RESOLVED_TO). `brain/graph.py` is the store.

- **The four write invariants, enforced mechanically.** This is the heart of
  the paper and the heart of why we trust the graph. A write that breaks one
  of these *raises loudly* — it cannot silently store a fact with no
  provenance:
  1. Every Claim has a Source **or** is explicitly marked `inference=True`.
  2. Every Artifact names its authoring AgentRun **and** carries a version.
  3. Every Evaluation identifies a rubric (an ungrounded verdict is not
     evidence).
  4. Every superseded object stays addressable — `supersede()` sets a flag
     and adds a REVISES/SUPERSEDES edge; it **never deletes**. There is no
     delete path in the store at all. Old versions stay queryable.
  Each invariant has a test that proves it both raises on violation and
  passes when satisfied (`tests/test_brain_graph.py`).

- **Entity resolution as a reversible, additive, inspectable operation
  (paper §IV.D + §IX.G).** When we decide "Mohawk Austin" is the same venue
  as "Mohawk", we fold one into the other — but the canonical entity
  *retains* both surface forms as aliases, keeps every source document, and
  records the rationale and a confidence for the merge. The folded entity is
  marked superseded (still fully addressable, never deleted) and linked with
  a RESOLVED_TO edge. Crucially, `unresolve()` undoes the merge exactly,
  without rebuilding the graph. **A false merge is a mistake, not a
  catastrophe.** This is the eventual successor to today's
  `worker/resolve_entities.py` fuzzy venue/artist matching — but we did NOT
  wire it into the live pipeline (see "what we did not do").

- **Context construction from the graph (paper §V.B).** `subgraph(node,
  hops=N, edge_types=...)` returns a bounded neighborhood *with its
  provenance edges*. The point is to retrieve the connected state needed for
  one decision, instead of replaying all history into the model's context.

- **The provenance thesis.** "Every important output can be traced to an
  objective, a plan, an artifact, a source, a graph path, an evaluator
  decision, and a bounded execution record." The demo shows this end to
  end: a Source → a sourced Claim about an Entity → an AgentRun that
  PRODUCED an Artifact → an Evaluation against a rubric, saved, reloaded in a
  fresh graph, and printed back with every link intact.

- **The staged capability path (paper §VII: tools → planning →
  multi-agent → graph → swarm).** Where OneLive already is: we have tools, we
  have planning (the session loop + contract-first discipline), and we have a
  multi-agent org (generator + independent evaluator + friction + the six
  thinking hats). This package adds the **graph** stage as a substrate. We
  are deliberately NOT at "swarm."

## What we deliberately did NOT adopt (and why)

- **AgentHub-style commit-DAG replacing pull requests.** The paper sketches
  agents committing directly to a shared DAG. We keep **gated pull requests**
  with the independent non-Claude evaluator and green required checks. That
  review gate is a trust invariant here; trading it for speed is not an agent
  decision.

- **Auto-publish from the graph.** The graph is memory. It must never become
  a path by which the AI publishes to users — that violates the prime
  directive "AI never publishes." `brain/` cannot import `worker.promote`,
  and `tools/trust_gate.py` enforces that mechanically.

- **Wiring the graph into the live pipeline.** This is a proven,
  self-contained foundation, not a rewrite of anything already running.
  `worker/resolve_entities.py`, the promotion path, and the shadow-only
  Subjective Logic substrate (`worker/convergence/`) are all untouched. The
  Claim confidence field is designed to *later* feed convergence — the seam
  is noted in the code, not connected.

## Honest list of what the paper describes that we did not build yet

Recorded so these are staged, not silent:

1. **Recurrence / temporal knowledge** — the graph has no notion of "this
   fact was true at time T, superseded at T+1" beyond the supersede flag; no
   bitemporal validity intervals. (Relates to the existing G-BRAIN-1D
   temporal-recall trigger, R-010.)
2. **Multi-hop query optimization** — `subgraph()` is a plain breadth-first
   walk over an in-memory edge list. Fine for thousands of nodes; it would
   need indices for millions.
3. **Convergence wiring** — Claim confidence is not connected to
   `worker/convergence` (deliberately; that coupling is founder-crucial per
   the convergence spec).
4. **Live-pipeline adoption** — entity resolution here does not yet subsume
   `worker/resolve_entities.py`; nothing writes to this graph from ingestion.
5. **Concurrency / durability under crash** — persistence is a single-writer
   JSONL snapshot; no append-during-crash recovery or multi-process locking.

## The objective triggers for the next stages

- **Adopt graph entity resolution into the pipeline** when a measured
  false-merge or missed-merge from `worker/resolve_entities.py`'s fuzzy
  matching costs real event trust (a logged incident), OR when the Emotion
  Graph build begins (G-BRAIN-1D trigger T1) — whichever first. That work is
  its own contract-first PR through the evaluator.
- **Add temporal validity** when pgvector temporal-recall failures are logged
  (G-BRAIN-1D trigger T2) or relationship queries outgrow flat SQL/JSONL
  (T3). New infrastructure spend at that point is founder-crucial.
- **Wire Claim confidence to convergence** only on an explicit founder ruling
  (convergence coupling is founder-custodied, per the convergence spec).

## Where the code lives

- `brain/schema.py`, `brain/graph.py`, `brain/store.py`, `brain/demo.py`,
  `brain/__init__.py`.
- Proof tests: `tests/test_brain_graph.py` (22 tests, all passing).
- Run the proof yourself: `python -m brain.demo`.

---

**Codified by:** `brain/` package + `tools/brain_iq.py` and `docs/metrics/` Brain IQ ledger; FROZEN off-mission until v1 is live (`docs/UNWIRED_DECISIONS.md`, founder call pending).
