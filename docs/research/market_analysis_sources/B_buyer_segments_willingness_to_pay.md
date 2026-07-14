<!-- Raw research-agent report — the agent-authored BODY below is preserved
verbatim; this header comment is editorial. Audit trail for
docs/research/PR_AGGREGATOR_MARKET_ANALYSIS.md. Single-pass, search-index/secondary
sources unless a row says otherwise; confidence labels are the agent's own.
Compiled 2026-07-14. -->

# Buyer Segments & Willingness-to-Pay: Investment-Research / Disclosure-Monitoring Tools (as of July 2026)

Method note: all facts gathered via web search (sandboxed session, ~30 queries, July 2026). Confidence key: **HIGH** = primary source or multiple independent corroborations; **MED** = single reputable secondary source or aggregator (Vendr/Sacra/SpendHound-type spend data); **LOW** = single blog/forum/unverified claim. Vendor-price aggregator figures (Vendr, SpendHound, costbench) are directionally reliable but not contract-verified.

---

## 1. Buy-side (hedge funds, asset managers, family offices)

### Seat pricing — reported ranges

| Tool | Reported price | Source | Confidence |
|---|---|---|---|
| Bloomberg Terminal | **$31,980/yr single seat; $28,320/seat multi-terminal (2025-26, after 6.5% Jan-2025 increase)**; real first-year TCO ~$33-35k with keyboard/data add-ons | [NeuGroup](https://www.neugroup.com/bloomberg-terminals-how-much-more-youll-pay-next-year/), [costbench](https://costbench.com/software/financial-data-terminals/bloomberg-terminal/), [godeldiscount](https://godeldiscount.com/blog/bloomberg-terminal-cost-2026) | HIGH (widely corroborated) |
| Bloomberg Terminal — installed base | ~325,000 subscribers (2022), "more than 350,000 decision makers" per Bloomberg marketing (2026) | [Wikipedia](https://en.wikipedia.org/wiki/Bloomberg_Terminal), [Bloomberg](https://www.bloomberg.com/professional/products/bloomberg-terminal/) | HIGH |
| AlphaSense | $10-20k/seat/yr standard; **$40k+/seat with expert-call transcript tier**; typical 3-seat deal $45-60k/yr ($120k+ with expert calls); deals $50k-$1M+; started ~$12k/yr entry | [Vendr](https://www.vendr.com/marketplace/alphasense), [SpendHound](https://www.spendhound.com/marketplace/alphasense-pricing), [tomba.io](https://tomba.io/blog/alphasense-pricing-reviews-pros-and-cons) | MED-HIGH |
| Tegus (now AlphaSense-owned) | Subscription scaled by AUM, **from ~$20-25k/user/yr**; expert calls at-cost $300-450/hr avg (vs $1,000+ at classic networks) | [Sacra](https://sacra.com/c/tegus/), [Not Boring](https://www.notboring.co/p/tegus-the-outsiders), [Inex One](https://inex.one/expert-network-directory/tegus-expert-network) | MED-HIGH |
| FactSet | Median buyer **~$25,160/yr** (Vendr transaction data); implied ASV/user ~$11.2k (ASV $2.1B ÷ 187,845 users, FY23); full workstation builds $12-30k+; total ASV $2.4B Q1 FY26 (+5.9% organic) | [Vendr](https://www.vendr.com/buyer-guides/factset), [costbench](https://costbench.com/software/financial-data-terminals/factset/), [Motley Fool transcript](https://www.fool.com/earnings/call-transcripts/2025/12/18/factset-fds-q1-2026-earnings-call-transcript/) | MED-HIGH |
| LSEG/Refinitiv Workspace (team) | $70-110k/yr for a small team build (aggregator estimate) | [godeldiscount](https://godeldiscount.com/blog/bloomberg-alternatives-hedge-funds) | LOW-MED |

### Research-tech budget per analyst
- No clean public "per-analyst" benchmark exists; Substantive Research sells this as a paid benchmark (factors: users, licenses, AUM). [Substantive Research](https://substantiveresearch.com/products/market-data/) — HIGH that it's opaque/benchmark-as-a-service.
- Proxy: a fully loaded fundamental analyst seat at a mid/large fund = Bloomberg ($32k) + FactSet or AlphaSense ($15-25k) + expert calls ($20k+) ≈ **$60-90k/analyst/yr**; consistent with reported FactSet team builds $60-90k and Coalition Greenwich finding 80% of buy-side firms expect market-data spend to keep rising ([The TRADE](https://www.thetradenews.com/buy-side-market-data-costs-on-the-rise-as-asset-managers-tap-fixed-income-equities-and-etfs-for-the-greatest-spend/), [Coalition Greenwich](https://www.greenwich.com/market-structure-technology/market-data-spending-roll)) — MED (derived).
- Burton-Taylor: S&P, FactSet, Bloomberg, LSEG **each earned >$500M from the "research analyst" segment alone (2022)** ([Burton-Taylor PDF](https://tpicap.com/burtontaylor/sites/g/files/escbpb181/files/burton-taylor/reports/2023-09/Research%20Analysts%20Data%20Usage.pdf)) — HIGH.

### Firm counts (TAM denominators)

| Population | Count | Source | Confidence |
|---|---|---|---|
| Hedge fund firms globally | **10,000+** firms; ~$4.7-5.5T AUM mid-2025; 551 "Billion Dollar Club" firms hold 86% of AUM; **60-65% of funds are <$250M AUM but hold only 10-12% of AUM** | [Aquis Capital](https://aquis-capital.com/news/how-many-hedge-funds-are-there), [With Intelligence](https://www.withintelligence.com/insights/billion-dollar-club-h1-2025/), [CoinLaw](https://coinlaw.io/hedge-fund-industry-statistics/) | MED-HIGH |
| SEC-registered RIAs (US) | **16,544 firms (2025, record)**, 73.7M clients, $176.8T RAUM (incl. double counting) | [ThinkAdvisor/IAA](https://www.thinkadvisor.com/2026/06/03/number-of-rias-sets-new-record-report/), [IAA](https://www.investmentadviser.org/industry-snapshots/) | HIGH |
| Single family offices worldwide | **~9,030 (2025 proj.)**, from 8,030 (2024); →10,720 by 2030; NA 3,180 / APAC 2,290 / EU 2,020 | [Deloitte](https://www.deloitte.com/global/en/about/press-room/global-edition-explores-the-rapid-expansion-family-offices-and-ffers-vision-of-the-future-landscape.html) | HIGH |

### The underserved tier (<$100M AUM)
- Framing found in the wild: a 5-10 analyst team on Bloomberg = $140-280k/yr, untenable for a $50-500M fund; recommended alt-stack is "Koyfin + stripped LSEG + Polygon.io API = 90% of functionality at 10% of cost" ([godeldiscount](https://godeldiscount.com/blog/bloomberg-alternatives-hedge-funds)) — MED (vendor-adjacent blog, but matches practitioner consensus).
- What small funds actually pay: **Koyfin $2,340-5,940/yr** ($39+/mo tiers), Godel Terminal $4,980-7,080/yr, Interactive Brokers market data ~$6k/yr, plus Seeking Alpha/TIKR/Fiscal.ai at consumer prices ([Koyfin pricing](https://www.koyfin.com/pricing/), [godeldiscount](https://godeldiscount.com/blog/bloomberg-alternatives-hedge-funds)) — MED-HIGH.
- **Gap evidence:** the jump from ~$5k/yr prosumer tools to ~$15-30k/yr institutional seats is a genuine pricing chasm; Koyfin's whole business (500k users, only ~$3.9M est. ARR — [getlatka](https://getlatka.com/companies/koyfin.com), LOW-MED) shows huge usage but weak monetization at the bottom of that chasm.

---

## 2. Retail / prosumer serious investors

| Product | Price | Scale evidence | Source | Confidence |
|---|---|---|---|---|
| Seeking Alpha Premium | **$299/yr** list (promos $239-269 first year); PRO **$2,400/yr** | ~20M monthly visits; paying-subscriber count NOT publicly disclosed (widely cited "hundreds of thousands" unverified) | [about.seekingalpha.com](https://about.seekingalpha.com/premium-subscription-price-update), [seekingalpha.com/subscriptions](https://seekingalpha.com/subscriptions) | Price HIGH; sub count UNKNOWN |
| Motley Fool Stock Advisor | **$199/yr list, $99 intro** | "500,000+ subscribers" across services (long-standing company claim, not audited) | [fool.com](https://www.fool.com/services/stock-advisor/), [stockanalysis.com review](https://stockanalysis.com/article/motley-fool-stock-advisor-review/) | Price HIGH; subs MED |
| TIKR | Free / Plus / Pro / Ultimate, paid **from $14.95/mo (annual)** | claims **300,000+ individual investors** | [tikr.com/pricing](https://www.tikr.com/pricing), [Capterra](https://www.capterra.com/p/231145/TIKR/) | MED |
| Koyfin | Free tier + paid **from $39/mo** (~$468-1,188/yr; pro tiers to ~$5,940/yr) | **500,000 users**; est. ~$3.9M ARR 2025 → implied paid conversion in low single digits | [koyfin.com/pricing](https://www.koyfin.com/pricing/), [getlatka](https://getlatka.com/companies/koyfin.com), [growjo](https://growjo.com/company/Koyfin) | Price HIGH; ARR LOW-MED |
| Fiscal.ai (ex-FinChat) | Free tier; **Pro $49/mo ($468/yr); Max $99/mo ($948/yr)**; raised $10M Series A | — | [fiscal.ai/pricing](https://fiscal.ai/pricing/), [WallStreetZen review](https://www.wallstreetzen.com/blog/finchat-io-fiscal-ai-review/) | HIGH |
| Substack finance newsletters | The Diff **$20/mo / $220/yr**; Slow Boring $10/mo with **13,000+ paid subs → >$1.04M/yr**; finance among top-3 Substack categories by revenue | [Readless](https://www.readless.app/blog/best-paid-substack-newsletters-2026), [Sidestack](https://sidestack.io/directory/category/finance?language=en&sort=paid) | MED |

**Takeaway (derived, MED):** the prosumer band clusters at **$15-100/mo ($180-1,200/yr)**; $299/yr (Seeking Alpha) is the proven ceiling for mass-scale, $2,400/yr (SA PRO, The Diff-tier newsletters $220+) is the ceiling for the top sliver. Free-tier-to-paid is the universal acquisition motion (TIKR, Koyfin, Fiscal.ai all freemium).

---

## 3. Consultants (strategy / DD)

- **AlphaSense penetration: "80% of top consultancies"** are customers; corporate+consulting is a core segment alongside financial services (75% of top hedge funds, 90% of S&P 100) ([Sacra](https://sacra.com/c/alphasense/)) — MED-HIGH. AlphaSense hit **$600M ARR (Mar 2026)**, 7,000+ enterprise customers — MED-HIGH.
- **Expert network market: ~$2.1B (2022) → ~$2.5B (2024), ~16% CAGR over the decade**; est. ~$3B 2025 ([Inex One](https://inex.one/blog/expert-network-market-size)) — MED-HIGH. **Consulting firms = 46% of global expert-network application share** ([Valuates](https://reports.valuates.com/market-reports/QYRE-Auto-2C13581/global-expert-networks)) — MED. GLG revenue >$400M, 1M+ experts ([CleverX](https://cleverx.com/blog/largest-expert-networks-top-global-players-by-size-and-market-share/)) — MED.
- **Per-project commercial-due-diligence budgets:** full CDD engagement **$100k-500k**; mid-market $50-150k; lower-mid-market add-ons $80-180k total external DD with $20-40k commercial-scan component; expert calls $500-2,000/hr, **typical CDD expert-call program $50-200k for 10-20 conversations**; hybrid AI-interview approaches quoted at $2-15k (AI) + $20-40k (expert calls) ([UserIntuition](https://www.userintuition.ai/posts/commercial-due-diligence-cost/), [Plausity](https://plausity.com/en/news/commercial-due-diligence-costs)) — MED (vendor-side blogs, but ranges mutually consistent).
- Implication: consultants buy **by project, not by seat** — data budgets of $20-200k/project are normal, and platforms (AlphaSense/Tegus model) win by converting per-call spend into subscriptions.

---

## 4. Policy makers / government affairs / regulators

| Tool | Price / scale | Source | Confidence |
|---|---|---|---|
| POLITICO Pro | **~$10,000/yr** per subscription (multiple journalists/Hill staff confirm); older data: 20,000 paid subscribers = ~half of Politico revenue | [X/Sam Lyman](https://x.com/SamLyman33/status/1887156001733820706), [Digiday](https://digiday.com/media/half-politicos-revenue-now-20000-subscribers/) | MED-HIGH |
| Bloomberg Government (BGOV) | **$7,500-14,000/yr**, custom-quoted | [Fed-Spend comparison](https://fed-spend.com/blog/govwin-govspend-govtribe-bloomberg-pricing-compared-2026) | MED |
| FiscalNote | Public co (NYSE: NOTE): **FY2025 revenue $95.4M (down from $120.3M)**, ARR $84.1M, **3,500+ customer orgs → implied ~$24k/org/yr**, 95% subscription revenue, NRR ~96%; deep restructuring, "PolicyNote" AI pivot | [StockTitan 10-K](https://www.stocktitan.net/sec-filings/NOTE/10-k-fiscal-note-holdings-inc-files-annual-report-184582cb14e3.html), [Investing.com](https://www.investing.com/news/company-news/fiscalnote-q4-2025-slides-ai-pivot-amid-revenue-decline-margin-gains-93CH-4572052) | HIGH (SEC filings) |
| Quorum | No public pricing; 9 modular plans (Federal, State, Grassroots, PAC…); reviews say Quorum/FiscalNote "quote significantly higher prices" than budget alternatives; FiscalNote publicly offers to undercut Quorum by 10% | [quorum.us/pricing](https://www.quorum.us/pricing/), [FiscalNote](https://fiscalnote.com/policynote/quorum-alternative), [LegiStorm](https://info.legistorm.com/blog/best-public-affairs-software) | MED |

**Gov-affairs seat benchmark (derived, MED): $8-15k/seat/yr for monitoring platforms; $20-30k+/org for full FiscalNote/Quorum suites.** These tools monitor *legislation/regulation*, not corporate disclosures.

**Do any tools serve regulators tracking CORPORATE claims?** Mostly no — this is a genuine white space:
- EU Commission JRC has built internal AI tools for environmental-claims monitoring since 2022; **Dutch ACM piloted AI screening of 170+ corporate websites, flagging potential greenwashing violations in 42% of cases**; French DGCCRF also piloting ([Directors' Institute](https://www.directors-institute.com/post/ai-powered-greenwashing-detection-the-next-frontier-in-esg-governance)) — MED.
- Korea's KEITI detected **2,528 greenwashing violations in 2024 vs 110 in 2020 (23x)** ([BigGo/SK AX launch](https://finance.biggo.com/news/LcLRQp4BrAZSr0oSbOIR)) — MED.
- Commercial greenwashing-claim scanners exist but target *corporates pre-publication*, not regulators: SK AX "X-GenticWire Compliance" (2026), EcoAppraise, GreenSignal.ai, Green Claims Scanner, SESAMM ([sesamm.com](https://www.sesamm.com/blog/beyond-greenwashing-how-ai-identifies-greenwishing-and-greenhushing-amid-tightening-esg-regulations)) — MED. No established pricing benchmarks found — LOW.
- SEC uses in-house data analytics for enforcement (583 actions FY2024, $8.2B penalties; late-filer sweeps identified via analytics) rather than buying commercial disclosure-monitoring seats ([Finrep guide](https://www.finrep.ai/blog/sec-filing-analysis-tools-the-2026-practitioners-guide)) — MED.

---

## 5. IR / corporate comms (the flip side)

- **Yes, corporates monitor their own and peers' disclosure language — this is a real, growing budget line.** AlphaSense's corporate segment: **90% of S&P 100, ~70% of S&P 500, >50% of Fortune 500** are customers ([Sacra](https://sacra.com/c/alphasense/)) — MED-HIGH.
- **Quartr Pro** explicitly sells IR teams: peer earnings-call Q&A topic analysis ("anticipate questions"), keyword alerts, "Mentioned by" tracking (any company mention by customers/suppliers/competitors), slide-evolution tracking; 700+ institutions/companies use Quartr; pricing quote-only ([quartr.com/products/quartr-pro](https://quartr.com/products/quartr-pro)) — MED-HIGH on features, pricing UNKNOWN.
- **Notified IR** offers "earnings call due diligence, peer and market monitoring, Q&A analysis, sentiment"; Q4 Inc and Irwin (FactSet) sell IR CRM+monitoring — all quote-based, no public pricing ([notified.com](https://www.notified.com/resources/which-IR-platform-is-best-for-hosting-earnings-calls-in-2026), [getirwin.com](https://www.getirwin.com/)) — MED features / pricing UNKNOWN.
- **Media-monitoring seat benchmarks (your $5-15k hypothesis is low):** Meltwater median **$25k/yr** (range $6k-$100k+; SMB avg ~$16.2k, enterprise avg ~$69.6k); Cision starts ~$10k, avg $12-15k, SMB avg $8.1k, enterprise avg $94k ([Vendr](https://www.vendr.com/marketplace/meltwater), [SpendHound](https://www.spendhound.com/marketplace/meltwater-pricing), [Prowly](https://prowly.com/magazine/meltwater-pricing/), [authoritytech](https://authoritytech.io/blog/cision-vs-meltwater-2026)) — MED-HIGH. So entry ~$6-10k, realistic mid-market $15-25k/yr per org.

---

## 6. Pain points / unmet needs (review mining)

**AlphaSense** (G2 ~4.4-4.6 stars, but):
- Price/opacity is complaint #1 "by a wide margin": "teams dislike the quote-only model, the size of the number, and how fast add-ons inflate it" ([tomba.io analysis of G2](https://tomba.io/blog/alphasense-pricing-reviews-pros-and-cons)) — MED.
- **Noise is complaint #2: "Noisy search results top the complaint list with 19 G2 mentions — finding the exact report you need can feel like digging through a haystack"; "setting up alerts sometimes just results in a lot of noise"** ([G2 pros/cons](https://www.g2.com/products/alphasense/reviews?qs=pros-and-cons), via [prospeo](https://prospeo.io/s/alphasense-pricing-reviews-pros-and-cons)) — MED-HIGH. Directly relevant: even the category leader is weak on signal-vs-noise and alert precision.
- Learning curve / overwhelming interface for newcomers — MED.

**Meltwater** — complaints are about the *company*, not the product:
- "Meltwater deceptive auto-renewal policy and truly awful customer service" (review title, [TrustRadius](https://www.trustradius.com/reviews/meltwater-media-intelligence-platform-2017-04-24-12-19-30)) — HIGH (verbatim).
- "Beware of Hidden Contract Terms like Auto-renewal Clauses and Built-in Price Increases" ([TrustRadius](https://www.trustradius.com/reviews/meltwater-media-intelligence-platform-2020-09-28-11-13-43)); 60-day cancellation window + auto-renew is the recurring theme across G2/Trustpilot/BBB; "a nice product but a terrible company to work with" (G2 reviewer via [Agorapulse roundup](https://www.agorapulse.com/blog/social-media-management-tools/meltwater-reviews/)) — HIGH. Lesson: transparent pricing + easy exit is a differentiator in this market.

**Quartr:** "missing many companies… a number of S&P 500 companies were not listed, several spelled incorrectly"; "adequate for average to novice investors who only follow large blue-chips" ([justuseapp reviews](https://justuseapp.com/en/app/1552412128/quartr-investor-relations/reviews)) — MED. Coverage completeness is the retail complaint.

**Koyfin:** users want "more comprehensive data… especially UK markets," CUSIPs, more feeds; charting/data-management feature gaps ([G2 pros/cons](https://www.g2.com/products/koyfin/reviews?qs=pros-and-cons)) — MED. Cheap tier = data-depth ceiling.

**Bloomberg:** complaint is simply price ($32k) and paying for a monolith when you need a slice — the entire "Bloomberg alternative" content industry ([godeldiscount](https://godeldiscount.com/blog/why-is-bloomberg-terminal-so-expensive), [helmterminal](https://helmterminal.dev/blog/best-bloomberg-terminal-alternatives)) — HIGH.

**AI-hallucination anxiety (systemic, 2026):**
- FINRA warning on AI hallucination risk (2026); Wall Street firms adding AI-hallucination risk disclosures; banks piloting "hallucination dashboards" ([NeuralWired](https://neuralwired.com/2026/07/07/deloitte-ai-hallucination-finra-2026/), [PYMNTS](https://www.pymnts.com/news/artificial-intelligence/2025/the-future-of-trustworthy-ai-can-hallucinations-be-tamed)) — MED.
- KPMG 2024: 21% of companies using AI in financial reporting cite hallucinations as a significant concern ([Trullion](https://trullion.com/blog/ai-hallucination-in-accounting-and-audit/)) — MED.
- One blog claims "$2.3B in avoidable Q1 2026 trading losses from hallucinated earnings forecasts" ([tendem.ai](https://tendem.ai/blog/true-cost-ai-hallucinations-business-data)) — **LOW, unverified, do not use as a headline stat.**
- **Longitudinal tracking gap:** no incumbent markets alert-precision or claim-tracking-over-time well; closest features are Quartr's slide-evolution tracking and AlphaSense/Hebbia flagging "year-over-year language changes in risk factors and MD&A" ([Finrep guide](https://www.finrep.ai/blog/sec-filing-analysis-tools-the-2026-practitioners-guide)) — MED. This is the least-served complaint cluster (noise + no longitudinal memory) across all reviews found.

---

## 7. Data-feed buyers (quant funds / AI platforms)

| Feed | Pricing evidence | Source | Confidence |
|---|---|---|---|
| RavenPack | **Enterprise ~$100-150k/yr** for full historical news-analytics access; academic $20-40k; new advisor-facing AI tool at $50-100/user/mo (low-end product) | [Datarade](https://datarade.ai/data-providers/ravenpack/profile), [econjobrumors (academic)](https://www.econjobrumors.com/topic/academic-pricing-for-dow-jones-thomson-reuters-ravenpack-news-analytics), [FA-Mag](https://www.fa-mag.com/news/ravenpack-launches-fully-ai-powered-research-tool-for-advisors-80031.html) | MED |
| Bloomberg Event-Driven Feeds | Machine-readable news + sentiment for black-box trading; new customizable Real-Time News Feeds launched 2025; only dated pricing found: ~$20k/mo base + $10k/add-on (2013 forum) → assume **$200k+/yr order of magnitude** today | [Bloomberg](https://www.bloomberg.com/professional/products/data/enterprise-catalog/event-driven-feeds/), [Bloomberg press](https://www.bloomberg.com/company/press/bloomberg-launches-customizable-real-time-news-feeds-for-enhanced-systematic-workflows/), [EliteTrader](https://elitetrader.com/et/threads/any-one-tried-bloomberg-event-driven-feed.269723/) | Pricing LOW (dated); product HIGH |
| Benzinga APIs | "Originates and aggregates alternative data for the largest hedge funds and research platforms"; free Basic News API tier on AWS Marketplace + custom premium tiers; consumer Pro $27-177/mo (+$49 squawk add-on) | [benzinga.com/apis](https://www.benzinga.com/apis/), [AWS Marketplace](https://aws.amazon.com/marketplace/pp/prodview-xwgvhwowjmw3g), [benzinga.com/pro/pricing](https://www.benzinga.com/pro/pricing) | MED; enterprise pricing UNKNOWN |
| Quartr API | Sells "live earnings data & transcripts, structured for AI" — explicitly positioned as data infrastructure for AI builders | [quartr.com/products/quartr-api](https://quartr.com/products/quartr-api) | HIGH (positioning) |
| Kensho (S&P Global) | No public pricing found | — | UNKNOWN |

**MCP / agent-tools market (emerging, moving fast):**
- MCP (Anthropic, Nov 2024) now supported by every major AI platform; Linux Foundation confirmed **10,000+ active public MCP servers** early 2026; Python SDK >164M monthly PyPI downloads by Apr 2026; Agentic AI Foundation ~150 member orgs ([truthifi](https://truthifi.com/education/state-of-mcp-2026-ai-agents-custom-connectors), [qveris](https://qveris.ai/guides/mcp-server-list-finance/)) — MED (secondary reporting of LF/PyPI figures).
- Finance-specific MCP servers already shipping from FMP, Alpha Vantage (leading market-data MCP), Alpaca (live trade execution via agent) ([FMP](https://site.financialmodelingprep.com/developer/docs/mcp-server), [chartlibrary comparison](https://chartlibrary.io/blog/financial-mcp-servers-compared)) — MED-HIGH.
- Enterprise GRC agents arriving: IBM OpenPages 9.2 GA Mar 2026 exposes compliance workflows to AI agents ([Integrate.io](https://www.integrate.io/blog/mcp-servers-financial-services-compliance/)) — MED.
- **Implication:** demand for machine-readable, agent-consumable event/claims feeds is real and pricing anchors exist at three tiers: free/freemium API (Benzinga basic, FMP), ~$10-50k/yr mid-tier data subscriptions, $100-200k+/yr institutional-grade analytics feeds (RavenPack/Bloomberg EDF).

---

## Cross-cutting summary table (WTP bands by segment)

| Segment | Population | WTP band (per seat/org/yr) | Anchor products | Confidence |
|---|---|---|---|---|
| Large buy-side | ~551 $1B+ HFs; top asset managers | $30-90k/analyst stack | Bloomberg, FactSet, AlphaSense+Tegus | MED-HIGH |
| Small funds/RIAs/family offices (underserved) | ~6,500 sub-$250M HFs + 16.5k RIAs + ~9k FOs | **$1-6k/seat (gap: nothing between $6k and $15k)** | Koyfin, Godel, TIKR Pro | MED |
| Prosumer retail | 300k+ (TIKR) / 500k (Koyfin) / millions (SA visits) | $180-1,200/yr, sweet spot ~$300 | Seeking Alpha, Fiscal.ai | HIGH |
| Consultants | Big-4 + strategy + boutiques (46% of $3B expert-net market) | $20-200k **per project**; platform seats $15-40k | AlphaSense, GLG, Third Bridge | MED |
| Gov affairs / policy | FiscalNote's 3,500 orgs is the observable market | $8-15k/seat; $24k/org avg (FiscalNote) | Politico Pro, BGOV, Quorum | MED-HIGH |
| Regulators monitoring corporate claims | Handful of pilots (ACM, DGCCRF, JRC, KEITI) | No commercial market yet — in-house/pilot | none established | MED (that it's white space) |
| IR/comms | 70% of S&P 500 already on AlphaSense; 700+ orgs on Quartr | $6-25k media monitoring; $10-40k+ IR platforms | Meltwater, Cision, Quartr Pro, Notified | MED |
| Quant/AI data-feed buyers | systematic funds + AI app builders | free→$50k API; $100-200k+ premium feeds | RavenPack, Bloomberg EDF, Benzinga, Quartr API | MED |

**Known gaps I could not close:** Seeking Alpha paid-subscriber count and revenue (private, undisclosed); Quorum and Quartr Pro actual contract prices; Kensho pricing; current Bloomberg EDF pricing; any per-seat benchmark for regulator-facing claim-monitoring tools (market doesn't exist yet).
