# One Live — Conductor

Ratified: 2026-09-07. Status: in force.
How jobs run. Not a ninth vision. Coverage, Operating, Trust, and Vision still govern product.

## World-class here
Narrow invariants. Wide execution.

Invariants live in **code and CI**, not in a growing "do not" list:
trust_gate, pytest, the independent evaluator, Coverage Law (do not invent, do not drop, do not bypass walls, no pay-to-rank).

The agent is hired to change the catalog or the live site. The machine's job is to make that path cheap: tools, a branch, tests that name the Must-do, one job, honest CI.

Adding another prohibition after a failed run is not engineering. Fix the **cause** (a blocking hook, a missing tool, a merge conflict, a red check) and rerun with that cause in context.

## The machine
`.github/workflows/claude.yml`

- `@claude` from OWNER / MEMBER / COLLABORATOR starts a job with git, gh, pytest, python, and 80 turns as a **ceiling**, not a target.
- One job per issue/PR. A new `@claude` on the same ticket cancels the in-flight run. That is CI concurrency, not a leash.
- Plan-first / session-reconcile / construction-loop hooks do not block a product commit. They were burning the budget before any file landed. Trust gates still run on the PR.
- Success: product files + tests on a PR that CI and the evaluator can judge.

## Happy path
1. Ticket names files or behaviors.
2. Job writes them, with tests that lock the Must-do.
3. Push onto the existing PR if there is one; otherwise open one.
4. CI and the evaluator run. Green + APPROVE → squash-merge (vision and conductor PRs). Claude does not merge unless the founder pastes "merge".

## When it fails
Retry **with the failure**, not a blank "continue":
- Paste the red check names, the error, the file. Same PR.
- Do not stack a second job while one is running.
- An empty stub (0 product files) is not a PR. Fill it.
- If the failure is the **system** (hooks, missing tools, merge conflict with master), fix the system first, then rerun.
- If the remaining work is known and small and the agent has already shown the shape, the PM lands it. That is finish-the-diff, not a cap on thinking.

Ticket-order notes (current board, not law): #252 stays unmerged while the evaluator is red. August drafts stay parked. Census (#251) follows place / gather / pack doors.

## What this file is not
Not a turn ration. Not "push whatever at turn 40." Not a ban on continuing a half-done PR. Not a freeze of the board for one red check.

A rule that lives only in a chat is not a rule. Change this file, then push.
