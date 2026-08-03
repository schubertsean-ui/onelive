# Decision: "notify me at merge" is a sequence/semantic reading — merges stay silent

**Date:** 2026-08-03
**Founder words (verbatim):** "Update it" · "It's a sequence / semantic reading"
**Context:** The charter v3 audit surfaced an apparent conflict between two
founder directives: "You do the merge and notify me" (2026-07-18,
`2026-07-18_agent-merges-on-green.md`) and "I don't want to know about merge"
(2026-07-25). Charter §0.4 flagged that CLAUDE.md prime directive 1 still
carried the 2026-07-18 "notifying the founder at merge" wording; amending
charter text is founder-only, so the mismatch was flagged, not edited.

**Ruling:** the two directives were never in conflict — the 2026-07-18 "notify
me" reads as sequence/semantics: the notification is the **recorded merge
evidence in the merge sequence** (evidence to disk — STATE/changelog/ledger and
the PR record), not a message to the founder. The 2026-07-25 directive governs
messaging: **no merge messages, ever**. CLAUDE.md PD1 updated in this commit to
state that reading, preserving the 2026-07-18 verbatim quote untouched.

**Also closes:** charter §0.4's open flag (updated in the same commit).
