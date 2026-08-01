# ONE LIVE — B2A / GEO-AEO Market Assessment & Toolkit Options v1

**Compiled 2026-07-22 · Status: PROPOSAL — research response to the founder's third 2026-07-22 directive (leading B2A/GEO actors and practices; McKinsey-style market assessment; SWOT + Porter; Value Prop Design + Neumaier onliness; de Bono po + Six Hats; consumer cost/margins; best 3 toolkit options for an unrivaled, ~zero-customer-cost B2A product that makes the customer say "this is a no-brainer"). Companion to `ONE_LIVE_OWNED_AGENT_v1.md` (Parts I–II). Nothing here is license to build.**

Greppable summary: GEO/AEO is a $1–1.5B market growing 34–50% CAGR toward
$7–20B, priced for enterprises ($29–$50k/mo tools, $1.5k–$25k/mo agencies)
while 45% of consumers now ask AI where to go and 83% of local venues are
INVISIBLE in those answers — a served-enterprise/unserved-local gap that is
OneLive's opening. Key correction logged: llms.txt is largely UNREAD by AI
systems (Ahrefs 137k-site study: 97% zero reads; Google: "no AI system
currently uses llms.txt") — real B2A leverage is entity consistency across
the pipes agents actually read (Foursquare ~70% of ChatGPT local results,
Yelp, Bing Places, reviews ≥~4.3★ confidence threshold), plus becoming a
citable verified source. Three toolkit options assessed (Mirror / Feed /
Doorman); recommendation: they compose as one funnel — A (Mirror: "how AI
sees you" report card) as the no-brainer hook on top of B (Feed: verified
presence kit, already Phases A/B) with C (Doorman: live agent endpoint) as
the Phase-C moat. Method note and single-model caveat in §1. Founder
questions Q9–Q13 at the end (Q13 covers §14's beyond-core consultant
catalog: what paid B2A consultants deliver beyond our free core, with a
NEVER/REFER/LATER/EDGE stance on each).

---

## 1. Method note (read first)

Frameworks used at the founder's direction: McKinsey-style opportunity
assessment (§4), Porter Five Forces (§5), SWOT (§6), Osterwalder Value
Proposition Design (§7), Neumaier onliness/zag (§8), de Bono po battery +
Six Hats (§9–§10), unit economics (§11), option scoring (§12).

**Independence caveat, stated plainly:** the Six Hats and po sections below
were authored by one model (this session) playing the hats sequentially —
NOT the charter's independent-parallel-lens structure, which requires
lenses that never see each other's output and at least one non-Claude
attacker. Per the hats registry, the TRUE Black hat on this work is the
non-Claude adversarial evaluator that reviews this PR, and the Red hat is
the founder. Treat §9–§10 as structured single-author thinking; the
mandatory independent attack happens at review. If the founder wants the
full multi-model Friction structure on the chosen option before build, that
fires at the Phase-A friction gate as already queued.

**Correction to Part II (Kaizen, caught pre-merge):** Part II §13 cited a
vendor claim that llms.txt adoption (844k sites, a Chrome Lighthouse check)
made it a formal web-quality signal. Deeper research for THIS assessment
found the counter-evidence decisive: [Ahrefs' 137,000-site study found 97%
of llms.txt files got zero AI-bot reads](https://ahrefs.com/blog/llmstxt-study/),
[Google's John Mueller states "no AI system currently uses llms.txt"](https://www.seroundtable.com/google-ai-llms-txt-39607.html)
and [Google's generative-AI guidance says machine-readable files like
llms.txt aren't needed](https://www.searchenginejournal.com/google-says-llms-txt-is-purely-speculative-for-now/577576/).
Part II's §13 has been tempered in the same commit; F6's static half is
downgraded to a zero-cost hedge, never a promise. The correction is
ledgered (docs/metrics/KAIZEN_LEDGER.md). What replaces it as the real
lever is §3.4 below — and it is BETTER news for OneLive, not worse.

## 2. The demand shift (why this window is real)

1. [45% of consumers now use AI tools for local business recommendations —
   up from 6% one year earlier; AI is already the #3 local-discovery
   channel behind Google and Facebook, past Yelp and
   TripAdvisor](https://bloomintelligence.com/blog/ai-restaurant-discovery/).
   Adoption peaks at 64% among ages 30–44 — squarely OneLive's
   going-out demographic.
2. [83% of restaurant locations are entirely invisible in AI-generated
   recommendations](https://www.businesswire.com/news/home/20260507962493/en/83-of-Restaurants-Are-Invisible-in-AI-Search-New-Uberall-Report-Reveals-the-Discovery-Gap-Reshaping-the-Quick-Service-Restaurant-Industry)
   (Uberall, May 2026). Music venues, galleries, and independent artists
   are certainly worse — nobody is even auditing them.
3. [AI assistants name only 3–5 businesses per answer and
   stop](https://www.localfalcon.com/blog/the-ai-visibility-crisis-why-83-percent-of-restaurants-dont-exist-in-chatgpt);
   [79% of AI local prompts are conversational research questions
   ("best patio for a group of eight")](https://bloomintelligence.com/blog/ai-restaurant-discovery/)
   — the exact "what's on tonight that feels like X" queries OneLive's
   Emotion/Vibe layer is designed for.
4. Macro: [Google's search share ~91%→~78% since 2024; zero-click results
   56%→69% after AI Overviews](https://www.omnibound.ai/blog/generative-engine-optimization-statistics).
   Discovery is consolidating into a few answer slots, and the slots are
   filled from structured, verified, review-corroborated data.

**The strategic read:** the market's pain is no longer "get me ranked on
Google" — it is "AI is answering questions about me, wrongly or not at
all, and I can't see it or fix it." That pain is brand-new, measurable,
demonstrable in 60 seconds, and currently priced at enterprise rates.

## 3. World-leading actors and practices (the landscape)

### 3.1 AI-visibility / GEO platforms (the tool layer)
- **[Profound](https://www.surmado.com/blog/best-ai-visibility-tools-2026)** —
  category leader: $96M Series C at a $1B valuation (Feb 2026), 700+
  enterprise customers; answer-share-of-voice tracking, Conversation
  Explorer, multi-country enterprise reporting.
- **[Peec AI](https://www.surmado.com/blog/best-ai-visibility-tools-2026)** —
  $29M raised, $4M+ ARR within ten months — evidence of violent demand
  growth in the category.
- **[Scrunch AI](https://ayzeo.com/comparisons/geo-platforms-compared)** —
  "Agent Experience Platform" positioning (closest in language to B2A):
  audits how AI agents experience a site, enterprise/SOC-2 posture.
- **[Otterly.ai](https://www.surmado.com/blog/best-ai-visibility-tools-2026)** —
  the affordability floor of the monitoring category: from ~$29/month.
- Incumbent SEO suites (Semrush, Ahrefs, BrightEdge, Conductor) bolting AI
  tracking onto existing subscriptions; [10+ platforms compared
  here](https://www.searchinfluence.com/blog/ai-seo-tracking-tools-2026-analysis-platforms/).
- **Practice pattern:** all of these MEASURE visibility and advise; almost
  none can FIX the underlying data, because they don't own a trusted
  source or a consumer surface. They sell mirrors, not plumbing.

### 3.2 GEO/AEO services (the agency layer)
[$1,500–$5,000/mo small-business retainers; $3,000–$25,000/mo typical
engagements; to $50k+/mo enterprise](https://www.webfx.com/blog/ai/generative-engine-optimization-cost/)
([pricing guide 2](https://thedigitalelevator.com/blog/aeo-and-geo-pricing-guide/)).
This is the fee wave Part II already identified. The services sold:
entity/schema cleanup, listings consistency, review strategy, content
restructuring for conversational queries, citation building, monitoring.

### 3.3 Local-listings incumbents (the adjacent throne)
- **Yext** — [$199–$499+/year per location](https://www.socialpilot.co/reviews/comparison/brightlocal-vs-yext);
  the "sync your data everywhere" model, now marketing AI-visibility
  features. **The closest structural analog to F1/F2 — at a price.**
- **BrightLocal** (~$39+/mo), **Synup**, **Uberall**, **Birdeye** (now
  branding as an "agentic marketing platform" for multi-location brands).
- **Practice pattern:** per-location subscription pricing, aimed at
  multi-location brands and agencies. None has a consumer surface; none
  verifies; none is free; none cares about a 120-cap music venue.

### 3.4 What ACTUALLY feeds AI local answers (the practices that work)
This is the section that replaces the llms.txt myth with mechanics:
- [ChatGPT local results pull ~70% from Foursquare's Places API, plus
  Yelp (formal integration), Bing Places, and the Bing
  index](https://www.localfalcon.com/blog/chatgpt-local-search-data-sources-where-does-business-info-come-from)
  ([Search Engine Land corroborates](https://searchengineland.com/how-does-chatgpt-conduct-local-searches-454894));
  ChatGPT has NO direct Google Business Profile access.
- [Perplexity has a formal Yelp API partnership and rewards presence
  across diverse directories](https://www.soci.ai/blog/how-to-rank-in-chatgpt-perplexity-and-google-ai-overview/).
- [Reviews act as a CONFIDENCE THRESHOLD, not a ranking gradient:
  AI-recommended locations average ~4.3★; below ~3.4★ with <5% response
  rate is effectively invisible](https://local-ai-audit.com/blog/how-chatgpt-finds-local-businesses/).
- NAP (name/address/phone) consistency across Google, Apple Maps, Yelp,
  Bing, Facebook is the baseline hygiene AI engines cross-check.
- Schema.org/JSON-LD event markup remains the one machine-readable format
  with actual consumption (Google "Things to do", event surfaces) — F3
  stands unaffected by the llms.txt correction.
- **World-leading practice, distilled:** (1) be present and IDENTICAL in
  the 5–6 databases agents actually read; (2) clear the review-confidence
  bar; (3) serve real structured data on your own site; (4) publish
  content shaped like conversational answers; (5) monitor the answers and
  correct drift. Enterprise tools charge monthly for #5 and consult on
  #1–#4. OneLive can DO #1–#4 and give #5 away.

### 3.5 The rails being laid (where this goes next)
[OpenAI+Stripe's Agentic Commerce Protocol is processing live transactions
(Etsy; rolling to 1M+ Shopify merchants, Walmart)](https://stripe.com/newsroom/news/stripe-openai-instant-checkout);
[Google's AP2 went to the FIDO Alliance in April 2026; the likely outcome
is composed standards — discovery (UCP-style) + authorization (AP2) +
per-surface execution](https://www.digitalapplied.com/blog/agentic-commerce-standards-ucp-acp-ap2-2026-merchant-guide).
Translation for live events: within 1–2 years, consumer agents will
routinely DISCOVER events, CHECK details, and hand off to TICKETING. The
entity that agents trust for the discover/check steps owns the top of that
funnel. That is the seat OneLive's gate is built to occupy.

## 4. Market opportunity (McKinsey-style)

**Market size (the paid market we DON'T charge into, but arbitrage):**
[GEO services ~$0.9–1.5B in 2024–26, forecast $7.3B by 2031 (34% CAGR) to
$17–20B by 2034 (40–50% CAGR depending on
firm)](https://finance.yahoo.com/news/generative-engine-optimization-geo-services-151200019.html)
([alt forecasts](https://dimensionmarketresearch.com/report/generative-engine-optimization-geo-market/));
[67% of Fortune 500 CMOs name GEO a top-3 priority for FY2026, up from 18%
in 2024](https://www.omnibound.ai/blog/generative-engine-optimization-statistics).
Adjacent listings-management market (Yext et al.): mature, per-location
subscription, $200–$500/location/year list pricing.

**TAM/SAM/SOM for the OWNED-AGENT wedge (supply-side entities, US —
illustrative, assumption-explicit):**
- TAM: US live-culture supply — order 100k+ venues/stages/organizers
  (bars/clubs with live programming, theaters, galleries, festivals) plus
  several hundred thousand actively-gigging artists. At the $200–$500/yr
  listings price analog, that is a $60–250M/yr equivalent value pool for
  presence services alone — before AI-visibility premiums that currently
  price 10× that.
- SAM: metros where OneLive operates; entities with any digital presence
  (calendar, page, or social) — the auto-discoverable set. Austin alone:
  our source catalog already carries 266 sources at Step-5 scale;
  full-metro coverage is plausibly 1.5–3k entities.
- SOM (12–18 months, Austin): the claimed-entity target is a COVERAGE
  metric, not revenue — e.g., 30–50% of active venues claimed via the
  magic-link pre-seed motion (§ONE_LIVE_OWNED_AGENT_v1 F0), which no
  incumbent can replicate because none holds a pre-verified event graph
  to seed claims from.
- **Value capture, honestly:** we charge $0. The "market opportunity" is
  arbitrage: incumbents monetize the pain directly; we convert the same
  pain into (a) supply acquisition at near-zero CAC, (b) data accuracy no
  scraper can match, (c) the consumer moat (§ONE_LIVE_OWNED_AGENT_v1
  §16.3), and (d) OPTIONAL future non-rank revenue (ticketing handoff
  fees, ACP-era transaction rails — Phase 3+, founder-gated, never
  ranking). The B2A toolkit is a CAC weapon dressed as a product — and it
  must genuinely be a great product or the dress falls off.

**Where to play / how to win (the McKinsey one-liner):** play in the
unserved local-live-culture segment of a market priced for enterprises;
win by owning the only free, verified, consumer-connected data path — the
plumbing every mirror-vendor lacks.

**What would falsify this opportunity (pre-registered):** (a) AI platforms
launch free first-party business consoles that close the gap themselves
(Threat T1, §6); (b) consumer AI-for-local adoption stalls below ~20%;
(c) claimed-entity conversion in Austin under ~10% after the Mirror hook
ships — if the report card doesn't convert, the no-brainer thesis is wrong.

## 5. Porter Five Forces (the free-B2A-for-live-culture niche)

| Force | Rating | Analysis |
|---|---|---|
| Threat of new entrants | **HIGH** | Tooling is cheap; any GEO startup can pivot down-market. BUT: our moat isn't the tool, it's the verified event graph + consumer surface + $0 price no VC-funded tool can sustainably match. Entry into "free forever" requires our cost structure and a reason to exist without SaaS revenue. |
| Supplier power | **MEDIUM-HIGH** | The "suppliers" of AI visibility are the answer engines and their data pipes (Foursquare, Yelp, Bing). They can change access/pricing at will (Meta precedent). Mitigation: multi-pipe syndication, our own citable surface, and first-party data the pipes ultimately want. |
| Buyer power | **LOW** (by design) | Venues/artists individually have no leverage — but at $0 they don't need any. Churn risk is apathy, not negotiation. The real "buyer" test is attention: the toolkit must pay for its five minutes of setup instantly. |
| Substitutes | **MEDIUM** | DIY (claim your own Bing/Yelp/Foursquare — free but unknown and tedious); agencies ($1.5k+/mo); Yext-class tools ($200–500/yr/loc); doing nothing (the 83%). Our position: we ARE the productized version of DIY-done-right, free. |
| Rivalry | **LOW today, HIGH in 24mo** | Nobody serves this segment now. As GEO consolidates (Profound at $1B), down-market moves are inevitable — Birdeye/Yext already market "agentic." The window is the next 12–18 months, which matches our Steps 6–10 → Phase A/B timeline. |

## 6. SWOT

**Strengths:** the gate (verified truth is exactly what answer engines need
and cannot make themselves); pre-seeded claims from an existing event
graph; two-sided flywheel (consumer surface makes the business tool
valuable and vice versa); $0 economics via deterministic-first pipeline;
trust invariants as brand (no pay-to-rank is provable, not asserted).

**Weaknesses:** pre-launch — no consumer traffic yet, so "we help you get
found" initially means found via pipes + OneLive, not via a large OneLive
audience; single-metro; tiny team (agent+founder) — support load is the
scaling constraint; no direct control over third-party pipes; the
"AI" word itself is radioactive with a big artist cohort (Part II §14).

**Opportunities:** the 83%-invisible gap with a 60-second demo; the fee
wave making "free" newsworthy; standards flux (early citable sources get
grandfathered into agent habits); ACP-era ticketing handoff as future
non-rank revenue; the E1–E7 standard as a category definition we author.

**Threats:** T1 — platforms self-serve the gap (OpenAI/Google business
consoles for local); T2 — pipe access tightens (Foursquare/Yelp monetize
harder); T3 — a funded GEO player goes freemium down-market; T4 — AI
assistants strike exclusive local-data deals (e.g., ticketing giants),
bypassing independents entirely — which would make OneLive's independent
verified graph MORE valuable to the losing assistants, our hedge; T5 —
reputational: one bad auto-sync that misstates a business hurts the whole
trust story (mitigation: the gate + dispute mechanics, already physics).

## 7. Value Proposition Design (Osterwalder)

**Segment: venue owner/manager (primary).**
- Jobs: fill the room tonight; publish once; look professional; not fall
  behind technology they don't understand.
- Pains: invisible in AI answers (and unaware of it); inconsistent
  listings everywhere; no time; fear of being ripped off by "AI
  consultants"; can't evaluate what's true.
- Gains: more walk-ins attributable to nothing they did; one dashboard-
  free habit ("it just stays right"); proof ("here's how you appear now").
- Pain relievers: Mirror report card (see the problem in 60s); one-click
  fix-all (F0–F3 + pipe syndication); silence/accuracy alerts (F4).
- Gain creators: before/after AI answers; monthly "how you appeared"
  digest in plain language; free forever, in writing.

**Segment: independent artist.**
- Jobs: get gigs; grow fans; protect how they're presented.
- Pains: mislabeled/hallucinated info about them in AI answers; zero
  budget; hostility to "AI" replacing creativity.
- Gains: accurate presence everywhere with zero effort; control.
- Distinct framing (Part II §14): representation and control, never
  generation. The agent DEFENDS them against AI slop; it doesn't make art.

**Segment: organizer/promoter.** Jobs: sell the run, not the venue;
multi-venue series coherence. Pains/gains: same shape, multiplied across
venues — served by the same functions once entity model supports series
(watcher records already do).

**Fit statement:** the pains are urgent (demand shift is measured),
demonstrable (the Mirror shows them), and unaffordable to fix at market
prices ($1.5k/mo against a venue's margins) — free + instant + verified is
structural fit, not marketing.

## 8. Neumaier tools (onliness, zag)

**Onliness statement:** *OneLive's Owned Agent is the ONLY (what) free
representative that makes live-culture businesses visible and accurate to
AI agents and answer engines (how) by feeding gate-verified truth to the
pipes AI actually reads — and to OneLive's own consumer surface (who) for
venues, artists, and organizers (where) starting metro-by-metro from
Austin (why) because 45% of consumers now ask AI where to go and 83% of
local culture is invisible or wrong in the answers (when) at the exact
moment agencies start charging $2,000/month for a worse version.*

**The zag** (when they zig...): the entire industry sells VISIBILITY
ANALYTICS to marketers. We give the ANSWER-SIDE FIX to the businesses
themselves, free, and monetize nothing about it. Competitors literally
cannot follow without destroying their revenue model — the classic zag.

**Brand-ladder rung:** trust through mechanics ("we couldn't lie about
your events if we wanted to — here's the gate") — consistent with the
consumer-side trust display rules; one brand story on both sides.

## 9. Po battery (charter-mandated at divergent moments; seed 20260722, random word "kite"; full run per docs/skills/po_provocation.md — provocations are stimuli, never facts)

Target statement: "OneLive gives every venue and artist a free B2A toolkit
that represents them to AI agents and answer engines." Assumptions listed,
all operators run standalone + random-combos; the HARVEST (each traceable,
≥2 movement techniques applied; dead ends logged in the arc):

| # | Provocation (operator) | Harvested candidate |
|---|---|---|
| H1 | P2 reversal: "AI agents represent themselves TO the venue" | **Agent-traffic log**: show the business which AIs asked about them this week and what they were told — turns invisible demand into a visceral, retainable artifact (feeds Option C; also the single best re-engagement email we could send). |
| H2 | P7 "kite"/tether: the venue holds the string | **Revocable authority token**: every agent-facing representation carries an owner-revocable grant; "unclaim" instantly degrades data to scraped-provenance state. Makes "they control the content" mechanical, auditable, and marketable ("you hold the string"). |
| H3 | P7 "kite"/fighting kites | **The adversarial demo AS the product**: the Mirror's report card leads with the WRONG answers AI currently gives about them (wrong hours, missed events, "no information found"). The 83% stat says most demos will land a hit. This is the no-brainer moment made concrete. |
| H4 | P3 exaggeration-down: 1/10000th toolkit = one byte | **The one-field product bar**: if the entire onboarding cannot be reached from "paste one URL," the design has failed (already §9 of the v1 doc; now a hard acceptance criterion for whichever option builds first). |
| H5 | P7 "kite"/tail stabilizes | **Provenance tail on every agent-served fact**: the Doorman endpoint answers with fact + confidence state + freshness + source — the trust display rules, machine-formatted. Differentiator no GEO tool can copy (they have no gate). |
| H6 | P1 escape: "free" is false | **Cost-honesty ledger**: publish the per-entity serving cost internally (§11) with a budget cap BEFORE launch; "free forever" survives only if marginal cost stays ~pennies — a standing FinOps gate, not a hope. |
| H7 | P4 distortion: the pipes read US first | **Source-of-record inversion**: instead of only pushing to Foursquare/Bing/Yelp, make OneLive's open verified feed attractive enough that pipes and engines pull FROM us (the §3.5 seat). Sequenced: push first (their habit), pull as we earn citations. |
| H8 | P5 wishful: every answer engine always right about everyone | **Public accuracy scoreboard** (per metro): "X% of Austin venues are now accurately represented in AI answers." Mission-framed PR asset; also the coverage metric SOM tracks (§4). |

## 10. Six Hats pass (single-author caveat in §1; Black defers to the PR evaluator; Red is the founder's)

- **White (facts):** §§2–4 above; all load-bearing numbers sourced; the
  llms.txt correction is White-hat work overturning a prior claim.
- **Yellow (validated upside, per docs/hats/yellow.md):** best case — the
  Mirror converts at Bandsintown-like rates because the demo is a live
  wound; each claimed entity improves gate corroboration density, which
  improves consumer trust, which makes the next claim easier: a compounding
  loop with $0 paid CAC. Validation criteria (fill at ship, append-only):
  claim conversion ≥25% of Mirror runs; measurable answer-accuracy lift in
  re-scans within 60 days; ≥1 unsolicited press/word-of-mouth citation of
  the scoreboard (H8).
- **Black (attack, to be superseded by the independent evaluator):**
  scan costs can silently scale with adoption (H6 cap is mandatory, not
  optional); third-party TOS on programmatic querying of AI engines needs
  legal reading BEFORE the Mirror ships (flagged founder-crucial with
  legal posture); "free forever" is a promise we can never walk back —
  Q4's public-promise decision becomes LOAD-BEARING for this whole
  strategy; the 83%/45% stats are vendor-adjacent research (Uberall sells
  listings; Bloom sells restaurant marketing) — directionally corroborated
  across independent sources but treat magnitudes with a haircut.
- **Green:** the §9 harvest, especially H1/H3/H7.
- **Red (founder's seat — questions, not answers):** does "you hold the
  string" feel like the brand? Does leading with others' failures (wrong
  AI answers) fit the voice, or should the Mirror lead with the fix?
- **Blue (merge, conflict preserved):** the plan below (§12–§13). Standing
  conflict NOT averaged away: Black says the Mirror's engine-querying is
  the legally/costly-riskiest component; the market section says it is the
  single best hook. Resolution deferred to the friction gate with legal
  input — the Feed (Option B) does not depend on it and builds first
  regardless (it is already Phases A/B).

## 11. Consumer cost and our margins (unit economics, pre-cap)

**Customer cost: $0** for everything in Options A/B and the read layer of
C — ratified as Q4's public promise if adopted. No setup fee, no tier that
gates accuracy, nothing that could read as pay-to-rank.

**Our marginal cost per claimed entity (order-of-magnitude, to be measured
against the M7-style meter before launch — H6):**

| Component | Mechanism | Est. cost |
|---|---|---|
| Claim + discovery (once) | fetch + parse + 1 extraction pass | ~$0.01–0.05 |
| Calendar/page sync | deterministic ICS/JSON-LD parse; LLM only on unstructured change | ~$0.00–0.03/entity/mo |
| Widget + JSON-LD serving | cached static reads (CDN) | ~$0.00 |
| Pipe syndication (Bing/Foursquare/Yelp assists) | API calls / guided flows | ~$0.00–0.02/mo |
| **Mirror scan** (the costly one) | N engines × ~10 prompts × ~1–2k tokens, monthly, batched | **~$0.05–0.50/entity/mo** |
| Digest/alerts | template from existing pipeline state | ~$0.00 |

Read: everything except the Mirror rounds to zero at the cheapest-capable
tier (cost-discipline rule 1). The Mirror is the only component with real
COGS — it needs a per-metro monthly budget cap and scan-cadence rules
(e.g., monthly for claimed entities, one-shot for prospects) set BEFORE
launch, same discipline as ingestion caps. At 1,000 claimed Austin
entities: worst case ~$500/mo, typical ~$100/mo — an acquisition budget a
paid channel could never touch. "Margins": no revenue by design at this
layer; the return is supply coverage, data accuracy, and consumer moat
(§4 value capture), with ACP-era transaction rails as the founder-gated
future revenue that never touches ranking.

## 12. The three toolkit options (3 distinct kits, composable)

### Option A — "The Mirror" (audit-first: see yourself as AI sees you)
Paste one URL → 60-second report card: how ChatGPT/Gemini/Perplexity
answer about you today (wrong hours, missed events, absent entirely — H3),
an accuracy score, and ONE button: "fix it — free." The fix enrolls them
in F0–F3 + pipe-consistency assists; monthly re-scan shows the line going
up. UX: one field, one score, one button; report shareable (venues will
screenshot their F grade — viral by indignation).
**Cost to us:** the only real-COGS option (§11), capped. **Risk:** engine
TOS/legal on programmatic querying (Black hat) — needs legal read.
**No-brainer force: MAXIMUM** — it demonstrates the pain in their own name
before asking anything.

### Option B — "The Feed" (source-of-truth-first: publish once, correct everywhere)
The v1 doc's F0–F4 + F6-live, sequenced as the E-standard: claim & verify
→ calendar/page sync → JSON-LD widget → NAP/pipe-consistency assists
(Bing Places, Foursquare, Yelp — §3.4's actual levers) → alerts + digest.
llms.txt included only as a free hedge (post-correction). This IS Phases
A/B already queued — the assessment strengthens it with the pipe-
syndication additions.
**Cost to us:** ~zero marginal (§11). **Risk:** lowest; no new externals.
**No-brainer force: HIGH but latent** — the value compounds silently; it
needs A's demonstration or a stat-led pitch to be FELT at minute zero.

### Option C — "The Doorman" (agent-interaction-first: an endpoint that answers for you)
OneLive-hosted agent endpoint (MCP now; NLWeb-compatible if it matures)
answering any agent's questions about the entity from PROMOTED gate data
with provenance tails (H5), plus the agent-traffic log (H1: "9 AI agents
asked about you this week; here's what they were told"), owner-revocable
authority (H2), and ACP-readiness for the ticketing handoff when
transactions arrive (§3.5).
**Cost to us:** serving ~zero (cached reads); build cost is the real
spend. **Risk:** standards flux; adoption depends on agents finding the
endpoint — strongest AFTER OneLive earns citations (H7 sequencing).
**No-brainer force: MEDIUM today, MAXIMUM in the agentic-commerce era** —
it is the moat, not the hook.

### Scoring (1–5, higher better)

| Criterion | A Mirror | B Feed | C Doorman |
|---|---|---|---|
| Time-to-"no-brainer" | 5 | 3 | 2 |
| Cost to us (inverse) | 3 | 5 | 4 |
| Customer cost | 5 ($0) | 5 ($0) | 5 ($0) |
| Trust-invariant fit | 4 (read-only demos) | 5 | 5 (gate-served) |
| Dependency risk (inverse) | 2 (engine TOS) | 4 | 3 (standards flux) |
| Moat contribution | 2 (copyable) | 5 (network) | 5 (seat at the rails) |
| Uses what exists (Steps 5–7 machinery) | 3 | 5 | 4 |

## 13. Recommendation (Blue merge — sequenced, not averaged)

**They are one funnel, not three rivals: A hooks → B delivers → C moats.**

1. **Build B first** — it is ALREADY the ratification-gated Phase A/B plan
   (v1 doc), now upgraded with §3.4's pipe-consistency assists (Bing
   Places/Foursquare/Yelp) as part of F2, and llms.txt demoted to hedge.
   Zero new decisions beyond Q1–Q8.
2. **Ship A as B's front door, not a separate product** — the Mirror is
   the claim-flow's first screen (the report card IS the onboarding
   preview, upgraded with live engine answers). Gated on: legal read of
   engine-querying TOS + a scan budget cap (both founder-crucial by
   existing rules: legal posture, spend). If legal kills live engine
   queries, the degraded Mirror (our-data-vs-their-site diff + the
   published 83%/45% stats) still works — weaker hook, same funnel.
3. **Build C in Phase C** exactly as Q6 already frames it, enriched with
   H1 (agent-traffic log), H2 (revocable authority), H5 (provenance
   tails), and ACP-readiness watch. Revisit timing the day any major
   assistant ships a local-events discovery API or ACP local inventory.

The composed pitch, one breath: *"Paste your website. Here's what AI gets
wrong about you today. One button fixes it — everywhere, free, forever,
and you hold the string."* That is the no-brainer sentence, and each
clause is a mechanism this stack actually delivers (Mirror; Feed;
pipes+widget; $0 promise; revocable authority token).

## 14. Beyond our core: the full B2A consultant service catalog (what a paid consultant could deliver that we deliberately don't — and our stance on each)

The founder's directive: name the specific services a B2A consultant could
deliver, beyond the core we've defined (F0–F6, Mirror/Feed/Doorman), that
would still be of real value to a business or artist. This matters for
three reasons: (1) it defines the honest boundary of our "80/20" — what
the free agent will NOT do, said out loud; (2) it maps the ecosystem that
will grow around the gap — some of it complementary, some of it the fee
wave we're protecting members from; (3) it is a future partner/referral
surface that must be designed to never contaminate the trust invariants.

Stance legend: **NEVER** (conflicts with invariants or physics) ·
**REFER** (real value, not our business — candidate for a vetted-referral
list) · **LATER** (could become ours in a later phase, founder-gated) ·
**EDGE** (partially covered by our core already; consultant adds the rest).

### 14.1 Visibility & data (adjacent to our core)
| Service | What the consultant does | Typical market price | Value to business | Our stance |
|---|---|---|---|---|
| Review strategy & response management | Solicitation flows, response SLAs, recovery campaigns to clear the ~4.3★ AI confidence threshold (§3.4) | $300–$1,500/mo | HIGH — reviews are the #1 AI-visibility lever we DON'T touch | **REFER** — F4 can alert ("your rating is below the AI threshold") but soliciting/responding is voice work we must not automate for them |
| Conversational content engineering | Rewriting site/FAQ content to answer the "best patio for eight" query shapes (79% of AI local prompts) | $1–5k one-time + retainer | MEDIUM-HIGH | **EDGE** — our JSON-LD + event data covers the factual layer; narrative content is theirs; F4 could someday flag gaps (LATER) |
| Competitor share-of-voice analysis | Which rivals appear in the 3–5 answer slots and why | in $2–8k/mo retainers | MEDIUM | **NEVER as a paid tier**; a neutral market-level version could be public data (H8 scoreboard); per-business competitive targeting sits badly beside no-pay-to-rank |
| Wikipedia/Wikidata/knowledge-graph presence | Notability-compliant entity entries AI models actually train on and cite | $2–10k one-time | HIGH for established entities | **REFER** — editing on behalf of subjects is COI-fraught; we should never ghost-edit knowledge bases |
| AI-crawler technical config | robots.txt/CDN/bot-access settings so AI crawlers can read the site at all (a silent killer) | $500–2k one-time | HIGH when broken | **EDGE** — the Mirror should DETECT "your site blocks AI crawlers" and show the fix; doing the server work is theirs/their webhost's |
| Hallucination correction filings | Formal feedback/correction submissions to OpenAI/Google/Perplexity and data providers (Foursquare/Yelp/Bing) when AI states falsehoods | emerging; hourly | HIGH when it bites | **LATER (Phase C candidate)** — a natural Doorman extension: we already hold the verified truth and the diff; founder decision because it makes us an agent-of-record |

### 14.2 Marketing execution (the classic agency stack, now AI-flavored)
| Service | Typical market price | Value | Our stance |
|---|---|---|---|
| Social media management (calendars, posting, community/DMs) | $500–$3k/mo | HIGH but labor-heavy | **NEVER as full service** — F5 drafts only, owner publishes (our physics); the E6 tail is deliberately theirs |
| Paid media (social ads, search ads, emerging AI-surface placements) | 10–20% of spend + fees | MEDIUM-HIGH | **NEVER** — pay-to-reach adjacency; also the first AI-surface ad markets are exactly the pay-to-rank world we refuse |
| Email/SMS/fan-club CRM (list building, newsletters, drops) | $200–$1k/mo + tools | HIGH for artists | **REFER** — real gap for artists; our F3 widget/feed can SUPPLY the content (next shows auto-populate their newsletter template) without us becoming their CRM |
| Photography/video/creative assets | $500–$5k/shoot | HIGH | **REFER** — pure creative services; note Descriptor Foundry governs only OUR descriptor text, never their creative |
| Brand strategy (positioning, naming, identity, voice) | $5–50k engagements | MEDIUM-HIGH for growth-stage | **REFER** — Neumaier-style work; ironically the discipline this doc uses is one we'd never sell |
| Influencer/creator collabs & seeding | $500–$5k/campaign | MEDIUM | **NEVER facilitate for pay**; Tastemaker posts remain a fully separate human trust category (standing architecture rule) — no commercial bridge, ever |

### 14.3 Revenue & operations (deep value, far from our lane)
| Service | Typical market price | Value | Our stance |
|---|---|---|---|
| Ticketing strategy, pricing/yield, comps policy | consulting rates; % deals | HIGH for venues | **NEVER advise; LATER hand off** — ACP-era ticketing handoff (§3.5) is infrastructure, not advice; pricing advice from the neutral truth-keeper is a conflict |
| Agentic-commerce enablement (ACP/AP2 checkout readiness, payments setup) | $2–10k implementations | HIGH within 1–2 yrs | **LATER (Phase C)** — Doorman's ACP-readiness covers discovery/handoff; merchant-side payment integration is theirs/Stripe's |
| Sponsorship & partnership brokering | 10–20% commissions | HIGH for festivals/series | **NEVER** — brokering with a fee against our own data is a rank-adjacent conflict |
| Grant writing / arts funding applications | $1–5k or % | HIGH for nonprofits/artists | **REFER** — genuinely valuable, entirely outside our physics |
| Staff AI-literacy training | $1–3k/workshop | MEDIUM | **REFER**; our plain-language digests and docs quietly do the 80% version for free |
| Web design/build, accessibility (WCAG), performance (CWV) | $3–30k | HIGH when the site is the bottleneck | **EDGE** — the widget gives them a correct, fast events section inside whatever site they have; whole-site work is theirs. Mirror can flag "your site is unreadable/slow for crawlers" |

### 14.4 Artist-specific services
| Service | Typical market price | Value | Our stance |
|---|---|---|---|
| EPK (electronic press kit) creation & maintenance | $300–$1,500 | HIGH for booking | **LATER-lite** — a verified OneLive artist page with accurate dates/venues/links IS 70% of an EPK; a "share as EPK" view is a cheap Phase-B+ candidate (queued as an idea, not a promise) |
| DSP profile management (Spotify for Artists, Apple Music) & playlist pitching | $200–$1k/mo; per-pitch fees | HIGH (and scam-dense) | **REFER with a warning label** — payola-adjacent pitching is exactly the ecosystem our members need protecting from; any referral list must exclude pay-for-placement operators |
| Sync licensing representation | 20–50% commissions | MEDIUM-HIGH | **NEVER** (already in the founder-decision backlog as its own P3 question — unchanged here) |
| Tour routing & demand analytics | tools + consulting | MEDIUM | **LATER-lite** — aggregate, privacy-clean demand signals from our consumer side could someday inform artists ("Austin indexes high for your genre") — founder-gated, Phase 3+, never individual-user data |
| Merch strategy & fulfillment | % or retainers | MEDIUM | **REFER** — commerce operations, not our lane |

### 14.5 What this catalog means strategically
1. **The 80/20 boundary is now explicit and defensible.** Our free core =
   presence, accuracy, representation (the universal substrate every
   entity needs). The paid world = judgment, creative, negotiation, and
   labor (reviews, content voice, ads, brokering, brand). We should SAY
   this boundary in partner-facing copy — it makes "free forever" credible
   because the business model behind the free tier is legible.
2. **A vetted-referral surface is a real future asset with a live wire in
   it.** Businesses will ask "who should I hire for the rest?" A referral
   list monetized in ANY way (fees, commissions, placement) recreates
   pay-to-rank one layer out. If we ever do this: unpaid, criteria
   published, no-payola exclusions explicit (especially playlist
   pitching), and founder-ratified. Logged as Q13 — not proposed for now.
3. **Three LATER items are genuine roadmap candidates** because they ride
   machinery we already build: hallucination-correction filings (Doorman +
   verified diffs), EPK-view (artist page reskin), AI-crawler diagnostics
   in the Mirror. Each returns through the normal gates when its phase
   arrives.
4. **The NEVERs are load-bearing.** Ads brokering, competitive targeting,
   sponsored placement, commission brokering, ghost-editing knowledge
   bases — each is a real revenue line competitors will take, and each
   would cost us the only thing that makes the whole strategy work. The
   catalog doubles as a pre-registered list of temptations refused.

## 15. Additions to the consolidated founder list (Q9–Q13)

- **Q9 — Sequencing ratification:** adopt §13 (B first as already gated;
  A as B's front door behind legal + cap; C per Q6 with H1/H2/H5)?
- **Q10 — Mirror preconditions (founder-crucial by existing rules, asked
  once here):** (a) authorize a legal read of AI-engine querying TOS
  before any Mirror build; (b) approve a per-metro monthly scan budget cap
  as a standing FinOps gate (H6). No dollar decision needed today —
  approval to PREPARE both, decision packet returns with numbers.
- **Q11 — Pipe-consistency scope:** fold Bing Places/Foursquare/Yelp
  consistency assists into F2 (guided or API where free; never charging,
  never reselling)? This edits the ratification packet Q1 covers.
- **Q12 — Public accuracy scoreboard (H8):** adopt per-metro answer-
  accuracy as a published mission metric (with the vendor-stat haircut
  noted in §10 Black)?
- **Q13 — Beyond-core stance ratification (§14):** confirm the
  NEVER/REFER/LATER/EDGE stances as standing policy — in particular the
  NEVERs (§14.5.4) as pre-registered refusals, and that any future
  vetted-referral list is unpaid, criteria-published, payola-excluding,
  and founder-ratified before it exists in any form?

## 16. Sources

Landscape/actors: [Search Influence — AI SEO tracking tools 2026](https://www.searchinfluence.com/blog/ai-seo-tracking-tools-2026-analysis-platforms/) · [Surmado — Profound vs Peec vs Otterly](https://www.surmado.com/blog/best-ai-visibility-tools-2026) · [Ayzeo — GEO platforms compared](https://ayzeo.com/comparisons/geo-platforms-compared) · [WebFX — GEO cost](https://www.webfx.com/blog/ai/generative-engine-optimization-cost/) · [Digital Elevator — AEO/GEO pricing](https://thedigitalelevator.com/blog/aeo-and-geo-pricing-guide/) · [SocialPilot — BrightLocal vs Yext pricing](https://www.socialpilot.co/reviews/comparison/brightlocal-vs-yext) · [Guideflow — listings tools 2026](https://www.guideflow.com/blog/local-listing-management-software-tools)
Market/demand: [Valuates via Yahoo — GEO services $7.3B by 2031](https://finance.yahoo.com/news/generative-engine-optimization-geo-services-151200019.html) · [Dimension MR — GEO CAGR 40.6%](https://dimensionmarketresearch.com/report/generative-engine-optimization-geo-market/) · [Omnibound — 60+ GEO statistics](https://www.omnibound.ai/blog/generative-engine-optimization-statistics) · [Bloom Intelligence — AI restaurant discovery data](https://bloomintelligence.com/blog/ai-restaurant-discovery/) · [Uberall via BusinessWire — 83% invisible](https://www.businesswire.com/news/home/20260507962493/en/83-of-Restaurants-Are-Invisible-in-AI-Search-New-Uberall-Report-Reveals-the-Discovery-Gap-Reshaping-the-Quick-Service-Restaurant-Industry) · [Local Falcon — the AI visibility crisis](https://www.localfalcon.com/blog/the-ai-visibility-crisis-why-83-percent-of-restaurants-dont-exist-in-chatgpt)
Mechanics (what AI reads): [Local Falcon — ChatGPT local data sources](https://www.localfalcon.com/blog/chatgpt-local-search-data-sources-where-does-business-info-come-from) · [Search Engine Land — how ChatGPT conducts local searches](https://searchengineland.com/how-does-chatgpt-conduct-local-searches-454894) · [SOCi — ranking in ChatGPT/Perplexity/AIO](https://www.soci.ai/blog/how-to-rank-in-chatgpt-perplexity-and-google-ai-overview/) · [Local AI Audit — review thresholds](https://local-ai-audit.com/blog/how-chatgpt-finds-local-businesses/)
llms.txt correction: [Ahrefs — 137k-site study, 97% unread](https://ahrefs.com/blog/llmstxt-study/) · [SERoundtable — Mueller: no AI system uses llms.txt](https://www.seroundtable.com/google-ai-llms-txt-39607.html) · [SEJ — Google: llms.txt speculative](https://www.searchenginejournal.com/google-says-llms-txt-is-purely-speculative-for-now/577576/)
Rails: [Stripe — ACP with OpenAI](https://stripe.com/newsroom/news/stripe-openai-instant-checkout) · [ACP spec repo](https://github.com/agentic-commerce-protocol/agentic-commerce-protocol) · [Digital Applied — UCP vs ACP vs AP2](https://www.digitalapplied.com/blog/agentic-commerce-standards-ucp-acp-ap2-2026-merchant-guide)
