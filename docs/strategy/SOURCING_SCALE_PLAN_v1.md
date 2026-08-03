# 1LIVE Sourcing Scale Plan v1 — the full-scale, top-0.1% engine

**Status:** PROPOSAL for founder ratification (built from six researched inputs,
2026-08-03; every claim cited in the companion reports referenced below).
Validation: this plan + the code already landed go through the mandatory
non-Claude adversarial evaluator on PR #150 — the "world-class" grade is
rendered by an independent model against evidence, never self-asserted.

**One sentence:** find every event-producing entity per segment per market with
an automated discovery engine, read each through one protocol-keyed adapter,
verify through an odds-based truth-discovery gate, publish at earned confidence
behind founder-controlled flags, and prove it all with committed per-window
coverage snapshots — so local supply dominates licensed feeds 50:1+ and every
new metro is a week of data work, not an engineering project.

---

## 0. Where this stands on the day it was written

Audited 2026-08-03 (run ids and file:line evidence in session records):
- Feed is ~94% Ticketmaster (~1,317 of ~1,403 rows); local:TM ratio INVERTED
  (~1:15 vs the founder's ≥50:1 bar).
- 180 hand-curated sources ≈ **4% of the addressable Austin universe**
  (quantified below); 5 of 22 segments render empty.
- Already true and strong: fail-closed budget custody, 4-state confidence,
  disputed-shown-never-hidden, gate-custodied promotion — the benchmark
  research confirms **no competitor occupies this trust position**. The gap
  is industrial, not philosophical.
- Landed on PR #150 the same day: the three-layer sourcing model
  (`SOURCING_MODEL_v1.md`), the auto-promote engine (`worker/autopromote.py`,
  flag OFF), the JS-render fallback (capped, fail-safe), the per-segment
  universe decision with the windowed dominance KPI.

## 1. The bar, defined by evidence (who we must beat)

From the benchmark study (PredictHQ, Bandsintown/Songkick, Google Events,
TM/SeatGeek/Eventbrite, DICE/Fever, Yelp/Foursquare place-matching):
- **PredictHQ** — the reference predator: verify-then-publish at global scale,
  deletes up to 45% of aggregated events as spam/inaccurate, 55M-entity spine,
  per-minute freshness. We must match its verification industrialization.
- **Bandsintown** — 700k artists maintain their own data because listings
  propagate everywhere; 65k venues, 2.3M events/yr (≈35 events/venue/yr — the
  yield constant our projections use).
- **Google** — structured-data-first extraction, change-frequency-adaptive
  recrawl, canonical-election dedupe.
- **Yelp/Foursquare** — precision-first entity resolution (auto-merge only at
  ~99% precision), merge-don't-drop.
- **The moat nobody holds:** a user-facing epistemic state machine. Our
  4-state confidence display is unoccupied territory. Everything below feeds
  it; nothing below relaxes it.

## 2. The engine, five subsystems (FIND → READ → VERIFY → PUBLISH → PROVE)

### 2.1 FIND — the per-segment discovery engine (new build)
The quantified Austin/Central-TX universe: **~4,000–5,000 event-producing
entities** (350 music venues, 500-800 bars, ~4,500 restaurants at 15-25%
event-capable, 200-250 breweries/wineries, 1,219 arts nonprofits, ~40 museums
+ ~100 galleries, 80-100 library branches, 2,247 religious orgs at 20-30%,
17-20 colleges = 150-300 calendar surfaces, 40+ farmers markets, festivals,
clubs...). Rule of thumb: **≈140–170 event-producing sources per 100k
population** (music-city premium included; generic metro ~120-140).

Pipeline (stages D0–D6, full design in the discovery report):
**Overture Places (CDLA-P 2.0) + Foursquare OS Places (Apache 2.0) spine**
(~90-120k places for our 14 counties → ~10k event-capable POIs) → website
resolution → **calendar-surface probe** (sitemap/path patterns, JSON-LD
detection, ICS autodiscovery, platform fingerprints, robots.txt honored) →
pathway classification into the EXISTING adapter kinds → scored
**auto-enrollment as market data** with full provenance (humans review only
the gray band, <10% of volume). Standing loops: 90-day re-probe of
no-surface POIs, dead-source dormancy (recorded, never deleted), monthly
spine refresh. Google Places rejected as spine (ToS forbids warehousing);
OSM held to enrichment pending a founder ODbL decision.
**Projection: 180 → ~2,700–4,200 sources on the first full probe pass;
~4,500–6,500 by month 6** including the artist/group graph (lineups mine
artists free with every extracted event; MusicBrainz joins authority IDs;
artists' own tour pages become probed sources — the graph feeds itself).

### 2.2 READ — protocol adapters, written once (mostly built)
Layer 1 of the sourcing model: licensed_api / ics_feed / jsonld_embedded /
calendar_platform / gov_open_data / ai_extract_triangulated / partner /
social / manual_upload. Extraction is a **cost waterfall**: JSON-LD/ICS
deterministic parse first (near-zero cost, highest a-priori confidence),
platform APIs second, learned per-source templates third (LLM synthesizes
selectors ONCE per source; re-invoked only on template drift — the Vertex
pattern, the single biggest cost-per-verified-event lever), frontier-model
extraction LAST and only for genuinely unstructured pages. The JS-render
fallback (landed, capped) rescues the modern-website half of the moat; its
CI browser step is a small follow-up arming PR.

### 2.3 VERIFY — odds-based truth discovery (upgrade of the existing gate)
Published mechanisms, mapped onto our 4-state model (formulas in the
truth-discovery report):
- **Claims, not overwrites:** per-attribute claims table with source +
  extractor + confidence; fusion computes calibrated probability per fact
  (Knowledge Vault separation of extractor vs source reliability).
- **Source trust EARNED from agreement history** (TruthFinder/KBT loop,
  Beta-Bernoulli updates; syndication edges so copied feeds never
  double-count as corroboration).
- **Gate as fused log-odds** instead of raw source counts: `likely` σ≥0.7;
  `confirmed` σ≥0.95 AND ≥1 authoritative-class claim; `disputed` = two
  value-clusters both above σ 0.5 — making disputed-shown-never-hidden a
  mechanical fusion output. Partial-agreement kernels (8:00 doors vs 8:30
  show corroborate, different days dispute).
- **Entity resolution:** venue spine lookup first (O(n), stable IDs), then
  blocked Fellegi–Sunter (Splink-style match weights, TF-adjusted,
  precision-first thresholds; gray band → the existing review queue).
  Slot-confidence partial records — the "flyer-grade" events every
  competitor drops — held, re-linked, completed, never dropped.
- **Source health sentinels** (Deequ pattern): per-source yield/parse/dup
  metrics with anomaly quarantine so one broken source can't poison trust.
- **Recurrence engine:** RRULE hypothesis scoring per (venue, series) —
  predictive crawling, fusion priors, series-break dispute detection.
Gate-custody note: every change here is mandatory-evaluator territory, and
thresholds move only by founder decision. The upgrade ADDS evidence
machinery; it relaxes nothing.

### 2.4 PUBLISH — earned confidence behind founder flags (built, OFF)
`worker/autopromote.py` (landed): re-evaluates the gate fresh per candidate,
publishes only PASS via the re-asserting promoter, audits every outcome as
`system`, per-candidate failure isolation, orchestrator structurally unable
to promote. `AUTO_PUBLISH_RATIFIED` and `AUTO_PUBLISH_SPARK` both default
OFF — the founder flips each once, never approves per item.

### 2.5 PROVE — committed coverage snapshots (new build, small)
A scheduled, dead-man-watched job commits a dated snapshot: rows by
segment × source × market, each source's last-successful-yield, and the
**dominance ratio per bounded window — today · 2 days · 3 days · week ·
weekend · month** (founder-corrected definition; catalog-total comparisons
are the recorded anti-pattern). Plus the funnel metrics the elite publish:
rejection rate, duplicate rate, dispute count, correction latency,
single-API dependency share, cost-per-verified-event. Targets: provisional
≥50:1 per window pending the empirical calibration (research in flight;
its numbers land in §5 when complete). Day-one task: one TM Discovery
`dmaId` call makes the denominator measured, not estimated.

## 3. Efficiency — the order of operations that keeps this affordable

Key measured fact: GitHub's cron under-delivers ~15× (R-023) and is
accidentally our spend cap (~$21/day actual vs $300+/day if fixed naively).
**Sequence (from the efficiency design, each verified absent today):**
1. Unchanged-content skip + conditional GET (S; hash computed-but-never-
   compared today; plumbing for 304s built-but-uncalled) — kills 60-85% of
   extraction spend.
2. Cost ledger interim (S): per-run calls/tokens/dollars; makes
   cost-per-verified-event computable (charter §14.2 gap closed).
3. Change-frequency ledger → due-time recrawl (M): λ̂ estimator
   (Cho–Garcia-Molina) + time-to-event boost (recheck T-48h/24h/6h — 
   cancellations cluster near showtime).
4. Prompt caching + usage capture (S code, but manifest-bound → bundle into
   ONE attended re-certification sitting; ~63% per-call cut).
5. THEN fix scheduler delivery (external metronome — founder-crucial new
   service) once the pipeline is efficient: designed state ≈ $0.55/run vs
   $4.20, full cadence ≈ $40/day vs $300 — ~7.5× events-per-dollar at 15×
   throughput.
6. Batch API and cheaper-tier re-exams last (the 80% Haiku cut stays a
   scheduled golden-exam experiment; certification never relaxes for cost).

### 3b. TOTAL cost per timeframe (founder-directed 2026-08-03: "not only
'per x' cost... but 'total cost per x' per timeframe")

All figures are estimates until the P2 cost ledger converts them to
measurements; basis stated per row. "Weekend" = Fri-Sun (3 days).

| State | Per DAY | Per WEEKEND | Per MONTH | Basis |
|---|---|---|---|---|
| Austin today (broken cadence) | ~$21 | ~$63 | ~$630 | measured R-023 rate × $4.20/run |
| Austin naive full cadence (DON'T) | $300-750 | $900-2,250 | $9-22k | 72 runs/day un-optimized — the trap §3 sequencing avoids |
| **Austin optimized (P2)** | **$25-40** | **$75-120** | **$0.8-1.2k** | $0.55/run ceiling × 72; change-skip makes most runs near-zero |
| Austin optimized + Batch (−50%) | $13-20 | $40-60 | $0.4-0.6k | batch-eligible because nothing user-facing waits on extraction |
| + Haiku IF it passes re-exam (−80% tier) | $3-8 | $9-24 | $0.1-0.25k | contingent on the 1% golden bar — never assumed |
| 10 metros optimized | $150-300 | $450-900 | $4.5-9k | marginal metro ≈ $15-30/day (below) |
| 10 metros + Batch | $75-150 | $225-450 | $2.3-4.5k | |
| **50 metros (national) + Batch** | **$375-750** | **$1.1-2.3k** | **$11-23k** | + one-time discovery ~$200/metro |
| 50 metros + Batch + Haiku-passed | $90-250 | $270-750 | $2.7-7.5k | the designed end-state IF certification allows |

One-time (non-recurring): discovery probe ~$50-130/metro + review hours;
spine ingest ≈ $0 (public Parquet); re-cert sitting = founder time.
Deterministic imports (TM/structured): ≈$0 marginal (runner minutes only).

### 3c. Geographic-scale compute doctrine (the "absolute most efficient way
to execute per timeframe" — founder-directed)

Marginal cost per added metro is driven to the floor by SHARING everything
shareable and paying only for CHANGE:
1. **One spine job, all markets** — a single DuckDB pass over Overture/FSQ
   Parquet filters every active market's boundary in one read; adding a
   metro adds a WHERE clause, not a job.
2. **Templates learned once, globally** — a platform's calendar template
   (Squarespace, The Events Calendar, Localist...) is learned per PLATFORM,
   not per venue or metro; metro #50's Squarespace venues cost $0 new
   learning. LLM extraction remains the last-resort path everywhere.
3. **Pay only for change** — content-hash skip + conditional GET + λ̂
   due-time scheduling mean steady-state extraction cost scales with
   EVENT CHURN, not source count or metro count. A metro's quiet Tuesday
   costs cents.
4. **Timeframe-shaped crawl waves** (matches the KPI windows): T-0 morning
   local-time sweep for the daily window (the flagship); Thu-Fri surge for
   the weekend window; nightly Batch-API deep sweeps (24h-tolerant, −50%)
   for week/month windows; T-48/24/6h recheck ONLY for events already in
   the near window (cancellations cluster there). Per-timezone waves also
   spread load so 50 metros never spike one hour.
5. **Host-sharded politeness** — frontier grouped by host, so 50 metros of
   Squarespace sites share one polite queue; no per-metro crawler fleets.
6. **Cheapest-capable tier per stage** (charter cost rule 1): deterministic
   parse → template → Haiku-class utility calls (classification, website
   disambiguation) → certified frontier model ONLY for last-resort
   extraction. The certified-model constraint is the one honest ceiling:
   lowering it is a golden-exam event, never a config flip.

## 4. Phases, each with a proof gate (no phase "done" without its number)

| Phase | Content | Proof gate |
|---|---|---|
| **P0 (this PR)** | Sourcing model, autopromote (OFF), render fallback, decisions | Evaluator APPROVE + all checks green on #150 |
| **P1 Publish** (days) | Flip-readiness: autopromote smoke on real candidates; render browser step (arming PR); coverage snapshot job v1 | First committed snapshot shows local events live in ≥17 segments |
| **P2 Efficiency** (1-2 wks) | Skip/conditional-GET, cost ledger, due-time recrawl; bundled re-cert sitting (caching+usage) | Cost-per-verified-event on the snapshot; extraction calls/run down >50% measured |
| **P3 Find** (2-4 wks) | Spine ingest, probe, classification, auto-enroll for Austin; scheduler metronome decision | Catalog ≥2,500 enrolled sources with provenance; structured kinds yielding with zero new adapter code |
| **P4 Verify** (3-6 wks) | Claims fusion, source-trust loop, Fellegi–Sunter resolver, health sentinels, recurrence engine | Dominance ratio per window on the snapshot; dispute mechanics live; delete/duplicate rates published |
| **P5 Replay** (per metro) | Market file + spine filter + probe pass + localized seeds | ~1 week, <$200, ~2,000-3,000 sources per 2M-metro; same gates, zero forked code |

National = P5 × 50 metros ≈ a year of background compute (~$10k) once P1-P4
hold in Austin. Global adds boundary-resolver kinds + locale fields per the
market registry — data, not architecture.

## 5. KPI calibration — empirical results (FOUNDER-RATIFY the retarget)

The calibration research (full report in session records, sources cited)
measured the real Austin universe per window and stress-tested the ratio
itself. Findings:

- **TM per window, Austin (from our own 1,317-row import + Songkick decay
  shape):** today ~8-20 · weekend ~35-75 · week ~70-130 · month ~300-450.
- **Total real events, deduped:** week ~2,500-6,000 (central ~3,500-4,500);
  today ~250-600 weekday / 500-1,000 Fri-Sat; month ~11,000-22,000.
- **The honest ratio range: ~20:1-60:1 near-term.** 50:1 sits at the
  optimistic edge (≈ what near-total coverage produces). **100:1 is NOT
  supported** — reachable only via banned counting (uncollapsed recurrence,
  add-ons, no dedup) — canonizing it would incentivize exactly the inflation
  that ruins event datasets (PredictHQ deletes ~45% of raw aggregate).
- **The ratio fails four metric-design tests:** noisy uncontrolled
  denominator; Goodhart-gameable numerator; doesn't measure user value;
  no ground truth. The search-engine literature (Lawrence & Giles coverage
  studies) gives the right template: measure RECALL AGAINST REALITY.

**Recommended KPI stack (replaces ratio-as-target; ratio becomes a reported
"coverage multiple" context stat):**
- **North star: Verified Coverage@Window** — trust-weighted share of all
  real public events in (market, window) present with correct venue+time,
  measured at window start (T-0). Flagship cut: **Coverage@Daily** (tonight
  is the product). Ground truth: monthly hand-census of one random
  neighborhood-window + continuous capture-recapture across independent
  source families.
- **Guardrails:** unique-supply share (% found nowhere else — the moat
  metric); false-event rate (precision twin, zero-escape bar); discovery
  lead time (% live by T-24h); per-segment coverage floors (no
  cross-segment averaging).
- **Honest-count canon:** occurrence-counted recurrence (weekly trivia = 1
  per day-window, ~4 per month-window, never 52×); add-ons/parking/VIP
  never counted; series-collapsed twin always published; all counts at T-0.
- **Staged targets:** now ≈2-5% Coverage@Daily → M1 (catalog flowing)
  25-40% → M2 (~1,000 sources) 50-70% → M3 (~5,000 sources) **≥80%
  trust-weighted, ≥40% unique supply, ≥90% live by T-24h, no segment <50%.**
  The TM multiple that falls out at M3 is ~30-60:1 — the founder's 50:1
  instinct is what near-total coverage LOOKS like; it becomes the
  consequence, not the target.

## 6. Founder-crucial asks (consolidated; nothing proceeds on these without you)

1. **Flip decision path for `AUTO_PUBLISH_RATIFIED`** — after #150 merges at
   APPROVE, a smoke run on real candidates, then your one-flag flip.
2. **New services for FIND:** spine ingestion (DuckDB over public S3 Parquet
   — free), ONE search API for website resolution (~$30-80/metro), crawler
   identity policy (we identify honestly as the 1LIVE bot). Approve as a
   package?
3. **Scheduler metronome** (fix R-023's 15× under-delivery): an external
   cron trigger — new service + credential. Approve AFTER P2 per §3.
4. **One attended re-certification sitting** (prompt caching + token
   capture, ~63% cost cut) — scheduled at your convenience.
5. **ODbL posture:** may OSM-derived rows enter the catalog if the catalog
   thereby becomes share-alike-open? (Recommendation: defer; Overture+FSQ
   suffice.)
6. **Ratify this plan** (or amend) — it becomes canon at merge either way;
   the RATIFIED marker waits for your word.

## Companion evidence (session 2026-08-03)
Benchmark matrix & top-0.1% practices · truth-discovery mechanisms & formulas ·
efficiency design & cost model · discovery-engine design & Austin universe ·
KPI calibration (in flight). Decision records:
`2026-08-03_sourcing-model-three-layer.md`,
`2026-08-03_source-universe-per-segment.md`.
