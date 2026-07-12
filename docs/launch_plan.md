# OneLive — Stealth Launch Plan (world-class bar, autonomous build)

**Owner:** Sean Schubert. **Directive (2026-07-11):** drive to a world-class
live stealth site autonomously and fast; return only with final go-live
decisions the founder must make. Quality bar = docs/OPERATING_RULES.md §1
(world-class across EVERY aspect; test-as-you-go).

This is the durable checklist. It survives context compaction. Each gate ends in
a verified state (full pytest + trust_gate green) and a commit on the branch.

## Gates (in dependency order)

1. **Eval loop (Layer 4)** — DONE (commit 651abfd). 14-case adversarial corpus +
   deterministic runner reusing the one scorer; over_suppression first-class;
   sabotage tests prove it reports failure. `python -m ai.eval_loop` exit 0,
   gate/sensor accuracy 1.000, over_suppression 0.000.

2. **Source schema: geo/coverage dimension** — DONE (commit 8b3fc9b). Migration
   0010 adds `county` (CHECK-constrained to the 5-county MSA), `sub_region`,
   `coverage_categories`; importer writes + upserts them (commit 9a70a04).

3. **Real source catalog** — DONE (commit a85da83). 193 VERIFIED sources across
   all 5 counties (Travis 86, Williamson 39, Hays 36, Bastrop 18, Caldwell 14).
   196 candidates from browser research → HTTP sweep → browser re-verification
   of every non-200 → 8 URLs corrected, 3 dead dropped. NEVER model-invented.
   `sources/austin_metro_catalog.json` is canonical; old 43 renamed *_LEGACY.

4. **Coverage report** — DONE (commit 9a70a04). `tools/coverage_report.py` renders
   the county × category grid and surfaces coverage debt (empty cells,
   uncategorized, out-of-domain county). Proven on both catalogs.

5. **Pipeline on real data** — PARTIALLY VERIFIED (honest scope).
   - VERIFIED DB-less on REAL data (`tools/real_source_probe.py`): 189/193 real
     source pages fetch (98%; the 4 misses are sandbox SSL/403 artifacts on
     sites confirmed live in-browser), and **189/189 fetched pages pass the
     hardened context-hygiene sensor (100%, zero over-suppression on real data)**
     — the first real-world failure mode (silent sensor rejection) is measured
     and clear. Fixed a latent bug in `worker/run_once.py --real` found here:
     it queried non-existent columns (`active`/`url`/`source_class`); corrected
     to the real schema (`enabled`/`base_url`/`source_type`).
   - NOT YET RUN: full `--real` (fetch→extract→gate→promote) end-to-end and
     hallucination_rate on real extractions. BLOCKED by environment, not code:
     `fetch_url` writes a raw_fetch audit row and `extract_candidate` writes the
     candidate store, so every real stage needs a live Postgres; extraction also
     needs the model key. The build sandbox has neither. This is a Gate-9
     founder-environment decision (point prod DSN + key, run one real cycle),
     documented rather than faked. The extract→gate→promote path IS exercised
     hermetically by the suite + eval loop; only the real-data measurement waits.

6. **Public feed UI** — `/tonight` + event feed, world-class UX: loading/empty/
   error states, accessibility, copy, and trust display (confidence states:
   confirmed/likely/unverified/disputed all render with their state). Exit: renders real
   promoted events from the API.

7. **Deploy + stealth gate** — wire public API to Supabase in prod; deploy web
   app; invite/password wall for stealth. Exit: a real URL reachable behind the
   gate.

8. **World-class QA on live data** — security, performance, failure semantics,
   observability; final trust review across all aspects. Exit: no unnamed
   weakness; every aspect graded with named comparisons.

9. **Founder finalize** — return with the live URL + the decisions only the
   founder can make (domain, invite list, stealth copy, launch timing, any
   category/geo scope calls). Do NOT bounce answerable questions back.

## Discipline
- Sunset Law before adding guards; sabotage-validate every guard.
- Findings are claims until verified against ground truth.
- Checkpoint arc + STATE.md before compaction; update this file as gates close.
