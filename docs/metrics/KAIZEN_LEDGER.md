# KAIZEN LEDGER — append-only measures (docs/KAIZEN.md)

Greppable summary: one row per merged PR (M1 rounds-to-green, M2 catches by
gate/class, M5 est. cost), plus event rows for M3 escapes (immediately),
M4 gate-gap fixes, M6 po harvests. Rows are never edited after append —
corrections get a new row referencing the old. Trends quoted in the weekly
founder digest in plain language.

## PR rows

| Date | PR | M1 rounds | M2 catches (gate: class × n) | M4 gate-gaps closed | M5 est. cost | Notes |
|---|---|---|---|---|---|---|
| 2026-07-13 | #11 | 3 | evaluator: reviewer-supply-chain ×2, silent-truncation ×1, coverage-gap ×2, SCA-gap ×1; CI: empty-env ×1 | trusted-base-ref bootstrap; no-path-filter; blocking SCA gate | ~3 evaluator calls + CI | gate armed itself; bootstrap merged red under human review (documented exception) |
| 2026-07-13 | #12 | 2 | evaluator: fail-open budget ×2, shell-injection-surface ×1, empty-env ×1, audit-trail ×1 | fail-closed caps at every layer; env-only workflow inputs | ~2 evaluator calls + CI | |
| 2026-07-13 | #13 | 1 | — | — | ~1 evaluator call | communication rules (docs-only) |
| 2026-07-14 | #14 | 5 | evaluator r1: trust-invariant-not-enforced ×2, enforcement-not-wired ×2, silent-deferral ×3; r2: fail-open-provisional ×2, invariant-not-at-entry-point ×1, overstated-record ×1; r3: swallowed-error(CI) ×2, fail-open-empty-env ×2; r4: unclosable-config-channel ×1 | non-Claude-evaluator invariant (router + reviewer entry point); OPEN-row-only Record enforcement + SQL/block-comment scanning; fail-loud router steps; CI override channel removed | ~5 evaluator calls + CI | repeat class across r3–r4: empty-env fail-open (same class as #11/#12) — see class note below |
| 2026-07-14 | — (session) | — | deferral_scan(SQL pass): pre-existing silent deferral in 0006 RLS comment ×1 (already resolved by 0007; retro-recorded R-011) | SQL + block comments added to scanner | ~0 | M4 example: a widened gate immediately caught a real latent item |
| 2026-07-14 | — (session) | — | external-review(Weco RSI post): charter-prose gap ×1 — gate-tooling changes not named in the evaluator-MANDATORY list; no founder interrupt on gate relaxations | gate custody added to charter; threshold relaxations now founder-crucial (CI enforcement predates the prose — adversarial-review.yml was already path-filterless per #11) | ~0 | class: gate-custody-prose-gap; caught by founder-supplied external article review, founder approved amendment same day |
| 2026-07-15 | — (first real run) | — | pipeline fail-loud: stale extraction model id (claude-3-5-sonnet-latest, 404) ×1 — class: stale-model-config; log review: run reported SUCCESS + dead-man pinged healthy despite 3/3 sources erroring ×1 — class: fail-open (silent-degradation) | model id → routed tier + P3 liveness check queued; TotalRunFailure raises so dead-man pings /fail on zero-work runs | ~$0 (calls 404'd) | infrastructure itself green first try: DB (266 sources), caps, splice, replay, pings |
| 2026-07-15 | #21 | 3 | evaluator r1: invariant-not-at-entry-point ×1 (provider bypassed router gate — repeat class from #14), fail-open explicit-param ×1, ungated-model-change ×1 (my own KAIZEN §M7 rule enforced against me) | provider wired through router (tools now a package, single-sourced id); blank explicit model fails closed; model change WITHDRAWN until the Step 6 golden gate exists (R-013) | — | the reviewer enforcing the ratchet doc within hours of it merging |
| 2026-07-14 | #16 | 1 | — | — | ~1 evaluator call | harness-review adoptables (docs-only) |
| 2026-07-14 | #17 | 2 | evaluator r1: dispute-collapse-in-candidate-idea ×1, link-possession-elevation ×1 (+3 nits: DMARC alignment, fast-lane contradiction check, hibernation reachability) | disputes never collapsed; magic links only initiate verified claim flows | ~2 evaluator calls | sensor canon |
| 2026-07-14 | #19 | 3 | evaluator: GITHUB_ENV secret-scope regression ×1, add-mask escaping hole ×1, scope-without-masking ×1, untruthful-record ×1 | credential scoped to one step AND escaped-masked; assembly in tested script; no-secret-in-errors invariant | ~3 evaluator calls | DSN founder-ergonomics |
| 2026-07-15 | #22 | 1 | — | — | ~1 evaluator call | measured-unit definition (docs-only) |
| 2026-07-15 | R-006 ratified | — | — | the 1% bar + one-way ratchet codified (KAIZEN §M7); extraction remains BLOCKED under R-013 until the golden-set gate ships and the starting model passes (Step 6) | — | founder: "I'm ok to BEGIN at 1%" — the NUMBER is ratified; the gate that proves it is next |

## Class watch (M2 repeat classes — these must trend to zero)

- **empty-env fail-open**: seen PR #11 (model var), #12 (source cap), #14 r3–r4
  (review model). Gate response has now escalated three times (or-default →
  hard-fail → channel removed). If this class appears again, the process fix
  is structural (an env-contract linter for workflows), not another patch.

## M3 escapes (absolute-zero goal)

| Date | What escaped | Where found | Root cause | Gate-gap closed |
|---|---|---|---|---|
| — | none recorded to date | | | |

## M6 po harvests

| Date | Decision/plan | Provocations run | Ideas surviving gates |
|---|---|---|---|
| 2026-07-14 | Scale-out sensor architecture (RATIFIED) | Full battery, seed 20260714, word "beehive" — all P1–P8.6 | 5 candidates harvested into the doc appendix + TODOS triage item (multi-party authority; burst/hibernation lifecycle; per-source extraction templates; confirm-your-listing magic link; change-rate attention allocation) — survival through design gates TBD at Step 7 |
| 2026-07-14 | Global sensing challenge (founder research note — PROPOSAL) | Full battery, seed 20260715, word "anchor" — all P1–P8.6, 2 dead ends logged | 12 candidates H1–H12 in docs/strategy/ONE_LIVE_GLOBAL_SENSING_PO_AND_PEIRCE_NOTE_v1.md (two-phase crawl→push; coverage denominator; aggregators-first; second-county drill; zero-result queue; two-tier sensing; source-portfolio economics; anchor-institution bootstrap; community sighting channel; recurrence-as-polling-optimizer; link-graph discovery; sparse-market mode) — all screened against trust invariants, converge at Step 7 |
| 2026-07-15 | Design directions v1 (founder-directed in-house generation) | Full battery, seed 20260716, word "scaffold" — all P1–P8.6, 2 dead ends logged | Adopted into the mockups: first-door rule, fixed control geography, Doorlight signature (P5), Time Rule signature (P7), uniform glyph sky-corner (P8.6). Parked candidates: quiet-night sparse spec (→H12 tie), sequential preview autoplay (white-hat test needed). design/proposals/README.md |
| 2026-07-16 | Dedicated-hat registry design (docs/hats/) | Full battery, seed 20260716, word "scaffold" — all P1–P8.6, 2 dead ends logged | 5 harvested, ALL adopted into the registry: H1 memory-informs-checklists-never-verdicts (P1); H2 vendor-agnostic model bindings via the router (P2); H3 two-tier ritual — sequential cheap mode vs dedicated-parallel for founder-crucial (P3-down); H4 Blue merge pre-registers the decision frame before lenses run (P4); H5 per-hat retirement condition (P7 "scaffold": removed when the building stands) |

## M8 Yellow-hat validated upside (docs/hats/yellow.md)

| Date | Decision | Upside argued | Validated (what shipped and performed) |
|---|---|---|---|
| — | none recorded to date (first firing: the R-008 cron-arming Friction pre-work — see TODOS hat shakedown) | | |
