# 2026-08-01 — Founder ratifies truth-states v2, invariants/hypotheses split, and the cross-artifact consistency test

**Founder, verbatim (2026-08-01, second directive on the external review):**
"Confirm you're addressing 1-8 and also / Asopt Truth-state additions
(OWNER-CONFIRMED, STALE) / Adopt invariants-vs-testable-hypotheses split is
excellent / adopt their meta-recommendation (an automated cross-artifact
consistency test)" *(sic — "Asopt" read as "Adopt")*

Context: the external review of the Model deliverable
(`Review_of_AI_Agent_and_Marketing_1live_doc.txt`, assessed 2026-08-01;
items 1–4 of the agent's action list already executed at "Go with 1–4").
"1–8" refers to the eight **Real catches** in the agent's assessment
scorecard. This record ratifies the three items that were explicitly held
as founder-crucial or canon-touching in that assessment.

## Decisions

1. **Truth-states v2 (ADOPTED).** The confidence model gains two states:
   `OWNER-CONFIRMED` (explicitly asserted by a verified owner/authorized
   operator — separate from independent corroboration) and `STALE`
   (previously supported but outside the applicable freshness window).
   The model is now six states:
   `confirmed | owner-confirmed | likely | unverified | disputed | stale`.
   Drift and similar observations become **issue flags**, not states.
   Spec: `docs/strategy/ONE_LIVE_TRUTH_STATES_v2.md`. The prior "4-state,
   confirmed decision" (2026-07-15) is superseded BY FOUNDER RATIFICATION —
   this is the additive change that decision reserved to the founder.
   **Unchanged, explicitly:** disputed shown-never-hidden (charter
   invariant); AI never publishes; confidence derived from corroboration,
   never asserted (owner assertion is its own labeled state, not a
   corroboration shortcut).

2. **Invariants vs. testable hypotheses split (ADOPTED).** Engagement/
   content rules divide into hard invariants (truth, rights, consent,
   accessibility) and testable defaults (video-first, send windows,
   carousel structure, etc.). Registry:
   `docs/strategy/ONE_LIVE_ENGAGEMENT_HYPOTHESES_v1.md`. The design brief
   v2.4 remains ratified canon; this ratification is the instruction to
   treat its engagement *effectiveness* claims as defaults-to-test, while
   its trust-display rules stay invariant.

3. **Automated cross-artifact consistency test (ADOPTED).**
   `docs/strategy/marketing_model/check_artifacts.py` (built during
   items 1–4) is formalized as a standing gate:
   `tests/test_artifact_consistency.py` runs it inside the normal pytest
   sweep, so `tools/validate` fails when any deliverable source
   contradicts canonical event facts, retired claims, or (now) the
   six-state model.

## Implementation boundary (this session is docs-armed)

Canon, personas, ledger, and tests land now (docs/ + tests/). The
**pipeline implementation** of the two new states (DB enum, gate logic in
`worker/confidence.py`/`worker/gating.py`, `tests/test_gates.py`
transitions, public API display) and the CLAUDE.md charter-text update are
code-arm work — recorded as R-026 in `docs/RECORD.md` with an objective
trigger. Until that lands, the running pipeline remains 4-state and honest
about it; no doc claims the new states are live.
