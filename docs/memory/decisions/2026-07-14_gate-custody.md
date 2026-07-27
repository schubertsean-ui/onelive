# Gate custody: the Generator never merges an unreviewed change to its own examiners; gate relaxations interrupt the founder.

**Ratified:** 2026-07-14, founder: "I approve the charter amendment."

## The decision

Two additions to the charter (CLAUDE.md):

1. **Gate custody joins the evaluator-MANDATORY list.** Any change to
   verification tooling or its thresholds (`tools/validate`, `trust_gate.py`,
   `deferral_scan.py`, `lint.py`, `adversarial_review.py`, `eval_harness`,
   the CI gate workflows) requires independent non-Claude evaluator approval.
2. **Gate-threshold relaxations are founder-crucial.** Any loosening of
   validate/trust_gate/evaluator/eval-harness enforcement interrupts the
   founder; it is never an agent decision, whatever the justification.

## Why

Triggered by the founder-requested review of Weco AI's "first evidence of
recursive self-improvement" post (2026-07). Their credible core finding: an
agent improving its own scaffold beats hand-tuning — but only because the
evaluation was HELD OUT from the loop. The classic failure of
self-improvement loops is the agent making its own exam easier instead of
getting better. OneLive's Generator maintains its own harness (that is a
feature), so the exam — the gates — must be custodied outside the
Generator's sole authority.

## What was already true (don't re-learn this)

`adversarial-review.yml` runs on EVERY PR with **no path filter** — a
deliberate PR #11 (rounds 1–2) decision: the evaluator judged path filters
bypassable because trust rules live in docs/** as much as in code. So the
evaluator half of this amendment was already mechanically enforced; the
amendment states it as standing intent (so it doesn't depend on one
workflow file's comment surviving refactors) and adds the genuinely new
founder interrupt on relaxations.

## Boundary

"Relaxation" means the gate becomes easier to pass (threshold lowered, check
removed or made advisory, skip-path widened). Making a gate STRICTER, or
fixing a gate bug that produced false passes, is normal evaluator-reviewed
work — it does not interrupt the founder.

---

**Codified by:** `CLAUDE.md` prime directive 1 + founder-crucial list; `.github/workflows/adversarial-review.yml` (no path filter); `docs/EXTRACTION_EXCEPTION.md`.
