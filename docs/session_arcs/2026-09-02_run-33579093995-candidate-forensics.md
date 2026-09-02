# What happened to the 198 — run 33579093995 candidate forensics

**Session:** 2026-09-02 · read-only forensics, no product code changed.
**Question the founder asked:** what is the time window of run 33579093995's
candidates, and can any of them appear on `/tonight`?

Everything below is quoted from evidence that survives this session: the run's
own job log, the two autopromote passes that followed it, and the code on
disk. Numbers I could **not** verify are marked `UNVERIFIED` with the reason —
they are not estimated and not guessed.

---

## 0. The run

| fact | value |
| --- | --- |
| run | [33579093995](https://github.com/schubertsean-ui/onelive/actions/runs/33579093995) — "Ingestion Run", `workflow_dispatch` |
| head | `c0d80c2` on `claude/follow-pages-live-loop-o0g3tm` |
| wall clock | 2026-09-02 01:22:03Z → 01:37:55Z (Austin: Mon 1 Sep, 20:22 → 20:37) |
| pipeline `run_id` | `9b7723a4-295f-4ceb-9007-ad6fb9e9d999` |
| budget | `MAX_SOURCES=10`, `SOURCE_CLASS=B`, follow ≤15/source ≤30/run |
| RunReport | `fetched 9 · extracted 9 · passed 8 · escalated 1 · held 0 · errors 1 · pages_followed 19 · pages_extracted 18 · pages_missed 11 · pages_walled 0 · candidates 198` |

**"the time window of the candidates" has two readings, and they have different
answers.** The window in which the rows were *created* is the 15 minutes above,
exactly. The window the founder actually cares about — the window of the
*events* those rows describe — is a database fact I cannot read from this
sandbox (see §3).

---

## 1. The table

Read the two right-hand groups as: what the run log proves, then what only the
database can answer.

| source | candidates in that wave | earliest start | latest start | start on 2026-09-01 | start in next 7 days | held | ready_to_promote | already promoted | on /tonight today |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bullock Texas State History Museum | **0** (HTTP 403 on its calendar URL — `stage=error`) | — | — | 0 | 0 | 0 | 0 | 0 | 0 |
| Austin Food & Wine Festival | ≥1 · exact UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Stubb's Austin | ≥61 (56 from 8 followed pages + ≥5 base) | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Blanton Museum of Art | ≥51 (51 from 11 followed pages) | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Kingdom Nightclub | ≥13 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| The Contemporary Austin | ≥3 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Emo's Austin | ≥10 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Come and Take It Live | **1** (zero events from a 53,617-char page — one flagged empty candidate) | n/a | n/a | 0 | 0 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 0 |
| Elephant Room | ≥19 | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| Ballet Austin | **1** (zero events from a 247,963-char page — one flagged empty candidate) | n/a | n/a | 0 | 0 | UNVERIFIED | UNVERIFIED | UNVERIFIED | 0 |
| **TOTAL** | **198** (107 from followed pages, 91 from the 9 base pages) | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED | 0 at ingest | see §2 | see §2 | UNVERIFIED |

**Where the per-source floors come from.** The RunReport prints follow-page
candidate counts per source, and `worker/ai_extract.py` logs one line per
candidate whose date claim it refused. Counting those refusal lines gives an
exact floor per source. The run log does not print base-page candidate counts
per source, so the exact split of the 91 base-page rows across 9 sources is
not recoverable from the log; the replay-log artifact that holds it
(`replay-log-33579093995`) is on Azure blob storage, which this sandbox's
egress proxy refuses (`403 CONNECT`).

### The number that matters most

**92 of the 198 candidates (46%) were stored with `start_time = NULL`.**

| source | candidates whose `start_time` was refused | reason |
| --- | --- | --- |
| Blanton Museum of Art | 42 | `no-full-date-evidence` |
| Elephant Room | 19 | `no-full-date-evidence` |
| Kingdom Nightclub | 13 | `no-full-date-evidence` |
| Emo's Austin | 10 | `no-full-date-evidence` |
| Stubb's Austin | 5 | `no-full-date-evidence` |
| The Contemporary Austin | 3 | `no-full-date-evidence` |
| **total** | **92** (44 of them also lost `end_time`) | — |

The refused raw values in the log are things like `'6:00PM'`, `'9:00PM'`,
`'7:30 PM'` — a time with no date next to it on the page.

---

## 2. The gate that stops them — one paragraph

Nothing stops a gate-passed row from being **promoted**: promotion already
happens automatically. `.github/workflows/autopromote.yml` runs hourly at :15
with `AUTO_PUBLISH_RATIFIED: "1"`, and the two passes that bracket this wave
each published 185 events (run
[33579788399](https://github.com/schubertsean-ui/onelive/actions/runs/33579788399)
at 01:33Z and run
[33584503550](https://github.com/schubertsean-ui/onelive/actions/runs/33584503550)
at 02:47Z, both `promoted 185 · human_review 14 · errors 1`). What stops those
published rows from reaching `/tonight` is a **date**, in two places. Upstream,
`normalize_datetime_claim` in `worker/datetime_normalize.py` refuses any claim
that does not evidence a full calendar date — it parses the string twice
against two different default dates and, when the two disagree (which is what
`'6:00PM'` does), returns the refusal `no-full-date-evidence` and stores NULL,
preserving the raw claim in provenance. `worker/promote.py::promote_candidate`
does not require a `start_time`, so those rows publish into `event` with a NULL
start. Downstream, every dated read filters on that column —
`buildPromotedQuery` in `web/lib/promoted.ts` appends `start_time=gte.<fromISO>`
and `api/public.py::tonight` uses `e.start_time >= %s and e.start_time <= %s` —
and in SQL a comparison against NULL is never true, so a NULL-start event is
silently absent from every time-windowed view, forever, with no error anywhere.
The region filter is **not** implicated: `filterToCapcog` in `web/lib/region.ts`
is deliberately tri-state and keeps rows whose city it cannot classify. So the
honest answer to "can any of the 198 appear on /tonight" is: **at most 106** kept
a date and can appear (the ones dated today already should have) — at most,
because a candidate that claimed no date at all, such as the two flagged empty
rows, is refused nothing and so logs nothing; the 92 that lost theirs cannot
appear on any dated surface at all, no matter how many promote passes run.

Two second-order consequences worth knowing, both visible in the same code:
`promote_candidate` runs duplicate detection only `if start_time` (line 132), so
the 92 NULL-start rows also bypass dedupe entirely; and they still count as
"published events" in every total the scope report prints, which is why
published-event counts can rise while the per-window discovered counts do not.

---

## 3. Why four columns say UNVERIFIED

The four DB columns (earliest/latest start, start on 2026-09-01, start in the
next 7 days, held / ready / promoted / on-Tonight per source) need one
wave-scoped read of `event_candidate` and `event` filtered by this run's rows.
I have no way to run it from here, and I will not fake it:

1. **No credential in the sandbox.** `ONELIVE_DB_DSN` is unset;
   `tools/session_reconcile.py` reports `DB facts UNVERIFIED` for the same reason.
2. **No network path.** The egress proxy answers `403 CONNECT` for `1live.co`
   and for the artifact blob host, so neither the live feed nor the replay log
   is readable from here.
3. **The read-only reporter that does have the credential cannot answer this
   question, and cannot run from a branch.** `.github/workflows/db-report.yml`
   is guarded `if: github.ref == 'refs/heads/master'` (deliberately — a
   dispatch runs the dispatched ref's code, so a branch must never be paired
   with production secrets), and the script it runs,
   `tools/db_scope_report.py`, reports whole-catalog scope, not one wave.

Making those four columns real therefore needs a founder decision, which is §4.

---

## 4. The throughput finding (why this is not only a date problem)

Both autopromote passes examined **exactly 200** candidates — the batch ceiling
`LIMIT` — while their gate-stamping pre-phase classified far more rows as ready
in the same pass:

| pass | stamped ready | promoted | net change to the ready queue |
| --- | --- | --- | --- |
| 01:33Z run 33579788399 | 278 | 185 | **+93** |
| 02:47Z run 33584503550 | 347 | 185 | **+162** |

The `ready_to_promote` queue is growing by roughly 100–160 rows an hour. This is
structural, not a backlog blip: `worker/orchestrator.py::_process_fetched_page`
gate-stamps only the **first** candidate of each page during the run (the
comment says so: "the rest are stamped by the orchestrator's backlog sweep"), so
of this wave's 198 rows only about 27 — one per extracted page — were stamped at
ingest; the other ~171 waited for the hourly sweep. The sweep is keeping up
(it examined 487 < its 1000 ceiling, meaning it drained what was there). The
**promote** step is not.

---

## 5. What I did not do, and why

Per the session leash: no catalog upsert (R-086), no R-087 start-page-wall
reclassification, no search-triage product, no `/tonight` redesign, no new
vendor, no 180-row `source.config` write. None of those were touched.

I also did not raise the promote batch ceiling, did not write a new report
script, and did not file a RECORD row for the two defects named above — each is
a change the founder asked to approve first. They are §6.

---

## 6. The ask — four numbered items, one list

1. **Let me measure the wave.** Cheapest option: I add a read-only,
   wave-scoped query script (same shape as `tools/db_scope_report.py` —
   connection opened `default_transaction_read_only=on`, so it physically
   cannot write) plus a dispatch mode, you merge it, and it runs on master.
   *Why this and not the alternatives:* editing `ingest.yml` to run a query on
   a branch would pair branch-edited code with production secrets, which is the
   exact thing `db-report.yml`'s master-only guard exists to prevent; handing me
   a DSN would be credential-minting, which agents never do. *Tradeoff:* it
   costs one merge before any number exists.
2. **Raise the promote ceiling, or accept a growing queue.** `LIMIT` is 200 per
   hourly pass against 278–347 newly-ready rows per pass. Raising the default in
   `.github/workflows/autopromote.yml` is a one-line change to a live scheduled
   loop — a policy change, so it is yours, not mine. *Tradeoff:* a larger batch
   means more DB writes per pass and a longer job; it does not change any gate,
   any threshold, or what qualifies for publication.
3. **Decide what a dateless event is worth.** 46% of this wave has no date, so
   it is invisible on every dated view and skips dedupe. Fixing it means either
   teaching extraction to carry the page's date context down to each event
   block (touches `worker/ai_extract.py` — explicitly outside this session's
   leash) or giving the feed an honest "date unknown" surface (a `/tonight`
   change — also outside it). *Tradeoff:* both are real work; doing neither
   means the crawl keeps paying for rows that can never be seen.
4. **May I file the two RECORD rows?** The charter says a noticed-but-unfixed
   issue is recorded in `docs/RECORD.md` in the same commit, and items 2 and 3
   qualify. The leash says only the listed work. I am surfacing the collision
   instead of resolving it: say the word and I file them.
