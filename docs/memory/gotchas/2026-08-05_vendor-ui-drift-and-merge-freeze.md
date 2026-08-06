# Gotcha: vendor-UI click-paths and the exam-bound merge freeze (kickoff conduct rules, recorded)

**Date:** 2026-08-05 · **Source:** founder conduct rules in
`docs/ops/SESSION_KICKOFF_2026-08-05.md`, earned across the 2026-08-04 arc.

**Vendor-UI drift.** Never give the founder click-path instructions through a
third-party UI the agent cannot see — vendor UIs drift, and a wrong path
costs a founder round-trip. Order of preference: delegation token / API from
CI (the ops-diagnostics workflow is the standing vehicle), else ask for a
screenshot FIRST and direct from what is actually on screen. The 2026-08-05
delegations (CLERK_SECRET_KEY_ADMIN, VERCEL_TOKEN, HEALTHCHECKS_API_KEY)
exist precisely to keep vendor work API-side.

**Merge freeze during exam-bound PRs.** While any exam-bound PR (golden-exam
verifier red BY DESIGN) is open, FREEZE all other merges to master: the
freeze is one instance of the wider `green-on-stale-base` class — a merge
that changes which branch of a base-state-dependent gate applies invalidates
other PRs' greens. Resolve or close the exam-bound PR first (2026-08-05:
#154 was closed as superseded, dissolving the freeze).

**Retrieval tokens:** `vendor-ui-drift`, `merge-freeze-exam-bound`,
`screenshot-first`.
