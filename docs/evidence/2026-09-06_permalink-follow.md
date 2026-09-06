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

`tests/test_permalink_follow.py`, none of which opens a socket. The count is
whatever this prints, and is not restated anywhere else in this document:

```
$ python -m pytest tests/test_permalink_follow.py -q | tail -1
93 passed in 0.40s
```

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
| carries a structured date on a node that speaks for a DIFFERENT happening | that date is not read (`structured-hit-not-bound`) |
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
by the hermetic tests in §3 and by the LIVE run in §8; the dry run prints the
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

**The table on the SHIPPED code** — run
[34007753540](https://github.com/schubertsean-ui/onelive/actions/runs/34007753540)
on head `9e3029a`, `--real --dry-run --max-pages 3 --follow-budget 40`. Pasted
from that job log:

| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 120 | 39 | 81 | 0 | 0 |
| `do512-today` | 0 | 0 | 0 | 1 | 0 |

`mash_n` is **0**, which is the precondition the whole tick rests on: a mashed
row's address IS the list page, so following it would have written one page's
date onto every happening on the desk.

Three sample rows, pasted from the same log:

| # | listing_url | start_time | place |
|---:|---|---|---|
| 1 | `.../event/back-to-the-ranch-the-lbj-bbq-returns-14329073` | 2026-09-26T18:00:00-05:00 | Lyndon B. Johnson National Historical Park |
| 2 | `.../event/boeing-boeing-14285657` | 2026-09-18T19:30:00-05:00 | TexARTS |
| 3 | `.../event/austin-steel-guitar-fest-14286428` | 2026-10-01T10:00:00-05:00 | Austin Airport Marriott South |

All three are `filled_from_detail = (when, place_text)` — every one of those six
fields is a hole the list card left and the event page filled. Of the 40 pages
opened, 39 were dated and 1 stated no date; the other 80 followable rows were
NOT opened because the founder's 40-page budget was spent, so `dated_n` is a
FLOOR and `still_null_n` a CEILING. See §12 for why this table's counts are
directly comparable to the earlier one only on `dated_n`, and for a defect the
run's own diagnostics revealed.

**The earlier table, kept** — run
[34006786824](https://github.com/schubertsean-ui/onelive/actions/runs/34006786824)
on head `7925f00`, `--real --dry-run --max-pages 40 --follow-budget 40`. Every
number below is pasted from that job log; the one derivation is marked.

| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 1568 | 39 | 1529 | 0 | 0 |
| `do512-today` | 0 | 0 | 0 | 1 | 0 |

`dated_n`/`still_null_n` for the first row are derived from the decomposition
immediately below (1568 rows, 1 page stated no date, 1528 not asked); the
do512 row and both `mash_n`/`403_n` columns are pasted. **`mash_n` is 0**, which
is what makes following safe at all: a mashed row would have sent every fetch at
the list page and written one page's date onto the whole desk.

```
| desk                           | pages opened | page stated no date | page could not be read | not asked (budget) | no followable address |
| `austin-chronicle-eventsearch` |           40 |                   1 |                      0 |               1528 |                     0 |
| `do512-today`                  |            0 |                   0 |                      0 |                  0 |                     0 |
```

**39 of the 40 pages the budget reached were dated.** The 1528 remaining are
UNASKED — the founder's cap for this ticket, not a fact about the desk — so
`dated_n` is a floor and `still_null_n` a ceiling.

What the opened pages said. Every remaining refusal is about the TIME, except
three pages where a structured node spoke for somebody else or the only date sat
in the page's plumbing:

```
| the page said           | pages | of opened |
| `no-clock`              |    26 |       65% |
| `clocks-ambiguous`      |     7 |       17% |
| `clock-elsewhere`       |     2 |        5% |
| `structured-not-bound`  |     2 |        5% |
| `date-in-plumbing`      |     1 |        2% |

- clocks-ambiguous — .../event/day-of-dance-14167854:
    page prints 2 different clocks (10 am, 5 pm)
- clocks-ambiguous — .../event/story-sessions-14275760:
    page prints 2 different clocks (8 pm, 8:00 pm)
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

Every clock and every venue there came from the event page — the list cards
stated none of them, and `filled_from_detail` says so on the row itself.

The write plan moves with them:

```
at least 1567 happening(s) planned, of which 1540 publish and 27 are HELD
(a desk stated the night and no time ... R-111). 11 carry a clock a desk
stated; 0 publish DISPUTED; 1529 publish with a true 'Date TBA'.
```

1568 rows became 1567 planned because dated rows now MERGE on the founder's
night+place+title key. The 27 HELD are R-111 working: a day with no time is not
published as "Date TBA", because that would hide a date the desk gave us.

`do512-today` is unchanged and still walled at its list page (403, class D,
queued for a claim) — an UNKNOWN list, never an empty one.

### 9c. Known, and NOT fixed here

Two rows of the plan still carry a venue as the page's whole labelled block
("Venue Details Canopy 916 Springdale, Austin East canopyaustin.com 1 event").
That is what the page labels as its venue, so it is honest, but it is not a
usable Place — and it becomes part of the de-dup key. It shows up only where the
structured node does not speak; where one does, its `location.name` is clean
("TexARTS"). Naming it here rather than fixing it: place-text normalisation is
Ticket C's neighbour, not its scope.

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

Tests were added for each case in the table above; the file's total is derived
in §3, not restated here. The other two lenses APPROVE'd the
same head, and `gemini/spec-vs-contract` independently verified all three
founder acceptance criteria and `mash_n = 0`.

## 11. Evaluator round 3 — the page is not the grain; the node is

Round 2 asked the right question at the wrong grain. `speaks_for()` correctly
worked out WHICH nodes speak for this row, and then `event_scoped()` threw that
answer away:

```python
if hit.kind == "jsonld":
    return bool(mine)          # ANY bound node ⇒ EVERY jsonld date is scoped
```

So a permalink whose own node carries no `startDate`, sitting beside a sidebar
node for a different happening, published the sidebar's date. Reproduced on the
pre-fix head, and note what is missing from the second half of the line:

```
REPRO r3: 2026-12-25T20:00:00-06:00 | carrier: jsonld | codes: ()
```

No refusal code. The row did not merely take a wrong date — it reported nothing
wrong at all, which is the part that would have reached `--write` unnoticed.

The check is now per hit. Each bound node's `startDate` becomes an instant key;
a JSON-LD date carries scope only if its own instant is one of them, and an
unmatched hit is refused as `structured-hit-not-bound` so the hole says why.

| page | before | after |
|---|---|---|
| bound node has NO date, sidebar has one | `2026-12-25T20:00:00-06:00`, no code | `None` + `structured-hit-not-bound` |
| bound node HAS a date, sidebar has one | could take either | `2026-09-06T21:00:00-05:00` / The Hall |
| the live shape (one bound node) | dated | unchanged — `2026-09-26T18:00:00-05:00` / LBJ Park |
| bound node named by a RELATIVE url | bound nothing | `2026-09-26T18:00:00-05:00` |

**Two traps inside the fix, both caught by re-running rather than by reading
the patch.** The instant keys were first compared naive-against-aware, which
would have holed every desk that omits an offset — naive is now read as UTC,
the same reading `_to_utc_z` already gives the node side (`Z vs offset: True`,
`naive vs Z: True`, `different: False`). And `speaks_for()` compared a relative
`url` (`/event/1846201`) against an absolute address and bound nothing; relative
addresses are resolved against the page before the comparison.

This is the same red class as round 2 — `whose-statement-is-this` — one level
finer, so the class now carries the triggers that would have caught it: a
page-level `bool()` or `any()` standing in for a per-hit question. Each of the
four cases above is a test; the file total is derived in §3.

## 12. Two things the r3 live run found, both in the report rather than the data

Run 34007753540 walked the desk on the shipped r3 code. `dated_n` was unchanged
at 39, which is the right answer — every Chronicle permalink carries exactly one
bound node, so per-hit binding has nothing to reject there. But reading the
run's own output found two defects, neither of them in a published field.

**(a) A refusal code was recorded for a hole that did not exist.** The last line
of the clock section recorded the page-level `clocks-ambiguous` scan whenever
the page's prose disagreed with itself — including when a structured carrier had
already stated the whole instant. `/event/boeing-boeing-14285657` is the shape:
JSON-LD says `2026-09-18T19:30:00-05:00`, the prose prints "7:30, 10:15 pm, 4:45
pm", and the row is complete. The run reported 7 of 40 opened pages (17%)
needing a clock repair when their rows had no clock hole at all.

Nothing wrong was ever published — `when` is untouched by this — but the
diagnostic is what the NEXT ticket is chosen from (Law §9.3: the repair with the
largest count). A count that overstates the work sends the next ticket at
nothing. The code now records only when the row actually lacks a time, pinned
from both sides: a complete instant records no complaint, and the same
contradictory prose on a page whose date carries no time still does.

**(b) A test count in the record was typed, not derived.** The r3 commit message
and this document's §11 both said "86 tests"; the real count at that commit was
82. The commit message is history and stays as written; every count in this
document is now derived by the command printed in §3 and stated exactly once.
This is `retyped-evidence`, self-caught, and the reason the rule exists is
visible in how quietly it happened: 82 and 86 both look like a green suite.

Comparability note, so the two published tables are not read as a change they
are not: run 34006786824 (head `7925f00`) walked the list at the workflow's
default 40 pages and found 1568 rows; run 34007753540 walked 3 and found 120.
`dated_n` is 39 in both because it is capped by the 40-page FOLLOW budget, not
by the list walk. `still_null_n` differs for the same reason — 1529 against 81 —
and neither number moved because of the r3 code.

## 13. Evaluator round 4 — absence is not proof, and a script is not a sentence

Three seats APPROVE, one REQUEST-CHANGES (openai/attacker-smuggle) with two
blocking findings. Both reproduced on the pre-fix head before anything changed.

**(a) `speaks_for`'s weak arm trusted an absence.** Round 2 refused a lone node
that names ANOTHER HAPPENING, asking the committed identity table. The evaluator's
point: absence from that table is not proof the node is ours. A stale or
promotional Event at an address the table cannot classify — a vanity URL, a
ticket link, a partner site — passes the test while being about something else,
and on a page whose own listing carries no structured markup it is the lone node.

```
PRE-FIX  f1 unpatterned lone node  when=2026-12-25T20:00:00-06:00  place=The Other Room  codes=()
POST-FIX f1 unpatterned lone node  when=None                      place=None            codes=('structured-not-bound', …)
```

The arm now needs both halves: the address is not another happening's AND the
page's own printed content states the day the node claims. An unidentified
witness dates nothing.

**A trap inside that fix, caught by the test the fix was written for.** The
corroboration first compared the node's day against the page's — and
`parse_jsonld` hands back a start already converted to UTC (`2026-12-26T02:00Z`)
while the page prints the local day it means (`2026-12-25`). That is wrong by
one day for every evening show west of Greenwich, and it refused a page that
corroborates itself perfectly. Both sides now read through `same_page_dates`:
one module's convention, with the node found in it by the same instant key the
per-hit bind uses. This is the third appearance of one class in this ticket —
comparing a moment across two normalisations — after r3's naive-vs-aware key.

**(b) A structured day borrowed a clock from unrelated prose.** A bound JSON-LD
node states `2026-09-06` and no time. The carrier was matched to a segment BY
DATE, so the one content block that also mentioned Sep 6 became the statement
that "gave" the day — and its clock became the show's start:

```
PRE-FIX   when=2026-09-06T10:00:00  precision=datetime  text='2026-09-06 10:00am'  codes=()
POST-FIX  when=2026-09-06           precision=date      text='2026-09-06'          codes=('clock-elsewhere',)
```

The code's own comment had said "a structured carrier belongs to no segment and
gets none" since round 1. The date-matching arm quietly did the opposite. A
`<script>` payload and an ICS body are not sentences the page prints; they own
no segment and borrow no clock. A structured node stating a day and no time has
told us the day and no time.

**A test that passed for the wrong reason, caught before pushing.** The first
fixture wrote the box-office line as "Box office opens Sep 6 at 10:00AM" — no
year, so it resolves to no date at all, so the segment never becomes the
carrier's owner and the test went green without reaching the defect. Printing
the year is what makes it reproduce. That is `false-confidence-gate` in a test I
wrote to close a finding, which is the most expensive place to have one.

### 13a. The same round, second pass — the place path had no entity tie

The review of the next head found the class one field over. Rounds 1-4 gave
DATES their scope, their locality and their per-node binding; the place
fallback still took "the one labelled venue anywhere in the content". A page
whose own listing carries no venue markup, beside a related card that does:

```
PRE-FIX   when=2026-09-06T21:00:00  place='The Other Room'  codes=()
POST-FIX  when=2026-09-06T21:00:00  place=None              codes=('place-among-other-happenings',)
```

Cardinality of one, so nothing to refuse as ambiguous, and no code recorded.

The tie is the one the split ladder already uses: a related card links to
another happening's PERMALINK, which is exactly what the committed identity
table matches. The page's content links are now collected by the SAME scanner
pass that finds the places, under the same plumbing rule — two passes would be
two definitions of "this page's content" and they would drift.

A first attempt did this per SEGMENT and broke 13 tests at once, which was the
useful answer: `segments()` returns TEXT, so a scanner that needs `class="venue"`
markup finds nothing in it. That is also why the residual below cannot be closed
the obvious way.

**What this does NOT close, recorded as R-112 rather than implied:** a
promotional block carrying venue markup and NO link is still read as this row's
place. Separating it from the page's own venue block needs a notion of CARD this
module does not have, and the two available substitutes are both refused on the
record — a chrome-word list (r1: "related", "more", "also" are English) and a
title match (brittle across punctuation and truncation). The bound is narrow: a
bound node's venue is read first and is unaffected, two labelled places already
refuse, and the live desk resolves its places through bound nodes.

### 13b. The live desk rejected my own fix, and it was right

Run [34008921609](https://github.com/schubertsean-ui/onelive/actions/runs/34008921609)
on head `bb6380a` — the r4 fixes — against run 34007753540 on `9e3029a`:

| the page said | r3 head | r4 head |
|---|---:|---:|
| `structured-not-bound` | 2 | **17** (42% of opened) |
| `date-in-plumbing` | 1 | **14** (35%) |
| `no-clock` | 26 | 13 |

Fifteen of forty pages stopped being dated. The diagnostic named the reason in
the desk's own words:

> `/event/prodigal-sun-14267156`: … the address it names is one no committed
> pattern classifies, and **the page's own content states 2026-09-06, which does
> not corroborate the day it claims**

The node states Sep 4. The page displays Sep 6. Both are about Prodigal Sun — a
run of performances has more than one date, and the two statements are about
different ones. **That is not evidence the node belongs to another happening.**

The evaluator asked an IDENTITY question — is this node ours? — and I answered
an AGREEMENT question — does the page's content back up its day? They are not
the same question, and on any desk that lists a run rather than a single night
they give opposite answers. The corroboration is now the identity test it should
always have been: the node must NAME what the page names, comparing its `title`
against the page's own `<h1>`/`<title>` with case, punctuation and spacing
treated as noise and containment allowed either way (a desk heads a page
"Prodigal Sun at Saengerrunde Hall" and the node says "Prodigal Sun").

The evaluator's case is still closed by it, and more directly than before: its
attack node calls itself "Something Else" on a page headed "Dominic Fike".

Two tests pin the shape that broke — the disagreeing run, and the heading that
says more than the node. This is the value of running the rule against the desk
rather than only against the fixtures I wrote for it: every hermetic test passed
on both versions, because I had not thought to write the case where a page and
its own node disagree about which night.

## 14. What this ticket did NOT do

* No Tonight redesign, no catalog upsert, no `ai_extract` change, no new vendor,
  no login, no Planomato, no touching PRs #230/#231/#232.
* The LIST walk's 40-page cap is unchanged (`--max-pages`); the new
  `--follow-budget` is a separate cap on event pages.
* Nothing is written or promoted. `--write` still needs `--real` and a DSN, and
  neither this run nor that workflow passes either.
