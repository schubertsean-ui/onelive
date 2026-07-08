# One Live (v1) — Build-Ready MVP

One Live is a truth-first live entertainment discovery platform. AI proposes candidates; publication requires multi-confirm evidence or trusted claims. No pay-to-play ranking. No bypassing login/paywalls/bot protections.

## Stack

- DB: Supabase-managed Postgres (see `supabase/migrations/`)
- API: FastAPI (Python)
- Worker: Python (ingestion + candidate gating)
- Web (Ops UI): Next.js 14 (App Router)
- Mobile: Expo + React Native
- Source registry: JSON seeds imported into DB

## Quick Start (Local Dev)

1) Apply schema (via Supabase migrations — see `STATE.md` for the `apply_migration` workflow, or run against a local Postgres using the SQL files directly):
   ```
   # Each file in supabase/migrations/ can be run in order against any Postgres 14+ instance
   ```
2) Import sources:
   ```
   python tools/import_sources.py --json sources/master_sources_catalog_120.json
   ```
3) Run API:
   ```
   pip install -r api/requirements.txt
   uvicorn api.main:app --reload --port 8000
   ```
4) Run worker smoke test:
   ```
   pip install -r worker/requirements.txt
   python worker/run_once.py
   ```
5) Run Ops UI:
   ```
   cd web
   npm i
   npm run dev
   ```
6) Run Mobile:
   ```
   cd mobile
   npm i
   npx expo start
   ```

## Key Endpoints

- `GET /tonight?city=Austin`
- `GET /events?limit=50`
- Ops:
  - `GET /ops/candidates/inbox`
  - `GET /ops/candidates/{id}`
  - `POST /ops/candidates/{id}/evidence`
  - `POST /ops/candidates/{id}/promote`

## Policies (Non-negotiable)

- Do not bypass login/paywalls/bot protections.
- For restricted sources: partner feed, OAuth, claimed uploads (ICS/CSV), opt-in email forwarding.
- Social is evidence/weak signal unless claimed or anchored.

## Docs

See `CLAUDE.md` for coding standards, `STATE.md` for current build status and architecture decisions, and `docs/Final_ONE_Live_Authoritative_Technical_Spec.md` for the original reference spec.
