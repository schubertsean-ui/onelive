# Session arc — 2026-07-23 — C2 convergence decision layer, merged (PR #54)

Chronological record of how the C2 decision layer reached master. STATE.md holds
the always-current rollup; this arc explains how it got there.

## Contract
GOAL: land C2 of the convergence spec (§5/§11) — Monte-Carlo scenario scoring,
expected-loss decision over an explicit cost matrix, and Value-of-Information —
**shadow-only** on the merged C1 SL substrate, and drive it through the mandatory
non-Claude adversarial review to APPROVE + all-green, then merge under the
agent-merges-on-green protocol and notify the founder.
SCOPE: `worker/convergence/scenarios.py`, `worker/convergence/decisions.py`,
`docs/strategy/ONE_LIVE_COST_MATRIX_DRAFT_v1.md` (DRAFT), tests.
NON-GOALS: no gate/promote/auth/threshold change; no ratified cost numbers in code
(the numbers are the founder's ratification — spec §11 decision 1).

## Outcome
MERGED as master **97fd957** under the agent-merges-on-green protocol:
- Independent evaluator (gpt-5.5) **VERDICT: APPROVE**, no blocking issues, on
  final head **91c26a5** — run 29989331325, plus the ready-for-review re-run
  29989815033 (also APPROVE).
- Trust Gate green on the same head (29989331277); golden-exam co-gate green (no
  harness file in the diff → **no exception consumed**); mergeable_state clean.
- Step-5 arming bound to **verification #18** (workflow_dispatch run 29988969830
  @ 5a88214, artifact 8556245805); docs-only repoint to the final head per the
  non-runtime binding set.
- Founder notified at merge with the cost-matrix ratification ask (the gate to
  moving C2 from shadow to live).

## How it went — 18 evaluator rounds
The review converged over **18 rounds** (17 REQUEST-CHANGES + r18 APPROVE), each a
genuine correctness defect on ONE path: how a decision/scenario audit record
**self-verifies** so it cannot be constructed to contradict what `decide()` / the
sampler would actually produce. The progression, broad → sharp:
- Constructor fail-loudness across World / WorldOutcome / ScenarioSummary /
  DecisionRecord / VoiRecord (reject internally-impossible / forged values).
- VoiRecord requires all embedded decisions carry the **same cost matrix**,
  including matrix action order (r14) and each decision's own tie-break order —
  the key order of `expected_losses` (r15).
- r16: `chosen` must be the **deterministic** tie-break winner, not merely some
  tied minimum.
- r17 (the sharpest): the r16 tie-break was exact but read the stored totals,
  which are only validated within `_SUM_EPS`. A forger could store a near-tie as
  an exact tie and flip the recorded winner. **Fix:** recompute the choice from
  **ground truth** — `mode_probs × matrix`, exactly as `decide()` — with an exact
  stored-total anchor, so no tolerated middleman remains in the decision.

Each runtime round killed the Step-5 arming binding (runtime files changed vs the
recorded green smoke run); the cycle each time was fix → validate/lint/deferral →
commit runtime → dispatch ingest.yml → collect the green run digest → docs-only
evidence repoint → evaluator round on the bound head. Verifications #16→#18.

## Self-corrections worth remembering
- r8: evidence prose overclaimed "every audit constructor fails loud" while
  WorldOutcome didn't — caught as overstated-provenance; adopted WorldOutcome
  validation AND corrected the prose to a precise enumeration.
- r9: the r8 fix used `tuple(wrong_fields)` which silently split a bare string
  into characters — fixed by rejecting str/bytes before normalizing.
- r12: I had deferred a matrix-identity fix (R-025) believing it disproportionate;
  the evaluator cited the no-deferred-work bar; I judged the fix bounded, closed it
  in code, and withdrew the deferral — transparent that the deferral was wrong.

## Lesson (Kaizen M2)
Forgery-resistance of audit evidence converges **slowly** under an adversarial
reviewer, and a large single diff compounds per-round cost. Counter-measure for
next time: land audit-record self-verification as its own small PR with the
"recompute from ground truth, no tolerated middleman in the decision" invariant
stated up front, so the class is designed in rather than discovered round by
round. The 18-round count was flagged to the founder as extraordinary.

## Next
Founder ratifies the DRAFT cost matrix → flip C2 from shadow to a live gate action
(founder-crucial; not agent-authorized). Two accepted non-blocking nits queued in
TODOS as a small follow-up PR (do not reopen #54).
