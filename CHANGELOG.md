# Changelog

## v1.0

- Postgres schema (via Supabase migrations) for sources, raw_fetch, candidates, evidence, events, audit log
- FastAPI ops + public endpoints
- Worker ingestion, AI extraction stub, multi-confirm gating, promotion, dedupe, reliability hooks
- Next.js Ops Inbox UI
- Expo mobile skeleton consuming /tonight
- 120-source master catalog scaffold with deterministic priority scoring model (ranks 1-41, 119-120 populated; 42-118 flagged as TODO expansion)
