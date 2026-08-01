# Gotcha — three recurring error classes to check BEFORE building (2026-07-25)

Retrieve this before starting a build or reporting it "done." These are real,
repeated failures from the 2026-07-25 live-site/brain arc, each caught by the
founder or the blind review after the fact — i.e. prevention would have been ~10×
cheaper (poka-yoke / 1-10-100). Applying OPERATING_RULES §1 ("a repeated error is
a finding, not a rhythm"). Full analysis:
docs/memory/decisions/2026-07-25_repeated-error-is-a-finding-applied.md.

1. **Do not report "built" as "live."** A capability with passing unit tests is
   NOT wired to production. Before saying a feature is live, name the live path
   and show its wiring test. (Missed 3×: multi-event fan-out advanced only 1-of-N;
   the category resolver collapsed to title-keywords in promote because the
   candidate never stored the venue/@type signals; auto-publish's flag did nothing
   because `autopromote.py` didn't exist.)

2. **Read prior work first — it is not greenfield.** The founder has usually
   already specified the thing (sources, trust-scoring, publish model). Read the
   persistent brain + docs/strategy before proposing a "new" approach. (Missed
   repeatedly across the arc — "was I working for nothing?")

3. **State the cost/budget as an acceptance criterion, up front.** Unbounded
   fan-out / all-Opus routing / no cost meter are cost fail-opens. A build spec
   must carry its budget + the bound is a test. (Missed: the multi-event fan-out
   defeated the per-run AI-call ceiling, R-043; ~15 subagents ran on Opus.)

**The prevention:** the poka-yoke'd direction template — every build states its
outcome, testable acceptance criteria (invariants as hard constraints), "what it
must NOT claim," a cost ceiling, and a blind/independent check — so these three
are designed out of the instruction, not caught after. A repeated instance of any
of the above is a §1 finding: root-cause + record, never routinize.
