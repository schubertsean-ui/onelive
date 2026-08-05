# 1Live — Operating Rules (Loops, Harness & Kaizen)

**Status:** Active convention. Read alongside `CLAUDE.md` (architecture) and
`docs/session_arcs/README.md` (session continuity). `CLAUDE.md` says *what* the
system is; this doc says *how we work on it*.

**Owner:** Sean Schubert. **Established:** 2026-07-10.

---

## Rule Zero — read completely before acting; the founder greenlight gates the work (founder-directed 2026-08-02, from repeated skim/fragment failures — this rule outranks every rule below it)

**No action of any kind — building, fixing, scanning, code or doc changes, merges,
migrations, or any substantive response that commits to or performs work — is
permitted until the controlling rules and documents for that task have been read
COMPLETELY: in full, end to end, with NO skimming, skipping, reading in fragments,
or summarizing, and that complete reading has been explicitly confirmed.**

- **A partial read is treated as NO read.** Reading a document in fragments —
  offset/limit slices, truncated tool output, one page of many — and then acting
  on the fragment is the exact failure this rule exists to prevent. If a document
  is too large to read in one call, read every part of it before acting; never act
  on the part you have seen.
- **Skimming, skipping, fragmenting, or summarizing the controlling rules in place
  of reading them is FORBIDDEN.** It is a violation, not a shortcut. Cost or
  context pressure is never an excuse — Rule Zero's enforcement (below) removes the
  excuse.
- **The founder greenlight gates the work.** The enumerated actions are not
  permitted on the founder's product or repository unless the founder has
  explicitly greenlit that work. A **ratified contract, a queued TODO the founder
  set, or a direct founder instruction IS the greenlight** (this preserves the
  charter's "proceed on ratified work" — ratified means greenlit). When it is not
  clear that the work is greenlit, **STOP and ask** — never proceed on an
  assumption of authorization.
- **State it precisely — CONFLATION is its own violation (added 2026-08-03,
  founder-directed).** Reading completely is necessary but not sufficient. Once
  read, anything you then ASSERT about a rule, invariant, or guardrail must be
  stated in the canon's own terms: **quote the controlling text; never paraphrase
  an invariant from memory**, and never state it narrower or broader than the doc
  does. And distinct concepts must be kept distinct — collapsing two separate
  things into one claim is a CONFLATION, and a conflation asserted as fact is a
  violation exactly as a fragment read is. Load-bearing separations that have
  already bitten us, kept apart by name: **trust in a fact ≠ the right to
  reproduce an image** (credibility vs copyright/license); **grounding text ≠
  displayed media** (Descriptor-Foundry faithfulness gate vs media
  provenance/license gate); **resolving an entity's identity ≠ crawling its
  website** (identity-first cascade vs raw fetch); **"the entity's own domain"
  includes the venue/organizer as host, not only the artist.** When you feel two
  ideas collapsing into one sentence, STOP, separate them, and cite each to its
  source before you assert it. **Never frame against an impossible absolute.**
  "Risk-free", "perfect", "zero risk", "true by construction", "guaranteed" — these
  do not exist; invoking one as a baseline manufactures a false shortfall (or a
  false assurance) and is a violation of this rule. Everything is a trade-off:
  state the trade-off and name the live procedure that manages it as far as is
  humanly and technologically possible — that IS the standard, not the absolute.

**Why this rule exists (the failures it fixes):** on 2026-08-02 the agent twice
read the controlling documents (STATE.md, this file, the `/tonight` UI canon) in
fragments and acted on the partial picture — it proposed a delay/timer that §6a
explicitly bans, and it mis-stated a trust invariant ("AI never publishes" — the
canon, now worded gate-custodied publication (2026-08-03), is "AI never
publishes *unvalidated*", satisfied by the gate). Both errors
trace to the same root: reading fragments instead of whole documents. **Extended
2026-08-03 (founder-directed):** the same work then produced CONFLATION errors of
the second kind — stating an invariant more narrowly than the canon ("only the
entity's own image" when canon also allows the venue/organizer's own-domain
image), and merging distinct concepts (identity-resolution vs website-crawl;
grounding vs display). Complete reading fixes the input; precise, un-conflated
statement fixes the output — **both are now required.** These cost the founder
time and trust. They do not recur.

**Enforcement — harness + brain + caching (so the rule is mechanical, not
remembered):**
1. **Harness** — `docs/SESSION_START.md` Step 4 mandates reading the controlling
   docs IN FULL at session open, before any work; `tools/validate` remains the
   end-of-shift gate.
2. **Brain** — this rule and its failure-lessons live in `docs/memory/`
   (`decisions/2026-08-02_complete-reading-gate.md`,
   `gotchas/2026-08-02_skim-fragment-is-no-read.md`, and the conflation lesson
   `gotchas/2026-08-03_conflation-is-a-violation.md`) so a future session RETRIEVES
   them at start rather than relying on memory.
3. **Caching** — the controlling docs are read once, in full, early in the session;
   being stable, they sit in the cached prompt prefix, so complete re-reading is
   cheap and there is no cost excuse to skim.

Changing, narrowing, or waiving Rule Zero is founder-crucial — agents may not relax it.

---

## 0. Prime directive — trust is the foundation, integrated not bolted on

1Live is a truth-first live-events platform. Trust is not a feature, a badge, or
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
- **No research without the primary source.** (Founder directive, verbatim,
  2026-07-24: "Don't ever assume or summarize or proceed to perform any
  strategic or deep research that you are unable to access the primary
  documents or files or information." Decision record:
  `docs/memory/decisions/2026-07-24_primary-source-gate.md`.) If the primary
  document/file/data behind a strategic or deep-research task cannot be
  accessed (paywall, 403, missing attachment, login gate), the research does
  NOT proceed on excerpts, mirrors, search summaries, or memory — however
  heavily caveated. STOP that thread, deliver a blocker report naming exactly
  what was inaccessible and the smallest founder action that unblocks it
  (paste the text, attach the file, grant access), and only continue work
  that does not depend on the inaccessible source. Secondary-source
  reconstruction is not a fallback; it is the defect.
- **A repeated error is a finding, not a rhythm.** (Founder-directed
  2026-07-25 and ratified by the founder as a global standing condition;
  the verbatim directive lives in the decision record —
  `docs/memory/decisions/2026-07-25_repeated-error-investigation-rule.md`
  — kept there per dissemination minimization, r12 nit.)
  The SAME error, warning, or anomalous message appearing more than twice —
  in a loop, across polls, across tool calls, across sessions — is itself a
  defect signal that MUST be investigated at its root before (or alongside)
  any workaround: name the cause, decide deliberately whether the fix is
  ours, upstream, or a justified accepted-cost workaround, and record the
  determination (session note or Kaizen row) so the repetition never
  normalizes. Routinizing a recurring error without a recorded root-cause
  determination is the defect, whatever the error turns out to be. Applies
  to every project adopting the universal kernel (K-GATE class; queued as a
  kernel amendment in the universal model doc).

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
- **Build through the Construction Loop.** (Founder-directed 2026-07-25;
  canon: `docs/skills/construction_loop.md`; verbatim directive + RCA:
  `docs/memory/decisions/2026-07-25_construction-loop-directive.md`.)
  Every substantive build runs the seven stages — A3-form contract →
  ledger-seeded premortem (tree, not chain) → BLOCKING memory retrieval
  (cite matched green examples and red classes before any design is
  accepted; "no matches" is a printed result, never silence) → scored
  path selection (precedent collapses the search; no precedent = 2-3
  independent candidates judged against the contract) → small-batch
  execution with validate BEFORE the evaluator → lessons committed only
  in machine-consumed form (gate rule / retrieval token / regression
  case — prose-only rows are open defects) → rounds-to-APPROVE and
  repeat-class rate trended as the loop's own health metrics. The loop
  adds an upstream pass; no downstream gate relaxes, ever.

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
2. **Publication is gate-custodied** (reworded 2026-08-03 from the shorthand
   "the AI step never publishes" — decision record
   `docs/memory/decisions/2026-08-03_invariant-wording-gate-custody.md`;
   mechanics unchanged). Extraction only proposes candidates; everything
   passes the multi-confirm gate (`worker/gating.py`); promotion is
   human-custodied or earned-confidence AUTO behind founder-flipped,
   fail-closed flags. Custody, never absence.
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

**External-stall escalation ladder (founder-directed 2026-07-22: "Do not let
things run for so long without firing. Troubleshoot faster. Fix faster."):**
When an external system misses an expected event (a scheduler slot, a webhook,
a deploy callback):
- **First miss:** verify our own configuration immediately and completely
  (config on the authoritative branch, service state via API). Apply every
  self-serve mitigation in the same pass — do not save any available action
  for later.
- **Second miss:** if the remaining fix needs founder hands, the consolidated
  founder ask goes out NOW — options, recommendation, tradeoffs, links. Never
  wait for a round number of misses or an "escalation checkpoint" hours out.
- **Watching cadence:** watch interval = ONE expected-event interval + provider
  lag allowance, never multi-interval windows.
- **A watch turn never ends unarmed:** success is silent (CI success and
  merges deliver no webhook) — before ending ANY turn that awaits an
  external outcome, arm a wake-up for it; if the preferred scheduling
  mechanism is unavailable or declined, use the best available fallback
  and SAY SO. (Added 2026-07-22 after the 05:28Z→11:56Z gap: an APPROVE
  sat unmerged 6.5h because the awaiting turn ended with no timer.) Bridging actions (manual runs,
  pings) buy time; they never substitute for the escalation.
- Origin: the 2026-07-22 cron-arming stall — first missed slot 01:07Z,
  founder ask not delivered until 04:02Z, while the fix (a two-tap
  disable/enable only the founder could perform) was available from the first
  miss. Three hours of patience with a stuck external scheduler was a process
  defect, not diligence (founder(Red) catch; Kaizen ledger row same date).

---

### 4a. Plan-first — never build without a plan (founder-directed, 2026-08-02)

No substantive build begins without a **plan** presented to (and approved by) the founder that
states, for the work at hand:
1. **What** — the change/build, concretely.
2. **How** — the approach and the sequence.
3. **Why** — the reasoning, tied to the core principles/goal.
4. **Why it matters** — the stakes; what gets better, for whom.
5. **Expected outcomes/results** — what success looks like, ideally measurable.

**The full process (canon, founder-directed 2026-08-02) — every substantive build runs it, in order:**
1. **PLAN** — what · how · why · why-it-matters · expected-outcomes; presented to and **approved by
   the founder before building** (never skip the approval).
2. **BUILD** in small batches.
3. **VALIDATE** — lint, tests, trust-gate.
4. **INDEPENDENT EVALUATOR** (code) — the non-Claude adversarial review on the PR.
5. **PREVIEW for the founder** — a real URL/artifact to react to.
6. **FOUNDER APPROVAL** → **MERGE** → **MEASURE** (Heartbeat / the effortless-UX metrics).
7. **INDEPENDENT REVIEW OF THE WORK** — a reviewer who is **not the builder** critically assesses
   how well the work did at (a) **designing** the plan, (b) **building** it, (c) **executing** it,
   and (d) **confirming it was built as designed**. It is adversarial by intent — cites specifics,
   finds gaps/overreach/drift, never rubber-stamps; its findings are **fixed or RECORDED**, not
   ignored. This is distinct from step 4 (which reviews the code diff): step 7 reviews *how well the
   whole plan→build→execute→confirm cycle was performed*.

"World-class" (§5) is never unplanned, unreviewed, or unconfirmed. This applies with full force to
UI/UX work, whose spine is the user-journey model (`docs/design/ONE_LIVE_USER_JOURNEY_LIFECYCLE_v1.md`),
which is being grounded in proven, tested strategy/methodology/tactics (a "Methodology & Evidence"
section is being added to that doc — research in progress).

### 4b. API & tool-call frugality — event-driven, never busy-poll (founder-directed, 2026-08-02)

**Why this rule exists (verbatim trigger).** An avoidable incident: the agent exhausted the hourly
GitHub API quota (5,000 req/hr — the same on every plan) by (a) making **oversized** list calls —
`actions_list` / `list_pull_requests` returning 77k–140k characters each — and (b) **busy-polling**
CI in tight loops, re-fetching the same status repeatedly. This blocked a go-live merge and **cost
the founder time and money** for zero added information. Founder directive: *"Never perform this kind
of action again … Codify to canon and repo."* Every external API call spends the founder's money and
time; treat it that way.

**The rules (checkable in review and by self-audit):**
1. **Event-driven, not poll-driven.** This session already receives forwarded GitHub webhook events
   (CI results, review comments, merges, mergeability transitions). **Rely on them.** Check a PR/CI
   state **at most once per genuine need**; if a required check is *pending*, **STOP and end the
   turn** — the event will wake you. **Never** loop-poll a status. Never use `sleep` to wait for an
   external result.
2. **Bound every list/search/log call.** Always pass `minimal_output: true` where available, the
   **narrowest** filter, and `perPage ≤ 5`. **Never** call `list_workflow_runs` / `actions_list` /
   `list_pull_requests` / `get_job_logs` unbounded — they can return 100k+ characters that burn both
   the API quota *and* the context window.
3. **One authoritative signal, not many.** A single `pull_request_read` **`get`** returns
   `mergeable_state` (`clean` / `blocked` / `unstable` / `dirty`) — that alone answers "is it
   merge-ready." Do **not** additionally fire `get_status` + `get_commit` + `actions_list` for the
   same question.
4. **Route unavoidable large output through a subagent** so it never enters the main context.
5. **If a task needs more than a couple of status calls, the approach is wrong** — wait for events.

**Enforcement.** Reviewer- and self-checked today; the mechanical upgrade (Kaizen, if the class ever
recurs) is a `PreToolUse` settings hook that **denies** an unbounded `mcp__github__` list call
(missing `minimal_output` / oversized `perPage`). Logged as an ESCAPED defect —
`docs/metrics/KAIZEN_LEDGER.md`, class `api-busy-poll`.

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

## 6b. Founder-path preflight (canon, founder-ratified 2026-08-05 — decision record docs/memory/decisions/2026-08-05_founder-path-preflight-and-real-db-leg.md)

Nothing that asks the founder to touch the product — a walkthrough, a runbook
step, a "go try X" — is sent until the exact path has been exercised against
the LIVE deployment by a mechanical probe (ops-diagnostics), with the probe
run linked in the message. A step that cannot be probed is labeled UNPROBED
in the message itself. The founder discovering a broken path the agent
described is an ESCAPED defect, ledger row mandatory. (Mechanism shipped in
the ratification commit: ops-diagnostics mode `auth-probe` walks the hosted
sign-in page and every enabled OAuth button to its authorization redirect,
failing loud on a missing client_id — the exact 2026-08-05 founder-caught
break. New probes are added per surface as walkthroughs need them; a surface
with no probe yet is what UNPROBED is for.)

## 6c. Real-database leg for publish-path changes (canon, founder-ratified 2026-08-05 — same decision record)

Any change to code that writes the canonical public tables (promote,
importers, migrations) must pass a CI test against a real PostgreSQL with the
repo's migrations applied — hermetic fake-cursor tests cannot see server-side
types/constraints and never satisfy this rule alone. (Mechanism shipped in
the ratification commit: `.github/workflows/db-integration.yml`, every PR, no
path filter, PostgreSQL 15 service container + `tests/integration/` running
the actual promote path over the committed migrations.)

## 6a. Follow-ups & keeping the founder informed (canon, founder-directed 2026-07-31)

The agent is the **manager** and reports to the founder; driving work to done and
keeping the founder informed is the agent's job, never the founder's to chase.

1. **Keep working — no delays.** Default to **immediate continuation**: finish one
   step, start the next, in the same run. Do NOT stop to schedule a far-out
   check-in and do NOT sit on a timer. Long delays are banned (founder-directed
   2026-07-31: *"Stop with the long delays and check-ins!"*).
2. **Completion-triggered, not clock-triggered — NO timers, NO `send_later`, NO
   self-check-ins (founder-directed, repeated ~10×; hardened 2026-08-03 after the
   agent scheduled a "~1h fallback" anyway).** Continuation is driven by an EVENT
   finishing — a build step done, a PR going green, a CI/review/merge webhook. The
   PR-activity subscription (`<github-webhook-activity>` messages) IS the trigger;
   it wakes the session. **Do NOT call `send_later`, `create_trigger`, `sleep`, or
   any scheduling/delay tool to wake yourself** — a clock-based self-check-in "just
   in case" is the exact banned anti-pattern, and a "shortest-possible fallback
   timer" is still a timer. The ONLY thing that ever justifies a scheduled wake is
   an **actual external trigger that emits no webhook at all** (e.g. polling a
   third-party job the harness genuinely cannot be notified about) — and even then,
   prefer to **END THE TURN with a clear status** and let the harness re-invoke you
   on real events; a subscription's "success is silent" gap is covered by re-checking
   when the NEXT real event arrives, not by a timer. Requesting a delay for anything
   other than an actual external trigger is a Rule-Zero-level violation.
3. **Non-user-facing content does not circle (founder-directed 2026-07-29, canon;
   restated here 2026-08-03 because the review/re-review cluster kept recurring).**
   Gates, reviews, and tests exist to protect USER-FACING trust — fabricated/
   unverified data on a user surface, AI publishing unvalidated, disputed hidden,
   auth/RLS fail-open, non-parameterized SQL, unvalidated input, broken trust
   display, pay-to-rank. Process/harness/docs ceremony (red-class recitation,
   Kaizen rows, construction contracts, doc formatting, session-doc structure) is
   EXPLICITLY out of review scope and must NEVER block a merge or trigger a
   re-review cycle. Mechanisms already live (do not re-derive them): the adversarial
   reviewer is scoped to user-facing harm; `construction_gate` and `kaizen_trends`
   are ADVISORY; `trust_gate`/`lint`/`deferral_scan`/full pytest stay blocking. On
   a NON-user-facing gate/test failure: fix it ONCE or route around it and land the
   change — do not enter a review circle over it. Relaxing any USER-FACING trust
   gate is a different thing entirely: still founder-crucial, never done to escape a
   circle. When unsure whether a failure is user-facing, that judgment is the
   founder's, asked ONCE — not litigated across rounds.
4. **Own it; report, don't ask.** Decisions the agent can make and reversibly
   verify, the agent makes — then reports the outcome. Do not park buildable work
   as a founder "switch/decision" when the honest blocker is unbuilt code. Naming
   an unbuilt engine as a founder toggle is the 2026-07-31 anti-pattern this rule
   exists to prevent.
5. **Every handoff is WORLD-CLASS, and currency is PROVEN, not asserted
   (founder-directed 2026-08-03).** Any prompt/doc/message that transfers work to a
   next session, another agent, or a future self MUST meet the eight-property bar in
   `docs/ops/HANDOFF_STANDARD.md` (self-contained · disk-is-truth · current-AND-proven
   · prioritized actionable work · failure memory · interaction contract · decisions
   separated by ownership · plain/honest/linked). The canonical handoff artifact is
   `docs/ops/NEXT_SESSION_KICKOFF_PROMPT.md`, rewritten to that bar at every session
   close. **Proof discipline (generalizes §1 to every currency/completeness claim):**
   never write "everything is current / all reconciled / done / green" as an
   assertion — SHOW the evidence a reader can re-run (`python tools/staleness_check.py`;
   marker == `git rev-parse origin/master`; `tests/test_live_state_consistency.py`;
   `bash tools/validate` RESULT with no gate FAILED; PR/DB facts via the GitHub/Supabase
   connectors, recorded UNVERIFIED when absent, never guessed). If you cannot produce
   the evidence, you do not yet know the claim is true — state what is unverified.
6. **Adjudication stays with the evidence; fresh missions get fresh sessions
   (founder-directed 2026-08-03).** Work that consists of judging feedback,
   verifying claims, or following through on in-flight artifacts belongs to the
   session that HOLDS the evidence (its context, its research, its authorship
   memory) — transferring it discards fidelity a summary cannot restore. Work
   that is a NEW mission (a different surface, a different deliverable) starts
   in a FRESH session with a HANDOFF_STANDARD prompt, so no session becomes a
   bottleneck holding unrelated threads. Corollary: before any session's
   evidence becomes load-bearing for future work, COMMIT it to the repo
   (disk-is-truth applies to research and reasoning artifacts, not just code —
   the 2026-08-03 research reports in docs/strategy/research/ are the model).

---

## 7. When in doubt

- Prefer surfacing a gap over hiding it.
- Prefer a smaller verified step over a larger unverified one.
- Prefer fixing now over noting for later.
- Ask only as a last resort, after using tools to answer the question yourself.
