# KAIZEN — continuous improvement with measures (founder-ratified 2026-07-14)

Greppable summary: the measurement layer over the existing improvement loop
(validate = stop-the-line; AGENT_FEEDBACK = hansei; RECORD.md = deviation
register). Founder direction: Kaizen with levels and measures and a goal of
zero errors, applied to the overall process and to each step. Framing per
Deming: the absolute goal is ZERO ESCAPED DEFECTS (nothing wrong reaches
users or the trust surface); internally-caught defects are TREASURE — each
one is counted, classified, and mined for the process fix that prevents its
class. A high internal catch-count with zero escapes is the system working.
Ledger: `docs/metrics/KAIZEN_LEDGER.md` (append per PR/session close).
Maturity LEVELS are deliberately deferred until the pipeline runs real data —
RECORD.md R-012 holds the objective trigger.

## The two-goal structure (why not a blanket "zero errors")

Deming's critique of zero-defect slogans: an unqualified zero-errors goal
makes people hide errors — the exact opposite of the Record's
no-silent-deferrals rule. So the goal splits:
1. **Zero ESCAPED defects (absolute):** nothing incorrect reaches users, the
   trust surface, or production data. Any escape is a Sev-defect: root-caused
   in the changelog, its gate-gap closed, its class added to a gate.
2. **Internal catches are mined, not minimized:** every defect found by any
   gate (evaluator, trust_gate, lint, deferral_scan, pytest, friction) gets a
   ledger row — what, which gate caught it, which class, what process change
   (if any) prevents the class. The number found may be high; the trend that
   must fall is REPEAT CLASSES.

## Measures (recorded per PR at merge, and per session at close)

| ID | Measure | What it tells us | World-class direction |
|---|---|---|---|
| M1 | Evaluator rounds-to-green per PR | Convergence quality of generated work | falling trend |
| M2 | Defects caught, by gate and by class | Which gates earn their keep; which classes repeat | repeat-classes → 0 |
| M3 | Escaped defects (found after merge/deploy) | THE goal metric | 0, always |
| M4 | Gate-gap fixes shipped (a catch that produced a new/tightened gate) | Compounding improvement | steady > 0 |
| M5 | Cost per merged PR (evaluator calls + CI minutes, est.) | Efficiency at the same bar (charter Cost discipline) | falling at flat quality |
| M6 | Po-sourced ideas surviving gates (docs/skills/po_provocation.md) | Whether divergence is producing adopted value | > 0 over time |
| M8 | Yellow-hat validated upside (docs/hats/yellow.md) | Whether the deliberate best-case lens produces adopted real value, not hype | asserted→validated conversion rising |
| M9 | Expected-vs-actual performance (prediction calibration) | Whether a claimed improvement actually landed, AND whether we predict well | prediction MET-rate rising; \|actual−expected\| shrinking |

(M7 — the extraction hallucination ratchet — is defined in its own section
below rather than in this table; the number is not skipped. M9 — the
expected-vs-actual discipline — likewise has its own section below.)

Recording rules: one ledger row per merged PR (M1/M2/M5), plus rows for any
M3 escape (immediately, not at close), M4 gate-gap fix, or M6 harvest, or
M9 performance prediction (opened in the SAME commit as the change that makes
the claim; measured at its trigger).
Session close (docs/SESSION_START.md) appends the session's rows; the weekly
founder digest quotes the trends in plain language.

In-flight repeat-class rule (added 2026-07-17, from the r22–r24 lesson on
PR #28): class detection must not wait for the merge-time ledger row. After
EVERY evaluator round, classify the round's findings before fixing them;
if any finding shares a class with the previous round on the same PR, stop
patching that instance and fix the CLASS — enumerate or (better) DERIVE the
complete set the defect lives in, in the same commit. Three consecutive
rounds of one class on one PR (r22 golden set → r23 scoring files → r24
dependencies, each round hand-adding one item to a binding list) cost two
avoidable rounds; a derived-closure check written at r22 would have ended
the class in one. Corollary for lists specifically: a hand-maintained
enumeration guarding a trust property (a manifest, an allowlist, a trigger
list, a mirror of another list) is a defect class waiting to repeat — every
such list gets a test that derives or cross-checks it against ground truth.
## Hat measures (added 2026-07-16 — docs/hats/)

Each dedicated hat (docs/hats/README.md) declares three things in its
registry file: its **measure**, its **counter-measure** (the Goodhart
inverse — a hat rewarded per catch will manufacture catches), and its
**escape definition** (what it means for that hat to have failed). No new
ledgers: hats are catchers named in M2 (e.g. gate `blue-merge`, class
`smoothed-conflict`), gate-gap sources in M4 (each hat's drain toward
mechanization), and M6/M8 hold the Green/Yellow harvests — everything in
the one ledger so cross-hat trends (a class escaping one hat, caught by
another) stay visible in one table.

## Per-step application (founder: "to each step in the process")

Every pipeline stage (Sources → Fetch → Extract → Gate → Promote → /tonight)
and every harness gate gets the same treatment when it runs for real: its
own defect classes in M2, its own escape definition for M3 (e.g. Extract's
escape = a hallucinated fact passing the gate; Promote's = an unverified
event published). The eval-harness thresholds (§11.2) are Extract's M3
instrument. No stage is "done" at world-class without its measures flowing.

## Extraction ratchet (M7) — founder-ratified 2026-07-15: "BEGIN at 1%"

The extraction hallucination threshold starts at **≤ 1%** (release-blocking,
R-006 RESOLVED) and only ever TIGHTENS — a one-way ratchet driven by
measurement, never by optimism.

**1% of WHAT — the exact unit (founder question, 2026-07-15):** the
countable unit is a **field assertion** — one claimed fact about one event
(title, artist names, venue, date, start time, price, ticket URL, …).
Implementation: `ai/eval_harness.py::hallucination_rate`.
- **Numerator** (a hallucination): the extractor asserts a field the
  source text does not support — either INVENTED (source contains no such
  fact) or WRONG (source says 9pm, extractor says 8pm; counted as both a
  hallucination and a miss, deliberately harsh).
- **Denominator**: ALL fields the extractor asserted across the measured
  corpus (micro-averaged). Fields it correctly left empty don't pad the
  score; bookkeeping fields (`_provenance`) are excluded; trivial
  case/whitespace differences don't count as errors, but times are
  compared strictly (the prompt forbids reformatting).
- **So 1% means:** of every 100 individual facts the extractor states, at
  most 1 is unsupported by its source.
- **Anti-gaming pair:** an extractor could look "safe" by asserting
  almost nothing — so RECALL (fraction of truly-present facts captured)
  is measured and reported alongside, and a recall collapse fails review
  even with a perfect hallucination score.
- **Event-level view (secondary, reported not gated):** field-level 1% is
  NOT "1% of events wrong" — an event card asserting ~8 fields could see
  up to ~8% of events carrying ≥1 bad field at the field-level bar. The
  ledger therefore ALSO reports "% of events with ≥1 hallucinated field"
  for product-level visibility, and the downstream gates (corroboration,
  confidence states, admin review) remain the second wall between an
  extraction error and a user.

**How it's measured (two instruments):**
1. **The exam (pre-ship):** every extraction change (model id, prompt,
   parsing) runs the golden set in CI — hallucination rate = invented facts
   ÷ total extracted facts against the answer key. Above threshold = the
   change does not ship.
2. **Production sampling (the Kaizen input):** every admin-review verdict
   (Step 7), every user "Something off?" report, and every gate-caught
   contradiction is checked against what extraction produced. Every
   confirmed extraction error becomes (a) an M2 ledger row (class:
   extraction-hallucination) AND (b) a NEW GOLDEN SET CASE — production
   failures permanently harden the exam. The weekly digest quotes the
   trailing measured rate.

**The ratchet rule (mechanical, no judgment calls):** when the trailing
measured rate holds at ≤ HALF the current threshold for 4 consecutive
weekly cycles AND the sample size makes that measurement statistically
meaningful (below), the threshold drops to 2× the measured rate (rounded
to a clean step: 1% → 0.5% → 0.25% → 0.1% → …). Each drop is a ledger
row + digest line. The threshold never loosens; a regression above the
CURRENT bar is release-blocking and, if it reached users, an M3 escape.

**Sample-size honesty (why the ratchet can't skip ahead):** you cannot
distinguish 0.05% from 0.04% on a 200-fact exam. Verifying a rate p needs
roughly 3/p extracted facts of evidence:

| Threshold step | Minimum evidence (facts measured) |
|---|---|
| 1% | ~300 |
| 0.5% | ~600 |
| 0.1% | ~3,000 |
| 0.01% | ~30,000 |
| 0.001% | ~300,000 |

The golden set + production sampling volume must cross each line before
the ratchet may claim it — so the path to 0.001% is paved by scale itself:
more real traffic → more verified facts → finer measurable thresholds.
Improvement levers between steps: per-source extraction templates (po
harvest), prompt hardening from each error class, structured-output
constraints, and model upgrades that pass the same exam.


## Trend instrumentation (added 2026-07-18 at founder direction — trends are computed, never asserted)

Founder: everything — every action, decision, non-action, the loop, the
harness, the meta — trends toward zero/perfect, and the trend itself must be
measured. The meter: `tools/kaizen_trends.py`, run on every `tools/validate`
pass (advisory: findings make the run non-green; --strict makes them FAIL).
It computes, from the ledger alone:
- **M3 escapes** — 0, absolute (any `M3-ESCAPE` token = hard finding).
- **Repeat-class alarm** — any class family caught ≥3 times with no
  structural-fix marker = finding (the rule the evaluator enforced by
  judgment on PR #35 r2, now mechanical).
- **M1 rounds-to-green direction**, **founder(Red) catches** (must trend to
  0 — each one means every automated layer missed it), **catches per gate**
  (the judgment→mechanical drain, visible), **M4 cumulative**.

Machine-readable conventions the meter relies on (naming discipline IS the
enforcement surface):
1. **Class tokens are single kebab-case tokens** immediately before "×N" in
   M2 (`empty-env ×1`, never "empty env issues ×1"); REUSE the exact token
   for a repeat. Single-word tokens count as classes ONLY from the declared
   short-token registry (`tools/kaizen_trends.py::SHORT_TOKEN_REGISTRY`:
   sql, rls, xss, auth, csrf, ssrf, race, leak — extend it there, in a
   reviewed diff); any other bare word before ×N is prose and must use a
   plain x ("records x4") so it never enters the class grammar. Matching is exact-token + containment families
   (`empty-env` ⊂ `fail-open-empty-env`).
2. **A class fix is marked** by naming the class token in the fixing row's
   M4 column — no marker, no credit, alarm keeps firing. Markers are
   EPOCH-scoped, never permanent waivers (evaluator r6): a marker covers
   catches at-or-before its own row only; ANY catch of the family in a later
   row alarms immediately as a post-fix recurrence ("the fix escaped") and
   demands a root-cause plus a NEW marker row.
3. **M3 escape rows carry the literal token `M3-ESCAPE`.**
4. Rows stay append-only; marker backfills for already-shipped fixes land as
   correction rows referencing the original (see 2026-07-18 backfill row).

What must trend to zero: escapes, repeat classes, founder catches,
rounds-to-green, judgment-dependent catches per class (each hat's drain to
mechanization, docs/hats/). What must NOT be minimized: raw internal catches
— treasure, per the two-goal structure above; suppressing them is the
Deming failure mode this file opens with.

## M9 — Expected-vs-actual performance (added 2026-07-23 at founder direction: "Create 'expected performance improvement' metrics and measure actual vs expected and make it part of the process")

Any change that CLAIMS a performance, cost, latency, or quality improvement
opens an **M9 row** in `docs/metrics/KAIZEN_LEDGER.md` — a PREDICTION — in the
SAME commit that makes the claim, and records the ACTUAL at an objective
trigger. This is the same anti-optimism discipline as M7 (measured, never
asserted) and the no-silent-deferral rule (a claim without a measurement plan
is a silent deferral of the proof): "we expect −45%" is not evidence until
actual-vs-expected is on the ledger.

This structure was HARDENED 2026-07-23 against a triadic red-team of M9 vs
validated practice (Superforecasting/Brier, FinOps forecast-vs-actuals + unit
economics, Google SRE SLI/error-budget, Six Sigma DMAIC + SPC, Earned-Value
variance, clinical-trial pre-registration, A/B causal inference). The red-team's
load-bearing findings — no noise model, confounded before/after attribution, an
undefined MET band, and a categorical verdict that hides systematic bias — are
closed by the field rules below. Full report: the M9 red-team artifact.

**The row's fields (every one required for its status; enforced by
`tools/perf_ledger_scan.py`):**
- **Metric — DIRECT & CAUSAL, one unit.** Prefer a per-unit ratio the change
  causes directly (cache-savings ratio per call; batch-discount per job; LCP, s),
  NOT a confounded aggregate (total spend moves with traffic, source mix, and the
  spend cap — a caching "win" could just be a traffic drop, red-team A3). If only
  an aggregate is available, the Basis field must name the confounders excluded.
- **Baseline — real value + how measured + N.** From a REAL measurement, paired
  to the same workload/window as the eventual actual (no cross-workload baseline
  drift). No baseline → a row may not go MEASURED.
- **Expected %Δ + Basis.** The predicted change and the WHY (vendor estimate,
  arithmetic, or — best — a REFERENCE CLASS: how our last N same-type predictions
  actually landed). No basis → rejected.
- **Trigger & measurement method.** The OBJECTIVE trigger (never "someday") AND
  the pre-registered method for computing `actual` (the exact formula/window/N),
  so the measurer has no post-hoc freedom to pick a flattering window (red-team
  S3, pre-registration).
- **Band.** The numeric tolerance within which the prediction counts as MET
  (e.g. ±10pp). Declared UP FRONT so MET is arithmetic, not judgment (red-team S1).
  The band should reflect the metric's noise: a delta inside the band is not a
  confirmed win, it is indistinguishable from expected (red-team A1, SPC common-
  cause).
- **Actual %Δ + N**, **Signed error (actual − expected)**, **Verdict** —
  `MET` iff |signed error| ≤ Band; `UNDER` (we over-promised, optimism bias) /
  `OVER` (we under-promised — money left on the table, or sandbagging). The error
  is SIGNED on purpose: a MET-rate can hide a systematic +19% optimism; the mean
  signed error cannot (red-team A2, Brier). A miss carries a one-line ROOT CAUSE
  (DMAIC Analyze) that feeds the next prediction's basis.
- **Status** — `PENDING-MEASUREMENT` or `MEASURED`.

**The calibration meta-metric (why this is Kaizen, not a log):** three numbers
trend — mean SIGNED error → 0 (BIAS; catches systematic optimism OR sandbagging),
mean |error| → 0 (ACCURACY), MET-rate ↑ (readable headline). A repeatedly-biased
class (always optimistic on caching, say) is an M2 repeat class with a counter-
measure. INNOVATION (queued): before a new prediction, surface the prior same-
class calibration as the reference-class prior — Kahneman's outside view,
mechanized.

**Process integration (this is the "part of the process" the founder asked for):**
1. **At claim time** — open the M9 row (Metric, Baseline, Expected+Basis,
   Trigger&method, Band) in the change's own commit. `perf_ledger_scan.py` fails
   a PENDING row missing any, so a bare "faster/cheaper" claim can't ship
   unmeasured.
2. **At the trigger** — append Actual+N, Signed error, Verdict (→ MEASURED); the
   scanner checks MET==within-band when the numbers parse.
3. **Continuous, not just on-claim (red-team S2, survivorship):** the unit metric
   (cost-per-verified-event) is meant to be monitored CONTINUOUSLY so a SILENT
   regression — a change nobody predicted — is caught too; M9 rows are the
   predicted subset of that surveillance. (The continuous meter is gated on real
   pipeline volume — tracked here, not silently deferred.)
4. **CONTROL the booked win (DMAIC Control):** once a win is MEASURED, it earns a
   standing ceiling/alarm so it can't silently decay back.
5. **At session close** — review OPEN (PENDING) M9 rows like RECORD.md OPEN rows:
   a fired-but-unmeasured trigger is a defect. `perf_ledger_scan.py` runs here
   (blocking inside `tools/validate` once proven out — a gate-custody change,
   evaluator-reviewed; tracked, not silently deferred).
6. **In the founder digest** — the calibration trend (bias, accuracy) + big misses.

## Levels (deferred — R-012)

Maturity levels per stage (ad-hoc → measured → self-correcting) are real
Kaizen but premature before the pipeline processes real data — levels graded
on an idle factory measure nothing. RECORD.md R-012 holds the objective
trigger: first real scheduled ingestion cycle completes (R-008 resolved +
one cron week) → design the level rubric on actual flow, grade every stage,
add level to the ledger.
