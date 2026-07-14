# Disclosure-Intelligence Market Analysis — PR Aggregator / Promise Ledger Venture

**Date:** 2026-07-14 · **Status:** RESEARCH (standalone new-venture analysis; multibagger is context + prospective customer #1, not a required integration) · **Session Contract:** #6 (STATE.md) · **Companion doc:** `PR_AGGREGATOR_RESEARCH.md` (sources, licensing, legal posture — R-013 still gates any spend)

**Provenance (applies to every number in this document):** compiled from eight single-pass research-agent reports committed in `market_analysis_sources/` (files A–H; agent report bodies preserved verbatim — the only non-agent text is the editorial header on each file and, in appendix C, one explicitly-marked ADDITIVE editor REFUTED-verdict on a time-incoherent citation with the original content preserved in place, see §15), gathered via web search from this sandbox (direct vendor-page fetches largely blocked by egress policy). Each figure below carries its appendix letter; confidence labels are stated where the underlying report flagged them. Nothing here is adversarially verified to the companion report's 3-vote standard, and analyst-firm market-size figures for niche segments disagree by up to 10x — ranges are shown, not point estimates. **Treat this as directional research only — not contract-grade, not spend-grade.** The de Bono section is explicitly divergent material: provocations are stimuli, never facts (charter rule); only the harvest table feeds the convergent sections, and everything converges through the normal gates before any build.

---

## 1. Executive summary

*(Every bullet below inherits the provenance caveat above: single-pass, directional research — not adversarially verified, not contract- or spend-grade.)*

1. **The market is large, growing, and consolidating upward.** Financial market data/analysis spend hit **$49.2B in 2025 (+6.5%, Burton-Taylor)** [A]. The AI-research-platform tier is growing far faster than the ~6.5% overall market — AlphaSense went ~$350M → **$600M+ ARR** in ~18 months and raised at **$7.5B** (June 2026), and venture capital is concentrating there [A] — though no committed evidence ranks every market slice, so "fastest" is not claimed. General LLMs are not killing specialized platforms — they're commoditizing undifferentiated work while value migrates to proprietary corpora, provenance, and workflow [D].
2. **A genuine pricing chasm exists between $6k and $15k/seat.** Prosumer tools top out near $6k/yr; institutional platforms start near $15–25k. ~6,500 sub-$250M funds, 16,544 RIAs, and ~9,000 family offices live in that chasm [B]. No direct occupant serving them disclosure intelligence at a mid-four-figure price was found in this pass.
3. **The #1 and #2 complaints about the category leader are noise and price** — "noisy search results top the complaint list"; alerts produce "a lot of noise" [B]. No incumbent markets longitudinal claim-tracking or alert *precision*. The complaint data independently confirms the promise-ledger thesis.
4. **The distribution layer is being captured by AI assistants.** Between mid-2025 and mid-2026, FactSet, S&P/Kensho, LSEG, Moody's, Morningstar, Daloopa, and Fiscal.ai all shipped MCP servers; Anthropic and OpenAI now run finance-connector storefronts [C][D]. Agent-reachability is table stakes; **the differentiated payload is pre-verified, source-linked change events** — exactly what a diff engine produces and what agents can't cheaply reconstruct per-run [C].
5. **The newswire layer is financially fragile** (Cision at Caa1 after a distressed exchange; Notified sold; EQS taken private) and drowning in AI slop (~24% of wire releases already LLM-assisted; 62.5% of crypto releases tied to high-risk projects) [F]. Verification, dedup, and trust-scoring of corporate communications is a monetizable feature with no C2PA-style occupant for text [F].
6. **Regulatory clock favors moving now:** earnings press releases remain untagged/unstructured in the US with no rule proposed (3–5 years of durable NLP-extraction value), while LEI becomes the mandated cross-agency entity key (FDTA, effective Oct 2026) — adopt LEI as the native entity ID from day one. ESAP (July 2027) will commoditize raw EU collection; differentiation must sit above collection [E].
7. **The accountability demand is real and moving to courts:** greenwashing/AI-washing enforcement (DWS €25M, ASIC penalties, SEC AI-washing actions) needs dated statements matched to outcomes — the ledger's output — even as US mandatory-disclosure rules retreat [H].
8. **Whitespace verdict (detail §10):** press-release-level, entity-resolved longitudinal analysis had **no occupant found in this pass**; promise-tracking is **adjacent-occupied** (Marvin Labs, earnings-guidance-scoped); the strongest openings are the say-vs-do ledger across ALL corporate communications, silence/overdue-promise detection, machine-readable change-event feeds for agents, and the govtech/accountability buyer — plus an IR-side "pre-flight" reverse mode that reuses the same engine.
9. **Historical data is the entry weapon (founder directive, §12):** EDGAR full-text since 2001, CC-NEWS since 2016, and Wayback-archived IR pages allow launching with a decades-deep, point-in-time promise ledger already populated — content no fast-follower can honestly reproduce without repeating the archaeology.

## 2. Market definition & segmentation

**Product-market:** "disclosure intelligence" — software/data products that collect corporate communications (filings, press releases, transcripts, IR pages) and sell organized access, analysis, or feeds. We segment it in three planes:

**By layer (value chain position):**
| Layer | What's sold | Examples | Gross-margin character |
|---|---|---|---|
| L1 Distribution | Issuers pay to disseminate | PR Newswire, Business Wire, GlobeNewswire | Squeezed; PE-owned; per-release $175–$8,700 [A][F] |
| L2 Collection/normalization | Raw aggregated content, feeds | Benzinga, RTPR, news APIs; free: EDGAR/ESAP | Commoditizing (regulators give it away) [E] |
| L3 Analysis/insight | Search, summarization, diffs, scores | AlphaSense, Quartr, Hudson Labs, Marvin Labs | Where the margin lives; ARR/customer rising [A][D] |
| L4 Workflow/agents | Analyst workflows in customers' tools | MCP connectors, Claude/ChatGPT finance storefronts | Emerging; distribution-controlled by AI vendors [C] |

**By buyer (WTP bands from [B], full table in appendix B):**
| Segment | Population | WTP band | Today's spend goes to |
|---|---|---|---|
| Large buy-side | ~551 $1B+ hedge funds + big AMs | $30–90k/analyst stack | Bloomberg, FactSet, AlphaSense |
| **Small funds / RIAs / family offices** | ~6,500 small HFs + 16,544 RIAs + ~9,030 FOs | **$1–6k/seat — then a gap to $15k** | Koyfin, TIKR, spreadsheets |
| Prosumer investors | 100k's paying | $180–1,200/yr (ceiling ~$299 mass) | Seeking Alpha, Fiscal.ai |
| Consultants | 46% of the ~$3B expert-network spend | $20–200k per project | AlphaSense, expert networks |
| Policy/gov-affairs | ~3,500 orgs observable (FiscalNote) | $8–15k/seat, ~$24k/org | FiscalNote, Politico Pro, BGOV |
| Regulators (corporate-claims monitoring) | pilots only (ACM, DGCCRF, JRC, KEITI; SEC in-house) | no commercial market yet | in-house SupTech [B][G] |
| IR/comms (the flip side) | 70% of S&P 500 already buy monitoring | $6–25k monitoring; $10–40k IR platforms | Meltwater, Cision, Quartr Pro |
| Quant/AI-platform feed buyers | systematic funds + agent builders | free→$50k APIs; $100–200k+ premium feeds | RavenPack, Bloomberg EDF, Benzinga |

**By jurisdiction:** US (EDGAR-rich, free) → UK/EU (NSM now, ESAP 2027) → JP (EDINET free API; TDnet iXBRL from July 2026) → rest (license-gated) [E, companion doc §5].

## 3. Market size & structure

- **Anchor:** $49.2B total financial market data/analysis spend, 2025, +6.5% — the only institutional-grade number in this space (Burton-Taylor) [A]. Bloomberg ~33% share; Bloomberg+LSEG ≈ half [A, 3rd-party-derived].
- **Our addressable slice is not the anchor.** Bottom-up from buyer bands [B]: (a) underserved-tier disclosure intelligence: ~30k orgs (small funds+RIAs+FOs) × $2–6k = **$60–180M/yr** attainable-market ceiling in the chasm alone; (b) IR-side monitoring: US-listed issuers (~4,000–5,000 companies) × $10–25k/org ≈ a **$40–125M/yr pool** for listed-issuer comms monitoring alone — and the observable spend is real, not hypothetical: Meltwater's revenue is ~$460M+ and Cision's in the $600–830M range across all monitoring customers [A] — money already flowing to worse-fitting tools; (c) agent-feed tier: free→$50k→$150k pricing anchors exist (Benzinga/RavenPack) [B]. A $5–15M ARR business requires low-thousands of customers across these — no heroic share assumptions.
- **Momentum evidence at the analysis layer:** AlphaSense $600M ARR / $7.5B; Daloopa $47M Series C (May 2026); Fiscal.ai $10M Series A with a $990/yr API+MCP SKU; Fintool acquired by Microsoft (Apr 2026); Rogo doubling valuation in 9 months [A][D]. Capital is flowing specifically toward AI-native, feed/agent-positioned disclosure products.
- **Counter-evidence / sober notes:** Koyfin — 500k users, est. only ~$3.9M ARR [B, LOW-MED confidence] — shows bottom-of-market usage doesn't monetize itself; FiscalNote collapsed to an ~$8.6M market cap on ~$88M revenue [A] — policy-monitoring seats alone are not a durable business; niche "competitive intelligence" market sizings disagree 10x and shouldn't be used for planning [A].

## 4. Five forces (disclosure-intelligence analysis layer)

| Force | Reading | Basis |
|---|---|---|
| Supplier power (content) | **Falling structurally** — regulators keep making the raw substrate free and structured (EDGAR, ESAP, NSM, EDINET; LEI as join key), and wires' distress limits their leverage; BUT commercial wire full-text remains license-gated (Benzinga/RTPR terms) | [E][F], companion §3 |
| Buyer power | High in enterprise (procurement, compliance packs demanded [G]); low-moderate in the underserved tier (no alternatives between $6k and $15k) | [B][G] |
| New entrants | **High threat at the summarization layer** (frontier models + free EDGAR = zero-marginal-cost competitor); LOW at the longitudinal-archive layer — time-indexed corpora and change-detection ground truth can't be back-filled honestly after the fact | [D] |
| Substitutes | ChatGPT/Claude + web search for one-off questions; internal bank AI suites (JPM 200k seats) for big institutions — both commoditize single-document work, neither maintains a persistent, auditable claim ledger | [D] |
| Rivalry | Consolidating upward (AlphaSense rollup; Microsoft buying Fintool; point tools → platforms); a live SEC-diff *microcategory* is forming (EDGAR Analyst, FilingsIQ, StoxPulse, Brightwave) — filings-scoped, US-scoped, no press releases, no promise semantics | [D] |

**Structural conclusion:** the defensible position is L3 analysis anchored on an L2 asset that is free-to-acquire but expensive-to-organize (the longitudinal, entity-resolved, point-in-time archive), delivered through L4 pipes we don't own but can be best-in-class inside.

## 5. Competitive landscape

(Composite of companion doc §8 and appendices A/B/D — pricing reported, unverified.)

**Tier 1 — platform incumbents:** AlphaSense ($7.5B val, $600M ARR, Blacklining = filings-pair redline, Deep Research agent), Bloomberg (~$10B rev, AI doc-analysis shipped, no MCP — walled garden), FactSet/S&P/LSEG/Moody's (all MCP-shipped, data-first). None do press-release-level longitudinal promise semantics. Their economics (ARR/customer $28k→$66k at AlphaSense [D]) prove enterprises pay for verified, citable coverage.

**Tier 2 — AI-native challengers:** Quartr (calls/docs, API-first), Hudson Labs (forensic red flags + "what changed before earnings"), Daloopa (source-linked fundamentals, MCP), Fiscal.ai (prosumer + $990/yr API/MCP), Rogo/Hebbia/Brightwave (AI-analyst workflows). Closest DNA to ours: Daloopa's "every datapoint hyperlinked to source" — but for numbers, not claims.

**Tier 3 — the diff microcategory:** EDGAR Analyst, FilingsIQ.ai, StoxPulse, Last10K, BamSEC Compare, Visualping-class monitors. All document-pair, filings-only, US-only, no entity timeline, no promise lifecycle, no "unanswered" layer.

**Tier 4 — promise-tracking adjacents:** **Marvin Labs** (guidance promises vs delivery, ~$89/mo, earnings-comms-scoped — the direct precedent), **Paragon Intel ManagementTrack** (0–10 *executive* rating from ~50 career datapoints across ~5,000 execs, launched May 2024, vendor-claimed +8%/yr long-short backtest — the closest occupant to a people-level credibility score) [H], FinCatch (early), Visible Alpha (guidance numbers), Hudson Labs (fraud-level risk scores), Net Zero Tracker/ChatNetZero (climate-only). Appendix H's synthesis: neighbors exist at people-level, fraud-level, and number-level, but **no major occupant selling language-level promise-fulfillment tracking was found in this pass** — the general corporate-promise ledger appears unclaimed [companion §8][H].

**Tier 5 — the flip side:** Meltwater/Cision (media monitoring, hated contracts — "deceptive auto-renewal… truly awful customer service" is a *recurring* review theme [B]), Quartr Pro/Notified/Irwin for IR. Transparent pricing + easy exit is itself a differentiator against this tier.

**Positioning map (verbal):** on axes of *document-pair ↔ longitudinal-ledger* and *filings-only ↔ all-communications*, the upper-right quadrant (longitudinal × all-communications, with machine-readable output) is empty. Marvin Labs sits longitudinal × earnings-guidance; AlphaSense/diff-microcategory sit document-pair × filings; wires/monitors sit neither.

## 6. Buyer analysis — what the evidence says they'll pay for

1. **Enterprises pay for verified completeness, not summaries** (AlphaSense ARR/customer trajectory [D]; FINRA/procurement demanding model-governance packs [G]) → ship accuracy SLAs, eval results, provenance logs as sales assets.
2. **The chasm tier pays $1–6k and is starved** [B] → a $99–299/mo disclosure-intelligence seat with honest coverage guarantees has no direct competitor.
3. **Consultants buy by project** ($20–200k DD budgets [B]) → per-entity "disclosure-integrity dossier" as a transactable SKU, not a seat.
4. **Policy buyers exist but the segment alone is a trap** (FiscalNote's collapse [A]) → serve them through the same platform, never build only for them; note the *regulator/state-AG/litigant/journalist* accountability demand rising as federal datasets destabilize [G].
5. **Agent builders pay three price anchors** (free tier → $10–50k mid → $100k+ premium [B]) → freemium MCP with metered depth is the proven ladder (Fiscal.ai's $990/yr shows the low rung works).
6. **IR teams already pay $6–25k for monitoring they dislike** [B] → the reverse-mode product (§9 H5) lands in an existing budget line with a better-fitting tool.

## 7. Trends & discontinuities (3–5 year)

1. **Agent-native delivery becomes the default pipe** — MCP donated to Linux Foundation, every major data vendor shipped a server in 12 months; deep-research agents re-derive state each run, making a persistent diff/change stream the natural memory layer they'll pay to call [C].
2. **Model vendors move up-stack** — Anthropic's finance agent templates, OpenAI in Excel; generic summarization inside the assistant is free within 1–2 years. Never compete there [C][D].
3. **Disclosure infrastructure structures slowly but surely** — earnings PRs stay unstructured in the US (no rule even proposed) while Japan tags them from July 2026 and ESAP centralizes the EU from 2027; a diff engine spanning text-level (today) and tagged-fact-level (tomorrow) rides the whole curve. LEI is the mandated entity key — build on it natively [E].
4. **The wire layer melts** — PE distress, subscription pivots (ACCESS $1–2.5k/mo), issuer bypass to IR-site-first disclosure; content that leaves the wires becomes exactly what only IR-page/EDGAR monitoring catches [F].
5. **AI slop makes provenance the product** — ~24% of releases LLM-assisted; verified-source badges shipping (CLEAR Verified) but no cryptographic/C2PA occupant for text disclosures; fake-release enforcement actions (Getty) prove the harm [F][G].
6. **Regulation nets out as tailwind with one dated obligation** — EU AI Act Art. 50 (Aug 2, 2026): machine-readable marking + disclosure of AI-generated text, €15M/3% exposure — build the marking in now; it doubles as the provenance feature. SEC punishes AI *overclaiming*, not AI use; a product that anchors every claim to the primary document is structurally the safe design [G].
7. **Independent timestamped archives gain civic value** as public datasets are altered/removed and FOIA capacity degrades — accountability demand migrating to states, litigants, journalists [G].
8. **LLM homogenization is degrading naive text-diffing** — FY2024+ filings show measurable shifts toward templated, LLM-drafted language, and LLM rewriting can inflate tone past standard sentiment detectors [H, medium/low confidence]. Surface-text diffs and tone scores decay as signals; *semantic claim-level* diffing (entity-resolved promises with deadlines) is the robust design — and conveniently is the product thesis. The academic base also deepened post-Lazy-Prices: risk-factor additions/removals move variance risk premia (Accounting Review 2023), GPT-based disclosure analysis beats median analysts on earnings direction, and CEOs measurably increase promising after misses [H].
9. **The accountability buyer is shifting from compliance to litigation/consumer law** — SEC climate rule heading to rescission and the ESG task force disbanded, while courts and national enforcers deliver: DWS fined €25M (2025), ASIC's three greenwashing penalties (A$10.5–12.9M), KLM/Lufthansa rulings, EU Empowering Consumers Directive live Sep 2026, and SEC "AI-washing" actions generalizing claims-vs-reality enforcement beyond green [H]. Dated public statements matched to subsequent facts — the ledger's exact output — is what litigators, prosecutors, NGOs, and D&O underwriters need; "anything-washing" broadens the TAM beyond one regulatory cycle.

## 8. de Bono divergent pass (po battery — full canon)

Run per `docs/skills/po_provocation.md` with `tools/po_battery.py --seed 20260714`, random word **"beehive"**, all operators P1–P8.6, ≥2 movement techniques per provocation. The generator's complete output (the prompt battery) is committed at `market_analysis_sources/PO_BATTERY_RUN_20260714.txt`, and the **complete per-provocation working notes — every operator P1–P8.6, every provocation, ≥2 named movement techniques each — are committed at `market_analysis_sources/PO_BATTERY_WORKING_NOTES_20260714.md`**. This section presents the condensed view; the committed notes are the auditable full record (coverage never sampled down, per the PR #15 precedent). **Everything in this section is stimulus, not fact.** Full working notes condensed; the harvest table is what feeds §§10–11. M6 ledger row recorded.

**Step 0 assumptions surfaced:** documents are the unit · the company is the axis · customers want what companies *say* · one-directional pipeline · reader is the customer · companies are passive subjects · text is the medium · self-comparison only · subscription software is the wrapper · point-in-time matters · we sell insight.

Condensed highlights below (the full per-provocation record is in the committed working notes):

- **P1 escape** ("po: documents are not the unit") → claims are first-class objects with lifecycle states: made → reiterated → modified → fulfilled / broken / **silently dropped**.
- **P1 escape** ("po: the entity is not the axis") → credibility follows *executives* across companies — a career-spanning management promise-keeping graph from public officer-change records.
- **P1 escape** ("po: they don't want what companies say") → pair every claim with observable *behavior* streams (8-K actions, hiring, capex, permits): say-vs-do cross-examination.
- **P2 reversal** ("po: the diff writes the press release") → run the engine in reverse pre-publication: an IR "pre-flight linter" that tells the issuer what the market will flag as changed/unanswered — second market, zero new data.
- **P2 reversal** ("po: policy makers are the entities") → agencies/politicians in the same ledger; the engine is subject-agnostic.
- **P3 exaggeration-down** ("po: one claim per company per year") → materiality editorial: surface only the 3 load-bearing promises per company — the direct answer to the category's #1 complaint (noise).
- **P4 distortion** ("po: the analysis exists before the release") → **silence detection**: model each entity's expected disclosure cadence; overdue = signal. "What's unanswered" becomes an *alert*, not a footnote.
- **P4 distortion** ("po: fulfillment recorded before the promise") → the archive is the cold start: backfill decades of promises so day-one has receipts (→ §12, converges with founder directive).
- **P5 wishful** ("po: every claim self-reports when it dies") → parse due-dates from claim language ("by Q3") → a promise **maturity calendar** that ticks like a bond ladder; "promises coming due this week" digest.
- **P5 wishful** ("po: perfect truth oracle") → fulfillment verdicts carry the OneLive 4-state confidence model (unverified/likely/confirmed/disputed), never binary.
- **P6 absurd** ("po: press releases sue each other") → intra-sector contradiction detection (five companies claiming #1 share can't all be right) — cross-entity insight and a media hook.
- **P7 random 'beehive'** (honey = stored value → history-depth pricing tiers; waggle dance = compressed direction-encoding → an **open claim schema** — metric, target, date, confidence — "iCal for corporate promises," standard-setting as moat; stings → never-verbatim legal posture; queen → the extraction taxonomy is versioned + golden-set like Descriptor Foundry).
- **P8.2 random+reversal** ("po: flowers visit the bees") → issuers voluntarily register claims (verified-issuer program) — triangulates with the IR pre-flight from P2: the second side of the market keeps arriving independently, a convergence signal.
- **P8.5 random+wishful** ("po: bees never die") → zombie-promise reports: the oldest unfulfilled promises in the index — content marketing that writes itself.
- **P8.6 random+absurd** ("po: the hive reviews the flowers") → disclosure-integrity **ratings** per company (clarity, specificity, follow-through) — a Morningstar-of-communication-integrity layer.

**Compact Six Hats check on the venture (de Bono, convergent-side):** *White:* the verified facts are the EDGAR backbone, Lazy-Prices validation, the noise complaint, the $6–15k chasm. *Red:* the promise-calendar and zombie-promise surfaces feel immediately compelling; the govtech pull feels real but slow. *Black:* extraction precision on forward-looking language is the single existential risk — a wrong "broken promise" verdict is defamation-adjacent; incumbents can bolt on diffing; wires may lock licensing. *Yellow:* the same engine sells to readers, issuers, and agents — three revenue sides on one corpus. *Green:* the harvest below. *Blue:* run precision evals before any public verdict; ship confidence states; stage buyers chasm-first.

**Harvest table (traceable; feeds §§10–11):**

| # | Idea | Provocation | Disposition |
|---|---|---|---|
| H1 | Claim registry with lifecycle states (incl. silently-dropped) | P1 | Core architecture |
| H2 | Executive-level credibility graph across companies | P1 | Differentiator; PE/board-DD adjacency |
| H3 | Say-vs-do evidence pairing | P1 | Insight depth; phase 2 |
| H4 | Issuer right-of-reply + verified-issuer program | P1/P8.2 | Trust + network effect |
| H5 | IR pre-flight linter (reverse mode) | P2 | Second market, zero new data |
| H6 | Government/agency promise ledger | P2 | TAM expansion; neutrality guardrails needed |
| H7 | Materiality editorial ("3 promises that matter") | P3 | Anti-noise positioning |
| H8 | Silence detection / expected-disclosure calendar | P4 | Novel alerting; no occupant found |
| H9 | Promise maturity calendar (due-date parsing) | P5 | Engagement loop |
| H10 | 4-state confidence on fulfillment verdicts | P5 | OneLive DNA reuse; legal safety |
| H11 | Intra-sector contradiction detection | P6 | Viral analytics; phase 2 |
| H12 | Credibility index licensing | P6 | Long-run monetization |
| H13 | Open claim schema ("promise markup") + MCP-native | P7 | Standard-setting moat |
| H14 | History-depth pricing; archive as cold start | P7/P4 | Pricing + GTM (→ §12) |
| H15 | Zombie-promise reports | P8.5 | Content marketing |
| H16 | Disclosure-integrity ratings | P8.6 | Combines H2+H7; ratings moat |

## 9. Revisit — what the divergent pass changes about the analysis

Re-reading §§2–7 with the harvest in hand, four upgrades to the original framing:

1. **The product is a *ledger with three doors*, not a feed with readers.** Investors read it (§6.1–2), issuers answer to it and pre-flight against it (H4/H5, landing in an existing $6–25k IR budget line [B]), and agents call it (H13, [C]). The same corpus monetizes three ways; the original analysis under-weighted the issuer door.
2. **"What's unanswered" is the differentiated alert, not a report section.** Silence detection (H8) directly attacks the category's documented #1 complaint (noise) by alerting on *absence* — high signal, low volume — something search-index incumbents structurally can't do without cadence models per entity.
3. **The claim schema is a standards play.** If the open promise-markup format (H13) becomes what agent builders consume, the moat isn't only the archive — it's being the reference implementation of the format (the "iCal of corporate promises"), reinforced by the MCP-storefront distribution wave [C].
4. **People, not just companies** (H2): officer-level promise history survives ticker changes, mergers, and rebrands — harder to replicate than entity timelines and uniquely valuable to PE/board/DD buyers who pay by project [B].

## 10. Whitespace map

| Whitespace | Occupancy today | Evidence | Attack |
|---|---|---|---|
| Longitudinal all-communications promise ledger | **No occupant found in this pass** (Marvin = earnings-guidance only) | companion §8; [D] microcategory is filings-pair | Core product |
| Silence/overdue-disclosure alerting | No occupant found in any pass | [B][D] | H8; needs cadence models |
| Cross-jurisdiction normalized disclosure timeline (US+EU+UK+JP) | No occupant found in this pass; ESAP will hand out raw EU pieces free in 2027 | [E] | LEI-native entity graph now, ESAP as planned supply |
| Machine-readable change-event feed for AI agents | Emerging demand, no claim-semantics occupant (Daloopa = numbers) | [C] | MCP-first + H13 schema |
| Text-disclosure provenance/verification | Badges exist (CLEAR Verified); no cryptographic/cross-source occupant | [F] | "Matches the filed 8-K, verified issuer, unaltered" as a product property |
| The $6–15k/seat chasm | Structurally unserved | [B] | Price the reader seat at $99–299/mo |
| Executive-level promise history (H2) | **Adjacent-occupied**: Paragon MTR rates execs from career datapoints — but not from their promise *language* | [H] | Differentiate on language-level receipts, not biography |
| Litigation/enforcement evidence packs | No commercial occupant; demand demonstrated by DWS/ASIC/KLM outcomes + Sep 2026 EU consumer directive | [H] | Per-matter dossier SKU alongside the consultant dossier |
| Regulator/AG/litigant corporate-claims monitoring | Pilots only; no commercial category | [B][G] | Sell via SupTech/GSA channels later; don't build-for-first |
| IR pre-flight (outbound linting) | Nothing found doing pre-publication diff/unanswered analysis | [B] Tier-5 tools monitor, none lint | H5, phase 2 |
| Disclosure-integrity ratings | Academic indices exist; no commercial Morningstar-of-integrity | [D][G] | H16 after golden-set precision proven |

**Where we can be 10x better, honestly stated:** *content* (decades-deep backfilled ledger vs incumbents' forward-only features), *quality* (point-in-time correctness + 4-state confidence + per-claim provenance vs search-noise), *insight* (promise lifecycle, silence, say-vs-do — semantics nobody ships), *cost* (chasm pricing on a free-substrate corpus). **Where we won't win:** *speed* (sub-second dissemination is a paid arms race — compete on time-to-understanding), raw summarization (free inside assistants within 1–2 years [D]).

## 11. Combinatorial opportunities (the analysis × the harvest)

1. **Ledger × agents (H1+H13+[C]):** the promise ledger exposed as MCP tools ("what changed since X", "claims coming due", "unanswered questions for $TICKER") — the persistent memory layer deep-research agents lack. Three-tier pricing already validated by the market (free → $10–50k → $100k+) [B].
2. **Archive × chasm (H14+[B]):** decades of receipts at a $99–299/mo seat — content depth as the differentiator where incumbents won't drop price.
3. **Engine × issuers (H5+H4+[B] Tier 5):** the same diff engine as pre-flight linter + right-of-reply, sold into the existing (resented) Meltwater/Cision budget line with transparent pricing as the wedge.
4. **Verification × slop crisis (H10+[F][G]):** provenance marking (required by AI Act Art. 50 anyway) + cross-source canonical-text verification = the trust badge for an AI-slop era; regulation turns a compliance cost into the brand.
5. **People graph × consultants (H2+[B]):** executive credibility dossiers priced per-project into $20–200k DD budgets — revenue that doesn't wait for seat-count scale.
6. **Multibagger × everything:** customer-zero consumes the change-event feed (stock engine's missing event-calendar input) and the promise-maturity calendar (catalyst tracking); its retrodiction loop becomes the first golden-set consumer. Standalone product, one committed reference customer.

## 12. Historical-data entry strategy (founder directive: "enter with robust content")

The archive is the cold-start weapon (H14/P4 convergence). Cheapest-viable backfill stack, in build order — all subject to R-013 licensing checks where non-regulatory sources are involved:

1. **EDGAR bulk backfill (free, sanctioned):** full-text-searchable to 2001-05; 8-K EX-99.1/2.02 exhibits = ~25 years of earnings/material press releases for every US issuer; nightly bulk ZIPs are the SEC-preferred bulk path [companion §2]. This alone populates a launch-grade US promise ledger.
2. **CC-NEWS WARCs (compute-cost):** global news/PR text back to Aug 2016; partial coverage accepted; AWS egress/compute budgeted [companion §6].
3. **Wayback Machine IR pages (verify ToS):** archived issuer newsrooms/IR sites recover releases that never hit a wire and capture *as-published-then* text — the point-in-time gold standard for silence-detection baselines. Licensing posture needs its own check before commercial use.
4. **Free international regulators:** EDINET (free API, for-profit reuse reported), NSM (reuse-permissive terms reported), info-financiere (license unconfirmed) — historical statutory disclosures for JP/UK/FR [companion §5, all pending R-013].
5. **Academic corpora as accelerants (verify licenses):** EDGAR-derived research corpora and the Lazy-Prices methodology give pre-built baselines for change-significance scoring [D].
6. **What the backfill yields at launch:** per-entity timelines with 10–25 years of depth; a zombie-promise index (H15) on day one; cadence models for silence detection (H8) trained on real historical rhythm; retrodicted promise→outcome pairs to calibrate fulfillment verdicts before any live claim is scored — the analytics engine is *in motion before entry*, which is exactly the founder's ask.

**Honest constraint:** backfilled non-EDGAR text carries the same reuse rules as live text (store internally, publish re-expressed facts); and historical IR-page archaeology is compute- and QA-heavy — budget it as the venture's main pre-launch cost line.

## 13. Strategic options (why this, not that)

| Option | For | Against | Verdict |
|---|---|---|---|
| A. Broad news aggregator + AI summaries | Fast demo | Zero moat; assistants eat it in 1–2 years [D] | Reject |
| B. SEC-filings diff tool | Cheap, proven demand | Microcategory already crowding [D]; filings-only misses the PR/IR surface | Reject as endgame; fine as internal milestone |
| C. **Promise ledger, chasm-first, agent-native, archive-backed** (per §§10–12) | Empty quadrant; three doors on one corpus; archive moat compounds; customer-zero committed | Slowest to first revenue; extraction precision is existential and must be proven on a golden set first | **Recommended** — gated on R-013 (pricing/ToS re-verification before any provider spend) and R-014 (real EDGAR-seeded golden set before any extraction work); this row is directional research, not a build order |
| D. IR-side pre-flight first | Lands in existing budgets | Sells to issuers before credibility exists with readers; conflicts-of-interest optics at launch | Sequence at phase 2, not entry |

**Recommended beachhead sequencing (framework, founder decides):** one sector (candidate criteria: high PR cadence, promise-dense language, clear fulfillment observables — e.g., biotech catalysts or consumer-tech launches), US-first on EDGAR+IR pages, chasm+prosumer pricing, MCP feed from day one; multibagger as reference customer; expand jurisdictions on the free-regulatory curve (ESAP 2027, EDINET now).

## 14. Risks & falsifiers

1. **Extraction precision** — a false "broken promise" verdict is the product's AP-v-Meltwater moment. Falsifier: golden-set precision below bar after two eval iterations → stop, narrow to numeric-guidance-only claims (Marvin's scope) until solved. The eval harness exists before the product does (charter discipline).
2. **Incumbent bolt-on** — AlphaSense ships "promise tracking" on its corpus. Mitigation: archive depth + people-graph + open schema are the parts a feature-bolt-on skips; move before the microcategory consolidates.
3. **Licensing lockdown** — wires restrict as revenue falls [F]. Mitigation: regulatory-substrate-first design already assumes it (R-013 gates every commercial source).
4. **Chasm monetization risk** — Koyfin's 500k-users/$4M-ARR warns that cheap seats may not fund the build [B]. Mitigation: the agent-feed and consultant-dossier doors carry higher price points on the same corpus; falsifier: if none of the three doors clears meaningful ARR at pilot scale, the thesis fails cheap.
5. **LLM homogenization** — if issuers' text converges to templates, naive diffs die; the claim-level design is the mitigation, and the eval harness must include LLM-rewritten adversarial cases from day one [H].
6. **Sizing humility** — every niche market-size figure disagrees by up to 10x [A]; this analysis deliberately relies on bottom-up WTP bands instead. If pilot WTP contradicts the bands, re-anchor before scaling.
7. **A live check on the noise thesis is already scheduled:** the whole design bets that *precision* beats *coverage* as the buying trigger — the pilot's first cohort NPS on alert precision is the earliest falsifier.

## 15. Sources & provenance

Raw agent reports (audit trail — verbatim as produced, except additive editor REFUTED-verdicts that preserve the original content in place; appendix C carries one such verdict): `market_analysis_sources/A_market_sizing_industry_economics.md` · `B_buyer_segments_willingness_to_pay.md` · `C_trends_mcp_agent_native_delivery.md` · `D_trends_llm_disruption_research_platforms.md` · `E_trends_disclosure_infrastructure.md` · `F_trends_newswire_industry_stress.md` · `G_trends_regulatory_tailwinds_ai_liability.md` · `H_trends_disclosure_change_academics_accountability.md`. Verified-claim substrate (3-vote adversarial): companion `PR_AGGREGATOR_RESEARCH.md` + its committed verification journal. Po battery: `tools/po_battery.py --seed 20260714` (generator output: `market_analysis_sources/PO_BATTERY_RUN_20260714.txt`; complete working notes: `market_analysis_sources/PO_BATTERY_WORKING_NOTES_20260714.md`), harvest in §8, M6 ledger row in `docs/metrics/KAIZEN_LEDGER.md`. Single-pass figures in this document are NOT adversarially verified; the R-013 gate applies to anything that would drive spend.
