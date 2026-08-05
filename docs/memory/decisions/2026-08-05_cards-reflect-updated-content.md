# Decision: cards must reflect the updated content — founder-directed (2026-08-05)

**Founder, verbatim (2026-08-05, in the session chat, alongside the request
for the next-session kickoff):**

> "I want the UI/UX to reflect all the updated content on the cards now."

**Context at the moment of the directive.** The first live stamp+promote pass
(autopromote run 30979536905) had just auto-published 136 discovered events as
confirmed, with the card columns (`title`, `category`, `subsegment`,
`ticket_url`) populated by `worker/promote.py` `card_fields()` — the writer
wired in the 0010-era work. The `/tonight` surface predates tonight's volume:
its card rendering has never been audited against the full set of populated
fields now flowing (title, category, subsegment, ticket link, 4-state
confidence, provenance/disputed display, artist links once PR #186's uuid[]
cast lands).

**What this directs (scoped into the 2026-08-06 kickoff, Workstream A):**
an audit-then-align pass — enumerate every field the promote path now writes,
audit what `/tonight` (feed + detail) actually renders, and close the gap so
the cards display the updated content, under the RATIFIED design canon
(`docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` +
`ONE_LIVE_TONIGHT_UI_CANON_v1.md`): verbatim copy strings, trust display
rules (no badges/"confirmed" text; quiet icon for low confidence;
disputed-shown-never-hidden), WCAG 2.2 AA, CWV budgets.

**What this does NOT change.** No trust invariant moves: display honesty
rules stay exactly as ratified; this is rendering catching up to data,
never data invented for rendering.
