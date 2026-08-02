# 1LIVE — "Brain" Options: Persistent Memory for the Build Agent and the Platform (v1)

**Compiled 2026-07-13 · Status: RATIFIED 2026-07-13 — founder decision (verbatim): "Brain: 1A+1B, platform at Step 7". G-BRAIN CLOSED. Researched per the charter's citation discipline; sources linked per clause.**

## RATIFIED DECISION + the standing 1D trigger (G-BRAIN-1D — never lose this)

- **Build brain = 1A + 1B fused**: sharpened file brain (`docs/memory/` — live as of this ratification) + pgvector semantic recall in the existing Supabase (build queued: see TODOS "Brain 1B build").
- **Platform brain = 2C now, 2A at Sprint Step 7** (embed events/artists/venues once real rows exist; same pgvector migration as 1B).
- **G-BRAIN-1D — graph-infrastructure trigger (founder-directed, standing):** *"if it ever needs graph infrastructure, that's the moment option 1D becomes worth it, one investment serving both brains."* Option 1D (self-hosted Graphiti + a graph database) is NOT built now — recorded as [R-010] in `docs/RECORD.md` per the no-silent-deferrals rule — but it fires for re-evaluation when ANY of these objective conditions is met:
  - **T1 — Emotion Graph implementation begins** (P3 per the Emotion & Vibe spec): the platform moat needs relationship storage; evaluate 1D as its engine so one investment serves both brains.
  - **T2 — build-brain temporal recall fails**: the pgvector index demonstrably cannot answer "what was true, and when" questions (e.g. contradictory decisions across ≥50 session arcs surface as retrieval errors logged in AGENT_FEEDBACK).
  - **T3 — platform relationship queries outgrow SQL**: artist×venue×hour×feel queries require multi-hop traversals that Postgres/pgvector cannot serve within the CWV budget.
  - **On fire:** run a Friction pre-work attack on the 1D adoption plan, then escalate to the founder (new infrastructure = money/new-services = founder-crucial). The standing TODOS item "G-BRAIN-1D trigger watch" keeps this in the every-session work queue.

## Addendum 2026-07-13 — RAG investigation (founder ask: "investigate the use of a RAG System")

**Finding: the ratified Brain 1B IS a RAG system.** RAG ("retrieval-augmented generation") is the umbrella name for exactly what 1B does: store knowledge outside the model, retrieve the relevant pieces by meaning, and hand them to the model as context. The pgvector-in-Supabase recommendation the founder ratified is the standard production RAG pattern on this stack — no change of direction is needed, only two quality upgrades folded into the queued 1B build (same PR, no new vendors, no new spend):

1. **Hybrid retrieval** — combine meaning-based (vector) search with classic keyword search (Postgres full-text, already in our database). Meaning-search finds paraphrases ("the azp thing" → the CSRF decision); keyword-search wins on exact terms (error codes, function names, `[R-###]` tags). Production guidance is unambiguous that the combination beats either alone ([RAG production patterns](https://ailearningguides.com/rag-optimization-production-ai-guide/), [advanced RAG techniques](https://blog.starmorph.com/advanced-rag-techniques-hybrid-search-reranking-query-transformation)).
2. **Reranking** — retrieve ~20 candidates cheaply, then have a small model re-order them for true relevance before using the top ~5. The single biggest precision win in the literature (typ. 15–30% quality gain) for pennies per query.

**GraphRAG (the graph-database flavor of RAG) = our option 1D**, already covered by the standing G-BRAIN-1D trigger above: it earns its extra cost only for cross-document "connect-the-dots" relationship questions ([GraphRAG vs vector RAG](https://buildmvpfast.com/blog/graphrag-vs-vector-rag-complete-guide/), [Neo4j advanced RAG](https://neo4j.com/blog/genai/advanced-rag-techniques/)), which is precisely fire-condition T3. pgvector remains the right engine below ~10M chunks — we are at ~10² documents. Nothing new to decide; the trigger already encodes the graduation point.

---

**Founder ask:** "Add a 'brain' so you [the build agent] never forget and so 1Live platform never forgets. Research the best world-class options."

These are two different brains with two different jobs, so they get separate options:

---

## Brain 1 — the BUILD brain (the agent never forgets)

### What exists today (honest baseline)
The repo already has a disciplined file-based memory: `CLAUDE.md` (standing rules), `STATE.md` (current truth, machine-reconciled), session arcs (how we got here), `TODOS.md`, changelog, `AGENT_FEEDBACK.md`. Its real weakness is **recall, not storage**: nothing retrieves the *relevant* past decision automatically — the agent must know which file to read, and industry analysis agrees flat instruction files "don't retrieve relevant context based on what you're currently working on" ([MindStudio comparison](https://www.mindstudio.ai/blog/claude-code-memory-systems-compared), [Felo guide](https://felo.ai/blog/claude-code-memory/)). Claude Code itself has no native cross-session memory beyond these files ([official docs](https://code.claude.com/docs/en/memory)).

### Option 1A — Sharpen the file brain (no new anything)
Structured `docs/memory/` directory (decisions, gotchas, entity notes) written via the Anthropic memory-tool pattern — file operations the agent performs itself ([Anthropic memory tool docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)); retrieval stays grep/read.
- **Cost:** zero. **Speed:** one session.
- **Tradeoff:** recall stays keyword-level; misses paraphrases ("the azp thing" won't find "CSRF validation"). Files keep growing; pruning is manual (§0.8).

### Option 1B — Semantic memory in the Supabase we ALREADY have (pgvector) — RECOMMENDED (fused with 1A)
Add the `pgvector` extension (one migration; same review/apply process as 0005–0007) + an `agent_memory` table; embed every session arc, decision record, and changelog entry; retrieve by meaning at session start ("what do we know about Clerk?" finds the azp record). This is the standard production pattern on our exact stack ([Supabase pgvector docs](https://supabase.com/docs/guides/database/extensions/pgvector), [pgvector+Supabase agent-memory architecture](https://dev.to/moneylab_ai/building-persistent-memory-for-ai-agents-a-pgvector-supabase-architecture-558n), [HNSW guidance](https://www.kreante.co/post/build-smart-apps-with-supabase-vector-database-semantic-search-guide)). Files remain the source of truth (disk is truth — prime directive 2); the vector index is a *finding aid*, rebuildable from the files at any time.
- **Cost:** no new vendor; embedding API calls are pennies at our volume (uses an existing key). **Speed:** 1–2 sessions incl. tests + evaluator review.
- **Tradeoff:** ~200 lines of ours to maintain; embeddings must re-run when files change (a small hook); meaning-search quality < the dedicated graph products below.

### Option 1C — Hosted memory service (Mem0 / Zep)
Purpose-built memory clouds. Zep's temporal knowledge graph is the benchmark leader (63.8% vs Mem0's 49.0% on LongMemEval, the standard long-memory test) ([2026 comparison](https://particula.tech/blog/agent-memory-frameworks-tested-mem0-zep-letta-cognee-2026), [multi-system review](https://medium.com/@wasowski.jarek/i-compared-5-ai-agent-memory-systems-across-6-dimensions-none-wins-6a658335ed0a)). Pricing: Zep Flex ~$125/mo, Mem0 Pro ~$249/mo ([provider comparison](https://www.developersdigest.tech/blog/best-ai-agent-memory-providers-2026)).
- **Tradeoff:** new paid vendor (founder-crucial: money), our decision history leaves our stack, another key to mint/rotate — for recall quality we don't yet need at ~5 sessions of history.

### Option 1D — Self-hosted graph memory (Graphiti + Neo4j/FalkorDB, or Letta)
The open-source core of 1C ([Graphiti, Apache-2.0](https://github.com/getzep/graphiti)); strongest "what was true, and when" memory. Requires running a graph database ourselves ([self-hosting requirements](https://help.getzep.com/graphiti/getting-started/welcome)).
- **Tradeoff:** a whole new production system to operate (backups, upgrades, monitoring) for a one-founder company pre-launch. Overkill now; the natural revisit point is when the Emotion Graph (Brain 2) needs a graph engine anyway.

**Recommendation: 1A + 1B fused.** Why over 1C/1D: zero new vendors or spend, builds on infrastructure we already run and trust (RLS'd Supabase), keeps the charter's disk-is-truth property, and the vector index is disposable/rebuildable so we can graduate to 1C/1D later without losing anything. What we give up: the last ~15 points of recall quality on temporal questions — acceptable at our history size, revisit at ~50 sessions.

---

## Brain 2 — the PLATFORM brain (1Live never forgets)

### What exists today (mostly already built — by design)
1Live's trust architecture *is* a memory system: append-only `audit_log`, deterministic `replay_log` (every pipeline decision re-runnable), `_provenance` stamped on every AI extraction, disputed-events-never-deleted, source-reliability history. The platform already never forgets *what happened and why*.

### What's missing (the options)
- **2A — Semantic event/artist/venue memory (pgvector, same migration as 1B):** embed artist bios, venue descriptions, event text → powers dedupe ("is this the same show?"), Spark Line sourcing, and future Feel search. Build when real rows exist (after Sprint Step 7 — embedding zero events is pointless).
- **2B — The Emotion Graph** (already the named third moat in [the ratified-pending spec](../strategy/ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md)): city × venue × artist × hour × felt-emotion accreting nightly. This is the platform's long-term brain; phased P3 per the spec. If/when it needs a graph engine, that's the moment 1D's infrastructure becomes justified — one graph investment serving both brains.
- **2C — Do nothing extra now:** legitimate — the audit/replay/provenance layer already satisfies "never forgets" for trust purposes.

**Recommendation: 2C now, 2A at Step 7 (same pgvector migration as 1B, so one review covers both), 2B on its existing P3 schedule.**

---

## Consolidated founder decision (HISTORICAL — answered; see §RATIFIED at top)
*This ask was answered 2026-07-13 with "Brain: 1A+1B, platform at Step 7" — kept verbatim for the record, no reply needed.* Original ask: reply with one line: **"Brain: fused 1A+1B, platform 2A-at-Step-7"** (the recommendation), or name a different combination. If 1C/1D is chosen, that's a money/new-vendor decision and I'll prepare the friction attack first. Nothing is built until you pick (PROPOSAL ≠ license to build).
