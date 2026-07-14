# Press-Release Aggregator + Longitudinal Analysis — Research Report

**Date:** 2026-07-14 · **Status:** RESEARCH (new-venture idea, not an OneLive feature) · **Session Contract:** #4 (STATE.md)
**Question (founder):** Are there press-release (PR) aggregators with free or very low cost APIs? Is a product viable that ingests PRs per public company worldwide, builds a per-entity timeline, and produces diff-style analysis vs prior releases — what's new, what changed, what's unanswered, what was promised but not delivered — for investors, consultants, and policy makers? What are the real moats?

**Method:** deep-research harness — 5 parallel search angles → 25 sources fetched → 46 falsifiable claims extracted → top 25 adversarially verified by 3 independent verifier votes each (2/3 refutes kill a claim). Result: 22 confirmed, 3 refuted, 0 unverified. 107 agents total. Sections marked **[VERIFIED 3-0]** survived that gate; sections marked **[BEST-EFFORT]** come from a follow-up direct-fetch pass of vendors' own pricing pages (primary sources, single-pass, not adversarially verified — pricing changes often; re-check before contracting).

---

## 1. Executive summary (plain language)

1. **Yes, free ingestion exists — but the truly free, legally clean backbone is regulatory filings, not newswires.** SEC EDGAR gives every US public company's material disclosures — including the press releases companies attach to 8-K filings — free, with no API key, ~25 years of searchable history, and government-sanctioned programmatic access. Nothing else in the landscape comes close on cost + legal cleanliness. **[VERIFIED 3-0]**
2. **The commercial newswires (PR Newswire, Business Wire, GlobeNewswire) sell distribution to companies, not data to us.** Reading their content at scale goes through either their public RSS/web surfaces (ToS risk) or third-party news APIs (low cost, but licensing terms — not price — are the real constraint). See §3–§4.
3. **The legal posture of the product is favorable in the US if we build it the right way:** facts are uncopyrightable; a diff/summary that *re-expresses* facts is on strong ground; systematic *verbatim excerpting* in a paid product that doesn't drive traffic back is exactly the fact pattern that lost in court (AP v. Meltwater). Design rule: store full text internally, publish re-expressed facts + short attributed quotes only. **[VERIFIED 3-0]**
4. **The core product thesis is academically validated.** "Lazy Prices" (Journal of Finance 2020): changes between a company's current and prior disclosures predict returns (~188 bps/month in-sample), future earnings, and even bankruptcies. Diffing disclosures carries real fundamental signal. Caveat: proven on SEC filings, not press releases — the extrapolation is ours. **[VERIFIED 3-0]**
5. **Raw diffing is commoditized; the moat is the ledger.** Redline tools are a crowded, cheap market. The defensible asset is the longitudinal, entity-resolved **promise ledger** — a growing, point-in-time-correct record of what each company claimed and what happened — because it compounds with time and cannot be back-filled cheaply by a late entrant. See §7.
6. **Canada is a trap; Europe is opening up.** SEDAR+ terms prohibit scraping, database-building, and commercialization outright — verified against the actual ToS. Meanwhile the EU's ESAP and existing free national mechanisms (see §5) are the international expansion path.
7. **You are customer #1.** The multibagger stock engine needs event/filing ingestion that is point-in-time correct. This product's machine-readable output is exactly that feed — which both de-risks product-market fit and enforces the right data discipline from day one (§7.4).

## 2. The free backbone: SEC EDGAR **[VERIFIED 3-0]**

| Fact | Detail | Source |
|---|---|---|
| Cost | Free. No API key, subscription, or license. US-government work; storable, transformable, republishable | [SEC: Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) |
| Press releases | Companies file material press releases as exhibits (typically EX-99.1) to Form 8-K; earnings PRs under Item 2.02 | same |
| Rate limit | Hard cap 10 requests/second regardless of machine count, per-IP, ~10-minute 403 block on breach | same |
| Identification | Mandatory declared `User-Agent: Company Name admin@email` or requests are denied | same |
| Bulk path | SEC explicitly prefers nightly bulk ZIPs (`companyfacts.zip`, `submissions.zip`) + index files for backfill | same |
| Archive | Full-text search (efts.sec.gov) covers all electronic filings + exhibits since 2001-05-04; 1993+ index-browsable | same |
| Latency | Free endpoints: minutes-level. Sub-second dissemination = paid PDS feed | same |
| Format caveat | JSON APIs cover *structured* data; the documents/exhibits themselves are HTML/text (a claim that everything is JSON was refuted 0-3) | verifier finding |

Design consequences: poll ≤10 req/s for freshness, bulk ZIPs for the 2001+ backfill, compliant User-Agent from day one.

## 3. Newswire and news-API ingestion **[BEST-EFFORT — single-pass primary-source fetch]**

> The adversarial pass produced zero *verified* claims about commercial API pricing (marketing pages don't survive a 3-verifier bar; several pages block fetchers). The tables below were compiled directly from vendors' own pricing/terms pages in a follow-up pass. Treat as accurate-as-of-2026-07-14, re-verify before contracting.

<!-- FILL:FINANCIAL_APIS -->

<!-- FILL:GENERAL_NEWS_APIS -->

<!-- FILL:WIRE_RSS -->

## 4. Legal posture **[VERIFIED 3-0 unless noted]**

1. **Facts are uncopyrightable** (Feist; 17 U.S.C. §102(b)). The US Copyright Office's June 2022 study found headline+lede aggregation "more likely to reproduce unprotectable ideas and facts" than protected expression, and declined to recommend an EU-style press-publishers' right. No US federal or state ancillary right exists as of mid-2026. A diff product that *re-expresses* extracted facts sits even further on the safe side. [USCO study](https://www.copyright.gov/policy/publishersprotections/202206-Publishers-Protections-Study.pdf)
2. **Fair use bounds verbatim reuse, not analysis.** Near consensus: large extracts or full articles exceed fair use; headline + very small snippet + link is likely fine; everything between is fact-dependent. Practical rule: full text stored internally for analysis; published output = re-expressed facts, diffs, short attributed snippets. [USCO; RCFP](https://www.rcfp.org/journals/news-media-and-law-summer-2012/content-aggregation-spreadi/)
3. **Hot-news misappropriation is a residual, not a blocker.** NBA v. Motorola (2d Cir. 1997) and Barclays v. Theflyonthewall (2d Cir. 2011) held the tort largely preempted; republishing time-sensitive *facts* is not by itself actionable.
4. **The cautionary template is AP v. Meltwater (SDNY 2013)** — a *paid* clipping service, taking *lengthier excerpts than typical aggregators*, *not driving traffic back*, lost on fair use at summary judgment, then settled. That is the fact pattern to design away from — we are an analysis product, not a clipping service. *(Confidence: medium — secondary press coverage of a settled district-court case.)*
5. **Refuted (0-3), do not rely on:** "press releases carry implicit consent to republish because issuers want distribution." The PR industry's plagiarism norms do not create a legal license.
6. **Not yet assessed (open):** EU press-publishers' right (DSM Art. 15), EU database right, UK/EU text-and-data-mining exceptions. Required before serving or sourcing from Europe. Also: each commercial API's ToS overrides all of the above doctrine for content obtained *through that API* — contract beats copyright analysis.
7. **Canada / SEDAR+ is out** as a scraped source: the ToS license only *unaltered* extracts for informational/internal use, and expressly prohibit commercialization, database construction, and robots/scraping — a diff product breaches all of these simultaneously. Canadian coverage = paid ASC bulk-data license, a commercial redistributor, or cross-listed companies' EDGAR filings. [SEDAR+ ToS](https://www.sedarplus.ca/onlinehelp/terms-of-use/)

## 5. Non-US regulatory feeds **[BEST-EFFORT — single-pass primary-source fetch]**

<!-- FILL:REGULATORY_FEEDS -->

## 6. Open-data bulk: Common Crawl CC-NEWS **[VERIFIED 3-0]**

Daily WARC drops (often within hours of capture) at `s3://commoncrawl/crawl-data/CC-NEWS/`, continuous archive back to August 2016 (~1.3B articles processed by academic users). Two verified caveats: coverage is partial (~83% of sampled news domains in a 2026 census; press-release wire coverage depends on crawler seeds — unguaranteed), and the claim that access is entirely free without an AWS account was **refuted 0-3** — budget AWS access/egress/compute. Role in the stack: retrospective backfill and a redundancy layer, not the primary live feed. [commoncrawl.org/news-crawl](https://commoncrawl.org/news-crawl)

## 7. Is the analysis worth anything? The evidence **[VERIFIED 3-0]**

**"Lazy Prices" (Cohen, Malloy & Nguyen — NBER WP 25084; Journal of Finance 2020):** textual changes between a company's current and prior 10-K/10-Q strongly predict future returns — a portfolio shorting "changers" and buying "non-changers" earned up to 188 bps/month alpha (>22%/yr, 1995–2014) — and predict *concrete fundamentals*: future earnings, profitability, news, and firm-level bankruptcies. Markets are slow to price disclosure changes; the information is real. [NBER](https://www.nber.org/papers/w25084)

Three honest qualifications: (a) evidence is on SEC filings, not press releases — our EDGAR-first stack applies it directly, but PR-text diffing is an untested extrapolation; (b) the tradeable return spread is likely partially arbitraged post-publication (McLean-Pontiff decay); (c) crucially, the *fundamental-prediction* results — the basis for a promise ledger — are not decay-sensitive the way trading alpha is. The paper also found no announcement-day effect: returns accrue when the change's meaning is later revealed. That is precisely the gap this product monetizes for humans: surfacing the change *at disclosure time* instead of quarters later.

## 8. Competitive landscape **[BEST-EFFORT — single-pass]**

<!-- FILL:COMPETITORS -->

**Verified data point:** raw document comparison is commoditized — Draftable (~$249/user/yr legal tier, free tool, API), Litera Compare (~72% of the legal industry), Word Compare, Acrobat. Diff *mechanics* cannot be the moat. **[VERIFIED 3-0, medium confidence on exact figures]**

## 9. Moat assessment — real vs weak

| Moat candidate | Verdict | Why |
|---|---|---|
| **Longitudinal promise ledger** (entity-resolved claims → outcomes, point-in-time correct) | **REAL — the moat** | Compounds with time; a late entrant must reconstruct history without contaminating it with hindsight. Academically underwritten (§7: disclosure changes predict fundamentals). Directly analogous to multibagger's retrodiction/Kaizen philosophy applied to issuers. No verified evidence any incumbent ships this (see §8 whitespace check). |
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
5. **International regulatory (free-first):** per §5 — sequence by what's genuinely free and licensed for reuse (EDINET-style APIs, ESAP as it comes online) and defer license-required venues (SEDAR+, licensed RNS) until revenue justifies them.
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

*Sources: all VERIFIED-tagged findings trace to the deep-research run of 2026-07-14 (22 claims confirmed 3-0 against primary sources: sec.gov, sedarplus.ca, copyright.gov, commoncrawl.org, nber.org, rcfp.org, hudson-labs.com). BEST-EFFORT sections cite vendors' own pages inline. Full verification journal preserved in the session transcript.*
