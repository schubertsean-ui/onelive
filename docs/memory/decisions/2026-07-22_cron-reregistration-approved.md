# 2026-07-22 — Cron re-registration PR approved (founder)

**Decision (founder, verbatim):** "Approved" — 2026-07-22 ~04:35Z, in
response to the consolidated escalation ask offering: Option A ("reply
'approved' and I'll run the same two-minute change through the full
machinery — new branch, PR, mandatory evaluator review, merge at
APPROVE, fresh evidence run") or Option B (founder edits the file
directly in the GitHub UI). The founder chose A. This record is the
independently-checkable citation for the "founder-approved" note beside
the cron line in `.github/workflows/ingest.yml` (PR #46 r2 nit).

**Context:** GitHub's scheduler fired zero schedule-event runs across
9+ slots (01:07–04:47Z) on cron `7,27,47` despite an active workflow,
verified config, and the founder's disable/enable at ~04:07Z. The
minute shift `7,27,47 → 9,29,49` (cadence unchanged, every 20 minutes)
is the strongest remaining re-registration signal. Escalation ran under
the external-stall ladder (OPERATING_RULES §4, founder-directed the
same night).

**Written answer to the PR #46 r2 validate blocker** (charter: blockers
answered in writing): the r2 round holds that a validate run
self-labeled `INCOMPLETE-ACKNOWLEDGED` cannot serve as approval
evidence. The label is the *skip→Record binding mechanism* speaking —
the mechanism this same review channel demanded and approved in the
PR #35 arc, whose rule is: an UNRECORDED skip is RED even under
`--allow-skips`; a skip bound to an OPEN Record row with an objective
resolution trigger is the lawful, visible form of standing debt. The
sole skip here is R-002 (visual_regression), whose trigger is the first
deployed preview URL (Step 9): no deploy exists, so the gate cannot
fire on ANY tree today — requiring it green would create a gate that
cannot pass, blocking every PR until Step 9 while adding no
verification ("a test that cannot fail proves nothing" cuts both
ways). Every merged PR since the mechanism shipped — including #43 and
#44, APPROVEd by this same evaluator hours before this PR — carried
byte-identical validate evidence. The label's "not release evidence"
sentence is true and stays: PR-merge evidence ≠ release evidence, and
nobody cites it as the latter. A validate reporting refinement that
names "all diff-applicable gates green; skips = Record-bound
non-applicable (R-002)" is a good idea and is RECORDED as R-022
(docs/RECORD.md) with an objective trigger — the charter's lawful form
for deferred work — rather than riding a one-line cron change (the
scope-mixing this channel itself flagged on PR #45).

**Also acknowledged from r2/r3:** the review packet's raw-diff preamble
claims npm/SCA validation is visible in the web log even when the web
log reports not-applicable — a false packet claim, recorded in the same
R-022 row. Structural fact, not preference: `adversarial-review.yml` is
BASE-owned (`pull_request_target` — a PR's copy never judges itself),
so a fix inside this PR cannot change this PR's own packet; a separate
PR is the only path on which the fix can ever operate.
