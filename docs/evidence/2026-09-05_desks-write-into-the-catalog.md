# The desks write into the catalog — 2026-09-05

**What this is.** `worker/locale/desk_walk.py` has been reading the two local
desks' public lists for several sessions, and `worker/locale/desk_union.py` has
been folding them into one table on the founder's de-dup rule. Both stopped at a
printed table. This session adds the last hop — candidate, evidence, promote —
so what the desks printed becomes what the site serves.

**The headline, stated plainly: nothing was written to the live catalog from
this build sandbox, because this sandbox cannot read the desks.** Section 2 is
that refusal, in the tool's own words. Section 4 is the one command that makes
the write happen on a machine that can fetch.

Every block below is pasted from the tool's stdout. No number in this document
was typed by hand.

---

## 1. The write plan, from the committed fixtures

`python tools/desk_ingest.py --dry-run`

These are FIXTURE pages — "Fixture Quartet at the Shape Hall" is a test page,
not a show. They prove the plan, never the catalog: the write seam
(`desk_publish.refuse_fixture_write`) refuses a fixture union at the database,
so none of these titles can reach production even if someone passes `--write`.

```
# Desk ingest — Austin Chronicle Events + Do512 — FIXTURE walk

## 1. Desks

| desk | label written on the row | class the gate reads | pages read | pages blocked | rows | walk ended |
|---|---|---|---:|---:|---:|---|
| `austin-chronicle-eventsearch` | Austin Chronicle Events | `local_media` | 3 | 0 | 17 | `no_next_link` |
| `do512-today` | Do512 | `local_media` | 3 | 0 | 16 | `next_control_not_a_link` |

## 2. The write plan

| # | key | desks | title | place | starts | clock |
|---:|---|---|---|---|---|---|
| 1 | `2026-09-11~shape hall~fixture quartet at the shape hall` | Austin Chronicle | Fixture Quartet at the Shape Hall | Shape Hall | 2026-09-12T01:00:00Z | stated |
| 2 | `2026-09-12~fixture room~shape town brass` | Austin Chronicle + Do512 | Shape Town Brass | The Fixture Room | 2026-09-12T21:30:00-05:00 | stated |
| 3 | `url:https://desk.example/Events/placeholder-reading` | Austin Chronicle | A Placeholder Reading | Fixture Branch Library | — | no desk stated a date for this row |
| 4 | `2026-09-13~fixture square~example farm stand` | Austin Chronicle | Example Farm Stand | Fixture Square | — | the desk stated a night, not a time |
| 5 | `2026-09-13~placeholder theatre~sample improv night` | Austin Chronicle | Sample Improv Night | Placeholder Theatre | 2026-09-13T19:00:00-05:00 | stated |
| 6 | `2026-09-14~fixture annex~something the table does not cover` | Austin Chronicle | Something The Table Does Not Cover | Fixture Annex | 2026-09-14T18:00:00-05:00 | stated |
| 7 | `url:https://desk.example/Events/no-date-stated` | Austin Chronicle | A Listing With No Date On The Page | Fixture Annex | — | no desk stated a date for this row |
| 8 | `2026-09-16~fixture cinema~example screening a test print` | Austin Chronicle | Example Screening: A Test Print | Fixture Cinema | 2026-09-16T19:30:00-05:00 | stated |
| 9 | `2026-09-17~fixture city hall~sample city meeting` | Austin Chronicle | Sample City Meeting | Fixture City Hall | 2026-09-17T09:00:00-05:00 | stated |
| 10 | `2026-09-19~fixture greenbelt~placeholder trail walk` | Austin Chronicle | Placeholder Trail Walk | Fixture Greenbelt | 2026-09-19T08:00:00-05:00 | stated |
| 11 | `2026-09-19~fixture studio~test pottery class` | Austin Chronicle | Test Pottery Class | Fixture Studio | 2026-09-19T13:00:00-05:00 | stated |
| 12 | `url:https://desk.example/Events/sample-kids-hour` | Austin Chronicle | Sample Kids Hour | Fixture Branch Library | — | no desk stated a date for this row |
| 13 | `2026-09-20~fixture district~example taco crawl` | Austin Chronicle | Example Taco Crawl | Fixture District | 2026-09-20T11:00:00-05:00 | stated |
| 14 | `2026-09-24~placeholder theatre~placeholder stage play` | Austin Chronicle | Placeholder Stage Play | Placeholder Theatre | 2026-09-24T20:00:00-05:00 | stated |
| 15 | `2026-09-25~fixture field~sample league night` | Austin Chronicle | Sample League Night | Fixture Field | 2026-09-25T18:30:00-05:00 | stated |
| 16 | `2026-09-26~fixture gallery~example gallery opening` | Austin Chronicle | Example Gallery Opening | Fixture Gallery | 2026-09-26T18:00:00-05:00 | stated |
| 17 | `url:https://desk.example/Events/test-open-mic` | Austin Chronicle | Test Open Mic | The Fixture Room | — | no desk stated a date for this row |
| 18 | `2026-09-12~bright room~bright room quartet` | Do512 | Bright Room Quartet | The Bright Room | 2026-09-13T01:00:00Z | stated |
| 19 | `2026-09-12~placeholder playhouse~second sunday comedy hour` | Do512 | Second Sunday Comedy Hour | Placeholder Playhouse | 2026-09-12T19:00:00-05:00 | stated |
| 20 | `2026-09-12~alley lot~taco alley pop up` | Do512 | Taco Alley Pop-Up | Alley Lot | 2026-09-12T18:00:00-05:00 | stated |
| 21 | `2026-09-13~shape warehouse~warehouse district late set` | Do512 | Warehouse District Late Set | Shape Warehouse | 2026-09-13T00:30:00-05:00 | stated |
| 22 | `url:https://desk.example/events/2026/9/19/riverside-story-circle` | Do512 | Riverside Story Circle | Riverside Lawn | — | no desk stated a date for this row |
| 23 | `2026-09-13~kite field~kite field fun run` | Do512 | Kite Field Fun Run | Kite Field | 2026-09-13T08:00:00-05:00 | stated |
| 24 | `2026-09-13~old depot~pop up print fair` | Do512 | Pop-Up Print Fair | Old Depot | 2026-09-13T10:00:00-05:00 | stated |
| 25 | `2026-09-13~shape pool~family splash morning` | Do512 | Family Splash Morning | Shape Pool | 2026-09-13T09:30:00-05:00 | stated |
| 26 | `2026-09-14~council chamber~council budget hearing` | Do512 | Council Budget Hearing | Council Chamber | 2026-09-14T09:00:00-05:00 | stated |
| 27 | `desk:Do512~back room address not printed~no address chapbook swap` | Do512 | No-Address Chapbook Swap | Back room, address not printed | — | no desk stated a date for this row |
| 28 | `2026-09-14~spring fed pool~sunrise swim` | Do512 | Sunrise Swim | Spring-Fed Pool | 2026-09-14T06:30:00-05:00 | stated |
| 29 | `2026-09-14~annex studio~watercolor basics` | Do512 | Watercolor Basics | Annex Studio | 2026-09-14T18:30:00-05:00 | stated |
| 30 | `2026-09-15~marquee room~silent film night` | Do512 | Silent Film Night | Marquee Room | 2026-09-15T20:00:00-05:00 | stated |
| 31 | `2026-09-15~corner bookshop~poetry off the page` | Do512 | Poetry Off the Page | Corner Bookshop | 2026-09-15T19:00:00-05:00 | stated |
| 32 | `2026-09-16~east side blocks~gallery walk east side` | Do512 | Gallery Walk: East Side | East Side blocks | 2026-09-16T18:00:00-05:00 | stated |

at least 32 happening(s) planned: 25 carry a clock a desk stated, 7 publish with an honest hole on the clock. 31 come from ONE desk and are written anyway (founder: do not require a second desk to publish); 1 carries two.

## 3. Nothing was written

This was a dry run over COMMITTED FIXTURES. Re-run with `--real --write` on a machine that can reach the desks and holds `ONELIVE_DB_DSN`.
```

Read the two things the founder asked for in that table:

* **Single-desk rows are written.** 31 of the 32 rows come from ONE desk and
  every one of them is planned for publication. Nothing waits for a second desk,
  and nothing is dropped for being alone.
* **A row on both desks is ONE row.** `2026-09-12~fixture room~shape town brass`
  carries two vias and becomes one candidate with two evidence rows — a second
  desk widens the catalog instead of doubling it.

## 2. The live desks, from this sandbox: UNREADABLE

`python tools/desk_ingest.py --real --dry-run --max-pages 1`

```
# Desk ingest — Austin Chronicle Events + Do512 — LIVE walk

## 1. Desks

| desk | label written on the row | class the gate reads | pages read | pages blocked | rows | walk ended |
|---|---|---|---:|---:|---:|---|
| `austin-chronicle-eventsearch` | Austin Chronicle Events | `local_media` | 0 | 1 | 0 | `fetch_error` |
| `do512-today` | Do512 | `local_media` | 0 | 1 | 0 | `fetch_error` |

**UNREADABLE**: `austin-chronicle-eventsearch` opened no page (page 1: fetch failed: ProxyError: HTTPSConnectionPool(host='calendar.austinchronicle.com', port=443): Max retries exceeded with url: /austin/EventSearch?sortType=date&v=g (Caused by ProxyError('Unable to connect to proxy',); `do512-today` opened no page (page 1: fetch failed: ProxyError: HTTPSConnectionPool(host='do512.com', port=443): Max retries exceeded with url: /events/today (Caused by ProxyError('Unable to connect to proxy', OSError('Tunnel connection failed: 403 For) — an unread desk has an UNKNOWN list, never an empty one. Nothing is written for it and nothing is deleted because of it.

## 2. The write plan

| # | key | desks | title | place | starts | clock |
|---:|---|---|---|---|---|---|

at least 0 happening(s) planned: 0 carry a clock a desk stated, 0 publish with an honest hole on the clock. 0 come from ONE desk and are written anyway (founder: do not require a second desk to publish); 0 carry two.

## 3. Nothing was written

This was a dry run. Re-run with `--real --write` on a machine that can reach the desks and holds `ONELIVE_DB_DSN`.
```

Raw probe, same answer, outside the tool:

```
$ curl -sS -L --max-time 45 https://www.austinchronicle.com/events/
curl: (56) CONNECT tunnel failed, response 403
$ curl -sS -L --max-time 45 https://do512.com/events/today
curl: (56) CONNECT tunnel failed, response 403
```

The 403 comes from the build sandbox's egress proxy — `Tunnel connection
failed: 403` is the CONNECT, before either desk is reached. It is not a
Cloudflare challenge, not a paywall, and not evidence about either desk. So:
**UNREADABLE, and nothing is written.** A blocked desk has an unknown list,
never an empty one; the tool prints zero rows for it and deletes nothing.

## 3. Why a single desk publishes, with no gate change

Both desks are already in the committed source catalog as `local_media`
(`sources/master_sources_catalog_120.json`), and `worker/gating.py` has treated
that class as an anchor — promote on ONE source — since the founder's
2026-08-05 ruling on newspapers and periodicals. So "do not require a second
desk to publish" needed no new rule and no relaxed threshold; it needed the
walk to reach the publish seam at all.

`tests/test_desk_publish.py::test_both_desks_carry_a_class_the_gate_promotes_on_one_source`
asserts it against the live gate, so a future catalog edit that moved either
desk out of the anchor class fails loudly instead of silently stranding rows.

The label the founder asked for is the registry's own name — `Austin Chronicle
Events`, `Do512` — read from that same catalog row and matched by domain, never
typed into the code. A door with no catalog row REFUSES to write rather than
publishing an unlabelled listing.

## 4. The one command, on a machine that can fetch

Anywhere with open egress and the production DSN:

```
export ONELIVE_DB_DSN='<the Supabase pooler URI>'
pip install -r worker/requirements.txt
python tools/desk_ingest.py --real --write --city Austin --hours 168
```

It prints the before/after table for `GET /events` and `GET /tonight` against
the same database the API reads, using `api/public.py`'s own predicates.

Or, with no laptop at all: **Actions → `desk-ingest` → Run workflow**, tick
`write`. Same tool, same output, on a runner with egress and the DSN already in
secrets. The job is manual-dispatch only, `write` defaults to false (a live dry
run), and it is master-only — so it can run once this branch is merged.

## 5. What is still true after the write

* Re-running is safe. Every candidate carries the founder's de-dup key at
  `extracted._desk.key`; a key already in the store is skipped, so a second run
  adds what is new rather than a second copy of what is not.
* Only a clock a desk STATED becomes a start time. A row dated to the day
  publishes with a NULL start (the feed renders that as "Date TBA" and never
  hides it); two desks stating different times publish with the same hole and
  both claims recorded.
* Nothing is invented to fill a column: no artists derived from titles, no city
  asserted that no desk stated, no listing page relabelled as a ticket link.

## 6. The write path, proven on a real PostgreSQL

The only step this sandbox cannot perform is READING the desks. Everything
after the walk is runnable here, so it was run: a disposable PostgreSQL 16 with
this repo's own committed migrations applied, the two desks registered in
`source` exactly as the catalog spells them, and the real
`create_candidate` → `add_evidence` → `promote_candidate` path — the same
functions the dispatch job calls.

The rows below stand in for the desks' rows (they could not be fetched); the
machinery is not a stand-in for anything. Everything below is the tool's own
stdout.

### Run 1 — an empty catalog, then the two desks

| outcome | rows | what it means |
|---|---:|---|
| promoted | 7 | written and published — visible on `/events`, and on `/tonight` when the clock falls in the window |
| held | 0 | written as a candidate, not published — the gate or the duplicate guard said so (reason below) |
| skipped | 0 | this happening was already in the store under the same key — a re-run, not a loss |
| failed | 0 | not written — the reason is printed, never swallowed |

| surface | before | after | delta |
|---|---:|---:|---:|
| `GET /events` (all scheduled) | 0 | 7 | +7 |
| `GET /tonight?city=Austin` (default 12h window) | 0 | 3 | +3 |
| `GET /tonight?city=Austin&hours=168` (this week) | 0 | 6 | +6 |

### Run 2 — the identical desks again, one minute later

| outcome | rows | what it means |
|---|---:|---|
| promoted | 0 | written and published — visible on `/events`, and on `/tonight` when the clock falls in the window |
| held | 0 | written as a candidate, not published — the gate or the duplicate guard said so (reason below) |
| skipped | 7 | this happening was already in the store under the same key — a re-run, not a loss |
| failed | 0 | not written — the reason is printed, never swallowed |

| surface | before | after | delta |
|---|---:|---:|---:|
| `GET /events` (all scheduled) | 7 | 7 | +0 |
| `GET /tonight?city=Austin` (default 12h window) | 3 | 3 | +0 |
| `GET /tonight?city=Austin&hours=168` (this week) | 6 | 6 | +0 |

### The catalog after both runs

| listing | labelled | starts (UTC) |
|---|---|---|
| Quartet at the Long Room | Austin Chronicle Events | 2026-09-05 08:19 |
| Brass Union | Austin Chronicle Events | 2026-09-05 09:19 |
| Late Set: Riverside | Do512 | 2026-09-05 14:19 |
| Reading: New Voices | Austin Chronicle Events | 2026-09-07 05:19 |
| Sunrise Swim | Do512 | 2026-09-08 05:19 |
| Print Fair | Do512 | 2026-09-10 05:19 |
| Open Mic | Austin Chronicle Events | (Date TBA) |

Read four things in that output:

* **Eight desk rows became seven listings.** `Brass Union` was printed by both
  desks at the same place and time; it is one listing carrying both.
* **Every listing is labelled** with the desk that printed it — the registry's
  own name, on the public row.
* **The date-TBA row published** and is correctly OUTSIDE the `/tonight`
  windows: it never claimed to be in one, and it is not hidden either — it sits
  in `/events` and, on the site, under All.
* **The second run added nothing.** Seven skipped, zero promoted, every count
  flat. A nightly run adds what is new instead of a second copy of what is not.

The same path is pinned in CI by `tests/integration/test_desk_ingest_pg.py`,
which runs on every PR against a real PostgreSQL service container
(`.github/workflows/db-integration.yml`) — so this is a re-runnable check, not
a one-off transcript.

**What this is NOT.** It is not the live catalog, and it is not a claim about
what onelive-alpha.vercel.app shows today. The production before/after table is
produced by the run in section 4, on a machine that can reach the desks.
