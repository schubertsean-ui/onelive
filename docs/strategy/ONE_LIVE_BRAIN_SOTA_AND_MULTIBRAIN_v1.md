# ONE LIVE — Brain SOTA + Multi-Brain research (v1, 2026-07-25)

Founder directive (2026-07-25): "Research what is available for building the best
brain and whether having more than 1 brain could accelerate improved performance
at greater than normal rate."

**Evidence grade — SEARCH-SNIPPET (honest).** WebSearch works from this
environment; WebFetch is proxy-blocked (403 on arxiv PDFs, mem0.ai, github.io —
verified 2026-07-25). So every external claim below is from a search snippet, not
a paper read in full. Treat system names + numbers as leads to verify, not
settled facts (same posture as R-023/R-024). Recorded so nothing is overclaimed.

---

## Part A — What's available for building the "best" brain (2026 landscape)

**Benchmarks (how "best" is measured):** LongMemEval (500 Q, 6 categories incl.
temporal reasoning + knowledge-update), LoCoMo (~1,540 Q), BEAM (1M/10M-token
scale). Our internal 33-Q benchmark maps to LongMemEval's categories but is NOT
leaderboard-comparable (R-041).

**Leading systems (snippet-level):**
- **Memanto (2026)** — reported SOTA ~**89.8% LongMemEval / 87.1% LoCoMo**, and
  notably **vector-only** — no graph, no LLM-mediated ingestion. The important
  caution for us: a *simpler* architecture is currently topping the recall
  benchmark, so "best brain" ≠ "most elaborate brain."
- **Supermemory** — ~**95% Recall@15** adding only ~720 tokens (retrieval
  efficiency, our EFFICIENCY dimension).
- **Zep / Graphiti** — ~**63.8%** on the temporal sub-task; temporal knowledge
  graph (closest in kind to ours).
- **Cognee** — graph-native (KG as primary store). **Mem0 / Mem-α** —
  multi-component (core/episodic/semantic) trained memory management.
- **MemGuard** — memory *contamination* prevention (directly relevant to our
  gaming/held-out concern).

**The five mechanism families (the taxonomy the field uses):** (1) context-resident
compression, (2) retrieval-augmented stores, (3) reflective self-improvement,
(4) hierarchical virtual context, (5) policy-learned management.

**Consolidation / "sleep-time compute" (a real trend):** SCM (Sleep-Consolidated
Memory), AutoDream (background sub-agent that reviews+consolidates memory between
sessions, REM-analogy), TiMem (temporal-hierarchical consolidation), ZenBrain
(7-layer neuro-inspired). Caveat from the sleep-time literature: offline
consolidation helps most when future queries are *predictable* from existing
context; an "attractive but irrelevant dream" wastes compute.

**Where OneLive's brain actually sits (honest):** we are graph-based like
Zep/Graphiti/Cognee, and we **lead** on axes the recall benchmarks mostly don't
score — mechanical provenance (100% citation), reversible entity resolution,
disputed-shown, the 4 write-invariants, and now bi-temporal validity. On *raw
recall*, a tuned vector system (Memanto) would likely beat a naive graph — so our
edge is **trust/provenance/auditability**, not benchmark recall. Best next
adopts, cheapest-first: (1) a **consolidation/"sleep" pass** (idle-time review +
merge — AutoDream/SCM pattern); (2) **contamination defense** (MemGuard — same
substrate as the held-out judge); (3) a **hybrid** (graph for trust + vector for
fast recall) since vector-only is winning recall; (4) **specialization** of memory
types (episodic/semantic/procedural).

---

## Part B — Would MORE THAN ONE brain accelerate at a greater-than-normal rate?

**Short answer: yes, but conditionally — and it's a live, validated 2026 research
direction, not speculation.** Directly relevant work (snippet-level): **MemEvolve**
(meta-evolution of the memory system itself), **"Governed Collaborative Memory as
Artificial Selection in LLM Multi-Agent Systems"** (multiple memories + a
selection/governance mechanism — essentially the reputation/selection idea from
our prior thread, as a paper), **Self-Consolidation for Self-Evolving Agents**,
**MemMA** (multi-agent memory cycle + in-situ self-evolution), **Self-Evolving
Multi-Agent Systems via Decentralized Memory**, **Tree-based Credit Assignment for
Multi-Agent Memory**, **Joint Optimization of Multi-Agent Memory** (each memory
optimized under a shared global objective).

**Super-linear ("greater than normal rate") happens ONLY when all four hold:**
1. **Specialization** — separate brains for episodic vs semantic vs procedural, or
   per-domain (events vs acquisition-know-how vs quality/reputation). Reduces
   interference → each learns faster in its niche (neuro-inspired: hippocampal vs
   neocortical; ZenBrain's layers).
2. **Diversity / decorrelation** — brains with different structure/seed (ideally
   not all the same base model) → decorrelated errors + cross-checking. This is
   also a *gaming defense*: one brain becomes a held-out judge for another.
3. **Selection + consolidation** — a fitness function selects winners (Artificial
   Selection) and a consolidation/"sleep" pass merges their gains. WITHOUT this,
   N brains = N copies → linear at best, minus coordination + contamination cost.
4. **Credit assignment** — you must know WHICH brain/memory produced a win
   (Tree-based Credit Assignment) to reinforce it; otherwise gains don't compound.

**Risks (why it can go negative):** memory **contamination** (MemGuard) spreading
across brains; **conflict/consistency** (which brain is right?); **correlated
failure** if every brain shares one base model (diversity is fake); coordination +
consolidation **cost**; and **Goodhart** if the shared objective is a gameable
single metric. Plus the Memanto caution: **more structure is not automatically
better** — measure it, don't assume it.

**This unifies the prior threads.** The safe multi-brain engine is exactly the
gaming-resistant substrate we already sketched:
- **held-out / blind eval** = the *fitness function*,
- **reputation economy** = the *selection pressure*,
- **multiple diverse brains** = the *population*,
- **consolidation ("sleep")** = the *merge*,
- **credit assignment** = what makes gains *compound*.
Run in that order, super-linear improvement is plausible and measurable on our
brain-IQ trend. Run the loop before the blind judge exists, and multi-brain just
multiplies Goodhart.

---

## Recommendation for OneLive (staged, cheapest-first)

1. **Now, cheap, no new spend:** build the **held-out/blind eval** (base-owned
   hidden set) — it's the fitness function every later step needs, and it makes
   the *current* single brain gaming-resistant. Prerequisite for everything below.
2. **Next:** a **consolidation pass** (idle-time "sleep": dedupe, resolve, decay
   stale, promote durable recipes) — improves the single brain and is the merge
   step a population will reuse.
3. **Then, deliberately:** a **small specialized population** — start with the
   two proto-brains we already have (the knowledge graph + the acquisition
   toolkit) as distinct specialists, add a quality/reputation brain, and select
   between candidate strategies on the held-out fitness with credit assignment.
   This is where the "greater than normal rate" can appear — measured on brain-IQ,
   not assumed.
4. **Founder-crucial spend decisions (not agent calls):** running the real
   **LongMemEval** externally (budgeted LLM judge, G-BRAIN-1D), and any **graph-DB
   infrastructure** (Kuzu/Neo4j/FalkorDB) for million-node scale + true model
   diversity (a second base model for decorrelation).

**Honest bottom line:** more than one brain *can* beat a single one at a
super-linear rate, but only with diversity + selection + consolidation + credit
assignment — and the single most valuable next build is the blind fitness
function, which pays off whether or not we ever run a population. And keep the
Memanto result in view: elaboration must earn its place on the scoreboard, not by
assumption.

## Sources (search-snippet level; WebFetch was 403)
- mem0.ai — State of AI Agent Memory 2026 (benchmark report)
- Vektor Memory (Medium) — The State of AI Agent Memory in 2026
- 2026 Memory Literature Scan (lin-guanguo.github.io)
- arXiv (abstracts via search): Memanto (2604.22085); MemGuard (2605.28009);
  MemEvolve (2512.18746); "Governed Collaborative Memory as Artificial Selection"
  (2605.04264); Self-Consolidation for Self-Evolving Agents (2602.01966); MemMA
  (2603.18718); Self-Evolving Multi-Agent Systems via Decentralized Memory
  (2605.22721); Tree-based Credit Assignment (2605.04811); Joint Optimization of
  Multi-Agent Memory (2603.12631); SCM Sleep-Consolidated Memory (2604.20943);
  TiMem (2601.02845); ZenBrain (2604.23878); Phasor Agents (2601.04362)
- Letta — Memory Models: Towards Agents That Learn; Zylos Research — Agent Memory
  Architectures / Memory Consolidation (2026)
