# SESSION START — read this first, every session

> **KERNEL DOC — project-agnostic, inherited verbatim.** This file describes the
> METHOD and nothing about any particular product. The concrete commands, tool
> paths, and datastore names belong in `OVERLAY.md`. Text in `[square brackets]`
> is a placeholder the overlay must bind.

This is the single canonical entry point. Its only job: get you to a trustworthy
picture of where we are, in the right order, without re-researching from scratch
or missing something important. Follow it top to bottom before doing any work.

> **Why this exists:** continuity fails not from missing docs but from *unverified
> trust* in them. STATE.md can drift from reality between sessions. This flow
> makes STATE.md trustworthy *before* you rely on it. See
> `docs/OPERATING_RULES.md` §4.

---

## Step 1 — Reconcile (mandatory, mechanical)

Run `tools/session_reconcile.py`. It verifies STATE.md's ground-truth block against live
ground truth (version control, open PRs, the datastore) and classifies any drift:

```bash
# In a fully credentialed env — full verification + auto-heal benign drift:
`tools/session_reconcile.py` --heal

# In a sandbox without credentials — verifies what it can; the rest is flagged:
`tools/session_reconcile.py`
```

Interpret the exit code:
- **exit 0** — clean (or only benign drift, auto-healed). Proceed to Step 2.
- **exit 2 — MATERIAL CONTRADICTION** — STATE.md asserts something live ground
  truth denies (e.g. a PR it calls merged that's open, a table it calls empty
  that's populated). **Stop. Fix the STATE.md prose to match reality, re-run,
  then proceed.** Do not build on a contradicted claim.
- **exit 2 — UNVERIFIED** — a critical fact couldn't be checked here.
  Verify it through whatever channel is available, update the ground-truth block,
  then proceed. Never treat "couldn't check" as "fine".

If the environment lacks direct datastore access, run the query the script printed
through the available connector and reconcile the counts in STATE.md's block by
hand or via a follow-up `--heal` run once you've confirmed the numbers.

## Step 2 — Read STATE.md (now trustworthy)
The always-current rollup: what's done, what's next, locked-in decisions, open
founder decisions. The machine block at the top is the verified snapshot; the
prose is the human context.

## Step 3 — Skim the latest session arc
``docs/session_arcs`/README.md` → open the most recent arc. Arcs are the "how we got
here": decisions with reasoning + tradeoffs, bugs found, open threads. This is
where the *why* lives that STATE.md summarizes.

## Step 4 — Refresh the working rules (once, or when they change)
- `docs/OPERATING_RULES.md` — quality bar, Loops/Kaizen, trust rules, the Harness.
- The project charter — architecture invariants and PR review criteria.
- `docs/CODING_CONVENTIONS.md` — the reviewer-facing conventions checklist.

## Step 5 — Know the queue (what to work on)
TODOS.md is the work queue (seeded from STATE.md "What's next" + open
founder decisions). Take the highest-priority **unblocked** item; never start one
that depends on an open founder decision. For an autonomous/overnight run, follow
the project's [autonomous run skill] (orchestration loop + layered exits + hard
stops).

---

## During the session (the Harness, from OPERATING_RULES §4)
- **Checkpoint proactively** before a context-heavy stretch risks compaction:
  append/write a session arc so no decision or finding is lost.

## Session close (finalize)
1. Update STATE.md prose (what changed, what's next). Update TODOS.md (check
   off done items, add new ones). Do NOT hand-edit STATE.md's machine-readable
   ground-truth block.
2. Re-run `tools/session_reconcile.py` `--heal` so the ground-truth block matches reality
   at close (leaves the next session a verified starting point).
3. **Run `tools/validate`** — the single "run everything" gate. RESULT: FAIL → you are
   not done. A SKIPPED check is NOT a pass — resolve it or hand it to the founder
   explicitly, and **every skip you report (chat, PR body, changelog) must cite
   its `docs/RECORD.md` row by id (e.g. "visual_regression skipped — R-002")**.
   This is MECHANICAL, not remembered: validate binds every environmental SKIP to
   an OPEN Record row and goes RED on an unrecorded skip (`--allow-skips` never
   covers one), and it emits a machine-stamped evidence block. **The ONE evidence
   rule:** when CI ran validate on the commit you're describing, CITE that run by
   run id/link — never paste a copy, it goes stale; only when no CI run exists for
   the commit (purely local close) does the machine block from the FINALIZING run
   get pasted, verbatim, never retyped or hand-edited (classes:
   skip-report-missing-record-citation, unverifiable-claim, stale-evidence).
4. Write the session arc (``docs/session_arcs`/YYYY-MM-DD_slug.md`), add it to the
   README index, and **tag it** `arc/YYYY-MM-DD_slug`.
   Mirror key decisions to `docs/memory/`.
5. Append honest friction/feedback to `docs/AGENT_FEEDBACK.md` (what slowed you
   down, what to automate next) — periodically ingested to improve the workflow.
6. Note any new external dependency in STATE.md.
7. Review `docs/RECORD.md` OPEN rows (the no-silent-deferrals register):
   resolve, re-affirm, or escalate each. A row whose resolution trigger has
   fired but wasn't acted on is a defect, not a backlog item.
8. Run `tools/kaizen_trends.py` (also runs inside validate) and act on
   any finding — an alarm is a due fix, not information. Append the session's
   Kaizen ledger rows (`docs/metrics/KAIZEN_LEDGER.md`):
   M1/M2/M5 per merged PR, M4 gate-gap fixes, M6 po harvests (M3 escapes are
   recorded the moment they're found, never batched). See `docs/KAIZEN.md`.

---

**One-line version:** reconcile → trust STATE.md → skim latest arc → know the
rules → pull from TODOS.md → work → checkpoint before compaction → at close:
update STATE/queue → re-reconcile → `tools/validate` (green, no unresolved skips)
→ write + tag the arc → append AGENT_FEEDBACK.
