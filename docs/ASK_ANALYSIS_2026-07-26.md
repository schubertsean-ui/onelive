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

## Ask 5 — what an escaped defect should do to the gate

### The situation, mechanically

`docs/metrics/KAIZEN_LEDGER.md` now carries the literal token `M3-ESCAPE` on one
row. `tools/kaizen_trends.py::escapes()` counts occurrences of that token in the
ledger text; any non-zero count is a finding
(`"M3 ESCAPES RECORDED: {n} — the absolute goal is 0"`), the report prints
`m3_escapes: 1 (goal: 0, absolute)`, and `tools/validate` goes red. Two tests read
the live ledger and assert zero. `--allow-skips` does not waive it, deliberately.

An escape is **permanent history** — the whole point is that it is never erased.
So as written, the gate is **red forever**, on this and every future PR.

### Recurrence history — the honest count

**This is the first M3 escape ever recorded.** The ledger row states it
*"supersedes the 'none recorded to date' row above."* The alarm has never fired
before, so there is no history of it being argued down. That matters both ways:
nobody has been eroding this gate, and nobody has yet had to live with it.

**But the underlying problem is not new, and the repo has already solved it once.**
`tools/kaizen_trends.py::family_alarm` handles the sibling case — the repeat-class
alarm — and its docstring records the semantics the independent evaluator ratified
at round 6 of an earlier PR:

> *"a fix marker is credit for catches AT-OR-BEFORE its row only, never a permanent
> waiver. No marker: alarm when total catches ≥ threshold. Marker exists: any catch
> in a row AFTER the last marker row alarms IMMEDIATELY — a recurrence after a
> claimed structural fix means the fix escaped, the exact condition the meter must
> surface loudest."*

That is option (a) already built, already reviewed, already in the same file. The
M3 escape alarm is the one counter in that tool that did **not** get the treatment.

### The one relevant precedent for relaxing a gate, and how it went

**R-051, 2026-07-25.** `tools/adversarial_review.py`'s 800 KB diff cap refused to
review a 1.26 MB branch. The founder was given the options explicitly (raise the
cap / split now / merge on founder authority) and chose to merge on authority,
because trust-gate was fully green. **Consequence: a whole session's work — 154
files, ~21k added lines — merged with the mandatory independent review never
having run.** Prevention shipped afterwards (`tools/pr_size_check.py`).

The lesson is not "never relax". It is that **when a gate blocks and there is no
mechanism to satisfy it, the pressure resolves as an override, and the override is
what costs you.** That is precisely the position a permanently-red alarm creates,
on every PR, forever.

### The countervailing precedent

**M7, founder-ratified 2026-07-15: the extraction hallucination threshold "only
ever TIGHTENS — a one-way ratchet driven by measurement, never by optimism."** The
culture of this repo is that gates do not get easier. Any change here has to be
squared with that, not waved past it.

### The options, and what each costs

| | Option | What it costs |
|---|---|---|
| **(a)** | An escape stops blocking once its **`Gate-gap closed`** column names a shipped mechanism. Count stays 1 and stays visible. A recurrence *after* the fix alarms immediately. | Someone could fill the column dishonestly. Bounded by: the column must name a real test, and the post-fix recurrence rule means the lie fails loudly the next time the class appears. |
| **(b)** | Window the count (e.g. last 90 days). | Hides history. Weakest option — it makes the ledger lie by omission, which is the thing this repo exists not to do. |
| **(c)** | Keep permanent red. | `validate` is red forever. Every future PR merges on `--allow-skips` or founder authority — the R-051 pattern, made routine. **And it creates a standing incentive not to record escapes at all**, which would destroy the measure. The PR #76 reviewer already identified omitting the token as the fail-open. |
| **(d)** | Founder acknowledges each escape; acknowledgement clears the block. | Real human custody, but it is a manual step in a machine gate. Manual steps rot, and it puts the founder in the loop on every future PR — the opposite of what the founder has asked for. |

### Recommendation, and an honest note about my own reversals

**Recommended: (a), implemented exactly as `family_alarm` already implements it,
with a standing notification to the founder at each escape (not as a gate).**

Rationale: it is not a new invention — it is the semantics an independent reviewer
already ratified for the sibling alarm in the same file. It does **not** move the
M3 target, which stays **0, absolute**. What changes is the *blocking condition*:
from "any escape ever recorded" to "any escape whose gate-gap is not closed." An
escape with no shipped mechanism still blocks forever, which is the property worth
protecting.

**Whether that counts as a relaxation or a refinement is exactly the judgement
that is yours and not mine**, and it is the reason this is written up rather than
done.

**I have changed this recommendation twice, and you should know that before
weighing it.** First (a); then (d), after finding the M7 ratchet and the R-051
consequence in the docs; now back to (a), after reading `family_alarm`'s actual
code and finding the precedent already built. The reversals track new evidence, not
new opinions — but two reversals mean this is finely balanced, and my confidence
should be read as moderate, not high.

### What is true today regardless of the decision

`validate` is red, PR #76 cannot merge, and the `adversarial-review` job runs the
test suite before the review — so this also blocks the independent review, not just
the merge. Verified on CI at head `ac44dd6`: **1,692 passed, 2 failed, 28 skipped**;
the two failures are these tests and nothing else.

---

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
