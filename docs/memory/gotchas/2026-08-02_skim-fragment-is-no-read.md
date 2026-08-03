# Gotcha — a skim or a fragment is NO read; and cite the canon, don't paraphrase invariants from memory

One-line: two linked failures from the prior session — (a) reading fragments then acting on the partial picture, and (b) mis-stating an invariant from memory. Read in full first; QUOTE the canon for any invariant.

Retrieve this before acting on any doc you have only partially read, and before
you state a trust invariant in your own words.

## What happened

- **Fragment-acting.** Enough of a doc was read to form a plan, and the plan was
  acted on — but the binding detail lived in the unread remainder. In this repo,
  where STATE.md is ~800 lines and RECORD.md carries 50+ open deferrals, the
  unread part routinely contains the constraint that changes the plan.
- **Invariant-from-memory.** A trust invariant was paraphrased and got it subtly
  wrong. The charter's rule is **"AI never publishes UNVALIDATED"** — satisfied by
  the gate (extraction → candidate → gate → promote), NOT "AI output is safe by
  construction" and NOT "AI never publishes anything." The gate IS the validation;
  building the gate is how the invariant is honored, not by refusing to build.

## Why each is a real defect, not a style nit

- A paraphrased invariant drifts. "AI never publishes" (dropping "unvalidated")
  would forbid the earned-confidence auto-publish the founder ratified
  (2026-07-31: "the gate means validation, not a human click"). The exact words
  encode exactly what is and isn't allowed; approximating them changes the policy.
- A fragment read produces confident wrong action, which is worse than a known gap.

## The rule

1. If you have not read the whole doc, you have not read it — say "partially read"
   and finish before acting.
2. For ANY invariant (AI-never-publishes-unvalidated, disputed-shown-never-hidden,
   RLS-fail-closed, no-pay-to-rank), QUOTE the canon (`CLAUDE.md` / `OPERATING_RULES.md`)
   at the point of use. Do not reconstruct it from memory. If you can't cite it,
   go read it.
