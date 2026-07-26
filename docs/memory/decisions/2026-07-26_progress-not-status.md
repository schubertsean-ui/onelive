# Decision — progress not status, and the go-live test (founder-ratified 2026-07-26)

**Founder directive, verbatim:** "I'm very very frustrated with all the
feedback about what you are doing. Diarrhea from you about status not
progress. Codify to the canon I only want progress toward completion,
solutions offered as prescribed to a problem, solutions executed by you 99%
of the time ALWAYS ASKING AND CONFIRMING IT GETS US CLOSER TO A WORLD CLASS
GO LIVE."

## What it changes

`CLAUDE.md` communication rule 7, which outranks the completeness instinct
behind rules 1–5:

1. **The go-live test, applied before work starts.** Does this move the live
   product closer to a world-class go-live? No → it does not start.
2. **Report the delta, not the diary.** What is now true, what remains, what
   is needed. Review rounds and error post-mortems live in the ledger.
3. **Prescribe and execute.** Decided and done, then reported. Asking is the
   exception.
4. **Length is a defect.** Under thirty seconds on a phone.

## The failure that produced it

PR #73 ran fourteen review rounds. Rounds 7–14 were spent on
`tools/blocking_failure_check.py` — CI tooling — chasing a 45-second saving
that broke gate discovery and cost four self-inflicted gate-custody defects
before being reverted whole at r14.

Every one of those rounds was reported to the founder in detail. None of
them shipped anything a user will ever see. The detector arc would have
failed the go-live test at round 7, before any of it was written, had the
test existed.

The reporting compounded it: each round produced a long reply about lens
verdicts and class names, which is exactly the material the Kaizen ledger
and the decision records exist to hold. Narrating it to the founder is
duplication that costs their attention and returns nothing.

## What this does NOT relax

Rule 6 (proof or label) is unchanged — a number still ships with the command
that produced it. Brevity is satisfied by citing a command or a SHA, never
by dropping the proof. The trust invariants, the gates, and the
founder-crucial escalation list are all untouched: this rule governs what
work is chosen and how it is reported, never what is verified.
