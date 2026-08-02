# FINAL 1LIVE — AUTHORITATIVE TECHNICAL SPEC (v1)

## 1) Handoff Memo

- Build DB first, then import sources, then ops + public API, then UI, then mobile.
- AI proposes candidates; publish requires multi-confirm anchors or corroboration.
- No auth/paywall bypass. Restricted data via partner feeds, OAuth, claimed uploads, opt-in email.

## 2) Business Plan (Operational)

- Revenue:
  - Venue SaaS ($49–$199/mo)
  - Festival/city integrations ($25k–$250k/contract)
  - API licensing (usage-based + minimums)
  - Premium user subscriptions ($4.99/mo)
  - Contextual local advertising (restaurants/bars/hotels/transport/tourism) with strict non-influence rules.

## 3) Architecture

Sources -> Raw Fetch -> Candidate -> Evidence -> Gate -> Canonical Event -> /tonight

## 4) Ranking & Sources

- Priority scoring model in `worker/source_rank.py`
- Master catalog in `sources/master_sources_catalog_120.json` (imported into DB)

## 5) Build Order Commands

- `docker compose up -d` (legacy local-dev fallback; production uses Supabase — see note in STATE.md)
- `bash db/apply_schema.sh` (legacy local-dev fallback)
- `python tools/import_sources.py --json sources/master_sources_catalog_120.json`
- `uvicorn api.main:app --reload --port 8000`
- `python worker/run_once.py`
- `cd web && npm i && npm run dev`
- `cd mobile && npm i && npx expo start`

**Note:** This document is the original reference build spec (v1). The actual 1Live repo uses Supabase-managed Postgres (`supabase/migrations/`) rather than local Docker Postgres + `db/apply_schema.sh` for schema management — see `STATE.md` for the authoritative current architecture and deviations from this reference.
