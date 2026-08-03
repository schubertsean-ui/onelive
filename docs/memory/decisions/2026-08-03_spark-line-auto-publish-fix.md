# Decision — Spark Lines auto-publish on validation, not per-item human approval

One-line: founder-directed fix — #148 wrongly required a human to approve EVERY Spark Line (the exact per-item-approval model the founder killed for events on 2026-07-25). Fixed by mirroring the ratified events auto-publish: a Foundry-VALIDATED line auto-approves behind one fail-closed flag (`AUTO_PUBLISH_SPARK`, default OFF); the founder controls the switch, never each line.

**Date:** 2026-08-03. **Authority:** founder-directed. The founder caught the catch-22 verbatim: *"This seems like a catch-22 so worthless. I do not want to be in the middle of things approving all day … the point is to share this content with users … Fix this."*

## The defect

#148's Spark Line take-live (`worker/descriptor/publish.py::approve_candidate`) required a HUMAN approver per line (`_require_human_approver` refuses AI identities), one at a time. That is the model the founder already rejected for events (2026-07-25, `2026-07-25_auto-publish-earned-confidence-ratification.md`): *"Good lord I can't approve every one of thousands of events!"* A feature meant to enrich the feed for users, gated behind thousands of manual clicks, publishes nothing in practice — worthless.

## The fix (mirrors the ratified events model)

"AI never publishes UNVALIDATED" is satisfied by the VALIDATION GATE, not a human click (2026-07-31 canon). A Spark Line's validation is the Descriptor Foundry: the mechanical faithfulness gate (every proper noun/number grounded in the artist's OWN materials) + an INDEPENDENT judge (a different model than the generator). So:
- `worker/descriptor/publish_policy.py` (pure, unit-tested) — `decide_spark_publish(judge_score, …)`: fail-closed to human review unless the `AUTO_PUBLISH_SPARK` flag is ON; human review for a below-bar or missing judge score; otherwise **auto_approve**.
- `worker/descriptor/store.insert_with_policy(result, …)` — writes `approved` directly for an auto-approved line, else `candidate`. The judge score is read from the FRESH FoundryResult (never a re-read of a mutable row), so custody holds: the INDEPENDENT judge + the founder flag drive the promotion, not the generator.
- The manual `approve_candidate`/`reject_candidate` path remains for spot-checks/overrides.

## Custody / trust (unchanged invariants)

- **Not "AI approves itself":** promotion is driven by the independent judge's score + the founder flag, exactly as events auto-publish uses the base-owned gate decision + `AUTO_PUBLISH_RATIFIED`.
- **Fail-closed:** `AUTO_PUBLISH_SPARK` defaults OFF; with it off, every line lands as `candidate` and nothing reaches a user. No behavior change until the founder flips it.
- **Still gated on held decisions:** the flag flips ON only when the founder rules on the free-lane grounding source (MusicBrainz+Wikidata) + tier-C generation spend. Building the mechanism consumes neither.

## The transferable rule

The trust invariant is "AI never publishes UNVALIDATED" — the validation GATE is what satisfies it, so validated content auto-publishes at earned confidence behind a founder SWITCH. A design that puts a human in the per-item loop is the anti-pattern; the founder controls policy + the switch, never each item.
