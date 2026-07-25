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

## What does NOT change (precise scope — #67 r1 tightened this wording)

- The merge conditions themselves (evaluator APPROVE + required checks
  green) are untouched — this is a notification-posture change only.
- Founder-crucial escalations still interrupt, and they interrupt
  BEFORE the work exists, as decisions the founder must make — money,
  legal posture, trust-invariant CHANGES (any relaxation or alteration
  of the invariants themselves), gate-threshold relaxations, go-live,
  credential minting. A PR in any of those categories is not
  agent-mergeable AT ALL under the charter, so the silent-vs-notified
  question never arises for it: the founder is in the loop by making the
  decision, not by receiving a merge notice.
- Therefore the precedent this record sets is exactly: a PR the charter
  already permits the agent to merge (evaluator APPROVE + required
  checks green, no founder-crucial content) merges without a
  notification. It is NOT a precedent for merging trust-invariant
  changes silently — those remain unmergeable by the agent regardless
  of notification posture.
- The weekly founder digest still summarizes merged work.

First application: PR #65 (Meta carousel engine), merged 2026-07-25 as
squash 5481c159 at evaluator r15 APPROVE + trust-gate green on head
af6aeed, with no notification. Why #65 qualified: it BUILT new
enforcement (publish custody, autonomy authentication, cadence ceilings)
on a founder-contracted surface (Contract #23 and its ratified follow-up
directives) and relaxed no invariant — "AI never publishes" is STRONGER
after it, and the autonomy ladder it ships is exactly the founder's
requested sign-off process, inert until the founder signs a record. Its
custody code was trust-path, so it carried the mandatory non-Claude
adversarial review on every round — which is the charter's compensating
control for trust-path code, distinct from the founder-crucial category
above.
