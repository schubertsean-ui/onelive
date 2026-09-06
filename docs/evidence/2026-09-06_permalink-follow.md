# Ticket C — follow the permalink for fields: what changed, and how it was proven

Date: 2026-09-06 · Branch `claude/event-page-date-place-alilfe` · Law:
`ONE-LIVE-ENTITY-SPLIT-LAW.md` §4 (the field tick) and §9.6 (counters) ·
No `--write`, no merge.

Every number below was printed by a command named beside it. Nothing here is
retyped from memory.

## 1. What the ticket asked for, and what it is

Ticket B split the list: 1565 `/event/…` rows, `mash_n` 0 (founder, run
34000699427). Those rows carry the address the desk printed and, for most of
them, a hole where the clock goes — a list CARD prints a title and a link.

This ticket opens that address and reads the date and place from THAT page.
§4's spine already named it: "fetch best door -> fields (when, place, actors)
same-page only".

New module `worker/locale/desk_follow.py` (pure; `fetch` injected, `as_of`
a parameter — no network, no DB, no clock inside it):

| | |
|---|---|
| `field_read(html, url=, as_of=)` | what ONE page states about itself |
| `followable(row, patterns=)` | may this row's address be opened at all |
| `apply_read(row, read)` | fill HOLES, never overwrite |
| `follow(rows, fetch, budget=40, as_of=)` | the bounded tick |

## 2. The date rule is not new, and deliberately so

`worker/same_page_dates.py` (R-030) already holds exactly the rule the founder
restated: machine carriers first (JSON-LD `startDate`, `<time datetime>`, ICS
`DTSTART`), then visible prose, and **a year missing from the page is supplied
only when the page's own weekday pins exactly one** inside a window anchored to
the fetch day. No "today", no "this year", no next-occurrence guess.

That file is inside the ARMED CRON's computed runtime closure, so it is
IMPORTED and not edited. The closure is unchanged by this PR:

```
$ python -c "from tools import arming_runtime as a; fs=sorted(a.runtime_files()); \
  print(len(fs), any('desk_follow' in f for f in fs))"
42 False
```

## 3. The founder's three tests

`tests/test_permalink_follow.py` — 47 tests, none of which opens a socket.

| ticket case | test | result |
|---|---|---|
| (a) list card + event page states day and time -> dated | `test_a_list_card_with_no_date_is_dated_by_its_own_event_page` | row is `2026-09-05T21:00:00`, `filled_from_detail=('when','place_text')` |
| (b) event page clock-only -> still NULL | `test_an_event_page_stating_a_clock_and_no_date_leaves_the_row_null` | `when is None`; the place still fills |
| (c) a list-page date must not attach to the event page's clock | `test_a_date_from_the_list_page_never_attaches_to_the_event_pages_clock` | row keeps `2026-09-06` at `date` precision; NEVER `2026-09-06T21:00` |

Case (c) is the one that would look right in every table we print. The list card
states the day, the event page states only "9:00PM", and joining them across
pages yields an instant NEITHER page published. The test asserts the row's
precision is not upgraded, that `when` is not in `filled_from_detail`, and that
the event page's own read carries `when=None`.

## 4. A finding in the founder's own example string

The ticket's example is `"Sat Sep 6 • 9:00PM"`. Run literally, that page dates
NOTHING, and the rule is right to refuse:

```
$ python -c "from datetime import date; print(date(2026,9,6).strftime('%A'))"
Sunday
```

Sep 6 2026 is a **Sunday**. A page printing "Sat Sep 6" has contradicted itself
about which day it means, and R-030 treats the weekday as a checksum: it pins a
year only where exactly one year in the window carries that month/day on that
weekday. The alternative — publishing 2026-09-06 for a page that said Saturday —
is a wrong day on a public row.

Both behaviours are pinned, so neither can drift:

* `test_a_weekday_that_contradicts_the_day_dates_nothing` — the founder's string
  verbatim, asserting the hole and the reason.
* `test_a_list_card_with_no_date_is_dated_by_its_own_event_page` — the same page
  with a weekday that matches (`Sat Sep 5`), asserting the date.
* `test_the_same_page_with_a_year_printed_dates_without_any_pinning` —
  "September 6, 2026 • 9:00PM" dates with no weekday arithmetic at all.

A real desk page states a year, or a `<time datetime>`, or a weekday that
matches its own date. This only bites a page that is wrong about itself.

## 5. Refusals that can fire (each with a test)

| what the page did | what we do |
|---|---|
| states two different dates | NULL + "which one this happening is on is not stated" |
| prints two different clocks | keeps the DAY, holes the time |
| publishes two schema.org events naming different places | no place |
| labels two different places | no place |
| answers 401/402/403/407/429 | hole, queued for a claim, **one knock**, row kept |
| answers a proxy 403 with no HTTP status | still counted as a wall |
| answers 404/5xx | triage, not "this happening has no date" |
| redirects off-origin | not read — a redirect is a different door |

Cardinality is asserted as the three-way split it actually is
(`test_zero_one_and_many_dates_are_three_different_outcomes`), and the wall rule
is parametrised over all five statuses.

## 6. Two defects found by my own tests, before any review

1. **A printed year read as a time of day.** `_HAS_CLOCK_RE` was
   `\d:[0-5]\d|[T ]\d{2}[0-5]\d`, and the space-arm matched the space before
   "2026" — so "September 6, 2026" was treated as a carrier stating the whole
   instant and came back as a confident `2026-09-06T00:00:00` **midnight**,
   with the page's own printed 9:00PM never consulted. Anchored to `T`.
2. **A shadowed loop variable.** The new report block reused `one`, the name
   `main()` holds the union in, so `bounded()` was handed a `DeskWalk` and the
   fixture dry run died on `AttributeError: 'DeskWalk' object has no attribute
   'all_readable'`. Caught by the wiring test, not by reading.

## 7. Dry ingest — FIXTURE run

`$ python tools/desk_ingest.py --dry-run`

| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 17 | 13 | 4 | 0 | 0 |
| `do512-today` | 16 | 14 | 2 | 0 | 0 |

| desk | pages opened | page stated no date | page could not be read | not asked (budget) | no followable address |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 0 | 0 | 0 | 0 | 4 |
| `do512-today` | 0 | 0 | 0 | 0 | 2 |

**The fixture run opens ZERO event pages, and that is honest rather than
broken.** The committed fixtures are served from a test host, and no row in
`sources/identity_patterns.json` covers it — so no fixture row's address is one
a committed pattern calls a single happening. Committing a test host to the
production pattern table to make this column non-zero would put a fixture inside
the data that decides what a live page's links mean. The tick is proven instead
by the 47 hermetic tests above and by the LIVE run in §8; the dry run prints the
reason in place of the number.

`dated_n` here is what the LIST cards stated, unchanged by this PR — the same
17/16 rows Ticket B produced.

## 8. Dry ingest — LIVE run

The build sandbox cannot produce this: its egress proxy answers 403 to CONNECT
for both desks. `.github/workflows/desk-split-dryrun.yml` (manual dispatch, any
branch, no secrets, cannot write) is the one command that produces it, and this
PR adds a `follow_budget` input to it.

<!-- LIVE TABLE: pasted verbatim from the dispatched run; see the PR body -->

## 9. What this ticket did NOT do

* No Tonight redesign, no catalog upsert, no `ai_extract` change, no new vendor,
  no login, no Planomato, no touching PRs #230/#231/#232.
* The LIST walk's 40-page cap is unchanged (`--max-pages`); the new
  `--follow-budget` is a separate cap on event pages.
* Nothing is written or promoted. `--write` still needs `--real` and a DSN, and
  neither this run nor that workflow passes either.
