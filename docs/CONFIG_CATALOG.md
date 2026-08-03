# CONFIG CATALOG — what is tunable-by-config vs. protected-by-gate

Founder directive (2026-07-25): *"Make it all config-driven. That should be
incorporated for all similar items."* And, standing: *"Ensure it's functionally
easy and energy moderate to change these elements and their frequency."*

This catalog is the single index of every operational tunable in 1Live. It
answers two questions for each one: **where do I edit it**, and **is it a plain
config edit or a founder-crucial decision?** The split is not cosmetic — it is
the trust boundary.

## The rule that draws the line

There are two kinds of numbers in this system:

1. **Tunables** — weights, cadences, budgets, prioritization knobs. Changing
   them re-tastes the system; it does not weaken any guarantee. These SHOULD be
   plain-data config: one editable JSON file, loaded and **fail-loud-validated**
   by code that never hardcodes the value. Editing them is a 3-step recipe (edit
   JSON → run the tool's `--print`/tests → commit), no code change.

2. **Gate thresholds** — the bars that `validate` / `trust_gate` / the evaluator
   / the eval-harness enforce, and the safety thresholds that keep "AI never
   publishes" true. Lowering one of these is, by definition, a **gate-threshold
   relaxation** — CLAUDE.md's Founder-crucial list names it explicitly and
   CLAUDE.md §"Cost discipline" #3 says *"Quality gates never relax."* Making a
   gate threshold a free JSON edit would hand exactly that relaxation to anyone
   with a text editor. So gate thresholds stay **in code**, changeable only
   through a reviewed PR (and, for the base-owned ones, only by the founder).
   That is not an oversight in the "make it all config-driven" directive — it is
   the one place the directive must NOT reach, because config-driving a gate
   defeats the gate.

Litmus test for a new number: *"If someone edited this to an extreme value with
no review, could a wrong/fabricated event reach a user, or could a failing
change merge?"* If yes → **gate, protect it**. If no → **tunable, config it**.

---

## Part A — Tunables (config-driven; editing them is a plain data edit)

| What | Config file | Loaded + validated by | Frequency field? | Notes |
|---|---|---|---|---|
| **KPIs** — which are tracked, targets, review frequency, area, owner, on/off | `docs/metrics/kpi_registry.json` | `tools/kpi_report.py` `load_kpi_registry()` | yes (`per_run\|daily\|weekly\|monthly\|quarterly`) | Reference implementation. New KPI reusing an existing `compute` or `manual_gap` = JSON-only; a genuinely new measurement needs one function in `_COMPUTE_FUNCTIONS`. Recipe: framework doc §4a. |
| **Brain-IQ weights** — knowledge sub-weights, learning sub-weights, and the knowledge/efficiency/learning composite blend | `brain/config/brain_iq_config.json` | `brain/iq.py` `load_iq_config()` | — | Measurement weightings for the "how smart is the brain" scorecard (three groups: `knowledge_weights`, `learning_weights`, `composite_weights`). NOT a gate: re-weighting changes the reported number, never what merges or publishes. Each group fail-louds unless its weights sum to 1.0. (Efficiency is a formula, `ref/(ref+work)`, not a weight dict — nothing to config there.) |
| **Source-rank weights** — credibility / access-reliability / … blend that orders which sources get crawled first | `worker/config/source_rank_config.json` | `worker/source_rank.py` | — | Prioritization only — decides crawl ORDER under the per-run budget ceiling, never whether an event is trusted. |
| **Per-run AI-spend cap** — max event-blocks extracted per page | env `EXTRACT_MAX_EVENTS_PER_PAGE` (default 50) | `worker/ai_extract.py` `_max_events_per_page()` | — | Budget bound (R-043). Env-driven so a run can tighten it without a code change; the source-count ceiling in `ingest.yml` is the other half of the bound. |
| **Ingestion cadence + source ceiling** — cron schedule, schedule-event source cap | `.github/workflows/ingest.yml` (cron line + `MAX_SOURCES`) | the workflow itself; `tests/test_ingest_workflow_contract.py` binds cadence↔dead-man period | yes (cron) | Editable, but the dead-man period is derived from the cron line by a test, so the two cannot drift silently. |
| **Ledger review cadences** — Kaizen / KPI / digest frequency | `docs/metrics/kpi_registry.json` (`frequency`) + `docs/KAIZEN.md` prose | reporting tools / session loop | yes | The KPI half is now data; the Kaizen prose cadence is a doc edit. |

**Convention for any NEW tunable:** add a JSON file next to the code that uses
it (`<area>/config/<name>_config.json`), a `load_<name>_config()` that
fail-louds on malformed/unknown/missing fields (never a silent default), a test
that a config-only edit changes behavior, and a fail-loud test per invalid case.
Then add a row here.

---

## Part B — Protected (gate thresholds; NOT config-editable; change = reviewed PR / founder-crucial)

These are deliberately **in code**, not in an editable registry. Each row says
why config-driving it would defeat its purpose.

| What | Where it lives | Why it stays protected |
|---|---|---|
| **Extraction certification + `EXTRACTION_THRESHOLD_RATIFIED`** | `tools/trust_gate.py`, `ai/golden/CERTIFIED_HARNESS.json` (base-owned) | The re-lock that keeps a drifted harness from certifying. Flipping it is the founder's 3-step re-open (attended exam → authenticated record → head-bound flag PR). A JSON knob here IS the fail-open. |
| **Trust-gate thresholds** — hallucination ≤1%, recall ≥80% | evaluator gate / `trust_gate` | These ARE the quality bar. CLAUDE.md: identical at every cost tier; relaxing = founder-crucial. |
| **Surface-exam recall floor** (`DEFAULT_RECALL_FLOOR`) | `tools/surface_regression_exam.py` | Gates the surface regression exam. A ratchet with an editable floor proves nothing. |
| **Brain blind-eval floors** | `brain/eval/baselines.json`, `brain/eval/held_out.py` (base-owned, `pull_request_target`) | The held-out floor is base-owned precisely so a PR can't lower its own passing bar. Config-driving it would re-open the gaming hole the base-owned pattern closes. |
| **Publish reliability threshold** (`DEFAULT_RELIABILITY_THRESHOLD` = 0.35) | `worker/publish_policy.py` | Routes often-unreliable sources to human review — a direct guard on gate-custodied publication. Lowering it lets more through unreviewed; that's a trust-invariant decision, not a knob. |
| **Gate custody set** | `tools/validate`, `trust_gate.py`, `deferral_scan.py`, `lint.py`, `adversarial_review.py`, eval-harness, CI gate workflows | Any change here is mandatorily evaluator-reviewed (CLAUDE.md Agent org). Config-driving a gate's own enforcement is the thing the custody rule exists to prevent. |

**If a future change wants to make any Part-B item config-editable:** that is a
gate-threshold relaxation — STOP and escalate to the founder (CLAUDE.md
Founder-crucial). It is never an agent decision, and it does not become one by
calling it "config-driven."

---

## Why this exists (the honest tradeoff)

Making tunables easy to change is pure upside: the founder can re-cadence a KPI
or re-weight the brain scorecard in seconds, and fail-loud validation means a
typo stops the tool instead of silently corrupting a number. The cost is the
discipline of the split — every new number has to be classified before it's
added, and getting the classification wrong (config-driving a gate) would be a
trust regression, not a convenience. That classification lives here, in the
open, so the boundary is auditable rather than implicit.
