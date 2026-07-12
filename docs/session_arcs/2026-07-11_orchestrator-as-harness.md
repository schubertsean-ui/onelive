# Session Arc — 2026-07-11 — Trust gate (CI) + orchestrator-as-Harness

**Rollup:** see `STATE.md`. **Prior arc:** `2026-07-10_source-import-and-ai-provider.md`.

## Context
Continuation. The PR #6 CI check ("review") was failing. Directive sequence from
the founder: fix CI and merge PR #6, then build the source-loop orchestrator —
explicitly AS the Loop/Harness architecture we had evaluated and defined for
"world leading," not a plain pipeline decorated later. Founder reinforced the
standing quality bar (no "ok" code, nothing deferred/lingering, no swallowed
errors, no dead code, no red tests) and corrected a process slip: when presenting
options, MAKE the recommendation with why + implications and PROCEED — do not end
turns bouncing questions back.

## Decisions (with reasoning + tradeoffs)

1. **CI: replace the AI PR-reviewer with a deterministic in-repo trust gate
   (`tools/trust_gate.py`). (Founder chose Option B.)**
   - Root cause of the red check was a stack of five defects in the
     `anthropics/claude-code-action@v1` workflow, terminating in a hard blocker:
     the Claude GitHub App was not installed on the repo (401 "Claude Code is not
     installed"), and @v1 requests OIDC even when given an API key (upstream issue
     #649). The secret was added, model IDs corrected, and permissions fixed along
     the way, but the App-install dependency made the AI reviewer the wrong
     foundation for a trust-critical gate.
   - Why deterministic instead: a gate that decides whether code is safe to merge
     must itself be deterministic and dependency-free. An AST-based check that
     encodes our actual trust invariants is a *stronger* guarantee than an LLM's
     opinion, and it cannot be flaky, throttled, or de-authorized by a third party.
   - What it enforces (exit 1, loud, on any violation): (1) no dynamic SQL in
     api/worker/tools (rejects f-string / %-format / .format() / concat into
     .execute(); allows static %s params and psycopg2.sql composition); (2)
     ads/tastemaker code must not import worker.gating / worker.promote; (3) the
     AI/extraction layer (ai/*, worker/ai_extract.py) must not import
     worker.promote — AI never publishes directly. A PROMOTE_IMPORT_ALLOWLIST
     names the few legitimate callers of promote.
   - Tradeoff: a deterministic gate only catches the invariant classes we encode,
     not arbitrary "code smell." Accepted — those invariants are exactly the
     trust-critical ones, and the gate is cheap to extend as new invariants harden.
   - Hardened two real dynamic-SQL sites the gate would (correctly) have flagged:
     `worker/resolve_entities.py` and `tools/session_reconcile.py` now compose
     identifiers via psycopg2.sql with an allowlist/assertion guard.
   - Verified: gate green locally and in CI (first run), full suite green; merged
     PR #6 to master (squash a135ca9).

2. **The orchestrator IS the Sensors -> Harness -> Loop, built as one artifact.**
   - The founder's question — why we weren't implementing the Loop/Harness we'd
     defined — was correct. The answer was not to build a plain pipeline and add
     trust later; it was to build the orchestrator so its structure *is* the
     harness. Committed to that and proceeded.
   - Five components, wiring the real existing functions (no stubs/rewrites of
     fetch/extract/gating/promote/candidate_store):
     - `worker/trust_gate3.py` — three-way PASS / HOLD / ESCALATE gate that WRAPS
       (never replaces) `multi_confirm_gate`. This is the heart of the change.
     - `worker/replay_log.py` — append-only JSONL deterministic-replay logging.
     - `worker/sensors.py` — input-quality/context-hygiene gate before extraction.
     - `worker/orchestrator.py` — the loop tying it together with per-source error
       isolation.
     - `worker/run_once.py` — rewritten to drive the real loop (stub + guarded
       `--real`).

3. **The gate must be THREE-way, and ESCALATE is non-negotiable. (Core decision.)**
   - `multi_confirm_gate` is 2-way (ok_to_promote true/false), which is correct for
     *corroboration counting* but insufficient for *auto-publish safety*.
     trust_gate3 adds ESCALATE: promotable-by-count BUT the evidence is conflicting
     or needs human judgement — conflicting start_time across evidence, a
     validation_error flagged in extraction provenance, a private/RSVP event, or a
     dedupe-ambiguity hint. ESCALATE => leave in needs_review, log it, never
     auto-promote.
   - Why: "enough sources said so" is not the same as "safe to publish." Collapsing
     ambiguous cases into PASS is precisely the trust failure this product cannot
     afford. HOLD (insufficient corroboration) is a normal wait state; ESCALATE is
     the human-judgement branch; PASS is clean-and-corroborated.
   - Defense in depth: trust_gate3 never promotes; on PASS the orchestrator calls
     `promote_candidate`, which independently re-checks the 2-way gate. Two
     independent gates guard every publish.

4. **The Karpathy "iterate-on-green, never-ask-a-human" ratchet is fenced to the
   BUILD loop only — explicitly REJECTED for the product gate.**
   - Two independent red-teams (external AI + self) converged on this: the ratchet
     is a good discipline for how WE evolve the code (commit on green, revert on
     regression), but "never ask a human" is exactly wrong for the product's
     trust decision. The orchestrator does not self-modify and never auto-approves
     a promotion "to keep the run going." ESCALATE-to-human is the intended,
     correct outcome, not a bug to route around. This fence is documented in the
     orchestrator module docstring so it cannot silently erode.

5. **Deterministic-replay logging from line one (not deferred).**
   - Every loop step (fetch / sensor / extract / gate3 / promote|escalate|hold|
     error) emits a ReplayRecord with sha256 digests of canonicalized inputs/
     outputs, so any promotion decision is auditable and re-runnable months later.
   - Fail LOUD if the log dir is unwritable (ReplayLogWriteError) — losing an audit
     record silently is the "we failed looks like nothing happened" anti-pattern
     this project bans. Runtime artifacts live under `var/` (gitignored).

## Failure semantics (consistent with the 0006 / ai_extract precedent)
- Config/structural errors (e.g. unwritable replay dir) fail LOUD and abort the run.
- Per-source transient errors (flaky fetch, provider hiccup, and — in a DB-less
  sandbox — the OperationalError from extract's DB write) are caught in exactly one
  place in `run_loop`, logged to BOTH the RunReport and the replay log, and the loop
  continues. One bad source never takes down the run; a failure is never absorbed as
  "nothing to do."

## Verification (all self-run, not taken on the subagent's word)
- `python -m pytest -q` → 117 passed, 10 skipped (78 pre-existing + 39 new; skips
  are pre-existing DB-integration tests needing ONELIVE_TEST_DB_DSN).
- `python tools/trust_gate.py` → exit 0.
- `python worker/run_once.py` → exit 0; RunReport printed; per-source
  OperationalError correctly isolated + logged (error-isolation contract proven
  live) and mirrored into the replay JSONL.
- Reviewer (me) caught and fixed two quality-bar issues the subagent left: a
  garbled run-on sentence in the run_once docstring and a redundant `import os`.

## Known follow-ups (do not let lapse)
- Run the orchestrator `--real` against live Austin sources once a DB is reachable
  in-session; confirm a real candidate lands (DB currently 0 events / 0 candidates).
- Fold 1–2 proven instruments (the "Four Silent Costs" guards) into the EXISTING
  `docs/OPERATING_RULES.md` with the escalate-fence — NOT a new doc.
- Per-evidence start_time is not persisted separately today, so trust_gate3's
  conflicting-start_time signal currently sees a single value in the live path;
  wire richer per-evidence signals when the schema carries them.
