# Decision — loop-latency budget, and the go-live posture (2026-07-26)

**Status: BINDING for the decisions it records.** These are agent decisions taken
under `CLAUDE.md` ("Everything else: decide, write the decision record, proceed").
None of them is founder-crucial; the two that *would* have been are named at the
bottom as explicitly NOT taken.

Triggered by two founder messages on 2026-07-26:

> *"Tell me why any function or round or action should take more than 10sec let
> alone 2 minutes or 30 to run and be verified it ran or didn't and evaluate the
> results and take action on them in similar timeframes?"*

> *"This is terrible timing. I want to go live, in the real world for friends to
> begin testing, asap. Remove the 8/1 date - it was arbitrarily set by you."*

---

## Decision 1 — a three-tier latency budget, with measured numbers

Recorded in `docs/HOW_WE_WORK.md` §6a. Every figure is a timed run on the session
container (4 cores), not an estimate.

| Tier | What runs | Measured | Budget |
|---|---|---|---|
| Inner (every save) | the 10 static gate checks | **5.8 s** combined | ≤ 10 s — MET |
| Pre-push | inner + full pytest suite | 49.7 s serial → **20.15 s** at `-n 4` | ≤ 30 s — met only with a dependency we do not declare (R-067) |
| Outer (PR) | two-seat model review · runner queue · real fetches | minutes | not 10 s, and must not pretend to be |

**The distinction the budget rests on** is *local computation* versus *another
party's clock*, not "fast checks vs slow checks". Conflating the two is how a
6-second job comes to be described as taking half an hour.

**Rule established: slow is a defect until proven to be someone else's clock.**
When a step exceeds its tier budget, profile it and name the line item. Never widen
the budget; never report queue time as run time.

**The three genuinely irreducible waits, named so they are not re-litigated:**
two independent non-Claude reviews (another company's inference latency — making it
faster by reading less is a gate relaxation, not an optimisation); the GitHub runner
queue (time-to-first-log is queue time, and on this very day it was pathological —
R-095); real fetches against venue servers (politeness delays, or we get blocked).

**Stated as NOT met, deliberately:** pipeline verification is still a 12-hour
scheduled period with a dead-man alarm. That is right for a nightly feed and wrong
for a red pipeline, and it is exactly how `import_structured.yml` stayed broken
across every scheduled run it ever had (R-054).

## Decision 2 — memoise the two subprocess-backed KPIs

`tools/kpi_report.py::_kpi_trust_gate` and `::_kpi_pytest_count` are now
`functools.lru_cache(maxsize=1)`.

**Why it is correct and not a shortcut:** a KPI run is ONE snapshot of ONE working
tree. The second call in a process spawned an identical subprocess against
identical bytes for an identical answer. `_kpi_pytest_count` is a nested
`pytest --collect-only` (~3.3 s) which, under pytest, is pytest collecting pytest —
six times per suite, it was the single largest line item in the repo's wall clock.

**Two properties deliberately preserved.** `lru_cache` does not cache *raises*, so
a transient subprocess failure still retries — a failure is never memoised into a
fact, and `test_a_failed_probe_is_never_memoised_as_a_fact` guards it against a
future cache that would. The call count is asserted, and the uncached form was
**proven red** (`first is second` fails) before the cached form was accepted green.

## Decision 3 — Step 4 (go live for friends) promoted to P0, ahead of Steps 5–7

Steps 6 and 7 measure the felt experience with real people; neither can begin
without a URL a stranger can open. Ordering measurement ahead of the thing being
measured was an error in the plan, corrected.

**Scope boundary held:** "go live asap" was **not** read as authorising a public
launch. Go-live is founder-crucial. The deliverable was the click-path, the
recommendation and the rejected alternatives — the founder still pushes the button.
(The founder did, at 17:10Z: the Vercel project now exists and deployed Ready on the
first attempt with zero environment variables.)

**Recommended path recorded, with the alternatives costed:** preview + a
Deployment-Protection bypass link. Rejected: production with
`NEXT_PUBLIC_AUTH_DISABLED=1` (the entire internet — a public launch wearing a
test's clothes, and founder-crucial); the full Clerk stealth gate (right before
public launch, overkill to unblock three friends tonight).

## Decision 4 — the Anthropic reset date is not a planning input

The API's own words are *"you have reached **your specified** API usage limits"* —
a founder-owned console cap raisable in about a minute. It had been reported across
four documents as though it were a fact of nature, once framed as favourable timing
for building. **No step of the v1 plan waits on a date.** Corrected in `docs/V1.md`,
`docs/V1_AUDIT_2026-07-26.md`, `TODOS.md`, `STATE.md` and the changelog.

## Decision 5 — record unverifiability rather than route around it

Two things this session could not verify, both written down as OPEN rows instead of
being softened or omitted:

- **R-067** — the 20.15 s pre-push number requires `pytest-xdist`, which is neither
  installed nor declared, so the loop the founder actually gets today is the 49.7 s
  one. Recorded as met-with-a-caveat, never as met. Ships with `docs/V1.md` Step 3's
  dev-requirements file, with two objective conditions before `validate` runs the
  suite parallel: three consecutive identical serial-vs-parallel pass/fail sets, and
  an unchanged exit code and check-name set. Parallelism must be a speed change,
  never a coverage change — otherwise it is a gate relaxation and founder-crucial.
- **R-068** — the agent cannot verify its own deployment. `/api/health` exists
  precisely so a deploy is verifiable without guessing, and the network policy
  denies both the `*.vercel.app` host and `vqipjlvzfiwnandjumvx.supabase.co` with a
  403 to CONNECT. Deployment *success* is confirmable via the head-SHA commit
  status; the site's *contents* are not.

## Correction recorded in the same commit as the fact that falsified it

I wrote *"there is no Vercel project linked to this repo — verified, no
`vercel.json`, no `.vercel/`, no deployment ever recorded."* True when written,
false an hour later. **The inference was never sound**: a Vercel↔GitHub link lives
in Vercel's dashboard and leaves no trace in the repo, so a project could have
existed all along. The conclusion happened to be right; calling it *verified* was
the defect. `false-confidence-gate`. **A repo check cannot answer a dashboard
question — the commit status on the head SHA can**, and that is what the docs now
point at.

---

## What was NOT decided here, and why

- **Ask 5 — the escape-alarm semantics.** A gate-threshold change. `validate` is red
  on it and PR #76 cannot merge, and the temptation to fix one's own blocker is
  exactly why this is founder-crucial. Untouched. Analysis:
  `docs/ASK_ANALYSIS_2026-07-26.md`.
- **Ask 3 — the auto-publish ratification.** Touches a trust invariant. The founder's
  message quoting my own scope paragraph could be read as authorising Step 2; it was
  deliberately not read that way, because resolving an ambiguity about a trust
  invariant by assuming consent is precisely what the charter forbids. Analysis:
  same document, including a correction — a rollback path **does** partially exist
  (`set_event_confidence` / `mark_event_disputed`, audit-logged), contrary to what I
  told the founder earlier.

---

**Codified by:** `docs/HOW_WE_WORK.md` §6a (the three-tier budget); `tools/kpi_report.py` lru_cache + `tests/test_kpi_report.py` (the memoisation, proven red first); `.github/workflows/site_health.yml` (deployment verification without a founder interrupt); `docs/RECORD.md` R-067/R-068/R-069.
