# OneLive — GO-LIVE PLAN

**Written 2026-07-26 at founder direction.** Supersedes `LIVE_READINESS.md`
(2026-07-12) and `docs/SPRINT_LIVE_SITE.md` (2026-07-13), both of which are
stale. This file states what is DONE, what BLOCKS launch, and the exact action
required to advance each step — including which actions only the founder can
take.

**Definition of "live" used here:** a person in the Austin/CAPCOG area opens the
site, sees tonight's real events at real venues they can actually get to, and
the data is honest about what it does and does not know.

---

## THE ONE NUMBER THAT DECIDES LAUNCH

**CAPCOG venue coverage: `X of Y venues, by county`.**

Everything else is machinery. Until this number exists and is acceptable, the
site is not worth showing anyone — and until 2026-07-26 it did not exist. Event
counts ("85 → 168") are numerators with no denominator and cannot answer
"how much of the market is missing?"

**Current value: UNKNOWN — the denominator has not been built.** That is the
single highest-priority item on this plan (Step 2).

---

## STATUS AT A GLANCE

| # | Step | State | Blocked by |
|---|---|---|---|
| 0 | CI / GitHub Actions working | 🔴 **BROKEN** | Founder — Actions minutes/spend |
| 1 | Region correctness (no out-of-market venues) | 🟡 Built, not merged | PR #74 → needs CI |
| 2 | **CAPCOG venue denominator + coverage measurement** | 🔴 **NOT BUILT** | Founder — pick a source |
| 3 | Ingest breadth: cover the 10 counties | 🔴 7 of 10 counties at zero | Steps 1–2, then work |
| 4 | Importer correctness (empty vs failed vs corrupt) | 🟡 In review | PR #68 — 22 rounds, needs split decision |
| 5 | Scheduled ingestion (cron) | 🟢 ARMED on master | — |
| 6 | Extraction quality gate | 🟢 Certified | — |
| 7 | Public URL + deploy | 🔴 No public URL | Founder |
| 8 | Access gate (Clerk allowlist) | 🟡 Wired | Verify before public |
| 9 | Monitoring (Sentry + dead-man) | 🟡 Wired, keys needed | Founder — DSNs |
| 10 | Founder go/no-go | 🔴 | All above |

Legend: 🟢 done · 🟡 partial · 🔴 blocking

---

## STEP 0 — Unblock CI *(founder, ~2 minutes)*

**Problem:** every GitHub Actions job since ~02:21 today fails in 2 seconds with
no runner assigned (`runner_id: 0`, no logs). Two attempts, identical. This is
not a code failure — GitHub never started the jobs. Almost certainly Actions
minutes exhausted or a spending limit reached.

**Why it blocks everything:** no PR can merge without green checks, so every
item below is frozen.

**Action (founder):**
1. Open https://github.com/settings/billing
2. Check **Actions minutes** used this month, and whether a spending limit is capping them.
3. Either raise the limit, or tell me the reset date and I will plan around it.

**Cost note, honestly:** tonight burned an unusual amount — PR #68 alone ran
~22 review rounds at ~7 min each. I over-consumed this. Step 4's split
recommendation exists partly to stop that pattern.

---

## STEP 1 — Region correctness *(built; needs CI)*

**Problem it fixes:** the feed showed San Antonio. Root cause was not bad data —
`ticketmaster.py` and `seatgeek.py` request a **75-mile circle around downtown
Austin**, and San Antonio is ~75 miles away, so Bexar County was inside the
query by construction. Recorded as R-025 in July and deferred; that deferral
was wrong.

**Done (PR #74, pushed):** `worker/region/capcog.py` defines CAPCOG as its **ten
named counties** — Bastrop, Blanco, Burnet, Caldwell, Fayette, Hays, Lee, Llano,
Travis, Williamson — with their named towns, and explicitly excludes Bexar,
Comal, Guadalupe and Bell. Membership is tri-state (in / out / unknown) so an
unrecognised town is a worklist item, never a silent guess. 11 tests.

**Remaining in this step:**
1. Merge PR #74 (needs Step 0).
2. **Enforce on the read path** so an out-of-region row cannot reach `/tonight`
   however it was ingested. *(Not yet built.)*
3. **Replace the radius in the importers** with county-scoped queries, so we
   stop *fetching* out-of-market data. *(Not yet built.)*

**Owner:** me. **Founder action:** none.

---

## STEP 2 — Build the denominator *(BLOCKED ON ONE FOUNDER DECISION)*

**This is the highest-value item on the plan.** Without it, "coverage" is
unmeasurable and nobody can say whether the product is ready.

**Built already:** `tools/capcog_coverage.py` reports region correctness and
coverage — and **refuses to print a percentage without a real target list**,
because grading against the venues we happen to hold is self-scoring (100% of
what we found is what we found) and would read as success.

**Missing: the venue list itself.** It needs an authoritative enumeration of
venues in the ten counties.

**Founder decision — pick one:**

| Option | Cost | Quality | My view |
|---|---|---|---|
| **TABC licensed premises** (`data.texas.gov`) | Free | County-tagged, authoritative for bars/music venues; misses non-alcohol venues (theatres, museums, libraries) | **Recommended** — start here, supplement later |
| **Google Places** | Paid, needs API key | Broadest venue types | Better coverage, real cost, founder-crucial spend |
| **Manual seed list** | Your time | Exactly the venues you care about | Fastest to *something*; not a true denominator |

**Say "use TABC"** (or name another) and I will build the fetcher, run it where
egress works, and return: **X of Y CAPCOG venues covered, broken out by county.**

**Note:** the dev sandbox has no outbound network (proxy 403), so this fetch
runs in GitHub Actions — which means Step 0 must clear first.

---

## STEP 3 — Close the coverage gap *(the actual product work)*

**Known now:** of the ten counties, **seven currently have zero coverage** —
Bastrop, Blanco, Burnet, Caldwell, Fayette, Lee, Llano. Only Travis, Williamson
and Hays appear at all.

**Also known:** 55 of 64 curated sources yield nothing, because the long tail of
venues publishes by **newsletter**, not by machine-readable feed.

**Actions:**
1. Measure against the Step-2 denominator to find *which* venues are missing.
2. County-scoped importer queries (from Step 1) to stop missing outer counties.
3. The newsletter path — needs a dedicated email address (founder).

**Owner:** me, once Step 2 gives a target. **Founder action:** a dedicated email
address for venue newsletters and API signups.

---

## STEP 4 — Importer correctness *(decision needed)*

PR #68 fixes a real class of defect: a source that was denied, throttled, or
served corrupt data was reported as "no events" — data loss reading as an empty
calendar.

**It has taken 22 review rounds and is not converging.** Rounds r17–r22 kept
finding the same family on a new path each time. Root cause: every reader in
`structured_feed.py` returns `[]` on unparseable input, which is the inverse of
what the fix needs.

**Founder decision:** split the empty/failure/corrupt semantics into a small
dedicated PR (my recommendation), or keep pushing rounds on #68.

**Cost of continuing:** each round is ~7 CI minutes plus an evaluator call, and
the trend is worsening (blockers went 2 → 5 → 2 → 2 → 1 → 6).

---

## STEP 5 — Scheduled ingestion 🟢

Cron is armed on master (`ingest.yml`, every 20 minutes) with a dead-man switch
and per-run source caps. **No action.** Note it cannot run while Step 0 is broken.

---

## STEP 6 — Extraction quality gate 🟢

Certified via an attended exam (0.63% hallucination, 97.82% recall). Locked so a
drifted harness fails closed. **No action.**

---

## STEP 7 — Public URL + deploy *(founder)*

Vercel preview deploys are green. There is **no public URL**, so nothing can be
shared and no claim about "the site works" can be verified from outside.

**Action (founder):**
1. https://vercel.com/sss-projects-e4775771/onelive → Settings → Domains
2. Assign a production domain.
3. Send me the URL — I will run the shareability check against the *rendered
   page*, not against metadata.

---

## STEP 8 — Access gate

Clerk allowlist gating is wired. Before any public URL exists, it must be
verified that a non-allowlisted visitor is actually refused — fail-closed, tested
against the live deployment, not assumed.

**Owner:** me, once Step 7 gives a URL.

---

## STEP 9 — Monitoring *(founder mints keys)*

Sentry (web + API + worker) and a healthchecks.io dead-man ping are wired but
inert without credentials. **No scheduled loop should run in production without
both.**

**Action (founder):** mint `SENTRY_DSN` and `ORCHESTRATOR_PING_URL`.

---

## STEP 10 — Go / no-go *(founder)*

Launch when: coverage (Step 2) is acceptable to you · zero out-of-region venues
(Step 1) · the public URL serves real rendered events (Step 7) · the access gate
refuses non-allowlisted visitors (Step 8) · monitoring is live (Step 9).

---

## CONSOLIDATED FOUNDER ACTION LIST

Everything only you can do, in priority order:

1. **Unblock GitHub Actions** — https://github.com/settings/billing *(blocks everything)*
2. **Choose the denominator source** — say "use TABC" or name another *(blocks the launch metric)*
3. **PR #68** — split, or keep pushing rounds
4. **Public URL** — assign a Vercel production domain
5. **`SENTRY_DSN` + `ORCHESTRATOR_PING_URL`** — monitoring
6. **A dedicated email address** — unlocks the newsletter long tail and API signups
7. **`OPENAI_API_KEY` in the session environment** — lets me run the reviewer before pushing instead of after; would have cut most of PR #68's rounds
8. *(Deferred — carousel/marketing, not launch-blocking:)* Meta credentials, `ONELIVE_APPROVAL_KEY`, posting-posture ratification

---

## HOW TO KEEP ME ON TARGET

Written at founder request. The existing ruleset is large and covers *how* to
work; it does not say *what matters most*, which is how I ended up optimising
review rounds instead of coverage. Three rules would have prevented it:

1. **One ranked objective, stated in `STATE.md`.** Today it should read: *"Maximise
   CAPCOG venue coverage; everything else is subordinate."* Any work item that
   does not advance the top objective needs a one-line justification before it
   starts.
2. **A round ceiling.** If a PR exceeds N review rounds (suggest 5), stop and
   escalate rather than continue. I hit 22.
3. **A denominator rule.** No coverage or progress metric may be reported as a
   bare numerator. If there is no denominator, the first task is to build one.
