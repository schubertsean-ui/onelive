# 1LIVE — Heartbeat Analytics Productization & Market Strategy (v1)

**Status: PROPOSAL — research response to the founder's 2026-08-03 directive (Session
Contract #34, STATE.md). Nothing here is license to build, price, sell, or key a vendor.
Heartbeat external monetization is founder-crucial (money, new services, data resale,
legal posture — `docs/strategy/ONE_LIVE_ANALYTICS_METRICS_v1.md` §12); every number in
this paper is illustrative until founder-ratified. Web-sourced figures carry their source
and retrieval date (2026-08-03); ranges are ranges, never precision theater.**

Greppable summary: Heartbeat today is 100% specification and 0% implementation — a
world-class measurement canon (`ONE_LIVE_ANALYTICS_METRICS_v1.md`) with no tracking
events, no warehouse, no snapshots, no semantic layer, and no external surface. The
world-class "data IS the business" archetypes (Verisk, CoStar, Placer.ai, Luminate,
Zartico, Spotify-for-Artists) share five moves 1Live can run without breaking one trust
invariant: a contributory/observed data flywheel, chart-of-record status, free supply-side
analytics as lock-in, civic dashboard contracts, and API licensing last. The recommended
journey: measure ourselves → publish free public reports (brand, zero revenue) → free
consent-gated self-dashboards for artists/orgs (supply lock-in) → paid city/DMO contracts
+ org insights subscriptions → multi-metro benchmarks + API licensing. The critical
"per …" spine: **cost per verified event-record** (input, canon §14.2) × **verified
event-records per market-night** (coverage density) × **Heartbeat net revenue per
verified event-record** (output) — with **calibration** (are our 90%s right 90% of the
time) as the quality gate that makes the whole product sellable. The consumer North Star
(TTFR / verified discoveries acted on) is never replaced or diluted by any revenue KPI.

---

## §1 · The ask (2026-08-03, paraphrase-anchored)

1. Evaluate the canon and repo for the Heartbeat analytics engine — capability and
   functionality.
2. Assess world-class analytics models for businesses where data IS the business — what
   they do, how, how they position/market/deliver/engage/monetize.
3. Market analysis of productizing the data from initial to fully robust matured
   capability; recommend positioning/marketing/delivery/service/monetization along the
   journey.
4. Everything required to build and grow into one of those world-class platforms,
   including expected cost and revenue specs — and the core "per …" analytics that will
   be the key drivers of growth and the absolute critical KPI.

---

## §2 · Canon & repo evaluation — what Heartbeat is, and what actually exists

### 2.1 What the canon says Heartbeat is

One measurement engine, two faces (founder, 2026-07-31; `ONE_LIVE_ANALYTICS_METRICS_v1.md`
lines 10–18): 1Live measuring **itself** (the internal analytics canon — four lenses
breadth/depth/accuracy/usage · ITR 3/12·6/12·12/12 rate-of-change · one semantic layer ·
the honesty floor "never guess a number") and the **same engine pointed at the culture**
— the external Heartbeat insights offered to cities, orgs, and artists (§12 of that doc).
The product-vision canon frames it as "aggregate, real-time analytics on flows …
monetized as insights (premium dashboards, city contracts)"
(`ONE_LIVE_PRODUCT_VISION_AND_PRINCIPLES_v1.md`), and the convergence spec supplies the
differentiated metrics: genre momentum with business-cycle phase, venue vitality, and
"ambiguity as cultural signal" (`ONE_LIVE_CONVERGENCE_v1.md` §8).

### 2.2 Status honestly stated

| Artifact | Status |
|---|---|
| Analytics & Measurement canon (the internal engine spec) | PROPOSAL, unratified |
| Heartbeat as a monetized external product | Founder-crucial, net-new surface; no contract exists |
| Convergence engine (the data supplier for the cultural metrics) | Code exists, SHADOW-ONLY, quarantined by import-isolation tests |
| Analytics privacy policy (no-PII / opt-in) | **Does not exist as canon — a ratification blocker before any user-behavior capture** (`ANALYTICS_METRICS_v1` §9) |
| North Star metric | Unratified (RECORD R-046) |
| v1 wedge decision | **"Creator-Venue Matching (not Heartbeat Analytics) is the v1 differentiator" is a recorded decision (STATE.md).** This paper does NOT argue against it — it sequences Heartbeat as the second act, not the wedge. |

### 2.3 What exists in the repo (capability audit, verified 2026-08-03)

**Implemented: nothing of Heartbeat itself.** No `fact_*`/`dim_*`/`snapshot_*` tables in
`supabase/migrations/` (0001–0019 are pipeline/RLS/providers/spark-line); no tracking
events anywhere in `web/`; no analytics endpoint in `api/`; every "heartbeat" string in
running code is the healthchecks dead-man ping, not this product. The canon's own §8
says it plainly: product-usage capture, warehouse, snapshots, semantic layer, coverage
denominator, and per-event cost logging are "genuinely absent."

**Reusable seeds (real, tested, running):**
- KPI registry + reporter (`docs/metrics/kpi_registry.json`, `tools/kpi_report.py`) with
  the honest "not yet instrumented (trigger: …)" pattern — the seed of the semantic layer.
- The extraction eval harness (`ai/golden_exam.py`) — certified hallucination 0.63% /
  recall 97.82%; the accuracy-measurement muscle the external product will brag about.
- Source-pathway status (`tools/source_pathways.py`) — the source-coverage numerator.
- Entity resolution (`worker/resolve_entities.py`) + CAPCOG geo (tri-state, never guessed).
- The convergence shadow code (`worker/convergence/`): Subjective Logic opinions,
  Monte-Carlo scenario engine, expected-loss decision layer — and, crucially for a data
  product, the **closure loop** design: our claims *resolve* (the event happens or it
  doesn't), so every belief is a scored forecast and calibration is measurable. That is
  the moat no scraped-data competitor can fake.

### 2.4 The constraint set any productization must satisfy (physics, not preferences)

1. **Aggregate-only externally; individual-level data never sold or shared.** Violation
   is a dissolution trigger in the product-vision canon.
2. **Artist data is consent-gated** — an artist sees their own data free (Artist Bill of
   Rights #5); artist-level resale requires that artist's explicit consent.
3. **No PII, ever, in any external artifact**; privacy fail-closed; private RSVPs never
   enter analytics.
4. **Insights never touch ranking** — a paying city/venue can SEE the heartbeat, never
   reorder the feed. The insights surface is walled off from discovery exactly as
   tastemaker posts are. No pay-to-rank, one layer out, included: no paid referral lists,
   no per-business competitive targeting tiers (the B2A refused-temptations catalog).
5. **Resolved strata only, all four confidence states, disputed carried as a labeled
   dimension** — "resolved" ≠ "confirmed-only"; external numbers are exactly as honest
   as internal ones.
6. **Anti-attention-economy:** time-given-back is the success metric; no Heartbeat KPI
   may push the consumer product toward engagement farming.
7. **Legal posture (deep-review §10–§15, still PROPOSAL but binding direction):** TDPSA
   (precise geolocation = sensitive; GPC honored), TRAIGA (NIST AI RMF safe harbor),
   DPAs with every processor, SOC 2 Type-2 before city-contract procurement, EU-AI-Act
   emotion guardrails (declared-feel only, never biometric/inferred).

**One tension this paper resolves explicitly:** the B2A assessment's zag ("the industry
sells visibility analytics to marketers; we give the fix free and monetize nothing about
it") coexists with §12's premium dashboards by a clean line the canon already implies —
**market-level aggregates may be sold; entity-level competitive targeting never; an
entity's OWN data is free to that entity; nothing ever touches ranking.** Selling a city
its cultural vitality is not selling a venue its competitor's numbers.

---

## §3 · World-class models where data IS the business

Six archetypes, each a real company at world-class execution, each mapped to what 1Live
can copy and what it must refuse. (Figures: public sources, retrieved 2026-08-03.)

### 3.1 The contributory-data utility — **Verisk** (insurance)
- **What/how:** insurers contribute claims/loss data; Verisk aggregates 39B statistical
  records, licenses back analytics no single insurer could build; acts as the licensed
  "statistical agent" in all 50 states. Data gets better as more members contribute —
  a network effect competitors cannot enter.
- **Economics:** recurring subscriptions, ~50–56% adjusted EBITDA margin, >$1B FCF/yr.
- **Positioning:** neutral industry utility; embedded in regulatory workflow.
- **1Live lesson:** the **corroboration overlap** we already log for trust IS a
  contributory network (venues/orgs/artists supplying their own truth via claims and the
  B2A agent). The more entities publish clean truth through us, the better the coverage
  denominator and calibration — the same flywheel. Also the standard-setting play: be the
  "statistical agent" of live culture (the E-standard, the accuracy scoreboard).
- **Refuse:** Verisk's data is club-gated; our public layer stays public and free.

### 3.2 The observed-panel insights SaaS — **Placer.ai** (foot traffic)
- **What/how:** location panel → foot-traffic estimates for any venue/chain; freemium →
  tiered SaaS by locations tracked/seats; marketplace of third-party datasets; bespoke
  reports for enterprise.
- **Economics:** $100M ARR (Feb 2024), accounts ~$5k–$30k/yr, NRR >115%.
- **Positioning/marketing:** free viral-grade insights content (public rankings, "foot
  traffic recovery" press datasets) that journalists cite → inbound demand.
- **1Live lesson:** the **free public report as the marketing engine** (our Mantle M-C
  "State of the Scene" and M-G accuracy scoreboard are exactly this, already imagined,
  free, vendor-taint-free). Tiering by geography/slice depth, not by data category.
- **Refuse:** Placer sells competitive surveillance of named businesses — for us that is
  a NEVER (per-business competitive targeting sits badly beside no-pay-to-rank).

### 3.3 The chart of record — **Luminate/Billboard**, **Pollstar** (music industry)
- **What/how:** Luminate's verified consumption data powers the Billboard charts — the
  industry's shared scoreboard; subscriptions ~$3,540/yr for regional insight tiers.
  Pollstar sells box-office history (319k artists, 1999–present) as the touring
  industry's memory.
- **Positioning:** "never scraped, estimated or crowdsourced — verified and validated."
  The chart is marketing, the subscription is revenue, the verification story is the moat.
- **1Live lesson:** this is our closest kin — our whole identity is *verified*, and we
  can honestly print the confidence state and calibration score next to every number,
  which nobody else in cultural data does. A weekly/annual **1Live Chart of the Scene**
  (aggregate genre momentum by metro, disputed shown-as-disputed) is chart-of-record
  positioning from day one, free, citable.
- **Refuse:** pay-for-placement chart adjacency (chart integrity is the asset).

### 3.4 The civic dashboard vendor — **Zartico** (destination/tourism analytics)
- **What/how:** dashboards of visitor movement/spend/sentiment for government-affiliated
  DMOs; all clients are cities/counties/visitor bureaus.
- **Economics:** ~$10M ARR; entry contracts observed at $10k–$25k/yr even for small towns
  (Sanford NC $25k; Marfa+Alpine TX $10k each); Series A $20M.
- **Positioning/delivery:** "see your visitor economy clearly"; annual SaaS contract +
  onboarding + quarterly business reviews; procurement-friendly (this is where SOC 2 and
  DPAs pay off).
- **1Live lesson:** the **city/DMO cultural-vitality dashboard** is a proven,
  procurement-budgeted category with public price anchors; our §12 city audience maps
  onto it 1:1 (event density by neighborhood, genre momentum with ITR phase, venue
  vitality, supply-gap). Austin's ecosystem (city economic development, Visit Austin,
  county tourism) is the natural first logo set.
- **Refuse:** nothing structural — this is the cleanest first-revenue fit.

### 3.5 Free supply-side analytics as lock-in — **Spotify for Artists**, **Bandsintown**
- **What/how:** Spotify gives artists rich analytics free — not revenue, *supply
  acquisition and retention*; Bandsintown monetizes via ticket affiliate + data licensing
  + promoter tools while artist listing stays free.
- **1Live lesson:** the §12 artist audience ("their own momentum and reach,
  consent-gated — a Spotify-for-Artists analog") and org self-dashboards should be
  **free forever** as the claim-flywheel engine: every claimed dashboard deepens our
  entity resolution, corroboration, and consent graph. The canon's grant-currency
  finding (nonprofits/theaters need "provable community participation numbers") makes the
  free self-dashboard the single highest-leverage acquisition artifact for supply
  categories 14 and 22.
- **Refuse:** Bandsintown-style resale of fan-level data (aggregate-only is physics).

### 3.6 API/data licensing — **Foursquare-class places/eventdata APIs**
- **What/how:** usage-based licensing with minimums to developers/enterprises/research.
- **1Live lesson:** real, but **last** — API licensing commoditizes whatever it exposes
  and invites downstream misuse we cannot audit; it belongs only after aggregate-only
  export tooling, k-anonymity floors, and contract review exist. (The legacy spec's "API
  licensing (usage-based + minimums)" line survives, at maturity.)

### 3.7 The synthesis — what world-class looks like for us
Every one of these businesses monetizes **trust in a number**, and every one grew the
same way: give a credible free artifact the industry cites → let the supply side
contribute/claim (flywheel) → sell recurring seats/contracts on the derived aggregate →
license at the edges. Their moats are contributory network effects + being the record of
record + switching costs of embedded workflow. 1Live's version adds one thing none of
them have: **printed confidence states and scored calibration** on every number — an
audited cultural record. Market context for scale reference: location intelligence ~$25B
(2025) and alternative data ~$14–19B, both double-digit CAGR — we need a sliver of a
niche, not a market share.

---

## §4 · Why our data can be world-class (and where it honestly is not yet)

**Defensible:**
1. **Resolved ground truth with confidence states** — four states, disputed shown, every
   external number exactly as honest as the internal one. Nobody selling cultural or
   event data prints "X confirmed, Y disputed."
2. **Calibration as a product feature** — the closure loop Brier-scores every source and
   judge; "when we say 90% we are right 90% of the time" is an auditable sales claim.
3. **Honest coverage denominators** — capture–recapture + golden reference sets; we can
   state "we see an estimated 78% of the market's live events" with a method, where
   competitors imply 100% silently.
4. **The claim/consent graph** — venue/org/artist-claimed truth (B2A "works without us,
   better with us") compounds; it is the Verisk contributory move in our domain.
5. **Differentiated metrics** — genre momentum with ITR cycle phase, venue vitality,
   supply-gap (demand with thin supply), tag-entropy as cultural signal.

**Honestly not yet:**
- One metro (CAPCOG), no external market.
- ITR trending needs history: a 3/12 needs ≥15 months, a 12/12 needs ≥24 — the clock
  starts when snapshots start, which is the strongest argument for building Phase 1–2
  NOW even with zero revenue intent.
- No usage capture at all; DB row counts for events remain small/unverified; escaped-error
  and cost-per-event uninstrumented.
- No privacy-policy canon, no SOC 2, no DPAs — all required before the first paid civic
  contract.

---

## §5 · Market analysis by audience (initial → matured)

All figures are planning ranges, not commitments. Anchors: Zartico contract observations,
Placer account bands, Luminate/Chartmetric price points, the repo's legacy revenue lines
(venue SaaS $49–$199/mo; festival/city integrations $25k–$250k; API usage-based;
premium $4.99/mo) and the ratified Tier-2 direction (market alternatives $300–$5,000/mo,
we deliberately price below).

| Audience | Buyer & budget | Comparable price anchor | Our realistic entry (single metro) | At maturity (multi-metro) |
|---|---|---|---|---|
| Cities / DMOs / econ-dev / tourism | Public budgets; procurement | Zartico $10k–$25k/yr small-market; $25k–$250k legacy line for integrations | 1–3 contracts × $10k–$40k/yr | 8–20 metros × $25k–$100k+/yr |
| Orgs (venues, promoters, festivals) | Marketing/ops budget, thin margins (NIVA: 64% of independent venues unprofitable) | Tier-2 alternatives $300–$5k/mo; our SaaS line $49–$199/mo | Own-data dashboards FREE; paid market-context tier $49–$199/mo for a minority | Hundreds of subscribers/metro at $49–$299/mo |
| Artists | Near-zero willingness to pay (avg ~$32k income; Chartmetric artist tier is $10/mo) | Spotify-for-Artists = free | FREE, consent-gated, forever | FREE (the flywheel, not the revenue) |
| Nonprofits/arts councils/theaters (grant reporting) | Grant admin budgets; the number IS their funding currency | bespoke; no clean comparable | Free artifacts first (Mantle posture); paid "funder-ready participation reports" only if founder prices them | $500–$5k/yr per org reporting package |
| Researchers / press / API | Foundations, universities, media | Luminate $3.5k/yr; API usage-based | Free citable public reports (they are our marketing) | API licensing with minimums + research subscriptions |

Honest sizing: a fully-executed single-metro Heartbeat is a **$0.1–0.5M ARR** business;
the world-class outcome is the **multi-metro benchmark network** (the only version with
Verisk-style network effects), plausibly **$5–25M ARR at 15–30 metros** — a strong
second revenue engine beside the consumer product and B2A motion, not a Placer-scale
standalone. The data asset's larger value remains what it does for the core product:
coverage, trust, and default status.

---

## §6 · The productization journey — positioning, marketing, delivery, service, monetization at each stage

**Stage 0 — Measure ourselves (now; prerequisite; $0 revenue).**
Internal engine Phases 1–4 exactly as spec'd (`ANALYTICS_METRICS_v1` §11): tracking plan
(no PII) → fact/dim/snapshot tables → semantic layer + ITR ROC → denominator program.
*Position:* nothing external. *Why now:* "you cannot honestly sell a cultural heartbeat
you cannot yet measure" — and the 24-month ITR clock only starts when snapshots exist.
*Gate:* privacy-policy ratification before any user-behavior capture.

**Stage 1 — Give the record away (months ~3–9 from Phase-2 data; $0 revenue, all brand).**
*Deliver:* the free public artifacts already imagined in canon — the metro accuracy
Scoreboard (M-G), the annual/semiannual "State of the Scene / State of AI Visibility in
Austin Live Culture" report (M-C), a weekly aggregate genre-momentum chart. Disputed
shown as disputed; methods printed; PDF + public page.
*Position:* "the audited record of live culture" — chart-of-record, Luminate-style
verification story, zero vendor taint because we sell nothing.
*Market:* press citations, city-hall and arts-council distribution, the B2A roadshow.
*Service:* none — artifacts, not accounts.
*Monetize:* nothing. This stage builds the citation moat and the sales pipeline for
Stage 3 without touching a single invariant.

**Stage 2 — Free self-dashboards (supply lock-in; $0 revenue).**
*Deliver:* consent-gated own-data dashboards — artist momentum/reach
(Spotify-for-Artists analog), venue/org own-vitality (listing accuracy, resolution
trends, demand in their area at market-aggregate level), funder-ready participation
numbers for nonprofits/theaters (their grant currency).
*Position:* Artist Bill of Rights made tangible — "your data is yours, free."
*Market:* the claim flow itself + category-by-category outreach per the 23-segment
research (lead with the grant-currency segments 14/22 and promoters 13).
*Service:* self-serve; email support.
*Monetize:* nothing — this is the contributory flywheel (claims → better entity
resolution → better coverage → better product). *Gate:* claim/consent flows, RLS on
every org-scoped view (fail-closed).

**Stage 3 — First revenue: civic contracts + org market-context tier (founder-gated GO).**
*Deliver:* the §12 city dashboard (event density by neighborhood, genre momentum with
phase, venue vitality, supply-gap; confidence state as a visible dimension) as an annual
contract with onboarding + quarterly reviews (Zartico's service pattern). For orgs: a
paid market-context tier (their area/category demand patterns, supply-gap alerts —
aggregate-only, never competitor-named) at the existing $49–$199/mo SaaS line.
*Position:* for cities, "measure the cultural economy you fund"; for orgs, "see demand —
never buy placement."
*Market:* founder-led sales to 3–5 Austin-ecosystem logos off the Stage-1 report;
procurement docs ready (SOC 2, DPAs, TDPSA/TRAIGA posture).
*Service:* contract onboarding, QBRs, a named support channel; uptime + freshness SLOs
(the observability pillars become customer-facing SLAs).
*Monetize:* city $10k–$40k/yr; org tier $49–$199/mo; grant-report packages if the
founder prices them.
*Gates (all founder-crucial):* pricing, Stripe/billing service, contract templates
(legal posture), SOC 2 spend, the walled-off insights surface (new service).

**Stage 4 — Maturity: the benchmark network (multi-metro).**
*Deliver:* cross-metro benchmarks ("Austin vs Nashville genre momentum"), the annual
national report as category anchor, research subscriptions, and only now API licensing
(aggregate-only endpoints, k-anonymity floor ≥ a ratified threshold, usage minimums,
audit-able terms).
*Position:* the Verisk of live culture — the neutral statistical agent every city,
promoter association, and newsroom cites.
*Economics:* network effects finally real (each metro makes every benchmark more
valuable); NRR >110% via slice/seat expansion, Placer-style.
*Gate:* multi-metro expansion is a product decision that precedes the data decision —
Heartbeat maturity rides the consumer/B2A expansion map, never leads it.

---

## §7 · Everything required to build it (delta over the internal engine)

**Already spec'd (build first, unchanged):** Phases 1–4 of `ANALYTICS_METRICS_v1` §11 —
tracking plan, per-event cost logging, source-overlap logging, fact/dim (SCD-2) +
snapshot tables, dead-man-pinged snapshot jobs, semantic layer, ITR ROC engine,
capture–recapture denominator. Roughly 4–8 focused build-weeks of agent work across
existing Supabase/Python infrastructure; near-zero marginal infra cost at current scale.

**Net-new for the external product (each ⚑ = founder-crucial):**
1. A **walled-off insights surface** (separate routes/service; import-isolation tests
   from the discovery pipeline, exactly like tastemaker separation) ⚑ new service.
2. **Aggregation/anonymization layer with a ratified k-floor** (no cell smaller than k
   entities/users ships externally) + an export/reporting engine (PDF + dashboard).
3. **Accounts & entitlements** for orgs/cities on Clerk + fail-closed RLS per tenant.
4. **Billing** (Stripe subscriptions/invoicing) ⚑ money + new service.
5. **Compliance pack:** ratified analytics privacy policy (blocker), data map, DPAs with
   every processor, SOC 2 Type-2 program, TDPSA rights flow, TRAIGA/NIST AI RMF mapping
   ⚑ legal posture + spend.
6. **Contract + pricing packet** ⚑.
7. **Service muscle:** onboarding runbooks, QBR template, SLOs (freshness/uptime),
   support channel, status page.
8. **Sales/marketing artifacts:** the Stage-1 public report pipeline (generated from the
   semantic layer, like `marketing_model/build_paper.py` generates papers), a
   procurement one-pager, the calibration/methods page.

**Expected cost specs (planning ranges, not commitments):**
- Stage 0–2 incremental cash cost: **~$0–$500/mo** (Supabase/Vercel headroom, snapshot
  compute; no new vendors required by design; PostHog/warehouse deferred ⚑).
- SOC 2 Type-2 when triggered: **~$30k–$80k first year** (audit + tooling) ⚑.
- Legal (privacy policy, DPA review, city contract template): **~$10k–$30k** one-time ⚑.
- Stage 3 delivery cost per city contract: onboarding + QBRs ≈ **$3k–$8k/yr** equivalent
  effort — gross margin >70% at $25k/yr, Verisk-class at benchmark maturity.
- Model spend: Heartbeat adds **no new extraction spend** (it reads resolved strata the
  product already pays for) — the data product's COGS is amortized pipeline cost, which
  is why the per-event unit economics below are the whole game.

**Expected revenue specs (same caution):** Stage 3 year-one realistic case **$40k–$120k
ARR** (2–3 civic logos + 20–60 org subscriptions); single-metro ceiling ~$0.5M ARR;
multi-metro maturity $5–25M ARR (see §5). Break-even on the external build at roughly
**two civic contracts** — the venture risk is small and the invariant risk is the real
cost to manage.

---

## §8 · The "per …" spine — the critical KPIs

The businesses in §3 each run on one unit economic (Placer: revenue per tracked
location; Verisk: margin per contributed record; Zartico: revenue per destination).
Ours must bind revenue to the thing our gates make scarce and trustworthy: the **verified
event-record** (a resolved, published event carrying its confidence state). The spine:

1. **Cost per verified event-record** *(the input; already canon as §14.2
   cost-per-verified-published-event; uninstrumented — R-046).* Every pipeline decision
   (routing, caching, batching) shows up here. World-class = falling 12/12 while quality
   gates hold.
2. **Verified event-records per market-night, against the estimated universe** *(the
   asset: coverage density with an honest denominator).* You can only sell a heartbeat
   you actually hear. This is the growth driver of BOTH the consumer product and
   Heartbeat — one number serving both.
3. **Heartbeat net revenue per verified event-record** *(the output; at maturity, per
   metro: ARR ÷ verified event-records under coverage).* The single number that says the
   data asset is becoming a business. Its city-level cousin — **ARR per covered metro vs
   cost per covered metro** — is the expansion go/no-go arithmetic.
4. **The quality gate that makes 1–3 sellable: calibration** (Brier/calibration score on
   resolved claims) and **escaped-error rate** (zero is absolute). If these degrade, no
   revenue KPI matters — the product IS the trustworthiness.

**The absolute critical KPI**, if the founder wants exactly one: **net margin per
verified event-record** = (attributable Heartbeat revenue − amortized pipeline cost) per
verified event-record, trended 3/12·6/12·12/12. It fuses the canon's cost discipline
(§14.2), the coverage flywheel (denominator in view), and monetization into one honest
"per" — and it cannot be gamed by engagement farming because the unit is a *verified
record*, not a user-minute. Consumer North Star (verified discoveries acted on / TTFR)
remains separate and senior on the product side; no revenue KPI ever enters ranking or
feed logic (measurement observes, never ranks).

Instrumentation order (all inside the Stage-0 build, no new spend): per-event cost
logging → coverage denominator → revenue attribution comes free with billing at Stage 3.

---

## §9 · Risks and tradeoffs, honestly

1. **Neutrality optics:** selling city dashboards while claiming "we are a mirror, never
   a promoter" invites a "who do you really serve" story. Mitigation: publish the free
   public layer first (Stage 1), publish methods, and keep the refused-temptations list
   public-facing policy.
2. **Small-cell re-identification:** aggregate slices in a small metro can identify a
   single venue/artist. The k-floor must be ratified physics before any external export
   — treated with the same seriousness as RLS.
3. **The 24-month clock:** the flagship "genre momentum with cycle phase" product is
   honestly not computable until ≥24 months of snapshots exist; interim products must be
   level-and-short-trend only, labeled per the honesty floor. Delaying Stage 0 delays
   the sellable product one-for-one.
4. **Opportunity cost:** Stage 0–2 is real build time against a v1 whose ratified wedge
   is Creator-Venue Matching. Mitigation: Phases 1–2 are largely shared infrastructure
   (the product needs its own measurement regardless); Stages 1–2 are marketing/flywheel
   assets for the core product, not detours.
5. **Single-market concentration:** one metro's civic budget cycle can zero the revenue
   line; do not staff against it until multi-metro.
6. **Regulatory drift:** TDPSA/TRAIGA enforcement and EU expansion tighten annually —
   the aggregate-only/no-PII/consent-gated architecture is the durable answer; the
   compliance pack (§7.5) is not optional at Stage 3.

---

## §10 · The consolidated founder ask (the ONLY interrupts; everything else proceeds under existing canon)

Nothing below is time-critical today; items 1–2 unblock Stage 0, the rest sit until
their stage. Plain-language, one list, smallest-effort first:

1. **Ratify the Analytics & Measurement canon** (`docs/strategy/ONE_LIVE_ANALYTICS_METRICS_v1.md`)
   as the internal source of truth, and **pick the North Star** (its §5 candidate:
   verified event-discoveries acted on per week). — a yes/no + one choice.
2. **Ratify the analytics privacy policy** (no-PII, opt-in, on-device split per the
   user-journey canon) — required before any user-behavior capture ships; we will draft
   it for a yes/no.
3. **Bless the staged journey in principle** (this doc §6): free public reports and free
   consent-gated self-dashboards may be BUILT when the queue allows (they monetize
   nothing and touch no invariant); any PRICED surface returns as its own contract.
   — direction only, revocable.
4. At Stage 3 (not now): pricing packet, Stripe/billing, city-contract template, SOC 2
   spend — each arrives as its own founder-crucial packet with numbers.
5. **Confirm the reconciliation of the B2A zag with §12** as stated in §2.4 (market-level
   aggregates sellable; entity-level competitive targeting never; own-data free;
   nothing touches ranking) — this becomes the one-line rule every future insights PR
   is reviewed against.

**Why this plan and not the alternatives considered:** (a) *Sell city contracts now* —
rejected: nothing to sell honestly (no snapshots, no history, no privacy canon, no SOC 2);
(b) *API-first licensing* — rejected: commoditizes the asset before the brand exists and
maximizes misuse risk; (c) *never monetize (pure B2A zag)* — rejected: the canon already
ratifies insights as a legitimate lane and civic dashboards are the rare revenue that
strengthens neutrality (cities fund culture, they don't compete in it); the tradeoff we
accept is a slower path to revenue in exchange for an unassailable verification story.

---

## Appendix · Sources (retrieved 2026-08-03)

Placer.ai ARR/pricing: placer.ai blog ($100M ARR), growhackscale.com, softwarefinder.com
· Verisk model/margins: umbrex.com company profile, fool.com/yahoo finance coverage
· Zartico: techcrunch.com + businesswire.com (Series A), utahbusiness.com (~$10M ARR,
client pricing examples) · Luminate/Chartmetric pricing: luminatedata.com,
chartmetric.com/pricing, viberate.com comparison · Pollstar Data Cloud: pollstar.com
· Bandsintown/Songkick models: billboard.com, corp.bandsintown.com · Market sizing:
precedenceresearch.com (location intelligence ~$25B 2025; alternative data ~$14B 2025),
grandviewresearch.com (~$18.8B 2025). Internal grounding: the file:line citations in the
canon-evaluation sections were verified in-repo this session (see PR notes).
