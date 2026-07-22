# World Monitor applicability review — what koala73/worldmonitor offers OneLive, the Promise Ledger, and the Multibagger

**Status:** REVIEW (founder-requested 2026-07-22: "Evaluate this deeply for application to
OneLive or the Multibagger"). Nothing here is a build decision; every adoption
candidate below routes through the normal queues and gates. Session Contract #20
(STATE.md).

**Subject:** <https://github.com/koala73/worldmonitor> — "World Monitor", a real-time
global-intelligence dashboard by a single author (Elie Habib). Reviewed from a fresh
clone at commit `040424f` (2026-07-22, v2.10.0), read by one code-sweep agent pass
plus targeted direct reads. Provenance: single-pass code reading of the actual
repository — stronger than a marketing-page read, weaker than adversarial
multi-agent verification; file paths are cited so any claim can be re-checked.

---

## 1. What it is (plain language)

World Monitor aggregates ~65 external data providers — news RSS (500+ curated
feeds), GDELT, conflict databases (ACLED/UCDP), earthquakes, weather alerts,
flight/ship tracking, sanctions lists, financial APIs, prediction markets, and
more — into one live map-plus-panels web dashboard, with six themed variants
(world / tech / finance / commodity / happy / energy) served from one codebase by
hostname. It is unusually production-grade for a solo project: 21 CI workflows,
per-variant visual-regression screenshots, a native desktop app (Tauri), a REST
API with SDKs in three languages, a 40-tool MCP server for AI agents, and a paid
tier ladder ($0 → $39.99 → $99.99 → $249.99 → enterprise) with self-serve API keys.

Its analytical spine: a Country Instability Index (hand-tuned weighted scoring of
unrest/conflict/security/information signals per country), a correlation engine
(clusters co-occurring signals by country/entity/proximity and flags escalation),
temporal z-score anomaly detection ("3× normal military flights for a Tuesday"),
and LLM summarization/briefing on top (Groq/OpenRouter/Ollama chain — notable:
fully self-hostable with zero API keys via local Ollama).

## 2. The license gate — read this first

World Monitor is **AGPL-3.0-only** (declared in its package manifest, line 5; 34KB LICENSE; README offers
commercial dual-licensing as a paid alternative). AGPL's network clause means any
service that incorporates its code must offer that service's source to users.
Consequences for us, stated as rules for this review:

1. **No code copying into OneLive, the Promise Ledger, or the Multibagger.**
   All three are private-source products; importing AGPL code would obligate
   source disclosure or a commercial license (money + legal posture = two
   founder-crucial categories at once). Nothing below recommends importing code.
2. **Ideas, algorithms, and architecture patterns are fair game.** Copyright
   covers expression, not ideas; everything recommended below is
   pattern-level adoption re-implemented in our own code. For anything
   substantial we keep clean-room discipline: work from this review's
   descriptions, not from their source files open in the editor.
3. **Their curated feed *lists* are treated as AGPL content too** (a curated
   compilation is their expression). We use them as *leads* — the fact that
   "SEC press releases have an RSS feed at sec.gov" is a fact we verify and
   curate independently; we do not bulk-copy their feed configuration files.

Alternative considered: buying their commercial license to reuse code directly.
Rejected — we need patterns, not their code (different stacks: they are
vanilla-TS/Vercel/Redis, we are Python/FastAPI/Supabase + Next.js), so the
license would buy nothing the patterns don't. Tradeoff of the clean-room rule:
slower than copying, and honestly stated as such; it is the only posture that
avoids a founder-crucial legal decision entirely.

## 3. Is it a competitor to the Promise Ledger? (checked before admiring it)

No — and the check strengthens the whitespace map
(`docs/research/PR_AGGREGATOR_MARKET_ANALYSIS.md` §10). Their finance variant
*displays* regulatory press releases (SEC/CFTC/Fed/FDIC/FINRA RSS, keyword-
classified by severity in `scripts/seed-regulatory-actions.mjs`) but is
forward-only situational awareness: no claim extraction, no longitudinal ledger,
no point-in-time storage, no promise semantics, no per-claim provenance. It
partially occupies "machine-readable feed for AI agents" (28 cache tools + RPC
tools over MCP) — but for *situational* data, not claim semantics; Daloopa-like
in shape, not a promise ledger. Two market facts it contributes: (a) a solo
project sells agent-native intelligence access at $99.99–249.99/mo — live pricing
evidence for the chasm-pricing thesis; (b) its MCP registry is a working
reference for exactly the "Ledger × agents" play we ranked combinatorial
opportunity #1.

## 4. Applicability to OneLive

OneLive context: Steps 6–10 (golden-set gate → gate/candidate flow → admin review
→ /tonight → deploy), 20-minute ingestion cron freshly armed (PR #43 arc),
provenance-weighted gate design queued at Step 7.

### 4.1 Patterns worth adopting (each with why-this-not-that)

**A. Source-tier + multi-source triangulation as prior art for the Step-7
provenance-weighted gate.** They maintain numeric trust tiers per outlet
(the `shared/source-tiers` JSON config), classify sources by type (wire/gov/mainstream),
weight cluster confidence by tier, and emit a "triangulation" signal only when
wire + government + independent sources align. Their news-conflict floor
requires ≥2 high-tier sources across ≥2 distinct domains before a conflict
claim moves a country's score (`src/services/country-instability.ts`). This is
independently convergent with our gate3 corroboration ("held on insufficient
corroboration" in the arming smoke runs) — external validation that
tier-weighted, multi-domain corroboration is the right shape. Adopt as **design
input to the Step-7 gate doc**, citing this review; PR #4 was closed as
reference-draft for exactly that gate. Alternative: invent our weighting from
scratch — rejected, free prior art with production mileage beats a blank page.
Tradeoff: their tiers are hand-tuned editorial judgments; ours must stay
evidence-grounded (first-party channel > wire > aggregator) per the ratified
sensor architecture, so we take the *mechanism*, not their numbers. Their model
also has no human gate — signals publish straight to users — which is the
antithesis of AI-never-publishes; the mechanism imports, the publish model
never does.

**B. Unicode-safety lint (Trojan Source / zero-width / bidi controls).** Their
`scripts/check-unicode-safety.mjs` scans the whole tree for bidi control
characters, zero-width/invisible characters, variation-selector steganography,
and private-use-area payloads. OneLive ingests untrusted scraped text into an
extraction pipeline that already caught one live prompt-injection marker (DICE,
smoke run 29873390712) — invisible-character smuggling is a real adjacent
channel, both in ingested content and in our own source tree (agent-written
code is the Trojan-Source paper's core threat model). **Adopt: add an
equivalent check to `tools/lint.py`** (our own implementation, ~a page of
Python over the same character classes). This is a gate *tightening*, never a
relaxation — still routed through the evaluator like every gate-custody change.
Alternative: rely on GitHub's bidi warning UI — rejected: not blocking, not
local, silent for zero-width classes. Tradeoff: a rare legitimate use of exotic
Unicode in test fixtures would need an explicit allowlist entry (fine — loud
beats silent).

**C. Freshness metadata + staleness monitoring per source.** Every seed write
records `{fetchedAt, recordCount}`; a 15-minute CI cron fails when production
data goes stale (`scripts/check-seed-freshness.mjs`, seed-freshness workflow).
We have the dead-man ping for the *loop*; this is the per-*source* analog, and
it maps 1:1 onto the queued Watcher-records item ("freshness SLOs", P1 gated on
Step 7). Adopt as design input there — our raw_fetch ATTEMPT rows (PR #43 r2)
already give us the data; what's missing is the per-source staleness *alarm*.
Tradeoff: none now (it rides an existing queue item); at build time the cost is
choosing SLOs honestly per source cadence rather than one global number.

**D. Caching discipline for the /tonight budget (Step 9/10).** Their four-layer
cache (seed → in-memory → Redis → upstream), ETag/304 on API responses, and
"Lever Test" cost framing (egress ≈ origin-miss count × payload size) are the
right mental model for our CWV budget (LCP ≤ 2.5s) and Supabase egress costs.
Adopt as pattern-level guidance in the Step-9 implementation notes. Alternative:
Next.js defaults only — workable but leaves the API layer uncached; their
tier-by-volatility table is a better starting point than ad-hoc TTLs.

**E. Single codebase, hostname-selected variants.** Six products from one tree
(`src/config/variant.ts`) with variant-keyed feeds/panels/refresh rates. Not
needed now; file for the multi-metro expansion (Austin → second metro), where
metro-keyed config (already our direction: "config-not-code" in the
metro_outline TODO) beats forked deployments. No action today.

### 4.2 What NOT to take

- **Their trust display.** Severity chips and instability scores shown as flat
  authority with no confidence states, no dispute surface, no provenance on the
  card. Ours is ratified canon (4-state + Certainty Display Stack); theirs
  would be a regression.
- **Hand-tuned scoring constants** (0.25/0.30/0.20/0.25 weights, log pivots,
  boost caps). The *structure* (component scores → weighted blend → floors →
  trend deadband) is instructive; the constants are editorial opinion we'd
  never ship without golden-set evidence.
- **LLM-published briefs.** Their daily briefs are model output published
  directly to users. AI-never-publishes: our equivalent (if ever) is
  Descriptor-Foundry-style — gated, provenance-stamped, golden-regressed.

## 5. Applicability to the Promise Ledger (and through it, the Multibagger)

Multibagger context (from the research docs, `PR_AGGREGATOR_RESEARCH.md` §11):
its stated gaps are the stock engine's event-calendar ingestion and
point-in-time-safe data inputs (yfinance forbidden); the Promise Ledger is the
planned feed, Multibagger is customer-zero.

**A. Five free official-agency press-release feeds — direct ingestion-stack
leads.** `seed-regulatory-actions.mjs` polls SEC press releases
(`sec.gov/news/pressreleases.rss`), CFTC enforcement, Federal Reserve, FDIC
(govdelivery), and FINRA feeds. For the ledger these are the *consequence* side
of promises — enforcement actions are fulfillment/violation evidence for the
4-state verdicts, and regulator-published text is the lowest-ToS-risk source
class we have (same class as issuer IR-page RSS, stack item 3). **Adopt: add
these five to the venture's candidate source list** (verify each feed URL and
its terms ourselves — leads, not copied config). R-016 discipline applies as
always, though regulator feeds are the class most likely to clear it trivially.
Alternative: wait for ESAP/EDGAR only — rejected: enforcement RSS is free,
live today, and fills the promise→consequence link EDGAR filings alone don't.

**B. Earnings calendar / insider transactions — the Multibagger's
event-calendar gap, with a warning label.** They ingest Finnhub's earnings
calendar and SEC Form-4 insider transactions (with a small
transaction-code-to-conviction scorer, `get-insider-transactions.ts`). This is
exactly the shape of the Multibagger's missing event-calendar input — but
World Monitor is a live dashboard with **no point-in-time discipline**: it
overwrites state in a cache, which is the precise property that got yfinance
banned. So the lead transfers, the architecture does not: any calendar feed
enters the Multibagger only through the ledger's append-only, as-of-known-when
store. Finnhub itself is R-016-class (redistribution terms unverified — a
fifth provider letter if pursued). Form 4 data is also available first-party
from EDGAR (free, sanctioned), which our EDGAR client already targets —
prefer that; Finnhub only earns a place as a convenience layer if its terms
clear. Prediction-market APIs (Polymarket/Kalshi, free) are a second
catalyst-probability lead of the same class.

**C. Signal taxonomy for silence detection.** Their correlation engine names
`silent_divergence` (channels that normally move together, diverging),
`explained_market_move` vs unexplained, and `prediction_leads_news`. This
vocabulary — and the z-score-against-temporal-baseline mechanic ("N× normal
for this weekday") — is directly reusable *as design language* for the
ledger's silence/overdue-disclosure alerting (whitespace row 2, harvest H8):
a company's disclosure cadence is a temporal baseline; silence is a z-score
anomaly on it. Cheap, concrete, and nobody occupies that whitespace. Adopt
into the H8 design when it builds.

**D. The agent-native surface — a working reference implementation of our
plan.** Their MCP registry (28 cache tools + RPC tools, a universal `summary`
+ JMESPath query parameter on every tool, `describe_tool`, OAuth dynamic
client registration, `llms.txt`, `.well-known/agent-skills/` with SKILL.md
directories, self-serve keys, per-tool byte-budget lint) is the most complete
open example I've seen of the "MCP-first, three-tier pricing" distribution the
market analysis ranked play #1. When the ledger's MCP surface builds, study
this as the reference (design study, not code reuse — §2). Their
tool-description byte-budget check (`mcp-budget-check.mjs`) is a genuinely
clever guard we should replicate: agent tool lists are a context-cost surface.

**E. Entitlement plumbing, filed for later.** Clerk auth + Convex real-time
entitlements + Dodo payments + self-serve `wm_` keys is a complete reference
stack for the venture's eventual seat/API pricing. New services/money =
founder-crucial when the time comes; no action now, pointer recorded here.

## 6. Engineering-harness patterns (both products, our own gates)

Beyond §4.1-B (unicode lint — the one immediate adoption), three of their guard
patterns are convergent with what we already built, which is mutual validation
rather than new work: their rate-limit-policy drift lint ≈ our
`workflow_env_lint` (both kill silent fail-open via config/name drift); their
CI-verified docs-stats (capability counts asserted against code) ≈ our
`governance_claims_lint` (prose never ahead of mechanism); their architectural
boundaries lint ≈ our trust_gate import bans (orchestrator cannot import the
promote path). One pattern worth queuing cheaply: **hash-baseline "must stay
empty" enforcement** (their safe-html lint pins `innerHTML` call sites to an
empty baseline with no update flag) — a reusable shape for any "this class of
code must never grow" rule; candidate first use: `dangerouslySetInnerHTML` in
`apps/web` at Step 9. Their `AGENTS.md` (agent operating manual with recipes
and dependency-direction rules) is their CLAUDE.md-equivalent; ours is already
stronger on governance, theirs is stronger on task recipes ("adding an
endpoint/panel" cookbooks) — worth imitating at the next docs touch for the
Step-7+ stages.

## 7. Recommendations, consolidated (cost-disciplined)

| # | Action | Product | Cost | Route |
|---|--------|---------|------|-------|
| 1 | Unicode-safety check in `tools/lint.py` (own implementation) | OneLive harness | ~hours | Gate-custody PR, evaluator mandatory; tightening-only |
| 2 | Cite §4.1-A (tiers/triangulation/floors) in the Step-7 provenance-gate design | OneLive | ~zero (design input) | Step-7 contract |
| 3 | Per-source freshness SLO alarm — fold §4.1-C into the queued Watcher-records item | OneLive | ~zero now | Existing P1 TODO, gated on Step 7 |
| 4 | Add the 5 regulator PR feeds + prediction-market APIs as verified-by-us source candidates | Promise Ledger | ~hours at next venture session | Venture docs; R-016 discipline |
| 5 | Prefer EDGAR-first for Form-4/event-calendar; Finnhub only if terms clear (5th letter) | Multibagger via ledger | ~zero now | R-016 path |
| 6 | H8 silence detection uses cadence-baseline z-scores + their signal vocabulary | Promise Ledger | ~zero (design input) | H8 build contract |
| 7 | MCP surface: study their registry as reference implementation at build time | Promise Ledger | ~zero now | Ledger-MCP contract |
| 8 | Hash-baseline "must stay empty" lint shape; first use at Step 9 web code | OneLive harness | small | Step-9 PR |

Nothing above spends money, adds a service, touches a trust invariant, or
relaxes a gate. Items 1 and 8 *add* gates and therefore still route through the
mandatory evaluator (gate custody covers additions too — the evaluator checks
the new gate can actually fail).

## 8. Sources

- Clone: github.com/koala73/worldmonitor @ `040424f` (2026-07-22, v2.10.0),
  read in-session (single-pass agent sweep + direct reads); the sweep agent's
  full dossier is committed VERBATIM at
  `docs/research/worldmonitor_sources/APPENDIX_A_CODE_SWEEP_DOSSIER.md`
  (in-diff evidence rule, PR #47 r6 nit). Key files cited
  inline: `ARCHITECTURE.md`, `CONCEPTS.md`, `AGENTS.md`, `SELF_HOSTING.md`,
  the package manifest, `scripts/seed-regulatory-actions.mjs`,
  `scripts/check-unicode-safety.mjs`, `scripts/check-seed-freshness.mjs`,
  `scripts/enforce-safe-html.mjs`, the `shared/source-tiers` config,
  `src/services/country-instability.ts`, `src/services/correlation-engine/`,
  `src/services/temporal-baseline.ts`, `src/services/analysis-core.ts`,
  `server/worldmonitor/market/v1/get-insider-transactions.ts`, `api/mcp/`.
- OneLive canon: `docs/research/PR_AGGREGATOR_MARKET_ANALYSIS.md` (§10–§12),
  `docs/research/PR_AGGREGATOR_RESEARCH.md` (§10–§11), `docs/RECORD.md`
  (R-016/R-017), STATE.md contracts #14–#19, the PR #43 arming arc
  (changelog 2026-07-21/22).
