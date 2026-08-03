# Rule Zero — read the controlling rules COMPLETELY before any action; founder greenlight gates the work

**Founder-directed 2026-08-02.** Retrieval tokens: `rule-zero`, `complete-reading-gate`,
`no-skimming`, `no-fragments`, `read-in-full-before-acting`, `founder-greenlight-gate`.
Canonical text: `docs/OPERATING_RULES.md` → "Rule Zero" (outranks every rule below it).

## The rule (in force, non-waivable by agents)

No action of any kind — building, fixing, scanning, code/doc changes, merges,
migrations, or any substantive response that commits to or performs work — is
permitted until the controlling rules and documents for the task have been read
COMPLETELY (in full, end to end, no skimming/skipping/fragments/summarizing) and
that complete reading is explicitly confirmed. A partial read (offset/limit slice,
truncated tool output, one page of many) counts as NO read. The enumerated actions
require the founder's greenlight; a ratified contract, a founder-set TODO, or a
direct founder instruction IS the greenlight (this preserves "proceed on ratified
work"). When authorization is unclear: STOP and ask.

## Why (the failures this codifies — confirmed, so they never recur)

Twice on 2026-08-02 the agent read STATE.md / OPERATING_RULES.md / the /tonight UI
canon in fragments and acted on the partial picture:
1. **Banned delay/timer.** Proposed a 60-minute self-check-in — a direct violation of
   OPERATING_RULES §6a ("no delays… never sit on a timer"). Fix: continuation is
   completion-triggered (PR webhooks), never clock-triggered; no timers.
2. **Mis-stated a trust invariant.** Framed "AI never publishes" as "true by
   construction because a step can't be reached." The canon is "AI never publishes
   **UNVALIDATED**" (UI Canon §3) — satisfied by the validation GATE, with publishing
   gate-custodied and founder-controlled. Fix: the safety is the gate, never
   unreachability; the take-live path is buildable code (§6a.3), not a founder switch.

Root cause of BOTH: reading fragments instead of whole documents. That is the defect
Rule Zero removes.

## Enforcement (machine-consumed, not remembered)

- Harness: `docs/SESSION_START.md` Step 4 mandates reading the controlling docs IN
  FULL before any work.
- Brain: this record + `gotchas/2026-08-02_skim-fragment-is-no-read.md` are retrieved
  at session start.
- Caching: read the stable controlling docs once, in full, early — they cache, so
  complete re-reading is cheap and there is no cost excuse to skim.
- Charter pointer to CLAUDE.md is queued (TODOS) for the next lawful root-file window
  (editing CLAUDE.md trips the arming-evidence binding, R-023/R-065).

## Open point for the founder to confirm

The greenlight clause tightens autonomy. It is encoded to preserve the charter's
"proceed on ratified work" (ratified = greenlit). If the founder intends a stricter
gate (e.g. explicit per-task greenlight even for ratified work), say so and the rule
text is tightened accordingly.
