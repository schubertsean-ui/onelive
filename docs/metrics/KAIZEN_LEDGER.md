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
| 2026-07-14 | #18 (in review) | 2 (r1 red → fixes pushed) | evaluator r1: overstated-provenance ×2 (research doc claimed primary-source-derived pricing + "cites inline" when figures were search-index reads), unauditable-verification-artifact ×1 (journal in transcript, not committed), stale-cross-reference ×1 (contract #4 vs #5 after parallel-session renumber); nits: performative-metric, overstrong-"verified", provisional-license-in-ranked-bucket ×3 | verification journal now a committed artifact; per-subsection source-page lists | ~1 evaluator call | new class: **overstated-provenance in research docs** — watch for repeat; gate caught founder-facing spend/licensing claims presented stronger than their evidence |
| 2026-07-14 | #18 (in review, r2) | 3 (r2 red → fixes pushed) | evaluator r2: fail-open-reuse-rights ×1 (EDGAR company exhibits mislabeled US-gov work), overstated-provenance ×2 (section headers still said "primary-source fetch"; RTPR license simultaneously known-hostile and "unread"), fail-open-licensing-bucket ×1 (provisional France license in the cleared bucket), completion-overclaim ×1 (contract marked COMPLETE with pricing sub-scope deferred); nits: newline, "fetched"→"consulted", in-cell "reported" prefixes, per-vote records ×4 | per-vote verifier records committed (75 votes); STATE completion claim narrowed to "delivered, sub-scope OPEN under R-013" | ~1 evaluator call | overstated-provenance repeat within same PR (r1→r2) — the r1 fix patched the intro but not headers/cells; lesson: fix a provenance class doc-wide, not at the flagged line only |

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
