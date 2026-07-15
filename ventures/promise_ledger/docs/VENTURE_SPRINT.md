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
| 1 | Groundwork: claim schema, golden harness, EDGAR client, storage design | — | DONE (Contract #7, in evaluator loop) |
| 2 | Point-in-time ledger store v0 (append-only, as-of reads, corrections-as-events) | — | DONE this contract (#8) |
| 3 | Due-date parser v0 (deterministic; fiscal flagged, not guessed) | — | DONE this contract (#8) |
| 4 | ⛔ Live EDGAR run 1: pull ~50 real 8-K EX-99 press releases (one sector, budgeted), verify two-stage exhibit discovery against reality | **sec.gov egress** (R-017 unblock) | BLOCKED — founder: allowlist sec.gov/data.sec.gov/efts.sec.gov or provide an unproxied runner |
| 5 | ⛔ Golden set 1: hand-label ≥20 real examples (replaces synthetic; synthetic marked superseded, kept) | Step 4 | BLOCKED on 4 |
| 6 | ⛔ Extraction v1: LLM claim extraction against the golden set; iterate to the precision bar; hallucination threshold per R-006's eventual ratified number | Step 5 + **spend cap set in console FIRST** (charter) + R-017 cleared | BLOCKED on 5 |
| 7 | Cadence model + silence detection over backfilled timelines (deterministic first pass) | Step 4 (needs real timelines) | BLOCKED on 4 |
| 8 | Promise-maturity calendar + overdue alerts (parser + store + cadence) | Steps 2–3 done; real value needs 4 | Partially buildable now |
| 9 | ⛔ Sector taxonomy + coverage SLO for the beachhead | **Founder picks sector** (memo stands) → po battery + friction attack on the choice | BLOCKED on founder |
| 10 | Machine-readable surface: promise-markup API + MCP server (read-only, self-hostable) | Steps 5–6 green | Design can start |
| 11 | ⛔ Wire supplement: contract ONE provider per R-016's written answers | **R-016** (letters drafted, unsent; primary-source pass egress-blocked) + founder spend approval | BLOCKED |
| 12 | ⛔ Extraction of venture to its own repo + infra decisions (DB engine, hosting) | Founder call (new services = founder-crucial) | BLOCKED on founder |

## Standing rules for every step
Tests in the same PR · evaluator review through the gate · no verdict above
`likely` until golden-set precision is proven AND the confirmed-verdict
criteria are ratified by the founder · point-in-time invariant is
non-negotiable · every deferral gets an R-row.

## The critical path, plainly
Everything funnels through **step 4 (sec.gov access)**. Until then the
buildable remainder is: step 8's calendar mechanics, step 10's API design, and
hardening of steps 1–3 through the evaluator loop.
