# UI/UX Design Session — Kickoff Prompt (paste into a fresh session)

Rewritten 2026-08-03 at the close of Contract #39 (UI/UX quality-gates +
ratification session), per `docs/ops/HANDOFF_STANDARD.md`. The previous
version of this file was that session's own kickoff — fully executed, all
mission items DONE (see STATE.md Contract #39). Scope: the /tonight
experience layer ONLY. A parallel session owns the sourcing/ingestion engine —
do NOT touch `worker/orchestrator.py`, `worker/sourcing/`,
`worker/autopromote.py`, `tools/import_sources.py`, or `sources/markets/`;
this lane lives in `web/` + `docs/design/` (+ `worker/glyph/` and the
display side of `worker/descriptor/`).

---

## PASTE FROM HERE

You are continuing the 1Live UI/UX design effort. STOP — before any work:

1. **Open ritual.** Run `python tools/session_reconcile.py`, then read
   `docs/SESSION_START.md`, `STATE.md` (trust only after reconcile is clean),
   `docs/OPERATING_RULES.md` IN FULL. Two things changed 2026-08-03 you must
   not miss: (a) **plan-first is now MECHANICAL** — `.claude/settings.json`
   hooks print a [plan-first] banner at session start and a PreToolUse gate
   DENIES product-file edits unless STATE.md carries an OPEN Session Contract
   with the five plan fields (WHAT · HOW · WHY · WHY-IT-MATTERS · EXPECTED
   OUTCOMES) — write your contract FIRST (proven live: the gate fired in the
   #39 session); (b) CLAUDE.md is now **charter v3** (~70 rules, §0
   precedence) — read it fresh, do not assume older text.
2. **Read the design canon IN FULL (Rule Zero):**
   `docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md` (RATIFIED, single source of
   truth) · `docs/design/ONE_LIVE_FRICTIONLESS_NAV_v1.md` (**RATIFIED
   2026-08-03**, the navigation standard — first wave implemented, see below)
   · `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` · skim
   `docs/memory/decisions/` 2026-08-02 onward.
3. **Contract numbering:** #34–#39 are taken (parallel lanes collided once;
   the fix is renumber-on-merge). Check STATE.md for the highest number.

## What is BUILT and PROVEN (2026-08-03 close — verify, don't re-litigate)

Carried by PR #152. **FIRST TASK: verify #152's state** —
`git log --oneline origin/master | head -5`. If it is MERGED, confirm the
production deploy serves the new nav (open a card → the URL becomes
`/tonight/<id>` → Back closes the sheet) and that Speed Insights (founder
purchased + enabled 2026-08-03) shows field data — then annotate R-070 that
field CWV is live. If it is still OPEN, drive it to green + merge per the
agent-merges-on-green protocol (its last state: all checks green on the
pre-merge head; a master-merge conflict resolution pushed after, CI
re-running on that final head).

- **Visual regression is a REAL gate (R-002 RESOLVED):** synthetic fixture
  mode (`web/qa/fixtures.ts`, `ONELIVE_QA_FIXTURES=1`, fail-closed, frozen
  clock, visible banner) · `tools/visual_check.sh` (pixels + a11y/LCP, one
  boot) · 4 baselines in `tests/visual_baselines/` (its README = the
  determinism contract: TZ America/Chicago on server AND browser; Chromium
  build 1194 = Playwright 1.56.0; external hosts resolver-blocked) ·
  `.github/workflows/visual-regression.yml` fires on every web PR · validate
  runs it for real where a browser exists (R-068 = the browserless skip).
  **An intended visual change = recapture with `--update` in the SAME PR.**
- **WCAG 2.2 AA machine subset + lab LCP:** `web/qa/audit.mjs` (axe, full
  A/AA tag set, self-falsifying against a planted-broken page, audits the
  lens-OPEN dialog; throttled lab LCP vs the 2000ms bar — last measured
  228–372ms). Residuals: R-069 (human keyboard/screen-reader pass owed
  BEFORE DNS cutover), R-070 (field CWV — see task 1).
- **Frictionless nav, first wave (spec §12):** history-modeled
  URL-addressable lens — Back closes the sheet before leaving the feed
  (`web/lib/nav.ts` + FeedApp) · filters-in-URL · same-tab labeled ticket
  handoffs ("· finishes on <host>") · aria-labeled external links (the
  mechanical gate `web/qa/link-policy.test.ts` enforces §13.1) · skeleton
  `loading.tsx` (zero-CLS, anti-blink).
- **Emotion Glyph ENGINE (G-EG ratified):** `worker/glyph/` — deterministic
  Plutchik→lexicon (24 + 5 sanctioned dyads), banned rating-family tested,
  creator override wins, provenance stamped. Display gated on R-072.
- Merged this lane same day: **#145** (user-journey canon + OPERATING_RULES
  §4a/§4b), **#112** (nav spec, status flipped RATIFIED).

## The remaining work queue (priority order; greenlit unless marked FOUNDER)

1. **Verify/drive #152** (above), then the production nav + field-CWV checks.
2. **Spark Line ✳ tap-to-dismiss sheet** (zero-spend, this lane; TODOS
   Contract-#33 remainder (a)): the §4 disclosure sheet for tier-C lines —
   SparkLineView's ✳ currently carries title/aria only, not the one-tap
   sheet the canon specifies.
3. **Frictionless-nav second wave** (spec §9.1 remainder): prefetch-on-intent
   for in-viewport cards; feature-detected View Transitions
   (reduced-motion-guarded); a documented §13.2/§13.3 scroll-restoration +
   bfcache QA pass against the live deploy.
4. **R-069** — human keyboard + screen-reader pass over feed/lens/detail
   (attended), BEFORE the 1Live.co DNS cutover; fix or record findings.
5. **R-071 light theme** — the live app is dark-only; brief §4 requires
   light+dark. Ship light mode + light baselines in the same PR.
6. **R-072 Emotion Glyph display half** — needs: the ~29-glyph SVG art set
   (FOUNDER design agenda) · the real description→Plutchik mapper (FOUNDER:
   model spend, cap first) · creator descriptions (claim-flow build).
7. **Contextual preview upgrade** (UI Canon §13 Phase 2 item 1): music
   search-links → real embedded tracks — FOUNDER-GATED (music API key).
8. **Venue enrichment slots** (photo / character / specials) — data-gated
   (R-049); design honest empty states only as data lands.

## Founder-owned decisions (do NOT pick up)

Nav spec §15 (in-app ticketing partnership · native-wrapper trigger ·
Anticipatory-Greeting go-live) · music API key · glyph art-set commissioning
+ mapper spend · SENTRY_DSN minting (R-001) · DNS cutover timing (R-065).

## Failure memory (do not relearn)

- **Chromium on CI/root:** always `--no-sandbox --disable-dev-shm-usage`
  (ubuntu-24 AppArmor aborts the sandbox; proven pixel-identical). Gotcha:
  `docs/memory/gotchas/2026-08-03_chromium-ci-apparmor-and-npm-cwd.md`.
- **npm in the wrong cwd silently creates a root package.json** — the harness
  resets shell cwd between calls; verify `node_modules/<pkg>` at the intended
  path after any install.
- **Sandbox env heals (recurring):** `pip install pytest pydantic fastapi
  cffi cryptography PyJWT anthropic psycopg2-binary requests PyYAML` +
  `git fetch --unshallow`, else the python suite cannot run.
- **Baselines:** intended pixel change → `bash tools/visual_check.sh
  --update` + commit PNGs in the same PR; never widen the threshold.
- **Tag pushes are refused by this environment's git proxy** — arc tags stay
  local; don't burn time on it.
- **Parallel-lane merges:** KAIZEN_LEDGER / changelog / TODOS / STATE
  conflict at the tails — resolve chronologically keeping BOTH lanes'
  entries; contract numbers renumber-on-merge.

## Interaction contract (enforced)

Five-part comms (WHAT·HOW·WHY·WHY-IT-MATTERS·OUTCOMES) · ONE consolidated
founder ask list · NO timers/`send_later` (webhooks are the trigger) ·
non-user-facing failures never circle · proof over assertion (validate
evidence blocks, run ids, SHAs on origin; UNVERIFIED stated when unprovable) ·
disk is truth (STATE/TODOS/changelog/arc at close; `python
tools/staleness_check.py` must pass) · trust display is physics (no badges,
no "confirmed" text, disputed shown-never-hidden, feed never filters on
confidence).
