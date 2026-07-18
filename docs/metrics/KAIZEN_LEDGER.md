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
| 2026-07-14 | #15 | 2 | evaluator r1: fail-open coverage knob ×1, partial-coverage-as-full ×1 (battery trimmable while claiming "run EVERY prompt") | combos knob removed; tests fail if any P8.x missing | ~2 evaluator calls | row added 2026-07-15 — see record-missing note in class watch |
| 2026-07-15 | #23 | 1 | — | — | ~1 evaluator call | session-close arc (docs-only); row added 2026-07-15 |
| 2026-07-15 | #24 | 4 | evaluator: ratification-path governance hole ×1 (founder acceptance is the ONLY ratification path for founder-facing decisions), untruthful-record ×1 (ledger/changelog described intended state as existing), + structural nits | ratification-path rule written into the display-stack canon; records describe what EXISTS | ~4 evaluator calls | certainty display stack; row added 2026-07-15 |
| 2026-07-15 | #25 (in flight) | 5+ | evaluator r1–r4: exam-channel confinement (grep→runtime) ×2, None-swallowed-as-empty ×1, mismatch-display-only ×1, self-contradicting keys ×3, + nits; r5: wrapper-hole confinement ×2 (runtime + static layers), evidence-channel visibility ×2, sample-floor semantics ×1, secret-on-PR posture ×1 (→ R-014); exam cycles 1–4: prompt–key contradictions ×7 (title conventions), key incoherence ×3 (g004 vs g037/g066; g044), prompt–exam contamination ×1 (golden key strings cited as prompt examples) | two-layer golden_exam confinement; validity = property of the set; key-change log with justifications (ai/golden/README.md); prompt examples must be invented, never golden strings | 5 evaluator calls + 4 real exams (~$2 total) | final row at merge |
| 2026-07-17 | #25 (merge-coordination land) | 1 | evaluator: gate-truthiness-not-exact-boolean ×1 (`resolve_model` still used `not FLAG` after the r26 provider fix hardened only the provider read — REPEAT CLASS of r26, one production layer missed) | router extraction gate → exact `EXTRACTION_THRESHOLD_RATIFIED is not True`; repo-wide derived-completeness grep confirms BOTH production reads (provider + router) are now exact-boolean; router-level regression test asserts truthy non-bool ("False"/1/"yes") keeps extraction closed | ~1 evaluator call | in-flight repeat-class rule applied: fixed the CLASS by deriving the complete set of flag-reads (2), not just the flagged instance |
| 2026-07-16 | #27 | 4 | evaluator r1: gate-custody-ambiguity ×1 (sequential mode could look like it discharges Black custody), unverifiable-validation-claim ×1; r2: record-precision ×1 (pytest count didn't match CI log — same class as #20 r18's history-must-match-suite); r3: finding-laundering-path ×1 (generator-family Blue merge allowed on founder-crucial runs), exam-custody ×2 (lens-owned golden-set rows in TODOS + white.md) | fail-closed Blue-merge family constraint; exam custody never lens-owned; raw-outputs-preserved rule for manual hat runs | ~4 evaluator calls + CI | dedicated-hat registry (docs/hats/) — notable: the evaluator enforced custody language in the document that DEFINES custody; the M6 row for the design's po battery merged in the same PR; founder merged ("You merge it"), squash 2c1ef94 |
| 2026-07-18 | — (session, PR #35 in flight) | — | founder(Red): skip-report-missing-record-citation ×1 (visual_regression SKIP reported without citing R-002); evaluator r1 (f654c0f): gate-evidence-missing ×1, unverifiable-ci-claim ×1 (REPEAT CLASS — #20 r18 / #27 r1–r2 family, third PR); evaluator r2 (c384bf2): deferred-class-fix ×1 (queueing the mechanization after the repeat-class threshold was itself the violation — "a prose rule is not a failing gate") | SHIPPED same PR after r2: tools/skip_record_binding.py (fail-closed, 9 tests) + validate skip→Record binding (unrecorded skip = RED even under --allow-skips) + machine-stamped evidence block (stdout + .validate-evidence.txt) + adversarial-review.yml attaches validate.log to the evaluator — evidence generated, never hand-copied; SESSION_START prose now points at the mechanism | ~3 evaluator calls | class watch: unverifiable-claim family's structural fix now exists — a fourth catch of this class is an escape of the new gate, not another instance. Final M1 row at merge |
| 2026-07-18 | — (marker backfill) | — | no new catches — this correction row adds machine-readable M4 class markers for fixes that had ALREADY shipped, per the new docs/KAIZEN.md trend-instrumentation convention (rows are never edited; corrections append) | silent-deferral → deferral_scan SQL/block-comment widening (shipped, #14 M4); keys + contradictions + incoherence (the #25 exam-cycle prompt–key classes, prose names truncated by the token convention) → key-change log + validity-as-property-of-the-set + two-layer confinement (shipped, #25 M4) | — | `empty-env` deliberately NOT marked: its structural fix (env-contract workflow linter) is unshipped — the kaizen_trends alarm stays red-loud until it lands (R-019, TODOS P2) |
| 2026-07-18 | — (session, PR #35 in flight, cont.) | — | evaluator r3 (b9d3c99): fail-open-quick-exemption ×1 (note-substring exemption bypassable), fail-open-loose-binding ×1 (raw substring could bind unrelated Record rows), stale-evidence ×1 (arc carried a dirty-worktree block for a superseded head — repeat-adjacent to unverifiable-claim) | QSKIP structured status (exemption by state, never note text) + backticked-marker binding (incidental mentions never bind) + binding loop extracted to sourced tested file (5 loop tests) + arc evidence replaced by CI-artifact pointer; kaizen_trends meter SHIPPED (mechanizes the repeat-class + escapes-zero + trend-direction rules — trends computed, never asserted, per founder direction 2026-07-18) | ~1 evaluator call | the meter's first real run immediately caught R-019 (empty-env) and the marker-convention gap — instrumentation paying for itself on day one |
| 2026-07-18 | — (session, PR #35 in flight, r4) | — | evaluator r4 (7442f9a): self-firing-trigger ×1 (R-019's "next workflows-touching PR" trigger fired IN the PR that wrote it — the r2 deferral failure mode, subtler form, caught third time running), short-token-alarm-gap ×1 (class regex length floor let `sql`-style tokens escape counting), substring-fix-credit ×1 (M4 credit by raw substring — the r3 loose-binding pattern, meter edition) | empty-env CLASS FIX SHIPPED: tools/workflow_env_lint.py (R1 visible-source for every consumed env var, R2 vars. context ban, blocking in validate, 13 tests, 7/7 live workflows clean) — R-019 RESOLVED same day; meter hardened: no length floor on class tokens, exact-token M4 credit, single-segment tokens never absorb compounds | ~1 evaluator call | deferral-refusal is now 3-for-3 (r2, r4×2): the lesson is structural — never write a trigger your own diff fires; the alarm this row clears was created and resolved inside one PR |
| 2026-07-18 | — (session, PR #35 in flight, r4-fix push) | — | self(validate): pushed-on-red ×1 (commit cb87a84 pushed while validate was RED — the agent's shell chained `git commit && git push` off a `sed` pipeline that swallowed validate's exit code; the red itself was deferral_scan correctly flagging untagged deferral language in a test comment, plus its mirror pytest failure) | comment reworded (not a deferral — resilience description); process rule for the agent: NEVER chain commit/push off a pipeline containing validate — run validate bare, check its exit, then commit (candidate mechanization: a pre-push hook running validate --allow-skips, noted in AGENT_FEEDBACK) | ~0 | caught by the very next validate read, fixed in the immediately following push; CI red on cb87a84 is this defect's public trace |

## Class watch (M2 repeat classes — these must trend to zero)

- **empty-env fail-open**: seen PR #11 (model var), #12 (source cap), #14 r3–r4
  (review model). Gate response has now escalated three times (or-default →
  hard-fail → channel removed). If this class appears again, the process fix
  is structural (an env-contract linter for workflows), not another patch.
- **fail-open (threshold/floor mismatch)**: r6 on PR #25 caught the exam's
  300-fact floor silently moved from ASSERTED to EXPECTED facts by an r5
  refactor — a rate-passing run at 295 asserted facts was minutes from
  certifying the gate open. Caught internally by the evaluator's first
  graded round after billing was restored; zero escapes. Same class family
  as #11/#12/#14 empty-env — fail-open now has TWO sub-classes on watch.
- **incomplete-enumeration (binding/trigger lists)**: PR #28 r22 (evidence
  didn't bind the golden set), r23 (didn't bind the scoring/provider files),
  r24 (didn't bind dependencies or the dispatch workflow) — three rounds of
  one class, each hand-adding one item to a list. Structural response
  shipped 2026-07-17 (founder-prompted meta-review): the exam's import
  closure is now COMPUTED by a test and required to be a subset of the
  manifest, and the release gate's trigger paths are cross-checked against
  the manifest by a second test — the derived checks immediately found two
  more instances a fourth hand-audit had missed (tools/__init__.py absent
  from both the manifest and the trigger list). Process rule added to
  docs/KAIZEN.md: in-flight per-round class tracking; every hand-maintained
  trust-guarding list gets a derivation/cross-check test. If this class
  appears again on any OTHER list, the response is a repo-wide enumerated-
  list audit (workflow paths filters, allowlists, skip lists), not a patch.
  TRIGGER FIRED same day (2026-07-17, evaluator r26): the dependency
  binding enumerated 2 of 23 resolved packages — another mirror-list
  instance, created pre-rule, discovered post-rule. Escalation executed:
  the instance became derived (full lockfile installed with --no-deps;
  verifier requires every locked entry recorded at its locked version),
  and the repo-wide enumerated-list audit ran. Audit method: classify
  each list as POLICY (the list IS ground truth: promote/exam allowlists,
  ads markers — nothing external to derive from) vs MIRROR (tracks
  external reality — must be derived or swept). Findings: the exam-
  critical mirrors were already closed by the day's derived tests; the
  SQL/ads/promote invariant scans were directory-enumerated (ai/
  production code and any future scripts/ dir unscanned) — widened to a
  repo-wide-minus-tests production sweep, single-sourced skip list
  (tests excluded by documented design: they build stub SQL and import
  promote to test the guard itself). The widened scans surfaced no
  production violations. Class considered structurally closed; a further
  instance is a process escape and gets a root-cause row here.
- **record-missing / untruthful-record**: #19 (untruthful-record), #24 (same),
  and 2026-07-15: rows for merged PRs #15/#23/#24 were absent from this table
  while the changelog claimed the #15 row existed (caught during #25 r5
  bookkeeping; backfilled same commit). Two more appearances of this class
  and the fix is structural: a validate-gate check that every merged PR
  number since #11 has a ledger row.

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
