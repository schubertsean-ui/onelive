# The Construction Loop — closed-loop, memory-first code construction (v1)

Greppable summary: founder-directed 2026-07-25 (Contract #24; verbatim
directive in docs/memory/decisions/2026-07-25_construction-loop-directive.md)
— every substantive build runs a seven-stage closed loop: confirm
objectives → green/red probable-path assessment → RETRIEVE memory (green
examples + red classes) BEFORE design → scored path selection → run +
gather feedback → analyze/score/commit to brain in machine-consumed form
→ repeat with improvement measurement. Root cause it exists to fix
(Kaizen, PR #65 arc): class-level lessons sat in the ledger while sibling
defects shipped three times — prevention ran downstream in the evaluator
instead of upstream in construction. Research grounding per stage below
(sources in the Contract #24 research synthesis, changelog-linked).
STATUS: ADOPTED as agent practice effective immediately (founder-directed);
the mechanical enforcement tooling and the CLAUDE.md charter pointer are
queued in TODOS (the loop binds the agent now; the tooling makes it
physics).

## The loop

**Stage 1 — Confirm vision, goals, specific objectives.**
Practice: Toyota A3/PDCA problem framing + 2025-26 spec-driven
development. The session contract (charter prime directive 3) is written
in A3 form: current condition / target condition / measurable
done-criteria / explicitly out-of-scope. Designs are later scored against
this artifact, never against chat memory.

**Stage 2 — Assess green and red probable paths (premortem, tree-shaped).**
Practice: Klein's premortem (prospective hindsight raises failure-reason
identification ~30%, Mitchell/Russo/Pennington 1989) + NASA causal-factor
trees over 5-Whys (real failures are multi-branch; a single chain
anchors) + anticipatory reflection for LLM agents (EMNLP 2024 "Devil's
Advocate"). Encoded: before design acceptance, write "this build FAILED —
why?" answers across the standing branches — trust-path/custody, gate
custody, data corruption, CI/evidence binding, review scope — with the
seed list GENERATED from the Kaizen ledger's red-class tokens (Stage 3's
retrieval). Each branch gets a written answer; the answers ride the PR as
evidence.

**Stage 3 — Check the brain FIRST (the blocking step this loop exists for).**
Practice: CBR Retrieve→Reuse→Revise→Retain (Aamodt & Plaza) and its
agentic descendants — Reflexion, Voyager skill libraries, ExpeL (insights
always injected; similar trajectories retrieved by relevance). Mechanism,
stated plainly: a lesson that exists but is not injected into the design
context is functionally not known — that is exactly how
caller-suppliable-custody-inputs shipped three times. Encoded: before any
design is accepted, retrieve over docs/memory/ + KAIZEN_LEDGER keyed on
the touched paths/change type; the design must CITE each matched green
example (reuse candidate) and red class (with its premortem answer);
"no matched classes" is an explicit printed result, never silence.
Schema: distilled class RULES (always injected) vs full past CASES
(retrieved by similarity).

**Stage 4 — Select the most likely success path(s), scored.**
Practice: Large Language Monkeys (independent samples scale coverage
log-linearly WHERE a cheap mechanical verifier exists), Refine-n-Judge,
judge panels, bandit portfolio selection. Decision rule: a retrieved
green precedent collapses the search (reuse-with-revision, N=1);
otherwise generate 2-3 INDEPENDENT designs (never seeing each other —
the existing hat-independence rule) and judge against the Stage 1
contract before code. Score = precedent match + premortem-branch
survivals + verifier cheapness. Generate-N only where the verifier is
mechanical; iterate-one where feedback is rich and directional.

**Stage 5 — Instruct and run agents; gather feedback (small batches).**
Practice: DORA — small batches, trunk-based flow, CI. Small batches are
the direct antidote to multi-round review churn: a defect is caught
close to its cause with a small blast radius. Encoded: one coherent
change per PR (a design that cannot be sliced into reviewable batches is
rejected at Stage 4); the FULL mechanical suite (tools/validate) runs
before the expensive adversarial reviewer, and the reviewer receives the
premortem answers as attached evidence — review becomes confirmation,
not discovery.

**Stage 6 — Analyze, score, COMMIT TO BRAIN in machine-consumed form.**
Practice: SRE blameless postmortems + Army AAR, including their measured
failure mode — postmortems without follow-through create an illusion of
improvement (most action items die within two weeks). Encoded as the
repo's definition of "committed": a lesson is NOT committed until it
exists in one of exactly three machine-consumed forms, in preference
order: (1) a mechanical gate/lint rule; (2) a retrieval-indexed red-class
token with trigger keywords/paths that Stage 3 matches; (3) a golden-set
regression case. A prose-only ledger row is an OPEN defect, not a
committed lesson.

**Stage 7 — Repeat; measure improvement or slippage.**
Practice: PDCA Check/Act + DORA trend discipline + the SRE unclosed-
postmortem warning. Encoded: evaluator-rounds-to-APPROVE per PR (Kaizen
M1) and the repeat-class rate are the loop's own health metrics; a
rising trend in either is itself a recorded defect that forces a Stage 6
gate-gap fix. The loop measures the loop.

## The three highest-leverage commitments (from the failure analysis)

1. **Memory retrieval is a blocking gate, not a habit** — no design is
   accepted without the Stage 3 citation pass (tooling queued: a
   tools/-level check that refuses a session contract lacking the
   retrieval evidence).
2. **The premortem is seeded from the ledger's red classes and runs
   before design acceptance** — every past evaluator finding becomes a
   token the next build must answer in writing, shifting review-round
   discovery left into a pre-code checklist.
3. **"Committed to memory" is defined mechanically and repeat-classes
   are trended** — the difference between a ledger and a brain.

## Boundaries (unchanged physics)

The loop ADDS an upstream pass; no downstream gate relaxes (charter cost
rule 3: thresholds identical at every tier). Trust invariants, evaluator
mandate, and founder-crucial escalations are untouched. Using the loop's
outputs (premortem answers, retrieval citations) to argue a gate DOWN is
a gate-threshold relaxation: founder-crucial, always.
