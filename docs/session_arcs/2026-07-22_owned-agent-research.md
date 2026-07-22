# Session Arc — 2026-07-22 — Owned Agent research (founder question → PROPOSAL)

Greppable summary: founder asked how to build an AI agent "owned by and
working for" artists/venues/events that feeds OneLive as a side effect of
amplifying them; answered as a researched PROPOSAL
(`docs/strategy/ONE_LIVE_OWNED_AGENT_v1.md`, PR #48, docs-only). Session
Contract #20 lives HERE, not in STATE.md — the arming-evidence binding test
correctly blocked a STATE.md edit on this docs-only head (R-023 records the
fold-back trigger). One internally-caught defect, ledgered.

## Session Contract #20 (2026-07-22, research session `artist-owned-ai-agent` — founder: "How might we create an AI agent that is 'owned' by and 'works for' artists and events and venues? … Research how best to execute something like this")

STATUS: DELIVERED same session — docs-only research PROPOSAL on branch `claude/artist-owned-ai-agent-dvdn5c` (draft PR #48).
GOAL: Answer the founder's owned-agent question with researched execution options, challenges, and a consolidated question list — a PROPOSAL, not a build.
SCOPE: `docs/strategy/ONE_LIVE_OWNED_AGENT_v1.md` (precedent research: Bandsintown for Artists, Google Business Profile claim/verify, schema.org/Things-to-do, Meta API 2026 realities, MCP landscape; three-layer decomposition pipe/gift/skin; discrete function set F0–F5; phases A/B/C gated on Steps 6–7; trust-physics section confirming NO invariant changes; founder questions Q1–Q5) + TODOS queue entries + changelog row + this arc.
NON-GOALS: no code, no schema, no new services, no trust-rule changes (the doc leans entirely on the RATIFIED first-party fast lane from the 2026-07-14 sensor architecture), no preemption of Steps 6–10.
DONE-CRITERIA: doc lands as PROPOSAL with sources linked · one consolidated founder-question list (Q1–Q5) · queue entries gated so nothing builds before ratification + Step 7 · validate green · draft PR through the evaluator.

NOTE ON PLACEMENT (why this contract is not in STATE.md): the first push of
PR #48 carried this contract as a STATE.md edit; the trust-gate and
adversarial-review jobs both failed on
`tests/test_arming_smoke_binding.py::test_reviewed_head_is_runtime_code_identical_to_the_smoke_run`
— STATE.md is not in the binding's non-runtime set (`docs/`, `tests/`,
`TODOS.md`), so the recorded smoke-run evidence no longer covered the head.
The gate is working as designed and was not touched: the contract moved to
this arc (allowed surface), STATE.md was reverted to base, R-023 records the
deferral with the objective fold-back trigger, and the classification
question (does STATE.md belong in the binding's non-runtime set?) is queued
in TODOS as a gate-custody decision — never decided from inside a docs PR.

## What was produced

1. `docs/strategy/ONE_LIVE_OWNED_AGENT_v1.md` — the PROPOSAL. Core finding:
   the "owned agent" decomposes into pipe (verified first-party channels —
   already RATIFIED canon, sensor architecture 2026-07-14), gift (free
   functions F0–F4, each valuable to the business on its own), and skin
   (agent-shaped auto-discovery onboarding over watcher records, never idle
   per-entity LLMs). Precedents: Bandsintown for Artists (510k+ artists on
   free tools), Google Business Profile verification menu,
   schema.org/"Things to do" JSON-LD, Meta API 2026 friction (Phase C only),
   MCP landscape (Phase C reach).
2. TODOS.md — gated "Owned Agent" queue section (Phases A/B/C, all blocked
   on founder Q1–Q5 and Steps 6–7).
3. Changelog rows + this arc + R-023 + Kaizen ledger row for the binding
   catch.

## Trust posture

No invariant touched. The proposal states explicitly: the owned agent is a
source and owner channel, never a publisher; disputed stays
owner-unsuppressible; a no-connect-to-rank corollary is PROPOSED for
ratification (Q4), not assumed.

## Same-day follow-up (Part II addendum)

The founder extended the ask in-session with three theses; researched and
folded into the doc as Part II (§§12–17), same PR:

1. **B2A / agent-facing representation** — the owned agent as the business's
   representative to the incoming wave of consumer/org AI agents. Standards
   are forming now (llms.txt at 844k+ sites with a Chrome Lighthouse check;
   NLWeb; WebMCP). Proposed as function F6 (static profile in Phase B, live
   gated-truth endpoint in Phase C) with two binding trust notes: disputes
   served to machines as to humans; read-only surface of promoted data.
2. **The adoption-gap belief: VERIFIED** (non-adopter barrier data; GEO/AEO
   agencies already charging small businesses $1,500–$5,000/month for AI
   visibility — the exact fee wave the free agent undercuts) **with one
   nuance:** artist AI sentiment is split and loaded (displacement/copyright
   fears) → artist-facing copy leads with representation/accuracy/control,
   never "AI-powered"; sensitivity pre-registered for copy testing.
3. **Essential needs defined as E1–E7** (doc §15): F0–F4+F6 covers E1–E5+E7
   — the 80/20; E6 (social posting) is the deliberate Phase C tail. E-list
   proposed as the Phase A/B acceptance rubric ("build to that standard"
   made mechanical).
4. **Open + private positioning** (§16): open/exportable event truth vs
   walled gardens; on-device-first consumer personalization (opt-in sync),
   with the costs stated (competitors can consume the open feed; analytics
   constrained). Consumer-trust data supports it as differentiation.

Founder questions extended to Q1–Q8 (Q6 F6 ratification, Q7 the E-standard,
Q8 open+private as canon).

## Third directive (same session): B2A/GEO market assessment + toolkit options

Founder directed a full market assessment (McKinsey-style opportunity,
SWOT + Porter, Value Prop Design + Neumaier onliness, po + Six Hats,
consumer cost/margins, best-3 toolkit options at ~zero customer cost,
"no-brainer" bar). Delivered:
`docs/strategy/ONE_LIVE_B2A_GEO_MARKET_ASSESSMENT_v1.md` (PROPOSAL), same
PR. Highlights:

- **Landscape:** Profound ($1B valuation, enterprise), Peec, Scrunch,
  Otterly; agencies at $1.5k–$25k/mo; Yext-class listings incumbents at
  $200–500/yr/location; ACP/AP2 agentic-commerce rails live. Nobody serves
  local live culture; the window is ~12–18 months.
- **Demand:** 45% of consumers use AI for local recommendations (from 6%
  YoY); 83% of restaurant locations invisible in AI answers; answers name
  only 3–5 businesses.
- **CORRECTION (Kaizen M2 row, caught pre-merge):** Part II's llms.txt
  adoption/Lighthouse claim was vendor-sourced and is contradicted by
  Ahrefs' 137k-site study (97% unread) and Google's own statements —
  tempered in the same commit; the real levers are pipe consistency
  (Foursquare ~70% of ChatGPT local, Yelp, Bing Places), reviews as a
  confidence threshold, JSON-LD, and OneLive as a citable source.
- **Po battery run** (mandatory, divergent moment): seed 20260722, word
  "kite", full P1–P8.6; harvest H1–H8 in the doc §9; M6 ledger row added.
  Dead ends logged: P6 absurd ("the toolkit performs the concerts") and
  P8.5 ("every AI is always right about everyone") produced no adoptable
  candidates beyond H8's scoreboard framing.
- **Six Hats** with the single-model independence caveat stated in-doc;
  Black hat explicitly defers to the PR's non-Claude evaluator; standing
  Blue conflict preserved (Mirror hook value vs engine-TOS/cost risk),
  resolution deferred to the Phase-A friction gate with legal input.
- **Three options:** A "Mirror" (report-card hook, max no-brainer force,
  the only real COGS + a TOS/legal question), B "Feed" (verified presence
  kit = the already-gated Phases A/B, upgraded with pipe-consistency
  assists), C "Doorman" (gate-served agent endpoint + agent-traffic log +
  revocable authority; the Phase-C moat). Recommendation: one funnel —
  B first (already gated), A as B's front door (behind legal + scan cap),
  C in Phase C. Founder questions Q9–Q13 added (Q13: §14 beyond-core consultant catalog stances — added at the founder's fourth directive with the PDF delivery).

## Fifth directive (same session): the Mantle — thought leadership + execution default

Founder directed an assessment of claiming the thought-leadership AND
execution mantle: OneLive as the "default"/"no-brainer" for AI-era basics
in local culture, with "you shouldn't pay for table stakes" as the claim.
Delivered: `docs/strategy/ONE_LIVE_MANTLE_v1.md` (PROPOSAL, same PR).
Highlights: the mantle is structurally unclaimed (every incumbent is
barred from the claim by its own business model); category-design
economics justify taking it (creators captured 51% of growth/80% of
market cap among fast growers); precedents mapped — Let's Encrypt
(execution mantle: free HTTPS default, 700M+ sites) and HubSpot
(thought-leadership mantle: named "inbound", gave away the academy).
Seven mantle assets (Standard/Manifesto/Report/Roadshow/Curriculum/
Vocabulary/Scoreboard), all ~zero cash, founder-time-funded. Sequencing
LAW (Black hat): never claim execution mantle ahead of execution —
narrative prep now, publish WITH Phase A, the word "default" only when
coverage metrics earn it. Po battery run #3 (seed 2026072202, word
"telescope", harvest H-M1–M6, M6 ledger row; dead ends: P6 absurd "the
manifesto signs itself" and P8.3 "10000× reports" yielded nothing beyond
M-C's cadence). Questions now Q1–Q17. The Report/Mirror legal conflict
preserved in Blue, deferred to the Phase-A friction gate.

## Sixth directive (same session): Alternative S — the standalone B2A model

Founder directed a draft of the alternative where OneLive's pipes are not
in the picture (why is B2A good absent OneLive; the substrate thesis:
widespread agents facilitate our data gathering), with standalone SWOT +
deep competitive analysis, then that SWOT evaluated back to OneLive.
Delivered: `docs/strategy/ONE_LIVE_B2A_STANDALONE_v1.md` (PROPOSAL, same
PR). Key findings: S's value absent OneLive is real (all output on owner
property — markup, feeds, pipe consistency, own-domain doorman; lock-in
impossible by construction); the substrate thesis works mechanically AND
the ratified sensor canon's verified-external-channel rule means domain
provenance alone reaches the first-party fast lane, no claim needed. But
the standalone frame changes the competitor set to actors with total
distribution (site builders shipping natively: Squarespace AIO Scanner,
Wix AI Visibility Overview, Shopify agentic storefronts; the
Cloudflare-tolled read path), adds the spam-capture threat (an ungated
consistency tool is also a spam cannon), and — evaluated back to OneLive
if truly separate — funds a commons our better-distributed competitors
harvest while the claim flywheel, trust machinery, and mantle all
transfer away. Synthesis: S as ARCHITECTURE yes (Q18: "delete OneLive
and they keep everything" as a Phase-A acceptance test), S as separate
venture no (Q19, revisitable at scale signals), the Standard alone goes
standalone via site-builder adoption (Q20). Questions now Q1–Q20.

## Open threads carried forward

- Founder Q1–Q20 across the four strategy docs — nothing in the Owned Agent section of TODOS is
  buildable until answered.
- R-023 — fold Contract #20 into STATE.md when the trigger fires.
- Gate-custody decision queued: STATE.md classification in the arming
  binding's non-runtime set (evaluator-mandatory; any widening is a
  gate-relaxation question → founder-crucial).
