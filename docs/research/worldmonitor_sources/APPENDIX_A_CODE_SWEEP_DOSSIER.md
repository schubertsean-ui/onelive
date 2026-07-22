# Appendix A — WorldMonitor code-sweep dossier (verbatim agent output)

Provenance: single code-sweep agent over a fresh clone of
github.com/koala73/worldmonitor @ `040424f` (v2.10.0), 2026-07-22,
commissioned for Session Contract #20
(docs/research/WORLDMONITOR_APPLICABILITY_REVIEW_v1.md). Committed VERBATIM
per the in-diff evidence rule (PR #47 evaluator r1/r6 nit; PR #18 r6–r7
precedent). Unlike the two web fan-outs, this is a DIRECT READ of the
subject codebase (file paths cited throughout are verifiable against the
public repo), single-pass, one agent.

---

# World Monitor — Technical Dossier

Repo: `github.com/koala73/worldmonitor` · License AGPL-3.0-only · ~1,355 TS + 957 mjs files · 156 seed scripts · 21 CI workflows · 281 protos/35 services. Single author (Elie Habib). Actively maintained (recent commits dated 2026-03..07).

## 1. WHAT IT IS

**Purpose.** A real-time global-intelligence dashboard: aggregates 65+ external providers into a unified map + panel UI (`ARCHITECTURE.md:9`, `README.md:51-63`). Vanilla-TypeScript SPA (no React), dual map engine, 56 map-layer types, 500+ curated news feeds, server-authoritative country risk scoring.

**Product surfaces.**
- **Web SPA** (`index.html`, `src/main.ts`, `src/App.ts`), deployed on Vercel.
- **6 hostname-detected variants** from one codebase (`src/config/variant.ts`): `full` (world), `tech`, `finance`, `commodity`, `happy`, `energy`. Variant controls default panels, layers, refresh intervals, theme, feeds (`ARCHITECTURE.md:114-116`; feeds in `src/config/feeds.ts` keyed `VARIANT_FEEDS`).
- **Native desktop** via Tauri 2 (Rust) + Node.js sidecar — macOS ARM64/x64, Windows x64, Linux (`src-tauri/`). One binary switches variants in-app.
- **Embeddable widget** (`embed.html`, `src/embed/`, `src/embed-main.ts`).
- **CLI** (`cli/`, npm `worldmonitor`/`wm`), **SDKs** (`sdk/python`, `sdk/ruby`, `sdk/go`), **MCP server**, **REST API**.
- **Blog** (`blog-site/`), **Mintlify docs** (`docs/`), **pro-test** standalone QA app.

**Maturity — production-grade.** Extensive testing: `node:test` unit/integration (`tests/`), Playwright E2E with per-variant golden-screenshot visual regression (`e2e/`, `playwright.config.ts`), sidecar tests, API tests. 21 GitHub Actions workflows (`ARCHITECTURE.md:360-384`) including typecheck, biome lint, proto-freshness, feed-validation (daily cron), security-audit (npm audit, daily), **seed-freshness-monitor (15-min cron)**, mcp-live-smoke (6-hourly), multi-platform desktop build w/ code signing, docker multi-arch publish, and OIDC trusted-publishing for CLI/PyPI/RubyGems/Go. Husky pre-push hook runs tsc, CJS validation, esbuild bundle check, import guardrails, markdown/MDX lint, version sync (`.husky/pre-push`). Docs quality high: `ARCHITECTURE.md` (26KB), `CONCEPTS.md` (glossary), `AGENTS.md`, `CONTRIBUTING.md`, `SELF_HOSTING.md`, CHANGELOG (56KB); capability counts are CI-verified against code via `npm run docs:check` (`scripts/docs-stats.mjs`).

## 2. DATA SOURCES

Ingested via ~156 `scripts/seed-*.mjs` (write to Redis) and server RPC handlers (`server/worldmonitor/<domain>/v1/`). Key providers (host list extracted from `scripts/seed-*` and `server/`):

**News / OSINT / local-events relevant:**
- **RSS feeds** — 500+ curated, defined in `server/worldmonitor/news/v1/_feeds.ts` (`VARIANT_FEEDS`) and `src/config/feeds.ts`. Mix of direct publisher RSS (BBC `feeds.bbci.co.uk`, NPR, PBS, ABC, WSJ `feeds.content.dowjones.io`, Politico, Axios, Tagesschau, ANSA, NOS, etc.) and **Google News RSS search** proxied (`news.google.com/rss/search?q=site:...when:1d` via `gn()` helper). Free/scraped through `api/rss-proxy.js` (SSRF-guarded allowlist `shared/rss-allowed-domains.json`).
- **GDELT** — `api.gdeltproject.org` / `data.gdeltproject.org` (free, no key). `seed-gdelt-intel.mjs`, `src/services/gdelt-intel.ts`, tone timelines (military/nuclear/maritime). Article search + tone.
- **Telegram** — `api.telegram.org`, `t.me` channels (`data/` telegram channels, `src/services/telegram-intel.ts`, `api/telegram-feed.js`).
- **Reddit** — `oauth.reddit.com` (self-serve API app; needs credentials).
- **HackerNews** — `hacker-news.firebaseio.com`, `hnrss.org` (free); `server/.../research/v1/list-hackernews-items.ts`.
- **OREF (Israel Home Front Command)** rocket alerts — `api.tzevaadom.co.il` + relay OREF polling (`src/services/oref-alerts.ts`, `data/` OREF threat translations). Real-time local alerting.
- **Earthquakes** — USGS `earthquake.usgs.gov` (free). `seed-earthquakes.mjs`, `src/services/earthquakes.ts`.
- **Weather alerts** — NWS `api.weather.gov` (free); `seed-weather-alerts.mjs`, `src/services/weather.ts`.
- **NASA FIRMS** fire detections — `firms.modaps.eosdis.nasa.gov` (free key). Wildfires.
- **ACLED** conflict events (`acleddata.com`, free-for-researchers OAuth), **UCDP** (`ucdpapi.pcr.uu.se`, free), **HDX/HAPI** humanitarian (`hapi.humdata.org`).
- **Positive/"feelgood" events** — curated RSS (`reasonstobecheerful.world`, `humanprogress.org`, etc.), classified server-side.
- **US travel advisories** — `travel.state.gov` + AU/UK/NZ (embassy `*.usembassy.gov` feeds).

**Finance / disclosures / press-release relevant:**
- **Finnhub** (`finnhub.io`, free tier, keyed) — **insider transactions (SEC Form 4)** (`server/.../market/v1/get-insider-transactions.ts`: parses P/S/M/A/D/F transaction codes, computes buy/sell conviction), **earnings calendar** (`seed-earnings-calendar.mjs`), stock analysis.
- **Regulatory actions** — `seed-regulatory-actions.mjs` scrapes **official agency RSS**: SEC press releases (`sec.gov/news/pressreleases.rss`), CFTC enforcement, Federal Reserve, FDIC (`public.govdelivery.com`), FINRA (`feeds.finra.org`). Keyword-severity classified (HIGH: enforcement/fraud/fine/cease-and-desist; MEDIUM: rulemaking/guidance/investigation). Canonical key `regulatory:actions:v1`. **Directly relevant to press-release intelligence.**
- **Yahoo Finance** (`query1.finance.yahoo.com`, free/scraped) — quotes/market data.
- **FRED** (`fred.stlouisfed.org`), **EIA** (`api.eia.gov`), **IMF SDMX** (`api.imf.org`, keyed), **World Bank** (`api.worldbank.org`), **ECB** (`data-api.ecb.europa.eu`), **BIS** (`stats.bis.org`), **Eurostat**, **Comtrade** (`comtradeapi.un.org`), **WTO**, **CFTC COT** (`publicreporting.cftc.gov`), **US Treasury** (`fiscaldata.treasury.gov`), **AAII sentiment**, **Fear & Greed** (`alternative.me`, CNN `dataviz.cnn.io`).
- **CoinGecko/CoinPaprika/Hyperliquid/mempool.space** — crypto.
- **Prediction markets** — Polymarket (`gamma-api.polymarket.com`), Kalshi (`api.elections.kalshi.com`) — free.
- **OpenSanctions** (`api.opensanctions.org`) + **OFAC** (`sanctionslistservice.ofac.treas.gov`), **FATF** — `seed-sanctions-pressure.mjs`, `server/.../sanctions/v1/lookup-entity.ts`.
- **USAspending** (`api.usaspending.gov`), **SAM.gov** (`api.sam.gov`), **TED EU** (`api.ted.europa.eu`), Contracts Finder, CanadaBuys, NZ GETS, World Bank tenders — `seed-global-tenders.mjs` (procurement/tender intelligence).
- **USPTO** Open Data Portal defense patents (`seed-defense-patents.mjs`, keyed).
- **arXiv** (`export.arxiv.org`), **GitHub/OSSInsight** trending repos, **Crunchbase news** — `research/` domain.

**Other infra/geo:** OpenSky/adsb.lol/Wingbits (flights), AISStream (`aisstream.io`, ships — keyed, WebSocket relay), Cloudflare Radar (internet outages — **paid**), NASA EONET, Copernicus/Open-Meteo (climate), GIE/ENTSO-E/JODI/IEA/Ember (energy), Safecast/EPA RadNet (radiation), WHO/CDC/OpenAQ (health), PortWatch/IMF (chokepoints), abuse.ch/AlienVault OTX/AbuseIPDB (cyber).

**Collection methods** summarized in `SELF_HOSTING.md:95-102`: no-key (earthquakes, weather, UNHCR, prediction markets, crypto, cyber, BIS); free-signup-keyed (Groq, FRED, EIA, FIRMS, AISSTREAM, Finnhub, AviationStack, ACLED, OpenRouter); paid (Cloudflare Radar). Many "sources" are Google-News-RSS-scraped or direct-RSS-scraped through the SSRF-guarded proxy.

## 3. ARCHITECTURE

**Deployment topology** (`ARCHITECTURE.md:56-72`): SPA + 60+ Edge Functions on **Vercel**; **Cloudflare Worker** for CORS preflight on `api.worldmonitor.app` (`workers/api-cors-preflight/`); **Railway** runs the AIS relay (`scripts/ais-relay.cjs`) — WebSocket AIS proxy + continuous seed loops + RSS proxy + OREF polling — plus consumer-price Playwright scrapers (`consumer-prices-core/`); **Upstash Redis** cache; **Convex Cloud** for contact-form + waitlist + entitlements; Mintlify docs; GHCR multi-arch Docker image (nginx + Node API).

**Ingestion.** Two paths: (1) **Seed scripts** (`scripts/seed-*.mjs`) fetch upstream → transform → `atomicPublish()` to Redis with a SET-NX lock, writing `seed-meta:<key>` `{fetchedAt, recordCount}` (`scripts/_seed-utils.mjs`, `ARCHITECTURE.md:203-217`). Railway cron + relay seed loops are primary; standalone scripts are backup. (2) **On-demand RPC handlers** (`server/worldmonitor/<domain>/v1/handler.ts`) use `cachedFetchJson()` (`server/_shared/redis.ts`) for cache-miss coalescing.

**Caching — 4-layer** (`ARCHITECTURE.md:290-320`): bootstrap-seed(Redis) → per-instance in-memory → Upstash Redis (stampede-protected) → upstream fetch. Six cache tiers by `s-maxage` (fast 300s … daily 86400s, no-store 0). **ETag = FNV-1a hash** of body → 304. `CDN-Cache-Control` gives Cloudflare longer TTL. Bandwidth costing philosophy in `CONCEPTS.md` ("The Lever Test": egress ≈ origin-miss count × payload size; "Bootstrap View Key" = cache-what-we-show; "One-Shot Hydration" pitfall).

**Bootstrap hydration.** `/api/bootstrap` batch-reads Redis; SPA fetches two tiers concurrently (fast 3s + slow 5s timeouts) with separate abort controllers; panels read via `getHydratedData(key)` — one-shot consumption (`src/services/bootstrap.ts`).

**Frontend rendering.** Dual map (`ARCHITECTURE.md:98-102`): **DeckGLMap** (deck.gl + MapLibre GL, PMTiles self-hosted basemaps, Supercluster clustering, H3HexagonLayer etc.) and **GlobeMap** (globe.gl 3D + Three.js). 105 panel classes extend `Panel` base (`src/components/Panel.ts`), debounced `setContent(html)`, resizable spans persisted to localStorage. No state library — a central mutable `AppContext`. URL state syncs bidirectionally (`src/utils/urlState.ts`). Layer catalog in `src/config/map-layer-definitions.ts`.

**Web Workers** (`src/workers/`): `analysis.worker.ts` (Jaccard clustering + cross-domain correlation); `ml.worker.ts` (ONNX via `@xenova/transformers`); `vector-db.ts` (IndexedDB vector store).

**Refresh scheduling.** `startSmartPollLoop()` — exponential backoff (max 4×), viewport-conditional refresh, tab-pause on hidden, staggered flush (`src/app/refresh-scheduler.ts`).

**Desktop/offline.** Tauri Rust shell manages tray + IPC; stores secrets in OS keyring (Keychain/Cred Manager/libsecret); spawns Node sidecar (`src-tauri/sidecar/local-api-server.mjs`) that dynamically loads Edge Function handlers, injects keyring secrets, forces IPv4. `installRuntimeFetchPatch()` (`src/services/runtime.ts`) redirects all `/api/*` renderer fetches to the sidecar with 5-min bearer tokens, falling back to cloud API (`ARCHITECTURE.md:231-249`).

**Rate limiting.** Upstash sliding-window (`@upstash/ratelimit`, Lua) with per-endpoint overrides; auto-falls-back to non-Lua fixed-window (INCR+EXPIRE NX) when Lua rejected (self-hosted proxy). Gateway pipeline: origin check → CORS → OPTIONS → API-key → rate limit → route match → handler → ETag/304 (`server/gateway.ts`).

**Proto/RPC.** sebuf framework over Protocol Buffers (`proto/`, `buf generate` → `src/generated/client|server`, `docs/api/*.openapi.yaml`). CI enforces generated-code freshness (`proto-check.yml`).

## 4. AI / LLM USAGE

**Server LLM layer** (`server/_shared/llm.ts`, ~690 lines). Provider chain with health-gate + fallback: **ollama → openrouter → groq → generic** (OpenAI-compatible). Default models: OpenRouter `deepseek/deepseek-v4-flash`, Groq `llama-3.3-70b-versatile`, Ollama `llama3.1:8b`. Two profiles: `callLlmTool` (cheap/fast extraction, default groq) and `callLlmReasoning` (synthesis, default openrouter, reasoning-on). Streaming variant `callLlmReasoningStream` (SSE). Features: bounded error-body reads, thinking-tag stripping, markdown-fence stripping, finish-reason/length-limit retry, prompt-injection sanitization (`llm-sanitize.js`), usage telemetry (`server/_shared/usage.ts`, optional Axiom). Self-hostable with **zero API keys via Ollama**.

**Where LLMs are used** (server handlers): article summarization (`news/v1/summarize-article.ts`), humanitarian/displacement/giving/airport/sector summaries, `analyze-situation` (correlation-engine assessment), forecast generation, `chat-analyst` (WM Analyst chat over 30+ services with citations — Pro), `ask`/`brief`/`latest-brief` (daily world/regional briefs; `shared/brief-llm-core.js`, `shared/brief-filter.js`), market-implications/daily-market-brief. Direct-LLM quota-gated (`server/_shared/direct-llm-quota.ts`).

**Browser-side ML** (`src/config/ml-config.ts`, `@xenova/transformers` ONNX, HuggingFace CDN): all-MiniLM-L6-v2 embeddings (required), DistilBERT-SST2 sentiment, Flan-T5-base/small summarization, BERT-NER entity extraction. Used for **hybrid news clustering** and in-worker semantic vector search.

**Signals / anomaly / instability algorithms (concrete):**

- **CII — Country Instability Index** (server-authoritative; browser legacy engine `src/services/country-instability.ts`, ~1132 lines). Per-country score 0-100 = `baselineRisk*0.4 + eventScore*0.6 + boosts`, where `eventScore = unrest*0.25 + conflict*0.30 + security*0.20 + information*0.25`. Component sub-scores are hand-tuned capped formulas: unrest (protests log-scaled by event-multiplier + fatality/severity/outage boosts), conflict (ACLED battle*3/explosion*4/civilian*5 log-scaled at pivot 4000, sqrt-fatalities, HAPI fallback, **news-conflict floor** requiring ≥2 tier-≤2 sources + ≥2 domains, strike/OREF boosts), security (military flights/vessels + aviation-closure + GPS-jamming), information (news count + velocity sourcesPerHour + alert boost). Additional boosts: hotspot proximity (haversine <150km to `INTEL_HOTSPOTS`/conflict-zones/waterways), displacement (log10), climate, advisories (US/AU/UK/NZ travel), supplemental (AIS-dark-ship/satellite-fire/cyber/temporal), earthquake, sanctions. Floors from UCDP intensity (war=70/minor=50) and advisory level. Levels: ≥81 critical … ≤30 low; trend via ±1 deadband. 31 Tier-1 countries. Weights in `shared/cii-weights.ts`, server config `server/worldmonitor/intelligence/v1/_risk-config.ts`.

- **Correlation Engine** (`src/services/correlation-engine/engine.ts`, browser). 4 domain adapters (military, economic, disaster, escalation). Pipeline per adapter: `collectSignals → cluster → score → filter(threshold) → applyTrends → toCard → queueLLM`. Clustering modes: **by-country**, **by-entity** (compound/single keyword tokens — "supply chain","rare earth","oil","sanctions"…), **by-proximity** (grid-index + **union-find**, haversine radius). Scoring: weighted sum of per-type max severity + diversity bonus (`min(30,(uniqueTypes-2)*12)`), circular-mean centroid. Trend by score delta ±5 vs previous cluster (escalating/de-escalating). Clusters scoring ≥60 queue an **LLM assessment** (Pro-gated, `deductSituation` RPC, 30-min cache, max 3 concurrent).

- **Cross-Source Signals / Composite Escalation** (`scripts/seed-cross-source-signals.mjs`, ~895 lines; 15-min cron; key `intelligence:cross-source-signals:v1`). Reads ~23 Redis source keys (thermal, GPSjam, military flights, unrest, cyber, shipping, sanctions, earthquakes, radiation, outages, wildfire, displacement, forecast, GDELT tone, weather, CII, regulatory). ~25 `extract*` detectors emit typed signals with severityScore; `scoreTier` thresholds ≥3.5→CRITICAL, ≥2.5→HIGH, ≥1.5→MEDIUM. **`detectCompositeEscalation`** groups co-firing signals by normalized theater (`REGION_THEATER_MAP`) and synthesizes composite-escalation signals: `compositeScore = BASE_WEIGHT * min(3, 1+categoryCount/3) + totalScore*0.2`. Composites merged to front, capped `MAX_SIGNALS`.

- **Temporal-baseline anomaly detection** (`src/services/temporal-baseline.ts`): per-region **z-score** of current vs expected count for military_flights/vessels/protests/news/ais_gaps/satellite_fires; severity z≥3 critical, ≥2 high. Message: "Nx normal for {weekday}({month})".

- **News clustering** (`src/services/analysis-core.ts`): Jaccard title similarity with inverted-index candidate generation, tier-weighted threat aggregation (confidence weighted by `6-min(tier,5)`), primary = highest-tier source. Hybrid refinement merges Jaccard clusters by MiniLM semantic similarity when ML available (`src/services/clustering.ts`). Correlation signal types: prediction_leads_news, news_leads_markets, silent_divergence, velocity_spike, keyword_spike, convergence (≥3 source-types in 30m), **triangulation** (wire+gov+intel aligned), flow_drop, explained_market_move, etc.

## 5. MONETIZATION / API

**Tiers** (`docs/pricing.mdx`, source of truth `convex/config/productCatalog.ts` → public `GET /api/product-catalog`):
- **Free** ($0, no signup) — dashboard, 56 layers, 500+ feeds, briefs, CII, chokepoints, alerts, watchlists; 5-15 min refresh.
- **Pro** ($39.99/mo, $399.99/yr) — WM Analyst chat (30+ services w/ citations), Scenario Engine, Route Explorer, AI digests (daily/2×/weekly via Slack/Discord/Telegram/email/webhook), custom widgets, **MCP access (40 tools, one key)**.
- **API / API Starter** ($99.99/mo, $999/yr) — REST API, SDKs (npm/PyPI/RubyGems/Go), self-serve `wm_` license keys, 1,000 req/day, webhooks (5 rules), exports.
- **API Business** ($249.99/mo) — 300 req/min, 10,000 req/day, priority support.
- **Enterprise** (custom) — workspaces, SSO/MFA/RBAC, white-label, embeddable panels, SIEM connectors, on-prem/air-gapped.

**Billing/entitlements.** Checkout on **Dodo Payments** (`convex/lib/dodo.ts`, `api/create-checkout.ts`, `api/customer-portal.ts`); **Clerk** auth; entitlements in **Convex** with real-time WebSocket subscription (`src/services/entitlements.ts`) exposing `tier`, `apiAccess`, `apiRateLimit`, `mcpAccess`, `planLimits`. Gating enforced by `premiumFetch` + `PREMIUM_RPC_PATHS` (`src/shared/premium-paths.ts`, 59 lines).

**Published API/MCP.**
- **REST** — base `api.worldmonitor.app`, OpenAPI spec (`worldmonitor.app/openapi.yaml`, generated from protos).
- **MCP server** — `worldmonitor.app/mcp` Streamable HTTP; public `tools/list`, `tools/call` needs `X-WorldMonitor-Key` or OAuth (`api/mcp.ts`, `api/mcp/`). Registry (`api/mcp/registry/`): **CACHE_TOOLS** (28: `get_market_data`, `get_conflict_events`, `get_news_intelligence`, `get_country_macro`, `get_sanctions_data`, `get_research_signals`, `get_social_velocity`, …) + **RPC_TOOLS** (`get_country_risk`, `get_world_brief`, `analyze_situation`, `generate_forecasts`, `get_procurement_opportunities`, `describe_tool`, …). Universal `summary` + `jmespath` query injection per tool. OAuth dynamic client registration (`api/oauth/`, `api/oauth-authorization-server.ts`). A2A + agent-metadata endpoints (`api/a2a.ts`, `api/agent-auth.ts`, `api/widget-agent.ts`).
- **Agent discovery** — `llms.txt`, `.well-known/agent-skills/index.json` (SKILL.md dirs like `fetch-news-digest`, `track-unrest-events`, `scan-cyber-threats`, `check-chokepoint-status` in `public/.well-known/agent-skills/`), `.well-known/api-catalog`, `.well-known/mcp/server-card.json`, agent-card.json.
- **SDKs** — zero-dep clients in `sdk/{python,ruby,go}`; **CLI** in `cli/` (MCP-first, `npx worldmonitor tools`). Published via OIDC trusted-publishing. Listed on Smithery + skills.sh.
- **Embed** — `embed.html` + `src/embed/` iframe widget (Enterprise white-label).

## 6. ENGINEERING PRACTICES WORTH STEALING

Guard scripts (`scripts/`), wired into pre-push + CI (`package.json` `lint:*`):
- **`lint-boundaries.mjs`** — architectural forward-only dependency lint: `types→config→services→components→app→App.ts`; `api/*.js` must be self-contained (no `src/`/`server/` imports); `server/` must not import `src/components|app`. `boundary-ignore` escape comments. Agent-readable `file:line + remedy` output.
- **`enforce-premium-fetch.mjs`** — TS-AST walk: any `new ServiceClient()` that calls a method whose generated path ∈ `PREMIUM_RPC_PATHS` must be constructed with `{fetch: premiumFetch}`, else Pro users silently get swallowed 401s. Per-call-site analysis (allows a public+premium client split on one class).
- **`enforce-rate-limit-policies.mjs`** — every `ENDPOINT_RATE_POLICIES` key must be a real gateway route (validated against generated OpenAPI + `api-route-exceptions.json`), catching rename-drift that silently disables a limit. Also validates fail-closed/fail-open decision registries.
- **`enforce-safe-html.mjs`** — hash-baseline scan for `.innerHTML/outerHTML/insertAdjacentHTML` assignments in `src/`; baseline must stay empty (`--update-baseline` removed); allowlist only `dom-utils.ts`. XSS guard.
- **`check-unicode-safety.mjs`** — detects Trojan-Source bidi controls, zero-width/invisible chars, variation-selector steganography, PUA payloads across src/server/api/scripts/tests. `--staged` mode.
- **`enforce-sebuf-api-contract.mjs`** (`lint:api-contract`) — every `api/` file must be a sebuf gateway paired with a generated service_server, or a justified entry in `api-route-exceptions.json`; also reverse-checks orphan gateways.
- **`check-seed-freshness.mjs`** — production seed-meta staleness gate (backs 15-min CI cron).
- Others: `check-sentry-coverage.mjs`, `check-vite-env-secrets.mjs` (no secrets in client bundle), `check-local-secret-dumps.mjs`, `check-public-doc-plan-references.mjs`, `enforce-mintlify-reserved-slugs.mjs`, `mcp-budget-check.mjs` (tool-description byte budget), `docs-stats.mjs` (`docs:check` — capability counts CI-verified against code).
- **`AGENTS.md`** — agent operating manual: repo map, run commands, dependency-direction rules, API/server layer constraints, proto flow, "adding an endpoint/panel" recipes, circuit-breaker + caching patterns, pre-push list, "Shipping Velocity" agent workflow.
- **`compound-engineering.local.md`** — declares 5 review sub-agents (kieran-typescript-reviewer, security-sentinel, performance-oracle, architecture-strategist, code-simplicity-reviewer) + WorldMonitor-specific review context/patterns.
- **`.impeccable.md`** — UX-copy design principles for error/recovery flows.
- **`CONCEPTS.md`** — accreted domain glossary (Bootstrap Tier, Lever Test, Shift Mover/Victim, MCP discovery-vs-transport, Alert Rule/Country Scope/Event Attribution fail-closed semantics).

## 7. LICENSE

**`AGPL-3.0-only`** — declared in the package manifest line 5 (`"license": "AGPL-3.0-only"`), full GPL/AGPL text in `LICENSE` (34KB), header `Copyright (C) 2024-2026 Elie Habib`. README (`README.md:165-179`) permits personal/research/self-hosted/fork/commercial-SaaS use **only under AGPL copyleft + source-availability obligations**; "Private-source proprietary use or official branding rights" require **separate commercial or trademark permission**. README explicitly states: *"Commercial licensing is available as an alternative option for teams that need non-AGPL terms"* — i.e. **dual-licensing offered**. Plain-language summary in `docs/license.mdx`. SELF_HOSTING permits full local stack (Docker/Podman) under AGPL. Security policy `SECURITY.md`; CoC `CODE_OF_CONDUCT.md`.

---

**Most transferable to your two products (facts, not recommendations):**
- *Local-events trust pipeline*: `shared/source-tiers.json` (numeric 1-N trust tiers per outlet) + `SOURCE_TYPES` wire/gov/intel/mainstream classification (`src/config/feeds.ts`); Jaccard+semantic clustering with tier-weighted threat aggregation and **triangulation/convergence** multi-source-agreement signals (`src/services/analysis-core.ts`); news-conflict floor requiring ≥2 tier-≤2 sources across ≥2 domains (`country-instability.ts`); SSRF-guarded RSS proxy (`api/rss-proxy.js`, `shared/rss-allowed-domains.json`); OREF/earthquake/weather real-time local geocoded alerting; temporal z-score anomaly (`temporal-baseline.ts`).
- *Investment-research / press-release intelligence*: `seed-regulatory-actions.mjs` (SEC/CFTC/Fed/FDIC/FINRA RSS with severity keyword classification); Finnhub insider-transaction Form-4 conviction scoring (`get-insider-transactions.ts`) + earnings calendar; `analysis-core.ts` `explained_market_move`/`silent_divergence`/`prediction_leads_news` correlation between news velocity and market moves; global-tenders + USAspending + defense-patents seeders; entity extraction/index tying tickers to news (`entity-extraction.ts`, `entity-index.ts`); daily-market-brief LLM pipeline.
