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

**Denominator: BUILT (2026-07-26).** 69 target venues — Travis 65, Hays 2,
Williamson 2, and **the other seven counties zero**. That is layer 1 (our own
curated catalog) — a FLOOR, not the market universe. TABC is layer 2 and ships
here; Places is layer 3. **The numerator still needs a database read**, which
runs in the `CAPCOG Coverage` workflow once this branch merges.

---

## STATUS AT A GLANCE

| # | Step | State | Blocked by |
|---|---|---|---|
| 0 | CI / GitHub Actions working | 🟢 RECOVERED ~15:21Z | — |
| 1 | Region correctness (no out-of-market venues) | 🟡 Built + ENFORCED on the read path | PR #74 → needs review |
| 2 | **CAPCOG venue denominator + coverage measurement** | 🟡 Layer 1 built (69), TABC shipped | Merge, then run the workflow |
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

## STEP 0 — CI *(RESOLVED 2026-07-26 ~15:21Z)*

**What happened:** every Actions job from ~02:21 to ~15:21 failed in 2 seconds
with no runner assigned (`runner_id: 0`, no logs) — GitHub never started them.
Six consecutive failures across two branches, three commits and a manual re-run.
Resolved on the founder's side; jobs have run normally since 15:21Z.

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
2. **Enforce on the read path** — DONE. `web/lib/region.ts` filters every event
   before render: known-outside places are dropped, unrecognised ones are kept
   and counted (silently discarding them would hide a coverage gap while making
   the feed look cleaner). The boundary data is GENERATED from the Python source
   so the server and the site cannot enforce two different markets.
3. **Replace the radius in the importers** with county-scoped queries, so we
   stop *fetching* out-of-market data. *(Not yet built.)*

**Owner:** me. **Founder action:** none.

---

## STEP 2 — Build the denominator *(LAYER 1 + TABC DONE; founder chose TABC)*

**This is the highest-value item on the plan.** Without it, "coverage" is
unmeasurable and nobody can say whether the product is ready.

**Built already:** `tools/capcog_coverage.py` reports region correctness and
coverage — and **refuses to print a percentage without a real target list**,
because grading against the venues we happen to hold is self-scoring (100% of
what we found is what we found) and would read as success.

**Built.** Layer 1 (69 venues) comes from the curated catalog and needed no
source decision. Layer 2 is TABC (`tools/fetch_tabc_capcog.py`), founder-chosen
and shipped. Layer 3 (Places, founder's existing key) covers the venue types a
liquor licence cannot see — theatres, museums, libraries, all-ages rooms.

**To get the number:** merge PR #74, then run the **CAPCOG Coverage** workflow
(`.github/workflows/capcog-coverage.yml`, manual dispatch). It fetches TABC,
builds the target list, reads distinct ingested venues from the database, and
prints coverage per county. The workflow must be on the default branch before
GitHub will dispatch it — which is why the merge comes first.

**The figure always travels with its limits:** the report prints `FLOOR, NOT THE
MARKET UNIVERSE` and names the layer set whenever the denominator declares
itself incomplete, and a catalog-only run uploads under a different artifact
name so it cannot later be quoted as a full measurement.

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

1. ~~Unblock GitHub Actions~~ — DONE 2026-07-26
2. ~~Choose the denominator source~~ — DONE, founder chose TABC; shipped
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
