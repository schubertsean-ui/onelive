# Session Arc — 2026-07-22 — Owned Agent research (founder question → PROPOSAL)

Greppable summary: founder asked how to build an AI agent "owned by and
working for" artists/venues/events that feeds OneLive as a side effect of
amplifying them; answered as a researched PROPOSAL
(`docs/strategy/ONE_LIVE_OWNED_AGENT_v1.md`, PR #48, docs-only). Session
Contract #20 lives HERE, not in STATE.md — the arming-evidence binding test
correctly blocked a STATE.md edit on this docs-only head (R-023 records the
fold-back trigger). One internally-caught defect, ledgered.

## Session Contract #20 (2026-07-22, research session `artist-owned-ai-agent` — founder: "How might we create an AI agent that is 'owned' by and 'works for' artists and events and venues? … Research how best to execute something like this")

STATUS: DELIVERED same session — docs-only research PROPOSAL on branch `claude/artist-owned-ai-agent-dvdn5c` (draft PR #48).
GOAL: Answer the founder's owned-agent question with researched execution options, challenges, and a consolidated question list — a PROPOSAL, not a build.
SCOPE: `docs/strategy/ONE_LIVE_OWNED_AGENT_v1.md` (precedent research: Bandsintown for Artists, Google Business Profile claim/verify, schema.org/Things-to-do, Meta API 2026 realities, MCP landscape; three-layer decomposition pipe/gift/skin; discrete function set F0–F5; phases A/B/C gated on Steps 6–7; trust-physics section confirming NO invariant changes; founder questions Q1–Q5) + TODOS queue entries + changelog row + this arc.
NON-GOALS: no code, no schema, no new services, no trust-rule changes (the doc leans entirely on the RATIFIED first-party fast lane from the 2026-07-14 sensor architecture), no preemption of Steps 6–10.
DONE-CRITERIA: doc lands as PROPOSAL with sources linked · one consolidated founder-question list (Q1–Q5) · queue entries gated so nothing builds before ratification + Step 7 · validate green · draft PR through the evaluator.

NOTE ON PLACEMENT (why this contract is not in STATE.md): the first push of
PR #48 carried this contract as a STATE.md edit; the trust-gate and
adversarial-review jobs both failed on
`tests/test_arming_smoke_binding.py::test_reviewed_head_is_runtime_code_identical_to_the_smoke_run`
— STATE.md is not in the binding's non-runtime set (`docs/`, `tests/`,
`TODOS.md`), so the recorded smoke-run evidence no longer covered the head.
The gate is working as designed and was not touched: the contract moved to
this arc (allowed surface), STATE.md was reverted to base, R-023 records the
deferral with the objective fold-back trigger, and the classification
question (does STATE.md belong in the binding's non-runtime set?) is queued
in TODOS as a gate-custody decision — never decided from inside a docs PR.

## What was produced

1. `docs/strategy/ONE_LIVE_OWNED_AGENT_v1.md` — the PROPOSAL. Core finding:
   the "owned agent" decomposes into pipe (verified first-party channels —
   already RATIFIED canon, sensor architecture 2026-07-14), gift (free
   functions F0–F4, each valuable to the business on its own), and skin
   (agent-shaped auto-discovery onboarding over watcher records, never idle
   per-entity LLMs). Precedents: Bandsintown for Artists (510k+ artists on
   free tools), Google Business Profile verification menu,
   schema.org/"Things to do" JSON-LD, Meta API 2026 friction (Phase C only),
   MCP landscape (Phase C reach).
2. TODOS.md — gated "Owned Agent" queue section (Phases A/B/C, all blocked
   on founder Q1–Q5 and Steps 6–7).
3. Changelog rows + this arc + R-023 + Kaizen ledger row for the binding
   catch.

## Trust posture

No invariant touched. The proposal states explicitly: the owned agent is a
source and owner channel, never a publisher; disputed stays
owner-unsuppressible; a no-connect-to-rank corollary is PROPOSED for
ratification (Q4), not assumed.

## Same-day follow-up (Part II addendum)

The founder extended the ask in-session with three theses; researched and
folded into the doc as Part II (§§12–17), same PR:

1. **B2A / agent-facing representation** — the owned agent as the business's
   representative to the incoming wave of consumer/org AI agents. Standards
   are forming now (llms.txt at 844k+ sites with a Chrome Lighthouse check;
   NLWeb; WebMCP). Proposed as function F6 (static profile in Phase B, live
   gated-truth endpoint in Phase C) with two binding trust notes: disputes
   served to machines as to humans; read-only surface of promoted data.
2. **The adoption-gap belief: VERIFIED** (non-adopter barrier data; GEO/AEO
   agencies already charging small businesses $1,500–$5,000/month for AI
   visibility — the exact fee wave the free agent undercuts) **with one
   nuance:** artist AI sentiment is split and loaded (displacement/copyright
   fears) → artist-facing copy leads with representation/accuracy/control,
   never "AI-powered"; sensitivity pre-registered for copy testing.
3. **Essential needs defined as E1–E7** (doc §15): F0–F4+F6 covers E1–E5+E7
   — the 80/20; E6 (social posting) is the deliberate Phase C tail. E-list
   proposed as the Phase A/B acceptance rubric ("build to that standard"
   made mechanical).
4. **Open + private positioning** (§16): open/exportable event truth vs
   walled gardens; on-device-first consumer personalization (opt-in sync),
   with the costs stated (competitors can consume the open feed; analytics
   constrained). Consumer-trust data supports it as differentiation.

Founder questions extended to Q1–Q8 (Q6 F6 ratification, Q7 the E-standard,
Q8 open+private as canon).

## Open threads carried forward

- Founder Q1–Q5 (doc §10) — nothing in the Owned Agent section of TODOS is
  buildable until answered.
- R-023 — fold Contract #20 into STATE.md when the trigger fires.
- Gate-custody decision queued: STATE.md classification in the arming
  binding's non-runtime set (evaluator-mandatory; any widening is a
  gate-relaxation question → founder-crucial).
