# Decision record — Descriptor Foundry / Spark Line core (batch 1)

**Date:** 2026-08-02
**Session:** Contract #32 (ship CAPCOG), /tonight Phase 2 content layer
**Branch:** `claude/1live-phase-2-content-c7mozx`
**Author:** Claude Code (Generator)
**Type:** RATIFIED, unbuilt → build. Not founder-crucial (see "Escalation check").

## A3 contract (goal / scope / done-criteria)

**Goal.** Build the first, spend-free, gate-first increment of the Spark Line
feature (UI Canon §4, §13 Phase 2 item 2; Master Design Brief lines 65, 151–163):
the **Descriptor Foundry** generation-and-gate pipeline, as a pure Python module
that runs entirely offline in tests and produces **candidate-only** output which
cannot publish.

**Why the Spark Line before the contextual-preview media (§13's item 1).** Item 1's
highest-value slice — upgrading music search-links to real embedded tracks — is
founder-gated on a music-player API key (spend / new service; UI Canon §12, and the
founder's own "needs me first" list names the music-player API). The Spark Line is
fully unblocked, is the card's *primary curiosity gap* (§2/§4), and its Foundry gate
is the reusable AI-content trust gate the Emotion Glyph (item 4) reuses. Deviation
from the printed value order is **recorded here, not taken silently.**

**Scope (this batch only).**
- `worker/descriptor/foundry.py` — the pipeline: candidate generation (6) via a
  `DescriptorProvider` protocol → pairwise knockout vs a checklist → fusion-of-N
  synthesis (style new, facts never) → independent judge → provenance stamp.
- `worker/descriptor/gate.py` — the **mechanical faithfulness gate** (the load-bearing
  trust piece): word-count ∈ {3,5,7}; no marketing/trust/banned language; every proper
  noun and number in the line must be grounded in the artist's own source materials
  ("facts never invented"); fail-closed (no source materials → no line, mirroring §5's
  "no description → no glyph").
- `worker/descriptor/types.py` — `SourceMaterial`, `DescriptorCandidate`,
  `FoundryResult` (status always `candidate`), `DescriptorFoundryError`,
  `DescriptorProvider` protocol + a deterministic `FakeDescriptorProvider` for tests.
- A small golden-regression set + harness proving known-good pass / known-bad reject.
- `tests/test_descriptor_foundry.py` — full offline coverage.

**Non-goals (explicit, queued in TODOS as follow-on batches).**
- No DB migration / no schema field this batch (follow-on: `00xx_spark_line.sql`,
  separate trust category, RLS fail-closed, anon read of *approved* rows only).
- No real provider call, no worker job, no scheduled run, **no API spend.**
- No read-path or card-UI wiring; nothing reaches a fan.
- No approval step; `candidate` is the only status this batch can emit.

**Done-criteria.** `python tools/validate` green (bar documented skips) · evaluator
APPROVE · the pipeline emits a faithful candidate for a good source and **refuses**
(raises / returns None) for every unfaithful or sourceless case, proven by test.

## Ledger-seeded premortem (tree)

- **fabricated-qualitative-copy** (the whole point of the gate): a candidate invents a
  collaborator, venue, year, or genre not in the source. → The mechanical gate rejects
  any proper noun / number absent from the source materials; the independent judge is a
  second, semantic check; both must pass; fusion is "style new, facts never".
- **rule-stronger-than-mechanism**: claiming faithfulness the code does not enforce. →
  Every rule in this record has a test in the same batch; "facts never" is the
  proper-noun/number grounding check, not prose.
- **false-confidence-gate / self-weakenable-gate**: adding a gate that can pass itself.
  → This gate only ever emits `candidate`; publishing is a *separate*, later, gated step
  it cannot reach. No existing gate/threshold is touched.
- **untested-gate-branch**: a refusal path no test enters. → Tests cover: good→candidate,
  no-source→None, bad word count→reject, banned phrase→reject, invented proper
  noun→reject, invented number→reject, judge-below-threshold→reject, all-candidates-fail
  →None.
- **env-dependent-hermetic-test**: a test needing network/model. → `FakeDescriptorProvider`
  is deterministic and offline; no test calls a real model.
- **contract-scope-violation**: creeping into schema/wiring. → Bounded to `worker/descriptor/`
  + its test; the file list is derived by `git diff --name-only`, not typed.

## Blocking memory retrieval (Construction Loop stage 3)

Searched `docs/memory/` for spark / descriptor-foundry / emotion-glyph:
**no matches** — this is a greenfield feature with no prior brain entry. Nearest
green example in-repo: `social/carousel/generator.py` (trust-error/fail-closed idiom,
`foundry_descriptor{text,provenance}` contract already referenced at lines 197–204,
421–424) — mirrored here. Nearest red classes: `fabricated-qualitative-copy`,
`rule-stronger-than-mechanism` (RED_CLASSES) — answered in the premortem above.

## Escalation check (founder-crucial? — no)

- New service / money: **no** — fake provider, zero spend.
- Model budget at scale: **no** — not run at scale; built and unit-tested offline.
- Trust-invariant change: **no** — adds a *new, separate, gated* content category;
  does not touch the event extraction→promote path or any trust_gate threshold.
- Gate-threshold relaxation: **no** — this ADDS a gate.
- Auto-publish: **no** — candidate-only; nothing publishes.

Proceed, per the standing directive: RATIFIED-unbuilt is a build instruction.

## Lessons (filled at close, machine-consumed form)

- Retrieval token: `spark-line` / `descriptor-foundry` → this record + `worker/descriptor/`.
- (regression cases live in the golden set shipped with the batch.)
