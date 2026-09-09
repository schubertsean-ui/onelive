# 1Live schedules

Founder 2026-09-09: no process waits for a manual click.
A missed or failed schedule is a Fix Process kickoff (step 1).

## Cadence (why)

| Process | Cadence | Why |
|---|---|---|
| desk-ingest write=true doors=all | Every 2 hours | Desks change through the day. A walk can take up to 2 hours. FL-006: a new walk replaces a stale one. Faster than 2h stacks walks. Slower misses same-day listings. |
| M alignment | Hourly | Vision/Goals independent of tickets |
| Publisher clock | Hourly | Live N vs union |
| Witness | On merge to master | Ingest then count |
| After scheduled ingest | On ingest completion | If live N did not move → Fix Process |
| B Definer | Daily | Union vs 1live.co prescription |
| Hunt FIND_AGGREGATORS | Weekly per locale + on role_gap | Roles do not change hourly |
| Atlas / Ortelius | Weekday / daily | Fleet map, not writes |
| Themis / Holmes | On PR / failed check | Event, not cron |

Timezone for cron: UTC. Locale timezone is only for `when` on cards.

## desk-ingest on schedule

`write=true`, `doors=all`, `hours=168`, test default city only as the *count* label. Pack still walks every public door.
Manual dispatch still exists for a one-door walk.

## Fix Process × schedule

Kick off step 1 when:
- The scheduled ingest did not start in its window
- The scheduled ingest failed
- The scheduled ingest succeeded and 1live.co N did not move
- M hourly sees Goal 2 miss

Do not wait for a chat to be open.
