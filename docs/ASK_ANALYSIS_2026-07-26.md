# ASK ANALYSIS — asks 5 and 3, recurrence and consequences

**Status: REFERENCE.** Written 2026-07-26 on founder request: *"Tell me the
recurrence history of these and any tradeoffs or potential implications of saying
'yes' to each."* Then: *"Record the analysis and decisions."*

Both asks are **founder-crucial** — ask 5 is a gate-threshold change, ask 3 touches
a trust invariant — so neither is decided here. This document is the evidence and a
recommendation, nothing more. Every claim below is a file, a log line or a code
path read in this session; where something could not be verified it says so.

**One correction is carried in this document, and it changes an answer I already
gave you.** See ask 3, "rollback".

---

## Ask 5 — what an escaped defect should do to the gate  *(RESOLVED)*

**RESOLVED 2026-07-26 by the founder: "option a".** An escape stops blocking once its
`Gate-gap closed` column names a shipped mechanism. The M3 target is untouched — **0,
absolute** — the all-time count still prints and can never decrease, and an escape with
no named mechanism blocks forever.

**The full option analysis this section carried has been pruned** (WORLD_CLASS §0.8 —
prune, don't only add; and PR #76 r5, where the agent's accumulated prose pushed the diff
past the reviewer cap so the mandatory review could not execute). Nothing is lost: the
binding artefacts are

- the decision record — `docs/memory/decisions/2026-07-26_escape-alarm-semantics.md`,
- the mechanism — `tools/kaizen_trends.py` plus its 8 tests, and
- the deferral row — `docs/RECORD.md` R-064, which states all three options and why (b)
  was argued against on evidence.

The original argument remains in git history. A resolved analysis is history; the decision
record is canon.

## Ask 3 — does the auto-publish ratification still stand

### Recurrence history — and this one is not flattering to the system

**The founder has given this instruction three times.**

1. **Before 2026-07-25.** Quoted verbatim inside the ratification record itself:
   *"I told you to prep to enable AI to post without human approval except for
   exceptions or sources we have graded as often unreliable."* The instruction
   already existed and was already not executed.
2. **2026-07-25 — explicit ratification**, with the frustration on the record:
   *"Even a passing candidate waits for a human click. Good lord I can't approve
   every one of thousands of events!"* Decision record:
   `docs/memory/decisions/2026-07-25_auto-publish-earned-confidence-ratification.md`.
3. **2026-07-26 — asked again**, because the 2026-07-26 audit found `CLAUDE.md`
   still asserted the opposite ("never to auto-publish"), so canon contradicted the
   ratified decision and the decision could not be safely assumed to stand.

**The honest reading: this is not the founder repeating himself. It is the system
failing to execute a decision three times.** As of this session the state is
unchanged from the audit: `worker/publish_policy.py` is imported by nothing but its
own test, `worker/autopromote.py` does not exist, and safeguard 1 is not live. That
is R-056, and the recurrence itself is a Kaizen finding independent of the answer.

### What saying "stands" actually unblocks — and what it does not

It unblocks **building** Step 2. It does **not** flip the switch. The flag
`AUTO_PUBLISH_RATIFIED` is default OFF, fail-closed, reversible in one line, and
`decide_publish` returns `human_review` for everything until it is ON. The
ratification record requires three safeguards live before the flip; **safeguard 1
is not met** — `worker/source_reliability.py` exists but the outcome-driven update
loop does not run, so "graded unreliable → human review" is currently a no-op
default rather than a real gate. That gap is the largest engineering item left in
v1, and it comes first in the build order.

### Rollback — correcting what I told you earlier

**I previously told you no rollback path exists. That was wrong, and the correct
answer is materially better for you.** `worker/promote.py` carries:

- `set_event_confidence(event_id, confidence, actor_type)` — moves a live canonical
  event to **any** of the four confidence states, validated, and writes an
  `audit_log` row.
- `mark_event_disputed(event_id, actor_type)` — the same, pinned to `disputed`.

So a wrongly auto-published event can be **demoted or marked disputed immediately,
with an audit trail**. What does not exist is *un-publish / delete* — and that is
deliberate, not a gap: "disputed is always shown as disputed, never deleted, never
hidden" is one of the five trust invariants. My earlier statement searched for
un-promote/retract verbs and concluded from their absence that recovery was
impossible; the recovery verb in this system is *demote*, not *remove*.

### Blast radius, verified

Bounded and small at current volume. The scheduled structured import fetches with
`LIMIT` pinned to **40** per run (`.github/workflows/import_structured.yml`, both
read sites, post-fix), twice daily. The licensed import has **no schedule at all**
and runs only by hand (R-055). Extraction is additionally capped off at the
provider right now. So the realistic near-term exposure is tens of events per day,
not thousands — the window in which a mistake is cheap.

### Consequences of each answer

**"Stands"** → Step 2 proceeds in the ratified order: safeguard 1's grading loop
live and tested first, then `worker/autopromote.py` added to the promote-import
allowlist in the same change, then the flag flipped only after all three safeguards
are verified on a preview. Trust-path, so evaluator-mandatory. The risk you accept
is that a gate-passing but wrong event reaches the feed at its earned confidence
before a human sees it — recoverable by demotion, visible in the audit log, and
bounded by the volumes above.

**"Hold"** → nothing is wired, and the long tail keeps requiring a click per event,
which is the thing you have now said three times does not scale. This is a real
option and not a failure: it is the correct answer if you would rather ship v1 on
the deterministic feeds alone and revisit auto-publish once the feed is live and
you have seen its quality with your own eyes.

**Recommendation: "stands", with the flip-to-ON still gated on safeguard 1** —
because saying "stands" costs nothing today (the flag stays OFF either way) and
unblocks the largest remaining piece of engineering, while the actual moment of
risk stays behind a separate, deliberate, founder-visible switch.

---

## What this document is not

It is not a decision. Both asks remain open in `docs/V1.md` and `TODOS.md`. It is
also **not** a claim that the recommendations are safe to self-approve: ask 5 is a
gate-threshold change and ask 3 touches a trust invariant, and `CLAUDE.md` puts
both squarely on the founder-crucial list.
