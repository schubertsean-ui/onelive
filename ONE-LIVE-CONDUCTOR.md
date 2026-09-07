# One Live — Conductor (dispatch, retries, non-firings)

Ratified: 2026-09-07. Status: in force.
This file is how Atlas/Hermes (the PM) and `@claude` jobs are allowed to run.
It does not change Coverage Law, Operating Law, Trust, or Vision.
If this file fights Operating Law on *how a session works*, Operating Law wins.
If this file fights Coverage Law on *scope*, Coverage Law wins.

## Outcome
Minimum wait. Minimum wasted turns. Maximum product files on GitHub.
A rule that lives only in a chat is not a rule. Codify here, then push.

## One job per ticket
`.github/workflows/claude.yml` is the trigger. `@claude` from OWNER / MEMBER / COLLABORATOR only.

- One in-flight Claude job per issue or PR. A new `@claude` on the same ticket **cancels** the in-flight run. It does not stack a second 80-turn cap.
- Never comment `@claude` on both the issue and the PR for the same ticket.
- Never `@claude` to "continue" or "keep going." Named red checks, named files, then stop.
- Comments without `@claude` may skip. Skips are cheap. Stacked runs are not.

## What counts as "already has a PR"
- Draft or open PR **with product files** = has a PR. Do not open a second one. Push onto it.
- **Empty stub** (0 files, "open a draft first") = **no PR**. Retry is allowed. Fill it or close it.
- A PR whose only commit is ceremony (STATE, Hats, Kaizen, session-arc) = no product PR.

## Retry
- Do not retry a ticket whose Claude job is **running**.
- Job dead, no product PR → `@claude` **once** on the ticket. Push a draft. Stop.
- Job dead, product PR, checks red → `@claude` **once** on **that PR**: name the red checks. No new ticket. No second PR.
- **Two** 80-turn deaths on the same ticket with no green → the PM lands the files. **No third cap.**
- Do not retry #251 (census) until #253 / #254 / #255 have draft PRs with product files, or are running.

## Merge
- Vision PRs (#253 place, #254 gather, #255 pack doors): squash-merge only when required checks are green **and** the independent evaluator verdict is APPROVE.
- Conductor PRs (claude.yml, ceremony off, this file): squash-merge when green + evaluator APPROVE.
- #252 stays unmerged while the evaluator is red.
- August drafts stay parked.
- Claude never merges unless the founder pastes "merge".

## Blocks
A block is only real if nothing is moving on that ticket and nobody is allowed to push it.
- In-flight Claude or in-flight CI is **running**, not blocked.
- Dead job + red PR is **action**, not a wait.
- Founder holds (#252 evaluator red, August drafts) are holds. Do not work around them.
- Do not freeze the board for one red check.

## Ceremony
Off. Do not run `session_reconcile.py`. Do not write a Session Contract.
Do not read `docs/SESSION_START.md`. Do not run hats, Kaizen, construction loop, or `[S3:]` citations.
Open the Must-do files. Write them. Push. Stop.
If you hit turn 40 with no product file committed, push whatever you have and stop.

Trust gates stay: trust_gate, lint, pytest, independent evaluator.
