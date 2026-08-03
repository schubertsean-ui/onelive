# Red-Team Package — 1Live Sourcing Scale Plan v1

**For the founder, 2026-08-03.** External reviewer APIs are unreachable from
the build sandbox, so this package is built for MANUAL PASTE per your
instruction. Instructions:

1. Open three fresh sessions: **ChatGPT (GPT-4o or better)**, **Grok**, and
   **Gemini**.
2. Into EACH, paste: the CONTEXT PACKAGE below (Sections A+B+C — same for
   all three), followed by that AI's ROLE PROMPT (Section D/E/F — one each).
3. Bring all three outputs back to the build session verbatim. I will
   aggregate, adjudicate conflicts (3-option protocol), file each finding
   against the plan, and produce the final report + fix list.

---

## SECTION A — GOALS & OBJECTIVES (paste to all three)

PRIMARY GOAL: A sourcing/ingestion engine for 1Live (truth-first live-events
discovery) in the top 0.1% of comparable systems: it must find, verify, and
publish the fullest honest picture of real local events, at the lowest
achievable total cost per timeframe, scaling from one Texas region to
national then global, without ever weakening the trust invariants.

OBJECTIVES (measurable):
1. Coverage: ≥80% trust-weighted Verified Coverage@Daily in the launch
   market at maturity (staged: 2-5% now → 25-40% → 50-70% → ≥80%), with
   per-segment floors ≥50% and ≥40% unique supply (events found nowhere
   else). The local:Ticketmaster multiple (~30-60:1 occurrence-counted)
   falls out as a consequence, never a target.
2. Cost: total cost per timeframe at or below the plan's §3b table (e.g.
   Austin optimized $25-40/day; 50 metros + Batch $11-23k/month), with
   every number converted from estimate to measurement by a cost ledger.
3. Scale: adding a metro = data files + a ~1-week, <$200 discovery replay;
   zero forked pipeline code.
4. Trust (inviolable): AI never publishes UNVALIDATED (the validation gate
   satisfies the invariant); no pay-to-rank; disputed shown-never-hidden;
   every gate fail-closed; gate thresholds never relax for cost or scale.
5. Freshness: ≥90% of daily-window events live by T-24h; T-48/24/6h
   rechecks near event time.

SUCCESS: the staged coverage/cost/freshness numbers hold on committed,
re-runnable snapshots. FAILURE: coverage stalls below targets, cost scales
with source count instead of change, any trust invariant bends, or the KPI
is gamed by junk counting.
CONSTRAINTS: bootstrapped budget; one founder (non-engineer) + AI agents;
certified-extraction model is exam-locked (changing it = attended
re-certification); GitHub Actions is the current scheduler (measured ~15%
delivery); crawler must be polite and honest (robots.txt honored, no login
scraping, no ToS evasion).

## SECTION B — EVIDENCE: current state & key facts (paste to all three)

- Live feed today: ~1,403 events; ~94% from Ticketmaster's licensed API;
  86 from all local sources; 5 of 22 segments empty. Catalog: 180
  hand-curated sources ≈ 4% of the quantified ~4,000-5,000 event-producing
  entities in the 14-county Austin/Central-TX market.
- Pipeline (built, running on schedule): fetch → sensors → certified LLM
  extraction (multi-event fan-out, ≤50 events/page) → candidate store →
  evidence → 3-way trust gate (PASS/HOLD/ESCALATE; 2-source corroboration,
  3 during SXSW; anchor classes promote solo) → promote (human ops today;
  auto-promote engine just built behind a default-OFF flag that re-runs the
  gate fresh and audits every action as machine-actor).
- Confidence model: unverified | likely | confirmed | disputed. Disputed is
  always displayed, never hidden. No badges; quiet uncertainty UI.
- Efficiency facts (verified in code): content hash stored but never
  compared (unchanged pages re-extracted in full); conditional-GET plumbing
  built but uncalled; no token/cost recording; uniform source rotation (no
  change-frequency tracking); prompt caching absent; scheduler delivers
  ~7% of slots (~4.9 runs/day vs 72 designed) making measured spend
  ~$21/day at ~$4.20/run (~$0.021/extraction call, Opus-class $5/$25 MTok,
  ~2,950-token stable prefix).
- Model constraint: extraction model is certification-locked (golden exam,
  ≤1% hallucination bar; Haiku failed 3 cycles, Sonnet 4 — Opus-class is
  the only passer). Changing extraction internals requires a founder-
  attended re-exam.
- Legal/posture: robots.txt honored; no login scraping; catalog carries
  allowed/explicitly_disallowed per source; Overture Places (CDLA-P 2.0) +
  Foursquare OS Places (Apache 2.0) chosen as POI spine; Google Places
  rejected (ToS forbids warehousing); OSM held out pending ODbL decision.
- Calibration: Austin real events/week ~2,500-6,000 deduped vs TM ~70-130;
  honest near-term ratio ~20-60:1; 100:1 unreachable without junk counting.

## SECTION C — THE PLAN UNDER REVIEW (paste to all three, verbatim)

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

---

## SECTION D — ROLE PROMPT for ChatGPT (paste AFTER sections A-C)

ROLE: You are The Adversary in a red-team review. Assume this plan WILL
fail; find the specific reasons why. Standard: zero ambiguity in failure
modes; evidence over intuition (cite the plan's own text/numbers); fixes
implementable today by a tiny team; second-order thinking on every fix.
Review across FOUR dimensions, minimum 3 findings each (12+ total):
1. IMPLEMENTATION — the pipeline/engine designs themselves: where do the
   discovery probe, odds-based gate, entity resolution, adaptive recrawl,
   or auto-promote engine break in practice? Race conditions, poisoning
   paths, dedupe false-merges, fail-open holes.
2. CONCEPT — is any subsystem solving the wrong problem? What would a
   fundamentally better approach look like? What did comparable engines
   (PredictHQ, Google, Bandsintown) learn that this plan ignores?
3. LOGIC — attack the numbers: the ~4,200-source universe estimate, the
   per-timeframe cost table's assumptions (change-rate distribution,
   65% unchanged-visit rate, $0.55/run), the coverage staging, the
   capture-recapture ground-truth method. Name the fallacy where you find
   one.
4. EXECUTION — one non-engineer founder + AI agents, bootstrapped budget,
   GitHub Actions delivering 7% of scheduled slots: what breaks first?
   Missing rollback, monitoring, dry-run, or sequencing errors?
For EACH finding: FINDING / DIMENSION / OBJECTIVE THREATENED (#) /
MECHANISM OF FAILURE / EVIDENCE (quote the plan) / SEVERITY
(CRITICAL-HIGH-MEDIUM-LOW) / RECOMMENDED FIX / IMPLICATIONS OF FIX /
INNOVATION OPPORTUNITY. End with a per-dimension paragraph + overall
verdict: PROCEED / PROCEED WITH FIXES / HALT AND REDESIGN.

## SECTION E — ROLE PROMPT for Grok (paste AFTER sections A-C)

ROLE: You are The Skeptic in a red-team review. Challenge every claim with
"prove it." Same four dimensions and finding format as follows, minimum 3
findings per dimension (12+ total): for each finding give FINDING /
DIMENSION (IMPLEMENTATION-CONCEPT-LOGIC-EXECUTION) / OBJECTIVE THREATENED
/ THE UNSUPPORTED CLAIM (quoted) / WHY IT'S UNSUPPORTED / SEVERITY /
HOW TO VALIDATE OR REPLACE IT / IMPLICATIONS / INNOVATION OPPORTUNITY.
Attack especially: every number in the cost table (what evidence backs
each?); the assumption that auto-enrolled sources behave like curated
ones; the claim that the trust invariants survive 5,000 low-quality
sources; whether Coverage@Daily is actually measurable (hand-census
practicality, capture-recapture independence assumptions — the source
families overlap, which violates Lincoln-Petersen independence: how badly
does that bias the estimate?); whether "pay only for change" holds when
venue sites use dynamic templates/ads that defeat content-hash skipping.
End with per-dimension paragraphs + overall verdict:
PROCEED / PROCEED WITH FIXES / HALT AND REDESIGN.

## SECTION F — ROLE PROMPT for Gemini (paste AFTER sections A-C)

ROLE: You are The Architect in a red-team review. Evaluate structural
integrity and design quality. Same four dimensions, minimum 3 findings
each (12+ total): for each give FINDING / DIMENSION / OBJECTIVE
THREATENED / STRUCTURAL WEAKNESS / BLAST RADIUS (what else breaks) /
SEVERITY / RECOMMENDED ARCHITECTURAL FIX / MIGRATION COST & SIDE EFFECTS
/ INNOVATION OPPORTUNITY. Attack especially: the three-layer model's
seams (what happens when a "special" needs code the pathway layer doesn't
expose?); single points of failure (one Postgres, one scheduler, one
certification-locked model); whether the claims-fusion redesign can be
introduced incrementally without a big-bang migration of the existing
gate; schema evolution for millions of sources; the boundary-resolver
extension path for non-US geographies; observability (what alerts exist
per subsystem, what's mean-time-to-detection when a source family
silently degrades?). End with per-dimension paragraphs + overall verdict:
PROCEED / PROCEED WITH FIXES / HALT AND REDESIGN.

---

## ADDENDUM (2026-08-03, add to Section C when pasting) — §3d Adoption flywheel

The plan now includes §3d: venue/artist adoption of the 1Live entity agent
(claimed, self-maintained presences) as the terminal cost-bender —
adopted entities become push-based, ≈$0-acquisition, anchor-class evidence
sources (the gate's `claimed_upload` anchor class already exists);
extraction spend scales with the UNADOPTED share (~×(1−a)); adoption
carrot is propagation/citation (Bandsintown/Google precedent), never
payment; discovery-first-claim-second sequencing; no-pay-to-rank and
gate custody unchanged. REVIEWERS: attack this too — adoption-rate realism
for small venues, spoofed/hijacked claims as a poisoning vector, the
incentive's honesty (is "citation" a real carrot pre-scale?), and whether
agent-maintained data quietly becomes an unaudited side door around
corroboration.
