# OPERATING RULES — Loops, Harness & Kaizen

> **KERNEL DOC — project-agnostic, inherited verbatim.** This file describes the
> METHOD and nothing about any particular product. Project specifics (domain,
> stack, trust surface, tool and gate names, thresholds) live in `OVERLAY.md`.
> Text in `[square brackets]` is a placeholder the overlay must bind.

**Status:** Active convention. Read alongside the project charter (architecture)
and ``docs/session_arcs`/README.md` (session continuity). The charter says *what*
the system is; this doc says *how we work on it*.

**Owner:** [founder name]. **Established:** [date adopted].

---

## 0. Prime directive — trust is the foundation, integrated not bolted on

This project is truth-first. Trust is not a feature, a badge, or a later phase —
it is the property every layer must preserve. Every rule below exists to protect
it. When a rule and a deadline conflict, the rule wins; we cut scope, never trust.

What "trust" concretely means here — which surface must never carry an unverified
claim, and what the states of a claim are — is declared once in `OVERLAY.md` as
[trusted surface] and [trust-state model]. The rules below are written against
those names and do not change when the product does.

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
  them against ground truth (a query, a passing test, a real run) before asserting.
- **No research without the primary source.** (Founder directive, verbatim,
  inherited from the origin project: "Don't ever assume or summarize or proceed to perform any
  strategic or deep research that you are unable to access the primary
  documents or files or information.") If the primary
  document/file/data behind a strategic or deep-research task cannot be
  accessed (paywall, 403, missing attachment, login gate), the research does
  NOT proceed on excerpts, mirrors, search summaries, or memory — however
  heavily caveated. STOP that thread, deliver a blocker report naming exactly
  what was inaccessible and the smallest founder action that unblocks it
  (paste the text, attach the file, grant access), and only continue work
  that does not depend on the inaccessible source. Secondary-source
  reconstruction is not a fallback; it is the defect.

If something is merely "fine," it is not done. State the gap and close it.

---

## 2. Loops — the improvement engine (Kaizen)

We operate in tight, repeating loops. Each loop is small, ends in a verified
state, and feeds the next. This is the Kaizen practice applied to the build.

### 2a. The inner loop (per change)
```
Understand → Implement → Self-review against §1 → Fix what review finds → Verify (tests/data/real run) → Loop until clean
```
- Self-review is not optional and not a rubber stamp. Actively hunt for the ways
  the change could silently be wrong. The review that finds a dropped provenance
  key or a null-field bug before any gate does is the standard, not the exception.
- A loop iteration ends only when review finds nothing new *and* verification is
  green.
- **Mechanical backstop:** the pre-commit hook (`tools/lint.py` `--fix` + [project trust gate])
  enforces the floor on every commit, and `tools/validate` runs the *full* gate at
  checkpoints and at session close. "Verify" is not a vibe — it is these checks
  green. A SKIPPED check (e.g. a gate whose preconditions are absent) is *not*
  green; resolve it or surface it, never count it as a pass.
- For non-trivial changes, add a **cross-agent review** ([agent review tool]
  `--persona <p> --target <ref>`) by a different model than wrote the code, using
  the `docs/review_personas/` lens that owns the risk. Autonomous/overnight runs
  follow the project's [autonomous run skill] (orchestration + layered exits +
  hard stops).

### 2b. The weekly Kaizen loop (per week)
Once a week, step back from feature work and improve the *system that builds the
system*:
- What defect classes recurred? Encode a guard (a rule here, a test, a lint) so
  they can't recur silently.
- What did a session arc reveal about drift between STATE.md and reality?
- What manual step happened 3+ times and should be automated? (Add a script to
  `tools/` — see its README for the authoring conventions — or a check to
  `tools/lint.py` / `tools/validate`.)
- What friction did agents log in `docs/AGENT_FEEDBACK.md` since last week? Ingest
  it here and fix the top items.
- Update this doc and the charter's review criteria with anything learned.

### 2c. Definition of "improvement"
An improvement must be *measurable* or *structural*, not vibes. Prefer:
- a new test that would have caught a real bug,
- a metric moved in the right direction (e.g. [primary quality metric]),
- a silent path made observable (audit/log),
- a manual step removed.

---

## 3. Trust rules (how §0 becomes code)

1. **Fail loudly on misconfiguration; degrade safely on transient faults.**
   Split the two explicitly at every boundary: a wrong schema, a missing key, an
   unknown model id is a hard raise; a 429/5xx or a timeout may retry then
   degrade — and **every degrade is audited** so it is never invisible.
   (ILLUSTRATIVE EXAMPLE from the origin project: a fuzzy-match helper re-raised
   on the SQLSTATE that means "the trigram extension is not installed" — a
   misconfiguration — but soft-fell-back on other errors; the AI provider raised
   `ExtractionConfigError` on no-key/unknown-model/bad-schema and retried-then-
   degraded on 429/5xx with an audit row per degrade.)
2. **The generative step never publishes.** A model-produced value only ever
   *proposes* a candidate; reaching [trusted surface] always passes [promote
   gate]. No path, direct or indirect, may skip it.
3. **Everything auditable.** Every stage leaves a trail. Model outputs carry
   provenance (provider, model, prompt version, timestamp). Degradations and
   any fuzzy/heuristic merge write to an audit log.
4. **Never fabricate to fill a gap.** Null/empty is always the correct answer when
   the source doesn't state a value. Enforced by the prompt AND measured by
   [primary quality metric] in [eval harness] — a rule that is only stated is not
   enforced.
5. **Contested data is disclosed as contested, never deleted.** Whatever the
   project's [trust-state model] calls its lowest-trust and contradicted states,
   those records stay visible and labelled; suppression is not a trust action.
6. **Trust categories stay isolated.** Content of a different trust class (human
   opinion, marketing copy, user submissions) never enters the verified-data
   pipeline — declared in `OVERLAY.md` as [separate trust category], and checked
   structurally (imports, shared tables, shared helpers), not by convention.

---

## 4. The Harness — in-session discipline (NOT a cron)

The Harness runs by judgment during a session, not on a clock. "Assess where you
are prior to the need to compact."

**Session open — reconcile before trusting anything:**
- Run `docs/SESSION_START.md`, which runs `tools/session_reconcile.py`. It verifies STATE.md's
  machine-readable ground-truth block against live ground truth and classifies
  drift: benign drift auto-heals; a **material contradiction hard-stops
  (exit 2)** until STATE.md is corrected; unverifiable critical facts are
  flagged loudly (never treated as "fine").
- STATE.md is only trusted after this reconcile is clean. This is the
  mechanical enforcement of "findings are claims until verified" applied to
  STATE.md itself.

**During — checkpoint proactively at heavy moments:**
- Before a context-heavy stretch risks compaction, write/append a session arc so
  no decision, finding, or artifact is lost.

**Session close — finalize:**
- Update STATE.md (the always-current rollup), then **re-run `tools/session_reconcile.py`
  `--heal`** so the ground-truth block matches reality at close and the next
  session starts from a verified snapshot. Write the session arc
  (``docs/session_arcs`/YYYY-MM-DD_slug.md`, indexed in the README), mirror to
  `docs/memory/`. Note any new external dependency in STATE.md.

**External-stall escalation ladder:**
When an external system misses an expected event (a scheduler slot, a webhook,
a deploy callback):
- **First miss:** verify our own configuration immediately and completely
  (config on the authoritative branch, service state via API). Apply every
  self-serve mitigation in the same pass — do not save any available action
  for later.
- **Second miss:** if the remaining fix needs the founder's hands, the consolidated
  ask goes out NOW — options, recommendation, tradeoffs, links. Never
  wait for a round number of misses or an "escalation checkpoint" hours out.
- **Watching cadence:** watch interval = ONE expected-event interval + provider
  lag allowance, never multi-interval windows.
- **A watch turn never ends unarmed:** success is silent (CI success and
  merges deliver no webhook) — before ending ANY turn that awaits an
  external outcome, arm a wake-up for it; if the preferred scheduling
  mechanism is unavailable or declined, use the best available fallback
  and SAY SO. Bridging actions (manual runs, pings) buy time; they never
  substitute for the escalation.
- ILLUSTRATIVE EXAMPLE (origin project, kept because it is the rule's proof):
  a scheduled job's first missed slot was at 01:07Z and the owner ask was not
  delivered until 04:02Z, while the fix — a two-tap disable/enable only the
  owner could perform — was available from the first miss. Three hours of
  patience with a stuck external scheduler was a process defect, not diligence.
  Separately, an APPROVE sat unmerged for 6.5 hours because the awaiting turn
  ended with no timer — which is why "a watch turn never ends unarmed" is a rule
  and not advice.

---

## 5. Standard of "world-class"

We are building toward world-class technology, code, and UX/UI — with trust
integrated throughout. Practically, a change clears the bar when:

- **Technology:** correct failure semantics, observable, no silent paths, real
  metrics governing quality (not exact-match toys).
- **Code:** drop-in where it claims to be, decoupled (ILLUSTRATIVE EXAMPLE: the
  model provider knows nothing about the database — it takes an `audit_hook`),
  tested including the failure and degradation paths, comments explain *why* not
  *what*.
- **UX/UI:** trust made legible to the user without nagging — "infrastructural
  trust" over loud badges. Trust states and provenance surface honestly.
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

This applies to plans, technical choices, sequencing, and interactive question
prompts alike. A recommendation can still be overridden — but the default is a
considered position, not a shrug.

---

## 7. When in doubt

- Prefer surfacing a gap over hiding it.
- Prefer a smaller verified step over a larger unverified one.
- Prefer fixing now over noting for later.
- Ask only as a last resort, after using tools to answer the question yourself.
