# Decision: gate verdicts persist onto the candidate row (2026-08-05)

**Context — the stranded backlog.** The kickoff (WS2) ordered: "verify gates
stamp the 4,202 candidate backlog and autopromote's hourly pass shows
examined>0, promoted>0 … diagnose the stage that stamps `ready_to_promote`
and fix forward." Diagnosis (this session, from code + the first live pass):
`create_candidate` inserts every candidate at `status='needs_review'`; the
orchestrator computed the trust-gate verdict at gate3 but recorded it ONLY in
the replay log; the sole writer of `status='ready_to_promote'` was the human
ops action (`api/ops_candidates.py`). Net effect: the autopromote pass
selected an eternally empty population (first live run 30968880343:
`examined=0`), and the only road to publication was per-item human stamping —
the REJECTED per-item-approval design in disguise (charter 1.2).

**The fix (custody unchanged).**
1. `worker/candidate_store.stamp_gate_verdict` — persists status +
   gate_reason + required_next with the exact column contract the ops action
   uses.
2. The orchestrator stamps every gate3 verdict: PASS → `ready_to_promote`,
   HOLD → `needs_more_confirmation`, ESCALATE → stays `needs_review` with the
   reason recorded.
3. `worker/autopromote.stamp_backlog` — a bounded, DB-only sweep of the
   never-stamped backlog (`needs_review` with `gate_reason IS NULL`) through
   the SAME `evaluate_gate`, run as a pre-phase of the existing hourly
   autopromote entrypoint (`--stamp-limit`, required, 0 = skip; no new cron,
   so no new dead-man owed).

**Why this is not a custody change:** stamping CLASSIFIES; it never
publishes. `ready_to_promote` only makes a candidate visible to the two
custody-holding publish paths — the ratified earned-confidence autopromote
pass (fail-closed behind the founder-flipped flag) and the authenticated ops
promote — and both re-run their own gates before acting (defense in depth).
The orchestrator still cannot import the promote path.

**Honest residual (documented in the sweep's docstring):** a candidate
stamped `needs_more_confirmation` re-enters the gate only when new evidence
arrives through a re-gating path (ops add_evidence today; an orchestrator
evidence-merge re-gate when cross-candidate evidence merging lands). The
sweep drains the never-examined backlog; it is not a standing
re-adjudicator.
