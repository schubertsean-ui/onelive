# Next Session Kickoff — Sourcing Engine (rewritten 2026-08-03, post-plan)

Per `docs/ops/HANDOFF_STANDARD.md`. Lane note: UI/UX work uses its OWN prompt
(`docs/ops/UI_UX_SESSION_KICKOFF_PROMPT.md`) in a separate session. Rule
(OPERATING_RULES §6a.6): red-team ADJUDICATION belongs to the session that
authored the plan if it is still alive; this prompt exists so ANY session can
do it from disk if not.

---

## PASTE FROM HERE

You are continuing the 1Live SOURCING ENGINE effort. STOP — open ritual first:
`python tools/session_reconcile.py`, then `docs/SESSION_START.md`, `STATE.md`
(trust only after reconcile), `docs/OPERATING_RULES.md` IN FULL — §6a
especially: NO timers/send_later ever; non-user-facing failures never circle;
handoffs meet HANDOFF_STANDARD; proof over assertion; adjudication-stays-
with-evidence (§6a.6).

## Where things stand (2026-08-03 end-state, all PROVEN on origin)

Branch `claude/1live-session-kickoff-uvviqi` = PR #150 (draft). On it, verify
with `git log --oneline origin/claude/1live-session-kickoff-uvviqi | head -15`:
- **Sourcing model v1** (3 layers: protocol pathways / markets-as-data /
  declared specials): `docs/strategy/SOURCING_MODEL_v1.md`,
  `worker/sourcing/markets.py`, `sources/markets/austin.json`, registry-routed
  `tools/import_sources.py --market`. 21 tests.
- **Auto-promote engine** `worker/autopromote.py` + CLI, behind
  `AUTO_PUBLISH_RATIFIED` (default OFF): re-runs gate fresh, PASS-only,
  audits actor_type=system, orchestrator still cannot promote (test-asserted).
  19 tests. One pre-authorized allowlist line in `tools/trust_gate.py`.
- **JS-render fallback** wired in `worker/orchestrator.py` (capped
  `ONELIVE_MAX_RENDERS_PER_RUN`=5, fail-open availability / fail-closed
  trust). NOTE: renders NO-OP on CI until a browser-install step lands in
  `ingest.yml` (separate arming PR).
- **THE PLAN**: `docs/strategy/SOURCING_SCALE_PLAN_v1.md` — five subsystems
  (FIND/READ/VERIFY/PUBLISH/PROVE), phases P0-P5 with proof gates, §3b total
  cost per timeframe, §3c geographic compute doctrine, §3d entity-agent
  adoption flywheel, §5 KPI calibration (Coverage@Window recommended).
  Status: PROPOSAL awaiting founder ratification + external red team.
- **Evidence base** (committed verbatim): `docs/strategy/research/` — five
  reports (benchmark, truth-discovery mechanisms, efficiency design,
  discovery-engine design, KPI calibration). The plan cites them.
- **Red-team package** for manual paste into ChatGPT/Grok/Gemini:
  `docs/strategy/redteam/SOURCING_PLAN_REDTEAM_PACKAGE_v1.md` (+ its §3d
  ADDENDUM at the bottom — include it with Section C when pasting).
- **Decision records** (all 2026-08-03): sourcing-model-three-layer ·
  source-universe-per-segment (windowed 50:1 → provisional) ·
  spark-line-auto-publish-fix · spark-line-grounding-sources.

## CI state on PR #150 (do not re-diagnose — known and compensated)

Three reds re-fire on EVERY push, ONE root cause pair:
1. `trust-gate` + `adversarial-review` red via
   `tests/test_arming_smoke_binding.py`: the render build changed armed-cron
   runtime files (`worker/orchestrator.py`, `worker/fetch/render_fetch.py`)
   so `docs/evidence/ARMING_SMOKE_RUN.json` no longer covers the head.
   FIX (needs founder spend-yes, ~$0.50): dispatch `ingest.yml` on this
   branch with `max_sources=1`, confirm green, update ARMING_SMOKE_RUN.json
   with the new run id in a docs-only commit.
2. `golden-exam` red: refusal because `tools/trust_gate.py` changed; the
   classifier prints NOT manifest-bound → merge-ELIGIBLE under the charter's
   ratified exception once adversarial-review APPROVEs. No spend needed.
Merge condition: evaluator APPROVE + all other checks green + the eligible
golden-exam refusal per charter. Notify founder at merge.

## Founder decisions PENDING (do not proceed on these without answers)

1. Smoke-run spend (~$0.50) to clear CI → merge path for #150.
2. KPI retarget ratification: Coverage@Daily north star (ratio → context
   stat) per plan §5.
3. Plan phase ratification P1→P5.
4. Cost switches: scheduler metronome (AFTER P2), attended re-cert sitting
   (caching+token capture), search API ~$30-80/metro, buy-vs-build stance.
Founder rulings ALREADY given (hold them): engine first, UI/UX best-in-class
fast-follow · windowed KPI (daily/2d/3d/week/weekend/month), never catalog
totals · discovery is an engine per segment · adoption flywheel matters ·
total-cost-per-timeframe is mandatory in all cost talk.

## The work queue (priority order, after decisions land)

1. **Adjudicate red-team feedback** when the founder pastes the three
   external reviews: aggregate, 3-option protocol on conflicts, file
   surviving findings, amend the plan, THEN seek plan ratification.
2. **P1 publish-readiness**: smoke autopromote on real candidates (flag
   still OFF, --real dry inspection), coverage snapshot job v1 (per-window
   dominance + funnel metrics, dead-man watched), render browser-step
   arming PR.
3. **P2 efficiency** (order matters — BEFORE any scheduler fix):
   unchanged-skip + conditional GET (one PR), interim cost ledger,
   change-frequency ledger + due-time rotation. The bundled re-cert sitting
   (caching + usage capture) waits for the founder's calendar.
4. **P3 discovery build** per `docs/strategy/research/2026-08-03_source_
   discovery_engine_design.md` stages D0-D6 (needs decision 4's search API).
5. Standing: shepherd #150 to merge; close-or-drive PRs #145/#112/#108/#109
   per founder word; UI/UX session runs in parallel on its own prompt.

## Hard rules (violations have burned trust — zero tolerance)

Disk is truth (`python tools/staleness_check.py` green at close; update
STATE.md/TODOS.md/changelog). `bash tools/validate` before any PR. Never
claim done/current/canon without re-runnable proof (canon = merged master
ONLY). No timers. One consolidated founder ask-list, plain language,
why-this-not-that, honest tradeoffs, direct links. Never push to a branch
other than your designated one. Trust invariants are physics: AI never
publishes UNVALIDATED (the GATE satisfies this); no pay-to-rank; disputed
shown-never-hidden; every gate fail-closed; gate relaxation = founder-crucial.

## PASTE ENDS HERE
