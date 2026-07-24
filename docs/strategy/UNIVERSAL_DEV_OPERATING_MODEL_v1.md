# Universal Development & Operating Model v1 — kernel + overlay

**Status:** PROPOSAL (founder ratification required; PROPOSAL ≠ license to build)
**Date:** 2026-07-24 · **Session Contract:** #21 (STATE.md) · **Author:** Generator (Claude Code session)
**Prompted by:** founder request to assess Boris Cherny's "Steps of AI Adoption"
(July 2026) against the portfolio — OneLive, multibagger, the press-release
venture (Promise Ledger / PR-aggregator) — and to define a v1 single
**universal** development/operating-model foundation that any project can
inherit and then specialize with its own requirements, peculiarities, and
tribal knowledge.

**Source provenance (honest, precisely scoped):** NO full article text was
readable from this sandbox — the primary article
(<https://www.explainx.ai/blog/boris-cherny-steps-ai-adoption-claude-code-july-2026>)
and every mirror attempted return HTTP 403 through the egress proxy. Part 1 is
therefore reconstructed ONLY from search-engine result excerpts quoting the
coverage below; the excerpts from independent write-ups agreed with each other
on every detail used, which is the sole basis of the cross-check.

- *Primary source, NOT read (403):*
  [explainx.ai](https://explainx.ai/blog/boris-cherny-steps-ai-adoption-claude-code-july-2026) ·
  [Cherny's own LinkedIn post](https://www.linkedin.com/posts/bcherny_steps-of-ai-adoption-activity-7483695059843043328-LBg_)
- *Secondary coverage, read only as search excerpts (direct fetches also 403):*
  [Shelly Palmer's roadmap piece](https://shellypalmer.com/2026/07/boris-chernys-steps-of-ai-adoption-a-roadmap/) ·
  [a widely-shared summary thread](https://www.threads.com/@carnage4life/post/Da8F151FCdR/boris-chernys-stages-of-ai-adoption-for-software-teams-gated-restricted-access) ·
  [bosio.digital's roadmap article](https://bosio.digital/articles/ai-adoption-roadmap) ·
  [SmartScope's organizational-adoption analysis](https://smartscope.blog/en/blog/ai-adoption-stages-one-person-10x-organization/)

The excerpts themselves are preserved verbatim in Appendix A so the
reconstruction can be audited against exactly what was seen, not just a claim
that sources agreed. Anyone with normal browser access should spot-check the
primary source before ratifying anything that leans on a detail below. The
kernel in Part 3 does NOT depend on the article being reproduced perfectly —
it is extracted from our own repo, which we can read directly.

---

## Part 1 — The framework, compactly

Boris Cherny (creator/head of Claude Code at Anthropic) published "Steps of AI
Adoption" on 2026-07-16: five maturity levels for teams building with AI
agents. Each step names a human role, an approximate concurrent-agent count,
the binding bottleneck, and the guardrails that unlock the NEXT step.

| Step | Name | ~Agents/dev | Human role | Bottleneck | What unlocks the next step |
|---|---|---|---|---|---|
| 0 | Gated | 0 | — | Legacy approvals; no real access to capable AI | Access + policy change |
| 1 | Assisted | 1 | Pair partner (high supervision) | Your attention — you watch the agent work, synchronously | Self-verification loops (tests, auto-review) so you don't read everything |
| 2 | Parallel | ~10 | Orchestrator (AI codes, humans verify) | Reviewing output | Automated code/security review on by default, worktree isolation, multi-agent management surfaces |
| 3 | Supervised autonomy | ~100 | Manager of managers (AI verifies, humans handle exceptions) | Trust in the verification loop + the team's decision throughput | Loops/batch/dynamic workflows, routines, cost monitoring — and verified trust in the gates |
| 4 | AI-native | 1,000+ | Steering by intent (AI identifies the work) | Identifying and automating work at scale | — (frontier; Cherny claims Anthropic is at 3 pushing 4) |

Two theses carry the whole model:

1. **What separates the steps is trust, not the model.** Progression is earned
   by verification infrastructure, not by buying more tokens or a bigger model.
2. **The central trap:** scaling the agent count before the verification loop
   has earned that trust. More agents against weak gates = faster production of
   unverified work.

## Part 2 — Applicability assessment, per effort

### 2.1 OneLive (this repo)

**Verdict: the framework is strongly applicable — as confirmation, not as new
direction.** OneLive's charter independently converged on Cherny's two theses
before this article existed:

- "Trust, not the model, separates the steps" ≈ prime directive 1 ("trust
  invariants are physics, not policy") + cost-discipline rule 3 ("quality gates
  never relax; efficiency comes from routing, never from skipping
  verification").
- The "central trap" (agents scaled ahead of verification) is exactly what the
  Step-6 certification bootstrap refused to fall into: extraction stayed OFF
  (fail-closed flag) until a golden exam on the real provider path passed at
  the founder-ratified 1% bar, with the exam harness itself certified via an
  attended run. We built the verification loop first, then let the agent loose.

**Where OneLive sits:** structurally at **Step 3 (supervised autonomy)** for
repo operations — the agent writes, a non-Claude evaluator reviews every PR
mechanically, trust-gate/validate verify, and (founder-ratified 2026-07-18)
the agent merges its own PR on evaluator-APPROVE + all-green, notifying the
founder. Humans supervise exceptions only (the enumerated founder-crucial
list). Concurrency is the honest gap between us and the "~100 agents" label:
we run one deep session at a time by choice, not by missing guardrails — the
gates are already agent-count-independent.

**Where OneLive deliberately refuses the ladder:** the PRODUCT data path.
"AI never publishes" means the promote step is founder/human-custodied
regardless of adoption step. Cherny's ladder describes engineering throughput;
our product's trust surface holds a harder invariant on purpose. The universal
model must encode this distinction (kernel invariant I1 below) so no future
project confuses "we're at Step 3 in the repo" with "AI may publish to users."

### 2.2 Press-release venture (Promise Ledger / PR-aggregator)

**Verdict: directly applicable, and the kernel extraction below IS its
migration plan.** Promise Ledger lives inside this repo today *specifically*
to inherit the gates (evaluator, trust-gate, tests, Record discipline — its
README says so). Its sprint step 12 (extraction to its own repository, a
founder call) currently has no defined answer to "which parts of the harness
move with it?" Part 3's kernel/overlay split is that answer: the kernel moves
verbatim; the overlay (claim schema, 4-state fulfillment verdicts, EDGAR
fair-access contract, R-016/R-017 gates, never-verbatim storage rule) is
already cleanly separable because it was written as project docs, not charter
edits. The venture is at **Step 1–2** on its own work (assisted extraction
prototyping, golden-set harness built before the extraction model exists —
verification-first, i.e. already climbing the ladder in the right order).

### 2.3 multibagger (founder's separate repo — investor/stock engine)

**Verdict: applicable as the first true adoption target.** The repo is not
attached to this session, so its current state is unverified; from prior
session context (Contract #15) it is a standalone codebase worked in ordinary
assisted sessions — i.e. **Step 1**, with none of the harness: no session
reconcile, no contract-first, no independent evaluator, no deferral scan, no
Kaizen ledger. It is the cleanest test of the universal model's core claim:
that the kernel is genuinely project-agnostic and a project can adopt it
without inheriting OneLive's domain baggage. Its overlay would carry: market
data provenance/trust rules (the analog of "AI never publishes" is "AI never
places a trade / never asserts an unverified figure to the investor surface"),
its own golden sets (e.g. retrodiction), and its own founder-crucial list
(money movements, brokerage credentials, published investment claims).

### 2.4 What the article adds that we did NOT already have

Honesty requires naming what's actually new for us, not just claiming
convergence:

1. **A shared external vocabulary.** "Step 2 → Step 3" is a crisper way to
   discuss "should the agent merge on green?" with the founder than our
   bespoke prose. The kernel adopts the step numbers as a *descriptive* axis.
2. **The agent-count dimension.** Our harness is deep but serial. Cherny's
   ladder makes explicit that the next throughput unlock (many bounded
   parallel sessions/subagents under the same gates) is an orchestration
   problem, not a gating problem. That is a real, currently-unexploited
   capability — and safe to exploit precisely because the gates are already
   count-independent.
3. **"Decision throughput" as a named bottleneck.** At Step 3 the limiting
   reagent becomes how fast the human answers founder-crucial questions. Our
   consolidated-ask rule already mitigates this; the kernel promotes it from
   etiquette to a measured concern (see K-LOOP-4).

## Part 3 — The v1 Universal Kernel (extracted from what already runs here)

**Architecture: kernel + overlay.** The kernel is the project-agnostic
operating model — invariant *classes*, loops, gates, roles, escalation
taxonomy, cost and communication rules. Each project supplies an **overlay**
that instantiates the parameterized parts with its domain's specifics and
tribal knowledge. A project = kernel (verbatim) + overlay (unique). Nothing
in the kernel may be weakened by an overlay; overlays only ADD constraints or
bind parameters.

### 3.1 Kernel invariant classes (parameterized trust physics)

Each is the generalization of a OneLive invariant that has already survived
adversarial review. An overlay binds the bracketed parameters.

- **I1 — Generation never self-certifies.** No AI-generated output reaches the
  [trusted surface] (users, investors, a ledger, a trade, a filing) except
  through a [custodied gate] the generator cannot import or bypass.
  (OneLive: extraction → gate → promote; AI never publishes. multibagger: no
  AI-asserted figure to the investor surface without the verification gate.
  Promise Ledger: no claim enters the ledger unverified.)
- **I2 — Gates fail closed.** An unreadable manifest, missing env, empty
  golden set, or unverifiable record is a RED, never a skip. A gate that
  cannot fail proves nothing.
- **I3 — Verifier independence.** The generator's work is reviewed by a
  different model family; the generator never merges an unreviewed change to
  its own examiners (gate custody); no code judges its own certification
  (base-owned copies; a PR's copy never judges itself).
- **I4 — Adverse findings are shown, never hidden.** [Disputed/failed/
  uncertain] states are first-class and displayed as such on the trusted
  surface; deletion or silent suppression is a violation.
- **I5 — No incentive contamination of trust surfaces.** Nothing paid,
  preferred, or self-interested may alter ranking, verdicts, or verification
  outcomes on the [trusted surface]. (OneLive: no pay-to-rank. multibagger:
  no position-motivated assertion. Promise Ledger: no issuer-paid softening.)
- **I6 — No silent deferrals.** Every "later" is recorded with the bar it
  deviates from and an objective resolution trigger, in the same commit
  (the Record; mechanically enforced in code comments by a deferral scan).
- **I7 — Escalation is an enumerated, closed list.** Money/new services ·
  legal posture · trust-invariant changes · gate-threshold relaxations ·
  go-live pushes · credential minting · [overlay additions]. Everything else:
  decide, log the decision record, proceed. Making a gate easier to pass is
  never an agent decision.

### 3.2 Kernel loops (the working rhythm)

- **K-LOOP-1 Session bookends.** Open: reconcile state against ground truth
  (git/PRs/DB) before trusting any state file; disk is truth, never chat
  memory. Close: update STATE + TODOS + changelog + memory notes; review open
  Record entries (a fired-but-unactioned trigger is a defect).
- **K-LOOP-2 Contract-first.** No work before a written contract (goal, scope,
  non-goals, done-criteria) in STATE. Ambiguity → ONE consolidated question
  set to the founder, then proceed.
- **K-LOOP-3 Inner loop.** Understand → implement → self-review against the
  quality bar → fix → verify against ground truth → repeat until review finds
  nothing new AND verification is green. Findings are claims until verified.
- **K-LOOP-4 Decision-throughput discipline.** Founder interrupts are batched
  (one numbered, phone-friendly list), and every ask names its default-if-no-
  answer so unanswered questions block the minimum possible work. (New with
  this proposal — Cherny's Step-3 bottleneck, made operational.)
- **K-LOOP-5 Kaizen.** Zero escaped defects is absolute; internally-caught
  defects are treasure — ledger row per catch (gate, class); repeat classes
  get a structural gate-gap fix, not a promise.

### 3.3 Kernel gates (the verification stack)

1. **Composite validate** — one command runs everything (lint, full tests,
   trust gate, eval harness, deferral scan, audit sweeps); skips are debt,
   bound to Record entries, never silent.
2. **Golden-set exam pattern** — any AI capability that feeds a trusted
   surface is unlocked only by a passing exam on the REAL provider path, at a
   ratified threshold, with a valid sample floor, injection cases included,
   and the exam harness itself certified (the harness that grades the model
   must not be gradeable by the model's author-PR — certification records
   enter only through a base-owned authenticator).
3. **Independent adversarial review on every PR** — non-generator family,
   APPROVE/REQUEST-CHANGES, no path filter; mandatory-deeper for auth,
   pipeline, SQL/RLS, data-trust, prompts, and gate custody.
4. **Merge rule (Step-3 posture — ratified for OneLive specifically,
   2026-07-18; every adopting project must obtain its OWN founder
   ratification via overlay binding 7 before its agent merges anything):**
   the agent merges its own PR only at evaluator-APPROVE + every required
   check green on the final head (red or pending = hard stop), notifying the
   founder. Product publishing stays custodied per I1 regardless.
5. **Sentinel** — error tracking on every deployed surface + dead-man ping on
   every scheduled job, BEFORE the first scheduled run; budget caps before
   first spend.

### 3.4 Kernel roles (the org chart, model-agnostic)

Generator (writes) · Independent Evaluator (non-generator family, attacks
every PR) · Friction agent (pre-mortem before irreversible actions, structured
lenses that never see each other's output, conflict-preserving merge) ·
Sentinel (monitoring) · Librarian (bookends, digests) · the six-hat registry
(White=deterministic facts, Red=the founder, Black=evaluator/friction,
Yellow=deliberate best case, Green=po provocation, Blue=process+merge). Hats
fire at divergent/founder-crucial moments only; no hat's output is evidence.

### 3.5 Kernel cost & communication rules

Cheapest-capable tier first, escalation logged never silent, gates identical
at every tier; founder communication in plain language with
why-this-not-that, honest tradeoffs, direct links, numbered phone-friendly
steps, consolidated asks.

### 3.6 The overlay contract (what each project MUST define)

An overlay is a single `OVERLAY.md` (plus linked docs) binding:

1. **Trusted surfaces + custody** — what I1 protects, who holds the promote
   key, what "publish" means here.
2. **Domain invariants** — additional physics (e.g. OneLive's 4-state
   confidence model; Promise Ledger's never-verbatim storage; multibagger's
   no-AI-trades).
3. **Golden sets + ratified thresholds** — the exams, their bars, their
   ratchet rules.
4. **Escalation additions** — domain items appended to I7's closed list.
5. **Key manifest** — every credential the project touches; agents never mint
   keys.
6. **Tribal knowledge** — the memory dirs (decisions, gotchas, entity notes)
   and the design/tone canon; the stuff that makes the project itself.
7. **Adoption-step declaration** — which Cherny step the project currently
   operates at, per surface (repo ops vs product path may differ, as OneLive's
   do), and what evidence justified the current step. Moving UP a step is a
   founder decision; the kernel's gates are the prerequisites, not the
   trigger.

### 3.7 Mapping: kernel components → Cherny's "guardrails to advance"

| To reach | Cherny's unlock | Kernel component that provides it |
|---|---|---|
| Step 1→2 | Self-verification so you needn't read everything | K-GATE-1 validate, K-LOOP-3 inner loop, tests-in-same-PR |
| Step 2→3 | Automated review by default, isolation, trust in gates | K-GATE-3 evaluator on every PR, K-GATE-2 golden exams, I2/I3, K-GATE-4 merge rule |
| Step 3→4 | Routines, batch, cost monitoring, decision throughput | Sentinel + dead-man + budget caps, model routing, K-LOOP-4, night-shift orchestration |

The kernel is, in Cherny's terms, a complete Step-3 guardrail inventory —
which is the claim that makes it worth universalizing.

## Part 4 — Instantiation plan (v1)

**Recommended packaging: a template repository** (`universal-kernel` or
similar) containing the kernel docs (parameterized CLAUDE.md, OPERATING_RULES,
KAIZEN, RECORD, hats registry, SESSION_START) + the portable tools
(session_reconcile, validate skeleton, deferral_scan, adversarial_review,
model_router, po_battery, kaizen helpers) + an `OVERLAY.md` template with the
seven bindings above. New project = instantiate template → fill overlay →
first session runs the bookends natively.

**Why this, not the alternatives considered:**
- *Copy-paste per project* — zero coupling but guarantees drift; kernel fixes
  (e.g. a deferral-scan bug) never propagate. Rejected as the steady state,
  acceptable as the bootstrap.
- *Git submodule/subtree shared kernel* — propagates fixes but couples every
  project to kernel churn and makes gate custody murkier (a kernel bump is a
  gate change in EVERY project at once — one PR would need N evaluators).
  Rejected for v1; revisit-trigger: the third adopting project, when drift
  cost is measurable rather than hypothetical.
- *Template repo (chosen)* — fixes propagate by deliberate, per-project,
  evaluator-reviewed pulls (drift is visible as a diff against the template);
  each project keeps sovereign gate custody. Tradeoff, honestly: propagation
  is manual, and the template needs an owner or it rots — the weekly digest
  should carry a "kernel delta" line whenever the template changes.

**Bootstrap checklist for an adopting project (numbered, ~1 session):**
1. Instantiate the template; fill `OVERLAY.md` (seven bindings; the founder
   ratifies bindings 1, 3, and 4).
2. Wire the evaluator (its API key + the review workflow on every PR) before
   any other code lands — I3 from commit one.
3. Stand up validate with whatever exists (even nearly-empty test suites run
   green honestly); skips → Record from day one (I6).
4. Declare the adoption step per surface (overlay binding 7) with evidence.
5. First feature work begins only after 1–4 — the same order OneLive proved:
   verification loop first, then the agent.

**First adopters, in order:** (1) **multibagger** — cleanest test, founder
must attach the repo to a session and ratify its overlay; (2) **Promise
Ledger** — at sprint step 12 the extraction to its own repo uses this
checklist instead of inventing one.

## Part 5 — Consolidated founder asks (the ONLY questions from this session)

1. **Ratify the kernel/overlay split** (Part 3) as the v1 universal model —
   or mark specific invariants/loops you want changed. Nothing here alters
   OneLive's ratified charter; for OneLive this document is descriptive.
2. **Approve creating the template repository AND name its owner** (new repo
   = repo operation needing your GitHub say-so; no code moves out of OneLive
   until then). The ownership half is not optional garnish: an unowned
   template rots silently (Part 4's stated tradeoff), so approval without a
   named owner + a standing maintenance trigger (proposed: the weekly digest
   carries a "kernel delta" line, and any kernel-relevant OneLive gate fix
   opens a template-sync TODO in the same commit) is treated as NOT approved.
   Default if unanswered: nothing happens — this stays a paper spec.
3. **Pick multibagger's first session** — attach that repo to a session and
   I'll run the bootstrap checklist against it, producing its OVERLAY.md as a
   proposal for you. Default: untouched.
4. **Spot-check the article summary** (Part 1) from a normal browser, since
   this sandbox couldn't read the primary source — 2 minutes; the links are
   in the provenance block. Default: kernel stands anyway (it derives from
   our repo, not the article).

---

## Appendix A — the verbatim search excerpts behind Part 1 (evaluator r2 nit)

Everything known about the article in this sandbox is reproduced below,
verbatim, so the reconstruction is auditable against exactly what was seen.
Two kinds of material, labeled honestly: **[verbatim result title]** = the
literal title/preview text of a search result (author's or platform's own
words); **[search-tool synthesis]** = the search tool's summary sentences over
its result set (a machine's paraphrase, one step further from the source).
Nothing else was readable — every direct fetch returned HTTP 403.

**[verbatim result title]** (threads.com/@carnage4life):
> "Boris Cherny's 5 stages of AI adoption for software teams: Gated:
> Restricted access to AI. Assisted: 1 agent per dev(high supervision).
> Parallel: 10 agents per dev(AI codes, humans verify). Autonomy: 100 agents
> per dev(AI verifies). AI-Native: 1,000+ agents (AI decides what work to
> do)."

**[verbatim result title]** (substack.com/@aisupremacy, Michael Spencer):
> "According to Boris Cherny the Creator and Head of Claude Code he's been
> watching teams adopt AI, and he keeps seeing the same 4 steps. He mapped
> them out here: Steps of AI Adoption: He says Anthropic is on step 3 and
> pushing toward 4. And that personally, he just hit level 4…"

**[search-tool synthesis]** (over the query "Boris Cherny steps AI adoption
Claude Code July 2026"):
> "On July 16, 2026, Boris Cherny — creator of Claude Code — published Steps
> of AI Adoption on Anthropic's site. The framework names five maturity
> levels for Claude Code teams: Gated (0) → Assisted (~1) → Parallel (~10) →
> Supervised autonomy (~100) → AI-native (1,000+)." · "the gap is not 'more
> tokens,' it is bottlenecks and guardrails per maturity step." · "The
> framework became widely shared, with Lance Martin reposting it July 17; the
> thread hit 251K+ views in hours."

**[search-tool synthesis]** (over the step-detail query):
> "Step 0 is Gated: no access, legacy approvals. Step 1 is Assisted, one
> agent, you and it as a pair. Step 2 is Parallel, about ten agents, and you
> become an Orchestrator. Step 3 is Supervised autonomy, roughly a hundred
> agents, and Cherny calls the role Manager of managers. Step 4 is AI-native,
> a thousand or more, steering by intent." · "The bottlenecks themselves
> evolve: Your attention. Reviewing output. Trust in the loop and your team's
> decision throughput. Identifying and automating work at scale." · "What
> separates them is trust, not the model."

**[search-tool synthesis]** (over the guardrails/unlocks query):
> "Each step defines your role, the unlock, the bottleneck, Anthropic
> products, and guardrails to advance. Tokens alone do not move you forward —
> verification loops, auto mode, automated review, worktree isolation,
> routines, and cost monitoring do." · "giving Claude ways to verify its own
> work end to end means enabling auto mode for permissions, defaulting on
> automated code review and security review, and using interfaces that let
> you manage multiple agents at once. To get to higher levels it means /loop,
> /batch, dynamic workflows, and worktree isolation for subagents." · "the
> bottleneck is trust in the verification loop and the decision speed of the
> team. This is also where Cherny names the central trap of the whole model:
> scaling the agent count before the verification loop has earned that
> trust."

Part 1's table contains NO claim beyond what appears above; where excerpts
differed in granularity (four steps vs five levels counting Step 0), the doc
uses the 0–4 numbering the majority of excerpts carry.
