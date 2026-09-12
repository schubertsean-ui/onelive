# 1Live schedules

Optimal cadence. Fix Process applies if a scheduled run misses or does not fire.
CAPCOG is the test pack only. Locale = device or search.

## Cadence

| Process | Cadence | Why |
|---|---|---|
| desk-ingest write=true doors=all | 06:00 and 14:00 America/Chicago | Pack walk is 40–120 min. Twice daily catches morning listings and afternoon adds without stacking writers. FL-006: newest walk cancels the stale one. |
| Publisher clock | Hourly | Count 1live.co. Read only. |
| M alignment | Hourly | Vision + Goals. Does not patch. |
| Witness | On merge to master | Ingest then count. Event, not a timer. |
| B Definer / Audubon | Daily | Union vs live. One prescription. |
| Atlas | Weekday 08:15 Chicago | Conductor glance. |
| Holmes | On red check | Diagnose. |
| Themis | On PR open | Merge gate. |
| Ortelius | Daily | Fleet map. |
| FIND_AGGREGATORS | On new locale search, or weekly hole refresh | Not a full pack walk. |
| Fix Process | On any miss those seats see | Same 15 steps. A missed schedule is a miss. |

## desk-ingest schedule rule

`on.schedule` runs only on master. Treat schedule as write=true doors=all.
Do not schedule docs-only. Do not stack two writers (FL-006).

## If a schedule misses (Fix Process)

1. Failure — the run did not fire, or fired and live N did not move.
2. Why — one cause (lock, timeout, gate, empty write).
3. Success — the next scheduled run completes on current master and 1live.co is counted.
4. Prescribe — reuse FL-006 if stale lock; else the matching library fix.
5–15. Same loop as any other miss.

A paused Publisher or a dispatch-only ingest with no cron is a miss of this file.
