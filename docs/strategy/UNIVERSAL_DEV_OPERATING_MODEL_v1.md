# Universal Development & Operating Model v1 — kernel + overlay

**Status:** KERNEL RATIFIED (founder, 2026-07-24, verbatim: "Ratify the
Kernel.") — Part 3's kernel AS MERGED IN PR #61 is canon; each project's
OVERLAY remains a per-project instrument ratified at that project's
bootstrap (binding 7). Scope precision (evaluator, PR #62 r1): the
ratification covers the kernel as it stood when ratified — the K-LOOP-5
addition drafted AFTER it (from the founder-directed Kaizen review, Part 6)
is a PROPOSED AMENDMENT pending its own explicit ratification and binds
nothing until then. Companion decisions from the same founder message are
annotated in Part 5.
**Date:** 2026-07-24 · **Session Contract:** #21 (STATE.md) · **Author:** Generator (Claude Code session)
**Prompted by:** founder request to assess Boris Cherny's "Steps of AI Adoption"
(July 2026) against the portfolio — OneLive, multibagger, the press-release
venture (Promise Ledger / PR-aggregator) — and to define a v1 single
**universal** development/operating-model foundation that any project can
inherit and then specialize with its own requirements, peculiarities, and
tribal knowledge.

**Source provenance (honest, precisely scoped — updated 2026-07-24):**
Terminology, pinned once (evaluator r3 nit): wherever this doc or its
companion records say "the primary," they mean the FOUNDER-SUPPLIED SOURCE
ARTIFACT — the explainx export embedding Cherny's table — not Cherny's
original page, which remains unfetched. Part 1
is now VERIFIED against the primary: the founder supplied the full article
export (`Boris_Cherny_Jul_16_2026.md` — the explainx.ai post, which embeds
Cherny's table) directly into the session, satisfying the primary-source gate
(`docs/memory/decisions/2026-07-24_primary-source-gate.md`); the corrections
made during verification are itemized at the end of Part 1. The artifact
itself is committed for audit at
`docs/research/sources/Boris_Cherny_Jul_16_2026.md` with a SHA-256 manifest
(`…MANIFEST.json`) alongside — the verification claim is checkable against
the exact bytes, not "trust me, I saw it." Precision on source identity: the
verified artifact is the EXPLAINX post; it embeds what it presents as
Cherny's table and states that Cherny published on Anthropic's site — that
last claim is the explainx author's, since Cherny's own page remains
unfetched. History, kept for
the record: at first writing NO full article text was readable from this
sandbox — the primary URL
(<https://www.explainx.ai/blog/boris-cherny-steps-ai-adoption-claude-code-july-2026>)
and every mirror returned HTTP 403 through the egress proxy, and the original
Part 1 was reconstructed only from search-result excerpts of the coverage
below — the pattern the founder's directive has since forbidden outright.

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

> **VERIFIED AGAINST THE FOUNDER-SUPPLIED PRIMARY (2026-07-24):** the founder
> supplied the full article export (`Boris_Cherny_Jul_16_2026.md`, the
> explainx.ai post embedding Cherny's table) after this part had been
> reconstructed from search excerpts and then BLOCKED under the primary-source
> gate (`docs/memory/decisions/2026-07-24_primary-source-gate.md`). This
> section is now corrected against that primary; the corrections themselves
> are listed at the end of this part so the delta from the excerpt
> reconstruction is auditable. Appendix A (the excerpts) is retained as the
> record of what the pre-verification draft rested on, marked superseded.

Boris Cherny (creator/head of Claude Code at Anthropic) published "Steps of AI
Adoption" on 2026-07-16 — on Anthropic's site per the explainx post's own
account (the artifact verified here is the explainx export embedding his
table; Cherny's original page remains unfetched). Five maturity levels; each step
names a human role, an approximate concurrent-agent count, what it looks like,
the binding bottleneck, products that help, and guardrails — plus an explicit
"how to get to the next step" transition between every pair.

| Step | Name | ~Agents | Human role | Bottleneck (per the primary) | How you reach the NEXT step (per the primary) |
|---|---|---|---|---|---|
| 0 | Gated | 0 | — | Legacy security/approval processes; cost-per-token containment vs outcomes; lack of true technical voices in decisionmaking | Executive/buyer alignment + escalation of blockers; frameworks for launching Claude securely |
| 1 | Assisted | ~1 | You + an agent (a pair) | Your attention and the need to inspect each response/edit; low trust + no self-verification ⇒ work stays synchronous | Run >1 agent; a self-verification loop you TRUST (tests + build + lint + e2e in a real dev env); auto mode; automate code review |
| 2 | Parallel | ~10 | Orchestrator | Reviewing output (many streams instead of keystrokes); prompting/steering while juggling sessions | Give Claude context pull (code, wikis, discussions); agency + review speed across team boundaries; break work into loops and routines; let Claude kick off Claude |
| 3 | Supervised autonomy | ~100 | Manager of managers (an org tree) | Trust in the loop + your team's decision throughput; token efficiency at scale; "your trap is scaling agent count before the loop has earned widespread trust" | Scaled automation of domain-specific use cases (code migration, fuzzing, feature-building, feedback remediation) |
| 4 | AI-native | ~1,000+ | VP steering by intent | Identifying and automating work at scale, AND enforcing the right guardrails for each type of work — not one blanket policy | — (frontier) |

Load-bearing points, now quoted from the primary rather than paraphrased:

1. Cherny on X: *"There's no one right path through the steps… at each step,
   tokens aren't enough… you need to find and break down the next set of
   bottlenecks, and build up the next set of guardrails."* (The earlier
   draft's "what separates the steps is trust, not the model" was a
   paraphrase; the trust reading is supported — Step 1's bottleneck is low
   trust, Step 3's is trust in the loop — but it is OUR inference, labeled as
   such.)
2. The scaling trap is Cherny's **Step-3** bottleneck, verbatim: *"your trap
   is scaling agent count before the loop has earned widespread trust"* (the
   earlier draft over-generalized it to "the central trap of the whole
   model").
3. Cherny's Step-3 test: *"Ask yourself: is this something an engineer would
   have done?"* — automate if yes, keep a human gate if no.
4. Step-4 guardrails include *"separation between automation lanes
   (migrations, triage) and human-gated lanes (production deploys,
   security-sensitive refactors)"* — the primary's own statement of the
   distinction our kernel encodes as I1.
5. Step-2 guardrails include *"Hold the same quality bar for human and
   agent-generated code"* and Step-3 lists *"CLAUDE.md and Skills to encode
   standards."*
6. Status claims: Anthropic says it operates at Step 3; Cherny personally
   claimed Step 4 (2026-07-17). The article's own caveat: treat that as
   dogfooding signal, "not a guarantee your team can copy day one without
   Step 2–3 harness investment." Also his: adoption is measured by BEHAVIOR,
   not license tier ("We bought Enterprise so we're Step 3" is a named
   misread).

**Corrections from the excerpt reconstruction (the auditable delta):** (a) the
"what unlocks the next step" cells for Steps 2 and 3 previously listed those
steps' own features (review defaults/worktrees; loops/routines/cost
monitoring) instead of Cherny's actual transitions (context pull + loops +
Claude-kicks-off-Claude for 2→3; domain-use-case automation for 3→4) — fixed;
(b) thesis 1 relabeled paraphrase-as-inference per point 1; (c) the trap
rescoped to Step 3 per point 2; (d) Step 4's bottleneck gains the
per-work-type-guardrails half; (e) role names corrected to the primary's ("an
org tree", "VP steering by intent"). Nothing in Parts 2–5 reversed: the
corrected transitions STRENGTHEN the Part 3.7 mapping (Cherny's 2→3 unlock —
loops, context, Claude-kicks-off-Claude — is the kernel's loop/orchestration
layer; his lane separation is I1).

### Part 1b — the companion piece in the same file (the "final 10%" chart)

The founder-supplied file also carries the same-week "Kr$na" chart analysis
(sic — the primary's own spelling of the author's handle):
idea ≈ 5 min (green) → working demo ≈ 2 h (yellow) → the final 10% ≈ 6 months
(red: edge cases, security, perf, a11y, migrations, observability) → abandoned
= ∞ (blue), with the mapping that Step 1–2 teams get "incredible yellow bars
and brutal red bars" while Step 3+ runs red-bar work continuously in the
background. Applicability here is direct and confirming: OneLive's harness IS
red-bar machinery (validate, evaluator, golden exams, sentinel), the FLOW
prototype rounds are deliberately-labeled yellow-bar work (sample-data truth
boundaries on every surface), and the article's mitigation list — define
red-bar done before yellow, CI fails on missing tests, security review by
default, kill blue early — is the charter's existing practice restated. One
adoptable nugget for the overlay contract: its "before you post the demo /
before you call it production" checklist is a compact template for overlay
binding 7's per-surface step declaration.

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
  get a structural gate-gap fix, not a promise. **PROPOSED AMENDMENT
  (2026-07-24, generator-drafted from the founder-directed review in
  Part 6 — PENDING explicit founder ratification; until ratified, K-LOOP-5
  ends at the previous sentence and this paragraph binds nothing):**
  counter-measures are context-specific and discrete — each fix scoped to
  the defect's ACTUAL surface, with the defect shape pinned red in tests
  and the gate's honest limit stated; one-size-fits-all responses are
  reserved for TRANSPORT (the composite runner, the evaluator on every PR,
  the Record rule) and never for judgment; a blanket rule proposed as a
  class fix is itself a smell; the ledger's class watch is the single
  index that keeps discrete gates from fragmenting into unfindable pieces.

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

(Transitions below are quoted from the primary's "how to get from step N to
N+1" rows, corrected 2026-07-24 during primary verification.)

| To reach | Cherny's transition (per the primary) | Kernel component that provides it |
|---|---|---|
| Step 1→2 | Run >1 agent; a self-verification loop you trust (tests+build+lint+e2e); auto mode; automate code review | K-GATE-1 validate, K-LOOP-3 inner loop, tests-in-same-PR, K-GATE-3 evaluator |
| Step 2→3 | Context pull (code, wikis, discussions); agency + review speed; break work into loops and routines; let Claude kick off Claude | K-LOOP-1/2 bookends + contract, memory/tribal-knowledge dirs (overlay binding 6), K-GATE-2 golden exams + I2/I3 earning the trust, K-GATE-4 merge rule, night-shift orchestration |
| Step 3→4 | Scaled automation of domain-specific use cases (migration, fuzzing, feature-building, remediation) — with per-work-type guardrails and lane separation | Sentinel + dead-man + budget caps before first scheduled run, model routing, K-LOOP-4 decision throughput, I1 lane separation (automation lanes vs human-gated lanes) |

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

## Part 5 — Consolidated founder asks — ANSWERED 2026-07-24 (decisions annotated per ask; decision record: `docs/memory/decisions/2026-07-24_kernel-ratified-and-directives.md`)

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


**Decisions received (founder message, 2026-07-24; verbatim text lives in
the decision record only — dissemination of the founder's instructions is
deliberately minimized to that single home):** ask 1 — **RATIFIED** ("Ratify
the Kernel."), scope-precise per the status line above: the kernel as merged
in PR #61. ask 2 — **APPROVED with conditions** recorded in the decision
record (named owner; private visibility); creation is still pending because
this session's GitHub scope covers only the onelive repo and holds no
repo-creation right — smallest unblock: the founder creates the empty
private repo (~1 min) and attaches it to a session. ask 3 — **ON HOLD**
("Hold on the Multibagger") — no session scheduled, nothing touched.
ask 4 — **EXPLICITLY STILL OPEN** (optional, no deadline): a read of
Cherny's original page can still correct Part 1; this ask survives the
TODOS closure of asks 1–3, which covered only the decided items. Companion
decision: the Vercel preview fix is APPROVED ("Good with the Vercel fix") —
no Vercel/Clerk credentials exist in the agent sandbox, so the 2-minute
dashboard step stays founder-hands (documented on PR #60). **NEW ask 5
(created by the evaluator's PR #62 r1 scope correction):** the Kaizen
review's distilled principle is DRAFTED as a K-LOOP-5 amendment (Part 3.2)
but is generator-authored — ratify it, edit it, or decline it; until then
it binds nothing.

## Part 6 — Kaizen application review (founder-directed 2026-07-24: "more context-specific discreet vs. one fits all")

**Question examined:** is OneLive's recent continuous-improvement practice
appropriately context-specific and discrete, or drifting toward
one-size-fits-all responses? Grounded in the Kaizen ledger's recent rows and
its class watch — the primary artifacts, read directly.

**Finding 1 — the practice is decisively context-specific, and it got MORE so
recently.** Every repeat class in the watch carries its OWN counter-measure
and its OWN objective trigger, none interchangeable: empty-env fail-open has
a three-step escalation history ending in "next time it's an env-contract
linter, not another patch"; wrong-arithmetic has a numeric-forms gate with
its non-numeric gap STATED and trigger-armed; incomplete-enumeration
produced the POLICY-vs-MIRROR list taxonomy (mirror lists must be derived or
swept; policy lists ARE ground truth) — a classification, not a blanket rule
— and its repo-wide audit ran only when its own trigger fired. This week's
work sharpened the pattern: one family (stale-live-incident-state) now has
THREE sibling gates because its recurrences live on three genuinely
different surfaces — the live NEXT queue vs cadence claims vs lifecycle-
marker claims — each gate narrow, each with its defect shapes pinned red,
each stating its honest limit. The ledger's own precedent ("the fix moves to
the recurrence's actual surface") was upheld three separate times in one
arc.

**Finding 2 — the one-size-fits-all elements that DO exist are transport,
not judgment, and that is correct.** The composite validate runner, the
evaluator riding every PR with no path filter, and the Record rule are
uniform PIPES; the content flowing through them (which gates, which
thresholds, which classes) is all discrete. Uniform transport is what makes
discrete judgment auditable — this split should be preserved, and K-LOOP-5
now encodes it.

**Finding 3 — the honest costs, so the ratification is eyes-open.** (a)
Discrete gates accumulate: PR #61 alone added three, and took six evaluator
rounds — three of which were the evaluator correctly attacking repair gates
until their claims matched their behavior. That round-cost is the price of
gates that don't overclaim, and the new claims-discipline meta-gate now
forces the boundary statement that made those attacks resolvable. (b) The
blanket-rule temptation appears precisely at repeat-class moments, when a
sweeping fix feels decisive; the ratified principle names it a smell so the
temptation is pre-answered. (c) Fragmentation risk is real as gates
multiply; the class watch is the single index and must stay the only one.

**Verdict:** current practice matches the founder's directive — context-
specific and discrete, with uniform transport only. No corrective work is
needed. The distilled principle is DRAFTED as a proposed K-LOOP-5
amendment (marked as such in Part 3.2, pending explicit founder
ratification — ask 5 in Part 5): the review directive asked a question and
stated a preference; it did not ratify canonical wording the generator then
authored, and the evaluator correctly blocked the first version of this PR
for conflating the two.

---

## Appendix A — the verbatim search excerpts behind the PRE-verification draft (SUPERSEDED 2026-07-24)

> **SUPERSEDED:** Part 1 is now verified against the founder-supplied primary;
> these excerpts are retained only as the record of what the original draft
> rested on (and as the evidence base for the Kaizen `research-without-
> primary-source` row — the verification found five substantive deviations,
> itemized in Part 1's corrections note, which is exactly why excerpt
> reconstruction is forbidden). Do not cite this appendix for framework
> content.

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
