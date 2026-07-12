# OneLive — Agent Instructions

## Architecture (do not deviate without a STATE.md note)
Pipeline: Sources -> Raw Fetch -> AI Extract -> Candidate Store -> Evidence -> Gate -> Promote -> Canonical Event -> `/tonight` API.
Every stage is independently auditable. The AI extraction step never publishes directly — everything passes through the gate.

Confidence states (4-state, confirmed decision — do not revert to a 3-state model):
`unverified` | `likely` | `confirmed` | `disputed`
Rule: disputed events are always shown as disputed, never deleted.

Stack:
- PostgreSQL 15 (via Supabase), project ref: vqipjlvzfiwnandjumvx
- Python/FastAPI + Celery workers (pipeline, matching engine)
- Claude API — used only for weak-signal extraction from raw fetched text, never to auto-publish
- Next.js 14 PWA (consumer feed + ops console)
- Clerk (auth)
- S3 (photo storage for Tastemaker posts)
- Stripe Connect (deferred until Phase 3 matching payments — not needed for v1 intro-only matching)

## Coding standards
- TypeScript strict mode everywhere in the Next.js app. No `any` without a comment explaining why.
- Every API endpoint validates input (zod or pydantic schema) before touching the DB.
- Parameterized queries only — never string-interpolate SQL.
- Auth checks required on every protected route (venue/creator claim actions, tastemaker posting, admin moderation).
- Tastemaker posts (opinionated human content) must NEVER touch the event candidate/gating/promotion pipeline. They are a fully separate trust category from verified event data. See STATE.md if this boundary is ever unclear.

## Review criteria for any PR you generate or review
1. Does it touch the promotion pipeline or auth? If yes, flag for a deeper review pass, not the fast default pass.
2. Are confidence-state and moderation-state transitions covered by a test in `tests/test_gates.py` (or the tastemaker-post equivalent)?
3. Does it introduce a new external dependency? If yes, note it in STATE.md.

## Where to look first
**Run `docs/SESSION_START.md` before starting any session.** It reconciles STATE.md
against live ground truth (git/PRs/DB via `tools/session_reconcile.py`) so you can
trust it, then routes you to STATE.md (what's done/next), the latest session arc
(how we got here), and `docs/OPERATING_RULES.md` (how we work). Do not trust
STATE.md until the reconcile step is clean. Update STATE.md and re-run the
reconciler at the end of every meaningful session.
