# CLAUDE.md — the OneLive standing contract

Read at the start of every session. This file is short on purpose: it is the
binding contract, not the library. Rewritten 2026-07-26 from 2,834 words per
`docs/V1_AUDIT_2026-07-26.md` §5, then amended the same day to **open with the
vision instead of the rules** (founder directive, record at
`docs/memory/decisions/2026-07-26_vision-first-directive.md`). **No invariant, gate,
threshold or check was weakened in either pass.**

---

## Why this exists — read before the rules

**Vision:** *"A world where live music is easy to find, fairly represented, and
culturally valued. At scale: to let culture grow without being stripped of its
soul."*
**Mission:** *"To assemble truth about live music, protect discovery from
distortion, and help real culture travel."*
**What it is:** a system of record for what's really happening tonight —
artist-first by structure, trust-driven, **calm, useful, real**. Culture becomes
infrastructure, not content.
**What it is not:** not ticketing, not a social feed, not pay-to-play, not an
algorithm chasing engagement.

**The moment every change is judged against:** 9:04 PM, a warm Austin night, a
sidewalk on East 6th, a friend asking "so what are we doing?" — and about **ten
seconds** of everyone's patience.

**The feeling to create, which is a specification and not decoration:** the small
thrill of **anticipation** fused with **calm certainty** — *"this thing knows, and
it's right."* No FOMO, no doomscroll dread, no decision fatigue. A friend who
always knows what's on, has never once been wrong, and never makes it about
themselves.

**The payoff, and the whole brand in one sentence:** *"The fan locks their phone
within ten seconds holding a decision they feel good about, and the show is exactly
as promised when they walk in. That kept promise, repeated nightly, is the entire
brand."*

Full ratified text: `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` §1–§6.
Measurable form: `docs/BAR.md` §0 and section P.

---

**The three files that matter, in order:**

1. **`docs/BAR.md`** — what world class means for every aspect of this build, as a
   number, with the gate that enforces it and its honest current status. This is
   the definition of done. Read it before writing code.
2. **`docs/V1.md`** — what v1 is, what is left, in order, and the only open asks
   for the founder.
3. **`docs/HOW_WE_WORK.md`** — the loop: how a change goes from contract to merge.

Everything else is classified in `docs/INDEX.md` as CANON (binding), REFERENCE
(read on demand) or HISTORICAL (never a rule). Only the CANON list binds you.

---

## Prime directives

**1. Trust invariants are physics, not policy.** These five do not bend:

- **The AI that extracts never decides what publishes.** Extraction cannot
  promote; the gate decides; a fabricated event is never published. (The founder
  ratified on 2026-07-25 that a *gate-passing* candidate may be promoted without a
  human click, at its earned confidence, with named exceptions — see
  `docs/memory/decisions/2026-07-25_auto-publish-earned-confidence-ratification.md`.
  That is an operational rule the founder sets. The invariant above is untouched
  by it: the extractor still never decides, and fabrication is still never
  published.)
- **The orchestrator cannot import the promote path.** Structurally, not by
  convention.
- **No pay-to-rank surface, ever.** No paid field may influence ordering.
- **Disputed is always shown as disputed.** Never deleted, never hidden.
- **Row-level security stays fail-closed.**

Any change touching these: **STOP and escalate to the founder.**

Two ratified scope notes, in full at `docs/EXTRACTION_EXCEPTION.md`: (a) the agent
**may** merge its own PR when the independent non-Claude reviewer has APPROVED and
every required check on the final head is green — red or pending is a hard stop —
notifying the founder at merge; (b) there is exactly **one** enumerated exception,
the golden-exam verifier's red-by-design refusal on exam-harness changes, and a
machine (`tools/classify_extraction_surface.py`), never agent judgement, decides
whether it applies. Adding any further exception is a gate-threshold relaxation:
founder-crucial.

**2. Disk is truth.** Never trust chat memory over a file. Every session begins
with `python tools/session_reconcile.py` and ends by updating `STATE.md`,
`TODOS.md` and `docs/ONE_LIVE_CHANGE_LOG.md`. If the reconciler cannot verify a
fact, the fact is **UNVERIFIED** and must be labelled that way — never upgraded
to truth by repetition.

**3. Contract first.** No code before the session contract (goal, scope,
done-criteria) is written to `STATE.md`. If the contract is ambiguous, ask the
founder **one** consolidated question set, then proceed.

**4. Green before you finish.** `bash tools/validate` must pass before any PR is
opened. `--allow-skips` is temporary debt and every skip is recorded. A SKIP is
not a pass. *(Note: the gate is a bash script — `python tools/validate` errors out.
That wrong command sat in this charter until 2026-07-26.)*

**5. Every change serves the vision, and the feeling is part of the spec.**
(Founder directive, 2026-07-26, verbatim in
`docs/memory/decisions/2026-07-26_vision-first-directive.md`: *"Everything is to be
built toward the vision and goals and objectives and other content surrounding this
project and how it is supposed to work and make people feel. All actions should be
in support of all of those things."*)

*Does this serve the fan on the sidewalk at 9:04 PM?* is a **blocking question in
review, at the same standing as a failing test.** A change that is correct, fast,
well-tested and makes that moment worse is not done. Work that serves neither the
vision nor a `docs/BAR.md` row is not neutral — it is cost. This is the directive
that keeps the harness from becoming the product.

**6. Nothing is deferred silently.** Any "for now", "check later", "revisit", or
noticed-but-unfixed issue — in code, docs, PR text or chat — gets a row in
`docs/RECORD.md` **in the same commit**: what is deferred, the bar it deviates
from, and an objective resolution trigger. Never "someday". Enforced by
`tools/deferral_scan.py`. Fix-in-place beats recording; recording beats silence;
silence is a violation.

---

## Founder-crucial — the only interrupts

Money or new services · legal posture · trust-invariant changes ·
**gate-threshold relaxations** (any loosening of validate / trust_gate / evaluator
/ eval-harness enforcement — making a gate easier to pass is never an agent
decision) · go-live and allowlist pushes · credential minting.

Everything else: decide, write the decision record, proceed.

---

## Who does what

- **Generator** — this session. Writes code and its tests in the same change,
  small and self-contained.
- **Independent Evaluator** — non-Claude models (`OPENAI_API_KEY`, plus a second
  seat via `GEMINI_API_KEY`), run by `tools/adversarial_review.py`. **Mandatory on
  every PR**, enforced by `.github/workflows/adversarial-review.yml` with no path
  filter. The generator never grades its own work and never merges an unreviewed
  change to its own examiners.
- **Friction pass** — before any irreversible action (deploy, migration, spend,
  prompt-version bump), the plan goes in `docs/FRICTION_LOG.md` and is attacked by
  a non-Claude model: *what breaks, who is harmed, cheaper path, founder-crucial
  or not?* Blockers are answered in writing.
- **Sentinel** — Sentry on web, API and worker; a healthchecks.io dead-man ping on
  every scheduled job. **No scheduled loop ships without both.**
- **Red hat is the founder, never an agent.**

---

## Cost discipline

1. **Cheapest capable method first** — model tier, technique and tool.
   `docs/MODEL_ROUTING.md`, resolved by `tools/model_router.py`.
2. **Escalate spend deliberately, never silently.** Log the reason.
3. **Quality gates never relax for cost.** Thresholds are identical at every tier.
   Efficiency comes from routing, caching and batching — never from skipping
   verification.
4. **Measure, don't guess.** Cost per verified event and per-run ceilings govern
   the pipeline.
5. **Prefer the zero-marginal-cost source.** If a deterministic feed and a metered
   AI call can produce the same fact, the feed wins.

---

## Architecture

`Sources → Raw Fetch → Extract → Candidate Store → Evidence → Gate → Promote →
Canonical Event → /tonight`. Every stage independently auditable.

Confidence is a **4-state** model — `unverified` | `likely` | `confirmed` |
`disputed`. Confirmed decision; never revert to three, never add a fifth.

**Stack, as actually built** (this list was wrong in three ways until 2026-07-26):

- PostgreSQL 15 via Supabase, project ref `vqipjlvzfiwnandjumvx`
- Python + FastAPI (`api/`) and plain Python workers (`worker/`) — **no Celery**
- Claude API for weak-signal extraction from fetched text only
- Next.js 15 App Router in **`web/`** (consumer feed + ops console)
- Clerk for auth; Sentry; healthchecks.io
- Deferred, not built: S3 photo storage, Stripe Connect

**Tastemaker posts** (human opinion) must NEVER touch the candidate / gating /
promotion pipeline. Separate trust category, structurally separate path.

---

## Coding standards

Full checklist: `docs/CODING_CONVENTIONS.md`. Mechanically enforced by
`tools/lint.py`; the pre-commit hook (`tools/install_hooks.sh`) runs it with
`trust_gate.py` and blocks the commit on any violation.

- TypeScript strict everywhere; no `any` without a comment saying why.
- Every endpoint validates input (pydantic or zod) before touching the database.
- Parameterised queries only — never interpolate SQL.
- Auth checked on every protected route.
- No swallowed errors; no silent degradation — **"we failed" must never look
  identical to "there was nothing to do."** This is the founding anti-pattern.
- No dead code. A module nothing can reach is not done: wire it or delete it.
- Tests ship in the same change, and a new gate is proven **red** before it is
  proven green.

---

## Design

`docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` is ratified canon: verbatim
copy strings, **no badges and no "confirmed" text**, low confidence shown as a
quiet icon opening a dismissible sheet plus a venue link, WCAG 2.2 AA, LCP ≤ 2.5 s.
Design PRs are scored against the brief's 8-criterion rubric and deltas are
logged, never silent. AI-written descriptors go through the Descriptor Foundry.

---

## Environment (never in git)

`ONELIVE_DB_DSN` · Supabase publishable key (web) · `ANTHROPIC_API_KEY`
(extraction only, console spend cap set FIRST) · `OPENAI_API_KEY` and
`GEMINI_API_KEY` (reviewers) · Clerk keys · `SENTRY_DSN` ·
`ORCHESTRATOR_PING_URL`. Deployment variables and their runtime rules:
`docs/DEPLOY.md` — the single source of truth for env config.

**Agents never mint keys.**

---

## Current mission

**Finish v1: `docs/V1.md`.** Five done-criteria, ordered, with three founder asks.
Nothing outside that list gets built — not the carousel engine, not the
promise-ledger venture, not the knowledge-graph brain, not native mobile. They
stay in the tree, frozen, until the site is live.

The current bottleneck is **delivery**, not quality standards
(`docs/V1_AUDIT_2026-07-26.md` §6).
