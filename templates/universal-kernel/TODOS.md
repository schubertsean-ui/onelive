# TODOS — the task queue

Format: `- [ ] (P0-P3) Task — owner — context`. Autonomous work picks the
highest-priority unchecked item it can do without a founder decision. Check
items off in the same commit that completes them; leave the line in place —
completed items are a record of what got done, not clutter to delete.

## Priority key
- **P0** — blocks a phase, or ships something unsafe if skipped.
- **P1** — needed before the next phase's user-facing surface ships.
- **P2** — real gap, not currently blocking.
- **P3** — nice-to-have / ongoing background work.

## Bootstrap (delete this section once complete)
- [ ] (P0) Fill `OVERLAY.md` bindings 1–8 — owner: Generator (drafts) → founder (ratifies 1, 3, 8).
- [ ] (P0) Wire the independent evaluator on EVERY pull request, no path filter — owner: Generator; needs the founder to mint one API key (agents never mint keys).
- [ ] (P0) `tools/validate` runs green honestly; project checks registered in `tools/project_checks.d/`; every skip bound to a Record row — owner: Generator.
- [ ] (P1) Sentinel before any scheduled job: error tracking + dead-man ping + budget caps — owner: Generator (wiring) → founder (credentials).
- [ ] (P1) Declare the adoption step per surface with evidence (`OVERLAY.md` binding 8) — owner: founder.

## Standing items (do not check off)
- [ ] (P2, STANDING) Kaizen ledger discipline — every merged pull request gets its row; repeat classes get a structural gate-gap fix at the recurrence's actual surface.
- [ ] (P2, STANDING) Record review at session close — a fired-but-unactioned trigger is a defect.
- [ ] (P2, STANDING) Threshold ratchet watch — thresholds tighten by their ratified rule; loosening is founder-crucial.
