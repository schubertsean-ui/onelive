# One Live — Building Standard

CTO-level / best-in-class senior-engineer bar. Ratified: 2026-09-07. Density lock raised 2026-09-08. Status: in force.

This file does **not** outrank Coverage Law, Vision, Locale Launch Law, Entity Split Law, or Trust. Those still win on their subjects.
Operating Law still wins on *how a coding session works*.
This file is the **quality bar** every ticket and every bot must meet.

If a ticket ships below this bar, the ticket is not done.

## The lock

- **More of the real world than anyone else.** For any locale we Show, dated+placed listings (mash_n=0) must **exceed the union** of unique dated+placed happenings across **all named public aggregators** we can count for that locale and window — combined, deduped. Combined means union, never Chronicle_N + Do512_N. Unique Places that hold a dated happening must exceed the union of aggregator venues on the same window. Holes, TBA, and invented rows do not count. An uncountable aggregator is UNVERIFIED and is not guessed into the union. CAPCOG named set until a pack names more: Chronicle events, Do512, one civic/desk if it loads without login.
- **Measure, don't assert.** A green PR that does not change the catalog, Tonight, or a measured pipe is not a win.
- **Fail closed.** Unconfirmed fetch: no delete, no date edit, no cancel. 403 is unknown, not empty. Search snippets are leads, never listings.
- **Identity first.** mash_n = 0 before a public write. One happening, one row.
- **General model.** No category weighting. No `if austin`. Peculiarities live in pack JSON / identity patterns.
- **Beautiful, not dense.** First screen answers: what's on, here, when. Traffic out to the specialist is a feature.
- **Trust is infrastructure.** Gates exist so the map can be trusted. They are not the product.
- **Privacy is Apple-level.** Person location never shares a column with event location. Heartbeat is de-identified or it does not ship.
- **Anti-attention.** Time-on-site is not a KPI. Get in, decide, leave.
- **Smallest change that moves the bar.** One ticket, one PR. Ceremony never outranks the ticket. Budgets stop a tick; they are not the universe.

## Engineering (world-class, mechanical)

1. Tick budgets (wall-clock, extract calls, fetches, per-host) fail closed on typo — never uncapped.
2. Skip-unchanged before extract. Event-proximity ladder for published rows. Adaptive refresh.
3. Independent evaluator on trust-path diffs. REQUEST-CHANGES on a real defect: fix that defect only.
4. Armed-cron files: do not touch without an authorized smoke/evidence path.
5. Production writes and new vendors are founder-authorized. Atlas does not spend money quietly.
6. Views filter; they never delete catalog rows. N of M is true.
7. Impediments are work (ONE-LIVE-CONDUCTOR.md). Master CI red is P0. Rebase conflicts. Recapture an intended visual. Fill an empty PR. Do not write a new law instead of opening the error.

## Agents

- **Atlas** conducts: GitHub, merge when green+APPROVE, bots, density bar. Owner is not the builder.
- **Claude** builds: one Must-do, then stop. `@claude` on an issue after the mention workflow lands.
- **Bots** are narrow. Split only when rules conflict. Read-only unless the founder authorized a write. Quiet if nothing material. Report UNVERIFIED rather than reuse stale numbers.
- Approval required for: money, legal, credentials, production writes, new vendor, Vision conflict.

## Using this file

A ticket that ships fewer unique dated+placed rows than the **union** of the aggregators it cites, hides a disputed row, invents a date, or treats CAPCOG as the catalog, is below the bar. Note it under Refused rather than merge it.
