# Adversarial-review diff cap: 800,000 bytes, founder-ratified.

**Ratified:** 2026-07-16, founder: "approve 800k cap."

## The decision

`adversarial-review.yml` runs the evaluator with `--max-diff-bytes 800000`
(raised from the script's 300,000 default). The founder ratified this value
explicitly, closing the evaluator r23 (PR #18) finding that the raise carried
no recorded founder approval as the gate-custody amendment requires.

## Why this value exists (history, so nobody re-litigates it)

- PR #18 r6: a 405KB research diff hard-failed the 300KB cap (fail-closed
  working as designed).
- The Generator's first fix — excluding its own evidence appendices from the
  reviewed diff — was REJECTED by evaluator r7 as evidence-hiding: "shown,
  never hidden" applies to our own evidence, and adversarial review exists to
  read exactly that material.
- The sanctioned alternative was a VISIBLY raised cap with in-workflow
  rationale: a bigger review window, not a softer gate. Behavior above the
  cap is unchanged — the run HARD-FAILS rather than truncating (`--require`).
- The gate-custody amendment (2026-07-14) later made all gate-threshold
  changes founder-crucial; this raise predated it, so r23 correctly demanded
  the founder record. This document is that record.

## Scope and boundaries

- The cap is a **review-capacity bound**, not a quality threshold: no verdict
  logic, review depth, or fail-closed behavior changes with it.
- Third-party fetched corpus files (`ventures/promise_ledger/eval/
  source_material/`) are excluded from the diff under the lockfile precedent
  and validated by manifest sha256 tests instead — our own authored evidence
  is never excluded (r7 rule).
- Any FUTURE change to this value, in either direction, is a new
  founder-crucial decision: down risks unreviewable evidence-rich PRs; up
  risks review dilution. Neither is an agent call.
