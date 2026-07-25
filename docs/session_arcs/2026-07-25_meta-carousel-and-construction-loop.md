# Arc 2026-07-25 — Meta carousel engine (PR #65 merged) + Construction Loop ratified

One-line summary: the outbound Meta carousel engine merged after a
15-round adversarial arc (squash `5481c15`); the RCA of that arc produced
the founder-ratified Construction Loop (charter Thinking-tools item 4) —
this arc is the DIRECT INPUT to the Loop-Harness-Brain work and is
written for that session's retrieval as much as for chronology.

## Cross-session accessibility (founder directive, this session)

Founder: everything here must be accessible to the Loop-Harness-Brain
model applicability review session, and reciprocal. Mechanism (Brain 1A
canon): disk is the shared brain — no chat memory transfers between
sessions. Both directions:
- **This session → Loop-Harness-Brain session:** this arc + the records
  below, all landing on master at PR #67's merge (the shared read
  surface every session reconciles against).
- **Loop-Harness-Brain session → this session:** its outputs were read
  and USED here — `docs/strategy/ONE_LIVE_MEMOHARNESS_APPLICABILITY_REVIEW_v1.md`
  (arc `2026-07-17_memoharness-review.md`) shaped the Brain 1B TODOS
  constraints, and the Construction Loop's Stage 3/6 are the "Loop"
  leg's missing retrieval discipline. A reciprocal pointer now sits in
  that review doc's addendum.

## What the Loop-Harness-Brain session should retrieve from here

1. **The Construction Loop is a Loop-leg component** —
   `docs/skills/construction_loop.md` (charter item; founder-ratified
   verbatim in `docs/memory/decisions/2026-07-25_construction-loop-directive.md`):
   seven stages; the load-bearing ones for the Brain model are Stage 3
   (BLOCKING memory retrieval before design acceptance — the RCA'd root
   cause of the 15-round arc was lessons stored but not retrieved) and
   Stage 6 ("committed to brain" = machine-consumed form only: gate rule
   / retrieval-indexed token / regression case; prose-only rows are open
   defects). Brain 1B's recall tool is the natural implementation
   substrate for Stage 3; `tools/construction_gate.py` (SHIPPED, a hard gate
   in validate) is the enforcement.
2. **The evidence for why retrieval must be blocking** — the Kaizen
   ledger's #65 arc rows: caller-suppliable-custody-inputs fired at r3,
   r11, and r13 (clock, identity) despite the r3 class fix being in the
   ledger the whole time. M1=15 rounds. This is the repo's own measured
   proof of the ExpeL/CBR finding: uninjected memory is functionally
   unknown.
3. **New durable records this session:** decision records
   `2026-07-24_meta-carousel-engine.md` (+ listicle addendum),
   `2026-07-25_repeated-error-investigation-rule.md` (global operating
   rule), `2026-07-25_silent-merge-directive.md` (scoped precisely at
   #67 r1), `2026-07-25_construction-loop-directive.md`; the research
   synthesis grounding each loop stage (in the Contract #24 changelog
   entries); publish-custody patterns in `social/carousel/publish_gate.py`
   (allowlist registry, key-strength floor, gate-owned clock, total
   re-render verification, content-bound grants, durable-journal
   ceiling) — reusable custody precedents for ANY future outward
   surface.

## Session chronology (compressed; details in changelog r-entries + Kaizen rows)

Contract #23: engine built (spec, `social/carousel/` package, 135 engine
tests at close) → founder listicle/future-only directive → 15 evaluator
rounds (#63 superseded by #65 after a base-merge conflict; the 13-hour
stall RCA'd as stalled-state-needs-active-diagnosis) → merged silently
per the founder's no-notify directive at r15 APPROVE + trust-gate green.
Contract #24: founder's construction-method directive → research agent →
Construction Loop adopted, then founder-ratified into the charter same
day. Founder also deployed the Vercel Clerk key — first green Preview
deployment after days of known-noise red; Vercel red is a REAL signal
again. PR #67 carries the close bookkeeping + loop canon + the r15
trust-path nits (shipped, not parked — #67 r1's lesson).

## Open threads carried forward

- construction_gate v1 SHIPPED in this session (#67 r4) with the
  path-trigger index; the Brain 1B semantic-recall upgrade of Stage 3
  remains the natural joint build (same retrieval substrate).
- Prose-row retrofit (TODOS P2, rolling) per Stage 6.
- Founder-crucial queue unchanged: Meta credentials, ONELIVE_APPROVAL_KEY
  mint (with the r14 strength floor), posting posture, cron Sentinel
  wiring (R-027), autonomy ladder step, R-028.
