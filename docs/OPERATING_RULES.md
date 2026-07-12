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

> **Everything we build must be world-class, and everything is tested as it is
> built. No "ok" code. No "no immediate problems." Nothing lingers, is ignored,
> or is set for later.**

### 1a. World-class is the bar, and it is defined — not vibes
"World-class" is not a compliment we award ourselves; it is a claim we must be
able to defend.

**Scope: world-class applies to EVERY aspect of the build, without exception** —
not only code correctness. That means, at minimum: system & data architecture;
the data model and schema; APIs and contracts; the UX/UI and its copy,
accessibility, and states (loading/empty/error); the trust & verification layer;
security and privacy; performance and cost; reliability and failure semantics;
observability (logging, tracing, metrics); tests; the developer experience; and
the documentation itself. If any one aspect is only "fine," the thing is not
world-class — a great engine in a broken chassis is not a great car. No aspect
gets a pass because another aspect is strong.

A component (in ANY of the aspects above) is world-class only when ALL of the
following hold — and we state, for each, HOW we know:
- **Correct at the core, not only at the surface.** The central logic is right,
  not only the happy path. (Example failure: an extraction scorer whose
  hallucination KPI is poisoned because its comparison layer flags a correctly
  extracted `"8pm"` vs `"20:00"` as a hallucination. Surface metric, broken core.)
- **Adversarially tested, not only demonstrated.** We have tried to break it and
  shown it holds (sabotage-validation, §2b). "It works on the example I chose"
  is not evidence.
- **Best-in-class for its job, and we can name what we compared against.** If a
  simpler/stronger standard approach exists, we either use it or write down why
  ours is better. Reinventing a weaker version of a solved problem is not
  world-class.
- **No known weakness left unnamed.** If we can see a gap (naive normalization,
  missing calibration, no confidence interval), it is either fixed now or
  recorded as an explicit, tracked debt with an owner — never silently shipped
  under the word "solid."
- **Honesty about maturity is part of the bar.** Do not call something
  "world-class" or "solid" to close a thread. Grade it against this list and
  state the real level. Overstating quality is itself a quality-bar violation.

### 1b. Test everything as you go (not after)
Testing is not a phase that follows building; it is part of building. For every
unit of work, in the same change that creates it:
- write the test(s) that prove it does what it claims AND that it fails when it
  should (both directions — see sabotage-validation, §2b);
- run the full suite + `tools/trust_gate.py` and get to green before moving on;
- never advance to the next unit on top of un-tested or red work.
A feature without its tests, in the same increment, is not half-done — it is not
done, and does not count as progress.

Concretely, before anything is considered done:

- **No silent degradation.** Code must never make "we failed" look identical to
  "there was nothing to do." This is the project's founding anti-pattern (see §3).
- **No swallowed errors.** `except: pass` and `except Exception: <blank fallback>`
  are banned unless the caught branch is *itself* logged/audited and justified in
  a comment.
- **No dead code / unreachable features.** If a parameter, hook, or path can't
  fire in production, it isn't done — wire it or remove it.
- **No deferred cleanup.** If a review turns up a defect, fix it in the same
  change. Do not write a TODO and move on. A known issue left behind is a broken
  window.
- **No red tests.** Never write new work (or docs) on top of a failing test. Green
  first, then proceed.
- **Findings are claims until verified.** Row counts, scores, "it works" — prove
  them against ground truth (DB query, passing test, real run) before asserting.

If something is only "fine," it is not done. State the gap and close it.

### 1c. Language audit — prose is part of the build
Every piece of language in the build is a build artifact and is held to the same
bar as code. This covers, without exception: code comments and docstrings,
commit messages, UI copy, docs and the handbook, error and log strings, test
names, identifiers (variable/function/class names), source-catalog notes, and
spec prose.

**Rule:** audit all such language for adverbs and other qualifying or hedging
grammar, and remove it. Targets include filler adverbs (`just`, `simply`,
`quickly`, `basically`, `honestly`, `actually`, `really`, `very`), vague
intensifiers, and qualifiers the text cannot support. Hedging weakens a
truth-first product's voice and hides imprecision; treat it as a defect.

- The audit applies to everything already built and everything yet to be built,
  no matter how small the unit.
- Fix in-change (Sunset Law, §2b) — never leave hedged prose for later.
- **Exception:** keep an adverb when it states a genuine engineering property,
  not decoration — e.g. `idempotently`, `atomically`, `explicitly`, and
  `fail-loud`/`loudly` used in the §3 sense. The test: if deleting the adverb
  changes what the sentence technically asserts, keep it; if it only softens or
  inflates, cut it.

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

### 2b. The weekly Kaizen loop (per week)
Once a week, step back from feature work and improve the *system that builds the
system*:
- What defect classes recurred? Encode a guard (a rule here, a test, a lint) so
  they can't recur silently. Mature a guard along the path **point fix ->
  meta-rule -> mechanized scanner**: only guards that reach the mechanized-scanner
  stage stop recurrence (ad hoc point fixes recur). The trust gate
  (`tools/trust_gate.py`) and the language audit (`tools/language_audit.py`,
  §1c) are the canonical step-3 mechanized scanners.
- What did a session-arc reveal about drift between STATE.md and reality?
- What manual step happened 3+ times and should be automated?
- Update this doc and `CLAUDE.md` review criteria with anything learned.

**Every guard must be sabotage-validated before it is trusted.** Prove a new
guard is alive by deliberately introducing the exact violation it targets,
observing it fire, then reverting. In a system whose primary failure class is
*silent*, an unvalidated guard is indistinguishable from a vacuous one — a check
that looks present in the code but has zero real effect. (This is not
theoretical: hardening the sensor on 2026-07-11, a sabotage test caught a
mojibake guard whose marker constants were the wrong byte variant and would
never have fired on real corruption.) Tests written for a guard must assert both
that it fires on the violation AND that it does not false-positive on clean
input.

**The Sunset Law (guard-retirement discipline).** Guard/rule accumulation is not
self-limiting: every guard adds a part, and parts add seams, and defenses are
themselves incident surfaces. So the creation discipline above is paired with a
symmetric retirement discipline: **before adding a new guard/check/rule, attempt
to retire or fold in an equivalent existing one.** One logical invariant should
have one physical representation. When you add a guard, name in the commit /
arc what you considered retiring (even if the answer is "nothing yet"). The goal,
empirically supported, is that over time the system retires more duplicate
representations than it adds invariants — incident frequency falls without
slowing feature velocity.

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
   promotion always passes the multi-confirm gate (`worker/gating.py`). This is
   enforced structurally in CI by `tools/trust_gate.py` (an AST gate that fails
   the build if the AI/extraction layer imports `worker.promote`, if
   ads/tastemaker code imports gating/promote, or if any dynamic SQL appears in
   api/worker/tools). A deterministic gate — not an LLM reviewer — guards trust
   invariants precisely because the guard itself must never be flaky or
   de-authorizable.
3. **The gate is three-way: PASS / HOLD / ESCALATE.** Corroboration count alone
   (`worker/gating.py` is 2-way) does not equal safe-to-auto-publish.
   `worker/trust_gate3.py` wraps the count gate and adds ESCALATE for evidence
   that is promotable-by-count but conflicting or needs human judgement
   (conflicting start_time, a `validation_error` in extraction provenance, a
   private/RSVP event, a dedupe-ambiguity hint). ESCALATE => leave in
   needs_review, log it, never auto-promote. **Escalating to a human is the
   correct outcome, never a bug to route around.** Any build-time iteration
   ratchet ("commit on green, keep going") governs how WE evolve the code only —
   it must never leak into the product gate as "auto-approve to keep the run
   moving." This fence is documented in `worker/orchestrator.py` so it cannot
   silently erode.
4. **Everything auditable, and every loop decision is replayable.** Every stage
   leaves a trail. AI extractions carry `_provenance` (provider, model,
   prompt_version, timestamp); degradations and fuzzy merges write to
   `audit_log`. The orchestrator (`worker/orchestrator.py`) additionally emits a
   deterministic-replay record (`worker/replay_log.py`) for every loop step —
   fetch, sensor, extract, gate, promote|escalate|hold|error — with sha256
   digests of canonicalized inputs/outputs, so any promotion decision is
   auditable and re-runnable later. Losing an audit record fails LOUD
   (`ReplayLogWriteError`); it is never silently dropped.
5. **Never fabricate to fill a gap.** Null/empty is always the correct answer when
   the source doesn't state a value. Enforced by the extraction prompt and by
   measuring `hallucination_rate` (`ai/eval_harness.py`) — the KPI behind DoD #41.
6. **Disputed data is shown as disputed, never deleted** (4-state confidence model
   in `CLAUDE.md`).
7. **Tastemaker (human opinion) content never enters the event
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
  trust" over loud badges. Confidence states and provenance surface with each event.
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
   is informed, not asserted without support.

This applies to plans, technical choices, sequencing, and `ask_user_question`
prompts alike. A recommendation can still be overridden — but the default is a
considered position, not a shrug.

---

## 7. When in doubt

- Prefer surfacing a gap over hiding it.
- Prefer a smaller verified step over a larger unverified one.
- Prefer fixing now over noting for later.
- Ask only as a last resort, after using tools to answer the question yourself.
