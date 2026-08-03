# UI/UX Design Session — Kickoff Prompt (paste into a fresh session)

Written 2026-08-03 per founder request, following `docs/ops/HANDOFF_STANDARD.md`.
Scope: the /tonight experience layer ONLY. A parallel session owns the
sourcing/ingestion engine (branch `claude/1live-session-kickoff-uvviqi`,
PR #150) — do NOT touch `worker/`, `tools/import_sources.py`, or
`sources/markets/` in this session; UI work lives in `web/` + `docs/design/`.

---

## PASTE FROM HERE

You are continuing the 1Live UI/UX design effort. STOP — before any work:

1. **Open ritual.** Run `python tools/session_reconcile.py`, then read
   `docs/SESSION_START.md`, `STATE.md` (trust it only after reconcile is
   clean), `docs/OPERATING_RULES.md` IN FULL — especially §4a (never build
   without a presented plan: what/how/why/why-it-matters/expected-outcomes)
   and §6a (NO timers/send_later ever — webhooks and real triggers only;
   non-user-facing content does not circle through review loops).
2. **Read the design canon IN FULL** (complete files, no skimming — Rule
   Zero): `docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md` (RATIFIED, the
   single source of truth), `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md`
   (ratified canon: trust display rules, Spark Line waterfall, Emotion Glyph,
   Descriptor Foundry, behavioral architecture), and skim
   `docs/memory/` decisions dated 2026-07-25 onward for design rulings.
3. **Know what is BUILT vs NOT** (verified 2026-08-03, do not re-litigate):
   - BUILT and live: two-door card (artist+venue), slide-out lens,
     progressive disclosure, three-tier date buckets, contextual preview
     ("Hear them"/"Watch a talk"/… — honest name-searches, null for
     unpreviewable types), trust display (no badges, disputed always shown),
     image-less domain-hued cover band, venue contact/map links. PRs #127,
     #130, #131, #147; ~1,400 real events render from licensed_event ∪ event.
   - RENDER-READY but EMPTY: Spark Line (content layer #148 merged; shows
     nothing until generation + identity enrichment land — owned by the
     OTHER session; do not build generation here, but DO design/refine the
     empty-state so cards without a Spark Line read as finished).
   - NOT BUILT: Emotion Glyph, real venue photos/character, nearby
     street-map, voice navigation, Anticipatory Greeting.
   - NOT VERIFIED (standing quality gaps): WCAG 2.2 AA audit, CWV budgets
     (brief demands < 2.0s load — stricter than LCP 2.5s), visual-regression
     baselines (R-002 in docs/RECORD.md: trigger FIRED, a deployed URL
     exists — this is queued work, not optional).
4. **Open PRs in your lane** (review, then drive or close honestly):
   #145 (user-journey lifecycle canon — the design spine, likely
   merge-worthy), #112 (frictionless/automagical nav spec v1, PROPOSAL —
   the founder's "no friction, smooth as smooth can be" mantra; needs
   founder ratification via ONE consolidated question set, then
   implementation on /tonight).

## Mission (priority order, founder-adjustable)

1. **Visual-regression baselines (R-002)** — the fired trigger. Wire
   `tools/visual_regression` against the deployed preview; commit baselines;
   turn the standing validate SKIP green.
2. **WCAG 2.2 AA + CWV verification** — audit the live /tonight against the
   brief's bars; fix violations; make both mechanically checked (CI or a
   documented repeatable run), not asserted.
3. **Frictionless-nav implementation** (after founder ratifies #112):
   URL-addressable lens/modal over preserved feed state, Back closes the
   sheet before leaving, scroll restoration, external-link-by-intent with
   labeled handoff, skeletons-not-spinners.
4. **The content-slot designs** for what the sourcing engine will fill:
   Spark Line placement polish, Emotion Glyph spec→build (needs founder
   gap ratification G-EG first — ask, don't assume), venue
   photo/character slot with honest empty states.
5. Every design-derived PR gets the evaluator pass against the brief's
   8-criterion rubric; deltas from the brief are logged, never silent.

## Hard rules (violations have burned trust before — do not repeat)

- Disk is truth. Update STATE.md + TODOS.md + docs/ONE_LIVE_CHANGE_LOG.md
  at session close; `python tools/staleness_check.py` must pass.
- `bash tools/validate` green before any PR. Trust display rules are
  physics: NO badges, NO "confirmed" text, disputed shown-never-hidden,
  low-confidence = quiet icon → dismissible sheet + venue link.
- Never claim something is "done/live/in canon" without proof (a link, a
  run id, a commit SHA on origin). Canon = merged to master, nothing less.
- Work on YOUR designated branch only. Do not modify `worker/`,
  `sources/markets/`, `tools/import_sources.py`, or anything the sourcing
  session owns (its PR is #150). Shared docs (STATE.md, TODOS.md,
  changelog): append, never rewrite others' entries; merge conflicts are
  yours to resolve cleanly.
- Founder communication: plain language, why-this-not-that, honest
  tradeoffs, direct links, ONE consolidated question list.

Begin with the open ritual, then present your plan per OPERATING_RULES §4a
before building anything.

## PASTE ENDS HERE
