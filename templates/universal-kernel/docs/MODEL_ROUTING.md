# MODEL_ROUTING — cheapest-capable routing policy

> **KERNEL DOC — project-agnostic, inherited verbatim.** The METHOD below is
> kernel and must not be sampled down: the cheapest-capable principle, the
> cascade, the escalation triggers, the cost techniques, and the rule that
> QUALITY GATES NEVER RELAX across tiers. The LADDER TABLE is deliberately a
> TEMPLATE the adopting project fills and ratifies — model ids and vendor prices
> go stale, so this file never presents them as current fact. Project specifics
> (which vendors, which ids, which prices, which stages exist) live here once
> ratified, and their surfaces are bound in `OVERLAY.md`. Text in `[square
> brackets]` is a placeholder the project must bind.

Greppable summary: the cost-routing policy the charter's "Cost discipline"
section points at. Maps every loop stage to the cheapest-capable model tier,
names the escalation triggers that justify spending more, and lists the cost
techniques (prompt caching, batch, effort levels). Mechanical resolver:
`tools/model_router.py <stage>` (env-overridable per stage via
`KERNEL_MODEL_<STAGE>`); the values it resolves live in the pure-data module
`tools/routing_data.py`. **This doc is the policy; `routing_data.py` implements
it.** Change the table HERE first, then the data module, in the same commit
(`tools/README.md`, "What a project must supply", item 7). Quality gates NEVER
relax across tiers — routing changes who does the work, never whether it is
verified.

## The method (kernel — not negotiable)

1. **Cheapest-capable first.** Every task and every loop stage uses the
   cheapest tier, technique, and tool that meets the bar. A tier is EARNED by
   passing the same gates as any other tier, and it is LOST the same way.
2. **Cascade, don't guess.** Try the small model; escalate only when a
   *verification check fails* — never on a hunch, never "to be safe". The
   cascade is only sound because the harness owns deterministic verification
   ([eval harness], [project trust gate], `tools/validate`, the Independent
   Evaluator) that decides objectively whether the cheap tier's output was good
   enough.
3. **Escalate deliberately and visibly.** Every escalation gets one line in the
   session decision record: what escalated, from which tier to which, why.
   Silent escalation is the same defect class as a silent deferral.
4. **Gates are tier-independent.** `tools/validate`, [project trust gate], the
   evaluator, and the [eval harness] thresholds are identical at every tier.
   Efficiency comes from routing, caching, and batching — never from skipping
   verification. Using a routing argument to lower a threshold is a
   gate-threshold relaxation: founder-crucial (kernel I7).
5. **Measure, don't guess.** Cost-per-verified-unit and per-run ceilings govern
   the loop. A cheaper tier that fails the gates is not cheaper.

## Why routing (the research, one paragraph)

Production teams that route each task to the cheapest model capable of it
report 40–85% cost reductions at ~95% retained quality — most traffic never
needed a frontier model ([routing engineering guide](https://www.digitalapplied.com/blog/llm-model-routing-2026-cost-quality-optimization-engineering-guide),
[RouteLLM/cascade results](https://leanlm.ai/blog/llm-model-routing)). The
proven layering is: cheap **pre-request rules** for obvious cases, then a
**cascade** — try the small model, escalate only when a verification check
fails ([FrugalGPT](https://arxiv.org/abs/2305.05176),
[2026 survey](https://arxiv.org/html/2603.04445v2)). The hard part of a
cascade is not the routing, it is having a verifier whose verdict you trust;
a project adopting this kernel already owns one, which is what makes the cheap
tier safe to try first.

## The ladder — PROJECT TEMPLATE, fill and ratify before first use

**Nothing in this section is inherited as fact.** Vendors rename models,
supersede them, and change prices; a kernel that shipped live ids would ship
lies within a quarter. The adopting project fills this table from the vendors'
own current pricing pages, records the date it verified them, and ratifies it —
then keeps `tools/routing_data.py` equal to it.

Prices are per 1 million tokens, input / output.

| Tier | Model id | Price (in / out) | Verified on | Use for |
|---|---|---|---|---|
| Cheap | `[model id]` | `[$in / $out]` | `[YYYY-MM-DD]` | Mechanical work: classification, log parsing, formatting, renames, summaries of known-shape text |
| Standard | `[model id]` | `[$in / $out]` | `[YYYY-MM-DD]` | Default working tier: code generation, tests, docs, CI assistance |
| Critical | `[model id]` | `[$in / $out]` | `[YYYY-MM-DD]` | Architecture, security/trust-critical reasoning, hard debugging, founder-facing incident response |
| Evaluator | `[non-generator-family model id]` | `[$in / $out]` | `[YYYY-MM-DD]` | Independent review. The non-generator-family requirement dominates cost (kernel I3, write/grade separation) — never downgraded for price |

> **Ratification line — the project fills this in:** *"Ladder ratified
> `[YYYY-MM-DD]` by `[founder name]`; ids and prices verified against
> `[vendor pricing page URL]` on that date."* An unratified ladder means the
> values in `tools/routing_data.py` are the kernel's shipped placeholders and
> have never been checked against a real price list.

**Illustrative example only — DO NOT COPY.** The ids and prices below are what
the origin project ratified as of **2026-07-13**. They are reproduced solely to
show the shape of a filled row and are near-certainly stale by the time you
read this; verify every value against the vendor's own current pricing page
before entering it above.

| Tier | Example id (as of 2026-07-13) | Example price (in / out) |
|---|---|---|
| Cheap | `claude-haiku-4-5` | $1 / $5 |
| Standard | `claude-sonnet-4-6` | $3 / $15 |
| Critical | `claude-opus-4-8` | $5 / $25 |
| Evaluator | `gpt-5.5` (non-generator family) | n/a — set by the review budget, not the ladder |

**Freshness rule (kernel):** when a vendor renames, supersedes, or reprices a
model, update this table AND `tools/routing_data.py` in the same commit. A
stale id fails loud at the vendor API; it must never silently reroute to a
different tier. Re-verify prices at least whenever the ladder is cited in a
cost decision.

## Stage mapping

The stage labels are the resolver's contract — they are literal keys in
`tools/routing_data.py`'s `STAGE_MODELS`, so renaming one here without renaming
it there is doc drift and a review finding. Each is env-overridable via
`KERNEL_MODEL_<STAGE>` (present-but-empty is a hard failure, never "default").

| Stage label | Tier | Notes |
|---|---|---|
| `mechanical` | Cheap | |
| `standard` | Standard | The default working tier |
| `critical` | Critical | Escalation triggers below |
| `extraction` | **BLOCKED (fail-closed) until the project certifies it** | The kernel ships `EXTRACTION_THRESHOLD_RATIFIED = False`: this is the generative stage whose output feeds [the trusted surface], and a template has never sat an exam, so the resolver refuses to route it at all — overrides included. A project flips the flag to the literal `True` only as the RECORD of a passed attended exam on [golden set] against its ratified [primary quality metric] threshold, bound to the exact head commit, prompt hash, routed model, golden-set hash, and dependency lock. It returns to `False` the moment the routed model fails. Once open, it starts at Cheap governed by those gates: it keeps its tier while they pass and escalates the moment they fail. |
| `evaluator` | Evaluator | `OPENAI_REVIEW_MODEL` is honored as a legacy override. Hard invariant: the router REJECTS any generator-family model id in this slot (fail-closed in `resolve_model`) — the grader is never the generator's family, at any price. **Deliberate exception:** the CI reviewer (`tools/adversarial_review.py`) does NOT consume this router — it runs as a trusted copy from the base ref and must not import pull-request-controlled modules, so it enforces the same invariant independently (duplicated check plus its own fail-closed env handling), and CI passes it no model override at all. Changing the CI reviewer model is therefore a pull request editing its default, reviewed by the OLD model. |

## Subagent (build-agent) routing

The stage table governs the loop's own calls; this section governs **subagents
the orchestrator spawns**. The default failure mode is invisible and expensive:
a spawned agent INHERITS the orchestrator's tier, so a session of routine,
deterministic builds all run at Critical tier — the exact waste the ladder
exists to prevent.

| Subagent task | Tier | Examples |
|---|---|---|
| **Build / implementation (DEFAULT)** | **Standard** | feature code plus its tests, importers, parsers, module builds, harness builds |
| Mechanical / data / docs | **Cheap** | data entry, doc formatting, fixtures, renames, known-shape summaries |
| Trust-core / gate-custody / architecture / adversarial | **Critical** | anything on the path to [the trusted surface], gate and certification changes, blind friction or feasibility review, design decisions, hard-reasoning debugging |

Rule: **spawn build-agents at Standard unless an escalation trigger below
applies** — then Critical, logged. Quality is unaffected because every
subagent's output clears the identical gates (`tools/validate`, [project trust
gate], [test runner]) and, for trust-core work, the non-generator-family
evaluator — so a Standard-tier build that passes is exactly as trustworthy as a
Critical-tier one. This is a routing/cost change, NOT a gate relaxation (gates
are tier-independent), so it sits inside agent authority; the escalation
triggers below are the only reasons to spawn at Critical.

## Escalation triggers (spend more, deliberately, logged)

1. **User-facing or production-critical breakage** — speed beats cost; use the
   Critical tier (and fast paths) immediately.
2. **Trust-invariant surface** (auth, access control, the gate/promote path,
   prompts) — Critical tier plus the mandatory evaluator, always.
3. **Two failures at the cheaper tier on the same task** — escalate one tier
   rather than retrying a third time. This is the cascade rule: retries at a
   tier that is already failing are the real waste.
4. **The founder is waiting live** — interactive latency justifies a
   stronger/faster tier.

Every escalation gets one line in the session decision record: what escalated,
from/to, why. An escalation that is not written down did not happen, and the
Kaizen cost measure cannot see it.

## Cost techniques (apply BEFORE reaching for a bigger model)

- **Prompt caching** — cache reads typically bill a small fraction of the input
  price (order 0.1×), while cache writes cost a premium (commonly ~1.25× for a
  short TTL, ~2× for a long one; check the vendor's current numbers). Keep
  stable content — system prompts, tool lists, repo context — in an unchanging
  prefix; with a short TTL, two requests can already break even.
- **Batch APIs — commonly ~50% off** for jobs that tolerate a delayed
  turnaround (often up to 24h): backfills, N-candidate generation, golden-set
  regressions. Anything batch-shaped that is being run interactively is money
  burned for no gain.
- **Effort / reasoning levels** — on models that expose them, low effort for
  mechanical work cuts tokens materially; reserve high effort for
  trust-critical reasoning.
- **Context hygiene** — read only the file sections needed; don't re-derive
  what `STATE.md`, the session arcs, or `docs/memory/` already record.
- **Ceilings stay on** — per-run caps and vendor-console spend limits are not
  replaced by routing. Routing optimizes INSIDE the ceilings; the ceilings are
  what stop a runaway loop, and they are a Sentinel precondition (they exist
  BEFORE the first scheduled run or first spend, per the charter).

## What this does NOT change

- The evaluator stays non-generator-family and strong — grading is the safety
  system, not a line item.
- `tools/validate`, [project trust gate], and [eval harness] thresholds are
  tier-independent.
- The escalation list in kernel invariant I7 (money/new services, legal
  posture, trust-invariant changes, gate-threshold relaxations, go-live pushes,
  credential minting) is unaffected: a cheaper route is an agent decision, an
  easier gate never is.
