# Session Arc — 2026-07-10 — Source catalog import + real AI provider + operating rules

**Rollup:** see `STATE.md`. **Prior arc:** `2026-07-10_build-assessment.md`.

## Context
Continuation after merging PR #5 (session-arc system). Directive: "Merge PR #5.
Start on the source catalog import and real AI provider." Mid-session the founder
raised the quality bar explicitly ("no 'ok' code, nothing lingers/deferred") and
asked for a formal operating-rules doc incorporating Loops and a Kaizen approach.

## Decisions (with reasoning + tradeoffs)

1. **Import the 43-source catalog into live Supabase via service-role `execute_sql`.**
   - Why: no DSN/secret handling needed; bypasses RLS as service role; idempotent
     via `on conflict (name) do update` after adding migration 0009 unique constraint.
   - Tradeoff: most rows stored a compact `config` blob (rank/id/category — what the
     pipeline reads) rather than the full catalog JSON. Full JSON remains in the repo
     file; can re-upsert full blobs later without schema change. Accepted.
   - Verified: `count(*) = 43`, all enabled, 15 source_types, avg credibility 0.673.

2. **Real AI provider = Claude, failure semantics mirror `_fuzzy_match` (0006 precedent).**
   - Config/structural failures (no key, unknown model, bad schema, 4xx) → raise
     `ExtractionConfigError` (loud). Transient (429/5xx/timeout) → retry w/ backoff,
     then return None AND write an `audit_log` degradation row. Genuine empty → None.
   - Why: in a truth-first pipeline "we failed to look" must never look identical to
     "nothing was there." Extends the 0006 precedent with an audit trail on degrade.
   - Tradeoff: the orchestrator must catch `ExtractionConfigError` and route to manual
     review rather than crash — correct place for that decision. Accepted.

3. **Provenance stamping + decouple provider from the DB.**
   - Each successful extraction carries `_provenance` (provider/model/prompt_version/
     timestamp). Provider takes an `audit_hook` callable, not a DB cursor — it knows
     nothing about psycopg2. `worker/candidate_store.record_ai_degradation` is the hook.
   - Why: auditability (CLAUDE.md) + clean layering.

4. **Upgrade the eval harness to measure hallucination_rate.**
   - Old harness did exact-match only and could not measure false positives — the one
     metric that governs trust (DoD #41). Added precision/recall/F1 + hallucination_rate;
     kept old `evaluate_extraction` for back-compat.

5. **Codify how we work → `docs/OPERATING_RULES.md`** (Loops + Kaizen + trust rules +
   Harness + quality bar). Mirrored to memory.

6. **Session-continuity system → make STATE.md trustworthy mechanically, not by
   judgment.** New `docs/SESSION_START.md` (single canonical entry point) +
   `tools/session_reconcile.py`. The reconciler verifies STATE.md's machine-readable
   ground-truth block against live git/PRs/DB and does TIERED drift handling: benign
   drift auto-heals (`--heal`); a material contradiction (e.g. PR claimed merged but
   open, table claimed empty but populated) HARD-STOPS (exit 2); unverifiable facts
   are flagged loudly, never passed as clean.
   - Why tiered (analysis): a hard gate on *every* session gets bypassed (worse than
     none); report-only relies on the same judgment that let STATE.md go stale. Soft
     default + hard-stop only on decision-changing contradictions optimizes
     correctness × speed × robustness. It applies "findings are claims until verified"
     to STATE.md itself.
   - Seeded STATE.md's ground-truth block with connector-verified facts (source=43,
     event/candidate/evidence=0, 8 migrations, PR states). Wired SESSION_START into
     CLAUDE.md ("Where to look first") and OPERATING_RULES §4 (Harness open/close).
   - Verified: reconciler correctly reports PRs live, flags DB unverified in sandbox
     (fail-loud), and hard-stops on a simulated stale PR claim. 7 unit tests added.

## Bugs found by self-review/tests (fixed same change — nothing deferred)
- `_provenance` was being silently dropped at the pydantic validation boundary in
  `worker/ai_extract.py`. Fixed: split meta from event fields, re-merge after validation.
- Validation failure was silently blanked into an empty candidate. Fixed: log loudly +
  flag `_provenance.validation_error` + still create a review row.
- Provider audit path was dead (no cursor ever passed). Fixed: `audit_hook` wired via
  `inspect.signature` so only capable providers receive it (stub stays drop-in).
- Default-city guarantee broke on `null` (setdefault missed it). Fixed: default on falsy.

## Artifacts
- NEW `ai/claude_provider.py`, `tests/test_claude_provider.py`,
  `tests/test_ai_extract_integration.py`, `docs/OPERATING_RULES.md`,
  `supabase/migrations/0009_source_name_unique.sql`,
  `docs/SESSION_START.md`, `tools/session_reconcile.py`,
  `tests/test_session_reconcile.py`.
- MODIFIED (continuity): `CLAUDE.md` (Where to look first → SESSION_START),
  `STATE.md` (machine-readable ground-truth block).
- MODIFIED `ai/eval_harness.py`, `worker/ai_extract.py`, `worker/candidate_store.py`,
  `worker/requirements.txt` (+`anthropic`), `tools/import_sources.py` (upsert), `STATE.md`.
- DB: `source` table populated (43 rows); migration 0009 applied.

## Verification
- 71 unit/integration tests pass (10 DB-integration deselected — no live DB in sandbox).
- Source count + migrations + PR states verified against live DB/GitHub.
- Reconciler behavior verified: clean on live PRs, loud on unverifiable DB,
  hard-stop on a simulated material contradiction.

## Open threads / next steps
1. Build the source-loop orchestrator: fetch → extract (real provider) → gate →
   promote → `/tonight`, run on real Austin data. (Now the top bottleneck.)
2. Set `ANTHROPIC_API_KEY` in the worker environment (secure; not in repo).
3. Finish & merge PR #4 (source-trust scoring, migration 0008).
4. Optionally re-upsert full `config` JSON blobs for all 43 sources.
