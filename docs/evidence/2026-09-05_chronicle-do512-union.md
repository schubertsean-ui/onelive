# Evidence — one happening table across two desks (Chronicle + Do512)

**2026-09-05 · Session Contract #65 · FIXTURE run.**

What you are about to see: the two desk dumps already on master, folded into ONE
list. Until now each desk had its own table and its own count; adding a second
desk made the number bigger without telling anyone which rows were the same row.
This is the first artifact that says what 1Live holds ACROSS desks — one row per
happening, carrying every desk that printed it.

Three things to know before reading the numbers:

1. **These are fixture counts, not Austin.** Both desks' committed pages are
   synthetic shape fixtures (egress to the live desks is refused at this
   sandbox's proxy, recorded 2026-09-04). Every title, venue and date below is
   invented to exercise the walk and the key. The same command with `--real`
   walks the live desks and prints the same tables labelled LIVE.
2. **The de-dup rule is the founder's, implemented literally**: same night +
   same place-text + same title-or-performer → one row, many vias. No identity
   service, no scoring, no model. Three equalities.
3. **No row is dropped.** A row that cannot form that key (no stated night, no
   place text) stays in the table under a desk-local key, single-source. Table 4
   lists every one and why.

Re-run this yourself:

```
python tools/desk_union.py            # exactly what is pasted below
python tools/desk_union.py --real     # the live desks, same tables, labelled LIVE
```

The rest of this file is that command's own output, pasted verbatim.

---

# One happening table — Austin Chronicle + Do512 — FIXTURE walk
# One happening table — Austin Chronicle + Do512 — FIXTURE walk

Locale: `us-tx-capcog` (Capital Area Council of Governments) · nights are calendar dates in `America/Chicago`, projected from the instant each desk stated.
De-dup rule: same night + same place-text + same title-or-performer -> one row, many vias. No identity service. No invented dates.

## 1. Desks

| desk | via | pages read | pages blocked | rows | walk ended | state |
|---|---|---|---|---|---|---|
| `austin-chronicle-eventsearch` | Austin Chronicle | 3 | 0 | 17 | `no_next_link` | read to the end of its list |
| `do512-today` | Do512 | 3 | 0 | 16 | `next_control_not_a_link` | partial — the desk's list continues |

## 2. Happenings — the union, deduped

| # | unique key | via | kind | dated | title | place |
|---|---|---|---|---|---|---|
| 1 | `2026-09-11~shape hall~fixture quartet at the shape hall` | Austin Chronicle | `art` | yes | Fixture Quartet at the Shape Hall | Shape Hall |
| 2 | `2026-09-12~alley lot~taco alley pop up` | Do512 | `food` | yes | Taco Alley Pop-Up | Alley Lot |
| 3 | `2026-09-12~bright room~bright room quartet` | Do512 | `music` | yes | Bright Room Quartet | The Bright Room |
| 4 | `2026-09-12~fixture room~shape town brass` | Austin Chronicle + Do512 | `music` | yes | Shape Town Brass | The Fixture Room |
| 5 | `2026-09-12~placeholder playhouse~second sunday comedy hour` | Do512 | `comedy` | yes | Second Sunday Comedy Hour | Placeholder Playhouse |
| 6 | `2026-09-13~fixture square~example farm stand` | Austin Chronicle | `market` | yes | Example Farm Stand | Fixture Square |
| 7 | `2026-09-13~kite field~kite field fun run` | Do512 | `sport` | yes | Kite Field Fun Run | Kite Field |
| 8 | `2026-09-13~old depot~pop up print fair` | Do512 | `market` | yes | Pop-Up Print Fair | Old Depot |
| 9 | `2026-09-13~placeholder theatre~sample improv night` | Austin Chronicle | `comedy` | yes | Sample Improv Night | Placeholder Theatre |
| 10 | `2026-09-13~shape pool~family splash morning` | Do512 | `family` | yes | Family Splash Morning | Shape Pool |
| 11 | `2026-09-13~shape warehouse~warehouse district late set` | Do512 | `other` | yes | Warehouse District Late Set | Shape Warehouse |
| 12 | `2026-09-14~annex studio~watercolor basics` | Do512 | `class` | yes | Watercolor Basics | Annex Studio |
| 13 | `2026-09-14~council chamber~council budget hearing` | Do512 | `civic` | yes | Council Budget Hearing | Council Chamber |
| 14 | `2026-09-14~fixture annex~something the table does not cover` | Austin Chronicle | `other` | yes | Something The Table Does Not Cover | Fixture Annex |
| 15 | `2026-09-14~spring fed pool~sunrise swim` | Do512 | `outdoors` | yes | Sunrise Swim | Spring-Fed Pool |
| 16 | `2026-09-15~corner bookshop~poetry off the page` | Do512 | `literary` | yes | Poetry Off the Page | Corner Bookshop |
| 17 | `2026-09-15~marquee room~silent film night` | Do512 | `film` | yes | Silent Film Night | Marquee Room |
| 18 | `2026-09-16~east side blocks~gallery walk east side` | Do512 | `art` | yes | Gallery Walk: East Side | East Side blocks |
| 19 | `2026-09-16~fixture cinema~example screening a test print` | Austin Chronicle | `film` | yes | Example Screening: A Test Print | Fixture Cinema |
| 20 | `2026-09-17~fixture city hall~sample city meeting` | Austin Chronicle | `civic` | yes | Sample City Meeting | Fixture City Hall |
| 21 | `2026-09-19~fixture greenbelt~placeholder trail walk` | Austin Chronicle | `outdoors` | yes | Placeholder Trail Walk | Fixture Greenbelt |
| 22 | `2026-09-19~fixture studio~test pottery class` | Austin Chronicle | `class` | yes | Test Pottery Class | Fixture Studio |
| 23 | `2026-09-20~fixture district~example taco crawl` | Austin Chronicle | `food` | yes | Example Taco Crawl | Fixture District |
| 24 | `2026-09-24~placeholder theatre~placeholder stage play` | Austin Chronicle | `theater` | yes | Placeholder Stage Play | Placeholder Theatre |
| 25 | `2026-09-25~fixture field~sample league night` | Austin Chronicle | `sport` | yes | Sample League Night | Fixture Field |
| 26 | `2026-09-26~fixture gallery~example gallery opening` | Austin Chronicle | `art` | yes | Example Gallery Opening | Fixture Gallery |
| 27 | `do512-today#no address chapbook swap` _(desk-local)_ | Do512 | `other` | **no** | No-Address Chapbook Swap | Back room, address not printed |
| 28 | `austin-chronicle-eventsearch#no-date-stated` _(desk-local)_ | Austin Chronicle | `other` | **no** | A Listing With No Date On The Page | Fixture Annex |
| 29 | `austin-chronicle-eventsearch#placeholder-reading` _(desk-local)_ | Austin Chronicle | `literary` | **no** | A Placeholder Reading | Fixture Branch Library |
| 30 | `austin-chronicle-eventsearch#sample-kids-hour` _(desk-local)_ | Austin Chronicle | `family` | **no** | Sample Kids Hour | Fixture Branch Library |
| 31 | `austin-chronicle-eventsearch#test-open-mic` _(desk-local)_ | Austin Chronicle | `other` | **no** | Test Open Mic | The Fixture Room |
| 32 | `do512-today#riverside-story-circle` _(desk-local)_ | Do512 | `other` | **no** | Riverside Story Circle | Riverside Lawn |

33 row(s) came off the readable desk(s); 32 unique happening(s) after the de-dup; 1 carried by more than one desk. 26 carry a date a desk stated, 6 have an honest hole on the clock and can never be matched across desks.

## 3. Board

| bucket | rows | note |
|---|---|---|
| Austin Chronicle only | 16 | — |
| Do512 only | 15 | floor — this desk's list continues |
| both | 1 | matched on `night+place+title` (or `night+place+performer`) |
| **unique total** | **32** | the union, deduped (a FLOOR — at least one desk's list continues) |

## 4. Held apart — rows that can only ever be themselves

| row | why it can only ever be itself |
|---|---|
| Austin Chronicle: A Placeholder Reading | no night stated |
| Austin Chronicle: A Listing With No Date On The Page | no night stated |
| Austin Chronicle: Sample Kids Hour | no night stated |
| Austin Chronicle: Test Open Mic | no night stated |
| Do512: Riverside Story Circle | no night stated |
| Do512: No-Address Chapbook Swap | no night stated |

## 5. Near misses — same night, same place, different name

_None: no two desks put differently-named rows in the same place on the same night._

## Next doors we still miss

| door | type | via | evidence the pack states | category map |
|---|---|---|---|---|
| `austin-chronicle-arts` | local_desk | Austin Chronicle | found_unverified | `austin-chronicle` |
| `community-impact-austin` | local_desk | Community Impact | found_unverified | **none yet** |
| `culturemap-austin-events` | local_desk | CultureMap Austin | catalogued | **none yet** |
| `kutx-concert-calendar` | local_desk | KUTX | catalogued | **none yet** |
| `showlist-austin` | local_desk | Showlist Austin | found_unverified | **none yet** |
| `city-of-austin-library-events` | civic | Austin Public Library | catalogued | **none yet** |
| `city-of-bastrop-recdesk` | civic | City of Bastrop | found_unverified | **none yet** |
| `city-of-lockhart-calendar` | civic | City of Lockhart | found_unverified | **none yet** |
…and 16 more readable door(s) in this pack, unopened.
Not on this list, and not a gap to close: `ticketmaster-discovery`, `axs-austin`, `facebook-events`, `instagram-venue-posts`, `nextdoor-austin`, `allevents-austin`, `austingallery-events-index` — the pack states each as a wall, a copy farm, or a door with no read path we may use. We do not log in and we do not launder a copy farm into a listing.
**Nothing above was fetched.** These are names off the committed pack, and opening one is its own ticket.

## Limits of this table

- A night comes only from a date a desk STATED in markup. Prose ("this Saturday", "Ongoing") is carried verbatim and yields no night, so those rows never merge. No date is parsed out of prose.
- A 12:30am listing is keyed to its own calendar date, not to the evening before. Rolling late sets back a night is a rule the founder has not set, and it would move rows between nights silently.
- The performer strip removes a trailing "at <this row's own venue>" and a support-act tail ("w/", "feat."). It runs only after night AND place already match, and every merge it makes is listed above.
- **FIXTURE run.** Every count above is a count of committed shape fixtures — invented titles, venues and dates that exist to prove the walk, the key and the board. It is not a measurement of the Austin Chronicle, of Do512, or of any live desk.
- At least one desk's list continues past where its walk stopped (see table 1). Every count here is therefore a FLOOR.

This tool wrote nothing: no candidate, no promotion, no user-visible row. Reading two desks does not change the catalog — wiring these rows into the pipeline is a separate, named step.
