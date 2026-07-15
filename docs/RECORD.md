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
| R-006 | 2026-07-13 | Extraction hallucination-rate threshold unratified (§11.2 proposes ≤1% golden-set, release-blocking) | §11.2 eval thresholds stated, not implied | Founder one-line ratification (asked in the standing unblock list). Blocks Step 6 | RESOLVED (founder 2026-07-15: "BEGIN at 1%" + one-way Kaizen ratchet, docs/KAIZEN.md §M7 — the NUMBER; the gate that proves it is R-013, extraction stays blocked until it ships and passes) |
| R-007 | 2026-07-13 | Source catalog ranks 42–118 unpopulated (43 of 120+ target) | §5 data-trust coverage / catalog completeness | Sprint Step 6 exit gate (extraction evals green): ranks populated via the weekly source-backfill loop, or the remainder explicitly descoped by a founder decision record | OPEN |
| R-008 | 2026-07-13 | Ingestion cron deliberately unarmed (`ingest.yml` manual-only) | Charter Sentinel rule + §14.3 (a scheduled loop without dead-man + caps is forbidden — so this hold IS the bar; recorded for visibility) | Secrets P2/P3 in Actions + friction attack → arming PR through the gate | OPEN |
| R-009 | 2026-07-13 | PR #4 (draft, migration 0008) and PR #7 (superseded by #9's port) still open | §0.3 contract hygiene — parallel branches don't accumulate unreviewed | Founder one-liners: close #7 as superseded? finish-or-defer #4? (asked in the standing unblock list) | RESOLVED (founder 2026-07-15 "Close both": #7 superseded-by-#9, #4 closed as Step 7 reference draft — closing notes on both) |
| R-010 | 2026-07-13 | Option 1D (graph memory: Graphiti + graph DB) deliberately NOT built — the ratified brain is 1A+1B; 1D is the benchmark ceiling for temporal recall (Zep 63.8% LongMemEval) we chose not to buy yet | Brain doc §1C/§1D — best-in-class temporal recall | The standing G-BRAIN-1D trigger (brain doc §RATIFIED): fires on T1 Emotion Graph build begins / T2 pgvector temporal-recall failures logged / T3 relationship queries outgrow SQL → friction attack → founder decision (money/new services) | OPEN |
| R-011 | 2026-07-13 | (retro-recorded — surfaced by deferral_scan's new SQL pass) migration 0006's `event` public-read policy `using (true)` exposed private-event columns to the anon key, held as an "accepted tradeoff" comment | §6 RLS least-privilege / fail-closed | Narrow before any client-side anon-key use | RESOLVED (migration 0007_narrow_event_public_read.sql) |
| R-013 | 2026-07-15 | Extraction remains BLOCKED (router flag False; provider consults it at its entry point) — the 1% bar is ratified (R-006) but the golden-set gate that PROVES it does not exist: no golden data, no live-exam runner, no CI wiring | docs/KAIZEN.md §M7 — no extraction change ships without exam evidence at a valid sample size | Step 6 build (next focused session, contract-first, evaluator mandatory): ≥40-example golden set (~320 facts ≥ the 1% sample floor) + live-exam runner + blocking CI job; flag flips in the commit that attaches a PASSING result for the starting model | OPEN |
| R-012 | 2026-07-14 | Kaizen maturity LEVELS per pipeline stage deliberately not built (measures M1–M6 are live; levels graded on an idle factory measure nothing) | docs/KAIZEN.md §Levels — full Kaizen includes staged maturity | First real scheduled ingestion cycle completes (R-008 resolved + one cron week) → design level rubric on actual flow, grade every stage, add to ledger | OPEN |
| R-014 | 2026-07-15 | `extraction-eval.yml` runs PR-controlled code with `ANTHROPIC_API_KEY` on `pull_request` (evaluator nit, PR #25 r5). Accepted for now because: same-repo private solo project — fork PRs receive NO secrets from GitHub by default, so the only code path to the key is a branch this repo's own agents/founder pushed; the key is extraction-only with a console spend cap; and the alternative (environment approval per exam run) puts a founder interrupt inside every calibration cycle | §11.4 AI-supply-chain / secret-exposure hardening (deep review) | Repo goes public OR gains an outside contributor OR org runners change fork-secret behavior → move the exam to a protected environment or two-phase (trusted-base) workflow | OPEN |

**Adding an entry:** same commit as the deferral it records; cite the bar
section (or "n.a. — bar gap", which itself is a finding); give an objective
trigger, never "someday". **Resolving:** flip status to
`RESOLVED (<commit/PR>)`; leave the row. **Session close:** review OPEN
rows — resolve, re-affirm (trigger still pending), or escalate; a row whose
trigger has fired but wasn't acted on is a defect.
