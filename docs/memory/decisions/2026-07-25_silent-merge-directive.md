# 2026-07-25 — Silent merges: no founder notification at agent merge

**Directive (founder, verbatim, 2026-07-25, session `onelife-meta-carousel`):**
"I don't want to know about merge - just get the job done at a world class
level."

## The rule

When the agent merges its own PR under the charter's ratified protocol
(independent non-Claude evaluator APPROVE + every required check green on
the final head — CLAUDE.md prime directive 1, scope note of 2026-07-18),
it merges SILENTLY: no merge notification to the founder. This directive
narrows the 2026-07-18 "notifying the founder at merge" clause for this
founder's preference — the merge itself, its evidence chain, and its
records (changelog entry with the squash SHA, Kaizen M1 row, STATE
update) remain fully written to disk, so the founder can audit any merge
at any time without being interrupted by it.

## What does NOT change

- The merge conditions themselves (evaluator APPROVE + required checks
  green) are untouched — this is a notification-posture change only.
- Founder-crucial escalations (money, legal, trust-invariant changes,
  gate-threshold relaxations, go-live, credentials) still interrupt.
- The weekly founder digest still summarizes merged work.

First application: PR #65 (Meta carousel engine), merged 2026-07-25 as
squash 5481c159 at evaluator r15 APPROVE + trust-gate green on head
af6aeed, with no notification.
