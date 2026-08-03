# Decision — Adjudication stays with the evidence; fresh missions get fresh sessions

One-line: founder-ratified 2026-08-03 ("do this") — feedback adjudication,
claim verification, and follow-through belong to the session holding the
evidence; new missions (different surface/deliverable) start fresh with a
HANDOFF_STANDARD prompt; and any session evidence that future work will lean
on is COMMITTED to the repo first (disk-is-truth covers research/reasoning
artifacts, not just code). Codified: docs/OPERATING_RULES.md §6a.6.

**Context:** the 2026-08-03 sourcing-plan session produced five research
reports that existed only in-session; the founder asked whether red-team
review should happen there or fresh. Resolution: reports committed to
docs/strategy/research/ (making either choice safe), adjudication kept with
the authoring session, UI/UX split to a fresh session with its own prompt
(docs/ops/UI_UX_SESSION_KICKOFF_PROMPT.md). The engine-thread handoff
(docs/ops/NEXT_SESSION_KICKOFF_PROMPT.md) was rewritten so any session can
pick up from disk alone.
