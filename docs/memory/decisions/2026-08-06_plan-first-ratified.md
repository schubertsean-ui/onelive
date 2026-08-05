# 2026-08-06 — Plan-first is the standing mode (founder ruling)

## Founder directive (verbatim)

> Plan first - I don't trust your building - plus it's the operational charter.

Issued in answer to the agent's pending question, which had surfaced a tension
between OPERATING_RULES §4a (plan-first) and the founder's repeated pressure
for speed, and asked which mode to run in.

## The ruling, as it binds

**Plan first. No substantive build starts before a plan is presented and
approved.** This is not a per-session preference the agent may re-weigh
against urgency; it is the operational charter, and the founder has now
restated it directly. The agent does not get to decide that a change is
"small enough" to skip it.

Two reasons were given and both stand on their own:

1. **Trust in the building is not established.** Named plainly by the founder.
   The record supports it: this session's PR #189 took six adversarial review
   rounds, and rounds 3, 4 and 6 found the same class of defect — a partial
   identity signal treated as a total one — three separate times. Building
   first and discovering the rule afterwards is precisely what produced that.
2. **It is already the charter.** OPERATING_RULES §4a, enforced mechanically
   by the PreToolUse construction gate, which blocks product-file edits until
   an OPEN contract carries WHAT / HOW / WHY / WHY-THAT-MATTERS / EXPECTED
   OUTCOMES.

## What this changes in practice

- A plan is written and presented BEFORE product files change — including for
  work that looks like a bug fix, when the fix changes a RULE rather than
  correcting a typo. The r6 recurring-events fix, for example, changed what
  counts as the same event; that is a rule change and needed a plan.
- Answering an evaluator finding does NOT bypass this. "The reviewer told me
  to" is not an approval.
- The exceptions remain what the charter already allows: mechanical
  corrections that alter no rule (a signature mismatch, a typo, a test fixture),
  and re-binding evidence files.

## What it does not change

The founder's speed pressure is real and stands alongside this, not against
it: "When will this ever end and I get my site live and full of thousands of
events?" The answer to that pressure is a shorter path, not a skipped plan —
see docs/ops/PATH_TO_THOUSANDS_OF_EVENTS.md, which exists because of it.
