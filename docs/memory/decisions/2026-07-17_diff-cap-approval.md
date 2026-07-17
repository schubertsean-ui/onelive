# Adversarial-review diff cap: 300000 → 800000 bytes is founder-approved.

**Ratified:** 2026-07-17, founder: "I approve the 800 KB adversarial-review diff cap."

## The decision

The `adversarial-review.yml` `--max-diff-bytes` cap was raised from the 300000
default to 800000 (in PR #18 rounds r6–r7) so that research PRs can commit their
full evidentiary substrate — verbatim agent-report appendices and verification
vote records — and still have the **whole** diff reviewed rather than truncated.

That raise is a **gate-threshold relaxation**, which the 2026-07-14 gate-custody
amendment makes **founder-crucial** (never an agent decision). It predated the
amendment and carried no recorded founder approval, so evaluator round 23 on
PR #18 escalated it rather than self-resolving. This record closes that escalation.

## Why this, not the alternatives

- **Lower the cap / exclude evidence from the review diff** — rejected earlier by
  the evaluator (r6–r7): excluding cited evidence hides the very material
  adversarial review exists to check ("shown, never hidden" applies to our own
  evidence too). Machine-fetched *third-party* corpus is separately excluded and
  hash-verified; that is distinct from our authored evidence, which stays in-diff.
- **Keep it unapproved** — not allowed under gate custody.

## Scope and guardrails

- This approves the **800000-byte** value only. It remains **fail-closed**: a diff
  exceeding the cap HARD-FAILS rather than being reviewed truncated (`--require`
  unchanged). It is a wider window, not a softer gate.
- Any *further* increase is a new founder-crucial decision.
- Cited at the cap in `.github/workflows/adversarial-review.yml`.
