# Platform Success (for the Monitor)

Failure-type agnostic process is in docs/ONE-LIVE-FIX-LOOP.md.
This file is what Success looks like for each aspect of 1Live.
The Monitor (M) probes these. A miss kicks step 1 of the Fix Loop.
Universal: any locale. Austin is the test pack.

| Aspect | Success | Probe | Fail example |
|---|---|---|---|
| Catalog existence | A trusted readable door that printed a title has a catalog row | Ingest report rows vs door list count | Door listed 196, catalog held them |
| Live publish | That locale’s counted aggregator union is on https://1live.co | Live Showing N vs union N | 16 vs 196 |
| When | Start date stored; start time only if printed; no invented clock or duration | Sample cards vs source; no T17:00 on date-only | Date-only stamped 5 PM |
| Place | Printed place is stored; street only if a desk printed it | Card place vs door | Invented address |
| Kind | Door word mapped to 1Live kind + Other residual | Kind on card is a 1Live term | Chronicle `music` prints as a foreign id |
| Card | Slots filled from desks; holes allowed; nothing invented | Card vs door | Missing title with no “looking for more” note |
| Dedup | Same title + when + place is one happening | mash_n = 0 | Two cards for one show |
| View | Today / Tonight / Evening filter the catalog; they do not delete | All upcoming still holds undated/out-of-day rows | Today hide deleted the row |
| Ingest | Job starts; imports resolve; no 14-minute crash on a name | desk-ingest conclusion + smoke-import | complete_year missing |
| Module integrity | Real modules on master, not stubs | desk_read.py and feed.ts size / not `SEE_FILE` | SEE_FILE |
| Deploy | Live is running current master | Vercel SHA vs master tip | Old bundle after a view fix |
| Locale | Device or search picks locale; TZ is that pack | Page locale + when.ts tz arg | Chicago hardcoded as the product |
| Process | Fix Loop 15 steps + library search used on every miss | Library entry exists for the miss | Patch with no step 3 |

Ticket bars live in ticket files (docs/TICKET_B.md). They do not rewrite this table.
