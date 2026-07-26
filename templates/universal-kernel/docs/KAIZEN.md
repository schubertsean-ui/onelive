# KAIZEN — continuous improvement with measures

> **KERNEL DOC — project-agnostic, inherited verbatim.** This file describes the
> METHOD and nothing about any particular product. Project specifics (the quality
> metric, its unit, its starting threshold, the pipeline stages) live in
> `OVERLAY.md`. Text in `[square brackets]` is a placeholder the overlay must bind.

Greppable summary: the measurement layer over the existing improvement loop
(`tools/validate` = stop-the-line; `docs/AGENT_FEEDBACK.md` = hansei; `docs/RECORD.md`
= deviation register). The standing direction: Kaizen with levels and measures and
a goal of zero errors, applied to the overall process and to each step. Framing per
Deming: the absolute goal is ZERO ESCAPED DEFECTS (nothing wrong reaches
users or [trusted surface]); internally-caught defects are TREASURE — each
one is counted, classified, and mined for the process fix that prevents its
class. A high internal catch-count with zero escapes is the system working.
Ledger: `docs/metrics/KAIZEN_LEDGER.md` (append per PR/session close).
Maturity LEVELS are deliberately deferred until the pipeline runs real data —
a `docs/RECORD.md` row holds the objective trigger.

## The two-goal structure (why not a blanket "zero errors")

Deming's critique of zero-defect slogans: an unqualified zero-errors goal
makes people hide errors — the exact opposite of the Record's
no-silent-deferrals rule. So the goal splits:
1. **Zero ESCAPED defects (absolute):** nothing incorrect reaches users,
   [trusted surface], or production data. Any escape is a Sev-defect: root-caused
   in the changelog, its gate-gap closed, its class added to a gate.
2. **Internal catches are mined, not minimized:** every defect found by any
   gate (the Independent Evaluator, [project trust gate], `tools/lint.py`, `tools/deferral_scan.py`, the test suite,
   friction) gets a ledger row — what, which gate caught it, which class, what
   process change (if any) prevents the class. The number found may be high; the
   trend that must fall is REPEAT CLASSES.

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

(M7 — the quality ratchet — is defined in its own section below rather than in
this table; the number is not skipped.)

Recording rules: one ledger row per merged PR (M1/M2/M5), plus rows for any
M3 escape (immediately, not at close), M4 gate-gap fix, or M6 harvest.
Session close (docs/SESSION_START.md) appends the session's rows; the weekly
owner digest quotes the trends in plain language.

In-flight repeat-class rule: class detection must not wait for the merge-time
ledger row. After EVERY evaluator round, classify the round's findings before
fixing them; if any finding shares a class with the previous round on the same PR,
stop patching that instance and fix the CLASS — enumerate or (better) DERIVE the
complete set the defect lives in, in the same commit.
ILLUSTRATIVE EXAMPLE (origin project, the lesson that produced this rule): three
consecutive rounds of one class on one PR (r22 the golden set → r23 the scoring
files → r24 the dependencies, each round hand-adding one item to a binding list)
cost two avoidable rounds; a derived-closure check written at r22 would have ended
the class in one. Corollary for lists specifically: a hand-maintained
enumeration guarding a trust property (a manifest, an allowlist, a trigger
list, a mirror of another list) is a defect class waiting to repeat — every
such list gets a test that derives or cross-checks it against ground truth.

## Hat measures (docs/hats/)

Each dedicated hat (docs/hats/README.md) declares three things in its
registry file: its **measure**, its **counter-measure** (the Goodhart
inverse — a hat rewarded per catch will manufacture catches), and its
**escape definition** (what it means for that hat to have failed). No new
ledgers: hats are catchers named in M2 (e.g. gate `blue-merge`, class
`smoothed-conflict`), gate-gap sources in M4 (each hat's drain toward
mechanization), and M6/M8 hold the Green/Yellow harvests — everything in
the one ledger so cross-hat trends (a class escaping one hat, caught by
another) stay visible in one table.

## Per-step application ("to each step in the process")

Every pipeline stage declared in `OVERLAY.md` and every harness gate gets the
same treatment when it runs for real: its own defect classes in M2, its own
escape definition for M3 (e.g. the generative stage's escape = a fabricated fact
passing [promote gate]; the publish stage's = an unverified record reaching
[trusted surface]). The [eval harness] thresholds are the generative stage's M3
instrument. No stage is "done" at world-class without its measures flowing.

## The quality ratchet (M7)

The project's [primary quality metric] starts at a ratified threshold
([starting threshold], release-blocking) and only ever TIGHTENS — a one-way
ratchet driven by measurement, never by optimism.

**A threshold of WHAT — the exact unit:** the countable unit must be named
before the number means anything ([countable unit] in `OVERLAY.md`;
implementation in [eval harness]).
- **Numerator** (a defect): the system asserts something its source does not
  support — either INVENTED (the source contains no such fact) or WRONG (the
  source says one value, the system says another; counted as both a defect and a
  miss, deliberately harsh).
- **Denominator**: ALL units the system asserted across the measured
  corpus (micro-averaged). Units it correctly left empty don't pad the
  score; bookkeeping fields (provenance) are excluded; trivial
  case/whitespace differences don't count as errors, but the fields the prompt
  forbids reformatting are compared strictly.
- **So the threshold means:** of every 100 individual assertions the system
  states, at most [starting threshold] are unsupported by its source.
- **Anti-gaming pair:** a system could look "safe" by asserting
  almost nothing — so RECALL (fraction of truly-present units captured)
  is measured and reported alongside, and a recall collapse fails review
  even with a perfect defect score.
- **Record-level view (secondary, reported not gated):** a unit-level rate is
  NOT the same as a record-level rate — a record asserting ~N units could see up
  to ~N× the unit-level rate of records carrying ≥1 bad unit. The ledger
  therefore ALSO reports "% of records with ≥1 defective unit" for
  product-level visibility, and the downstream gates (corroboration,
  trust states, human review) remain the second wall between an
  extraction error and a user.

**How it's measured (two instruments):**
1. **The exam (pre-ship):** every change to the measured surface (model id,
   prompt, parsing) runs [golden set] in CI — the rate is computed against the
   answer key. Above threshold = the change does not ship.
2. **Production sampling (the Kaizen input):** every human-review verdict,
   every user "something looks wrong" report, and every gate-caught
   contradiction is checked against what the system produced. Every
   confirmed error becomes (a) an M2 ledger row AND (b) a NEW [golden set]
   CASE — production failures permanently harden the exam. The weekly digest
   quotes the trailing measured rate.

**The ratchet rule (mechanical, no judgment calls):** when the trailing
measured rate holds at ≤ HALF the current threshold for 4 consecutive
weekly cycles AND the sample size makes that measurement statistically
meaningful (below), the threshold drops to 2× the measured rate (rounded
to a clean step: 1% → 0.5% → 0.25% → 0.1% → …). Each drop is a ledger
row + digest line. The threshold never loosens; a regression above the
CURRENT bar is release-blocking and, if it reached users, an M3 escape.

**Sample-size honesty (why the ratchet can't skip ahead):** you cannot
distinguish 0.05% from 0.04% on a 200-unit exam. Verifying a rate p needs
roughly 3/p measured units of evidence:

| Threshold step | Minimum evidence (units measured) |
|---|---|
| 1% | ~300 |
| 0.5% | ~600 |
| 0.1% | ~3,000 |
| 0.01% | ~30,000 |
| 0.001% | ~300,000 |

[golden set] + production sampling volume must cross each line before
the ratchet may claim it — so the path to 0.001% is paved by scale itself:
more real traffic → more verified units → finer measurable thresholds.
Improvement levers between steps: per-source templates (po harvest), prompt
hardening from each error class, structured-output constraints, and model
upgrades that pass the same exam.

## Trend instrumentation (trends are computed, never asserted)

Everything — every action, decision, non-action, the loop, the harness, the meta
— trends toward zero/perfect, and the trend itself must be measured. The meter:
`tools/kaizen_trends.py`, run on every `tools/validate` pass (advisory: findings make the run
non-green; `--strict` makes them FAIL). It computes, from the ledger alone:
- **M3 escapes** — 0, absolute (any `M3-ESCAPE` token = hard finding).
- **Repeat-class alarm** — any class family caught ≥3 times with no
  structural-fix marker = finding (a rule the evaluator first enforced by
  judgment, now mechanical).
- **M1 rounds-to-green direction**, **founder/Red catches** (must trend to
  0 — each one means every automated layer missed it), **catches per gate**
  (the judgment→mechanical drain, visible), **M4 cumulative**.

Machine-readable conventions the meter relies on (naming discipline IS the
enforcement surface):
1. **Class tokens are single kebab-case tokens** immediately before "×N" in
   M2 (`empty-env ×1`, never "empty env issues ×1"); REUSE the exact token
   for a repeat. Single-word tokens count as classes ONLY from the declared
   short-token registry inside `tools/kaizen_trends.py` (sql, rls, xss, auth, csrf, ssrf,
   race, leak — extend it there, in a reviewed diff); any other bare word
   before ×N is prose and must use a plain x ("records x4") so it never enters
   the class grammar. Matching is exact-token + containment families
   (`empty-env` ⊂ `fail-open-empty-env`).
2. **A class fix is marked** by naming the class token in the fixing row's
   M4 column — no marker, no credit, alarm keeps firing. Markers are
   EPOCH-scoped, never permanent waivers: a marker covers catches at-or-before
   its own row only; ANY catch of the family in a later row alarms immediately
   as a post-fix recurrence ("the fix escaped") and demands a root-cause plus a
   NEW marker row.
3. **M3 escape rows carry the literal token `M3-ESCAPE`.**
4. Rows stay append-only; marker backfills for already-shipped fixes land as
   correction rows referencing the original.

What must trend to zero: escapes, repeat classes, founder catches,
rounds-to-green, judgment-dependent catches per class (each hat's drain to
mechanization, docs/hats/). What must NOT be minimized: raw internal catches
— treasure, per the two-goal structure above; suppressing them is the
Deming failure mode this file opens with.

## Levels (deferred)

Maturity levels per stage (ad-hoc → measured → self-correcting) are real
Kaizen but premature before the pipeline processes real data — levels graded
on an idle factory measure nothing. A `docs/RECORD.md` row holds the objective
trigger: first real production cycle completes → design the level rubric on
actual flow, grade every stage, add level to the ledger.
