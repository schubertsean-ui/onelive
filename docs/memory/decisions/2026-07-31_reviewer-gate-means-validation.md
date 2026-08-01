# Decision — the reviewer's "gate" means validation, not a human click

**Date:** 2026-07-31 · **Authority:** founder-directed ("Update the reviewer
rulebook asap") · **Scope:** gate custody (`tools/adversarial_review.py`).

## Why

The adversarial reviewer's discipline (V2, rule 1) blocks a change that
"publishes AI output without the gate." "The gate" had no explicit definition, so
a strict reviewer could read it as "a human must approve" and reflexively BLOCK
the **founder-ratified earned-confidence auto-publish** (2026-07-25) — the exact
feature the founder directed be built. This clarifies the rulebook BEFORE the
auto-publish promoter PR arrives, so the reviewer judges it on whether it truly
validates, not on the absence of a human click.

## What changed

Added V2_DISCIPLINE rule 5: **"THE GATE" MEANS VALIDATION, NOT A HUMAN CLICK.**
- "Without the gate" = output reaching a user WITHOUT passing the
  trust-gate/earned-confidence validation: fabricated/schema-invalid extractions,
  output that bypasses gate3 / the confidence model / source-reliability, or a
  disputed event shown as anything but disputed.
- It is NOT a violation for AI output to publish THROUGH that validation without a
  human click — triangulated against independent sources, published at its earned
  4-state confidence, fail-closed behind a single OFF-by-default flag, promote
  path still guarded by trust_gate's import allowlist.
- The reviewer must STILL block a change that publishes fabricated/unvalidated
  data, skips the confidence/reliability/gate checks, hides or downgrades a
  disputed event, is not actually fail-closed, or removes the promote-allowlist.

## Why this is a CLARIFICATION, not a relaxation

No trust protection is removed. `disputed` shown-never-hidden, no-fabrication,
fail-closed default, and the structural promote-import allowlist (enforced by
`tools/trust_gate.py`, untouched) all remain hard blockers. The change only names
what "the gate" already was — the validation path — so the reviewer stops
conflating "no human clicked" with "no gate ran." Pinned by
`tests/test_adversarial_review.py::test_v2_discipline_defines_the_gate_as_validation_not_a_human_click`.

## Note

This edits gate-custody code, so it runs through the mandatory adversarial review
on its own PR (every PR, no path filter). Landing this does NOT itself enable
auto-publish — the promoter is a later, separate, flag-OFF, reviewed change.
