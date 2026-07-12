# OneLive — Operating Rules (Loops, Harness & Kaizen)

**Status:** Active convention. Read alongside `CLAUDE.md` (architecture) and
`docs/session_arcs/README.md` (session continuity). `CLAUDE.md` says *what* the
system is; this doc says *how we work on it*.

**Owner:** Sean Schubert. **Established:** 2026-07-10.

---

## 0. Prime directive — trust is the foundation, integrated not bolted on

OneLive is a truth-first live-events platform. Trust is not a feature, a badge, or
a later phase — it is the property every layer must preserve. Every rule below
exists to protect it. When a rule and a deadline conflict, the rule wins; we cut
scope, never trust.

---

## 1. The quality bar (non-negotiable)

> **No "ok" code. No "no immediate problems." Nothing lingers, is ignored, or is
> set for later.**

Concretely, before anything is considered done:

- **No silent degradation.** Code must never make "we failed" look identical to
  "there was nothing to do." This is the project's founding anti-pattern (see §3).
- **No swallowed errors.** `except: pass` and `except Exception: <blank fallback>`
  are banned unless the caught branch is *itself* logged/audited and justified in
  a comment.
- **No dead code / unreachable features.** If a parameter, hook, or path can't
  actually fire in production, it isn't done — wire it or remove it.
- **No deferred cleanup.** If a review turns up a defect, fix it in the same
  change. Do not write a TODO and move on. A known issue left behind is a broken
  window.
- **No red tests.** Never write new work (or docs) on top of a failing test. Green
  first, then proceed.
- **Findings are claims until verified.** Row counts, scores, "it works" — prove
  them against ground truth (DB query, passing test, real run) before asserting.

If something is merely "fine," it is not done. State the gap and close it.

---

## 2. Loops — the improvement engine (Kaizen)

We operate in tight, repeating loops. Each loop is small, ends in a verified
state, and feeds the next. This is the Kaizen practice applied to the build.

### 2a. The inner loop (per change)
```
Understand → Implement → Self-review against §1 → Fix what review finds → Verify (tests/DB/real run) → Loop until clean
```
- Self-review is not optional and not a rubber stamp. Actively hunt for the ways
  the change could silently be wrong. The review that found the dropped
  `_provenance` key and the null-city bug is the standard, not the exception.
- A loop iteration ends only when review finds nothing new *and* verification is
  green.
- **Mechanical backstop:** the pre-commit hook (`tools/install_hooks.sh` →
  `lint.py --fix` + `trust_gate.py`) enforces the floor on every commit, and
  `bash tools/validate` runs the *full* gate (trust_gate, lint, full pytest,
  eval_harness, perf benchmarks, test_audit, commit_sweep, visual_regression) at
  checkpoints and at session close. "Verify" is not a vibe — it is these checks
  green. A SKIPPED check (e.g. visual_regression with no booted app) is *not*
  green; resolve it or surface it, never count it as a pass.
- For non-trivial changes, add a **cross-agent review** (`tools/agent_review
  --persona <p> --target <ref>`) by a different model than wrote the code, using
  the `docs/review_personas/` lens that owns the risk. Autonomous/overnight runs
  follow `docs/skills/night_shift.md` (orchestration + layered exits + hard stops).

### 2b. The weekly Kaizen loop (per week)
Once a week, step back from feature work and improve the *system that builds the
system*:
- What defect classes recurred? Encode a guard (a rule here, a test, a lint) so
  they can't recur silently.
- What did a session-arc reveal about drift between STATE.md and reality?
- What manual step happened 3+ times and should be automated? (Add a script to
  `tools/` — see `tools/README.md` for the authoring conventions — or a check to
  `tools/lint.py` / `tools/validate`.)
- What friction did agents log in `docs/AGENT_FEEDBACK.md` since last week? Ingest
  it here and fix the top items.
- Update this doc and `CLAUDE.md` review criteria with anything learned.

### 2c. Definition of "improvement"
An improvement must be *measurable* or *structural*, not vibes. Prefer:
- a new test that would have caught a real bug,
- a metric moved in the right direction (e.g. extraction hallucination_rate),
- a silent path made observable (audit/log),
- a manual step removed.

---

## 3. Trust rules (how §0 becomes code)

1. **Fail loudly on misconfiguration; degrade safely on transient faults.**
   Precedent: `worker/resolve_entities.py::_fuzzy_match` re-raises on SQLSTATE
   42883 (schema misconfig) but soft-falls-back on other errors. Mirror this split
   everywhere. The AI provider (`ai/claude_provider.py`) applies it: raise
   `ExtractionConfigError` on no-key/unknown-model/bad-schema; retry+degrade on
   429/5xx; **audit** every degrade so it is never invisible.
2. **The AI step never publishes.** Extraction only proposes candidates;
   promotion always passes the multi-confirm gate (`worker/gating.py`).
3. **Everything auditable.** Every stage leaves a trail. AI extractions carry
   `_provenance` (provider, model, prompt_version, timestamp). Degradations and
   fuzzy merges write to `audit_log`.
4. **Never fabricate to fill a gap.** Null/empty is always the correct answer when
   the source doesn't state a value. Enforced by the extraction prompt and by
   measuring `hallucination_rate` (`ai/eval_harness.py`) — the KPI behind DoD #41.
5. **Disputed data is shown as disputed, never deleted** (4-state confidence model
   in `CLAUDE.md`).
6. **Tastemaker (human opinion) content never enters the event
   candidate/gating/promotion pipeline** — separate trust category.

---

## 4. The Harness — in-session discipline (NOT a cron)

The Harness runs by judgment during a session, not on a clock. "Assess where you
are prior to the need to compact."

**Session open — reconcile before trusting anything:**
- Run `docs/SESSION_START.md`, which runs `tools/session_reconcile.py`. It verifies
  STATE.md's machine-readable ground-truth block against live git/PRs/DB and
  classifies drift: benign drift auto-heals; a **material contradiction hard-stops
  (exit 2)** until STATE.md is corrected; unverifiable critical facts are flagged
  loudly (never treated as "fine").
- STATE.md is only trusted after this reconcile is clean. This is the mechanical
  enforcement of "findings are claims until verified" applied to STATE.md itself.

**During — checkpoint proactively at heavy moments:**
- Before a context-heavy stretch risks compaction, write/append a session arc so
  no decision, finding, or artifact is lost.

**Session close — finalize:**
- Update STATE.md (the always-current rollup), then **re-run
  `session_reconcile.py --heal`** so the ground-truth block matches reality at
  close and the next session starts from a verified snapshot. Write the session arc
  (`docs/session_arcs/YYYY-MM-DD_slug.md`, indexed in the README), mirror to
  memory. Note any new external dependency in STATE.md (CLAUDE.md review rule #3).

---

## 5. Standard of "world-class"

We are building toward world-class technology, code, and UX/UI — with trust
integrated throughout. Practically, a change clears the bar when:

- **Technology:** correct failure semantics, observable, no silent paths, real
  metrics governing quality (not exact-match toys).
- **Code:** drop-in where it claims to be, decoupled (the provider knows nothing
  about the DB — it takes an `audit_hook`), tested including the failure and
  degradation paths, comments explain *why* not *what*.
- **UX/UI:** trust made legible to the user without nagging — "infrastructural
  trust" over loud badges. Confidence states and provenance surface honestly.
- **Verified:** proven against ground truth before being called done.

---

## 6. Presenting options (communication standard)

Whenever options are presented, never present a neutral menu. Always lead with a
recommendation and its reasoning. Every set of options must include:

1. **The recommended choice**, stated up front.
2. **Why** it's recommended (the reasoning, tied to the goal at hand).
3. **The recommended order/sequence** when order matters — and why that order.
4. **A standalone explanation of each option** — what it is, what it does, and
   what choosing it means — so each can be assessed on its own merits, not only
   as a foil to the recommendation.
5. **Tradeoffs** — of the recommendation *and* of each alternative, so the choice
   is informed, not just asserted.

This applies to plans, technical choices, sequencing, and `ask_user_question`
prompts alike. A recommendation can still be overridden — but the default is a
considered position, not a shrug.

---

## 7. When in doubt

- Prefer surfacing a gap over hiding it.
- Prefer a smaller verified step over a larger unverified one.
- Prefer fixing now over noting for later.
- Ask only as a last resort, after using tools to answer the question yourself.
