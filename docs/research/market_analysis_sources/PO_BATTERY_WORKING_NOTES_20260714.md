<!-- Complete po-battery working notes (operator by operator, provocation by
provocation, >=2 named movement techniques per provocation) for the run whose
generator output is PO_BATTERY_RUN_20260714.txt (seed 20260714, random word
"beehive"). Committed in full per the charter rule that po coverage is never
sampled down (PR #15 precedent). Provocations are stimuli, never facts; the
harvest (H1-H16) is the only thing that feeds convergent documents.
Movement technique key: PRIN = extract a principle · DIFF = focus on the
difference · MOM = moment-to-moment simulation · POS = positive aspects ·
SPEC = special circumstances.
Compiled 2026-07-14. -->

# Po battery working notes — PR-aggregator venture statement

**Target statement:** "A standalone product ingests corporate press releases and disclosures per entity, builds point-in-time timelines, and sells diff-style analysis (what's new, changed, unanswered, promised-but-undelivered) plus a machine-readable promise ledger to investors, consultants, and policy makers."

## STEP 0 — Assumptions surfaced

A1 documents are the unit of analysis · A2 the company is the aggregation axis · A3 customers want analysis of what companies SAY · A4 one-directional pipeline (ingest → analyze → sell) · A5 the reader is the customer · A6 companies are passive subjects · A7 text is the medium · A8 self-comparison (entity vs its own past) · A9 subscription software is the wrapper · A10 point-in-time correctness matters · A11 we sell insight (not data, not standards).

## P1 ESCAPE — negate each assumption

- **Po A1-neg: documents are not the unit.**
  - PRIN: the durable unit is the smallest thing whose truth can later be checked → a *claim*. Implementable: claim-level primary keys with lifecycle states (made → reiterated → modified → fulfilled / broken / silently dropped). → **H1**.
  - DIFF: a claim registry can notice a promise *disappearing* between releases — document diffs cannot say "this commitment was quietly dropped." The difference IS the product's headline feature.
- **Po A2-neg: the company is not the axis.**
  - PRIN: promises are made by people; accountability follows the promiser. → executive-level credibility graph across companies, built from public officer-change records. → **H2**.
  - SPEC: exactly right when a serial CEO/CFO moves — PE diligence and board searches pay per-project for precisely this person-level history.
- **Po A3-neg: customers don't want what companies say.**
  - DIFF: the provoked world analyzes what companies DO. Adoptable difference: pair each claim with observable behavior streams (8-K actions, hiring, capex, permits) — say-vs-do cross-examination. → **H3**.
  - POS: taken straight, behavior data is harder to game than language — a robustness answer to LLM-polished disclosures.
- **Po A4-neg: the pipeline is not one-directional.**
  - MOM: simulate the loop — issuer reads its own ledger entry, disputes a verdict, supplies evidence; the dispute is displayed (never hidden), confidence updates. That minute-by-minute loop is an issuer right-of-reply / verified-issuer program. → **H4**.
  - PRIN: two-sided data flows compound trust; the subject's participation is evidence, not contamination, if gated.
- **Po A5-neg: the reader is not the customer.**
  - PRIN: whoever bears the cost of a broken promise is a customer — issuers themselves (reputation), insurers/underwriters (D&O), litigants. Multiple doors on one corpus.
  - SPEC: when federal disclosure mandates retreat (current US posture), litigation/enforcement buyers grow — the counter-cyclical customer.
- **Po A6-neg: companies participate.**
  - POS: voluntary claim registration by issuers (pre-flight, badges) creates supply-side network effects no scraper has. Converges with H4/H5.
  - DIFF: participating issuers get faster corrections; the ledger differentiates verified vs unverified issuers — a trust tier, not a paywall.
- **Po A7-neg: text is not the medium.**
  - PRIN: claims live wherever executives speak — earnings-call audio, interviews, social posts (often less lawyer-scrubbed). Phase-2 expansion sources ranked by signal-per-cost.
  - MOM: an exec's off-script conference remark contradicts the 10-K → cross-medium contradiction alert; operationally needs transcript licensing — noted as a licensed-source decision (R-016 class).
- **Po A8-neg: not self-comparison.**
  - DIFF: compare across entities — five companies claiming #1 market share cannot all be right. Intra-sector contradiction detection. → **H11**.
  - POS: cross-entity contradictions are inherently newsworthy — organic distribution.
- **Po A9-neg: not subscription software.**
  - PRIN: if the asset is a ledger, monetize like data/standards businesses: API metering, index licensing, per-matter dossiers. → **H12** + consultant dossier SKU.
  - SPEC: standards bodies monetize reference implementations — see P7 waggle-dance schema (H13).
- **Po A10-neg: point-in-time doesn't matter.**
  - POS (of the negation failing): the strongest confirmation in the battery — without as-of-known-when discipline the product is useless for backtesting and unsafe for verdicts. Elevates point-in-time from feature to invariant.
  - PRIN: never let a later edit silently overwrite what was known earlier — same invariant as 1Live's disputed-shown-never-hidden.
- **Po A11-neg: we don't sell insight.**
  - DIFF: sell the *organized substrate* and let customers think (founder's stated positioning) — machine-readable feeds first, narratives second.
  - MOM: an analyst's agent calls "what changed for $TICKER since March" mid-meeting; the answer is a data payload, not an essay. API-first surface confirmed.

## P2 REVERSAL / INVERT / OPPOSITE

- **Po: investors are ingested; the product analyzes the readers.**
  - PRIN: track predictions/claims made by analysts and pundits — a sell-side credibility ledger. Adjacent product; defer (conflicts with neutrality at launch).
  - DIFF: attention analytics (which claims get scrutinized) sellable to IR — flagged with privacy caution; parked.
- **Po: the diff writes the press release.**
  - MOM: comms drafts a release; the engine flags "this drops the Q3 date you promised in April; the market will ask X" BEFORE publication. That is a pre-flight linter for IR — same engine, reversed direction, zero new data. → **H5**.
  - POS: sells into an existing budget (comms/IR tooling) without waiting for reader-side scale.
- **Po: policy makers issue; companies analyze.**
  - PRIN: the engine is subject-agnostic — agencies, regulators, politicians can be entities in the same ledger. TAM expansion with explicit neutrality guardrails. → **H6**.
  - SPEC: right when procurement or civic funders want government-promise accountability; wrong as a launch wedge (political exposure).

## P3 EXAGGERATION

- **Po 10,000× up: every sentence ever uttered by every company, diffed in real time.**
  - PRIN: exhaustiveness as an explicit SLO. Implementable at sector scope: "we miss nothing in <beachhead sector>" — coverage guarantees beat breadth. Feeds §13 sequencing.
  - MOM: a missed release in the guaranteed sector = incident + postmortem; coverage SLO becomes an operating discipline, not marketing.
- **Po 1/10,000 down: one claim per company per year.**
  - PRIN: extreme selectivity = editorial materiality — the three load-bearing promises per company. Directly answers the category's #1 complaint (noise). → **H7**.
  - DIFF: the provoked product sends almost nothing — and is trusted BECAUSE of it. Alert budget as a product principle.

## P4 DISTORTION (time/dependency scramble)

- **Po: the analysis exists before the release.**
  - MOM: Tuesday 9am, the model expects ACME's habitual mid-July trial update; nothing arrives; Thursday the "overdue disclosure" alert fires; the stock reacts to silence days later. Silence as signal → expected-disclosure calendar + overdue alerts. → **H8**.
  - PRIN: absence is data when cadence is modeled — nobody in the competitive scan ships this.
- **Po: fulfillment is recorded before the promise.**
  - PRIN: retrodiction — backfill decades of promises whose outcomes are already known; the archive calibrates verdicts before any live claim is scored. → **H14** and §12 (converged independently with the founder's historical-data directive — triangulation signal).
  - POS: launch-day content ("20 years of receipts") instead of cold-start emptiness.

## P5 WISHFUL

- **Po: every claim self-reports when it dies.**
  - PRIN: claims carry parseable due-dates ("by Q3", "next year") → automatic expiry; the ledger ticks like a bond maturity calendar. → **H9**.
  - MOM: Monday digest — "7 promises come due this week across your watchlist" — a recurring engagement loop that writes itself.
- **Po: a perfect truth oracle grades every promise.**
  - DIFF: since no oracle exists, verdicts must carry graded confidence — transplant 1Live's 4-state model (unverified/likely/confirmed/disputed) onto fulfillment status. → **H10**.
  - SPEC: legally load-bearing — a graded, evidence-linked verdict is defensible where a binary "broken promise" stamp is defamation-adjacent.

## P6 ABSURD

- **Po: press releases sue each other in claim court.**
  - PRIN: adversarial pairing — every new release cross-examined against the issuer's own record AND against competitors' incompatible claims. → **H11** (reinforces P1 A8-neg).
  - POS: "the claim court docket" is a natural content/media artifact.
- **Po: the ledger IS the company (tradable reputation).**
  - PRIN: a credibility score robust enough to be licensed as an index input (insurers, lenders, index providers). Long-run monetization, only after golden-set precision is proven. → **H12**.
  - SPEC: right when years of verdict history exist; wrong early — sequencing note recorded.

## P7 RANDOM ENTRY — "beehive"

Associations: hive mind · hexagonal cells · honey (stored value) · waggle dance (compressed direction-encoding) · queen/workers/drones · swarming · pollination · stings · smoke (keeper calms hive).

- **honey →** the ledger compounds like stored honey; depth-of-history is the scarce good → history-depth pricing tiers; archive as moat. → **H14**. (PRIN: price the vintage, not the tap. POS: aligns price with the hardest-to-copy asset.)
- **waggle dance →** a bee encodes direction+distance in a standard dance → encode every claim in a compact standard schema (metric, target, date, confidence, provenance) — an open "promise markup," the iCal of corporate promises; standard-setting as moat, MCP-native. → **H13**. (PRIN: whoever defines the encoding owns the ecosystem. DIFF: competitors ship documents; we ship a format.)
- **pollination →** foraging fertilizes other fields → our extraction fertilizes customers' own AI platforms; API/MCP-first confirmed from a second direction. (POS + DIFF.)
- **swarming →** colonies split at scale → per-sector replication playbook with sector-tuned taxonomies; expansion pattern, not launch concern. (PRIN, SPEC.)
- **stings →** defense mechanism → legal posture: never verbatim republication; productized "we say only what the receipts show" + counsel review of verdict language. (PRIN, SPEC.)
- **queen →** single reproductive source → the extraction taxonomy/prompt is the queen: versioned, golden-set-guarded, changed only through gates (Descriptor Foundry pattern reused). (PRIN, MOM: a taxonomy change re-scores history → version pinning required.)
- **smoke →** keeper calms the hive → the right-of-reply loop (H4) de-escalates adversarial issuer relations; corrections policy as smoke, not war. (POS, DIFF.)
- **hexagons →** most efficient packing → entity resolution on open identifiers (LEI/CIK) — no proprietary-ID tax; schema efficiency as a design value. (PRIN.)

## P8 RANDOM × OPERATOR COMBOS (apply the operator to the beehive associations, map back)

- **P8.1 random+ESCAPE — po: a hive without a queen.**
  - PRIN: a ledger without an editorial center → community-maintained corrections, Wikipedia-style, through gated verification. Parked: moderation cost vs trust; revisit at scale. (SPEC: right if the ledger becomes a commons/public-good product per H15's civic angle.)
- **P8.2 random+REVERSAL — po: the flowers visit the bees.**
  - DIFF: issuers come TO the registry — voluntary claim registration, verified-issuer onboarding. Third independent arrival of the issuer-side door (with P2 and P1 A6-neg) — strongest convergence signal in the battery. → **H4/H5** weighting raised in §9.
- **P8.3 random+EXAGGERATION — po: ten thousand hives.**
  - PRIN: personal micro-ledgers — every analyst's watchlist is their own hive with custom alert budgets. Standard SaaS personalization; noted, not novel. (POS.)
- **P8.4 random+DISTORTION — po: honey before flowers.**
  - PRIN: seed sector taxonomies top-down from analyst frameworks BEFORE ingesting, then let bottom-up extraction refine — hybrid taxonomy build order. Feeds the beachhead build plan. (DIFF: pure bottom-up taxonomies converge slowly; pre-seeding accelerates golden-set convergence.)
- **P8.5 random+WISHFUL — po: bees that never die.**
  - MOM: a claim from 2009 still open in 2026 surfaces in "oldest unfulfilled promises in the index" — the zombie-promise report; content marketing that demonstrates archive depth. → **H15**. (POS.)
- **P8.6 random+ABSURD — po: the hive writes reviews of the flowers.**
  - PRIN: the product grades issuers' communication integrity (clarity, specificity, follow-through) — Morningstar-of-disclosure ratings; combines H2+H7; gated behind proven precision. → **H16**. (SPEC: right only after golden-set precision + a defensible methodology doc; wrong at launch.)

## HARVEST

H1–H16 as tabulated in `PR_AGGREGATOR_MARKET_ANALYSIS.md` §8 — each traceable to the provocations above. Convergence notes: the issuer-side door arrived independently three times (P1, P2, P8.2); the archive-as-cold-start arrived twice (P4, P7-honey) and matched a founder directive issued mid-session. Divergent material ends here; everything downstream passes through the normal convergent gates.
