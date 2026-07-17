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

(M7 — the extraction hallucination ratchet — is defined in its own section
below rather than in this table; the number is not skipped.)

Recording rules: one ledger row per merged PR (M1/M2/M5), plus rows for any
M3 escape (immediately, not at close), M4 gate-gap fix, or M6 harvest.
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

## Levels (deferred — R-012)

Maturity levels per stage (ad-hoc → measured → self-correcting) are real
Kaizen but premature before the pipeline processes real data — levels graded
on an idle factory measure nothing. RECORD.md R-012 holds the objective
trigger: first real scheduled ingestion cycle completes (R-008 resolved +
one cron week) → design the level rubric on actual flow, grade every stage,
add level to the ledger.
