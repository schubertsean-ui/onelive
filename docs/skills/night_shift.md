# Night Shift — Autonomous Agent Loop Skill

SUMMARY: how an agent runs OneLive work autonomously and safely while the founder
is away. Defines the orchestration loop (pick work → inner loop → verify →
checkpoint), the layered exits that make it safe to walk away from, the
open-vs-closed loop choice per task, model-cost discipline, and the hard stop
conditions. This is the loop that `tools/validate` gates and that
`docs/OPERATING_RULES.md` §2 (Loops/Kaizen) describes at the per-change level;
this doc is the *orchestration* layer above a single change. Read with
`docs/SESSION_START.md` (session bookends) and `TODOS.md` (the work queue).

---

## 0. When this skill applies

Use this when you are asked to work **autonomously / asynchronously** — a batch
of queue items, an overnight run, or any "go do this while I'm gone." For a
single interactive change, `docs/OPERATING_RULES.md` §2a (the inner loop) is
enough; you do not need the full orchestration below.

The prime directive from `OPERATING_RULES.md` §0 still governs everything here:
**trust is the foundation; when a rule and a deadline conflict, the rule wins.**
Autonomy is leverage, never an excuse to lower the bar.

---

## 1. The orchestration loop (outer loop)

```
Open (reconcile) → Pick one queue item → [inner loop until done] → Verify (tools/validate)
   → Checkpoint (arc + STATE.md) → Pick next … → Close (feedback + full validate + tag)
```

### 1.1 Open — reconcile before trusting anything
Run `docs/SESSION_START.md` Step 1 (`tools/session_reconcile.py`). If it exits 2
with a **material contradiction**, STOP and fix STATE.md prose first — never build
on a contradicted claim. If it exits 2 with **UNVERIFIED** (no DB in sandbox),
verify the printed SQL via the Supabase connector before relying on those facts.

### 1.2 Pick one item from the queue
`TODOS.md` is the work queue. Take the **highest-priority unblocked** item. Never
start something that depends on an **open founder decision** (those are listed in
`TODOS.md` / STATE.md "Open founder decisions") — flag it and skip to the next
unblocked item. One item at a time; finish or cleanly park it before the next.

### 1.3 Inner loop (per change) — OPERATING_RULES §2a, verbatim discipline
```
Understand → Implement → Self-review against §1 quality bar → Fix what review finds
   → Verify (targeted tests / real run / DB check) → Loop until review finds nothing new AND verification is green
```
Then run a **cross-agent review** on anything non-trivial (`tools/agent_review
--persona <p> --target <ref>`), choosing the persona(s) that own the risk
(security/performance/domain-truth-and-trust/etc. — see `docs/review_personas/`).
A different model reviews than the one that wrote the code.

### 1.4 Verify the item
Run the checks relevant to the change, then keep going. The **full** gate
(`tools/validate`) runs at checkpoints and at close, not after every tiny edit.

### 1.5 Checkpoint (before compaction risk, per OPERATING_RULES §4)
At natural heavy moments — after a substantial item, a batch of decisions, or
before context is at risk — append/update the dated session arc
(`docs/session_arcs/YYYY-MM-DD_slug.md`) and refresh STATE.md prose. Losing state
is the failure this prevents: an arc must let a *different* agent resume mid-shift.

---

## 2. Layered termination — what makes it safe to walk away

A loop with no exit is the most expensive mistake there is. **Every** autonomous
run stacks ALL of these; any one alone is insufficient:

1. **Goal verifier** — the item's definition-of-done is met and `tools/validate`
   is green (skips are not green — see §5). This is the *only* success exit.
2. **Iteration cap** — a hard max attempts per queue item (default: **5** inner-loop
   iterations on one item). Hitting it = park the item with a written arc note
   explaining where it stalled; move on. Do not grind.
3. **Time / token budget** — a wall-clock or token ceiling for the whole shift.
   On breach, finish the current item's checkpoint and run the close sequence.
4. **No-progress detection** — if the last **3** iterations did not change the
   verifier result (same tests failing, same lint finding), STOP that item — the
   loop is spinning. Record the stuck signature in the arc so the next attempt
   doesn't repeat the dead end.

These four turn "run it and hope" into "run it and trust." Encode budgets
explicitly at the start of the shift, in the arc.

---

## 3. Open vs. closed loops — choose deliberately, per item

State which kind each queue item is *before* starting it; it sets the budget and
the verifier:

- **Closed loop** — bounded task, fixed target, cheap and safe. Example: "make the
  failing test pass without editing the test," "apply the lint --fix and re-green."
  Tight iteration cap, cheap models, strict external verifier. Default for
  maintenance and bug-fix items.
- **Open loop** — exploratory, novel approach, more budget for more upside.
  Example: "propose 5 new real source-catalog entries," "try a better dedupe
  heuristic." Wider budget, a frontier model for the hard step, and a **human
  checkpoint** before anything lands (open loops rarely finish unattended).

If you cannot say which one an item is, it is not ready to run autonomously —
flag it for the founder.

---

## 4. Model-cost discipline (loops make 10–100× the calls)

Route each step to the **cheapest capable** model; never use a frontier model for
work a small one handles:

- **Small / fast** — classification, marker detection, "which persona applies,"
  mechanical edits, running the checks. (lint/trust_gate/commit_sweep are pure
  code — free.)
- **Mid** — drafting an implementation, writing a doc, first-pass self-review.
- **Frontier** — only the final hard review on trust-critical code (the
  gate/promotion pipeline, auth, RLS, extraction prompts) and the cross-agent
  review persona pass.

Reuse the stable prefixes of prompts (architecture invariants, conventions) so you
are not paying to re-establish context every iteration. **This routing is the one
world-class gap the harness has not yet codified** — until a router exists, apply
this by judgment and note cost surprises in `docs/AGENT_FEEDBACK.md`.

---

## 5. Session close (finalize — non-negotiable before you stop)

1. Update STATE.md prose (what changed, what's next). Do **not** hand-edit the
   `GROUND_TRUTH` json block.
2. Run `tools/session_reconcile.py --heal` so the ground-truth block matches
   reality at close (next session starts verified).
3. Run **`bash tools/validate`** — the full gate. **RESULT: FAIL → you are not
   done; fix and re-run. SKIPPED checks are NOT green** (esp. visual_regression):
   resolve them or explicitly hand them to the founder. Never stop on red, never
   count a skip as a pass.
4. Write/finalize the session arc; add it to `docs/session_arcs/README.md`.
5. **Tag the arc** so it's findable later (see `session_arcs/README.md` git-tag
   convention): `git tag arc/YYYY-MM-DD_slug <commit>`.
6. Append honest friction/feedback to `docs/AGENT_FEEDBACK.md` (item 8) — what
   slowed you down, what should be automated next, any cost surprise.
7. Note any new external dependency in STATE.md (CLAUDE.md review rule #3).

---

## 6. Hard stop conditions (bail to the founder, do not push through)

Stop the autonomous run and leave a clear arc note + notification when:

- `session_reconcile.py` reports a **material contradiction** you cannot resolve
  from ground truth alone.
- An item requires an **open founder decision** (STATE.md "Open founder decisions").
- `tools/validate` is **red** and the fix is not obvious/safe within the iteration cap.
- Any **irreversible action** is needed (deploy, migration apply, sending anything,
  moving money). Per OPERATING_RULES §9 and CLAUDE.md, these are
  human-checkpoint gated — draft/PR it, never execute it autonomously.
  **Exception — PR merges (founder-directed 2026-07-18, `docs/memory/decisions/2026-07-18_agent-merges-on-green.md`):** the agent merges its own PR once EVERY gate is green (evaluator APPROVE + all required checks on the final head) and notifies the founder; merging on red or with any gate pending stays forbidden.
- The trust invariants (`trust_gate.py`) would have to be weakened to proceed.

The point of the loop is leverage, not recklessness. Park cleanly, checkpoint, and
surface the gap — surfacing a blocker beats a confidently-wrong autonomous change.
