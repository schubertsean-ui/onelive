# One Live — Conductor

Ratified: 2026-09-07. Status: in force.
How we **build, complete, and operate**. Not a ninth vision.
Coverage, Operating, Trust, Vision, Locale Launch, and the Building Standard still govern their subjects.

## World-class here
Narrow invariants. Wide execution.

Invariants live in **code and CI**, not in a growing "do not" list:
trust_gate, pytest, the independent evaluator, Coverage Law (do not invent, do not drop, do not bypass walls, no pay-to-rank).

The agent is hired to change the catalog or the live site. The machine's job is to make that path cheap: tools, a branch, tests that name the Must-do, one job, honest CI.

Adding another prohibition after a failed run is not engineering. Fix the **cause** (a blocking hook, a missing tool, a merge conflict, a red check) and rerun with that cause in context.

## A lesson is a failing check
A sentence in this file is not a control. A bot can ignore it. A lesson has landed when all three are true:

1. A check exists that would have gone **red on the original defect**.
2. That check sits on a **required** gate (`trust-gate` or the evaluator), not a skippable sidecar and not a path-filtered job that a docs PR skips.
3. A test fails if the check is removed or path-filtered.

| Defect | Required check that would have caught it |
|---|---|
| #260 unclosed `fetch()` — production could not compile | `npx tsc --noEmit` in `trust-gate.yml` (required). `next build` in `web-compile.yml` on every PR, no path filter. |
| Vercel red treated as “docs-PR fail” | `web/vercel.json` `ignoreCommand: exit 1`. Conductor: do not merge around Vercel red. |

Do not add a fourth paragraph instead of a check.

## Impediments are work
A conflict, gap, error, red check, empty PR, skip-storm, or master-red is **action**. It is not a wait, a new law, or a freeze of the board.

| Impediment | World-class response |
|---|---|
| Master CI red | P0. Name the failing test. Fix it on the smallest PR, or merge the open PR that already contains the fix. New tickets sit behind this. |
| Merge conflict | Rebase onto current master. Resolve. Push. Do not sit on DIRTY. |
| Trust-gate / pytest red | Read the assertion. Fix that file. Same PR. |
| Evaluator REQUEST-CHANGES | Fix the named trust defect only. |
| Visual red | If the product change is intended, recapture the baseline. If not, revert the accidental surface. |
| Vercel red | Open the inspect log. Fix the build. A red Vercel check is a failed deploy, including on a docs PR. Do not merge around it. Do not call it ignorable. |
| Web compile red | Master cannot ship. `.github/workflows/web-compile.yml` typechecks and `next build`s on every PR, no path filter. Fix the compile on the same PR. |
| Empty stub PR (0 files) | Not a PR. Fill it with the ticket files. |
| 80-turn death with files on the branch | Next job gets the red-check names and the error. Same PR. |
| 80-turn death with nothing | The PM writes the files. Do not burn a third identical cap on a blank. |
| Job skipped | Check the `@claude` association and concurrency group. Re-fire once if it never started. |
| Sandbox 403 | Fixtures + CI. Not a product failure. |
| Founder hold (#252 evaluator red, August drafts) | Hold. Do not work around. |

Do not invent a process document instead of opening the error.

## The machine
`.github/workflows/claude.yml`

- `@claude` from OWNER / MEMBER / COLLABORATOR starts a job with git, gh, pytest, python, and 80 turns as a **ceiling**, not a target.
- One job per issue/PR. A new `@claude` on the same ticket cancels the in-flight run. That is CI concurrency, not a leash.
- Plan-first / session-reconcile / construction-loop hooks do not block a product commit. They were burning the budget before any file landed. Trust gates still run on the PR.
- Success: product files + tests on a PR that CI and the evaluator can judge.

## Build
1. Ticket names files or behaviors (Must-do / Must-not).
2. Job writes them, with tests that lock the Must-do.
3. Push onto the existing PR if there is one; otherwise open one.
4. Print In scope / Refused. Extra files get reverted.

## Complete
- Required checks green **and** independent evaluator APPROVE → squash-merge.
- Claude does not merge unless the founder pastes "merge".
- A PR that is green except for a known master-red is not complete until that red is named and owned.
- Draft PRs with product files stay drafts until the founder or Atlas marks ready on green+APPROVE.

Ticket-order notes (current board, not law): #252 stays unmerged while the evaluator is red. August drafts stay parked. Census (#251) follows place / gather / pack doors.

## Operate
- Armed cron stays the ingest heartbeat. Do not edit `ingest.yml` without an authorized smoke/evidence path.
- Fail closed: unconfirmed fetch does not mutate a published row.
- Views filter; they never delete catalog rows.
- A rule that lives only in a chat is not a rule. Change this file (or the law it points at), then push.

## What this file is not
Not a turn ration. Not "push whatever at turn 40." Not a ban on continuing a half-done PR. Not a freeze of the board for one red check.

A rule that lives only in a chat is not a rule. Change this file, then push.
