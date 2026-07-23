# Audit records must recompute derived values from ground truth, not validate them within a tolerance you then key a decision off of.

Context: PR #54 (C2 decision layer) needed 18 evaluator rounds; the last and
sharpest blocking defect was a subtle fail-open in `DecisionRecord`
self-verification. The reusable lesson generalizes to any trust-path audit record.

## The trap
A `DecisionRecord` stores `chosen`, `expected_losses` (per-action totals), `terms`
(per-cell `P(mode)*cost`), `mode_probs`, and the cost `matrix`. Early rounds made
the recorded `chosen` the **deterministic** tie-break winner — but computed it from
the **stored** `expected_losses`. Those totals were only checked to match the terms
sum **within `_SUM_EPS` (1e-6)**. So a forger could store true totals
`a=1.0000005, b=1.0` as an exact tie `a=b=1.0` (inside the tolerance), and the
tie-break would pick `a` while `decide()` would really pick `b`. The audit record
would claim a winner the pipeline would never produce — fabricated evidence that
passed every tolerance check.

## The fix (the rule)
Derive the decision from the **ground truth the record commits to** — recompute
`mode_probs × matrix` in the record's own action order, **exactly** as the producer
(`decide()`) does — and require the stored derived values to equal that
recomputation **exactly** (not within eps). `decide()` is deterministic, so a
genuine record is bit-for-bit identical; only a forgery diverges. The choice is
then pinned to the pure-function output with no tolerated middleman.

## Generalize
- An `_SUM_EPS`/tolerance is fine for *detecting* internal inconsistency, but never
  let a downstream DECISION (a tie-break, a winner, a gate action) read off a value
  that is only tolerance-validated. Recompute the decision from the inputs the
  record carries, exactly.
- "Fails loud on impossible values" is not the same as "cannot be forged to a
  wrong-but-plausible value." The second bar is what trust-path audit evidence
  needs; reach it by making the derived fields recomputable and requiring exact
  agreement, not by adding more tolerance checks.
- Order matters when a tie-break policy exists: the deterministic winner is the
  first minimizer in the record's own action order (the key order of the totals
  map) — compare ordered, not as a set.

## Process lesson (see Kaizen M2, 2026-07-23)
Forgery-resistance of audit records converges slowly under an adversarial reviewer.
Land self-verification as its own small PR with the "recompute from ground truth,
no tolerated middleman in the decision" invariant stated up front, so the class is
designed in rather than discovered round by round. A large single diff also
compounds per-round review cost.
