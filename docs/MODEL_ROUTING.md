# MODEL_ROUTING — cheapest-capable routing policy (Loop Engineering step 17)

Greppable summary: the cost-routing policy the charter's "Cost discipline"
section points at. Maps every loop stage to the cheapest-capable model tier,
names the escalation triggers that justify spending more, and lists the
cost techniques (prompt caching, Batch API, effort levels) with real prices.
Mechanical resolver: `tools/model_router.py <stage>` (env-overridable).
Closes the TODOS "model-cost routing" gap, founder-directed 2026-07-13.
Quality gates NEVER relax across tiers — routing changes who does the work,
never whether it is verified.

## Why routing (the research, one paragraph)

Production teams that route each task to the cheapest model capable of it
report 40–85% cost reductions at ~95% retained quality — most traffic never
needed a frontier model ([routing engineering guide](https://www.digitalapplied.com/blog/llm-model-routing-2026-cost-quality-optimization-engineering-guide),
[RouteLLM/cascade results](https://leanlm.ai/blog/llm-model-routing)). The
proven layering is: cheap **pre-request rules** for obvious cases, then a
**cascade** — try the small model, escalate only when a verification check
fails ([FrugalGPT](https://arxiv.org/abs/2305.05176), [2026 survey](https://arxiv.org/html/2603.04445v2)).
OneLive already owns the hard part of a cascade: deterministic verification
(eval harness, trust gate, evaluator) that decides objectively whether the
cheap tier's output was good enough.

## The ladder (prices per 1M tokens, in/out — [source](https://platform.claude.com/docs/en/pricing.md))

| Tier | Model | Price | Use for |
|---|---|---|---|
| Cheap | `claude-haiku-4-5` | $1 / $5 | Mechanical work: classification, log parsing, formatting, renames, summaries of known-shape text |
| Standard | `claude-sonnet-4-6` | $3 / $15 | Default working tier: code generation, tests, docs, CI assistance (the tier CI's Actions resolve via the router) |
| Critical | `claude-opus-4-8` | $5 / $25 | Architecture, security/trust-critical reasoning, hard debugging, founder-facing incident response |
| Evaluator | `gpt-5.5` (OpenAI) | n/a | Non-Claude requirement dominates cost (§0.2 write/grade separation) — never downgraded for price |

Stage mapping (see `tools/model_router.py`, env-overridable via `ONELIVE_MODEL_<STAGE>`):

| Stage label | Tier | Notes |
|---|---|---|
| `mechanical` | Cheap | |
| `standard` | Standard | |
| `critical` | Critical | Escalation triggers below |
| `extraction` | **BLOCKED (fail-closed)** | The resolver refuses to route this stage at all — overrides included — until the §11.2 hallucination threshold is founder-ratified (docs/RECORD.md R-006). Once ratified (flip `EXTRACTION_THRESHOLD_RATIFIED` in the same commit), it starts at Cheap governed by the golden-set gates: keeps its tier while hallucination/faithfulness gates pass, escalates the moment they fail. |
| `evaluator` | Evaluator | `OPENAI_REVIEW_MODEL` overrides. Hard invariant: the router REJECTS any Claude/Anthropic id in this slot (fail-closed in `resolve_model`) — the grader is never the generator's family, at any price. |

All model ids and prices above are **live, current ids verified 2026-07-13**
(Claude ids against [the pricing page](https://platform.claude.com/docs/en/pricing.md);
`gpt-5.5` is the deployed evaluator already exercised in CI on PRs #11–#12) —
none are placeholders. When a vendor renames or supersedes a model, update
this table and `tools/model_router.py` in the same commit; a stale id fails
loud at the API, never silently reroutes.

## Escalation triggers (spend more, deliberately, logged)

1. **User-facing or production-critical breakage** — speed beats cost; use Critical tier (and fast paths) immediately.
2. **Trust-invariant surface** (auth, RLS, gate/promote, prompts) — Critical tier + mandatory evaluator, always.
3. **Two failures at the cheaper tier** on the same task — escalate one tier rather than retrying a third time (the cascade rule; retries at a failing tier are the real waste).
4. **Founder is waiting live** — interactive latency justifies a stronger/faster tier.
Every escalation gets one line in the session decision record: what escalated, from/to, why.

## Cost techniques (apply before reaching for a bigger model)

- **Prompt caching** — cache reads bill ~0.1× the input price (≈90% off); writes cost 1.25× (5-min TTL) or 2× (1-hour). Keep stable content (system prompts, tool lists, repo context) in an unchanging prefix; two requests already break even at the 5-min TTL. ([caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md))
- **Batch API — 50% off everything** for jobs that can wait up to 24h: embeddings backfills, Descriptor Foundry candidate generation (N=6 per descriptor is batch-shaped), golden-set regressions. ([batch docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing.md))
- **Effort levels** (`low`→`max`) — on models that support it, `low` effort for mechanical work cuts tokens materially; reserve `high`/`xhigh` for trust-critical reasoning.
- **Context hygiene** — read only the file sections needed; don't re-derive what STATE.md/arcs already record (the Brain proposal's semantic recall directly serves this).
- **Ceilings stay on** — per-run source caps (`--max-sources`), Anthropic console spend limit, OpenAI usage limit: routing optimizes inside the ceilings, never replaces them.

## What this does NOT change

- The evaluator stays non-Claude and strong — grading is the safety system.
- `tools/validate`, trust_gate, and eval-harness thresholds are tier-independent.
- Founder-crucial escalations (money/legal/trust/go-live/keys) are unaffected.
