# Ticket B plan

Success: 1live.co Today N ≥ that locale’s counted union.
Test floor: Chronicle today printed count (196 last human count).
Proof: Showing N on https://1live.co and /tonight. Show everywhere is the catalog check.

Chronicle-only HTML is not the only write. Class A (ICS, JSON-LD, Ticketmaster-style APIs already in the pack) may write at the same time. They must not share the desk-ingest lock in a way that cancels the Chronicle walk.

## How

1. PRE: 1live.co N + Chronicle printed N + each Class A door we will hit.
2. CI gate: fail if master contains `del as_of`, date/place hold strings, or Today hide-if-no-date.
3. Chronicle walk: write=true, door=austin-chronicle-eventsearch, current product SHA.
4. Class A walk: separate job/group so it cannot cancel (3).
5. Report line required: `DOOR read_n public_n LIVE_N`. Job **fails** if titled public_n < read_n.
6. POST: 1live.co N and Show everywhere N vs Chronicle 196.
7. Gap → Fix Process in the owning file. Repeat 2–6.

## Built-in locks (not markdown hope)

| # | Lock | Built as |
|---|---|---|
| 1 | Tests restore hold | Delete those tests. CI grep fails if hold strings return. |
| 2 | Docs SHA ingest | desk-ingest skips when the commit touched only docs/**. |
| 3 | Green without page | Last ingest step curls 1live.co (retry 3). Summary is Showing N. |
| 4 | Short walk | Job fails if Chronicle today read_n ≪ printed 196. |
| 5 | CAPCOG as map | Proof records Show everywhere N, not only scoped Tonight. |
| 6 | Wrapper | CI fails if a new module sets hold_reason for date/place. |
| 7 | Class D | No fetch. Job lists UNREADABLE and continues other doors. |
| 8 | Cancel good walk | Chronicle job and Class A job: different concurrency groups. Do not dispatch yaml-only. |

## Tools

Existing: 1live.co, desk-ingest.yml, ingest report, Fix Process, Witness, Publisher clock, pack ICS/JSON-LD doors.
Add: the grep job, the curl-N step, the read_n line, a second concurrency group for Class A.
No new bot. No hold wrapper.
