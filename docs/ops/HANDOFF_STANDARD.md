# 1Live — The Handoff Standard (world-class handoffs, and the proof discipline)

**Status:** Canon, founder-directed 2026-08-03 ("Save to canon and repo and arc that
all handoffs are to be world class with clarity about what that means. Ensure the
proof piece is also codified and saved."). Pointer from `docs/OPERATING_RULES.md`
(§6a); the live handoff artifact is `docs/ops/NEXT_SESSION_KICKOFF_PROMPT.md`, which
MUST meet this standard.

**What a "handoff" is here:** any prompt, document, or message that transfers work to
a next session, another agent, or a future self so it can continue without the author
present. The next-session kickoff prompt is the canonical case; a mid-task checkpoint
or an escalation packet is the same discipline at smaller scale.

---

## 1. What "world-class" means for a handoff (the eight properties — all required)

A handoff is world-class only if every one of these holds. Missing any one is a defect.

1. **Self-contained.** The receiver needs nothing but this handoff plus the repo. No
   reliance on chat history, on "where we left off," or on the author being reachable.
2. **Disk is the source of truth.** It tells the receiver to DERIVE state from disk
   (reconcile + read in full), never to trust the handoff's own snapshot blindly — and
   it says exactly which files to read, in full, first (Rule Zero).
3. **Current AND proven.** Its state snapshot reflects VERIFIED ground truth at write
   time (git/PR/DB checked, not remembered), and it SHOWS the proof or the command that
   reproduces it (see §2). A snapshot that cannot be re-derived is not allowed.
4. **Prioritized, actionable remaining work.** The exact next actions, highest-priority
   first, each marked unblocked / blocked-on-what. The receiver can pick item 1 and act.
5. **Failure memory.** The specific anti-patterns that have bitten us, named so the
   receiver recognizes the moment — each tied to the rule that governs it.
6. **Interaction contract.** How to operate: proceed on ratified work; interrupt only
   for founder-crucial; merge rules; communicate in the five-part protocol; no
   busy-poll, no timers.
7. **Decisions separated by ownership.** Founder HOLDS (do not build past) and
   founder-crucial items (escalate, never decide) are listed distinctly from agent-
   decidable work, so the receiver never silently makes a founder call.
8. **Plain, honest, linked.** Plain language for a smart non-engineer; honest
   trade-offs (never a choice framed as free); exact links; asks consolidated into ONE
   list; no stale beliefs carried forward (a claimed blocker is verified before it is
   repeated — see the stale-record lesson).

## 2. The proof discipline (currency/completeness is PROVEN, not asserted)

Founder directive, verbatim: *"confirm all is current - I mean everything and you must
prove it."* This generalizes OPERATING_RULES §1 ("findings are claims until verified")
to every claim of currency, completeness, or done-ness — in a handoff, a status report,
or a session close.

**The rule:** never write "everything is current" / "all reconciled" / "done" / "green"
as an assertion. Show the EVIDENCE — a command and its output, a passing gate, a git/API
check — that a reader could re-run to confirm it. If you cannot produce the evidence,
you do not yet know the claim is true; say what is unverified instead.

**The standing proofs (mechanical, re-runnable — this is the "proof piece", saved):**
- **STATE.md is not stale:** `python tools/staleness_check.py` — fails the build the
  moment `origin/master` advances past the last commit that updated STATE.md
  (zero-tolerance; measures "merges since STATE last changed", not a fudge-factor
  commit count). Also fails on a missing/malformed/off-history marker. Blocking in
  `tools/validate`.
- **STATE reflects the true tip:** at session close the block's
  `reconciled_through_commit` is set to the current `git rev-parse origin/master`, so
  master's tip is a STATE-touching commit and the guard reads drift 0.
- **STATE's live handoff matches the record:** `tests/test_live_state_consistency.py`
  (in the pytest suite) — STATE's live NEXT block may not direct work at a RESOLVED
  RECORD row.
- **The tree is green:** `bash tools/validate` → `RESULT: … no gate FAILED` (a SKIP is
  not a pass — cite its `docs/RECORD.md` row; advisories are not passes either).
- **PR/DB facts:** verified via the GitHub MCP tools and the Supabase connector when
  present; recorded UNVERIFIED (never guessed) when the environment lacks them.

A currency/completeness claim in any handoff or close MUST cite the relevant subset of
these, with output, not prose. Session close advances the marker to the session's head
so the next `staleness_check` starts clean.

## 3. Enforcement

- `docs/OPERATING_RULES.md` §6a points here; Rule Zero's precision clause already bars
  asserting an unproven claim as fact.
- `tools/staleness_check.py` (blocking) + `tests/test_live_state_consistency.py` are the
  mechanical half — a stale or self-contradictory handoff snapshot fails the gate.
- The kickoff artifact `docs/ops/NEXT_SESSION_KICKOFF_PROMPT.md` is reviewed against the
  §1 eight-property checklist each time it is rewritten at session close.
