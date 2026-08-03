# Session arc — 2026-08-03 — /tonight quality gates: R-002 real, WCAG/CWV mechanical (Contract #39 — renumbered from #35 at the master merge; #34–#38 were independently assigned)

## Contract
Kickoff-directed UI/UX lane (branch `claude/1live-ui-ux-design-xkk986`), mission
priority order: (1) R-002 visual-regression baselines — the FIRED trigger;
(2) WCAG 2.2 AA + CWV verification, mechanical not asserted; (3) drive lane PRs
(#145 merge-worthy, #112 PROPOSAL → founder ask); (4) Spark Line empty-state
check. Full open ritual run first (reconcile exit-2 UNVERIFIED = env limit, PR
state re-verified via GitHub API; complete reads of STATE/OPERATING_RULES/
UI Canon/Brief v2.4/RECORD/TODOS + 2026-07-25+ decisions).

## The load-bearing design decision
R-002's trigger text said "capture baselines against the deployed URL" — but a
pixel gate over LIVE data flakes by construction (events change nightly, the
feed is clock-driven), and a gate that cries wolf proves nothing (§9.6 cuts both
ways). Resolution: a **SYNTHETIC QA fixture mode** — `ONELIVE_QA_FIXTURES=1`
only, fail-closed off everywhere else, fully fictional events (example.com
venues, reserved 555 numbers — asserting nothing about real entities), a frozen
clock (`QA_FROZEN_NOW_MS`), and a visible "SYNTHETIC QA FIXTURES" banner. The
fixture set exercises the trust physics on one screen: all four confidence
states (disputed shown-never-hidden), both Spark Line registers, free/unknown
price, on-now, all three density tiers. Determinism contract pinned in
`tests/visual_baselines/README.md`: data+clock · TZ=America/Chicago on server
AND browser · Chromium build 1194 (= Playwright 1.56.0, discovered by mapping
npm tarballs' browsers.json) · external hosts resolver-blocked.

## What happened
1. **Fixture mode + baselines.** `web/qa/fixtures.ts` (+13 vitest contract
   tests), fixture branches in the two /tonight pages, `FeedApp` `qaFrozenClock`
   prop. `tools/visual_check.sh` boots the production build and pixel-diffs 4
   pages (mobile/desktop feed, disputed detail — its open-by-default disclosure
   is pinned, cancelled detail). Determinism PROVEN: independent boot+capture =
   0/329160 px different.
2. **First baseline review caught a real defect:** the detail page rendered the
   raw category slug ("live-music") as "Kind" — fixed to `domainLabel`
   (the card already used it; surfaces must not drift).
3. **CI gate.** `.github/workflows/visual-regression.yml` fires on every
   web-touching PR; diverged candidates upload as artifacts. `tools/validate`
   now RUNS the check where a browser + web deps exist; browserless skip is the
   narrower R-068. R-002 → RESOLVED with evidence.
4. **Two CI reds on PR #152's own first head, both fixed same-session:**
   (a) ubuntu-24 runners ABORT Chromium (AppArmor blocks the unprivileged-userns
   sandbox; small /dev/shm) → capture/audit run `--no-sandbox
   --disable-dev-shm-usage`, proven pixel-identical locally; (b) the SCA gate
   caught a NEWLY PUBLISHED high advisory (brace-expansion GHSA-rgw5-rvv9-x895,
   time-based, not this diff) → fixed at the root via the R-048 overrides
   pattern (^5.0.9), `npm audit --omit=dev` = 0.
5. **WCAG + CWV.** `web/qa/audit.mjs` as leg 2 of the same boot: axe-core full
   A/AA tag set 2.0→2.2, SELF-FALSIFYING (must flag a planted-broken page or
   hard-fail), audits the lens-OPEN dialog state; lab LCP under pinned throttle
   (4× CPU, 1.6Mbps/150ms). Result: 0 violations everywhere incl. lens-open;
   LCP 228–372ms vs the brief's 2000ms bar. Honest residuals recorded: R-069
   (human keyboard/screen-reader pass owed before DNS cutover), R-070 (field
   CWV waits on the founder monitoring decision).
6. **PR #145 MERGED** `c992a99` (squash) per agent-merges-on-green: evaluator
   APPROVE + trust-gate green on final head `2f46514`, mergeable clean. The
   user-journey lifecycle canon + §4a plan-first + §4b API frugality are now
   master canon. (Note: the kickoff cited "§4a" before this merge landed it.)
7. **Spark Line empty state VERIFIED** — cards without a line read as finished
   (no gap, no filler); tier-B/C registers render per canon §4; pinned by the
   baselines. No change needed.
8. **Noticed + recorded, not silent:** live /tonight is DARK-only while brief
   §4 demands light+dark → R-071 (light theme + light baselines at the
   founder's post-canon design agenda).

## Findings
- GitHub's ubuntu-24 runners cannot run Chromium's sandbox (AppArmor userns
  restriction) — gotcha filed: `docs/memory/gotchas/2026-08-03_chromium-ci-apparmor-and-npm-cwd.md`.
- `npm i` with the wrong cwd silently creates a root package.json +
  node_modules — same gotcha file; deleted and reinstalled in web/.
- The sandbox env needed the documented heals again (pip deps, `git fetch
  --unshallow` for the smoke-run commit) — same class as Contract #23's notes.
- `tests/test_skip_record_binding.py` hardcoded R-002 as the expected binding
  row; updating it to follow the register (R-068) proved the binding tracks
  the register, not an id.

## Documents / artifacts
| Artifact | Location |
|---|---|
| Fixture mode + tests | `web/qa/fixtures.ts`, `web/qa/fixtures.test.ts` |
| Audit runner | `web/qa/audit.mjs` |
| Gate runner | `tools/visual_check.sh` (leg 1 pixels, leg 2 a11y/LCP) |
| Baselines + contract | `tests/visual_baselines/` (4 PNGs + README) |
| CI gate | `.github/workflows/visual-regression.yml` |
| validate wiring | `tools/validate` (visual_regression section) |
| Records | R-002 RESOLVED; R-068/R-069/R-070/R-071 opened |
| PR | #152 (this lane's work) · #145 merged `c992a99` |

## Open threads / next steps (ordered)
1. Drive PR #152 to green + merge per protocol (evaluator + all checks on final head).
2. Founder ask list (ONE list, in the close report): ratify #112 · G-EG · monitoring timing.
3. On #112 ratification: implement frictionless nav on /tonight.
4. R-069 human a11y pass at the deploy session; R-071 light theme at the design agenda.
