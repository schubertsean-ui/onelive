# KPI LEDGER — quarterly KPI snapshot + trend (append-only)

Greppable summary: one snapshot per row-set (append-only, one row per tracked
KPI), mirroring `docs/metrics/KAIZEN_LEDGER.md`'s discipline — rows are never
edited after append; a correction lands as a new snapshot, never a rewrite.
Computed and written ONLY by `python tools/kpi_report.py --append TIMESTAMP`
(never hand-typed — see `docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md` for the
process this ledger serves). This is the AGGREGATION layer over ledgers that
already exist — `docs/metrics/KAIZEN_LEDGER.md` (defects/catches),
`docs/metrics/BRAIN_IQ_LEDGER.md` (brain smartness), the extraction
certification record, the trust gate, and `docs/RECORD.md` (deviations) — it
introduces NO new measurement, only reads and trends what those already
compute.

**Goodhart-honesty control:** a KPI this tool cannot yet compute NEVER gets a
guessed number. Its `Current` cell reads the literal text
`not yet instrumented (trigger: ...)`, and its `Trend` is always `-` (no
numeric history exists to trend). The canonical, machine-checked list of
these gaps is `tools/kpi_report.py::NOT_YET_INSTRUMENTED_SLOTS` (mirrors
`brain/iq.py`'s `MEASURED`/`NOT_YET_MEASURED` split) — see
"Measurement coverage" below and the framework doc's own table.

`Trend` = direction of this row's `Current` numeric reading vs the **most
recent prior row for the same Area+Metric** (`↑` up / `→` flat / `↓` down;
`-` for a metric's first-ever row, or any row with no numeric reading). A
trend arrow is DESCRIPTIVE, not evaluative — for some metrics ↑ is good (test
count, Brain IQ composite), for others ↓ is good (hallucination rate, escaped
defects, RECORD.md open rows). Read it next to its `Target` column, never
alone.

Areas tracked (CLAUDE.md "Cost discipline" + the KPI framework doc):
Ingestion/Coverage, Extraction Correctness (the zero-escaped-defects
reputation metric), Cost-efficiency (§14.2 cost-per-verified-event), Brain
quality (Brain IQ), UX/consumer, Trust/safety.

## Snapshots (append-only; computed by tools/kpi_report.py, never hand-typed)

| timestamp | area | metric | kind | target | current | trend | owner |
|---|---|---|---|---|---|---|---|
| 2026-07-25T12:00:00Z | Ingestion/Coverage | Source catalog size (enabled sources) | lagging | >=120 sources (R-007) | not yet instrumented (trigger: a session with ONELIVE_DB_DSN present runs `select count(*) from source where enabled` and folds it in) | - | ingestion loop (Sentinel) |
| 2026-07-25T12:00:00Z | Ingestion/Coverage | Scheduled cron slot-fire density | leading | >=80% of eligible 20-min slots fire (R-023) | not yet instrumented (trigger: a session with HEALTHCHECKS_API_KEY_RO + `gh` computes the trailing 24h slot-fire rate and folds it in) | - | ingestion loop (Sentinel) |
| 2026-07-25T12:00:00Z | Extraction Correctness | Field-level hallucination rate @ last certification | lagging | <= 1% (one-way ratchet, KAIZEN.md SS M7) | 0.63% (at certification 2026-07-18T20:08:51Z, run 29659010747, model claude-opus-4-8) | - | extraction loop / evaluator gate |
| 2026-07-25T12:00:00Z | Extraction Correctness | Recall @ last certification (anti-gaming pair) | leading | >= 80% | 97.82% (at certification 2026-07-18T20:08:51Z) | - | extraction loop / evaluator gate |
| 2026-07-25T12:00:00Z | Extraction Correctness | All-time escaped defects (M3) | lagging | 0, absolute (Deming zero-escaped-defects goal) | 0 (all-time, docs/metrics/KAIZEN_LEDGER.md) | - | Kaizen / evaluator gate |
| 2026-07-25T12:00:00Z | Extraction Correctness | Production trailing hallucination rate | lagging | tracked weekly; ratchets the certified bar down when it holds at <= half the current bar for 4 cycles | not yet instrumented (trigger: first batch of admin-review verdicts and/or user "Something off?" reports flows and a script tallies confirmed errors / total field assertions) | - | extraction loop / Kaizen M7 ratchet |
| 2026-07-25T12:00:00Z | Cost-efficiency | Cost per verified published event (SS14.2) | lagging | no baseline yet — SS14.2: 'it becomes your own baseline' | not yet instrumented (trigger: first real scheduled ingestion run with per-event cost logging wired (SS14.2) and at least one promoted event to divide by) | - | FinOps / model router |
| 2026-07-25T12:00:00Z | Cost-efficiency | Loop-stage model routing wired (no hardcoded ids) | leading | every declared stage resolves via tools/model_router.py | critical=claude-opus-4-8; evaluator=gpt-5.5; extraction=claude-opus-4-8; mechanical=claude-haiku-4-5; standard=claude-sonnet-4-6 | - | model_router / Generator |
| 2026-07-25T12:00:00Z | Brain quality | Brain IQ composite (knowledge/efficiency/learning) | lagging | one-way ratchet: knowledge & efficiency never regress (tools/brain_iq.py --check, wired into tools/validate) | composite=0.8975 (knowledge=1.0000 efficiency=0.8050 learning=0.7800) trend vs last Brain IQ ledger row: → | - | brain loop |
| 2026-07-25T12:00:00Z | UX/consumer | Web app test suite (vitest) green | leading | 100% green on every web PR | not yet instrumented (trigger: a stdlib-safe reader of the web CI job's test-count artifact/log is wired into this tool) | - | web loop |
| 2026-07-25T12:00:00Z | UX/consumer | Real user engagement / retention | lagging | TBD — defined at public launch (SS15 growth, PROPOSAL) | not yet instrumented (trigger: public launch + analytics wired (Vercel Analytics, TODOS P1) define and start reporting real engagement metrics) | - | web loop / growth |
| 2026-07-25T12:00:00Z | Trust/safety | trust_gate clean (trust invariants hold) | lagging | PASS, always (CLAUDE.md prime directive 1) | PASS | - | gate custody / evaluator |
| 2026-07-25T12:00:00Z | Trust/safety | Kaizen repeat-class alarms active | lagging | 0 active (docs/KAIZEN.md repeat-class rule) | 0 active | - | Kaizen / evaluator gate |
| 2026-07-25T12:00:00Z | Trust/safety | docs/RECORD.md open deviations | leading | every OPEN row carries a live trigger; not a fixed number | 32 OPEN / 13 RESOLVED (45 total rows) | - | gate custody / Generator |
| 2026-07-25T12:00:00Z | Trust/safety | pytest suite size (breadth) | leading | grows or holds steady; never silently shrinks | 1329 tests collected | - | Generator |
| 2026-08-05T02:13:16Z | Ingestion/Coverage | Discovered:licensed event ratio per window (today / weekend / next 7 days) | lagging | >=50:1 per window (founder 2026-08-04: 'The 50:1 is non-API ticketed events to API events on any given day weekend or weekly period.') | not yet instrumented (trigger: each db-report.yml run's artifact carries ratio_50_to_1 per window; a session folds the latest values in) | - | sourcing engine (Sentinel) |
| 2026-08-05T02:13:16Z | Ingestion/Coverage | Source catalog size (enabled sources) | lagging | >=120 sources (R-007) | not yet instrumented (trigger: a session with ONELIVE_DB_DSN present runs `select count(*) from source where enabled` and folds it in) | - | ingestion loop (Sentinel) |
| 2026-08-05T02:13:16Z | Ingestion/Coverage | Scheduled cron slot-fire density | leading | >=80% of eligible 20-min slots fire (R-023) | not yet instrumented (trigger: a session with HEALTHCHECKS_API_KEY_RO + `gh` computes the trailing 24h slot-fire rate and folds it in) | - | ingestion loop (Sentinel) |
| 2026-08-05T02:13:16Z | Extraction Correctness | Field-level hallucination rate @ last certification | lagging | <= 1% (one-way ratchet, KAIZEN.md §M7) | 0.63% (at certification 2026-08-04T17:52:28Z, run 30935638738, model claude-opus-4-8) | ↓ | extraction loop / evaluator gate |
| 2026-08-05T02:13:16Z | Extraction Correctness | Recall @ last certification (anti-gaming pair) | leading | >= 80% | 97.51% (at certification 2026-08-04T17:52:28Z) | ↓ | extraction loop / evaluator gate |
| 2026-08-05T02:13:16Z | Extraction Correctness | All-time escaped defects (M3) | lagging | 0, absolute (Deming zero-escaped-defects goal) | 0 (all-time, docs/metrics/KAIZEN_LEDGER.md) | → | Kaizen / evaluator gate |
| 2026-08-05T02:13:16Z | Extraction Correctness | Production trailing hallucination rate | lagging | tracked weekly; ratchets the certified bar down when it holds at <= half the current bar for 4 cycles | not yet instrumented (trigger: first batch of admin-review verdicts and/or user "Something off?" reports flows and a script tallies confirmed errors / total field assertions) | - | extraction loop / Kaizen M7 ratchet |
| 2026-08-05T02:13:16Z | Cost-efficiency | Cost per verified published event (§14.2) | lagging | no baseline yet — §14.2: 'it becomes your own baseline' | not yet instrumented (trigger: first real scheduled ingestion run with per-event cost logging wired (§14.2) and at least one promoted event to divide by) | - | FinOps / model router |
| 2026-08-05T02:13:16Z | Cost-efficiency | Loop-stage model routing wired (no hardcoded ids) | leading | every declared stage resolves via tools/model_router.py | critical=claude-opus-4-8; evaluator=gpt-5.5; extraction=claude-opus-4-8; mechanical=claude-haiku-4-5; standard=claude-sonnet-4-6 | ↑ | model_router / Generator |
| 2026-08-05T02:13:16Z | Brain quality | Brain IQ composite (knowledge/efficiency/learning) | lagging | one-way ratchet: knowledge & efficiency never regress (tools/brain_iq.py --check, wired into tools/validate) | composite=0.8975 (knowledge=1.0000 efficiency=0.8050 learning=0.7800) trend vs last Brain IQ ledger row: → | → | brain loop |
| 2026-08-05T02:13:16Z | UX/consumer | Web app test suite (vitest) green | leading | 100% green on every web PR | not yet instrumented (trigger: a stdlib-safe reader of the web CI job's test-count artifact/log is wired into this tool) | - | web loop |
| 2026-08-05T02:13:16Z | UX/consumer | Real user engagement / retention | lagging | TBD — defined at public launch (SS15 growth, PROPOSAL) | not yet instrumented (trigger: public launch + analytics wired (Vercel Analytics, TODOS P1) define and start reporting real engagement metrics) | - | web loop / growth |
| 2026-08-05T02:13:16Z | Trust/safety | trust_gate clean (trust invariants hold) | lagging | PASS, always (CLAUDE.md prime directive 1) | PASS | - | gate custody / evaluator |
| 2026-08-05T02:13:16Z | Trust/safety | Kaizen repeat-class alarms active | lagging | 0 active (docs/KAIZEN.md repeat-class rule) | 0 active | → | Kaizen / evaluator gate |
| 2026-08-05T02:13:16Z | Trust/safety | docs/RECORD.md open deviations | leading | every OPEN row carries a live trigger; not a fixed number | 55 OPEN / 21 RESOLVED (76 total rows) | ↑ | gate custody / Generator |
| 2026-08-05T02:13:16Z | Trust/safety | pytest suite size (breadth) | leading | grows or holds steady; never silently shrinks | 2088 tests collected | ↑ | Generator |

## Measurement coverage (Goodhart honesty)

You cannot measure every kind of progress at once, so this ledger names
exactly what it does and does NOT cover — the gap is visible and shrinking,
never hidden. The canonical, machine-checked list is
`tools/kpi_report.py::NOT_YET_INSTRUMENTED_SLOTS`, rendered in full by
`python tools/kpi_report.py --print` (rows tagged `[GAP]`) and asserted
non-empty + honest by `tests/test_kpi_report.py`. In short, as of this
ledger's creation — NOT YET INSTRUMENTED (each with a trigger, full text in
the framework doc and the tool's own registry): source catalog size (needs a
live DB connection), scheduled cron slot-fire density (needs the healthchecks
+ GitHub Actions APIs), production trailing hallucination rate (needs a live
admin-review/user-report sampling script — KAIZEN.md §M7 names the input,
none tallies it yet), cost per verified published event (§14.2 — no live cost
meter exists yet), the web app's own test suite (a different toolchain; this
tool is stdlib-Python-only and does not shell into npm), and real user
engagement/retention (the site is not public yet). Brain IQ's OWN known gaps
(reasoning depth, real production extraction yield, real wall-latency, the
external LongMemEval leaderboard) are tracked separately in
`docs/metrics/BRAIN_MEASUREMENT_COVERAGE.md` — not duplicated here.

## How this ledger is used (see the framework doc for the full process)

At each quarterly review, read this ledger's latest snapshot alongside
`docs/metrics/KAIZEN_LEDGER.md`'s trends and `docs/metrics/BRAIN_IQ_LEDGER.md`
— this ledger does not replace either, it aggregates a scorecard view across
areas for prioritization (RICE/ICE scoring, `docs/strategy/
ONE_LIVE_KPI_FRAMEWORK_v1.md` §Quarterly cadence). A snapshot with more
GAP rows than the last one is itself a finding (an area lost visibility, not
gained it) and belongs in the quarterly review's notes.
