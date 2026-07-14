# Press-Release Aggregator + Longitudinal Analysis — Research Report

**Date:** 2026-07-14 · **Status:** RESEARCH (new-venture idea, not an OneLive feature) · **Session Contract:** #5 (STATE.md)
**Question (founder):** Are there press-release (PR) aggregators with free or very low cost APIs? Is a product viable that ingests PRs per public company worldwide, builds a per-entity timeline, and produces diff-style analysis vs prior releases — what's new, what changed, what's unanswered, what was promised but not delivered — for investors, consultants, and policy makers? What are the real moats?

**Method:** deep-research harness — 5 parallel search angles → 25 sources consulted (several primary pages were reachable only via search-index captures after 403s) → 46 falsifiable claims extracted → top 25 adversarially verified by 3 independent verifier votes each (2/3 refutes kill a claim). Result: 22 confirmed, 3 refuted, 0 unverified. The verification record is committed alongside this report: `PR_AGGREGATOR_RESEARCH_verification.json` (claim-level aggregates, evidence, sources, refuted claims) and `PR_AGGREGATOR_RESEARCH_verification_votes.jsonl` (all 75 individual verifier votes with per-vote evidence). Sections marked **[VERIFIED 3-0]** survived that gate. Sections marked **[BEST-EFFORT]** come from a follow-up pass that *attempted* direct fetches of vendors' own pricing/terms pages but was blocked by this sandbox's egress proxy for most vendor domains — those figures therefore come from search-index captures of the vendors' pages plus secondary comparison sources, single-pass, NOT adversarially verified and NOT primary-source-confirmed. **The pricing/licensing half of the founder's question is answered provisionally, not definitively** — re-verification against live pages is recorded as deferral **R-013** in `docs/RECORD.md`, with an objective trigger (venture greenlight → primary-source re-check + written redistribution answers from finalists, before any spend).

---

## 1. Executive summary (plain language)

1. **Yes, free ingestion exists — but the truly free, legally clean backbone is regulatory filings, not newswires.** SEC EDGAR gives every US public company's material disclosures — including the press releases companies attach to 8-K filings — free, with no API key, ~25 years of searchable history, and government-sanctioned programmatic access. Nothing else in the landscape comes close on cost + legal cleanliness. **[VERIFIED 3-0]**
2. **The commercial newswires (PR Newswire, Business Wire, GlobeNewswire) sell distribution to companies, not data to us.** Reading their content at scale goes through either their public RSS/web surfaces (ToS risk) or third-party news APIs (low cost, but licensing terms — not price — are the real constraint). See §3–§4.
3. **The legal posture of the product is favorable in the US if we build it the right way:** facts are uncopyrightable; a diff/summary that *re-expresses* facts is on strong ground; systematic *verbatim excerpting* in a paid product that doesn't drive traffic back is exactly the fact pattern that lost in court (AP v. Meltwater). Design rule: store full text internally, publish re-expressed facts + short attributed quotes only. **[VERIFIED 3-0]**
4. **The core product thesis is academically validated.** "Lazy Prices" (Journal of Finance 2020): changes between a company's current and prior disclosures predict returns (~188 bps/month in-sample), future earnings, and even bankruptcies. Diffing disclosures carries real fundamental signal. Caveat: proven on SEC filings, not press releases — the extrapolation is ours. **[VERIFIED 3-0]**
5. **Raw diffing is commoditized; the moat is the ledger.** Redline tools are a crowded, cheap market. The defensible asset is the longitudinal, entity-resolved **promise ledger** — a growing, point-in-time-correct record of what each company claimed and what happened — because it compounds with time and cannot be back-filled cheaply by a late entrant. See §7.
6. **Canada is a trap; Europe is opening up.** SEDAR+ terms prohibit scraping, database-building, and commercialization outright — verified against the actual ToS. Meanwhile the EU's ESAP and existing free national mechanisms (see §5) are the international expansion path.
7. **You are customer #1.** The multibagger stock engine needs event/filing ingestion that is point-in-time correct. This product's machine-readable output is exactly that feed — which both de-risks product-market fit and enforces the right data discipline from day one (§7.4).
8. **What this report does NOT settle:** exact commercial pricing and — more importantly — whether any affordable provider's license permits republishing *transformed* diffs/summaries. Vendor pages could not be fetched directly from this sandbox, so §3/§5/§8 figures are search-index/secondary reads, and no provider's public terms answer the transformed-output question. That verification is recorded as deferral R-013 and fires before any spend or build.

## 2. The free backbone: SEC EDGAR **[VERIFIED 3-0]**

| Fact | Detail | Source |
|---|---|---|
| Cost | Free *access*. No API key, subscription, or license fee. **Access ≠ content rights:** SEC-authored material is public domain, but company-authored exhibits — including the press releases themselves — retain the company's copyright (the verification journal carries this caveat). Reuse is governed by the §4 rules: extract facts and re-express; no systematic verbatim republication | [SEC: Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) |
| Press releases | Companies file material press releases as exhibits (typically EX-99.1) to Form 8-K; earnings PRs under Item 2.02 | same |
| Rate limit | Hard cap 10 requests/second regardless of machine count, per-IP, ~10-minute 403 block on breach | same |
| Identification | Mandatory declared `User-Agent: Company Name admin@email` or requests are denied | same |
| Bulk path | SEC explicitly prefers nightly bulk ZIPs (`companyfacts.zip`, `submissions.zip`) + index files for backfill | same |
| Archive | Full-text search (efts.sec.gov) covers all electronic filings + exhibits since 2001-05-04; 1993+ index-browsable | same |
| Latency | Free endpoints: minutes-level. Sub-second dissemination = paid PDS feed | same |
| Format caveat | JSON APIs cover *structured* data; the documents/exhibits themselves are HTML/text (a claim that everything is JSON was refuted 0-3) | verifier finding |

Design consequences: poll ≤10 req/s for freshness, bulk ZIPs for the 2001+ backfill, compliant User-Agent from day one.

## 3. Newswire and news-API ingestion **[BEST-EFFORT — single-pass; search-index/secondary reads, NOT primary-verified]**

> **Provenance (read before trusting any number below):** the adversarial pass produced zero *verified* claims about commercial API pricing (marketing pages don't survive a 3-verifier bar; several pages block fetchers). A follow-up pass attempted direct fetches of vendors' own pricing/terms pages, but this sandbox's egress proxy returned 403 for the vendor domains — so the tables below were compiled from **search-index captures of the vendors' own pages plus secondary comparison sources**, as of 2026-07-14. No figure here is screen-verified against a live page. Conflicting numbers are shown as ranges; per-provider source pages to re-verify are listed at the end of each subsection. Re-verification is deferral **R-013** (fires at venture greenlight, before any contract or ingestion code).

### 3.1 Financial-data APIs that carry press releases

| Provider | Free tier (reported, unverified) | Lowest paid (reported, unverified) | PR coverage (wires named?) | Redistribution posture (reported) | Archive (reported) |
|---|---|---|---|---|---|
| **RTPR** (rtpr.io, Newsmatics) | "Wire" tier, never expires, ~60-min delay | **Pro $139/mo** | **Yes — its whole product**: Business Wire, PR Newswire, GlobeNewswire, AccessWire, sub-500ms claimed | **Red flag** (from a search-index capture of rtpr.io/terms, not a direct read): license is "solely for personal use," bans redistribute/resell/syndicate "in whole or in part" — direct read + written answer on transformed diffs required | unknown |
| **Benzinga** | AWS Marketplace basic tier (headlines/teasers only) | Sales-gated enterprise | **Yes — 5 wires** (ACCESSWIRE, Business Wire, GlobeNewswire, PRNewswire, Newsfile), **raw full text**, API pull or TCP push | Contracts contemplate display/redistribution — negotiated per use | implied historical (backtesting use) |
| **Finnhub** | 60 calls/min; company news NA-only, 1-yr history | opaque (pricing page gated; 3rd-party figures conflict) | Yes — `/press-releases` endpoint names 6 wires, **but full text = Enterprise only** | unverified | 1 yr free news |
| **Financial Modeling Prep** | 250 calls/day | Starter **$29/mo** (5-yr history), Premium $69/mo | **Yes — dedicated Press Releases + Search endpoints**, wire provenance undocumented | Public display of FMP-sourced data requires their separate Data Display & Licensing Agreement | 5–30+ yr (market data; PR depth unverified) |
| **StockNewsAPI** | 5-day trial only (Student $19.99/mo) | main-tier prices not published in index | **Yes — 5,000+ PRs/month from 5 named wires**, PR filter param | unverified | news to Feb 2019 |
| Polygon.io (now "Massive") | $0: 5 calls/min | $29/mo | News = Benzinga articles via partnership; raw PR feed appears premium-partner-gated | Market-data terms PDF unread | 2 yr free → 20+ yr $199 |
| Tiingo | 1,000 req/day, **news API excluded from free** | conflicting ($10 vs $30–50/mo) | No wire-PR claim; curated financial news | **Internal-use only by default**; redistribution by permission + fees ($250–500/mo tiers cited) | news: 3-mo window standard |
| EODHD | 20 calls/day (≈4 news requests) | $19.99–99.99/mo | No wire PR feed; general financial news, 15–60 min delay | Bars redistribution/display of data "original or repackaged" without approval | ~2018+ |
| Marketaux | 100 req/day | ~$166–199/mo top tier visible | No demonstrated wire-PR coverage | unverified | unknown |
| Alpha Vantage | **25 req/day** (unusable for polling) | $49.99/mo | No — aggregated news + sentiment | Standard grant is personal, non-commercial | unverified |

**Read of this table:** the only affordable self-serve products with *reported* wire-named press-release coverage are RTPR ($139/mo, but a hostile license as written), FMP ($29–69/mo, provenance undocumented), and StockNewsAPI (prices unpublished). Benzinga is the "right at scale, wrong at bootstrap" option — full raw text from five wires with redistribution contemplated in contract, at enterprise prices. The recurring pattern: **whether transformed diffs/summaries count as prohibited "redistribution" is answered by no provider's public terms — it must be asked in writing of any finalist before a line of ingestion code is written against them.**

*Source pages to re-verify (R-013):* rtpr.io + rtpr.io/terms · finnhub.io/pricing + finnhub.io/docs/api/press-releases · site.financialmodelingprep.com/pricing-plans + /developer/docs/stable/press-releases + /terms-of-service · stocknewsapi.com/pricing + /termsandconditions · benzinga.com/apis/cloud-product/press-releases · massive.com/pricing + /terms/market_data_terms.pdf (ex-Polygon) · tiingo.com/about/pricing + app.tiingo.com/tos · eodhd.com/pricing + /financial-apis/terms-conditions · marketaux.com/pricing + /tos · alphavantage.co/premium + /terms_of_service.

### 3.2 General news-aggregation APIs

> Sandbox caveat: this environment's egress proxy blocked direct fetches to most vendor domains, so these figures come from the search index citing the vendors' own pages (July 2026), plus secondary comparison sources. Conflicting numbers are shown as ranges. **The pattern that matters is consistent across all of them: price is not the barrier — licensing is.**

| Provider | Free tier (reported, unverified) | Lowest paid (reported, unverified) | Archive (reported) | Redistribution posture (reported — the deal-breaker column) |
|---|---|---|---|---|
| NewsAPI.org | 100 req/day (one source says 1,000), 24h delay, 1-mo archive, dev-only — no production use | Business $449/mo, 250k req/mo, 5-yr archive | 5 yr paid | ToS reportedly prohibits republishing article content (title/description/URL only); derived-summaries question unaddressed |
| NewsData.io | 200 credits/day (≈2,000 articles), 12h delay, no full content | Basic $199.99/mo, 20k credits, 6-mo history | up to 5–8 yr on top tiers | Redistribution only on upper tiers; GlobeNewswire content confirmed present |
| GNews | 100 req/day, 12h delay, non-commercial only | Essential ~€49.99/mo | ~2020+ top tiers | Commercial use OK paid; white-label redistribution prohibited |
| Mediastack | 100 req/**month**, 30-min delay | ~$24.99/mo | undisclosed | **Worst terms found**: data licensed for end-user "reference" only; storage/distribution by end users prohibited — incompatible with this product |
| Event Registry / NewsAPI.ai | 2,000 tokens, 30-day window, non-commercial | ~$90/mo token-based | **to 2014** (deepest self-serve) | Paid-tier derived-data terms unverified — direct ToS read required |
| Webz.io | News API Lite: 1,000 calls/mo, non-commercial | Sales-gated (expect 4–5 figures/yr) | **to 2008** (separate archive product) | Contract-negotiated — likeliest path to *explicit* redistribution rights |

*Source pages to re-verify (R-013):* newsapi.org/pricing + /terms · newsdata.io/pricing + /terms + /news-sources · gnews.io/pricing + /legal/terms-of-service · mediastack.com/pricing + /terms · newsapi.ai/plans + eventregistry.org ToS · webz.io/products/news-api + docs.webz.io/reference/news-api-lite.

**Key structural finding:** no general news API verifiably licenses "store + republish transformed summaries commercially" at a self-serve tier. The cheap tiers are cheap because they don't grant the rights this product needs. Either the rights come by contract (Webz.io-style), or the product leans on sources where the rights question is structurally easier: EDGAR (public domain) and the wires' own read surfaces (below).

### 3.3 The newswires themselves — read access

The wires sell *distribution* to issuers; reading is the product working as intended, but their site ToS don't always reflect that:

| Wire | Free read path (reported) | ToS posture on automation/derivatives (reported) |
|---|---|---|
| GlobeNewswire (Notified) | **Best free source found**: public RSS/Atom directory by category (public companies, earnings, M&A) at globenewswire.com/rss/list + full-archive access with a free Reader Account | ToS text not located — must be read before build |
| PR Newswire (Cision) | Free public RSS (prnewswire.com/rss/) | Site ToS reportedly bars robots/data-mining and derivative works without written consent — RSS consumption vs ToS text is in tension; consent or license needed for scale |
| Business Wire | Headline RSS free; **full-text Atom feeds that explicitly allow in-network storage exist but are arranged (and likely priced) via their media team** | "All reproduction other than personal reference prohibited without written permission" |
| ACCESSWIRE / Access Newswire | RSS page exists; real-time API/JSON/FTP feeds via sales | Terms unverified |
| EIN Presswire (Newsmatics) | Free topic/custom RSS (einpresswire.com/all-rss) | Reader-side terms unverified |
| openPR | RSS exists; low-tier releases | Reader-side terms unverified |
| **RTPR (rtpr.io, by Newsmatics)** | **Free "Wire" tier; Pro ~$139/mo, 7-day trial** — a real-time press-release API aggregating Business Wire, PR Newswire, GlobeNewswire, and ACCESSWIRE, sub-500ms claimed | Terms as captured in the search index show personal-use / no-redistribution language (details §3.1) — a direct read plus a written answer on transformed output is the single most important licensing task before relying on it |

**RTPR is the most interesting single discovery of this pass:** all four major wires, by API, at $139/mo — which would collapse the wire-ingestion problem to trivial cost, EXCEPT that its terms as indexed read personal-use-only with a blanket no-redistribution clause (§3.1). The gating question is written confirmation that derived analytical works are permitted; also diligence the product itself (young; who stands behind uptime and licensing indemnity).

*Source pages to re-verify (R-013):* prnewswire.com/rss + /terms-of-use · globenewswire.com/rss/list + Notified ToS (not located this pass) · businesswire.com/help/feed-options + services.businesswire.com/copyright · accesswire.com/rssfeed.aspx · einpresswire.com/all-rss · openpr.com/news/terms.html · rtpr.io/terms.

## 4. Legal posture **[VERIFIED 3-0 unless noted]**

1. **Facts are uncopyrightable** (Feist; 17 U.S.C. §102(b)). The US Copyright Office's June 2022 study found headline+lede aggregation "more likely to reproduce unprotectable ideas and facts" than protected expression, and declined to recommend an EU-style press-publishers' right. No US federal or state ancillary right exists as of mid-2026. A diff product that *re-expresses* extracted facts sits even further on the safe side. [USCO study](https://www.copyright.gov/policy/publishersprotections/202206-Publishers-Protections-Study.pdf)
2. **Fair use bounds verbatim reuse, not analysis.** Near consensus: large extracts or full articles exceed fair use; headline + very small snippet + link is likely fine; everything between is fact-dependent. Practical rule: full text stored internally for analysis; published output = re-expressed facts, diffs, short attributed snippets. [USCO; RCFP](https://www.rcfp.org/journals/news-media-and-law-summer-2012/content-aggregation-spreadi/)
3. **Hot-news misappropriation is a residual, not a blocker.** NBA v. Motorola (2d Cir. 1997) and Barclays v. Theflyonthewall (2d Cir. 2011) held the tort largely preempted; republishing time-sensitive *facts* is not by itself actionable.
4. **The cautionary template is AP v. Meltwater (SDNY 2013)** — a *paid* clipping service, taking *lengthier excerpts than typical aggregators*, *not driving traffic back*, lost on fair use at summary judgment, then settled. That is the fact pattern to design away from — we are an analysis product, not a clipping service. *(Confidence: medium — secondary press coverage of a settled district-court case.)*
5. **Refuted (0-3), do not rely on:** "press releases carry implicit consent to republish because issuers want distribution." The PR industry's plagiarism norms do not create a legal license.
6. **Not yet assessed (open):** EU press-publishers' right (DSM Art. 15), EU database right, UK/EU text-and-data-mining exceptions. Required before serving or sourcing from Europe. Also: each commercial API's ToS overrides all of the above doctrine for content obtained *through that API* — contract beats copyright analysis.
7. **Canada / SEDAR+ is out** as a scraped source: the ToS license only *unaltered* extracts for informational/internal use, and expressly prohibit commercialization, database construction, and robots/scraping — a diff product breaches all of these simultaneously. Canadian coverage = paid ASC bulk-data license, a commercial redistributor, or cross-listed companies' EDGAR filings. [SEDAR+ ToS](https://www.sedarplus.ca/onlinehelp/terms-of-use/)

## 5. Non-US regulatory feeds **[BEST-EFFORT — single-pass; search-index/secondary reads, NOT primary-verified]**

Ranked for a commercial store-and-transform product (each venue's cheapest sanctioned path):

**Free and commercial-reuse-friendly today (reported terms; confirm under R-013):**

| Venue | Access | Terms | Notes |
|---|---|---|---|
| **Japan EDINET** (FSA statutory disclosure) | Free API v2, self-service key | Secondary use **including for-profit** permitted (open-data posture) | Statutory filings, slower cadence than exchange timely disclosure; multi-year archive |
| **UK FCA NSM** (National Storage Mechanism) | Free web archive, CSV export; no documented retrieval API | Notably friendly: licence to use, store, copy, distribute, make available to third parties for lawful purposes | Slower than RNS real-time; read the Acceptable Use Policy before automating |

**Provisional — free access, reuse license NOT yet confirmed (do not treat as cleared):** **France info-financiere** (AMF OAM via DILA) — free official API on data.gouv.fr / Opendatasoft, per-issuer document lists + downloads. Reuse license *believed* to be Licence Ouverte 2.0 (the data.gouv.fr standard) but the license text was not read this pass; it joins the bucket above only when confirmed.

**Coming free:** **EU ESAP** — phase-1 collection starts 2026-07-10 (this week); public portal mandated by 2027-07-10, free, machine-readable, with API and bulk download by regulation. This will be the best free EU-wide source; design-track it now.

**Cheap published license:** **ASX ComNews** (real-time, every announcement, redistribution-grade): AUD 575/datafeed/month from Jan 2026, plus vendor/end-user fees — cheap by exchange standards. **Japan TDnet API**: ~JPY 70,000/month base + tiered fees; but its terms prohibit third-party redistribution and auto-accumulation environments — transformed-output question needs JPX's answer.

**Unpublished-price license:** **LSE RNS feed** (contact LSEG; site ToS explicitly ban all bots — no scraping path); **Canada ASC bulk data** (contact ASC; notably the *only* venue whose license explicitly permits resale under conditions).

**Effectively closed without bespoke licensing:** HKEXnews, SGXNet, India NSE/BSE (scraping contractually — in India possibly statutorily — barred), Germany's Unternehmensregister (register authority has said mass automated queries may be criminal; wait for ESAP).

*Source pages to re-verify (R-013):* fca.org.uk NSM pages + data.fca.org.uk/artefacts/NSM_Terms_of_Use.pdf · lseg.com RNS pricing-and-policy-guidelines-2026 PDF + website terms · esma.europa.eu ESAP pages + Reg (EU) 2023/2859 · info-financiere.gouv.fr/pages/api0 + data.gouv.fr listing · asx.com.au/legals/terms-of-use + asxonline.com schedule-of-fees PDF · jpx.co.jp TDnet API service pages · disclosure2dl.edinet-fsa.go.jp API docs + terms (WZEK0030) · sedarplus.ca/onlinehelp/terms-of-use · hkexnews.hk + hkex.com.hk terms · sgx.com/terms-use · nseindia.com/static/nse-terms-of-use + bseindia.com website policy.

## 6. Open-data bulk: Common Crawl CC-NEWS **[VERIFIED 3-0]**

Daily WARC drops (often within hours of capture) at `s3://commoncrawl/crawl-data/CC-NEWS/`, continuous archive back to August 2016 (~1.3B articles processed by academic users). Two verified caveats: coverage is partial (~83% of sampled news domains in a 2026 census; press-release wire coverage depends on crawler seeds — unguaranteed), and the claim that access is entirely free without an AWS account was **refuted 0-3** — budget AWS access/egress/compute. Role in the stack: retrospective backfill and a redundancy layer, not the primary live feed. [commoncrawl.org/news-crawl](https://commoncrawl.org/news-crawl)

## 7. Is the analysis worth anything? The evidence **[VERIFIED 3-0]**

**"Lazy Prices" (Cohen, Malloy & Nguyen — NBER WP 25084; Journal of Finance 2020):** textual changes between a company's current and prior 10-K/10-Q strongly predict future returns — a portfolio shorting "changers" and buying "non-changers" earned up to 188 bps/month alpha (>22%/yr, 1995–2014) — and predict *concrete fundamentals*: future earnings, profitability, news, and firm-level bankruptcies. Markets are slow to price disclosure changes; the information is real. [NBER](https://www.nber.org/papers/w25084)

Three honest qualifications: (a) evidence is on SEC filings, not press releases — our EDGAR-first stack applies it directly, but PR-text diffing is an untested extrapolation; (b) the tradeable return spread is likely partially arbitraged post-publication (McLean-Pontiff decay); (c) crucially, the *fundamental-prediction* results — the basis for a promise ledger — are not decay-sensitive the way trading alpha is. The paper also found no announcement-day effect: returns accrue when the change's meaning is later revealed. That is precisely the gap this product monetizes for humans: surfacing the change *at disclosure time* instead of quarters later.

## 8. Competitive landscape **[BEST-EFFORT — single-pass; search-index/secondary reads, NOT primary-verified]**

> All prices below are as reported by search index/third-party trackers as of 2026-07-14 (vendor sites largely blocked direct fetching); confirm before citing externally.

**Platform incumbents (search/summarize, some filing redlines, no promise ledger):**

| Company | What it does (relevant part) | Pricing (reported, unverified) | API for customer AI platforms? |
|---|---|---|---|
| AlphaSense | Search + AI summarization over filings/transcripts/news; "Blacklining" = redline of current vs prior 10-K/10-Q — a document-pair diff, not a timeline, filings-only | Sales-gated; reported ~$10K–20K/seat/yr (Vendr median contract $18,375/yr); $40K+ tiers w/ expert calls | Yes, enterprise-gated |
| Quartr | Earnings calls/IR docs, 15,000+ companies, 65 markets; aggregation + summaries, no diffing | Free app; Pro $499/mo; API sales-gated | Yes — flagship, "structured for AI" |
| Koyfin | Charting/fundamentals dashboards; no diffing | Free / $39 / ~$79 / advisor tiers $209–299/mo | No (their FAQ cites data-vendor restrictions) |
| Hudson Labs (ex-Bedrock AI) | Forensic red-flag scoring of SEC filings + "know what changed before earnings" filing comparison — the most analytical diff incumbent, but SEC-filings-scoped | Reported Core ~$100/mo; institutional ~$15K/team/yr | Reported in enterprise tier |
| Amenity Analytics | **Exited** — acquired by Symphony (Nov 2022), absorbed; no standalone product | — | — |
| Tegus / Sentieo / Stream | All acquired into AlphaSense (Tegus $930M, 2024); expert transcripts, not diffing | Sales-gated | via AlphaSense |
| Daloopa / Fintool / Fiscal.ai | AI fundamentals/copilots, no diffing or promises. Notable: Fiscal.ai sells API+MCP at $990/yr individual — evidence of pull for AI-platform-native delivery | Fiscal.ai Free/$39/$99/mo; others sales-gated | Daloopa yes; Fiscal.ai yes (MCP); Fintool enterprise |

**Diff-specific tools (all document-pair redlines of SEC filings — none cover press releases, none analyze):** BamSEC Compare Filings ($69/mo annual), Last10K ($9.99/mo retail), AlphaSense Blacklining, Hudson Labs comparison, free OSS (sec-diff, EDGAR Analyst), LexisNexis Knowledge Mosaic (legacy). Generic webpage-change monitors (Visualping, PageCrawl) are the only tools touching press-release pages — raw pixel/text diffs, no entity model, no analysis.

**Promise-tracking — the adjacent occupants (this is the important row):**

| Product | Scope | Pricing (reported, unverified) | Gap it leaves |
|---|---|---|---|
| **Marvin Labs** — "Guidance Tracking: Analyze Management Promises vs Delivery" | Extracts each management commitment from earnings communications, links restatements across time, scores promise-vs-delivery when the period closes | Free ≤15 companies; reported ~$89/mo/analyst | Earnings-guidance-scoped, equity-analyst-sold; not press releases broadly, not "what's unanswered," not policy makers/consultants |
| FinCatch | Early-stage; blog describes extracting forward-looking statements from transcripts AND press releases, scoring reality vs promise | Not public; traction unverified | Same loop, unproven; conviction-graph framing |
| Visible Alpha (S&P Global) | Structured guidance line items vs actuals (data layer) | Sales-gated | Numbers only, no narrative ledger |
| Net Zero Tracker / ChatNetZero / S&P NZ Commitments | Climate-commitment accountability | Free (nonprofit) / sales-gated | Climate-only; proves the accountability-timeline framing has demand |

**Whitespace verdict (from this pass):** filing-pair redlining is occupied and cheap — don't compete there. Press-release-level, entity-resolved longitudinal timelines with analysis are **empty**. Promise-tracking is **adjacent-occupied** (Marvin Labs exists and ships today) but is earnings-scoped and analyst-sold; multi-year promise ledgers across *all* corporate communications, the "what's unanswered" layer, the policy-maker/consultant buyer, and an open machine-readable promise-ledger API have **no direct occupant**. The category name is unclaimed in finance.

**Verified data point:** raw document comparison is commoditized — Draftable (~$249/user/yr legal tier, free tool, API), Litera Compare (~72% of the legal industry), Word Compare, Acrobat. Diff *mechanics* cannot be the moat. **[VERIFIED 3-0, medium confidence on exact figures]**

## 9. Moat assessment — real vs weak

| Moat candidate | Verdict | Why |
|---|---|---|
| **Longitudinal promise ledger** (entity-resolved claims → outcomes, point-in-time correct) | **REAL — the moat, but not empty-field** | Compounds with time; a late entrant must reconstruct history without contaminating it with hindsight. Academically underwritten (§7: disclosure changes predict fundamentals). Directly analogous to multibagger's retrodiction/Kaizen philosophy applied to issuers. Honesty check: Marvin Labs already ships promise-vs-delivery scoring for *earnings guidance* (~$89/mo, §8) — the open ground is all-communications scope, the "what's unanswered" layer, non-analyst buyers, and an open machine-readable ledger API. |
| **Point-in-time discipline** (immutable as-of-known-when records) | **REAL — quality moat** | Same reason multibagger forbids yfinance: most cheap news APIs silently revise. Doing this correctly from day one is cheap; retrofitting it is impossible. Also makes the dataset valuable as backtest input — a second customer segment (quants). |
| **Entity resolution + dedup quality** (same story across 4 wires + 8-K + IR page = one event) | **Real but earnable** | Genuine engineering asset and a visible quality bar; incumbents with money can replicate. A moat only in combination with the ledger. |
| **Machine-readable output for customers' AI platforms** | **Real as positioning, weak as moat** | "We organize, you think" + clean structured feeds (JSON/MCP) is the right wedge vs incumbents selling dashboards; but schemas are copyable. Stickiness comes from the ledger behind the schema. |
| **Speed** (fastest alert on a new PR) | **WEAK** | Sub-second dissemination is a paid arms race (SEC PDS, wire firehoses); HFT players own it. Compete on *time-to-understanding*, not time-to-byte. |
| **Cost** (cheapest access) | **WEAK alone** | Anyone can undercut; free EDGAR is available to all. Cost discipline is margin protection, not a moat. |
| **Sector-specific depth** (e.g., start with one sector's issuers, promise taxonomies tuned per sector) | **Real as go-to-market** | Narrow-and-deep beats broad-and-shallow for trust products; lets golden-set evaluation actually converge. Pick the beachhead sector deliberately. |
| **Trust/provenance architecture** (every claim links to source doc + extraction provenance) | **Real, inherited** | This is OneLive's existing trust-invariant DNA (evidence → gate → promote, AI never publishes directly) transplanted to a domain where the bar for "trusted information" is the product's entire value proposition. |

**The honest one-line version:** the defensible business is not "PR aggregator" (weak) — it is "the entity-resolved, point-in-time promise ledger over corporate communications, with machine-readable output" (real), where aggregation is merely the intake.

## 10. Recommended ingestion stack (cheapest viable) 

Underwritten by verified findings; per-source costs in §3/§5 are best-effort.

1. **US backbone (free):** EDGAR full-text search + data.sec.gov JSON APIs + nightly bulk ZIPs. Compliant User-Agent; ≤10 req/s polling; bulk archives for 2001+ backfill. Covers every US-listed company's material PRs via 8-K exhibits. **[VERIFIED]**
2. **Wire supplement (low cost, licensing-gated):** one financial news API chosen on *redistribution terms first, price second* (§3 tables) to catch non-8-K press releases (product launches, partnerships) and pre-8-K timing. Store full text internally; publish only transformed output.
3. **IR-page RSS (free, targeted):** for the beachhead sector's issuers, poll company IR RSS/newsroom pages directly — issuer-published content, lowest ToS risk among scraped sources, best earliest-copy provenance.
4. **Global backfill (compute-cost):** CC-NEWS WARCs 2016+ for retrospective timelines; accept partial coverage. **[VERIFIED, cost caveat]**
5. **International regulatory (free-first):** per §5 — Japan EDINET (free API, for-profit reuse allowed), France info-financiere (free API; reuse license still to be confirmed), UK FCA NSM (free, reuse-friendly terms) now; EU ESAP when its public portal opens (mandated July 2027, free + API by regulation); ASX ComNews (~AUD 575/mo) as the first *paid* venue when Australia matters; defer LSE RNS / ASC Canada / HKEX / SGX / India until revenue justifies bespoke licenses.
6. **Excluded:** SEDAR+ scraping (ToS), speed-race feeds (weak moat), any source whose ToS bans derived-work commercialization unless a license is bought deliberately (escalation: money/new services = founder-crucial).

## 11. Relationship to multibagger (founder context)

From the Multibagger Everything Document (uploaded 2026-07-14): the stock engine is the largest architecture gap; event-calendar ingestion is outstanding launch plumbing; the shared Data layer expects "events, filings, and historical inputs"; yfinance is forbidden for not being point-in-time. This product, built to §9/§10 discipline, is that missing feed — and multibagger's own retrodiction loop (did the promised catalyst happen?) is the first consumer of the promise ledger. Dogfooding order: EDGAR 8-K ingestion → per-entity timeline → promise extraction on the beachhead sector → machine-readable feed consumed by the stock engine.

## 12. Refuted claims (recorded so we don't re-believe them)

| Refuted claim (0-3 votes) | Planning consequence |
|---|---|
| Common Crawl is entirely free to access without an AWS account | Budget AWS access/egress/compute for CC-NEWS |
| EDGAR serves every disclosure as JSON | JSON = structured data only; exhibits are HTML/text — parse accordingly |
| PRSA norms create implicit republication consent for press releases | No "issuers want distribution" legal theory; rely on facts-doctrine + fair-use design rules |

## 13. Open questions (carried forward)

1. Commercial news-API licensing: which providers' ToS actually permit storing content and republishing transformed diffs/summaries? (§3 tables are pricing-first; a contract-level ToS read is required before building on any of them.)
2. EU legal posture: DSM Art. 15 press-publishers' right, database right, TDM exceptions — required before EU go-to-market.
3. ASC/SEDAR+ commercial license cost vs skipping Canada (cross-listed issuers are on EDGAR anyway).
4. Whitespace confirmation: §8's promise-tracking scan is single-pass; before committing, a buyer-interview pass (do investors/consultants *pay* for organized-not-analyzed?) is the real validation.
5. Beachhead sector selection — deliberate decision, po battery + friction attack per charter before any build.

---

*Sources: all VERIFIED-tagged findings trace to the deep-research run of 2026-07-14 (22 claims confirmed 3-0 against primary sources: sec.gov, sedarplus.ca, copyright.gov, commoncrawl.org, nber.org, rcfp.org, hudson-labs.com) — claim-by-claim journal committed at `docs/research/PR_AGGREGATOR_RESEARCH_verification.json`. BEST-EFFORT sections are search-index/secondary-source compilations (NOT primary-verified — sandbox egress blocked vendor fetches); each such subsection ends with the list of source pages to re-verify under R-013.*
