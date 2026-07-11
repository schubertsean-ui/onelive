# SESSION START — read this first, every session

This is the single canonical entry point. Its only job: get you to a trustworthy
picture of where we are, in the right order, without re-researching from scratch
or missing something important. Follow it top to bottom before doing any work.

> **Why this exists:** continuity fails not from missing docs but from *unverified
> trust* in them. STATE.md can drift from reality between sessions. This flow makes
> STATE.md trustworthy *before* you rely on it. See `docs/OPERATING_RULES.md` §4.

---

## Step 1 — Reconcile (mandatory, mechanical)

Run the reconciler. It verifies STATE.md's ground-truth block against live git,
PRs, and the DB, and classifies any drift:

```bash
# In an env with the DB DSN (worker/CI) — full verification + auto-heal benign drift:
ONELIVE_DB_DSN=... python tools/session_reconcile.py --heal

# In a sandbox without a DSN — verifies git/PRs; DB facts come from the connector:
python tools/session_reconcile.py
```

Interpret the exit code:
- **exit 0** — clean (or only benign drift, auto-healed). Proceed to Step 2.
- **exit 2 — MATERIAL CONTRADICTION** — STATE.md asserts something live ground
  truth denies (e.g. a PR it calls merged that's open, a table it calls empty
  that's populated). **Stop. Fix the STATE.md prose to match reality, re-run,
  then proceed.** Do not build on a contradicted claim.
- **exit 2 — UNVERIFIED** — a critical fact (usually DB) couldn't be checked here.
  Verify it via the Supabase connector using the SQL the script printed, update
  the ground-truth block, then proceed. Never treat "couldn't check" as "fine".

If you have no DB DSN (typical in the agent sandbox), run the printed SQL via the
Supabase `execute_sql` connector (project `vqipjlvzfiwnandjumvx`) and reconcile the
`row_counts` / `applied_migrations` in STATE.md's block by hand or via a follow-up
`--heal` run once you've confirmed the numbers.

## Step 2 — Read STATE.md (now trustworthy)
The always-current rollup: what's done, what's next, locked-in decisions, open
founder decisions. The machine block at the top is the verified snapshot; the
prose is the human context.

## Step 3 — Skim the latest session arc
`docs/session_arcs/README.md` → open the most recent arc. Arcs are the "how we got
here": decisions with reasoning + tradeoffs, bugs found, open threads. This is
where the *why* lives that STATE.md summarizes.

## Step 4 — Refresh the working rules (once, or when they change)
- `docs/OPERATING_RULES.md` — quality bar, Loops/Kaizen, trust rules, the Harness.
- `CLAUDE.md` — architecture invariants and PR review criteria.

---

## During the session (the Harness, from OPERATING_RULES §4)
- **Checkpoint proactively** before a context-heavy stretch risks compaction:
  append/write a session arc so no decision or finding is lost.

## Session close (finalize)
1. Update STATE.md prose (what changed, what's next).
2. Re-run `session_reconcile.py --heal` so the ground-truth block matches reality
   at close (leaves the next session a verified starting point).
3. Write the session arc (`docs/session_arcs/YYYY-MM-DD_slug.md`), add it to the
   README index, mirror key decisions to memory.
4. Note any new external dependency in STATE.md (CLAUDE.md review rule #3).

---

**One-line version:** reconcile → trust STATE.md → skim latest arc → know the
rules → work → checkpoint before compaction → finalize + re-reconcile at close.
