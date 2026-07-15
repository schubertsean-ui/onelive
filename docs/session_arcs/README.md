# Session Arcs — OneLive Working Log

A **session arc** is a durable, structured record of one working session: the key
decisions made, findings verified against ground truth, documents/artifacts produced,
and the open threads that carry into the next session. Arcs exist so that **nothing
pertinent slips through the cracks** and any session can resume continuously without
re-deriving where we are.

Arcs live in two places (kept in sync):
- **This repo** (`docs/session_arcs/`) — durable, reviewable, version-controlled next to the code.
- **Agent memory** — key facts mirrored so the next session recalls current state automatically.

`STATE.md` (repo root) remains the **always-current rollup** — the single snapshot of
"where we are right now." Arcs are the **chronological connective tissue** between
`STATE.md` and `CHANGELOG.md`: each arc explains *how* the state changed and *why*.

---

## The Harness (procedure run every session)

The harness is a repeatable ritual with two bookends and a safeguard in the middle.

### 1. Session-open reconciliation (before doing work)
Verify **ground truth** and correct any drift in `STATE.md` before trusting it:
- `git log` on `origin/master` — what actually landed.
- `gh pr list --state all` — real merge/draft status (not what a doc claims).
- Supabase `list_migrations` — which migrations are actually applied to the live project.
- Supabase row counts on core tables — what data actually exists (pipeline liveness).
- Deploy state (Vercel) and connected services (Clerk, GitHub, Supabase).

Drift found during reconciliation is itself a **finding** — record it in the arc.

### 2. Checkpoint safeguard (during work — "prior to the need to compact")
The arc is **not** a fixed end-of-session ritual. Checkpoint the arc **proactively at
natural heavy moments** — after a substantial investigation, after a batch of decisions,
or whenever enough new state has accumulated that losing it would hurt — **before**
context is at risk of compaction/truncation. Err on the side of checkpointing early and
updating the same dated file in place, rather than risking a gap.

> Operational note: there is no literal context-percentage meter. "Prior to compaction"
> is a standing instruction to checkpoint at heavy moments, not on a clock.

### 3. Session-close arc (when a session wraps)
Finalize the arc, refresh `STATE.md`, append to `CHANGELOG.md` if artifacts shipped,
and mirror key facts to memory.

---

## Arc file convention

- **Location:** `docs/session_arcs/`
- **Filename:** `YYYY-MM-DD_short-slug.md` (e.g. `2026-07-10_build-assessment.md`).
  If a session spans work already covered by a dated file, **update that file in place**
  rather than creating a duplicate.
- **Index:** newest arcs listed at the top of the table below.
- **Git tag (findability):** at session close, tag the commit that finalizes an
  arc with `arc/YYYY-MM-DD_slug` — the same slug as the arc filename — so any arc
  is directly reachable from git history later (`git tag arc/2026-07-11_agentic-harness <sha>`;
  find with `git tag -l 'arc/*'`, jump with `git show arc/<slug>`). Arcs are
  referenced *often* after the fact; the tag makes "which commits belong to that
  session?" a one-liner. Push tags with `git push --tags`. If a session spans an
  existing dated arc, move/retag rather than duplicate.

## Arc template

```markdown
# Session Arc — YYYY-MM-DD — <Title>

- **Session focus:** <one line>
- **Status at close:** <one line — what's true now>

## Ground-truth snapshot (reconciliation result)
| Dimension | Verified state |
|---|---|
| Repo (origin/master HEAD) | <commit + summary> |
| PRs | <merged / open / draft> |
| Migrations applied (live) | <list> |
| DB data (row counts) | <core tables> |
| Services | <GitHub / Supabase / Vercel / Clerk> |

## Decisions (what + why + tradeoffs)
- **<Decision>** — Why: <...>. Tradeoff: <...>.

## Findings (verified, not assumed)
- <Finding, grounded in a check above.>

## Documents / artifacts
| Artifact | Location | Note |
|---|---|---|

## Open threads / next steps (ordered)
1. <Next action> — why it's next.

## Drift corrected this session
- <Doc that was stale> → <corrected to>.
```

---

## Arc index

| Date | Arc | Focus |
|---|---|---|
| 2026-07-13 | [Genesis install + Session Contract #1](2026-07-13_genesis-install-and-session-contract-1.md) | Installed the ONELIVE_GENESIS doc package (charter merged with existing CLAUDE.md); verified PRs #9/#10 merged (STATE drift superseded); evaluator gate `tools/adversarial_review.py`, friction log entry #1, Sentinel minimum (Sentry no-op wiring + dead-man ping) online; sprint plan `docs/SPRINT_LIVE_SITE.md` written. Zero deploy/migrate/spend. |
| 2026-07-14/15 | [First real run, quality ratchet, sensor canon](2026-07-14_first-real-run-ratchet-and-sensor-canon.md) | PRs #14–#22 merged: po battery + Kaizen measures/ledger; scale-out sensor architecture RATIFIED (watchers, 3 modes, first-party = confirmed); all 4 secrets landed; FIRST REAL INGESTION RUN (infra green, extraction failed loud on retired model id, ~$0); R-006 ratified at 1% + one-way ratchet (M7, field-assertion unit); extraction gated at every entry point until Step 6's golden-set exam (R-013). M1 trend 5→1. |
| 2026-07-12 | [Harness review, merge & live reconcile](2026-07-12_harness-review-merge-and-live-reconcile.md) | (Index row added retroactively 2026-07-13 — the arc file existed but was missing from this table.) PR #8 cross-model reviewed, fixed, merged; validate gate SKIP/ADVISORY→INCOMPLETE; live DB reconciled. |
| 2026-07-11 | [Agentic-harness buildout](2026-07-11_agentic-harness-buildout.md) | Audited OneLive vs. the 18-item setup + 20-step Loop Engineering roadmap; built lint+hooks, validate gate, night-shift skill, commit_sweep, test_audit, perf benchmarks/profiler, visual-regression harness, personas, TESTS/CONVENTIONS/TODOS/FEEDBACK docs; wired all controlling docs. |
| 2026-07-10 | [Build assessment & session-arc system](2026-07-10_build-assessment.md) | Ground-truth audit of the build; defined next steps; established this arc system. |
| 2026-07-10 | [Source import + real AI provider + operating rules](2026-07-10_source-import-and-ai-provider.md) | Imported 43-source catalog; built Claude provider (fail-loud/audit-degrade/provenance); hallucination-rate eval; codified `OPERATING_RULES.md`. |
