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

`tests/test_permalink_follow.py` — 56 tests, none of which opens a socket.

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

## 7. Evaluator round 1 — a page's own timestamp is not a show's day

`adversarial-review` (v2 panel, po seed `a54968c…`) returned REQUEST-CHANGES.
Three of four lenses APPROVE; `openai/absence-only` found one blocking defect,
and it is real. Reproduced against my own code before fixing:

```
footer "Last updated September 3, 2026" + the event's "Doors 9:00PM"
   -> 2026-09-03T21:00:00
the event's "Sat Sep 5" + footer "Box office opens 10:00AM daily"
   -> 2026-09-05T10:00:00
```

Both well-formed. Neither stated by anybody. The read had no **event-scope**
check: "the only date anywhere on the page" and "the only clock anywhere on the
page" were joined into this happening's start — and the tick runs before the
union, so `--real --write` would have published them.

Two rules close it, both **structural** rather than a list of chrome words
("updated", "posted", "box office" are English, and an enumeration of them looks
complete right up until the next one):

* **The page's own plumbing is not a statement about this happening.** Text
  inside `<nav>`/`<aside>`, or a PAGE-level `<header>`/`<footer>`, is dropped —
  HTML's own sectioning rule, and the same tag sets `desk_read` already uses to
  keep a nav link from becoming a listing. Those sets are now public, so there is
  one definition rather than two that drift.
* **A clock joins a day only from the SAME statement.** One block, however it is
  marked up inside, is one statement; two sibling blocks are two. Where the clock
  is elsewhere the DAY still stands at `date` precision — refusing the time is
  not refusing the date.

A schema.org `Event.startDate` and an ICS `DTSTART` are exempt: they say whose
start they are, and are the one carrier needing no locality check.

| page | before | after |
|---|---|---|
| footer "updated" stamp + event clock | `2026-09-03T21:00:00` | `None` |
| event day + footer box-office clock | `2026-09-05T10:00:00` | `2026-09-05` (day stands) |
| one statement, "Sat Sep 5 • 9:00PM" | `2026-09-05T21:00:00` | unchanged |
| `<time>` in the article | dated | unchanged |
| `<time>` in a nav | dated | `None` |
| footer `class="address"` (publisher's office) | read as the venue | `None` |

The same defect one field over came with it: a `<footer class="address">` holding
the publisher's office would have given every happening on that desk the desk's
own address.

Both NITs from the approving lenses are answered. `fill_holes` no longer lets a
row imply a field came from a detail page that never stated it (a row names ONE
detail page, so a field merged from a second reading's page keeps its value and
makes no provenance claim). The third — comparing scheme/port in `followable()`
— is **declined on the record**: it would refuse a desk printing `http://` links
on an `https` page, narrowing coverage for no trust gain on what is a data-trust
boundary, not a security one (we send no credentials and never fetch cross-host).

### 7a. The same class one level deeper, self-caught before pushing the fix

Probing the fix rather than trusting it found the next instance:

```
<footer><article><footer>site links</footer></article>
        <p>Last updated September 3, 2026</p></footer>
   -> segments included the stamp -> when = 2026-09-03
```

A card's own `<footer>` inside the PAGE `<footer>` decremented a furniture
counter it never raised, so the rest of the page footer stopped being plumbing.
Deciding "is this furniture?" again at the close tag cannot work — the answer
depends on where the element SAT — so both scanners now push `(tag, opened)` and
only the element that opened plumbing closes it. Pinned by
`test_plumbing_inside_plumbing_does_not_re_open_the_page`.

### 7b. What the first live run made obvious about the report

The live run reported `still_null_n` = 1568 and gave nothing to act on: the
reason each opened page stated nothing sat in prose, one sentence per page, and
the section carrying this ticket's counters was behind a 1568-row markdown
table. Two report changes followed, neither touching the rule:

* every refusal now carries a stable CODE beside its sentence
  (`clock-without-date`, `date-in-plumbing`, `clocks-ambiguous`, `no-date`,
  `clock-elsewhere`, …) and the report counts them across the run — §9.3 asks
  for exactly this, as data rather than chat;
* the write plan prints its first 25 rows and states the total beside them. The
  cap is on PRINTING only: every row is still planned and still counted.

## 8. Dry ingest — FIXTURE run

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
by the 56 hermetic tests above and by the LIVE run in §8; the dry run prints the
reason in place of the number.

`dated_n` here is what the LIST cards stated, unchanged by this PR — the same
17/16 rows Ticket B produced.

## 9. Dry ingest — LIVE run

The build sandbox cannot produce this: its egress proxy answers 403 to CONNECT
for both desks. `.github/workflows/desk-split-dryrun.yml` (manual dispatch, any
branch, no secrets, cannot write) is the one command that produces it, and this
PR adds a `follow_budget` input to it.

### 9a. What the first live runs found — about my own rules

The live table did its job twice before it was a deliverable, and both times the
finding was mine rather than the desk's.

**Run on `ab92fe0`.** 1568 rows, `mash_n` 0, and **0 dated**. The refusal codes
said `dates-ambiguous` on 40 of 40 opened pages, and the quoted sentences said
why:

```
- dates-ambiguous — .../event/back-to-the-ranch-the-lbj-bbq-returns-14329073:
    page states 31 different dates (2026-09-26, 2026-09-05, 2026-09-06, 2026-09-07)
- dates-ambiguous — .../event/prodigal-sun-14267156:
    page states 32 different dates (2026-09-04, 2026-09-06, 2026-09-05, 2026-09-07)
- clocks-ambiguous — .../event/boeing-boeing-14285657:
    page prints 3 different clocks (7:30, 10:15 pm, 4:45 pm)
```

Thirty-one is a month: every event page on this desk prints a **calendar widget**
beside the listing. Two separate defects were hiding behind that one number:

1. **Scope was being checked AFTER cardinality.** Every date on the document was
   counted first, so any page with a footer stamp — or a widget — was "ambiguous"
   before the scope rule ever got to exclude it. A rule that is right about a
   page nobody publishes was wrong about every page anybody does. Scope is now
   asked first; cardinality applies to what is left. The combine step had the
   same shape one call deeper (`page_text=html` re-admitted the excluded dates),
   and now settles against the owning statement, which is what R-030's
   `block_text` is for.
2. **Tiers were being mixed.** Split Law §2's ladder says the first tier that
   yields wins and tiers are never mixed — and that holds for fields as much as
   for identities. A schema.org `Event.startDate` states WHOSE start it is; the
   prose around it is not a competing claim to be counted against it. A page that
   declares its start and also prints a month grid now dates from the
   declaration.

Neither change loosens anything. Two `startDate`s still refuse, two dates in the
page's own content still refuse, and prose beside a calendar widget is still a
hole — because which of thirty-one days this happening is on is exactly what is
not stated, and picking one would be a coin flip published as a fact.

### 9b. The table

Run [34005255072](https://github.com/schubertsean-ui/onelive/actions/runs/34005255072)
on head `40d0084`, `--real --dry-run --max-pages 40 --follow-budget 40`. Pasted
verbatim from the job log.

| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 1568 | 40 | 1528 | 0 | 0 |
| `do512-today` | 0 | 0 | 0 | 1 | 0 |

**`mash_n` is 0.** Every one of the 1568 rows carries its own `/event/…`
address, so the field tick opened 40 different pages rather than the list page
forty times.

**Every page the budget reached was dated — 40 of 40.**

| desk | pages opened | page stated no date | page could not be read | not asked (budget) | no followable address |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 40 | 0 | 0 | 1528 | 0 |
| `do512-today` | 0 | 0 | 0 | 0 | 0 |

`still_null_n` is 1528, and every one of those is **UNASKED**, not dateless: the
founder's 40-page cap for this ticket. `dated_n` is a floor.

What the opened pages said — all three remaining refusals are about the TIME,
never the day:

| the page said | pages | of opened |
|---|---:|---:|
| `no-clock` | 27 | 67% |
| `clocks-ambiguous` | 7 | 17% |
| `clock-elsewhere` | 2 | 5% |

```
- clocks-ambiguous — .../event/boeing-boeing-14285657:
    page prints 3 different clocks (7:30, 10:15 pm, 4:45 pm)
- clocks-ambiguous — .../event/day-of-dance-14167854:
    page prints 2 different clocks (10 am, 5 pm)
- no-clock — .../event/austin-film-festival-14316417:
    page states a day and no time
```

Those are correct refusals: a page printing "10 am" and "5 pm" has not said when
this happening starts, and the DAY stands regardless.

Three sample rows, as a person would read them:

| # | listing_url | start_time | place | filled from the event page |
|---:|---|---|---|---|
| 1 | `https://calendar.austinchronicle.com/event/back-to-the-ranch-the-lbj-bbq-returns-14329073` | 2026-09-26T18:00:00-05:00 | Lyndon B. Johnson National Historical Park | when, place_text |
| 2 | `https://calendar.austinchronicle.com/event/boeing-boeing-14285657` | 2026-09-18T19:30:00-05:00 | TexARTS | when, place_text |
| 3 | `https://calendar.austinchronicle.com/event/austin-steel-guitar-fest-14286428` | 2026-10-01T10:00:00-05:00 | Austin Airport Marriott South | when, place_text |

Every one of those clocks came from the event page. The list card stated none of
them, and `filled_from_detail` says so on the row itself.

The write plan moves with them:

```
at least 1567 happening(s) planned, of which 1539 publish and 28 are HELD
(a desk stated the night and no time ... R-111). 11 carry a clock a desk
stated; 0 publish DISPUTED; 1528 publish with a true 'Date TBA' because no
desk stated a date at all.
```

1568 rows became 1567 planned because dated rows now MERGE on the founder's
night+place+title key — two cards for one happening are one row once both carry
the night. The 28 HELD are the R-111 case working: a day with no time is not
published as "Date TBA", because that would hide a date the desk gave us.

`do512-today` is unchanged and still walled at its list page (403, class D,
queued for a claim) — an UNKNOWN list, never an empty one.

## 10. Evaluator round 2 — whose statement is this?

Two blocking findings, both openai seats, both reproduced before fixing. They
are ONE class asked from two sides, and the r1 tier fix **caused** the first.

**(a) `attacker-smuggle`** — any schema.org Event on a permalink page was
treated as this happening's. `field_read()` never saw the row, and
`owned_by_this_happening()` returned true for any structured hit:

```
sidebar node: url = /event/other-99, startDate 2026-12-25T20:00, "The Other Room"
row:          "Dominic Fike" at /event/dominic-fike-1
   ->  when = 2026-12-25T20:00:00-06:00, place = The Other Room
```

**(b) `absence-only`** — after a redirect only the HOST was re-checked:

```
/event/dominic-fike-1  ->  302  ->  /whats-on   (same origin)
   ->  when = 2026-09-30T19:00:00, place = Front Desk
```

Structured markup says whose fact it is **about itself**, so "the page carries
an Event" is not "this row has a date". And an identity gate that runs before
the request and not after the response only ever guarded the request.

Both ends now bind:

* `speaks_for()` keeps only nodes that do not name a DIFFERENT address — a node
  naming this `url`/`@id`, or the page's lone node naming none at all (a
  permalink page publishing one Event about itself). Requiring a `url` outright
  would hole every desk whose markup omits one.
* `same_identity()` requires the landed URL to be the address we asked for,
  compared on host + path so a desk's own `?ref=` tracking parameter is still
  the same page.

| page | before | after |
|---|---|---|
| sidebar node naming another address | `2026-12-25T20:00` / The Other Room | `None` / `None` |
| the same node naming THIS address | dated | unchanged |
| lone node naming no address | dated | unchanged |
| bound node beside a sidebar node | the sidebar could win | the bound one speaks |
| same-origin redirect to `/whats-on` | `2026-09-30T19:00` / Front Desk | `None`, queued |
| redirect adding `?ref=cal` | dated | unchanged |

**A trap inside the fix, caught by re-running rather than trusting it:** the
first cut stopped the unbound node from WINNING its tier and left it holding the
scope EXEMPTION that tier granted — so it still dated the row. Removing a
statement from its tier is not the same as removing its waiver; both had to go.

11 tests pin this round (75 in the file). The other two lenses APPROVE'd the
same head, and `gemini/spec-vs-contract` independently verified all three
founder acceptance criteria and `mash_n = 0`.

## 11. What this ticket did NOT do

* No Tonight redesign, no catalog upsert, no `ai_extract` change, no new vendor,
  no login, no Planomato, no touching PRs #230/#231/#232.
* The LIST walk's 40-page cap is unchanged (`--max-pages`); the new
  `--follow-budget` is a separate cap on event pages.
* Nothing is written or promoted. `--write` still needs `--real` and a DSN, and
  neither this run nor that workflow passes either.
