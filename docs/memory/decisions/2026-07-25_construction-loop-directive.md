# 2026-07-25 — Construction Loop directive (founder): closed-loop, memory-first building

**Directive (founder, verbatim, 2026-07-25, session `onelife-meta-carousel`):**
"Have you built in a root cause analysis - the world leading after
researching it or better kinds of processes - to get at the root of your
failures? You need to build in a better code construction method,
something along the lines of this: (research this): confirm vision, goals
and specific objectives, assess all parameters for green and red probable
paths to achieve objectives, check brain for existing green
examples/successes, select the most likely success path(s), if nothing
exists use the probable paths analysis to guide, instruct and run agents,
run agents and gather feedback, analyze, score, commit all to brain for
future learning, do it again, measure improvement or slippage, commit to
brain, inform next actions, repeat."

## RCA answered honestly (the root of the failures)

The PR #63/#65 arc took 15 adversarial-review rounds because class-level
lessons (e.g. r3's "no caller-suppliable inputs at a custody boundary")
were stored in the Kaizen ledger but never retrieved at design time —
sibling instances of the same class shipped at r11 (the clock) and r13
(the approver identity). Prevention ran downstream in the evaluator
instead of upstream in construction. Lessons existed; they were not
injected. A lesson not injected into the design context is functionally
not known.

## Decision taken (agent, within charter)

The seven-stage Construction Loop is ADOPTED as agent practice effective
immediately, research-grounded per stage (A3/PDCA + spec-driven
development; Klein premortem + NASA causal-factor trees + anticipatory
reflection; CBR/Reflexion/ExpeL retrieval-first memory; sampled-vs-
iterated path selection with judges/bandits; DORA small batches; SRE/AAR
follow-through discipline; PDCA trend measurement). Canon:
`docs/skills/construction_loop.md`; wiring: `docs/OPERATING_RULES.md`.

## Queued (never agent decisions / build items with objective triggers)

1. Founder ratification of the loop as CHARTER text — RATIFIED same day
   (founder, verbatim: "I approve making it part of the permanent canon")
   — CLAUDE.md Thinking-tools item 4 added in the same commit as this
   line.
2. `tools/construction_gate.py` — the mechanical Stage 3 blocking check
   (refuse a session contract lacking retrieval citations) + red-class
   token index over the Kaizen ledger. Build item in TODOS (P1); gate
   custody applies (evaluator-mandatory when it lands).
3. Retrofit: the ledger's existing prose-only rows get retrieval tokens
   as they are next touched (Stage 6's definition of "committed").
