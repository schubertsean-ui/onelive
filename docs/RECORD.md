# RECORD — the deviations-from-world-class register ("Recording")

Greppable summary: founder-directed (2026-07-13) ledger of EVERY deferral,
hold, or watch — any "for now", "check later", "revisit", "ok for now",
noticed-but-not-fixed. The standard is that such moments should not exist
(everything checked against the documented world-class bar for that item);
when one does exist it is recorded HERE in the same commit, naming the bar
it deviates from and the objective trigger that resolves it. Silent deferral
is a violation. Mechanical enforcement in code: `tools/deferral_scan.py`
(wired into `tools/validate`) — a deferral-language comment must carry an
`[R-###]` tag pointing at a live entry. Prose (docs, PR text, chat) is
covered by the charter rule + evaluator review. Entries are never deleted:
resolved entries flip status to RESOLVED with the resolving commit/PR.

Format: `R-### · opened · what is deferred/held · world-class bar it
deviates from (cite) · resolution trigger · status`.

| # | Opened | What | Bar deviated from | Resolution trigger | Status |
|---|---|---|---|---|---|
| R-001 | 2026-07-13 | Sentry wired for error monitoring only; performance tracing disabled (`traces_sample_rate=0` in `worker/sentinel.py`, `web/instrumentation*.ts`) | WORLD_CLASS §7 observability (golden signals incl. latency) | DSNs live + first real traffic (Sprint Step 9 preview): revisit sample rate as a deliberate, costed decision | OPEN |
| R-002 | 2026-07-13 | `visual_regression` gate permanently SKIPs (no booted app/baselines) — pre-existing defect D4 | §9.6 "a test that cannot fail proves nothing" (applies to gates) | First deployed preview URL (Step 9): capture baselines, make the gate fire in CI | OPEN |
| R-003 | 2026-07-13 | 4 moderate npm advisories accepted (postcss-via-next, no upstream fix) per `docs/SCA_BASELINE.md` | §3.5 dependency hygiene / SCA | `next` ships with postcss ≥ 8.5.10 → bump + clear baseline row (CI re-audits every web PR) | OPEN |
| R-004 | 2026-07-13 | STATE.md GROUND_TRUTH block stale (reconciler needs `gh` + DB DSN, absent in this sandbox); prose carries verified truth | §0.4 disk is truth (machine-verified) | First session in a credentialed env: `session_reconcile.py --heal`; also queued: GitHub-API fallback for the reconciler | OPEN |
| R-005 | 2026-07-13 | FRICTION_LOG entry #1 attacked by the generator model (PROVISIONAL), not non-Claude | §0.2 write/grade separation extended to planning | `OPENAI_API_KEY` present in session env (founder added; verify next session) → re-attack, clear flag. Blocks Step 5 arming | OPEN |
| R-006 | 2026-07-13 | Extraction hallucination-rate threshold unratified (§11.2 proposes ≤1% golden-set, release-blocking) | §11.2 eval thresholds stated, not implied | Founder one-line ratification (asked in the standing unblock list). Blocks Step 6 | OPEN |
| R-007 | 2026-07-13 | Source catalog ranks 42–118 unpopulated (43 of 120+ target) | §5 data-trust coverage / catalog completeness | Sprint Step 6 exit gate (extraction evals green): ranks populated via the weekly source-backfill loop, or the remainder explicitly descoped by a founder decision record | OPEN |
| R-008 | 2026-07-13 | Ingestion cron deliberately unarmed (`ingest.yml` manual-only) | Charter Sentinel rule + §14.3 (a scheduled loop without dead-man + caps is forbidden — so this hold IS the bar; recorded for visibility) | Secrets P2/P3 in Actions + friction attack → arming PR through the gate | OPEN |
| R-009 | 2026-07-13 | PR #4 (draft, migration 0008) and PR #7 (superseded by #9's port) still open | §0.3 contract hygiene — parallel branches don't accumulate unreviewed | Founder one-liners: close #7 as superseded? finish-or-defer #4? (asked in the standing unblock list) | OPEN |
| R-010 | 2026-07-13 | Option 1D (graph memory: Graphiti + graph DB) deliberately NOT built — the ratified brain is 1A+1B; 1D is the benchmark ceiling for temporal recall (Zep 63.8% LongMemEval) we chose not to buy yet | Brain doc §1C/§1D — best-in-class temporal recall | The standing G-BRAIN-1D trigger (brain doc §RATIFIED): fires on T1 Emotion Graph build begins / T2 pgvector temporal-recall failures logged / T3 relationship queries outgrow SQL → friction attack → founder decision (money/new services) | OPEN |
| R-011 | 2026-07-13 | (retro-recorded — surfaced by deferral_scan's new SQL pass) migration 0006's `event` public-read policy `using (true)` exposed private-event columns to the anon key, held as an "accepted tradeoff" comment | §6 RLS least-privilege / fail-closed | Narrow before any client-side anon-key use | RESOLVED (migration 0007_narrow_event_public_read.sql) |
| R-012 | 2026-07-14 | Kaizen maturity LEVELS per pipeline stage deliberately not built (measures M1–M6 are live; levels graded on an idle factory measure nothing) | docs/KAIZEN.md §Levels — full Kaizen includes staged maturity | First real scheduled ingestion cycle completes (R-008 resolved + one cron week) → design level rubric on actual flow, grade every stage, add to ledger | OPEN |
| R-013 | 2026-07-14 | PR-aggregator research (`docs/research/PR_AGGREGATOR_RESEARCH.md`): §3/§5/§8 pricing + ToS figures are single-pass search-index reads, NOT adversarially verified (sandbox egress proxy 403'd direct fetches to vendor/venue sites); sections are labeled BEST-EFFORT in-doc | §0 verification bar — figures driving a spend/build decision must be primary-source-verified | Founder greenlights the PR-aggregator venture (or any contract/build against a named provider) → re-verify that provider's live pricing page + ToS from an unproxied machine, and put the "do transformed diffs count as redistribution?" question to them in writing, BEFORE any spend or ingestion code | OPEN |
| R-014 | 2026-07-14 | Promise-ledger golden set is SYNTHETIC-ONLY (2 authored examples exercising harness mechanics) and the EDGAR client has never run against live EDGAR — this sandbox's egress blocks sec.gov (curl + WebFetch verified blocked 2026-07-14). The harness mechanically refuses to PASS on synthetic-only data (`ventures/promise_ledger/eval/golden.py`) | §0 verification bar — extraction thresholds mean nothing without real labeled data; the analysis names extraction precision the venture's existential risk | First session in an environment with sec.gov egress (or founder allowlists sec.gov/data.sec.gov/efts.sec.gov): run the EDGAR client under budget, seed ≥20 real 8-K EX-99.1 labeled examples, delete nothing synthetic (mark superseded), and only then treat PRECISION_BAR as meaningful. Blocks any extraction-model work | OPEN |

**Adding an entry:** same commit as the deferral it records; cite the bar
section (or "n.a. — bar gap", which itself is a finding); give an objective
trigger, never "someday". **Resolving:** flip status to
`RESOLVED (<commit/PR>)`; leave the row. **Session close:** review OPEN
rows — resolve, re-affirm (trigger still pending), or escalate; a row whose
trigger has fired but wasn't acted on is a defect.
