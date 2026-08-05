# PATH TO THOUSANDS — what remains before the live site carries thousands of events

**Written 2026-08-06 in answer to the founder's question, verbatim:**

> "When is all this testing going to end and I get my live site fully stocked
> with thousands of events?"

Method: a seven-agent adversarial investigation over the ingestion caps, every
loss point from source page to rendered card, all 16 open PRs, the live-state
evidence, and the source catalog — followed by a completeness critic that
attacked the findings and a synthesis that ordered them. Every claim below is
labelled **MEASURED** (read from code or a committed evidence artifact) or
**ESTIMATE** (modelled, with its band). Three findings marked MEASURED were
re-verified by hand before this document was written.

---

## THE HONEST ANSWER, FIRST

**Three things are true at once, and only one of them is what I have been
working on.**

**1. "Thousands live tonight" is not achievable, because it does not exist.**
Austin runs **250–1,000 events on any given night** (ESTIMATE, deduped and
occurrence-counted), 2,500–6,000 per week, 11,000–22,000 per month. "Thousands"
is a **week** or **month** number. This needs your confirmation before anything
else is scoped, because the two targets are months apart in effort.

**2. Tonight's low count is mostly NOT a supply problem — and I had this
wrong.** The feed hides anything past `start + 3h` assumed duration
(`web/lib/feed.ts:18-33`), while the database "today" window counts from
midnight. You looked at ~19:00 CT; every show that started before ~16:00 was
correctly filtered as already ended. 19 events in the window minus the
afternoon shows lands almost exactly on the 11 you saw. I spent this session
treating that number as evidence of thin supply. That was the wrong diagnosis.

**3. The real defect is that the discovered lane publishes events that can
never be seen — and I found the cause.** It is not the dates. It is two bugs
that are exact complements, and I verified both by hand:

- **Dated events can never publish.** `worker/candidate_store.py:174-181`
  builds the gate's conflict signal from *both* the `start_time` timestamptz
  column (psycopg2 returns it timezone-**aware** → `...T19:30:00+00:00`) *and*
  the same value's **naive** copy in the `extracted` JSON (`...T19:30:00`).
  The gate puts them in a set, sees two values, and ESCALATEs. I ran it:
  `_has_conflicting_start_time({'start_times': ['2026-08-08T19:30:00+00:00',
  '2026-08-08T19:30:00']})` → **True**. Same instant. Two string forms. Every
  candidate that carries a date is escalated as self-contradictory.
- **Dateless events can never render.** `web/lib/promoted.ts:94` filters
  `start_time=gte.<now-12h>`. In SQL a NULL is never `>=` anything, so every
  dateless promoted event is dropped by the server query — which is the entire
  population that *does* publish, precisely because dateless candidates have no
  date to conflict with. The "date TBA — never hide it" logic in
  `web/lib/feed.ts:22` is unreachable dead code.

That pair fully explains the live symptom **~1,363 published discovered events,
ZERO upcoming** (MEASURED, db-report run 31026850025). Dated events can't
publish; published events can't display.

**What this means for the work I did this session:** the date resolvers and
first-party gate fix in PR #191 are real improvements, but they were treating a
symptom. Neither would have put a single discovered event on the site while the
gate-conflict bug stands.

---

## THE ONE-WAY DOOR — READ THIS BEFORE ANY MERGE

**The date backfill must NOT run before the gate fix (B1) and the timezone
contract (B2) are on master.**

If it runs early, every row it successfully dates immediately acquires a
`conflicting start_time` ESCALATE **with `gate_reason` written**. That column
is the exact predicate `stamp_backlog` uses to *skip* rows
(`worker/autopromote.py:257-261` selects `gate_reason is null`), and
`run_autopromote` only ever looks at `ready_to_promote`. The human path is not
a fallback either — `promote_candidate` re-runs the identical gate and refuses.

**The backfill would convert thousands of recoverable rows into permanently
unpublishable ones.** This is not reversible by re-running anything.

---

## BACKLOG RECOVERY — making stuck data visible (~1 week)

| # | Step | Kind | Unlocks | Depends on |
|---|---|---|---|---|
| **B0** | Prove the gate-conflict bug against the live DB; dispatch `db-report.yml` **on master** | OPERATIONAL | Go/no-go for everything below | nothing |
| **B1** | Normalize the gate's start-time signals to one canonical instant | CODE (no PR exists) | Every dated discovered event, forever | B0 |
| **B2** | **FOUNDER**: settle the timezone storage contract, then fix it | FOUNDER → CODE | 0 new events; protects the correctness of all of them | before B8 |
| **B3** | One-time re-stamp that can revisit rows carrying a `gate_reason` | CODE (no PR exists) | **1,276 held + 97 escalated = ~1,373 rows** currently unreachable by *any* path (MEASURED). ESTIMATE 40–70% become promotable | B1, B5 |
| **B4** | Show promoted events that have no date (fix the NULL filter) | CODE (no PR exists) | Up to ~1,363 become eligible to render; ESTIMATE a few hundred actually do | none — shippable today |
| **B5** | **FOUNDER**: resolve #191 vs #193 on `worker/gating.py` | FOUNDER → merge | master 73/268 can publish alone → #191 ~172, #193 ~201 (MEASURED source counts) | B0, B1 |
| **B6** | **FOUNDER**: resolve #189 vs #191 date doctrine | FOUNDER → CODE | Prevents a silent doctrine inversion | B2 |
| **B7** | Merge the safe PRs (#192, #194, #195) | CODE | #192 zero (presentation); #194/#195 see below | B5 for #194's value |
| **B8** | Run the date backfill — dry-run, then real | OPERATIONAL ×2 | ESTIMATE, genuinely unknown: dozens to several hundred | **HARD: B1 + B2** |
| **B9** | Re-measure on master; reconcile STATE.md; close R-023 | OPERATIONAL | 0 — but nothing above is verifiable without it | B8 |

**B3 is the single most-missed step.** Nothing in the repo, and nothing in any
of the eight open PRs, can revisit a candidate once a `gate_reason` is written.
Merging *either* gating PR does **not** rescue the ~1,373 rows already judged by
the old five-anchor gate. That needs a deliberate sweep nobody has written —
the one I drafted this session (scratch only, not committed).

---

## ONGOING THROUGHPUT — making each day's crawl produce more

Ordered by leverage per unit effort.

| # | Step | Kind | Unlocks |
|---|---|---|---|
| **T1** | Give the committed catalog a way to reach the crawler at all | CODE | **+72 to +130 sources** (registry 268 → ~340–400). Cheapest volume in the plan — bookkeeping, not engineering |
| **T2** | Stop paying to re-extract unchanged pages (conditional requests) | CODE | 0 new events; frees **~60–70% of AI budget and wall clock** (ESTIMATE) |
| **T3** | Gate every candidate a page produced, not just the first | CODE | Up to **50×** gate throughput on multi-event pages |
| **T4** | **FOUNDER**: extraction cost and model tier | FOUNDER → CODE | Decides whether expansion is affordable at all |
| **T5** | Retain raw bytes so the segmenter can improve without re-crawling | CODE | 0 now; makes every future improvement free instead of a full paid re-crawl |
| **T6** | Measure what the segmenter throws away | CODE | Unknown — and that is the point |
| **T7** | Merge pagination (#195, not #189's copy) | CODE | **Modest**, hard-capped ~40 → 50 blocks/source/run |
| **T8** | **FOUNDER**: crawler politeness and legal posture | FOUNDER → CODE | Protects access to every source the plan depends on |
| **T9** | Source health, quarantine, per-source yield | CODE | Recovers **~19% of sweep slots** burned on dead sources (MEASURED: 31 failures of 166 eligible) |
| **T10** | A real migration runner | CODE | 0 directly; unblocks T9, T2, and every future schema change |
| **T11** | **FOUNDER**: the pipeline runtime | FOUNDER → CODE | **The hard ceiling on all throughput** |
| **T12** | Make the read path survive its own success | CODE | 0; stops the volume win from breaking the site |
| **T13** | Light the licensed lanes already built and dark | OPERATIONAL + credentials | ESTIMATE +55 to +215/month net of overlap |
| **T14** | Expand the registry along the axis that carries events | PROGRAM | The only step that reaches **thousands per week** |

### The three that will surprise you

**T7 — pagination is the *least* valuable of the three levers**, not "the single
biggest lever left" as PR #195 states. `ai_extract` takes `blocks[:50]` of the
*concatenation*, so following 5 pages of a 60-page calendar still yields at most
50 blocks. The Austin Chronicle's 2,362 events do not arrive by paginating.

**T11 — GitHub Actions cannot physically reach the target.** The charter says
"Python/FastAPI + Celery workers." There is no Celery, no Dockerfile, no
deployment of any kind. The whole pipeline is one serial loop in one
concurrency group under a 60-minute timeout. **No value of `MAX_SOURCES`
processes 800+ sources per sweep.** Cap tuning below this ceiling is wasted
effort. This also means the FastAPI ops console — the human half of gate
custody — is deployed nowhere (`web/lib/ops-api.ts` defaults to
`localhost:8000`).

**T14 — the catalog is yield-inverted.** 64 Hill Country tasting rooms are 36%
of the rows and carry ~13% of events; 28 institutional calendars are 16% of the
catalog and carry ~60%. Ten more university/library feeds are worth more than
the entire Hill Country block. The catalog was expanded along the axis cheapest
to hand-curate, not the axis that carries events.

---

## THE ARITHMETIC

- **MEASURED baseline** (db-report 31026850025, 2026-08-05 16:46Z): 3,004
  published events = 1,641 licensed + ~1,363 discovered. Upcoming 1,370, of
  which **discovered = 0**. Sources 268 cataloged / 268 enabled / 246 producing.
- **MEASURED**: master's `ingest.yml` already reads `'30'` sources per scheduled
  run (lines 100 and 195), not 10. Only the comments still say 10.
- **Wall-clock ceiling (the real one)**: 30 sources × 50 blocks = 1,500 model
  calls must fit 3,600s minus ~660s fixed overhead = **1.96 s/call required**.
  Opus is realistically 5–15 s/call. The job is killed at 60 minutes after
  roughly 300–600 calls **regardless of any cap**.
- **Observed delivery**: ~19% of cron slots fired on 2026-08-05 (live API
  observation, one day, NOT a certified measurement). R-023 records ~7% from
  2026-07-22 and its resolution trigger fired 2026-07-23 unactioned.
- **Duplication tax**: the orchestrator never sends conditional requests, so
  every sweep re-fetches and re-extracts unchanged pages at full model cost.
  ESTIMATE 60–70% of spend is re-work.
- **Cost — no dollar figure exists anywhere in this repo.** Per-call token usage
  is captured at `ai/claude_provider.py:417` with a comment saying it feeds the
  cost ledger; grep returns exactly one hit and nothing reads it. ESTIMATE at
  ~$0.011/call: **~$1,650/month today**, ~$13k/month at 800 sources,
  ~$66k/month at 4,000.

### What each target costs

| Target | Sources needed | Time | Feasible? |
|---|---|---|---|
| Hundreds visible | 268 (have them) | **~1 week** of ordered fixes | Yes |
| **Thousands per MONTH** | ~340–400 | **weeks** — mostly reconciling two registries we already have | Yes |
| Thousands per WEEK | ~800–1,600 | 2–4 months + new runtime + real monthly bill | Needs T11 + T4 |
| Near-total Austin coverage | ~2,900–4,200 | a program | Needs everything |

All source→event figures carry a **~3× band**. They are built from source
composition plus public anchors, not from a single measurement, because **no
per-source yield instrument exists**. Read them as shape, never as forecast.

---

## BLOCKERS THAT NO PR CAN CLEAR

1. **One-way door**: backfill before B1+B2 (above).
2. **Diagnostic**: no db-report since 2026-08-05 16:46Z. Branch dispatch is
   silently SKIPped by the master-only ref guard. Every population number here
   is second-hand until a master dispatch runs.
3. **Merge-order**: #189 and #191 merge **cleanly into a doctrine inversion** —
   git interleaves their date-recovery blocks into a sequence, and #191's block
   deletes the entries #189's block is guarded on, so an *inferred* year
   silently beats the source site's own declared date.
4. **Merge-order**: #189, #191, #193 all re-bind `ARMING_SMOKE_RUN.json`;
   whichever merges second must re-smoke. By design.
5. **Blocked PRs**: #187 (conflicts on `ops-diagnostics.yml`) and #190
   (conflicts on the Kaizen ledger) cannot merge in any state until rebased.
6. **External**: SeatGeek's API application awaits provider approval.
7. **Credentials**: `BRAVE_API_KEY` does not exist, so PR #187 cannot function.
   Agents never mint keys.
8. **No mechanism**: `tools/import_sources.py` is referenced by no workflow, so
   the two registries cannot converge without a human running a script.
9. **No mechanism**: 14 of 20 migrations are applied by nothing. There is no
   schema ledger and no migration runner.
10. **Architectural**: the serial-job ceiling (T11).
11. **Custody**: the ops backend is not deployed, so human-custodied promotion
    has no working surface.
12. **Cost blind spot**: no spend figure exists (T4).

---

## WHAT I NEED FROM YOU — one list

1. **Target**: thousands per **week** or per **month**? (Per night does not exist.)
2. **Gating (B5)**: is a newspaper/radio/TV calendar (`local_media`, 29 sources)
   first-party authoritative, or third-party needing corroboration? That single
   class is the entire disagreement between #191 and #193.
3. **Timezone (B2)**: when a venue writes "Fri Aug 8, 8:00 PM" with no zone, do
   we assume America/Chicago? (Recommended — it is what the venue means. Today
   we store naive and Postgres reads UTC, landing it 5–6 hours early.)
4. **Date doctrine (B6)**: source-site declared date beats inferred year —
   confirm, and I rework whichever PR loses.
5. **Money (T4)**: approve building the cost ledger, then choose a model tier.
6. **Legal (T8)**: robots.txt + per-domain rate limiting + a real abuse contact
   before any automated enrollment. (Today: no robots handling, a global rather
   than per-host delay, and an undeliverable `.example` contact address.)
7. **Runtime (T11)**: sharded Actions matrix (cheapest) or a real worker
   deployment. Either is new spend.
8. **R-081**: audit the 55 `community` sources — the largest single class,
   classified third-party on an explicitly unaudited assumption.

---

## PROVENANCE

Investigation: workflow `path-to-thousands`, run `wf_d8ea3440-e25`, 7 agents,
1,104,568 subagent tokens, 343 tool calls. Per-agent returns in that run's
`journal.jsonl`. The completeness critic's corrections to the investigators are
incorporated — including one factual correction (master's source cap is 30, not
10) that invalidated an entire lens's arithmetic.

Hand-verified before publication: the gate-conflict reproduction, the
`candidate_store` dual-signal construction, the `promoted.ts` NULL filter, and
`normalize_datetime_claim`'s naive return.
