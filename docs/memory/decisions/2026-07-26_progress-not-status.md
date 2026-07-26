# 2026-07-26 — Progress, not status; every action justified against go-live

**Directive (verbatim):** "I'm very very frustrated with all the feedback about
what you are doing. Diarrhea from you about status not progress. Codify to the
canon I only want progress toward completion, solutions offered as prescribed to
a problem, solutions executed by you 99% of the time ALWAYS ASKING AND
CONFIRMING IT GETS US CLOSER TO A WORLD CLASS GO LIVE."

**Context — what earned it.** Across this session the founder received a
running commentary: which seat was red, which round was running, which log was
being read, what had just been pushed. Almost none of it was actionable. The
work itself was real, but it was delivered as a stream of process narration
instead of finished outcomes, and the founder had to read all of it to find the
parts that mattered. Two adjacent frustrations the same hour name the same root
— a 55-minute self-check-in was scheduled when the standing rule is already
"never wait", and repeated asks for confirmation of things the agent should
simply have decided.

**The root is not verbosity for its own sake.** It is treating the founder as
the place where intermediate state gets reported, when disk is that place.
STATE.md, the Kaizen ledger, RECORD.md and the PR body exist precisely so
intermediate detail is *available on demand* rather than *pushed*.

**Decision — `docs/OPERATING_RULES.md` §1, "Progress, not status. Every action
justified against go-live."** Three binding parts:

1. **Report completion, not activity.** A message to the founder delivers a
   finished thing, a decision only they can make, or a blocker with its
   smallest unblock. Not "still working", not "the review is running", not a
   round-by-round diary. Intermediate detail goes to disk.

2. **Prescribe and execute, don't present.** On finding a problem: name the ONE
   recommended fix, with alternatives and the tradeoff in a sentence (charter
   communication rules 2 and 3), and then do it. The agent executes
   essentially all of it. The founder-crucial escalation list in `CLAUDE.md` is
   the exhaustive exception — money/new services, legal posture,
   trust-invariant changes, gate-threshold relaxations, go-live/allowlist
   pushes, credential minting — not a starting point for asking permission.

3. **The go-live test, per action.** Before starting a piece of work, state how
   it moves the live site closer to a world-class launch. Work that cannot
   answer is not neutral — it is a cost. Say so and drop it, or say why it is a
   genuine prerequisite. Gate and harness work qualifies when it is blocking a
   merge that ships product; polishing a control nobody is waiting on does not.

**Tension with the other standing rules, resolved explicitly** so this is not
read as license to hide problems. "Report completion, not activity" does NOT
weaken:
- *No silent deferrals* — a deferral still gets its RECORD row, in the same
  commit. It goes to disk, not into a status message.
- *Every claim independently verified* — brevity is never achieved by dropping
  the evidence. A short report with a command beats a long one without.
- *A repeated error is a finding* — investigation still happens; it just does
  not get narrated while in progress.
- *Escalations* — a real blocker is reported immediately. Silence is not the
  goal; noise is the problem.

**Reciprocal obligation this creates.** If the founder is not to be told what is
in flight, then in-flight work must be recoverable from disk without asking.
That is already the reconcile contract (`docs/SESSION_START.md`,
`tools/session_reconcile.py`) and it becomes load-bearing here.

**Contradictions found and resolved in the same change** (the founder's
follow-up: "Change any contradictory code or canon or rules"):
- `CLAUDE.md` prime directive 1 still read "notifying the founder at merge",
  which the 2026-07-25 silent-merge directive had already removed
  (`docs/memory/decisions/2026-07-25_silent-merge-directive.md`: "I don't want
  to know about merge - just get the job done at a world class level"). The
  charter now states the narrowing in place, so the two cannot be read as
  conflicting. The merge CONDITIONS are untouched — this was and remains a
  notification-posture change only.
- `CLAUDE.md` "Communicating with the founder" listed five rules, none of which
  said not to narrate. It now carries rule 6 pointing at this one, and states
  that it outranks the habit of narrating.
- The two directives are consistent and now say so explicitly: the founder is
  interrupted by DECISIONS, never by PROGRESS.

**Retrieval:** `docs/memory/RED_CLASSES.md` row `status-narration-not-progress`,
so the class is matched on future changes rather than remembered.
