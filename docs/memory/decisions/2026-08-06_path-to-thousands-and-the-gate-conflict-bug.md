# Decision: pause the PR push, find the real cause, and write the path down (2026-08-06, founder-directed)

**Founder, verbatim:**

> "When is all this testing going to end and I get my live site fully stocked
> with thousands of events?
> Find a place to pause.
> Create a detailed list of what remains to have thousands of events listed on
> the live site.
> Codify to the record.
> Create a prompt for a new session."

## What was happening when this landed

I was ~5 CI cycles into driving PR #191 (first-party gate + date resolvers +
dedupe) to green, having just fixed five real evaluator findings. Each fix
touched a file in the armed runtime closure, which invalidates the arming
evidence, which costs a paid smoke run and a full CI round. Two consecutive
smoke dispatches were then cancelled while queued, contending with a parallel
session's branches for the single `ingest` concurrency group.

The founder's question is fair and the answer is that the loop I was in would
not have ended, because **it was not the loop that mattered**.

## What the investigation found (the reason this record exists)

A seven-agent investigation (workflow `path-to-thousands`, run
`wf_d8ea3440-e25`) established that the work I had been doing all session was
treating a symptom. The cause is a pair of complementary bugs, both
hand-verified before this record was written:

1. **Dated discovered events can never publish.**
   `worker/candidate_store.py:174-181` builds the gate's conflict signal from
   BOTH the `start_time` timestamptz column (psycopg2 returns it
   timezone-AWARE) and the same value's NAIVE copy in the `extracted` jsonb.
   `trust_gate3._has_conflicting_start_time` sets them, sees two, ESCALATEs.
   Verified in-process: the same instant in two string forms returns `True`.
2. **Dateless discovered events can never render.**
   `web/lib/promoted.ts:94` filters `start_time=gte.<now-12h>`; SQL NULL is
   never `>=` anything, so the server query drops the entire population that
   does publish.

Together these fully explain the standing symptom **1,363 published discovered
events, ZERO upcoming**. Dated events can't publish; published events can't
display.

## The lesson, category (extends red class `silent-yield-collapse`)

The 2026-08-05 record `2026-08-05_ingestion-learns-or-it-fails.md` named the
class: a fail-closed policy at a lossy boundary must ship with a yield
measurement. This session proves the sharper form of it — **I diagnosed the
wrong cause twice in a row and both times shipped a real fix for it**, because
no instrument distinguished "the gate is too strict" from "the gate is
mis-computing its own inputs." Both produce the same visible symptom: events
held.

The corrective is not more care. It is that **a stage which drops an item must
record WHY in a form that can be counted**, so the top refusal reason is a
report row rather than a hypothesis. That is the refusal/yield ledger already
committed as the next workstream; this session escalates it from "next
workstream" to a prerequisite for further pipeline work.

## The second lesson: I was wrong about the founder's "11 items"

The founder's screenshot showed 11 events on /tonight. I treated that as
evidence of thin supply and built against it. It is not: `web/lib/feed.ts:18-33`
hides anything past `start + 3h`, while the DB "today" window counts from
midnight, so at ~19:00 CT the afternoon shows were correctly filtered as ended.
19 in the window minus the afternoon lands on 11. **The number was the code
working.** Chasing supply from it meant the fix that would actually change what
the founder sees at 7pm — honoring real `end_time` instead of assuming 3 hours,
and surfacing later-tonight/tomorrow density — was never scoped.

## Decisions taken

1. **PAUSE the #191 push.** The branch stays pushed at `cb6916f` with all five
   evaluator findings fixed and every local gate green; only the mechanical
   arming re-bind is outstanding. It is NOT merged, and per the founder's own
   standing rule it must not be while exam-bound #189 is open.
2. **The backfill is a ONE-WAY DOOR and is now blocked in the record.** Running
   it before the gate-conflict fix writes a `gate_reason` on every row it dates,
   which permanently removes those rows from every automated and human path.
   Recorded as R-083 with its ordering constraint.
3. **"Thousands" is re-scoped as a WEEK or MONTH target**, pending founder
   confirmation. Austin carries 250–1,000 events on any given night; thousands
   live tonight is not a thing that exists to be found.
4. **The full ordered plan is written to `docs/ops/PATH_TO_THOUSANDS.md`**, with
   every figure labelled MEASURED or ESTIMATE, and the eight founder decisions
   consolidated into one list per the founder-comms rule.

## Trust custody

Unchanged. Nothing in this record or its companion documents moves a gate, a
threshold, or a publication path. The gate-conflict fix (B1) is a trust-path
change and is evaluator-mandatory when it is built; the timezone contract (B2)
and the gating resolution (B5) are founder-crucial and are asked, not decided.
