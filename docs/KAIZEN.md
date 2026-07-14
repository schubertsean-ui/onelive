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

Recording rules: one ledger row per merged PR (M1/M2/M5), plus rows for any
M3 escape (immediately, not at close), M4 gate-gap fix, or M6 harvest.
Session close (docs/SESSION_START.md) appends the session's rows; the weekly
founder digest quotes the trends in plain language.

## Per-step application (founder: "to each step in the process")

Every pipeline stage (Sources → Fetch → Extract → Gate → Promote → /tonight)
and every harness gate gets the same treatment when it runs for real: its
own defect classes in M2, its own escape definition for M3 (e.g. Extract's
escape = a hallucinated fact passing the gate; Promote's = an unverified
event published). The eval-harness thresholds (§11.2) are Extract's M3
instrument. No stage is "done" at world-class without its measures flowing.

## Levels (deferred — R-012)

Maturity levels per stage (ad-hoc → measured → self-correcting) are real
Kaizen but premature before the pipeline processes real data — levels graded
on an idle factory measure nothing. RECORD.md R-012 holds the objective
trigger: first real scheduled ingestion cycle completes (R-008 resolved +
one cron week) → design the level rubric on actual flow, grade every stage,
add level to the ledger.
