# 1LIVE — Claim Ledger v1

**Created 2026-08-01 at founder direction ("Go with 1–4" on the external review
of the Model deliverable). Purpose: every load-bearing number or capability
claim in founder-/partner-facing materials carries ONE row here with its
source, population, approved wording, and evidence badge. A claim not in this
ledger does not ship with a number attached. Review dates are objective
triggers (RECORD discipline).**

**Evidence badges:** OBSERVED (live campaign, records retained) ·
DEMONSTRATED (system produced the artifact in a controlled run) ·
ESTIMATED (calculated from stated assumptions) · EXTERNAL BENCHMARK
(cited third-party research, population preserved) · PILOT TARGET (success
criterion, not a result) · HYPOTHESIS (to be tested).

| id | claim (as previously used) | approved wording | source · date | population/scope | badge | review by |
|---|---|---|---|---|---|---|
| C-01 | "83% of local businesses are invisible in AI answers" | "83% of restaurant/QSR locations were invisible in AI-generated recommendations (Uberall benchmark study, 2026) — a proxy for the broader local gap, not a measurement of it" | Uberall via BusinessWire · 2026-05 | US restaurant/QSR locations in Uberall's dataset | EXTERNAL BENCHMARK | 2027-02 |
| C-02 | "45% of consumers ask AI where to go" | "45% of surveyed US consumers say they have used AI to get local-business recommendations (BrightLocal survey, 2026)" | BrightLocal / Bloom Intelligence cite · 2026 | surveyed US consumers | EXTERNAL BENCHMARK | 2027-02 |
| C-03 | "~70% of ChatGPT local recommendations draw on Yelp/Foursquare" | RETIRED as a number. Approved: "AI assistants draw heavily on established local databases (Yelp, Foursquare, GBP-class data); being present and fresh there is the reliable path into AI answers" | prior vendor analyses; no primary source of sufficient quality | — | HYPOTHESIS (directionally supported) | before any external use |
| C-04 | "ChatGPT retrieval runs largely on Bing" | RETIRED. Approved: "OpenAI documents OAI-SearchBot as the crawler for ChatGPT search visibility; we allow it (and submit via IndexNow, which is notification, not guaranteed indexing)" | OpenAI crawler docs · Microsoft IndexNow docs · 2026 | — | EXTERNAL BENCHMARK (documented mechanism) | 2027-02 |
| C-05 | "97% of AI crawls ignore llms.txt" | "Ahrefs measured ~97% of AI crawler hits not requesting llms.txt; Google states no AI system uses it. We deploy it as a zero-cost hedge, never as strategy" | Ahrefs study; Google statements · 2025–26 | Ahrefs-observed crawl sample | EXTERNAL BENCHMARK | 2027-02 |
| C-06 | "email returns $36–42 per $1" | "industry benchmark studies place email marketing returns around $36–$42 per $1 spent — the highest of the major channels; methodology varies by study" | DMA/Litmus-lineage figures via BizIQ roundup · 2025–26 | cross-industry benchmark, not segment-measured | EXTERNAL BENCHMARK | 2027-02 |
| C-07 | "social ads ~$5 : paid search ~$8 : local SEO ~$13 per $1" | "SMB benchmark roundups report indicative returns of roughly $5 (social ads), $8 (paid search), $13 (local SEO) per $1 — indicative ordering, not precise constants" | BizIQ local-marketing statistics · 2025–26 | US SMB roundup | EXTERNAL BENCHMARK | 2027-02 |
| C-08 | "76% of local searchers visit within 24h" | "76% of consumers who search locally on a smartphone visit a business within 24 hours (industry research via Data Axle)" | Data Axle citing Google-lineage research | US mobile local searchers | EXTERNAL BENCHMARK | 2027-02 |
| C-09 | agency/freelancer pricing ($300–$1.5k freelance; $500–$25k agency tiers; $1k–$5k venue social) | as stated with tier labels and "typical ranges" | SolidGigs · SocialRails · NewMedia · Sprout · 2025–26 | US SMB market rates | EXTERNAL BENCHMARK | 2027-02 |
| C-10 | GEO/AEO retainers $1.5k–$25k/mo | as stated ("advertised retainer ranges") | assessment §16 sources · 2026 | US agency market | EXTERNAL BENCHMARK | 2027-02 |
| C-11 | worked-example outcomes (38 door codes · 41 signups · 9 club conversions · 62 taps · 12 signups · "carousel beat flyer 3-to-1" · owner minutes) | ALWAYS carry the badge "ILLUSTRATIVE — pilot targets, not observed results"; the 3-to-1 line is additionally a measurement HYPOTHESIS pending controlled comparison | internal design targets | fictional composites | PILOT TARGET | at first pilot readout |
| C-12 | Continental Club facts, states, and the Do512 "Friday" drift catch | as recorded in ONE_LIVE_CASE_STUDY_CONTINENTAL_v1.md, badge DEMONSTRATED; scope: extraction, corroboration, conflict detection, preview, drafting, structured data — NO live publishing, NO measurement | session run · 2026-08-01 | one venue, one run, search-snapshot read path (R-063) | DEMONSTRATED | R-063 trigger |
| C-13 | "set up from one pasted URL, ≤3 taps" | "paste one link → complete PREVIEW in minutes, no accounts connected. Activation is progressive: connect only the channels you choose; some require platform authorization or approval" | product design + platform API requirements | — | PILOT TARGET (preview) / capability-dependent (activation) | at pilot |
| C-14 | "updates everywhere within the hour" | "1Live updates connected channels immediately, reports each platform's publication status, and monitors until the change is public — submission, acceptance, display, and indexing are distinct states" | connector reality (registry) | — | PILOT TARGET | at pilot |
| C-15 | Gartner 7.7% budgets · Census 30.4M nonemployers · NIVA 64% · Brewers Assoc 434/268 · $10.3B listings leak · 68% would stop · ~40% tickets unsold | as sourced inline in Part I / research companions, populations preserved | per-claim sources in those docs | per claim | EXTERNAL BENCHMARK | 2027-02 |

**Standing rules:** (1) fictional examples never share visual styling with
observed data unless badged; (2) a retired wording (C-03, C-04) must not
reappear; (3) capability claims about platforms defer to
`ONE_LIVE_CONNECTOR_REGISTRY_v1.md` — marketing copy never outruns the
registry; (4) new numeric claims enter this ledger in the same commit that
uses them; (5) every reported OUTCOME carries a measurement class from
`ONE_LIVE_TRUTH_STATES_v2.md` §4 (directly tracked / attributed / assisted /
self-reported / modeled / incremental) — comparative claims without
treatment assignment ship as HYPOTHESIS (founder-ratified 2026-08-01);
(6) a claim's approved wording keeps its population scope verbatim —
restating a scoped benchmark as a universal fact is a defect
(the C-01 "83% of local businesses" escape, caught by the evaluator on
PR #142 r1, now mechanically guarded in `check_artifacts.py`);
(7) ownership-forever claims scope to the TIER-1 BASICS only (corrected
listings, live calendar, website widget, customer list, exportable
record) — campaigns/creative/components are service outputs, never a
perpetual-asset promise (founder 2026-08-02; mechanically guarded in
`check_artifacts.py`).
