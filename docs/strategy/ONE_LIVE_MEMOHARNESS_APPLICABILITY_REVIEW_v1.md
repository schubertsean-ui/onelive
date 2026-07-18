# MemoHarness applicability review — arXiv 2607.14159 vs the Loop-Harness-Brain model

Greppable summary: deep review of "MemoHarness: Agent Harnesses That Learn
from Experience" (Huang et al., Notre Dame/LMU Munich/USC, arXiv:2607.14159v1,
14 Jul 2026; code: github.com/HowieHwong/MemoHarness), founder-requested
2026-07-17. Verdict: strong independent validation of the Loop-Harness-Brain
architecture (their dual-layer experience bank ≈ arcs/ledger + docs/memory;
their harness bundle ≈ CLAUDE.md + OPERATING_RULES + memory; their
correctness-first/cost-tiebreaker rule ≈ the charter's Cost discipline).
Their novel piece — test-time per-case adaptation via retrieved experience —
is the mechanism Brain 1B should implement, and it motivates per-source
extraction adaptation post-Step-7. Their training-time automated harness
search is REJECTED for OneLive: it is exactly the outer-loop-over-harness
the gate-custody decision forbids (docs/memory/decisions/2026-07-14_gate-custody.md;
TODOS "Weco-pattern INNER-loop" item, 2026-07-16), because their search space
includes the validators (D6) and tool exposure (D2) with no independent
review of edits. Status: REVIEW/ANALYSIS — no proposal requiring ratification;
the two adoptions below are P3-cheap and ride existing queue items.

## 1. What the paper is

MemoHarness treats the **agent harness** — "the external control layer that
turns a base LLM into an executable agent" — as the object of optimization,
with three components:

1. **Six-dimensional harness space**, decomposed along the temporal flow of
   inference: D1 context assembly · D2 tool/retrieval use · D3 generation
   (decoding) control · D4 orchestration topology · D5 memory management ·
   D6 output processing. Search becomes structured editing over separable
   control surfaces instead of mutation of one opaque prompt.
2. **Dual-layer experience bank**: per-case execution entries (trajectory,
   reward, cost, and a *diagnosis*: success bit, primary failure dimension
   D1–D6, secondary dimensions, natural-language analysis) plus periodically
   *distilled global patterns* ("what works, what fails, how dimensions
   interact"), distilled every κ rounds or after repeated failures, with a
   per-round cap so controller context stays bounded. The controller never
   reads the whole bank — it retrieves a bounded slice.
3. **Test-time case adaptation, no feedback**: for each unlabeled case,
   retrieve the top-K most similar past *successes* AND *failures* plus
   relevant patterns, and adapt the search-derived global harness to a
   case-specific harness. No labels, no gradient, no extra search at test
   time.

Selection during search is **correctness-first lexicographic**: mean task
reward ranks candidates; lower token cost only breaks ties. Search starts
from a deliberately minimal harness so every adopted component is justified
by execution evidence. The harness is materialized as a "**harness bundle**":
a structured policy file (the D1–D6 state) plus textual scaffolding — the
agent's operating rules, a persistent playbook, and the distilled memory in
scope. Their Appendix G mines the bank for operation-level lift (which newly
added atomic shell operations correlate with reward gains — `cat`, `sed`,
`which`, `test` strongly positive; `curl`, `echo`, `grep` weak/negative).

### Evidence, with its stated limits

- Terminal-Bench (GPT-5.3-Codex base): 0.806 vs 0.722 for Codex, the
  strongest of four harness baselines (Claude Code among them). Gains
  largest on long-horizon agentic work (FinanceAgent 0.600→0.767), smallest
  on saturated single-shot code generation (LiveCodeBench 0.900→0.967).
- Transfer is **selective, not uniform**: the shell-search harness lifts
  SWE-Bench Pro +0.059 and MMMLU +0.030; saturated suites don't move.
  Cross-model transfer without retraining: +0.098 mean across six model
  families.
- Cost: MemoHarness uses ~1.7× Codex's input tokens, but 94% (13.32M/14.18M)
  are cached → $6.89 vs $10.28 per split. **The cost story depends entirely
  on cache reuse** (authors say so).
- Author-stated limitations: 18-task held-out split, point estimates, no
  confidence intervals, components not fully ablated, baselines not pure
  scaffold-only transplants, controller instantiated with heuristics.

**Reading rule for OneLive:** the *architecture* is validated direction; the
*effect sizes* are provisional. Nothing here justifies rebuilding anything on
the strength of these numbers alone.

## 2. Mapping to what OneLive already built

| MemoHarness | OneLive counterpart | Assessment |
|---|---|---|
| Per-case entries with dimension-level diagnosis ("scores alone are weak supervision") | Session arcs + Kaizen ledger M2 (defect, gate, class) + the in-flight repeat-class rule ("classify before fixing; fix the CLASS") | Convergent — same argument, independently derived. |
| Distilled global patterns, κ-scheduled, capped, dedup'd | `docs/memory/` (Brain 1A): decisions + gotchas with update/delete conventions | Convergent, including the bounded-retrieval concern (their retrieved slice ≈ our "skim, don't reload"). |
| Harness bundle: policy file + operating rules + playbook + distilled memory | CLAUDE.md + OPERATING_RULES.md + docs/memory | Nearly the same artifact. Published validation that a disk-resident natural-language harness is a first-class object. |
| Correctness-first, cost-as-tiebreaker selection | Charter Cost discipline rule 3: gates never relax; efficiency via routing/caching/batching only | Same ordering principle, formalized. |
| 94%-cached retrieved context making a bigger harness cheaper | MODEL_ROUTING prompt-caching technique | Quantitative support for our policy — and a hard design constraint for Brain 1B (below). |
| Operation-level lift mining from stored traces | The ledger's purpose ("which gates earn their keep") + disk-is-truth | Same argument: you can only mine what you recorded. |
| Test-time per-case adaptation via retrieved experience | **No counterpart yet** — closest is model routing + per-risk review personas | Their genuinely new piece. See §3. |
| LLM controller editing its own harness incl. validators, no independent review | **Forbidden**: gate custody (2026-07-14) + "outer-loop-over-harness FORBIDDEN" (TODOS, 2026-07-16) | See §4. |

The paper's premise sentence — harness design "can swing end-to-end task
success by tens of percentage points with the same base model" — is the
premise the Loop-Harness-Brain investment rests on, now with published (if
early) numbers behind it.

## 3. What to adopt (both cheap, both riding existing queue items)

1. **D1–D6 as a tagging vocabulary.** Tag Kaizen M2 defect classes, memory
   gotchas, and AGENT_FEEDBACK entries with the primary harness dimension
   (D1 context / D2 tool / D3 generation / D4 orchestration / D5 memory /
   D6 output). Free; gives the ledger a second trend axis ("which dimension
   do defects cluster in?") and gives Brain 1B a typed retrieval key beyond
   text similarity. Alternative considered: inventing our own taxonomy —
   rejected; theirs is adequate, published, and maps cleanly onto our stack.
2. **Two constraints folded into the Brain 1B spec** (TODOS item amended in
   this commit):
   - Recall returns **success neighbors AND failure neighbors** — the
     memory README already mandates recording confirmed approaches, not just
     gotchas; retrieval must surface both (their TopK over E⁺ and E⁻).
   - Memory slices are assembled as **stable, append-mostly prefix blocks**
     so they are cacheable — their own cost result collapses without cache
     reuse, and so would ours (MODEL_ROUTING: cache reads ≈ 0.1× input price).

Deferred-not-adopted (already queued, evidence noted): **per-source
extraction adaptation** — our pipeline's heterogeneous "cases" are sources;
their result predicts adaptation pays most exactly there (long-horizon,
failure-diverse) and least on saturated tasks. Already on the queue as the
"per-source extraction templates" po-harvest (P3, triage at Step-7 design)
and as a KAIZEN M7 improvement lever; this paper upgrades its evidence, not
its priority. Boundary when built: adaptation specializes the extraction
config/prompt per source; every adapted variant sits the SAME golden-set
exam at the SAME threshold. Adaptation touches the worker, never the exam.

## 4. What to reject, and why (the safety delta)

**Do not import the training-time automated harness search.** MemoHarness's
controller — an LLM — proposes edits across all six dimensions, including
**D6 output validation** and **D2 tool exposure**, guarded only by the task
reward. Correctness-first ranking prevents cheap-but-wrong configurations;
it does NOT prevent reward hacking of the metric itself — a search free to
edit validators can weaken a validator to raise measured reward. The paper
has no adversarial review of harness edits and no exam-custody concept.

This is precisely the failure mode the gate-custody decision anticipated
(docs/memory/decisions/2026-07-14_gate-custody.md, from the Weco RSI review:
"the classic failure of self-improvement loops is the agent making its own
exam easier instead of getting better"), and the 2026-07-16 Weco AIDE²
re-evaluation already drew the line MemoHarness now illustrates from the
other side:

- **INNER-loop search** (candidates judged against a custodied, held-out,
  never-touched exam; shipping only through the evaluator-gated PR path) —
  allowed, queued P3.
- **OUTER-loop search over the harness/exam** (the MemoHarness design) —
  FORBIDDEN. If any harness-search automation is ever proposed: every
  automated harness edit is a gate-custody change (non-Claude evaluator
  mandatory), and validators/thresholds are excluded from the searchable
  space entirely. Search optimizes inside the gates, never on them.

Also not applicable: their minimal-harness initialization ("every component
justified by evidence"). Our harness encodes trust invariants that are
physics, not empirically discoverable preferences — RLS fail-closed is not
an A/B arm. The salvageable kernel (periodically audit which harness
components earn their keep) is already Kaizen M2's job.

Secondary observation for the record: their own Appendix G lift table is a
small live demo of Goodhart pressure — operations correlated with reward
get biased into future proposals. Harmless for shell verbs; the same
mechanism pointed at our gates is the threat model above.

## 5. Sources

- Paper: arXiv:2607.14159v1 [cs.AI], 14 Jul 2026 — https://arxiv.org/abs/2607.14159
  (reviewed from founder-supplied PDF 2026-07-17; arxiv.org is blocked by
  this sandbox's network policy and the ID was not yet search-indexed).
  Reviewed-copy provenance: 20 pp, sha256
  `4a4db733f007fea3b035d00226b551587819177458086bf54f665f18faa507cc` —
  future auditors can distinguish "source temporarily unreachable" from
  "unverifiable summary" by hashing their copy against this.
- Code (per paper): https://github.com/HowieHwong/MemoHarness
- Closest prior work the paper names: Meta-Harness (Lee et al., 2026,
  arXiv:2603.28052 — training-time harness search, no test-time adaptation);
  Natural-Language Agent Harnesses (Pan et al., 2026, arXiv:2603.25723).
- OneLive artifacts cited: docs/memory/decisions/2026-07-14_gate-custody.md ·
  docs/KAIZEN.md · docs/MODEL_ROUTING.md · docs/memory/README.md (Brain 1A) ·
  TODOS.md (Brain 1B item; Weco-pattern inner-loop item) ·
  docs/skills/night_shift.md.
