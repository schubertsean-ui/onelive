# ONE LIVE — Analytics & Measurement Canon (v1)

**Status:** PROPOSAL → intended as the measurement source of truth once founder-ratified.
Governs how we measure the platform's **depth, breadth, accuracy, and usage** across every
entity and dimension, trended over time with ITR-Economics rate-of-change, on an architecture
built to **answer any question** we can pose. Wiring any analytics *vendor* (PostHog, a
warehouse) is a **new service = founder-crucial** — this doc specifies the framework; the
founder authorizes the spend/keys.

**The ask (founder, 2026-07-31):** *"A consistent analysis to understand depth, breadth,
accuracy of venues available, venues shown in a search, changes over time [3/12, 6/12, 12/12
per ITR Economics] — same for groups, people, orgs; same by category (22); same by genre;
same by feature including usage. Robust enough to answer any question we can think of."*

**Two goals, one framework:** (1) a **complete metric taxonomy** so no important question is
un-instrumented, and (2) a **queryable architecture** — dimensional model + a single metric
definition layer + periodic snapshots — so every metric is sliceable by any dimension and
trendable over any period.

---

## §0 · Principles (the measurement laws)

1. **Never guess a number.** A metric we can't yet compute reads literally *"not yet
   instrumented (trigger: …)"* — never a fabricated value. This mirrors the existing
   Goodhart-honesty control in `docs/metrics/kpi_registry.json` and the Record discipline
   (every deferral carries a live `[R-###]` trigger).
2. **Metrics never feed ranking.** No popularity signal ever reorders the feed. The
   no-pay-to-rank invariant and "genre/filters are lenses, never ranking dimensions"
   (`web/lib/feed.ts`) govern analytics too. Measurement observes; it never ranks.
3. **Privacy is fail-closed.** No PII in the analytics store; user identity is a stable
   opaque id, never an email/name. Engagement is opt-in and disclosed. `is_private_rsvp` /
   private events never enter analytics. (A dedicated privacy-analytics policy is a gap to
   ratify — see §9.)
4. **Coverage is honest or it is nothing.** Every breadth number states its denominator and
   its estimation method; an unknown denominator is labeled unknown, never implied to be 100%.
5. **Build on what exists.** Extend the KPI registry + Kaizen ledger; do not reinvent them.

---

## §1 · The measurement spine — the funnel over an unknown universe

Nearly every metric is either a **ratio between two adjacent stages** (a conversion) or a
**quality measure within a stage** (accuracy/completeness):

```
Addressable universe (all real live events in-market tonight)   ← the hard denominator
  → Known / ingested (we have a record)
    → Extracted (facts pulled)
      → Gated / promoted (trust decision made)
        → Indexed (searchable)
          → Matched to a query
            → Shown to a searcher
              → Engaged (open / expand / listen)
                → Acted on (saved / attended / shared)
```

The single hardest, highest-value number is the **top-of-funnel denominator** (§3). Without
it we can measure *yield*, never *coverage of the world* — which for a trust-first discovery
platform is the whole game.

---

## §2 · The four lenses (applied to every entity and dimension)

For **every entity** — venues, artists, **groups/orgs**, people, sources, events — and
**every slice** — the **22 categories**, the **18 genres**, geography (CAPCOG county / area),
confidence state, source-type, and **feature** — we compute a consistent set across four
lenses. This uniformity is what makes the analysis "consistent" and lets us answer
symmetrical questions ("depth of venues by category" vs "depth of artists by genre").

### A. BREADTH / coverage — "how much of the world do we have?"
- **Coverage %** = `distinct_entities_ingested / estimated_true_universe` (per market × period).
- **Recall vs a golden reference set** — the *measurable* proxy for coverage (see §3).
- **Source coverage** = `sources_ingested_LIVE / sources_known` (we already track source
  pathway status: LIVE / CODE_READY / ADAPTER_BUILT / NEEDS_BUILD — `tools/source_pathways.py`).
- **Supply gap** — category × geography × time-slot cells where search demand exists but
  supply is thin.

### B. DEPTH / completeness — "how rich is each record?"
- **Field fill-rate** = `populated_fields / expected_fields`, per entity and aggregated per
  field (finds systematically-missing attributes).
- **Weighted completeness** — fill-rate weighted by field importance (a missing `start_time`
  hurts more than a missing sub-genre).
- **Corroboration / source-count** — distinct sources per event and per critical field; the
  overlap that also powers coverage estimation (§3) and confidence derivation.
- **Confidence distribution** — count/% in `unverified / likely / confirmed / disputed`
  (`worker/confidence.py`). Track the *distribution's shape*, not just a mean. "Share of shown
  events that are disputed" is a first-class quality-of-experience metric (disputed is
  shown-never-hidden — reducing it to invisibility would violate the invariant).

### C. ACCURACY / quality — "is what we have correct, and would we know if it broke?"
- **The six data-quality dimensions** (DAMA-DMBOK): completeness, **validity** (% passing
  schema/business rules), **accuracy** (% matching a trusted reference), **consistency** (%
  with no cross-source contradiction), **uniqueness** (`1 − duplicates/total` — entity-
  resolution health, `worker/resolve_entities.py`), **timeliness/freshness** (data age vs
  source change).
- **Extraction precision / recall / F1** against the golden exam (we already certify
  hallucination 0.63% / recall 97.82% via `ai/golden_exam.py`).
- **Escaped-error rate** = `errors_reaching_users / published_facts` — charter-sacred (Kaizen
  "zero escaped defects is absolute"), paired with **internally-caught defect rate** (a rising
  caught-rate with flat escaped-rate is a *healthy* gate).
- **Data observability — the five pillars** (Barr Moses): freshness, **volume** (a silent
  drop in events/night = a broken source), schema, distribution, lineage. This is the formal
  home of our `healthchecks.io` dead-man ping + Sentry sentinels.

### D. USAGE / engagement — "do people find value and return?"
- **The search funnel** (§4).
- **North Star + input levers**, **activation**, **DAU/WAU/MAU + stickiness**, **cohort
  retention**, **feature adoption** (§5) — measured **per side** (searcher *and* supply).

---

## §3 · The denominator — estimating the true universe (the hard part)

Coverage is `have / exists`; the numerator is trivial, the **denominator is a hidden
population**. We estimate it two ways and cross-check (never trust one):

1. **Capture–recapture / Multiple Systems Estimation.** When independent sources list the
   same real events, their *overlap* estimates what neither caught. Two-list Lincoln–Petersen:
   `N̂ = (n_A × n_B) / n_overlap`; three+ lists → log-linear models. **This is why we must log
   the source(s) that independently reported every candidate** — the same corroboration
   overlap that drives trust (§2B) is the raw material for coverage estimation. Caveat: sources
   must be reasonably independent; cross-validate, never trust a single 3-source model.
2. **Golden reference-set recall.** A periodically-refreshed, hand-curated set of events
   *known* real for sampled market-nights (a manual neighborhood sweep, ticketing-partner
   data). `recall = have ∩ gold / gold`. This extends our existing `ai/golden/` discipline from
   *extraction* accuracy to *ingestion* coverage.
3. Sanity-check both against a **top-down TAM/SAM/SOM** market estimate; disagreement is
   itself a finding.

---

## §4 · Search & discovery quality — "venues available vs venues shown"

This is the founder's "venues available vs venues shown in a search," made precise.

- **Zero-result rate** = `zero_result_searches / searches` — best-in-class < 5%; each zero is
  a coverage-gap demand signal (we already log unmatched search terms for the taxonomy growth
  loop — extend it).
- **Available-vs-shown** = `shown_relevant / indexed_relevant` — the on-platform recall: of
  relevant events that exist in our index, how many surfaced.
- **Search abandonment** = leave-after-results rate (target < 25–30%).
- **Ranking quality** (against graded relevance labels): **Precision@K**, **Recall@K**,
  **MRR** (first-relevant position), **NDCG@K** (graded, position-discounted — ideal for our
  `confirmed > likely > unverified` gradient). Report set-quality + rank-quality + funnel
  together; they answer different questions.
- **Marketplace liquidity** — the two-sided roll-up: probability a searcher finds a
  satisfactory match in acceptable time. Watch searcher-fill-rate vs supply-sell-through and
  their ratio.

---

## §5 · Engagement, retention, usage — including "by feature including usage"

- **North Star Metric (candidate):** *verified event-discoveries acted on per week* — searches
  that led to a save/attend/share on a **trustworthy** event; it bakes coverage + accuracy +
  engagement into one number. Input levers: coverage %, zero-result rate, confirmed-share,
  returning-searcher rate.
- **Lifecycle (AARRR):** acquisition → activation → **retention (most important)** → referral
  → revenue, measured per side.
- **Usage:** activation (first acted-on verified event within N days), DAU/WAU/MAU (WAU is the
  natural cadence — people don't go out nightly), **stickiness** DAU/MAU, **cohort retention
  curves** (find the plateau = retained core).
- **Feature adoption & usage** (the founder's "by feature including usage"): for each surface —
  **Browse, Ask, Plan, filters, search, contextual preview/listen, share, venue contact,
  nearby, tasting-trail, detail** — track adoption (`adopted/eligible`), usage frequency, and
  contribution to the North Star. This tells us which features actually make the product easier
  and more loved (the founder's world-class bar), and which are noise.

---

## §6 · ITR rate-of-change — the "changes over time (3/12, 6/12, 12/12)" engine

**Every** metric above is captured as a **monthly series** and trended the ITR way — two
layers always shown together: the **level** (a moving total: "how big?") and the
**rate-of-change** (year-over-year % of that moving total: "which direction, how fast, what
phase?"). Turns in the ROC **lead** turns in the level — that early warning is the point.

### Formulas (verified against ITR's own method)
Let `x[t]` be the monthly count. `nMMT[t] = Σ_{k=0..n-1} x[t−k]` (n-month moving total).

- **1/12** = `(x[t] / x[t−12] − 1) × 100` — single month; noisiest.
- **3/12** = `(3MMT[t] / 3MMT[t−12] − 1) × 100` — **leading** signal of a turn.
- **6/12** = `(6MMT[t] / 6MMT[t−12] − 1) × 100` — intermediate confirmation.
- **12/12** = `(12MMT[t] / 12MMT[t−12] − 1) × 100` — smoothest; the **trend & cycle-phase**
  gauge. (Worked: 12MMT 20.3 now vs 18.0 a year ago → `(20.3/18.0−1)×100 = +12.7%`.)

The ROC is identical for the moving total or the moving average (the divisor cancels).

### Business-cycle phase (classify each month from the **12/12**)
Two attributes — is the 12/12 **rising or falling**, and **above or below zero**:

| Phase | 12/12 direction | vs zero | Meaning |
|---|---|---|---|
| **A · Recovery** | rising | below 0 | still down YoY, but decline easing — bottom is in |
| **B · Accelerating growth** | rising | above 0 | growing YoY *and* speeding up — strongest phase |
| **C · Slowing growth** | falling | above 0 | still growing YoY but decelerating — the treacherous back side (level at all-time high while growth already rolling over) |
| **D · Recession** | falling | below 0 | down YoY and worsening |

The **3/12 crossing the 12/12** is the practical early trigger (a "checking point"); confirm a
phase turn with ITR's debounce (≈3 months of 3/12 above 12/12 + a tentative 12/12 low) — never
call a turn off one month.

### Applying ITR to our COUNTS (the caveats that keep it honest)
- **History minimum:** a 12/12 needs ≥ **24 months** of data (12MMT now + 12MMT a year ago);
  a 3/12 needs ≥ 15 months. Until then the metric literally **does not exist** — print "not
  yet computable (needs N more months)", never fabricate (§0.1).
- **Immature series distort ROC:** a young metric shows arithmetic-artifact ROCs (300%+) off a
  tiny base — suppress/flag phase signals until the base is large and stable.
- **Seasonality is already handled** by the 12-month total (one of each calendar month) — do
  **not** additionally seasonally-adjust (a big win for nightlife's weekend/summer spikes).
- **Stock vs flow:** sum *flows* (events/month, searches/month) as moving **totals**; for
  point-in-time *stocks* ("venues live at month-end", MAU) use the moving **average** or the
  raw month-end level with a 12-month lag — a total would double-count persistent entities.
- **Guard zero/tiny denominators** — a year-ago window of ~0 makes the ratio explode; flag,
  don't emit a spurious %.

---

## §7 · The architecture that answers *any* question

The metric taxonomy is *what*; this is the *how* that makes every metric sliceable by any
dimension and trendable over any period.

1. **Governed event tracking.** Every user/system action is an event with a stable
   `object-action` name (`Search Executed`, `Event Shown`, `Event Saved`, `Candidate
   Promoted`), typed properties, and a stable opaque identity (no PII). A tracking-plan
   registry prevents the "we didn't log that" wall. This is the feedstock.
2. **Kimball dimensional model — facts + conformed dimensions.**
   - *Facts (three grains):* **transaction** (`fact_search`, `fact_event_shown` — one row per
     event), **periodic snapshot** (nightly/weekly state — §7.4), **accumulating snapshot**
     (`fact_pipeline` — one row per candidate, updated as it moves ingested→extracted→gated→
     promoted, giving stage-conversion + latency).
   - *Conformed dimensions* (one shared definition, reused everywhere): `dim_event`,
     `dim_venue`, `dim_artist`, `dim_org`, `dim_source`, `dim_searcher`, `dim_geo` (CAPCOG
     county/area), `dim_date`, `dim_category` (the 22), `dim_genre` (the 18),
     `dim_confidence_state`, `dim_feature`. Conformed dimensions are what let "coverage by
     genre" and "retention by genre" share one axis.
3. **Slowly-Changing Dimensions (Type 2)** — never overwrite an entity attribute; insert a new
   row with `valid_from / valid_to / is_current`. This is how we answer "what was true *then*"
   — how long events sit in `unverified` before promotion, whether a venue's data quality
   improved after we added a source. (Type 2 is mandatory for a platform that must audit its
   own trust decisions over time.)
4. **Periodic snapshots** (the "change over time" substrate): nightly `snapshot_market_coverage`
   (per market: estimated_universe, ingested, coverage %, confidence distribution,
   zero-result-rate), nightly `snapshot_event_state`, weekly `snapshot_engagement`. **The
   snapshot grain is the finest slice you can ever trend — you cannot reconstruct a snapshot
   you never took.** Rate-of-change then falls out of the snapshot series with a simple `LAG`.
5. **A semantic / metrics layer** — define each metric **once**, centrally, in version-
   controlled code (dbt-Semantic-Layer / MetricFlow or Cube pattern), so "coverage %" and
   "active user" mean exactly one thing in the ops console, the founder digest, and any ad-hoc
   query. Put the metric spine (§10) here first.

---

## §8 · What already exists to build on (don't reinvent)

- **KPI registry + reporter + ledger** (`docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md`,
  `docs/metrics/kpi_registry.json`, `tools/kpi_report.py`, `KPI_LEDGER.md`) — 15 KPIs across
  ingestion/coverage, extraction, cost, brain, UX, trust, with the honest "not yet
  instrumented" pattern. **This is the seed of the semantic layer.**
- **Kaizen ledger** (`docs/metrics/KAIZEN_LEDGER.md`) — per-PR defect/quality rows; the escaped-
  error and caught-defect metrics.
- **Extraction eval** (`ai/golden_exam.py`, `extraction-eval.yml`) — precision/recall/F1 machinery.
- **Source pathway status + probe** (`tools/source_pathways.py`, `real_source_probe.py`) — the
  source-coverage numerator and LIVE/status tally.
- **Entity resolution** (`worker/resolve_entities.py`), **CAPCOG geo** (`worker/region/capcog.py`,
  tri-state True/False/None — "None = we don't know", never guessed) — the uniqueness + geo
  dimensions.

**Genuinely absent (the build):** any product-usage event capture, an analytics/warehouse
store, periodic snapshot tables, the semantic layer, the coverage denominator (capture-
recapture), and per-event cost logging (the §14.2 unit economic — logged nowhere today).

---

## §9 · Guardrails & open founder decisions

- **Founder-crucial (money/new service/credentials):** choosing & keying any analytics vendor
  (PostHog), any warehouse/dbt, and any spend. Interim posture already on record: Vercel
  Analytics + Supabase logs + Sentry to start; PostHog only at launch, founder-minted.
- **Open policy gap to ratify:** a dedicated **no-PII / opt-in analytics privacy policy** does
  not yet exist as canon (deep-review §13 privacy is still a PROPOSAL). §0.3 states the intent;
  it needs formal ratification before user-behavior capture ships.
- **Trust invariants that bound analytics:** metrics never rank the feed; disputed stays shown;
  tastemaker data never mixes with the event pipeline; the honesty floor (never a guessed
  number).

---

## §10 · The go-live starter set (instrument these first, in the semantic layer)

Small, honest, and immediately trendable — the minimum that lets us answer real questions from
day one and grow into the full framework:

1. **Coverage %** per market (with its capture-recapture + golden-set denominator) — breadth.
2. **Confidence distribution** (confirmed / likely / unverified / **disputed** share) of shown
   events — depth/trust.
3. **Escaped-error rate** + extraction **F1** — accuracy (extend existing).
4. **Zero-result rate** & **available-vs-shown** — search quality.
5. **North Star**: verified discoveries acted-on per week, + its 3–5 input levers — usage.
6. **Two-sided retention** (searcher + supply cohorts) — usage.
7. **Cost per verified published event** (§14.2) — unit economics (needs per-event cost logging).
8. **Source coverage** (LIVE / known) — supply health (already partly built).

Each defined **once** in the semantic layer, **snapshotted** nightly/weekly, **sliceable** by
market / category(22) / genre(18) / source / confidence / feature, and **trended** with
**3/12, 6/12, 12/12** + phase once ≥24 months of history exist (until then: honest "not yet
computable").

---

## §11 · Build sequence

**Phase 1 — capture (no vendor needed):** define the tracking plan (event taxonomy, no PII);
log search/shown/acted events + per-event cost + candidate source-overlap to Supabase tables.
This alone unblocks funnel, zero-result, cost, and coverage-overlap metrics.

**Phase 2 — model & snapshot:** stand up the fact/dimension tables (SCD-2 dims) and the nightly/
weekly snapshot jobs (dead-man-pinged). Rate-of-change becomes a query.

**Phase 3 — semantic layer & the spine:** define the §10 metrics once; wire the ITR ROC + phase
computation; surface level+ROC pairs in the ops console and founder digest.

**Phase 4 — denominator program:** the capture-recapture + golden-reference-set coverage
estimation — the highest-leverage measurement investment (turns yield into honest coverage).

**Phase 5 (founder-gated):** a vendor (PostHog) and/or warehouse+dbt if scale demands it.

**Discipline throughout:** never a guessed number; metrics never rank; no PII; every deferral a
Record trigger.

---

## Appendix · Method sources
ITR Economics rates-of-change & Management Objectives (12/12·3/12, A/B/C/D phases); DAMA-DMBOK
data-quality dimensions; Barr Moses five pillars of data observability; Multiple Systems
(capture–recapture) Estimation; a16z marketplace liquidity; MRR/MAP/NDCG retrieval-evaluation;
Amplitude North Star + AARRR; Kimball dimensional modeling (facts/dimensions, three grains,
SCD-2, periodic snapshots); dbt Semantic Layer / MetricFlow. Grounding in OneLive's real model:
the 22 categories (`worker/importers/domain_map.py`), 18 genres (`web/lib/genres.ts`), 4
confidence states (`worker/confidence.py`), source catalog (`sources/master_sources_catalog_120.json`),
existing KPI/Kaizen tooling (`docs/metrics/`).
