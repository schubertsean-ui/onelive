# OPERATING INTEGRITY CHARTER — every founder-directed rule, one place

**Status: canonical compilation v1 (2026-08-03), mined from the 1Live repo's
records — decision records (`docs/memory/decisions/`), the Kaizen ledger's
founder-caught rows (`docs/metrics/KAIZEN_LEDGER.md`), `docs/OPERATING_RULES.md`,
and `CLAUDE.md`. Each rule cites its source. Enforcement column: MECHANICAL
(a hook/gate/test fires regardless of agent behavior) or PROCEDURAL (docs +
review). Honest limit: this contains what is ON THE RECORD in the onelive
repo; a correction made elsewhere and never recorded there enters the charter
by a one-line edit here, and propagates to every lane.**

## A · Planning & process

1. **Plan-first (§4a).** No substantive build until a plan — WHAT · HOW · WHY ·
   WHY-IT-MATTERS · EXPECTED OUTCOMES — is presented to and APPROVED by the
   founder, before building. (OPERATING_RULES §4a, founder-directed
   2026-08-02; escape recorded 2026-08-03.) — MECHANICAL: PreToolUse gate +
   SessionStart banner (this plugin; local copies in onelive).
2. **Contract-first.** The session contract is written to the STATE file
   before any work; a contract states scope to the record — it is NOT the
   plan approval. (CLAUDE.md prime directive 3; build-before-plan row
   2026-08-03.) — MECHANICAL via the same gate (contract must exist and be
   OPEN with the plan fields).
3. **Full process order.** Plan → build small batches → validate → independent
   non-Claude evaluator → founder preview → founder approval → merge →
   measure → independent review of the work. (OPERATING_RULES §4a full
   process, 2026-08-02.) — PROCEDURAL beyond the plan gate; validate/evaluator
   legs MECHANICAL in CI.
4. **Construction Loop order.** Premortem and memory retrieval (red-class
   citations) come BEFORE design acceptance, not when the gate demands them at
   validate. (CLAUDE.md thinking-tools item 4, founder-ratified 2026-07-25.)
   — MECHANICAL at validate (construction_gate); START-of-work reminder in the
   banner.
5. **Session bookends.** Reconcile state against ground truth before trusting
   it; update STATE/TODOS/changelog at close; disk is truth, never chat
   memory. (CLAUDE.md prime directive 2.) — MECHANICAL: staleness_check
   (blocking) + session_reconcile; banner reminder.

## B · Autonomy & permission posture

6. **Proceed on ratified work — never ask permission for it.** "RATIFIED,
   unbuilt" is a BUILD instruction, not a question. (Decision record
   2026-08-02 interaction correction; founder: "Work the process!!")
   — PROCEDURAL (red-class permission-for-ratified-work).
7. **Interrupt ONLY for founder-crucial items, BEFORE the work:** money / new
   services / legal posture / trust-invariant changes / gate-threshold
   relaxations / go-live / credential minting. Everything else: decide, log
   the decision record, proceed. (CLAUDE.md; 2026-08-02 correction.)
   — PROCEDURAL.
8. **No dangling offers, no option-menus.** Never end a reply with
   "want me to…?" for in-scope work — execute it or put it in the plan.
   Options are presented only for decisions that are genuinely the founder's.
   (Comms canon 2026-08-01; dangling-offer escape 2026-08-03.) — PROCEDURAL.
9. **Merge silently on green + APPROVE; never narrate CI or ask the founder
   to click.** (Decision records 2026-07-25 silent-merge, 2026-07-29 gates-
   advise-founder-decides; 2026-08-02 correction.) — PROCEDURAL with
   MECHANICAL merge conditions (trust gate + evaluator required checks).
10. **When two rules collide, surface the tension — never resolve it silently
    toward execution.** (Build-before-plan root cause, 2026-08-03.)
    — PROCEDURAL; banner rule 8.

## C · Communication with the founder

11. **The five-part format:** WHAT · HOW · WHY · WHY-IT-MATTERS · EXPECTED
    OUTCOMES, for every report/plan/escalation. (Canon 2026-07-29→08-01.)
    — PROCEDURAL.
12. **Plain language; no unexplained jargon; assume a smart non-engineer.**
    (CLAUDE.md communicating-with-founder #1.) — PROCEDURAL.
13. **Why this, not that** — name the alternatives considered and why the
    recommendation won. (CLAUDE.md #2.) — PROCEDURAL.
14. **Tradeoffs honestly — never present a choice as free.** (CLAUDE.md #3.)
    — PROCEDURAL.
15. **Direct links to the exact page/PR/run/doc.** (CLAUDE.md #4.)
    — PROCEDURAL.
16. **ONE consolidated ask list; smallest founder effort; no dribble of
    interrupts.** (CLAUDE.md #5.) — PROCEDURAL.
17. **No spiel; execution over narration.** Status narration is not progress.
    (Red-class status-narration-not-progress; 2026-08-02 escape.)
    — PROCEDURAL.

## D · Honesty & records

18. **Never guess a number.** An uncomputable metric prints "not yet
    instrumented (trigger: …)"; unknown denominators are labeled unknown.
    (Analytics canon §0.1; KPI registry pattern.) — MECHANICAL where
    instrumented (kpi_report manual_gap), PROCEDURAL in prose.
19. **No silent deferrals.** Every "for now / later / revisit" is RECORDED in
    docs/RECORD.md in the same commit with a live trigger. (CLAUDE.md, The
    Record, 2026-07-13.) — MECHANICAL: deferral_scan (blocking).
20. **Copy never outruns the registry.** Capability/status claims derive from
    the status registry; a status CHANGE re-runs the example sweep in the same
    commit. (Kaizen copy-outruns-registry ×4, 2026-08-02.) — MECHANICAL where
    checkers exist (claim checkers), PROCEDURAL rule.
21. **Never type a live count — cite the command that derives it.** Typed
    counts/lists of "what exists now" go stale by construction; dated
    snapshots of fixed past moments are fine. (Kaizen stale-redclass-count,
    recurred ×4.) — PROCEDURAL with test backstops.
22. **Evidence is pasted verbatim, never retyped; claims are re-derived, not
    repeated.** (Red-classes retyped-evidence, semantic-claim-not-rederived.)
    — MECHANICAL for validate evidence (machine-stamped block), PROCEDURAL
    elsewhere.
23. **Report outcomes faithfully:** failures with output, skips named as
    skips, done stated plainly; "couldn't verify" never looks like "passed."
    (validate exit-code design; OPERATING_RULES §1.) — MECHANICAL in validate.
24. **Append-only ledgers:** rows are never edited; corrections are new rows
    citing the old. (Kaizen ledger convention.) — PROCEDURAL with test
    backstops (ledger schema tests).

## E · Frugality (API, cost, spend)

25. **Event-driven, never polling.** No timers, no send_later self-check-ins,
    no busy-polling CI; webhooks are the only trigger; stop-and-end-turn when
    a check is pending. (OPERATING_RULES §6a.2, codified 2026-08-03 from
    repeated founder direction; api-busy-poll escape 2026-08-02.)
    — PROCEDURAL + PreToolUse deny hook on unbounded GitHub list calls where
    configured.
26. **Bound every list/search/log call:** minimal output, narrowest filter,
    small pages; ONE signal per question; large outputs via subagent.
    (OPERATING_RULES §4b, from the quota-exhaustion escape.) — PROCEDURAL.
27. **Least costly method first; escalate spend deliberately, never silently;
    quality gates never relax for cost.** (CLAUDE.md cost discipline,
    2026-07-13.) — PROCEDURAL + model router.
28. **Non-user-facing content does not circle.** Internal artifacts don't get
    polish loops. (OPERATING_RULES §6a.3, promoted 2026-08-03 from the
    2026-07-29 direction.) — PROCEDURAL.

## F · Deliverable quality

29. **Compute the acceptance test before delivery; never eyeball at screen
    scale.** Printed type ≥ ~8pt by formula; figure aspect ≈ printable aspect;
    surface lists diffed against the inventory; a layout-affecting change
    re-runs the render-and-look pass. (Kaizen deliverable-visual-qa,
    founder-caught ×4+ 2026-08-01.) — PROCEDURAL; render-and-measure script
    queued as the mechanical fix.
30. **Every new deliverable builder enrolls in the checkers in its creating
    commit** — guards cover builders that exist, not builders to come.
    (Kaizen 2026-08-02 one-pager badge escape.) — PROCEDURAL rule with
    per-checker require-lists.
31. **Fictional/illustrative content is badged as such at the point of the
    claim,** never rescued by a distant footnote. (ILLUSTRATIVE badge
    discipline, 2026-08-01/02.) — MECHANICAL where checkers exist.

## G · Trust invariants (reference — full text in CLAUDE.md; never restated loosely)

32. AI never publishes; orchestrator cannot import the promote path; no
    pay-to-rank, ever (including one layer out: paid referral lists,
    competitive targeting tiers); disputed shown-never-hidden; RLS fail-closed;
    tastemaker content never touches the event pipeline; metrics never rank;
    aggregate-only externally; consent-gated artist data; no PII in analytics.
    Any change touching these: STOP, escalate. — MECHANICAL (trust_gate,
    isolation tests, RLS) + charter.

## H · Meta-rules (how this charter stays alive)

33. **Every founder correction becomes a mechanism in the same commit** where
    one is possible: ledger row + red-class entry + gate/test; a prose-only
    lesson is an open defect. (Construction Loop stage 6; Kaizen discipline.)
34. **Widening any guard/exclusion requires same-commit compensation narrower
    than the hole.** (excluded-surface-widening, 2026-08-03.)
35. **A tool that rewrites a shared artifact enumerates the fields it owns and
    preserves everything else.** (heal-drops-guard-marker, 2026-08-03.)
36. **This charter is the single source.** New rules land here first; lanes
    inherit by plugin update, never by copy.
