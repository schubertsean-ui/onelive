# Session close — 2026-07-27: the honest state of everything

Written at the founder's direction ("Finish and document everything so far").
No new code, no new tests, no new review rounds. This is the state of the work
as it actually stands, so the next session starts from truth instead of memory.

---

## 1. The one-line answer

**Twenty pull requests are open. Exactly one of them (#74) removes a defect the
founder actually reported. The other nineteen are internal tooling.** That ratio
is the finding of this session and it is the thing to fix first.

The founder's words, verbatim, 2026-07-27: *"Are you getting closer to go live
or spinning wheels?"* The measured answer was: spinning. Recorded here rather
than softened, because a stale self-assessment is how this happens again.

---

## 2. What is actually live (verified vs. claimed)

| Thing | State | How I know |
|---|---|---|
| Ingestion cron | ARMED, 20-min cadence on master | STATE.md, PRs #43/#44 merged records |
| Extraction certification | Done, end-to-end mechanical | STATE.md, PRs #36–#41 merged |
| Vercel deployment | Building/Ready on every PR | Vercel bot comments observed this session |
| Public site content | **NOT VERIFIED BY ME** | see below |

**The site content claim is unverified.** PR #80's title asserts "The site is
public with 1,532 events." I could not confirm it: this sandbox's outbound
proxy denies `onelive.vercel.app` (a `403` on CONNECT from the proxy itself,
not from Vercel — the request never left the container). Treat 1,532 as an
unconfirmed number until something re-derives it.

**Recommended fix, not yet built:** a GitHub Actions job that fetches the live
`/tonight` and asserts (a) HTTP 200 and (b) no known-outside venue appears in
the HTML. CI runs on GitHub's network, which has no such restriction. This
turns "is the site good" into a number that re-checks itself on every push,
and costs the founder nothing. The alternative — adding the domain to the
sandbox allowlist — costs a founder settings trip and only lets one agent look
once.

---

## 3. PR #74 — the only go-live blocker (branch `claude/handoff-review-2026-07-25-15ucin`)

The defect: *"If you show San Antonio you've failed."* Root cause was found and
is not in dispute — the importers scoped the market as a 75-mile circle around
downtown Austin, and San Antonio sits ~75 miles away, so Bexar County was inside
the query by construction. CAPCOG is ten named counties: bastrop, blanco,
burnet, caldwell, fayette, hays, lee, llano, travis, williamson.

**Landed and proven (commit `adc03a5`):**

1. A field containing only `"Bexar County"` — with no city in front of it — used
   to match nothing, come back UNKNOWN, and get rendered (the read path
   deliberately keeps unknowns so coverage gaps stay visible). Fixed in both
   `worker/region/capcog.py` and its generated TypeScript mirror
   `web/lib/region.ts`; generated vectors pin the two implementations together
   so they cannot drift.
2. `web/app/(public)/tonight/page.render.test.tsx` — a test bound to the page
   itself, not to the helper. The old test proved `filterToCapcog` was correct
   and would have kept passing if `/tonight` stopped calling it. Verified by
   deleting the filter call from the page: the test went red, and green again
   when restored.
3. `web/vitest.config.ts` — the page test needed a JSX transform. Vitest 4 ships
   rolldown-vite, whose transformer is **oxc**, not esbuild; `esbuild` options
   are silently ignored (it prints "esbuild options will be ignored" and then
   fails on unparsed JSX). The working setting is `oxc: { jsx: { runtime:
   "automatic" } }`. Recorded because it cost real time to find.

**NOT fixed — round 15's remaining blockers, in the reviewer's own terms:**

- `CLASS:outside-county-read-as-unknown` (4 findings:
  `worker/region/capcog.py:140` and `:267`, `web/lib/region.ts:35` and `:146`).
  "Outside" is currently decided from `KNOWN_OUTSIDE_COUNTIES`, a list derived
  from hand-picked neighbouring cities. CAPCOG is *defined* as ten counties, so
  a real Texas county nobody thought to list — Colorado, Gonzales — returns
  `None`, and `None` is KEPT and rendered. Same San Antonio class, different
  shape.
  **Designed fix, not written:** embed the 254 Texas counties. Then: in the ten
  → `True`; a real Texas county not in the ten → `False`; anything else →
  `None` (out-of-state or a typo — stays visible as a gap, honestly).
- `CLASS:contradictory-location-admitted` (`capcog.py:294`, `region.ts:178`).
  `row_verdict()` lets county evidence short-circuit, so
  `{venue_county: "Travis", city: "San Antonio"}` is admitted.
  **Designed fix, not written:** gather *all* location signals from every field
  and let OUTSIDE win over INSIDE, and INSIDE win over UNKNOWN. Surface the
  contradiction in `region_report()` so it becomes a worklist entry rather than
  a silent drop.
- `CLASS:test-codifies-bad-contract` (`tests/test_capcog_region.py:210`,
  `web/lib/region.test.ts:132`). Both suites currently *assert* the bypass above
  is correct behaviour. They must flip with the fix, or they will defend the bug.
- `CLASS:false-confidence-gate` (`STATE.md:137`,
  `docs/metrics/KAIZEN_LEDGER.md:13`). STATE.md still reads as though the
  denominator/TABC/coverage work shipped in this PR; it was split to other
  branches. The Kaizen row records 8 review rounds when the PR is at 15.
  Both are governance claims that outrun the facts — correct them.
- `CLASS:sca-unsuppressed-advisory` (`web.log:32`). **The reviewer is wrong on
  the facts, and the recurrence is my fault.** `GHSA-qx2v-qp2m-jg93` is a
  **moderate** postcss advisory, correctly recorded in `docs/SCA_BASELINE.md`
  under the moderate table; the gate blocks high/critical only, and
  `tools/sca_gate.py` reads per-advisory severity correctly. It *looks*
  unaccounted-for because it sits under a `postcss` heading whose rolled-up
  severity is high, and because the gate prints only the blocking advisories —
  so the evidence the reviewer reads is silent about it.
  **Durable fix, not written:** have `tools/sca_gate.py` also print the
  non-blocking advisories it saw with their per-advisory severity and
  disposition. Replying on the PR does not work — the reviewer reads the diff
  and logs, never the comments. This is added output only; it relaxes no
  threshold.

---

## 4. Every other open PR (all parked — no further review rounds)

| PR | Branch | What it is | Go-live? |
|---|---|---|---|
| #89 | literary-analysis-caching | Anthropic call-pattern directive record | no |
| #86 | source-scorecard-tool | Source status derived from evidence + trend | no |
| #85 | source-scorecard | Every ingestion source catalogued once | no |
| #84 | capcog-coverage-workflow | Coverage measured on every push | no |
| #83 | capcog-denominator | A real denominator for coverage | no |
| #82 | tabc-fetch | Real venue universe from TABC | no |
| #81 | reviewer-concurrency | Review lenses run concurrently | no |
| #80 | experience-metrics-step5 | v1 criterion 4 machinery | no |
| #79 | change-set-discipline | Change-set size as a gate | no |
| #78 | verification-canon | Verification as mechanism | no |
| #76 | onelive-v1-evaluation | Deep audit + canon simplification | no |
| #75 | universal-kernel-staging | Kernel v1 staged in-repo | no |
| #73 | onelife-meta-carousel | Contract #27 close records | no |
| #68 | moat-sources-importable | Curated sources importable | no |
| #57 | operating-discipline | OPERATING_DISCIPLINE doc | no |
| #56 | kaizen-m9 | Expected-vs-actual perf metrics | no |
| #55 | loop-harness-brain-review | Session bookkeeping | no |
| #50 | epiplexity-research | Research assessment | no |
| #48 | artist-owned-ai-agent | Research: the Owned Agent | no |

**Unread CI failures at close** (left deliberately, not missed):
- #86, head `d3b3fdd`, run `30221032833` — round 4. The openai seat found
  `partial-evidence-read-as-zero` in `tools/source_scorecard.py`: when `--rows`
  is not supplied, every row-derived metric still serialises as `0` (events,
  venues, unique_venues, attempts, attempts_ok, yield_per_attempt), so
  "not measured" is recorded and trended as "measured zero", and `--record`
  writes those fabricated zeroes into the history file. Also
  `malformed-history-read-as-empty`: a corrupt previous snapshot is read as
  "no baseline" instead of failing loud. The gemini seat approved; any-lens-red
  is red.
- #79, head `c36af81`, run `30221205504` — unread.
- #68, heads `787f1c8` and `863841e`, runs `30233387141` / `30234373612` — unread.

---

## 5. Standing blockers that need the founder (nothing else does)

1. **`ONELIVE_DB_DSN`** — the password is rejected by Supabase. This blocks the
   coverage percentage and any live DB read from a session. It is the only
   credential issue outstanding. Agents never mint keys.
2. **Nothing else.** No founder decision blocks the critical path.

---

## 6. Canon changes ratified this session

Three founder directives were codified into `CLAUDE.md` and
`docs/OPERATING_RULES.md` (on branch `claude/change-set-discipline-2026-07-26`,
PR #79):

1. **Execution bias.** Verbatim: *"I only want progress toward completion,
   solutions offered as prescribed to a problem, solutions executed by you 99%
   of the time."* Status reporting without progress is the failure mode named.
2. **The ten-minute ceiling.** Verbatim: *"I will not ever allow a delay of more
   than 10 minutes. Do not ask for longer delays."* Absolute: no wait, poll,
   watch interval or self-scheduled check-in may exceed ten minutes, and asking
   for longer is itself the violation. Overrides every other cadence rule,
   including the external-stall ladder in `docs/OPERATING_RULES.md`.
3. **Contradictions resolved at the source**, not stacked. Five were fixed:
   ambiguity now resolves to a written assumption instead of a question; the
   "options" rule is scoped to founder-crucial decisions only; the
   communication rules no longer claim to outrank brevity.

---

## 7. What the next session should do, in order

1. **Finish #74.** The two designed fixes in §3 are specified precisely enough
   to write directly. Flip the two tests that currently pin the bug. Correct the
   two stale governance claims. Add the SCA gate's non-blocking output.
2. **Build the live-site CI check** from §2. It is the cheapest thing on this
   list and it is the only one that measures the actual product.
3. **Do not reopen the nineteen tooling PRs** until the site is right.

---

## 8. The lesson, in the form the brain consumes

Red class candidate for `docs/memory/RED_CLASSES.md`:

> `CLASS:tooling-outruns-product` — work that measures or governs the build
> accumulating faster than work that changes what a user sees. Trigger: count
> open PRs that remove a user-visible defect versus those that do not. When the
> ratio falls below roughly one in three, stop and ship the product work first.
> Observed 2026-07-27 at 1:19.

Not committed as a gate rule, because a gate for this would itself be more
tooling. It belongs in the session-close review as a counted question.
