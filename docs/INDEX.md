# INDEX — every document, classified

**Status: CANON.** Created 2026-07-26 (`docs/V1_AUDIT_2026-07-26.md` §5). The repo
holds ~263,000 words of prose. Before this file, an agent or a new reader had no way
to tell a binding rule from a two-week-old proposal, so everything read as a rule
and the effective contract was unreadable.

**Three classes, and only one of them binds you:**

| Class | Meaning |
|---|---|
| **CANON** | Binding. Read before working. Changing it is a deliberate act. |
| **REFERENCE** | True and useful; read on demand, when the task touches it. Not a rule you must hold. |
| **HISTORICAL** | A record of what was thought or done at a point in time. **Never a rule.** May be stale by design. Do not build from it without re-verifying. |

**A PROPOSAL is not a licence to build.** Most of `docs/strategy/` is proposal or
research. If a document is not CANON, it does not authorise work.

---

## CANON — the binding set (9 documents, ≈4,400 words)

Read these. That is the whole contract.

| Document | What it is |
|---|---|
| `CLAUDE.md` | The standing contract: prime directives, invariants, who does what, the mission. |
| `docs/BAR.md` | **What world class means, per aspect, as a number, with the gate and current status.** The definition of done. |
| `docs/V1.md` | What v1 is, what is left, in order, and the founder asks. |
| `docs/HOW_WE_WORK.md` | The loop: contract → think → build → verify → review → merge → close. Includes Kaizen and founder-communication rules. |
| `docs/EXTRACTION_EXCEPTION.md` | The one enumerated exception to "every required check green", with the ratified text verbatim. |
| `docs/RECORD.md` | The live register of deviations from bar. Machine-read by `tools/deferral_scan.py`. |
| `docs/DEPLOY.md` | The single source of truth for deployment and env config. |
| `STATE.md` | Where we are + the session contracts. Machine block maintained by the reconciler. |
| `TODOS.md` | The work queue. |

Also binding, and mechanically enforced rather than read:
`docs/memory/RED_CLASSES.md` (the red-class index `tools/construction_gate.py`
requires citations against) and `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md`
(ratified design canon, scored by rubric on design PRs).

## REFERENCE — read when the task touches it

**Process detail behind `HOW_WE_WORK.md`:** `docs/OPERATING_RULES.md` ·
`docs/KAIZEN.md` · `docs/skills/construction_loop.md` · `docs/hats/*` ·
`docs/skills/adversarial_review_v2.md` · `docs/skills/po_provocation.md` ·
`docs/skills/night_shift.md` · `docs/SESSION_START.md` ·
`docs/EXTERNAL_FINDINGS_POLICY.md`

**Engineering reference:** `docs/WORLD_CLASS.md` (the cited authority behind every
bar clause — note its self-audit table is dated 2026-07-12 and stale; `docs/BAR.md`
carries current status) · `docs/CODING_CONVENTIONS.md` · `docs/TESTS.md` ·
`docs/CONFIG_CATALOG.md` · `docs/SCA_BASELINE.md` · `docs/review_personas/*` ·
`tools/README.md`

**Product and domain reference:** `docs/Final_ONE_Live_Authoritative_Technical_Spec.md` ·
`docs/design/ONE_LIVE_VOICE_SEARCH_PERSONAS_v1.md` ·
`docs/strategy/ONE_LIVE_CERTAINTY_DISPLAY_v1.md` (canon for how certainty
displays) · `docs/strategy/ONE_LIVE_CATEGORY_TAXONOMY_v1.md` ·
`docs/strategy/ONE_LIVE_GENRE_TAXONOMY_v1.md` ·
`docs/strategy/ONE_LIVE_PLATFORM_API_INVENTORY_2026-07.md` ·
`docs/strategy/OneLive_AUTONOMOUS_BUILD_CHARTER_and_API_MANIFEST.md` (the key
manifest)

**Live operational records:** `docs/metrics/*` (Kaizen, KPI, Brain IQ ledgers —
machine-read) · `docs/FRICTION_LOG.md` · `docs/AGENT_FEEDBACK.md` ·
`docs/ONE_LIVE_CHANGE_LOG.md` · `docs/memory/decisions/*` (**each is binding for
the decision it records** — read the one that governs your change) ·
`docs/memory/gotchas/*`

## HISTORICAL — never a rule

Records of a moment. Do not build from these without re-verifying against reality.

- `docs/session_arcs/*` — per-session narratives.
- `docs/V1_AUDIT_2026-07-26.md` — this audit. Its *findings* drove `docs/V1.md`;
  the audit itself is a snapshot and goes stale the day it is acted on.
- `docs/ops/INCIDENT_2026-07-22_cron-scheduler.md`, `docs/ops/CLAUDE_CODE_KICKOFF_PROMPT.md`,
  `docs/ops/CHANGELOG_APPEND_2026-07-12.md`, `docs/ops/EXAM_ENVIRONMENT_SETUP.md`
- `docs/research/*` — market and method research, including the PR-aggregator
  analysis and the construction-loop synthesis.
- `docs/strategy/` **PROPOSALS — specified, not authorised:**
  `OneLive_WORLD_CLASS_v1.1_DEEP_REVIEW.md` (§10–§15 remain proposals) ·
  `ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md` · `ONE_LIVE_GROUP_PLANS_v1.md` ·
  `ONE_LIVE_MEMBER_PREFERENCES_v1.md` · `ONE_LIVE_NONMUSIC_EXPANSION_v1.md` ·
  `ONE_LIVE_GROWTH_LOOPS_AND_DESIGN_TOOLS_v1.md` · `ONE_LIVE_INGEST_INBOX_v1.md` ·
  `ONE_LIVE_SOCIAL_COMPOSITE_v1.md` · `ONE_LIVE_ACQUISITION_TOOLKIT_v1.md` ·
  `ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md` · `ONE_LIVE_CONVERGENCE_v1.md` +
  `ONE_LIVE_CONVERGENCE_PO_NOTES_v1.md` · `ONE_LIVE_SIGNAL_ACQUISITION_PO_NOTES_v1.md` ·
  `ONE_LIVE_GLOBAL_SENSING_PO_AND_PEIRCE_NOTE_v1.md` · `ONE_LIVE_COST_MATRIX_DRAFT_v1.md` ·
  `ONE_LIVE_KPI_FRAMEWORK_v1.md` · `ONE_LIVE_AGENT_PIPELINE_v1.md` ·
  `ONE_LIVE_CONSTRUCTION_AND_RCA_v1.md` · `ONE_LIVE_MEMOHARNESS_APPLICABILITY_REVIEW_v1.md` ·
  `UNIVERSAL_DEV_OPERATING_MODEL_v1.md`
- `docs/strategy/` **FROZEN — off-mission until v1 is live** (`CLAUDE.md` mission):
  `ONE_LIVE_META_CAROUSEL_ENGINE_v1.md` + `ONE_LIVE_CAROUSEL_EXAMPLES_v1.md`
  (code: `social/`) · `ONE_LIVE_BRAIN_*` ×4 + `ONE_LIVE_HELDOUT_EVAL_v1.md`
  (code: `brain/`) · `ventures/promise_ledger/docs/*` (code: `ventures/`)
- `design/proposals/*` — design iterations and renders.

## Deleted 2026-07-26, and why

Both were factually false and actively misleading; git history keeps them.

- `LIVE_READINESS.md` — dated 2026-07-12; reported master at `a0b3724`, zero
  events, and PR #7 as the blocker. All superseded. Replaced by `docs/V1.md`.
- `docs/SPRINT_LIVE_SITE.md` — stated in bold *"PLAN ONLY — nothing in this file
  has been executed. Zero deploys, zero migrations, zero spend so far."* Thirteen
  migrations are applied, the cron is armed, and the AI budget is exhausted.
  Replaced by `docs/V1.md`.

## The rule that keeps this file honest

**A new document must be classified here in the same commit that creates it.** An
unclassified document defaults to HISTORICAL — it binds nobody and authorises
nothing. If you want it to bind, say so explicitly and expect that to be reviewed.
