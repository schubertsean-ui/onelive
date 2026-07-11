# Session Arc — 2026-07-10 — Build Assessment & Session-Arc System

- **Session focus:** Assess where the OneLive build actually stands, define the best next steps with reasoning/tradeoffs, and stand up a durable session-arc system (Loops & Harness).
- **Status at close:** Infrastructure and code substrate are complete and well-engineered, but **the pipeline has never run on real data** — every table is empty. The bottleneck is no longer building; it's turning the machine on.

## Ground-truth snapshot (reconciliation result)

Verified live on 2026-07-10, not read from docs.

| Dimension | Verified state |
|---|---|
| Repo (`origin/master` HEAD) | `fc20386` — "Narrow event public-read RLS policy (migration 0007) (#3)" |
| PRs | #1 (feed pipeline hardening), #2 (RLS + pg_trgm), #3 (narrow event read) all **MERGED**; **#4 (source-trust scoring, migration 0008) is an open DRAFT** |
| Migrations applied (live project `vqipjlvzfiwnandjumvx`) | 0001, 0002, 0003, 0004, 0005 (pg_trgm), 0006 (RLS), 0007 (narrow event read) — **all applied** |
| DB data (row counts) | `source`, `venue`, `artist`, `event`, `event_candidate`, `raw_fetch`, `source_reliability` — **all 0 rows** |
| Security advisors | Only INFO-level `rls_enabled_no_policy` on the 11 service-role-only tables — **intentional/benign**, not real issues |
| Services | GitHub ✅ · Supabase ✅ (ACTIVE_HEALTHY, Postgres 17.6) · Vercel ✅ · Clerk ✅ |

## Decisions (what + why + tradeoffs)

- **Next priority = prove the pipeline end-to-end on real data (one city: Austin).** Import the 43-source catalog into the live DB, wire one real AI provider (Claude API per spec §14, replacing the `stub`), and build the missing orchestrator that loops the sources so `fetch → extract → gate → promote → /tonight` runs on real events.
  - Why: this is the difference between "we have code" and "we have a product." It validates the confidence model, dedupe, and fuzzy resolution against messy reality — where they'll actually break.
  - Tradeoff: least glamorous work, touches AI cost/rate limits. But skipping it leaves every downstream feature untestable.
- **Finish & merge PR #4 (source-trust scoring / migration 0008) alongside the import.** It's Wave 2's "load-bearing wall" and already in flight.
  - Why: retrofit scoring onto a populated `source_reliability` table is far messier than doing it before data lands.
  - Tradeoff: minor sequencing tension with the import, but they're complementary (import → score).
- **Defer the visible-trust UI (Wave 1: #42 last-verified, #43 report/correct, #41 DoD KPIs) until the pipeline is live.**
  - Why: an inaccurate "last verified" badge over an empty/unscored DB is worse than none — it actively destroys the trust the product bets on.
- **Consumer PWA + Clerk auth (Phase 1.2) comes after the feed has real data.**
  - Why: a PWA over an empty feed demos nothing. RLS 0007 already narrowed event public-read so the anon key is safe to ship client-side when we get there.

## Session-arc system decisions (this session's meta-work)

- **Loops & Harness = blend of built-in capabilities + user workflow conventions**, operating as one system.
- **Cadence = "assess prior to the need to compact"** — checkpoint arcs proactively at heavy moments, before context loss, not on a fixed clock.
- **Storage = repo + memory** — arcs in `docs/session_arcs/`, key facts mirrored to agent memory, `STATE.md` stays the always-current rollup.
- **Harness = standing in-session behavior, not a cron** — compaction risk is tied to conversation activity, not wall-clock time, so no recurring background loop was created.

## Findings (verified, not assumed)

- **Nothing has run yet.** All 14 tables are 0 rows, including `source` — the 43-source catalog (`sources/master_sources_catalog_120.json`, ranks 1–41 + 119–120 populated) was **never imported** to the live DB.
- **AI provider is a stub.** `ai/bedrock_provider.py` returns `None` whenever `client is None` or `model_id == "stub"` — no real model wired.
- **No orchestrator exists.** `worker/run_once.py` is a hardcoded smoke test (one fake Mohawk event); nothing loops over the source catalog to drive real fetches.
- **The trust UI is decoration over an empty DB** until the pipeline runs — exactly the risk `prioritization_narrative.md` warned about.
- Code quality is genuinely good: 4-state confidence enforced end-to-end, RLS locked down, anti-hallucination prompt, city-scoped fuzzy resolution, 48 passing tests.

## Documents / artifacts

| Artifact | Location | Note |
|---|---|---|
| Session-arc system README (harness + template) | `docs/session_arcs/README.md` | Created this session |
| This arc | `docs/session_arcs/2026-07-10_build-assessment.md` | Created this session |
| Prioritization narrative (Tier 0–3) | Space file `prioritization_narrative.md` | Strategy source |
| Easy-value build sequence (Waves 1–3) | Space file `easy_value_sequence.md` | Strategy source |
| Authoritative technical spec (v1) | `docs/Final_ONE_Live_Authoritative_Technical_Spec.md` | Reference build handoff |
| Source catalog (43 populated / 120 target) | `sources/master_sources_catalog_120.json` | Ranks 42–118 = TODO gap |

## Open threads / next steps (ordered)

1. **Import 43-source catalog → live DB** (`tools/import_sources.py`). Unblocks everything; first proof the DB path works with real rows.
2. **Wire a real AI provider** (Claude API) replacing the stub in `ai/bedrock_provider.py` / `ai/provider.py`.
3. **Build the source-loop orchestrator** so the worker fetches → extracts → gates → promotes real events for Austin.
4. **Finish & merge PR #4** (source-trust scoring, migration 0008).
5. **Then Wave 1 trust UI**, then **Phase 1.2 PWA + Clerk**.
6. **Housekeeping:** resolve open founder decisions in `STATE.md` — especially the **$1.2M vs $1.44M Year-1 revenue reconciliation** before any investor conversation.

## Drift corrected this session

- `STATE.md` claimed migrations 0005/0006/0007 were "NOT yet applied" and PRs #1–3 "not merged." **Reality: all three PRs are merged and all 7 migrations are applied.** STATE.md refreshed this session.
