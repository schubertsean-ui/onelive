# Promise Ledger — build sprint to MVP (v1, at greenlight 2026-07-15)

**Founder greenlight:** "Go" (2026-07-15). This plan sequences the build with
every gate marked. It is attacked by the independent evaluator through the PR
gate like everything else. Steps marked ⛔ cannot start until their gate
clears; everything else is sector-agnostic and free.

## Definition of MVP

For one beachhead sector: per-entity promise timelines over EDGAR 8-K press
releases (backfilled ≥5 years), claim extraction passing the golden-set
precision bar on REAL examples, promise-maturity calendar + overdue/silence
alerts, machine-readable output (the promise-markup schema over an API/MCP
surface), verdicts capped at `likely` until the confirmed-verdict criteria are
ratified. No paid sources in the MVP.

## Steps

| # | Step | Gate | Status |
|---|---|---|---|
| 1 | Groundwork: claim schema, golden harness, EDGAR client, storage design | — | DONE (Contract #16, in evaluator loop) |
| 2 | Point-in-time ledger store v0 (append-only, as-of reads, corrections-as-events) | — | DONE (Contract #17; r22 hardening: recorded_at knowledge horizon + source_retrieved writer) |
| 3 | Due-date parser v0 (deterministic; fiscal periods NEVER resolved to calendar dates) | — | DONE (Contract #17; r22: fiscal phrases return no due_date) |
| 4 | Live EDGAR run 1: pull ~50 real 8-K EX-99 press releases (financials, budgeted), verify two-stage exhibit discovery against reality | ~~sec.gov egress~~ **UNBLOCKED 2026-07-15** (founder allowlisted www.sec.gov; data.sec.gov/efts.sec.gov still asked, non-blocking) | STARTED (Contract #18): first live run done — real JPM/BAC press releases stored with provenance, authoritative exhibit-type path verified against reality; next: expand toward ~50 across the ~130-bank universe (H-S4) |
| 5 | ⛔ Golden set 1: hand-label ≥20 real examples (replaces synthetic; synthetic marked superseded, kept) | Step 4 corpus | UNBLOCKING — source material accumulating (2 of ≥20) |
| 6 | ⛔ Extraction v1: LLM claim extraction against the golden set; iterate to the precision bar; hallucination bar RATIFIED at 1% (R-006) — the golden-set exam gate that proves it is R-013 | Step 5 + **spend cap set in console FIRST** (charter) + R-017 cleared + R-013 gate green | BLOCKED on 5 |
| 7 | Cadence model + silence detection over backfilled timelines (deterministic first pass; incl. the 2023-regionals stress-window backtest, H-S2) | Step 4 at scale (needs real timelines) | BLOCKED on 4 completion |
| 8 | Promise-maturity calendar + overdue alerts (parser + store + cadence) | Steps 2–3 done; real value needs 4 | Partially buildable now |
| 9 | Sector taxonomy + coverage SLO for the beachhead | ~~Founder picks sector~~ **DECIDED 2026-07-15: FINANCIALS** → charter po battery run same day (harvest H-S1..H-S8) | OPEN — build seeded by H-S1 (claim classes beyond guidance) + H-S4 (named ~130-bank universe) |
| 10 | Machine-readable surface: promise-markup API + MCP server (read-only, self-hostable) | Steps 5–6 green | Design can start |
| 11 | ⛔ Wire supplement: contract ONE provider per R-016's written answers | **R-016** (letters drafted, unsent; primary-source pass egress-blocked) + founder spend approval | BLOCKED |
| 12 | ⛔ Extraction of venture to its own repo + infra decisions (DB engine, hosting) | Founder call (new services = founder-crucial) | BLOCKED on founder |

## Standing rules for every step
Tests in the same PR · evaluator review through the gate · no verdict above
`likely` until golden-set precision is proven AND the confirmed-verdict
criteria are ratified by the founder · point-in-time invariant is
non-negotiable · every deferral gets an R-row.

## The critical path, plainly
Step 4's gate cleared 2026-07-15 (www.sec.gov unblocked; first live run done).
The critical path is now **step 4 at scale → step 5 (≥20 real labeled
examples) → step 6 (extraction behind the R-013 exam gate + spend cap)**.
Buildable in parallel: step 8's calendar mechanics, step 10's API design,
step 9's taxonomy from the H-S harvest.
