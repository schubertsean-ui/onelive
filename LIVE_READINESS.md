# OneLive — "Live" Readiness Assessment (verified 2026-07-12)

Ground truth, verified this session against the GitHub remote and the live
Supabase project `vqipjlvzfiwnandjumvx` — NOT summary claims.

## What is TRUE now (verified)
- **Master HEAD = a0b3724** (PR #8 merged this session: the agentic-harness
  buildout — validate gate, lint+hooks, personas, night-shift, quality
  instrumentation). CI trust-gate green.
- **PR #8 review findings all fixed + merged**: the validate silent-pass P1
  (SKIP/ADVISORY now => INCOMPLETE/exit 2, `--allow-skips` to acknowledge),
  visual_regression shell-injection P1, and four P2s. Suite 127 passed / 27
  skipped.
- **DB migrations: 9 applied and current** — 0001-0007 + 0009 (source_name_unique)
  + source_geo_coverage. The RLS + narrowed-public-read migrations
  (0006/0007) are ALREADY LIVE (the prior "pending 0005/0006/0007" note was stale).
- **source = 230 rows** in the live DB.

## What BLOCKS "OneLive live" (verified gaps)
1. **Zero events.** `event = 0`, `event_candidate = 0`, `candidate_evidence = 0`.
   A consumer feed with no events is not "live". Populating these requires
   running a real ingestion pipeline (fetch -> extract -> gate -> promote) over
   the 230 sources.
2. **No real orchestrator on master.** `worker/run_once.py` is only a STUB smoke
   test (hardcoded text, stub AI provider). The real 3-way PASS/HOLD/ESCALATE
   orchestrator lives on **PR #7 (feat/orchestrator-harness, OPEN, unmerged)**,
   along with the /tonight feed UI and the 193->real-source work. Master cannot
   ingest real data until #7 (or equivalent) lands.
3. **GAP 1 (azp/CSRF) cannot be closed from here.** It targets
   `api/clerk_auth.py`, which does NOT exist on master or on ANY remote branch.
   It lives only in the user's Clerk stealth-gate commits (f970e3a, 1a9728d,
   35c5605 — Next 15 upgrade + two-layer fail-closed Clerk gate) that were
   authored on the OLD sandbox and were **never pushed** (remote
   feat/orchestrator-harness is at 3258a57, not the arc's 1a9728d). Pushing them
   is the user's step; this sandbox cannot reproduce or push them.
4. **Deploy not exercised.** No verified Vercel deploy of web/API from this
   session; and deploying an empty-feed app would be premature anyway.

## Honest conclusion
"OneLive live" is NOT achievable end-to-end from this sandbox in this session,
because the two things that would make it live — (a) a real ingestion run to
create events, and (b) the auth gate + Next 15 upgrade — depend on unmerged
PR #7 work and on 3 local commits that only exist on the user's old sandbox and
were never pushed. Fabricating events or a clerk_auth fix against files that do
not exist would be exactly the §1 "looks done but isn't" violation the whole
harness exists to prevent.

## The real critical path to live (for the user / next session)
1. Push the 3 local Clerk/Next-15 commits from the old sandbox to a branch
   (only the user can do this).
2. Land PR #7 (orchestrator + /tonight feed) into master — after its own review.
3. Close GAP 1 on api/clerk_auth.py (azp validation + tests) once that file is
   on master.
4. Run the real orchestrator over the 230 sources to populate event_candidate
   -> gate -> promote to event.
5. Deploy web + API to Vercel; verify /tonight renders real, gated events.
