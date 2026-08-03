The charter's publication invariant is restated at founder direction: "gate-custodied publication" (custody, never absence) replaces the stale shorthand "AI never publishes" — MECHANICS UNCHANGED.

# 2026-08-03 — Invariant wording: gate-custodied publication replaces "AI never publishes"

**Status:** RATIFIED (founder-directed). **Decider:** founder.
**Trigger (verbatim):** *"If this is still in the charter relive it and replace
it with the more recent and more nuanced statement. 'The charter's invariant is
"AI never publishes"' Relive = remove"* — after the founder had already
corrected the same over-broad reading in-conversation ("This is demonstrably
wrong about 1Live's position: 'AI never publishes / AI on product surfaces'").

## The change (wording only — NO mechanic moves)

CLAUDE.md's bare shorthand "AI never publishes" (prime directive 1, the
architecture pipeline note, and the Claude-API stack line) is replaced with
the more recent, more nuanced ratified formulation:

**Gate-custodied publication: AI output reaches users ONLY through the
validation gates** — extraction → candidate → gate → promote for events, the
Foundry faithfulness gate for descriptors — with promotion either
human-custodied or earned-confidence AUTO-published behind founder-flipped,
fail-closed flags. AI is structurally everywhere in the product (extraction
IS AI; the Descriptor Foundry produces user-facing copy, gated). The
invariant is CUSTODY, never absence.

## Why the shorthand had gone stale (the ratification trail)

1. **2026-07-25** — earned-confidence auto-publish RATIFIED (design; switch
   flip = founder trigger after safeguards): per-item human approval
   rejected for events ("I can't approve every one of thousands").
2. **2026-08-02** — interaction-correction record: *"'AI never publishes' is
   honored BY the eval-harness/gate on Foundry output (blank on
   sub-threshold), NOT by refusing to build."*
3. **2026-08-03** — Spark Line auto-publish fix (PR #150): Foundry-VALIDATED
   lines auto-approve behind `AUTO_PUBLISH_SPARK` (default OFF, founder
   flips) — the per-item-approval catch-22 killed for descriptors too.
4. **2026-08-03 (this session)** — the agent misapplied the bare shorthand as
   "no AI on product surfaces" in an evaluation; the founder corrected it and
   then directed the charter wording replaced.

## What did NOT change (stated so no reader ever doubts it)

- The orchestrator still cannot import the promote path.
- Every fail-closed flag stays fail-closed and founder-flipped
  (`AUTO_PUBLISH_SPARK` OFF; earned-confidence switch dormant).
- No pay-to-rank, disputed shown-never-hidden, RLS fail-closed — untouched.
- The golden-exam certification machinery, the compensated-exception
  classes, and the merge-on-green protocol — untouched (the prime directive's
  scope note now says "the publication invariant" where it said the old
  shorthand; same referent).
- Gate thresholds: nothing relaxes. This is a WORDING modernization; any
  reviewer reading it as a mechanic change should fail it.

Historical records (changelog, arcs, old decision records, STATE history)
keep the original phrase — they are append-only records of what was said when.
