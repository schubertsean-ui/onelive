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

## Seventh directive (2026-08-01): the Promotion Studio

Founder directed an additional-service concept: actual promotion
execution — ad/content creation, design, posting, carousels, measurement
— explicitly NOT on OneLive, via the business's own social channels
("wine tasting coming up → spin up ads and a carousel for them to run in
FB and IG"). Delivered: `docs/strategy/ONE_LIVE_PROMOTION_STUDIO_v1.md`
(PROPOSAL, same PR): proactive event-triggered campaign kits (the F1
spine means the agent already knows the event — the kit shows up before
they ask), the agency arbitrage table (the $1k–$5k/mo retainer's
event-promotion core is templated work over data we hold; genuinely-hard
work named and left to the REFER world), hard guardrails (their
channels/ad accounts/budgets, owner tap = send button always, no spend
percentage, artist framing rules, consumer data never feeds targeting,
and the Studio corollary: nothing ever affects any OneLive surface),
v1 with NO Meta API (2-tap boost recipe in their own app; authorized
execution is Phase C behind Meta review), COGS ~cents/kit, three pricing
postures presented (capped-free / low flat fee / defer — recommendation:
defer formally, build switchable). Records the F5/§14.2 posture
amendment honestly. Also this directive-pair produced the partner-facing
pitch drafts in-conversation (venue + artist voices, then extended with
the Studio section). Questions now Q1–Q22.

## Eighth directive-set (2026-08-01): segmentation research → CANON

Founder directed (in sequence): the marketing-operating-reality analysis
by size (with segment validation and tactic-level spend folded in), the
category-specific research paper for outreach conversations (originally
22 categories, split to 23 — bars separated from
breweries/wineries/distilleries, whose three-sided revenue model
[visit · product · experience/education] was added at founder note), and
finally RATIFICATION: "let's add to the canon the 23 segments and add
this content." Landed: decision record
`docs/memory/decisions/2026-08-01_supply-segments-canon.md`; canon doc
`docs/strategy/ONE_LIVE_SUPPLY_SEGMENTS_v1.md` (23 categories × 5 size
tiers — SOLO/SMALL/MEDIUM/LARGE/JUMBO per OECD bands + Census
nonemployer split); research companions
`ONE_LIVE_MARKETING_OPERATING_REALITY_v1.md` (sourced tier analysis;
figures in docs/strategy/assets/) and
`ONE_LIVE_CATEGORY_RESEARCH_23_v1.md` (23 briefs: challenges, growth
desires, validation questions, recommendations by size, outreach
angles). Canon/research boundary stated explicitly in all three docs:
the SEGMENTATION is canon; the briefs are conversation-validated
hypotheses. PDF editions (segment analysis v2, category research v2)
delivered in-conversation.

## Ninth directive-set (2026-08-01): the agent visuals arc + the comms framework enters canon

A rapid iterative arc produced the "Marketing Research & AI Agent" visual
package (v1→v5, delivered as PDFs in-conversation; all diagrams
regenerable from scratchpad scripts): process swimlanes with time/cost
ledgers per use case (bar/nightclub, winery/brewery/distillery, solo
artist), owner-facing phone-thread panels, the content factory (from the
first paste: four learned inputs — calendar, photos, voice, brand),
the demand-engine fan-out with explicit social formats, high-level flow
strips for both sides, a first-door glance pair, and the full OneLive
engine model (two ingestion paths, the trust machine, distribution, the
adoption loop). Framing corrections applied at founder direction:
maintenance (Tier 1) kept distinct from demand generation (Tier 2);
minder framing demoted to one-time floor; spiel removed. RATIFIED at
close: the five-part communication framework — WHAT · HOW · WHY · WHY
THAT WHY MATTERS · EXPECTED OUTCOMES — is canon for research and
explanatory materials, modifiable only on founder instruction
(docs/memory/decisions/2026-08-01_comms-framework-canon.md; CLAUDE.md
pointer amendment queued in TODOS — CLAUDE.md sits outside the arming
binding's non-runtime set).

## Tenth directive (2026-08-01): Tier-2 monetization direction

Founder scoped the pricing posture: Tier 1 basics free permanently (the
Mantle promise unchanged); Tier-2 ongoing demand generation free for an
initial period, then MAY be priced (flat monthly or percentage-based)
below documented market alternatives — grounded in the research (83%
don't do this work; buying it costs $300–$5,000/mo). Physics unchanged:
nothing paid or free affects OneLive ranking; owner tap = send button.
Recorded: decision record 2026-08-01_tier2-monetization-direction.md;
Studio doc §5-A amendment; Tier-2 pricing decision packet queued in
TODOS (model, %-base, rate, free-period length, grandfathering — founder
decides with Phase-B data). Deliverable PDFs carry the scoped constraint
from v6.

## Open threads carried forward

- Founder Q1–Q22 across the five strategy docs — nothing in the Owned Agent section of TODOS is
  buildable until answered.
- R-023 — fold Contract #20 into STATE.md when the trigger fires.
- Gate-custody decision queued: STATE.md classification in the arming
  binding's non-runtime set (evaluator-mandatory; any widening is a
  gate-relaxation question → founder-crucial).


## Directive set 11 (2026-08-01, later): proof, engagement canon, Model v1, surfaces, MERGE

Founder directives, in order: prove the agent on a real crawl → case study on
The Continental Club from real public data (search-index snapshots; R-063, renumbered from a duplicate R-025 id) —
extraction with 4-state confidence, a REAL drift catch (Do512 "Friday" on the
Sat Aug 1 Peterson Brothers show), engagement-canon campaign kit (video-first
carousel on brief v2.4 §3/§6, their footage/audio via IG Collab; same spine on
every channel), machine layer incl. GEO deploys. Then: fonts/layout escalations
(deliverable-visual-QA class, Kaizen-ledgered), integration into **Marketing
Research & AI Agent Model v1** (v9 + proof section + typed surfaces appendix),
GEO + wider SEO surfaces added to the appendix AND swept through every example
(fanout, factory, storyboards, threads, model chart rebuilt clean, case-study
artifacts). Session close: "update the repo and canon as appropriate" →
**PR #48 checked: all seats APPROVE + all checks green on a6966b3 → MERGED
(42b8b80) under the standing merge-on-green directive; founder notified.**
Canon landing on the restarted branch: AGENT_SURFACES_v1, CASE_STUDY v1,
marketing_model/ sources, R-063 (né R-025), Kaizen rows, Addendum 11, TODOS updates.


## Directive set 12 (2026-08-01): external review adopted — "Go with 1–4"

Founder commissioned an external review of Model v1 (PDF-only context) and
directed items 1–4: artifact fixes (InStock removed, PostalAddress, crawler
naming, check_artifacts.py regression), claim ledger + evidence badges
(Model v2 reissued badged; ILLUSTRATIVE stamps on all fictional examples,
DEMONSTRATED on the Continental artifacts), connector capability registry
(supersedes flat SYNC/STAGE; Songkick HELD for legal), and the 12-page
Customer Story v1 on the review's canonical six-step sequence. Reviewer's
disputed-display weakening REJECTED (charter invariant); their 11pm JSON-LD
contradiction claim disproven (artifact reads 21:30). Founder-crucial holds
queued in TODOS. Kaizen: ESCAPED-to-external-review row.

## Directive set 13 (2026-08-01): the three ratifications + evaluator round 1

Founder: "Confirm you're addressing 1-8" (the assessment's Real-catches list)
plus three explicit adoptions — truth-state additions (OWNER-CONFIRMED,
STALE), the invariants-vs-testable-hypotheses split, and the automated
cross-artifact consistency test as standing canon. Landed: Truth States v2
(six states + flags + evidence dependency graph + outcome classes; R-064
holds the pipeline implementation for a code-armed session),
ONE_LIVE_ENGAGEMENT_HYPOTHESES_v1.md (8 invariants, 10 hypotheses,
rotation rule), tests/test_artifact_consistency.py (checker now runs in
validate's pytest sweep). Same push answers PR #142 r1's REQUEST-CHANGES —
every finding real: dead check branch (false-confidence-gate, again),
83% caption outran C-01, Customer Story channel table outran the registry
(new class copy-outruns-registry, mechanically guarded), duplicate R-025
→ R-063, 22→23 label. Catches 1–3, 5–8 of the founder's "1–8" are now
executed; catch 4 (Songkick) remains the legal-review hold, with catch 8's
standing-authorization half also still held (interim: everything outbound
needs the tap).

## Directive set 14 (2026-08-02): reader's guides, Songkick hold, auth boundary, pricing question

Founder issued six directives (verbatim in the 2026-08-02 decision record):
plain-language front guides + per-page descriptions in both deliverables
(now a standing deliverable requirement); Songkick ON HOLD but RETAINED
(registry + inventory rows updated, legal-review reopen trigger); the
standing-authorization boundary explained in a new PROPOSAL doc
(ONE_LIVE_STANDING_AUTHORIZATION_v1.md — two-tier split awaiting
ratification, interim all-taps rule intact); pricing narrowed to one open
input (the %-of-ad-spend ruling); everything committed on the PR #143
branch. Pagination QA caught two orphan-page splits from the added
description lines (width-bound images ignore max-height) — fixed by
width-based sizing, verified page-by-page: Customer Story 13 pp, Model 26 pp.

## Directive set 15 (2026-08-02): the 1Live rebrand

Founder: "Change all 'OneLive' to '1Live' / Everywhere, in these last 2
documents and in the repo and in the canon." Executed to the edge of the
docs-arm boundary: 335 mentions across 80 living files, all figures
re-rendered, both PDFs rebuilt with zero-residual assertions, customer
deliverable renamed. Preserved: history/verbatim (facts of the OneLive
era), identifiers, filenames. R-065 records the code-armed remainder
(web BrandMark + runtime strings, CLAUDE.md, STATE.md, founder-owned
infra names) with a before-any-deploy trigger.
