# Research report — Efficiency layer design: cost model, unchanged-skip, conditional GET, caching, adaptive recrawl, scheduler sequencing

Produced 2026-08-03 by a session research agent; committed verbatim as the
companion evidence cited by docs/strategy/SOURCING_SCALE_PLAN_v1.md.

---

I have everything I need. Here is the efficiency design.

---

# 1Live Ingestion — Efficiency Layer Design

## Verdict up front

The **budget fail-closed design is genuinely strong** and should not be touched. `_resolve_source_cap` (`/home/user/onelive/worker/run_once.py:179-215`) rejects unset-but-empty, non-integer, and non-positive ceilings with distinct messages; `apply_source_ceiling` (`:118-140`) refuses `cap<=0` rather than reading it as "uncapped"; `_positive_int` (`:102-115`) duplicates the check at the argparse boundary; and `.github/workflows/ingest.yml:100,195` validates the same expression twice with an explicit comment that both steps must agree. `order_for_rotation` (`:143-170`) is a correct least-recently-*attempted* sweep, and the reason attempt rows exist at all (`/home/user/onelive/worker/fetch/http_fetch.py:28-39`) — so a permanently-failing source cannot monopolize the window — is a subtle bug most teams ship in production. This is top-decile budget hygiene.

**What is missing is the entire efficiency layer.** The pipeline is correct and audited but does the maximum possible work every run: it re-extracts unchanged pages with a frontier model, never sends a conditional GET despite storing the ETag, visits a monthly-changing museum page as often as a nightly venue calendar, and records zero cost data. Every one of the "candidates to evaluate" you named is genuinely absent, and I verified each in code.

---

## The cost model (assumptions stated)

Grounding numbers, so the gains below are auditable:

- Extraction routes to `claude-opus-4-8` (`/home/user/onelive/tools/routing_data.py`, `STAGE_MODELS["extraction"]`), **$5/MTok in, $25/MTok out**.
- Stable per-call prefix = tool schema + system prompt. `EXTRACTION_SYSTEM_PROMPT` is 10,355 chars ≈ **2,590 tokens**; the `AIEventExtraction` JSON schema + tool wrapper (`/home/user/onelive/ai/claude_provider.py:237-243`) ≈ 350 tokens. **≈2,950 token stable prefix.**
- Variable per-call input = one segmented block, assumed ~250 tokens (wide variance: `worker/segment.py:44` allows up to 200 blocks, and the single-block fallback sends the *entire page*).
- Output ≈ 200 tokens (`max_tokens=1024`, `ai/claude_provider.py:183`).

**Per extraction call today: ≈$0.021.** One call per block (`worker/ai_extract.py:254`), capped at `EXTRACT_MAX_EVENTS_PER_PAGE=50` (`:47`), × `--max-sources 10` → **≤500 calls/run, ≈$10.50/run worst case**; ≈$4.20/run at 20 blocks/page.

The uncomfortable corollary: at the *designed* 72 slots/day, that is **$300–$756/day**. At the *measured* R-023 rate of ~4.9 runs/day (`docs/RECORD.md:42`), it is ~$21/day. **The broken scheduler is currently the de facto spend cap.** Fixing R-023 without shipping the efficiency layer first multiplies spend ~15× overnight. That sequencing point belongs in the founder plan.

---

## The 5–8 highest-leverage mechanisms

### 1. Unchanged-content skip (hash short-circuit before AI) — **highest leverage, S**

**Today:** the content hash is computed and stored but *never compared*. `http_fetch.py:145` computes `ch = sha256(content)`; `:146-149` uses it only to skip re-*writing* the raw bytes file (`if not os.path.exists(path)`); `:151-170` inserts a new `raw_fetch` row unconditionally and returns `status: "ok"`. The orchestrator therefore proceeds straight to `_read_fetched_text` (`worker/orchestrator.py:153`), the sensor, and the full fan-out `extract_candidate` (`:168`). **A byte-identical page costs a full N-call extraction, every visit.** The only skip path is HTTP 304 (`orchestrator.py:147-151`), which never fires — see #2.

**Build:** in `fetch_url`, after computing `ch`, `SELECT content_hash FROM raw_fetch WHERE source_id=%s AND content_hash NOT LIKE 'attempt:%' ORDER BY fetched_at DESC LIMIT 1` (rides `idx_raw_fetch_source_time`, migration 0003). On match, still insert the attempt/fetch row (rotation depends on it — `http_fetch.py:28-39`) but return a new `status: "unchanged"`. Add an `"unchanged"` bucket to `_COUNT_KEYS` (`orchestrator.py:58-67`) and an early return mirroring `:147-151`. Do **not** silently collapse it into `not_modified`; the two are different facts (server said nothing changed vs. we downloaded and it was identical).

**Expected gain:** eliminates 100% of extraction spend on unchanged visits. Honest basis: the redundancy rate is **unmeasured** — no change-frequency data exists in the repo (see #4). Arithmetic bound: at the designed ~3 visits/source/day, a daily-changing calendar wastes ≥2/3 of visits; a weekly-changing one wastes ~95%. A realistic blended 60–85% reduction in extraction calls is defensible only *after* #4 measures it. This is the mechanism that makes every other cost lever secondary.

**Cost: S.** ~30 lines in `http_fetch.py` + `orchestrator.py`. Neither is extraction surface (`tools/classify_extraction_surface.py:44-57,82-88` — `on_surface` matches `ai/*` plus an explicit list; neither file is in it), so **no certification impact**. Both *are* in the arming runtime set (`tools/arming_runtime.py` output), so the PR must refresh `docs/evidence/ARMING_SMOKE_RUN.json` with a fresh head smoke run.

---

### 2. Conditional GET — the plumbing exists and is disconnected — **S**

**Today:** `fetch_url` fully implements conditional GET — `etag`/`last_modified` parameters (`http_fetch.py:105-106`), `If-None-Match`/`If-Modified-Since` headers (`:111-114`), correct 304 handling that skips `raise_for_status` (`:118-119`) and records a strict attempt row (`:135-142`). The response ETag and Last-Modified are already persisted into `raw_fetch.headers` jsonb (`:161-166`) and returned (`:178-179`).

**And the only production caller passes neither.** `orchestrator.py:139`: `fetch_url(source_id=source_id, url=url)`. Grep confirms no other caller (`worker/importers/structured_feed.py:682` is a different, unrelated `fetch_url`). The 304 branch, the attempt-row starvation fix built for it, and `_COUNT_KEYS["not_modified"]` are all **dead code in production**. This is the single cleanest unclaimed win in the repo: the hard part is written, tested (`tests/test_fetch_attempt_rows.py:132`), and never wired.

**Build:** same query as #1 (one `SELECT ... ORDER BY fetched_at DESC LIMIT 1`, returning `headers->>'etag'` and `headers->>'last_modified'`), passed into the existing parameters. Best implemented *inside* `fetch_url` so the orchestrator signature is untouched.

**Expected gain:** on 304-honoring origins, saves the bandwidth *and* the extraction pass, and saves it earlier than #1 (no download, no segmentation, no sensor). Honest basis: ETag/Last-Modified support across a ~180-source catalog (`sources/master_sources_catalog_120.json` holds 180 entries) is typically 40–70% for static-ish CMS calendars and near-zero for JS-rendered ones. Treat #2 as the cheap first line and #1 as the backstop that catches everything #2 misses — **ship them in the same PR**; #1 alone is sufficient, #2 alone is not.

**Cost: S.** Arming-evidence refresh only.

---

### 3. Anthropic prompt caching — **verified absent; ~63% per-call cut; S code, L governance**

**Today: not wired anywhere.** `grep cache_control` across `*.py` returns zero hits in runtime code — only `docs/MODEL_ROUTING.md:86` (policy, unimplemented) and `docs/memory/entities/2026-07-27_anthropic-messages-api-call-pattern.md` (a founder directive recording the *correct* call shape, explicitly scoped as "call SHAPE only"). The live call at `ai/claude_provider.py:248-255` passes `system=` as a bare string with no cache breakpoint.

**This is a textbook-perfect caching workload and it is being left entirely on the table.** Render order is tools → system → messages; the tool definition and system prompt are byte-identical across every call in a run, and the only varying content (the block text) is last. The ~2,950-token prefix clears Opus 4.8's **1,024-token minimum cacheable prefix** by ~2.9×. Fan-out means 20–500 consecutive calls share it, comfortably inside the 5-minute TTL.

**Build:** convert `system` to a list of text blocks with `cache_control: {"type": "ephemeral"}` on the last block; assert `usage.cache_read_input_tokens > 0` on the second and later calls (the verification rule the founder's own memory note already mandates).

**Expected gain, computed not asserted:** cache reads bill ~0.1× input, writes 1.25× (5-min TTL); break-even at two requests. Per call: input drops from (2,950+250)×$5/MTok = $0.0160 to (295+250)×$5/MTok = $0.0027 — **83% off input, 63% off total** once output is included. Note the honest gap: the headline "~90%" applies to the cached *portion* of input only, not to the bill. Per run at 200 calls: **$4.20 → $1.55**.

**Cost: S to write, L to land — and this is the honest catch.** `ai/claude_provider.py` is **manifest-bound**: it is line 66 of `HARNESS_MANIFEST` (`ai/golden_exam.py:64-88`), whose bytes feed the certification hash (`:94-97`). Editing it turns trust_gate red everywhere, and per `tools/classify_extraction_surface.py:246-263` the only green-at-merge path is a PR that simultaneously sets `EXTRACTION_THRESHOLD_RATIFIED` to literal `False` — i.e. **closes extraction** — with re-opening requiring the full standing three-step: attended exam → authenticated certification record → head-bound flag flip.

I checked the route-around and it does not work cleanly. `system_prompt` is passed in as a kwarg from `worker/ai_extract.py:105` (which is surface-classified but *not* manifest-bound), so a caller could in principle pass a block list. But `_stamp` then calls `(used_prompt or EXTRACTION_SYSTEM_PROMPT).encode("utf-8")` (`claude_provider.py:392-393`) on that value; a list has no `.encode`, the `AttributeError` falls through `_is_config_error` (`:298-305`) as "unknown → transient", gets retried three times, and returns `None` — a silent degradation into the manual path. The clean fix genuinely lives in the manifest-bound file.

**Recommendation:** do not spend a re-certification cycle on caching alone. **Batch it** with any other extraction-surface work into a single attended cycle, and note that the same cycle is the natural moment to re-sit the cheaper tiers (see #7).

---

### 4. Change-frequency ledger → adaptive recrawl cadence — **the compounding one; M**

**Today: no change-frequency tracking of any kind exists.** `worker/source_rank.py:106-114` computes a `priority_score` including an `update_frequency_score` term (`:102`, weight 0.15 in `worker/config/source_rank_config.json`) — but that value is a **static, human-curated number** typed into `sources/master_sources_catalog_120.json` at catalog-authoring time, and `compute_priority_score`/`SourceMetrics` have **zero production callers** (only `tests/test_source_rank_config.py:22` imports the module). Likewise `worker/source_reliability.py:13-27` — `adjust_source_reliability` has no caller anywhere; it is referenced only in comments at `worker/publish_policy.py:41` and `brain/acquisition.py:91`. Both scoring modules are, today, elegant dead code.

Rotation is therefore **uniform**: `order_for_rotation` (`run_once.py:143-170`) sorts purely by `max(raw_fetch.fetched_at)`, so a museum whose exhibition page changes monthly claims exactly as many budget slots as a venue posting nightly.

**Build:** #1 and #2 generate the measurement for free — every fetch already yields "changed / unchanged-hash / 304". Add a `source_change_stats` table (or columns on `source`): `last_change_at`, `consecutive_unchanged`, `observed_change_interval_s` (EWMA). Then replace the sort key in `order_for_rotation` with a **due-time** score: `due_at = last_fetched_at + clamp(observed_interval × 0.5, min_interval, max_interval)`, sort by most-overdue, and keep the never-fetched sentinel bucket (`:166-176`) leading. Keep the existing tiebreak so ordering stays deterministic and unit-testable — the docstring's own revisit trigger (">2,000 enabled sources → move ordering into the SELECT", `:158-161`) is the right escalation point.

**Expected gain:** this is what converts a fixed budget into *coverage*. Under uniform rotation, N slots buy N/|catalog| sweeps regardless of value. Under due-time rotation, the same N slots concentrate on sources that actually changed. Honest basis: the gain is a **reallocation**, not a discount — it does not reduce cost per call, it raises verified-events-per-call. The magnitude depends entirely on the change-interval distribution across the ~180-source catalog, which nobody has measured. Expect the distribution to be heavily skewed (a handful of nightly calendars, a long tail of monthly-static pages); if so, 2–4× more fresh events per budget dollar is a reasonable planning figure, to be replaced by measurement after ~2 weeks of ledger data.

**Cost: M.** One migration, ~60 lines, and a rewrite of the sort key with new unit tests. `run_once.py` is arming-runtime but not extraction surface — **no certification impact**. This mechanism is the reason to ship #1 first: it is #1's by-product.

---

### 5. Per-source cost ledger + cost-per-verified-event — **M; unblocks everything above**

**Today: nothing is recorded.** `grep 'input_tokens\|output_tokens\|resp.usage'` across `*.py` returns **zero hits** — `response.usage` is never read at `ai/claude_provider.py:248-256`. §14.2's canonical unit economic is explicitly registered as a gap: `docs/metrics/kpi_registry.json` `"id": "cost-per-verified-event"` carries `"compute": "manual_gap"`, `"why": "no live cost meter exists yet; tokens+fetch+ops-minutes per promoted event is not logged anywhere"`, trigger `"first real scheduled ingestion run with per-event cost logging wired"`. `docs/RECORD.md:82` (R-046) names it as one of six uninstrumented KPIs, and `CLAUDE.md:25` states the charter rule it violates: *"Measure, don't guess."* The `RunReport.counts` (`orchestrator.py:58-67`) tracks stage throughput but no tokens, no dollars.

**Build:** (a) capture `resp.usage` in the provider and return it as a `_usage` meta key — the `_META_PREFIX` split in `ai_extract.py:90-94` already routes underscore keys around pydantic validation and back into the stored `extracted` jsonb, so the plumbing exists; (b) accumulate per-source token totals in `RunReport`; (c) write one `run_cost` row per run (run_id, source_id, calls, input/cached/output tokens, computed USD, events extracted); (d) join against promoted events for the §14.2 divisor and wire `tools/kpi_report.py` off `manual_gap`.

Note (a) touches the manifest-bound provider again — **bundle it with #3 in the same re-certification cycle.** A cheaper interim: derive cost from call *counts* (already knowable from `candidate_ids` length) × a measured average, logged from `ai_extract.py` alone, which is surface-but-unbound and therefore charter-exception-eligible.

**Expected gain:** zero direct dollars; it is the instrument that makes every other number in this document a measurement instead of an estimate, and it closes an OPEN charter obligation. Without it there is no way to prove #1's redundancy rate, #4's reallocation, or #7's tier decision.

**Cost: M**, or S for the interim call-count version.

---

### 6. R-023 scheduler under-delivery — **the throughput bottleneck; M, and founder-crucial**

**Today, measured:** `docs/RECORD.md:42` is the single source of truth — **3 genuine schedule fires across ~44 eligible slots ≈ 7% slot-fire rate**, average one run per ~4.9h. Consequence (a) as recorded: **~49 source-attempts/day vs the §14.3 budget shape's ~720**, so the ~266-source catalog sweeps **once per ~5.4 days instead of ~3×/day** — a **~15× throughput shortfall**. Consequence (b): the dead-man alarm correctly fired 15 DOWN events/day tracking the gaps (verified mechanically, run 29963532221), so the Sentinel is not defective — it is honestly reporting a broken scheduler, and the crying-wolf volume is now measured fact.

The cadence itself is sound: `.github/workflows/ingest.yml:56` `cron: "9,29,49 * * * *"` with minutes deliberately off the `:00` congestion window (`:42-48`), `concurrency: group: ingest, cancel-in-progress: false` (`:68-70`) preventing overlap, and `tests/test_ingest_workflow_contract.py` deriving `EXPECTED_PERIOD_SECONDS: "1200"` (`:144`) from the cron line so cadence and alarm cannot drift. **Nothing in the repo is wrong. GitHub's hosted scheduler is simply not delivering.**

**Build — three options, honestly ranked:**

| Option | What it costs | What it buys |
|---|---|---|
| **A. External metronome** (self-hosted cron / Cloud Scheduler / a Routine) firing `workflow_dispatch` with `max_sources` | New service + credential — **founder-crucial** per CLAUDE.md | Deterministic delivery; keeps all existing gates, since dispatch already fails loud without an explicit ceiling (`ingest.yml:100`) |
| **B. Multiple offset workflows** (e.g. 3 files at `3,23,43` / `9,29,49` / `15,35,55`) | Zero new infra; but breaks the 1:1 cron↔`EXPECTED_PERIOD_SECONDS` binding that `test_ingest_workflow_contract.py` enforces, and `concurrency: group: ingest` serializes them | Raises *expected* fire count without fixing the underlying 7% rate — statistical patch, not a fix |
| **C. Accept measured cadence** and re-tune the dead-man period | Founder-ratified Sentinel change; one decision record | Stops the 15 false DOWN/day; honest about real coverage; **and preserves the accidental spend cap** |

**Recommendation:** ship mechanisms 1, 2, and 4 *first*, then A. Doing A first — restoring 72 slots/day against an un-optimized pipeline — takes spend from ~$21/day to ~$300–750/day for the *same* events, because the extra 67 slots/day would mostly re-extract unchanged pages. The efficiency layer is what makes the throughput fix affordable. That ordering is the core recommendation of this document.

**Cost: M** (option A), plus a founder decision that R-023's trigger already frames.

---

### 7. Batch API + cheaper-tier routing — **evaluate, but do not lead with these**

**Batch API: not wired.** `grep -i 'batches\|message_batches'` finds only `docs/MODEL_ROUTING.md:87` ("50% off everything for jobs that can wait up to 24h"). Extraction is a genuinely batch-shaped workload — the orchestrator **never promotes** (`worker/orchestrator.py:214-231`; publishing is an authenticated ops action only), so nothing user-facing depends on extraction latency, and 24h is well inside the tolerance. Batch stacks multiplicatively with #3: 0.5 × 0.37 ≈ **0.18 of today's per-call cost, ~82% total reduction**.

But the build cost is real: `extract_candidates` (`ai_extract.py:251-264`) is a synchronous loop that stores each candidate inline, and `_run_one_source` (`orchestrator.py:168-200`) immediately loads gate signals and evaluates gate3 on the returned id. Batching means submit → poll → resume, which fragments the per-source replay record (`orchestrator.py:177-182`) and the `RunReport` contract. **Cost: L**, and it should follow #1/#2/#4 — halving the price of calls you should not be making is the wrong order of operations.

**Cheaper-tier routing for extraction: state this plainly to the founder — it is certification-locked, not a config change.** `tools/model_router.py:74-89` fails closed on `EXTRACTION_THRESHOLD_RATIFIED`, and `ai/claude_provider.py:116-137` re-checks the same gate at the provider entry point *before* honoring any explicit model, so `ONELIVE_MODEL_EXTRACTION` cannot quietly reroute it. The escalation history in `tools/routing_data.py` records why Opus is there: `claude-haiku-4-5` failed the golden-set exam **3 consecutive cycles** and `claude-sonnet-4-6` failed **4**, the last two oscillating at 2.3–2.7% against a ratified 1% bar (`ai/exam_thresholds.py:HALLUCINATION_MAX = 0.01`). Changing the extraction model therefore requires the **full attended-exam re-certification loop** — attended run meeting the rate bar *and* both ≥300-fact floors with zero injections, evidence bound to the exact head commit, prompt hash, routed model, golden-set hash, harness-manifest hash, and dependency lock. That is not a cost optimization; it is a governance cycle with a founder in the room.

That said, `routing_data.py` records a **standing, tracked policy** that both cheaper tiers re-sit the exam via `workflow_dispatch` once the gate is open and extraction routes to the cheapest passer. **Recommendation:** treat the tier question as a scheduled experiment, not an efficiency lever — and note that if Haiku ever passes, it is $1/$5 vs $5/$25, an **80% cut that dwarfs caching and batch combined**. It is the largest single lever in the system and the one you are least free to pull.

---

### 8. Two smaller items worth naming

- **Per-page cap is a cost cap, not a coverage cap.** `EXTRACT_MAX_EVENTS_PER_PAGE=50` (`ai_extract.py:47`) defers overflow blocks with a loud warning and no drop (`:229-237`) — correct. But the deferral has **no memory**: the next run re-segments the same page and re-extracts the same first 50 blocks. A large calendar's blocks 51+ are structurally unreachable. Fix rides #1: once unchanged pages are skipped, add a per-source `extraction_offset` so deferred blocks are actually picked up. **S.**
- **`min_interval_s=2.0` is a blocking sleep** (`http_fetch.py:109`) — 20s of pure wall-clock per 10-source run. Politeness is correct and should stay, but it should be per-*host*, not per-call; consecutive fetches to different domains need not serialize. **S**, low value, mentioned for completeness.

---

## What maximally productive looks like

**Today (measured + estimated):** at the R-023 delivery rate of ~4.9 runs/day (`docs/RECORD.md:42`), the loop makes ~49 source-attempts/day at ~$4.20/run ≈ **$21/day**, and re-extracts every visited page in full regardless of whether it changed — so an unknown but likely majority of that spend buys zero new facts. Cost-per-verified-event is **not computable**, because no cost meter exists (`kpi_registry.json`, `"compute": "manual_gap"`) and promotion is manual. **Designed state:** ship #2 and #1 together (conditional GET + hash short-circuit) so unchanged pages cost one HTTP request instead of 20–50 Opus calls; ship #5 so the redundancy rate stops being an estimate; ship #4 so budget slots concentrate on sources that actually change; ship #3's caching and #5's token capture in one bundled re-certification cycle; then and only then fix #6's delivery. **Assuming** 65% of visits find unchanged content, 63% caching savings on the remainder, and adaptive cadence redirecting the freed slots to sources with real churn, per-run extraction cost falls from ~$4.20 to **~$0.55**, and a restored 72-slot day costs **~$40/day instead of ~$300** — roughly **7.5× more events per dollar at 15× the throughput**, i.e. the same catalog swept ~3×/day for about twice today's total spend rather than fifteen times it. Every number in that sentence is an estimate resting on an unmeasured change-frequency distribution; **mechanism #5 is what converts it into a founder-facing fact**, and until it ships, the honest answer to "what is cost-per-verified-event" remains the one the KPI registry already gives: not yet instrumented.

---

## Recommended sequencing

1. **#2 + #1** (conditional GET + unchanged-hash skip) — one PR, S, no certification impact, arming-evidence refresh. Largest gain per unit of risk.
2. **#5 interim** (call-count cost logging from `ai_extract.py`) — S, surface-but-unbound.
3. **#4** (change-frequency ledger + due-time rotation) — M, feeds on #1's output.
4. **#3 + #5 full** (prompt caching + `usage` capture) — one bundled attended re-certification cycle against `ai/claude_provider.py`.
5. **#6** (scheduler fix, option A) — founder decision, deliberately *after* 1–4.
6. **#7** (Batch API; tier re-exam as a scheduled experiment) — L, last.

**Files that carry a certification cost:** `ai/claude_provider.py` (manifest-bound, `ai/golden_exam.py:66`). **Files that carry only an arming-evidence refresh:** `worker/fetch/http_fetch.py`, `worker/orchestrator.py`, `worker/run_once.py`, `worker/ai_extract.py`, `worker/segment.py`, `.github/workflows/ingest.yml` (per `tools/arming_runtime.py`). **Files with no gate cost:** new migrations, new tables, `tools/kpi_report.py`.
