# Arc 2026-07-14/15 — First real run, the quality ratchet, and the sensor canon

Greppable summary: the marathon founder session (2026-07-13 → 07-15,
continuous conversation, PRs #14–#22 all merged): po+Kaizen chartered and
built; scale-out sensor architecture RATIFIED (watchers, three modes,
first-party = confirmed); all four secrets landed via founder; FIRST REAL
INGESTION RUN (infrastructure green end-to-end, extraction failed loud on a
retired model id); R-006 ratified at 1% with the one-way ratchet (M7);
extraction gated at every entry point until Step 6 ships the golden-set
exam (R-013). The evaluator loop matured from 5 rounds-to-green (#14) to
1 (#16, #22).

## Founder decisions ratified this arc (verbatim anchors in the canon docs)
1. **"All three"** — po battery (maximally robust: all operators standalone
   + ALL random×operator combos, never trimmable), Kaizen measures (zero
   ESCAPED defects absolute; internal catches mined by class), levels
   deferred (R-012). → CLAUDE.md "Thinking tools & Kaizen", docs/skills/
   po_provocation.md, tools/po_battery.py, docs/KAIZEN.md, ledger.
2. **Scale-out sensor architecture** — watcher records (not idle agents),
   pull/push/investigate modes, provenance-weighted gate: validated
   first-party assertion about OWN event logistics enters `confirmed`
   (DMARC-aligned channels OR authorized in-product account); scoped
   authority / no command authority / disputed-still-wins; channel
   playbook; gated scout swarm. → docs/strategy/
   ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md (build triggers Step 7+).
3. **R-006: "I'm ok to BEGIN at 1%"** + confirm the improvement mechanism →
   KAIZEN §M7 one-way ratchet (drop to 2× measured after 4 clean half-bar
   weeks at valid sample size; 1%→~300 facts … 0.001%→~300k) + precise
   unit definition (field assertion; recall anti-gaming pair; event-level
   secondary measure).

## Ground-truth events
- **Secrets landed** (founder, via phone — with the DSN splice built to
  spare hand-editing credentials): OPENAI_API_KEY, ONELIVE_DB_DSN (+
  ONELIVE_DB_PASSWORD), ANTHROPIC_API_KEY, ORCHESTRATOR_PING_URL.
- **First real run** (run #2 of ingest.yml, 2026-07-15, cap=3): DB
  connected (266 enabled sources read), budget cap enforced, dead-man
  pinged, replay artifact persisted. Extraction 404'd ×3 on retired
  `claude-3-5-sonnet-latest` — failed LOUD, nothing false entered the
  pipeline, ~$0 spent.
- **Two catches from that run** (ledger M2): stale-model-config; and the
  run reporting SUCCESS + healthy dead-man ping despite 3/3 errors
  (fail-open class) → `enforce_useful_work` now RAISES TotalRunFailure.

## Decisions with reasoning (the *why*)
- **Extraction stays blocked despite ratification (R-013):** ratifying the
  bar ≠ evidence the bar is met; the golden-set gate doesn't exist yet.
  The evaluator enforced KAIZEN §M7 against its own author's PR within
  hours of it merging — no extraction model change ships without exam
  evidence. Provider now resolves through tools.model_router (tools is a
  package; single-sourced id) with the gate checked FIRST on every
  construction path — explicit `model=` selects WHICH, never WHETHER.
- **CI reviewer-model override channel removed** (PR #14 arc, r4): GitHub
  renders unset and set-but-empty repo variables identically; the channel
  cannot fail closed, so it was deleted — changing the CI reviewer model
  is now a PR the OLD model reviews.
- **DSN ergonomics with defense in depth** (PR #19, 3 rounds): as-pasted
  Supabase URI + separate password secret, spliced by a tested script
  INSIDE the single step that needs it AND masked via escaped add-mask —
  scope and masking, both layers.

## Kaizen trend (M1 rounds-to-green)
#14: 5 · #15: 2 · #16: 1 · #17: 2 · #19: 3 · #21: 3 · #22: 1.
Repeat-class watch: empty-env fail-open reached its 4th appearance (#21,
extraction env) — per the ledger rule, a 5th demands a structural fix
(env-contract linter), not another patch.

## Open threads → next session
1. **Step 6 golden-set gate (TOP, unlocks everything):** ≥40-example
   golden set (~320 facts ≥ the 1% sample floor; include injection cases
   per SPRINT Step 6), live-exam runner exercising the REAL provider path
   (needs a deliberate, documented exam channel past the R-013 gate — the
   runner is the gate's evidence-generator; design carefully, evaluator
   will rightly probe it), blocking CI job, flag flip with passing result.
   Contract-first, evaluator mandatory.
2. R-008 cron arming: secrets now exist, but arming waits for Step 6
   (armed cron + blocked extraction = every run alarms). Friction attack
   (opened by the po battery, per charter) before the arming PR.
3. R-005: verify OPENAI_API_KEY in the session env at next session start;
   re-attack FRICTION_LOG #1 non-Claude.
4. Founder one-liners still open: PRs #4/#7 (recommend close both);
   4-state confidence model confirmation ("confirmed").
5. R-004: GROUND_TRUTH block still machine-unverifiable from this sandbox.
