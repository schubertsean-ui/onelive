# Session handoff — 2026-08-06

Written at founder direction: *"Pause and save the work and create a prompt
for a new session."* The prompt to paste is at the bottom.

---

## Where things stand

**Seven PRs open, none merged.** The founder's standing rule freezes all
merges while an exam-bound PR is open, and #189 is exam-bound.

| PR | What it does | State |
|---|---|---|
| **#193** | First-party/published sources promote on ONE source | **FULLY GREEN — evaluator APPROVE.** Merge first. |
| **#189** | Date recovery + multi-page ingestion | Six review rounds; round 7 pending |
| #195 | Multi-page ingestion | **Fully subsumed by #189** — see the decision below |
| #192 | Quiet trust display, new-tab handoffs, source link restored | Needs a review round |
| #194 | Chronicle points at its real calendar subdomain | Needs a review round |
| #190 | Kaizen ledger rows | Needs a review round |
| #187 | Brave search lane + festival windows | Needs a review round |

**#193 is the one that matters.** Live autopromote logs show candidates being
held with *"policy would publish … but the fresh gate verdict is 'hold'"* —
the publish policy already implements the founder's ruling and the gate does
not. #193 makes them agree. In a sampled pass: 3 promoted, 4 held on exactly
this.

## Two founder rulings from the end of this session

1. **Plan first, always** — `docs/memory/decisions/2026-08-06_plan-first-ratified.md`.
   Verbatim: *"Plan first - I don't trust your building - plus it's the
   operational charter."* No substantive build before an approved plan. An
   evaluator finding is not an approval.
2. **Festival budget ceiling $75/month** —
   `docs/memory/decisions/2026-08-06_festival-budget-75.md`. Verbatim: *"Yes to
   $46 budget - go to $75 to ensure no issues."* Headroom, not a target.

## The remaining work

`docs/ops/PATH_TO_THOUSANDS_OF_EVENTS.md` — eight items, each measured from
live logs with citations. Headline finding: **the bottleneck is the gate, not
the supply.** 266 sources × ~40 events on page 1 is already ~10,000 candidates
per cycle; items 1 and 2 are about letting what we already extract reach the
site.

## What went wrong this session, so it is not repeated

- **#189 took six review rounds**, and rounds 3, 4 and 6 found the SAME class
  of defect — a partial identity signal (one shared word, a shared hour, a
  shared name) treated as proof of identity. Each fix patched an instance
  rather than the rule.
- **#189's branch carried the whole pagination feature** because #195 was cut
  from it, while the pagination fixes went only to #195. The panel kept
  finding pagination defects on a date-recovery PR for four rounds before this
  was noticed.
- **All testing was internal.** Not one check verified the live site's event
  count. That is item 8 in the path document and it is why progress felt
  unmeasurable.

## Mechanics the next session needs

- **Concurrency:** `ingest.yml` shares one concurrency group with the live
  cron. Dispatch ONCE and leave it alone — a second dispatch cancels the
  first, and the cron cancels whatever is in the slot. A cancelled run reads
  like a failure and is not one.
- **Arming re-bind ritual:** any change to the runtime closure
  (`worker/date_callback.py`, `orchestrator.py`, `gating.py`, `paginate.py`,
  `segment.py`, `ai_extract.py`, `datetime_normalize.py`, `ingest.yml`)
  invalidates `docs/evidence/ARMING_SMOKE_RUN.json`. Trust-gate and
  adversarial-review go red until a fresh branch-head ingest run is bound.
  That red is expected, not a defect.
- **Golden-exam is red BY DESIGN** on any PR touching `worker/ai_extract.py`.
  Verify eligibility each time by reading the classifier line: it must print
  `NOT manifest-bound`. It has, every round.
- **The sandbox cannot reach the GitHub API directly** — MCP tools only.
  `actions_list` responses often exceed the token limit; parse the saved file
  with python instead.

---

# PROMPT FOR THE NEW SESSION

```
Continue the 1LIVE build. Read these first, in order:

1. docs/ops/SESSION_HANDOFF_2026-08-06.md   (state, and what went wrong)
2. docs/ops/PATH_TO_THOUSANDS_OF_EVENTS.md  (the remaining work, measured)
3. docs/memory/decisions/2026-08-06_plan-first-ratified.md
4. CLAUDE.md + docs/OPERATING_RULES.md

Then run: python tools/session_reconcile.py

STANDING RULES (founder, non-negotiable):
- PLAN FIRST. Present WHAT / HOW / WHY / WHY-IT-MATTERS / EXPECTED OUTCOMES
  and get approval before touching product files. An evaluator finding is not
  an approval. The founder has said directly they do not trust unplanned
  building.
- Merges are silent on evaluator APPROVE + all green. Freeze all other merges
  while an exam-bound PR is open.
- Every founder directive gets a verbatim decision record in the same commit.
- Say "discovered events", never "long tail".
- No timers, no scheduled self-check-ins. The webhook subscription is the
  trigger.
- Never give click-path instructions through a vendor UI you cannot see. Use
  APIs or delegation tokens, or ask for a screenshot.
- Batch anything you need from the founder into ONE list with paste-ready
  values.

THE FOUNDER'S ACTUAL QUESTION, which governs priority:
"When will this ever end and I get my site live and full of thousands of
events?"

Answer it with measurement, not assertion. Suggested order:

1. MERGE #193 once the freeze lifts. It is already green with evaluator
   APPROVE. It converts the "policy would publish but the gate says hold"
   rows — visible in live autopromote logs — into published events. Highest
   leverage available.
2. Drive #189 to APPROVE (round 7 pending) and merge. Then decide #195:
   it is fully subsumed by #189, so either close it, or use it to split
   pagination back out of #189. Tradeoffs are in the handoff doc.
3. BUILD MEASUREMENT (item 8). Nothing else is legible without it. A
   scheduled job reporting candidates created, gate PASS vs HOLD, events
   promoted, and the live /tonight count. One number, visible without asking.
4. Then work the path document in its stated order, planning each first.

Do not start a new feature before #193 is merged and measurement exists.
```
