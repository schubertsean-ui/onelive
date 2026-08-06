# SESSION KICKOFF — 2026-08-07 (successor to SESSION_KICKOFF_2026-08-06.md)

Founder-commissioned work order. **Read this file, then
`docs/ops/PATH_TO_THOUSANDS.md`, then
`docs/memory/decisions/2026-08-06_path-to-thousands-and-the-gate-conflict-bug.md`
— in that order — before touching anything.** Then run
`python tools/session_reconcile.py` and verify every claim below against live
state (PR states via the GitHub API, DB via `db-report.yml` **dispatched on
master**, site via `ops-diagnostics` site-probe — the sandbox proxy reaches
neither 1live.co nor venue sites directly). Contract-first: write Session
Contract #45 to STATE.md (five §4a fields) before any build.

Founder question that produced this kickoff (verbatim):

> "When is all this testing going to end and I get my live site fully stocked
> with thousands of events?"

---

## READ THIS BEFORE YOU PLAN ANYTHING

The previous session spent most of its time driving PR #191 (first-party gate
+ date resolvers + dedupe) through five CI cycles. **That work was treating a
symptom.** A seven-agent investigation then found the actual cause, and it was
hand-verified:

- **`worker/candidate_store.py:174-181`** feeds the trust gate BOTH the
  timezone-**aware** `start_time` column and its **naive** twin from the
  `extracted` JSON. The gate sees two strings, calls it a conflict, and
  ESCALATEs **every candidate that carries a date**. Reproduce it yourself in
  one line before you believe it:
  ```
  python3 -c "from worker.trust_gate3 import _has_conflicting_start_time; \
    print(_has_conflicting_start_time({'start_times':['2026-08-08T19:30:00+00:00','2026-08-08T19:30:00']}))"
  ```
  → `True`. Same instant.
- **`web/lib/promoted.ts:94`** filters `start_time=gte.…`, and SQL NULL is never
  `>=` anything, so every **dateless** promoted event is dropped by the server
  query.

Dated events can't publish; published events can't display. That pair is why
there are ~1,363 published discovered events and **zero** upcoming.

**Do not start by merging PRs.** Start at B0 in `PATH_TO_THOUSANDS.md`.

---

## HARD STOP — the one-way door (R-083)

**Do NOT dispatch `backfill-dates.yml` with `real=true`** until BOTH are on
master:
1. the canonical-instant gate-signal fix (R-084a), and
2. the founder-ratified timezone storage contract (R-083's second constraint).

Running it early writes a `gate_reason` on every row it dates, which
permanently removes those rows from every automated *and* human path. It
converts recoverable rows into unpublishable ones and nothing undoes it.

---

## WHERE WE ARE (verified 2026-08-05/06; RE-VERIFY at session start)

**Master:** `9a59189`. **This session's branch:** `claude/1live-kickoff-2026-587s4f`
pushed at `cb6916f`, PR **#191 OPEN, NOT MERGED**.

**PR #191 state — everything done except one mechanical step:**
- All five evaluator findings from round r3 are FIXED and tested: weekday-only
  claims no longer take a fabricated midnight; a raw claim's weekday is checked
  against the block date; a stale listing no longer rolls a year forward
  (`MAX_FUTURE_DAYS=300`); `end_time` before `start_time` is dropped; the
  backfill no longer writes onto disputed public rows.
- Local gates green: `trust_gate` OK, `lint` OK, pytest 2119 passed, perf 4/4.
- `golden-exam` red is the charter's **eligible compensated class** — the
  classifier prints `NOT manifest-bound … worker/ai_extract.py` and no
  `EXCEPTION-INELIGIBLE` marker. Verified each round.
- **Outstanding:** the arming smoke re-bind. `worker/datetime_resolve.py` is in
  the armed runtime closure, so `ARMING_SMOKE_RUN.json` must be re-bound to a
  fresh green ingest run on the head. Two dispatches were CANCELLED while
  queued, contending with a parallel session's branches for the single
  `ingest` concurrency group.

**A parallel Claude session (`session_01HZnpc5yC6GhDi19fLvWpHs`) is working the
same mission.** It owns #187, #189, #190, #192, #193, #194, #195. This is how
the #191/#193 collision happened. **Ask the founder whether both sessions
should keep running** before doing anything that touches a shared file.

**Open PRs and their real value** (full table in `PATH_TO_THOUSANDS.md`):
- **#191** (this branch) — gate + date resolvers + dedupe. Conflicts with #193.
- **#189** — date recovery via source callback. **Merges CLEANLY with #191 into
  a doctrine inversion**: git interleaves the two date blocks and #191's block
  deletes the entries #189's is guarded on, so an *inferred* year silently
  beats the source site's own declared date. Founder decision B6.
- **#193** — the same gate rewrite, differing on exactly one class:
  `local_media` (29 sources). Founder decision B5.
- **#192, #194, #195** — safe, mergeable, no decision needed.
- **#187** (conflicts on `ops-diagnostics.yml`) and **#190** (Kaizen ledger)
  cannot merge in any state until rebased.

---

## THE QUEUE — in dependency order, not preference order

Every step, its kind, and what it unlocks is in
`docs/ops/PATH_TO_THOUSANDS.md`. Do not re-derive it; execute it.

**Week one — backlog recovery (B0→B9):**
1. **B0** Dispatch `db-report.yml` **on master** (branch dispatch is silently
   SKIPped by the ref guard). Every population number in the plan is
   second-hand until this runs. Confirm the gate-conflict bug against live rows.
2. **B1** Canonical-instant gate signal (R-084a). New small PR, evaluator-mandatory.
3. **B4** Fix the promoted NULL filter (R-084b). Independently shippable today.
4. **B2/B5/B6** Founder decisions — ask as ONE list, then implement.
5. **B3** The one-time re-stamp sweep (R-085) — ~1,373 rows no path can reach.
   A draft exists in the previous session's scratch; it was never committed.
6. **B7** Merge #192/#194/#195.
7. **B8** Backfill, dry-run then real — **only after B1 and B2**.
8. **B9** Re-measure on master, reconcile STATE.md, close R-023.

**Then — ongoing throughput (T1→T14).** Highest leverage first: T1 (catalog
can't reach the crawler at all), T2 (60–70% of spend is re-work on unchanged
pages), T3 (only the first of up-to-50 candidates per page is ever gated).

---

## STANDING CONDUCT (founder-set; these outrank convenience)

- Never give click-path instructions through a vendor UI you cannot see — use
  the delegated CI diagnostics or ask for a screenshot.
- Freeze all other merges while an exam-bound PR is open.
- Merges are silent, on evaluator APPROVE + every required check green.
- Every founder directive gets a verbatim decision record in the same commit.
- Say "discovered events", never "long tail".
- No timers — webhook subscriptions are the trigger.
- Batch everything you need from the founder into ONE list with exact
  paste-ready values.

## KNOWN FRICTION (do not rediscover these)

- The sandbox proxy blocks 1live.co **and** all venue sites. Live pages cannot
  be fetched here; the pipeline's own logs are the only ground truth available.
- `ingest.yml` shares one `concurrency: group: ingest` with the master cron
  (`9,29,49`), so a branch smoke dispatch queued behind it gets **cancelled**,
  and a cancelled run looks like nothing happened. Fix (key the group by ref)
  belongs in a PR already re-binding for another reason.
- Any touch of a file in the armed runtime closure costs a paid smoke run plus
  a full CI round. **Batch all reviewer fixes into ONE commit before
  re-smoking.**
- `db-report.yml` and `backfill-dates.yml` are master-only by design (PR #174
  evaluator finding). A branch dispatch SKIPs silently.

## OPEN FOUNDER ASKS (consolidated — do not dribble these out)

The full list with context is the last section of
`docs/ops/PATH_TO_THOUSANDS.md`. In short: the target window (week vs month),
`local_media` classification, the timezone contract, the date doctrine, the
cost ledger + model tier, crawler legal posture, the pipeline runtime, and the
R-081 audit of 55 `community` sources.

## DEFINITION OF DONE FOR THIS SESSION

Not "PRs merged." **Discovered events visible in a forward window on
1live.co/tonight, proven by a master `db-report` and a site probe, with a
before/after table.** If that is not reachable, the session ends with the
specific step that blocked it and the evidence for why.
