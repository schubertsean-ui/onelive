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
130 passed in 0.43s
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
[34011052450](https://github.com/schubertsean-ui/onelive/actions/runs/34011052450)
on head `f436fe3`, `--real --dry-run --max-pages 3 --follow-budget 40`. Pasted
from that job log:

| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 118 | 38 | 80 | 0 | 0 |
| `do512-today` | 0 | 0 | 0 | 1 | 0 |

`mash_n` is **0**, which is the precondition the whole tick rests on: a mashed
row's address IS the list page, so following it would have written one page's
date onto every happening on the desk.

Why the rest are NULL — three different facts, and only the first is about the
desk:

| desk | pages opened | page stated no date | could not be read | not asked (budget) | no followable address |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 40 | 2 | 0 | 78 | 0 |

So of the 40 pages the budget reached, **38 were dated and 2 stated no date**.
The other 78 followable rows were never opened, which makes `dated_n` a FLOOR
and `still_null_n` a CEILING.

Three sample rows, pasted from the same log:

| # | listing_url | start_time | place |
|---:|---|---|---|
| 1 | `.../event/barbie-dream-heist-14311407` | 2026-09-04T22:00:00-05:00 | Butterfly Bar at the Vortex |
| 2 | `.../event/day-of-dance-14167854` | 2026-09-12T10:00:00-05:00 | AISD Performing Arts Center |
| 3 | `.../event/boeing-boeing-14285657` | 2026-09-18T19:30:00-05:00 | TexARTS |

All three are `filled_from_detail = (when, place_text)` — six fields the list
card left empty and the event page filled.

**What the opened pages said**, and what it says about the rounds:

| the page said | pages | of opened | at the r4 head |
|---|---:|---:|---:|
| `no-clock` | 24 | 60% | 13 |
| `clock-elsewhere` | 3 | 7% | 2 |
| `structured-not-bound` | 3 | 7% | **17** |
| `date-in-plumbing` | 2 | 5% | **14** |
| `place-among-other-happenings` | 2 | 5% | — |
| `clocks-ambiguous` | 1 | 2% | 1 |

The last column is the run that made §13b's finding. `structured-not-bound` 17 →
3 and `date-in-plumbing` 14 → 2 is the identity correction giving back the
coverage the agreement test had destroyed, measured rather than argued.

**The places are also visibly better, which was not the point of any round.**
Before the card boundary, a third of planned rows took their place from the
page's whole labelled venue block — "Venue Details Dougherty Arts Center 1110
Barton Springs Rd., Austin South Congress and South First
austintexas.gov/dougherty 10 events". Those same rows now read "Dougherty Arts
Center", "Hyde Park Theatre", "Saengerrunde Hall": the dump was outside the
page's card, and excluding it left the clean labelled element inside. Two rows
refuse a place outright rather than take a neighbouring card's.

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

### 13c. Both seats then named the same thing, and one half was still open

The review of `bb6380a` (the agreement version) came back with both openai
seats independently describing the defect the live run had already shown me:

> `_states_the_day()` only corroborates the day, not the event identity, title,
> time, or place

That half was already corrected in §13b. The other half was still live: the arm
for a node naming NO address never got the identity check at all, because round
2 had accepted it as "a permalink page publishing an Event about itself".

> a lone unaddressed JSON-LD `Event` … can be treated as this happening without
> checking title/content/entity identity

They are right, and it is the same sentence as the vanity case: a promotional
node that simply omits `url` is exactly as unidentified as one carrying a link
the table cannot classify. **What the node names does not decide this. What it
calls itself does.** The address check is gone from that condition entirely, so
every lone node now faces the same question.

Fixing it broke three fixtures, and both reasons were worth having:

* Two nodes were named `"A"`. Containment either way makes a single letter match
  "A Show", "A Completely Different Thing", and every heading with an article in
  it. The comparison is now on whole WORDS with a floor — one token of two or
  more characters, or two tokens — and `test_a_single_letter_names_nothing`
  pins it.
* One fixture page had no `<h1>` and no `<title>` at all, so there was nothing to
  compare against. That is an artifact of terse test HTML rather than a desk
  shape; the fixtures now carry the heading a real page carries.

## 13d. Evaluator round 5 — the strong bind, and the residual that would not stay recorded

Two blocking findings, both reproduced on the pre-fix head, both closed.

**(a) A node naming THIS address was accepted on the address alone.** That is
the strongest thing markup can say about whose page it is on, and until now it
needed nothing else. But a node claiming to be about this permalink while
calling itself another show is a desk publishing two different answers about
one page:

```
PRE-FIX   when=2026-12-25T20:00:00-06:00  place=The Other Room  codes=()
POST-FIX  when=None                       place=None            codes=('structured-not-bound', …)
```

The test that covered this shape was previously asserting the defect — it took
`SIDEBAR_EVENT`, rewrote its `url` to this page, and asserted the row was dated.
It now asserts the opposite.

The bound arm asks only that the node not CONTRADICT the page, not that it
positively agree, because the evidence is different in kind: an explicit address
assertion plus silence is still an assertion, while a lone node with no address
has only its name to stand on. **Absence is not disagreement** — a page with no
heading, or a node with no name, keeps the bind it earned, and that has its own
test. Requiring positive agreement there would hole every desk whose event page
heads with the venue or a masthead.

**(b) R-112's residual would not stay recorded, and the repo's own rule says so.**
Both seats blocked on the unlinked promotional block. `deferred-trust-work`:
*a RECORD row is not a safe harbour when the bound it states does not cover the
harm it names.* R-112's bound did not.

The CARD BOUNDARY that row said this module did not have was already in the
HTML, in the vocabulary the date path's scope rule has read since round 1: **the
page's own heading sits in a sectioning element; that element is the card; a
labelled place outside it is about something else.** No chrome-word list, no
title match. `_PlaceScanner` numbers each open element and remembers the section
holding the first non-plumbing heading; `_scan_places` keeps only the places
opened inside it. A page whose heading is in no section at all is ONE card and
keeps every place on it.

```
PRE-FIX   an unlinked <section class="sponsors">  ->  place='The Sponsor Lounge'  codes=()
POST-FIX                                              place=None                 codes=('no-place',)
```

Round 4's other-happenings rule is kept rather than replaced: on a page whose
heading is in no section, the boundary cannot separate anything, and that rule
is the only thing left between a promo venue and the row. It has its own test.

An attempt to close (b) by DELETING the unbound fallback outright broke 18
tests, including the founder's own case (b) — "event page clock-only -> the
place still fills". That was the useful answer: the fallback is what fills the
place on every page without structured venue markup, and the defect was never
the fallback but the absence of a boundary around it.

### 13e. One boundary, both fields

The review of the next head kept the place finding (fixed above) and added the
same question about the DATE path: the card boundary was built for places and
the date path still read every non-plumbing segment.

> a related/unlinked promo block in page content that prints the only date/clock
> can be attached to the current row

```
PRE-FIX   an unlinked <section class="promo">  ->  when=2026-12-25T20:00:00  codes=('no-place',)
POST-FIX                                           when=None                 codes=('date-in-plumbing', …)
```

`_SegmentScanner` now carries the same element numbering and the same
subject-scope as the place scan, and `segments()` returns only the statements
printed inside the section holding the page's own heading. One boundary, both
fields.

**It also settled an older test in the other direction, and that is worth
reading carefully.** `test_prose_beside_a_calendar_widget_is_still_refused`
asserted that an article stating "Sat Sep 5 • 9:00PM" beside a month grid dated
NOTHING, reasoning that the page "only prints one date among thirty-one". That
was never what the page does: it prints one date in the article holding its own
heading, beside a navigation calendar about no happening at all. The very first
live run refused 40 of 40 pages on this shape; the structured tier rescued the
ones that declare a start, and the ones that merely print one stayed poisoned
until now.

So the test's premise changed, not the standard, and both directions are pinned:

| the grid is | the page states |
|---|---|
| outside the card | `2026-09-05T21:00:00` — the article's own line |
| inside the card | `None` + `dates-ambiguous` — thirty-one days about itself |

The `date-in-plumbing` sentence is also corrected. The counter token keeps its
name so its history stays continuous, but a reason that says "plumbing" about a
promotional card sends the next reader at the wrong repair, so it now names
both: the page's own plumbing, or another card beside its own.

### 13f. Round 6 — the boundary's own two ends, and a definition that drifted

Three findings, both openai seats; both gemini APPROVE. All three reproduced
before fixing.

| | pre-fix | post-fix |
|---|---|---|
| a promo `<h2>` above the article | `2026-12-25T20:00:00` / The Other Room | `2026-09-05T21:00:00` / The Hall |
| sectionless heading + promo `<section>` | `2026-12-25T20:00:00` / The Other Room | `None` |
| `<h2>` subject + node claiming this URL | `2026-12-25T20:00:00-06:00` / The Other Room | `None` |

**(a) The subject was the first heading of ANY level.** A promotional block
placed above the real article carries its own `<h2>`, date and venue — so it
became the page's subject and pushed the real content outside the card. `<h1>`
is the subject by HTML's own semantics; `h2`/`h3` stand in only for a page that
prints no `<h1>` at all, and a page like that keeps its boundary (its own test).

**(b) A sectionless heading disabled the boundary entirely.** "One card" was a
permissive fallback, and it let an unlinked promo `<section>` supply the only
date on a page whose heading sits directly in `<body>`. The card rule now has
two clauses that pull opposite ways and needs both:

* a statement OUTSIDE the heading's section is not the page's own — the
  heading's sections must be a PREFIX of the statement's (which still admits a
  subsection of the card);
* a statement inside ANY section when the heading is in none is not the page's
  own either.

The first clause is what keeps the month-grid case from §13e working; the
second is the r6 finding. Writing only one of them breaks the other, which is
how the first attempt at this failed its own earlier test.

**(c) Two definitions of "the page's heading" had drifted.** The boundary
already treated `<h2>` as a page subject while `_headings` read only
`<h1>`/`<title>` — so a page whose visible subject is an `<h2>` had NOTHING for
`_contradicts_this_page` to compare against, and a poisoned node claiming this
URL sailed through. Both now come from `_HEADING_TAGS` with the same
precedence. Subheadings of a page that HAS an `<h1>` are deliberately excluded,
so the fix cannot hand a poisoned node an easier target — its own test.

That is the third time this ticket has been bitten by one rule expressed twice
(the r3 UTC/local instant keys, the r4 heading sets, this). The pattern is in
the red classes.

### 13g. Round 7 — the tab caption does not get a second vote

One blocking finding (openai/absence-only; both gemini APPROVE), and a gemini
nit that turned out to have the same fix.

**A stale `<title>` could rescue a node the visible heading contradicts.**
`_headings` fed `<title>` and the visible subject into ONE list, and a node need
only match ANY of them. CMS titles go stale routinely:

```
PRE-FIX   when=2026-12-25T20:00:00-06:00  place='The Other Room'
          headings=['Some Other Show', 'Dominic Fike']
POST-FIX  when=None                       headings=['Dominic Fike']
```

The visible subject now wins outright; `<title>` is read only when the page
prints no heading at all — and that fallback has its own test, because a desk
whose event page is headed by an image would otherwise lose every bind.

**The nit had the same root, and it is the class I opened last round.**
`_headings` was a regex over raw HTML while the scanners suppressed plumbing, so
`<nav><h1>Browse Events</h1></nav>` was a name this page answered to:

```
PRE-FIX   headings=['Dominic Fike', 'Browse Events', 'Dominic Fike']
POST-FIX  headings=['Dominic Fike']
```

Headings now come from the SEGMENT SCAN — the walk that already knows what
plumbing is. That removes the last place the heading rule was expressed twice:
one walk, one precedence, one answer. `one-rule-expressed-twice` was opened in
r6 with three instances; this is the fourth, found by a reviewer rather than by
me, one round after I named the class.

### 13h. Round 8 — identity is not certainty, and the tier rule had outlived its reason

Two blocking findings (openai/attacker-smuggle; both gemini APPROVE), one shape:
**the structured tier won outright without asking whether the page's own card
contradicts it.** A stale or series `startDate` published as the settled day
while the page visibly says another; a node `location` overriding a
contradictory visible venue.

**This reverses "never mix tiers", and the reason it can is worth stating.**
That rule was written at r1 because counting prose against a structured
statement refused 40 of 40 live pages — a month grid in the sidebar outvoted a
node that declared its start perfectly well. What changed is the CARD BOUNDARY
(r5/r6): `said` is no longer "text somewhere on the page", it is *this
happening's own card*. So a visible date there is not a competing tier — it is
the same desk contradicting itself about the same show, and a page that states
two different days about itself has not stated one. **The old rule was right
about the page it was written for, and the scope work since is what made a
narrower rule possible.**

**It also splits a test I wrote three rounds ago, and both halves survive.**
§13b established that a node disagreeing with the page is not evidence it
belongs to another happening — `/event/prodigal-sun-14267156` states Sep 4 and
displays Sep 6, both about Prodigal Sun. That is still true, and the node still
BINDS: its venue comes through. What it no longer does is settle the DAY.
Identity and certainty are different questions, and r4 taught the first while r8
teaches the second:

| | | |
|---|---|---|
| node Sep 4, card Sep 6 | `when=None` + `card-contradicts-its-own-markup` | `place='Saengerrunde Hall'` |
| node and card agree | `when=2026-09-04T19:30:00-05:00` | `place='Saengerrunde Hall'` |

**The commonest cause is a RUN**, and holing it is a deliberate choice about
whose job it is. A JSON-LD `startDate` carrying opening night while the page
displays the next performance is not a defect in the desk — it is a shape this
pipeline has no model for. Publishing the opening puts a day in front of a
reader the desk is visibly not claiming; modelling runs is the next ticket's
work; counting them is this one's, so that ticket opens with a number rather
than a hunch.

**The place comparison is `_same_name`, not equality** — a card routinely prints
"Saengerrunde Hall 1607 San Jacinto, Austin" where the node says "Saengerrunde
Hall", and calling that a contradiction would refuse every desk that tells its
readers where to go. Its own test.

**Expect `dated_n` to fall on the next live run.** That number is not a
regression to explain away: it is the measurement of how often this desk's
structured data disagrees with its own pages, which nothing before this round
could see.

### 13i. Round 9 — the last of the card rule's defaults

One blocking finding (openai/absence-only; both gemini APPROVE), and it is the
card rule's THIRD case: a page printing no heading at all.

I had written "nothing is known about what it is about, so nothing is excluded
on that basis". `_inside_the_card` read that as exclude nothing, so an
image-headed page with an unrelated promo `<section>` published that section's
date and venue:

```
PRE-FIX   when=2026-12-25T20:00:00  place='The Other Room'  codes=()
POST-FIX  when=None                 place=None
```

**Not knowing what a page is about is a reason to trust it less, not more.**
That sentence is the whole finding, and it is the third default in this one
rule to have been written the permissive way — r6 caught the sectionless
heading, r9 the absent one.

**The first fix was too blunt and three existing tests said so.** Page-level
statements only would have cost every heading-less page whose content sits in
one `<article>`. So the rule distinguishes: with exactly ONE top-level card,
that card is the subject — it is the only thing the page could be about; with
two or more there is nothing to choose between them, so only page-level
statements count and every section is excluded, which is the seat's case
exactly. Both directions tested.

### 13j. The r8 check met the live desk, and the desk corrected it twice

The prediction held. Run
[34013696335](https://github.com/schubertsean-ui/onelive/actions/runs/34013696335)
on head `e3f5d7f`:

| | run 18 (`f436fe3`) | run 21 (`e3f5d7f`) |
|---|---:|---:|
| `dated_n` | 38 | **23** |
| `card-contradicts-its-own-markup` | — | **15 of 40 opened (37%)** |

And the reason was the one predicted, in the desk's own words:

```
boeing-boeing-14285657: this happening's own card states 2026-09-19,
  2026-09-20, 2026-09-24 while the page's structured data states 2026-09-18
pecan-street-fall-festival: card states 2026-09-13, structured data 2026-09-12
```

Runs and multi-day festivals. **But reading that back showed the rule was
broader than its own message, twice over.**

**(1) It fired on elaboration, not just contradiction.** `card_days -
node_days` is non-empty whenever the card lists MORE days than the markup — a
card naming three performances and markup naming one is the desk agreeing with
itself at different resolutions. Narrowed to `node_days - card_days`: a
contradiction is the card NOT carrying the markup's day.

**(2) The narrowed rule still refused, for the r3 reason.** R-030 reports each
date under **the strongest carrier that stated it**, so a day the card prints
AND the markup names comes back as `jsonld` — and vanished from a "what the
card printed" filter applied to the document-wide scan. The card's days are now
read FROM THE CARD, segment by segment, where no structured carrier is in
scope. Two computations of one thing, compared: the same class as the r3
instant keys, third instance.

| the card says | the markup says | result |
|---|---|---|
| Sep 18, 19, 20 | Sep 18 | `2026-09-18T19:30:00-05:00` — elaboration |
| Sep 19, 20 | Sep 18 | `None` + `card-contradicts-its-own-markup` |
| Sep 18 | Sep 18 | `2026-09-18T19:30:00-05:00` |
| nothing | Sep 18 | `2026-09-18T19:30:00-05:00` |

**What the 37% still means, after both corrections, is the next run's to say.**
Some of those pages were elaboration and will come back; the rest are genuine
disagreement, and that residue is the measurement the run-modelling ticket
needs. Publishing this ticket's final number before that run would be reporting
a rule that no longer ships.

### 13k. Round 10 — the check that only checked half, and a rule that refused a language

Two findings, both `openai/attacker-smuggle`, both reproduced against the
shipped head `6449e63` before a line was changed.

**(1) The r8 cross-tier check compared DAYS and stopped there.** A card printing
`8:00PM` above markup stating `19:30` agreed about the day, so the check passed
it and the desk published a precise time its own visible page contradicts. The
r8 message already said "the desk is contradicting itself" — it just wasn't
looking at the clock. The fix compares the card's printed wall clock against the
structured instant's wall clock, LOCAL as written (`_wall_clock`): converting to
UTC first would compare `00:30` with the card's `8:00PM` and call every
Central-time desk a liar — the r3 instant-key lesson, applied before it could
bite a second time. The day is agreed, so **the day stands and only the clock is
holed** — the same shape as `clocks-ambiguous`, not a new one.

**(2) `_same_name` refused entire writing systems.** It normalised with
`[^0-9a-z]+`, so every character outside the Latin alphabet was stripped. The
evaluator reported the loose half: "Кино Night" collapses to `night` and matches
an unrelated node called "Night". Reproducing it found the tight half, which is
worse and was not reported: a page headed "Кино" alone collapses to the **empty
string**, `_same_name` can never be true for it, and so every lone node on that
page refuses `structured-not-bound` while every bound node reads as
contradicting the heading. **A desk in Cyrillic, Greek, Chinese, Hebrew or Thai
could not fill a single field** — a locale refused in code, which Coverage Law
forbids outright. "Café du Nord" came back as `caf du nord`. It was invisible
because every fixture and every desk in this repo is English.

**And the fix is an import, because this repo had already answered it.**
`docs/memory/RED_CLASSES.md` carries `destructive-normalization` from PR #214,
three review rounds deep, and its worked examples are — verbatim — `Кино Night`
→ `night` and `Café` → `caf`. The remedy lives two modules away in
`worker/locale/desk_union._hard`: NFC-compose, fold marks only where the base
decomposes onto ASCII (so Latin accents normalise and Devanagari vowel signs
survive), delete apostrophes, flatten the rest, drop a leading "The". I typed
the regex that class warns about, in the same package, and my first hand-rolled
fix (`str.isalnum()`) closed only the erasure half — it left "Café du Nord" and
"Cafe du Nord" as different venues, and **my first draft of the test asserted
exactly that**: the defect written down as the expectation, inside the test
meant to close it. `_hard` is now exported as `name_key` and `_name_tokens` is
`name_key(name).split()`. One question, one answer.

| | old `[^0-9a-z]+` | `str.isalnum()` (my draft) | `name_key` (shipped) |
|---|---|---|---|
| `Кино` binds at all | ✗ empty string | ✓ | ✓ |
| `Café du Nord` = `Cafe du Nord` | ✗ | ✗ | ✓ |
| `The Continental Club` = `Continental Club` | ✗ | ✗ | ✓ |
| Devanagari vowel signs kept distinct | ✗ | ✓ | ✓ |

**Residual, recorded not hidden (R-113):** in a script without spaces one name
is one token, so `東京ホール` binds to itself by exact match but `東京` does not
bind into it by containment. Pinned in the test both ways. Loosening
containment to substrings would match "Night" inside "Nightingale" for every
desk in the corpus, which is a worse trade than the one it fixes.

```
=== PRE-FIX (HEAD 6449e63) ===
card clock CONTRADICTS the markup  when=2026-09-18T19:30:00-05:00  codes=()
a Cyrillic page can bind at all    when=None  place=None  codes=('structured-not-bound', ...)
=== POST-FIX ===
card clock CONTRADICTS the markup  when=2026-09-18            codes=('card-contradicts-its-own-markup',)
card clock AGREES with the markup  when=2026-09-18T19:30:00-05:00  codes=()
card prints no clock               when=2026-09-18T19:30:00-05:00  codes=()
a Cyrillic page can bind at all    when=2026-09-18T19:30:00-05:00  place=Дом  codes=()
```

The declined half below was written against the hand-rolled draft and still
stands after the import: `name_key` normalises spelling, it does not decide how
much of a name has to match.

**DECLINED, on the record: tightening single-token containment.** The loose half
the evaluator reported is real — a node named "Night" still binds to a page
headed "Кино Night" — and I am not fixing it in this ticket, because every
available tightening costs coverage the desk actually uses:

| tightening | what it would also refuse |
|---|---|
| require the match to start at token 0 | "Live at the Continental Club" vs "Continental Club" |
| token-ratio floor (e.g. ≥50% of the heading) | a heading carrying a date or a presenter prefix |
| stopword / chrome-word list | refused on the record at r1 — host knowledge is DATA, and this would be English knowledge in code |

Containment is already floored at two characters or two tokens (r5), and a
false bind here costs a wrong FIELD on a page that is otherwise the right
happening, not a wrong happening. The cheap wrong fix would put a language's
vocabulary back into the reader module, which is the defect I just removed.
Recorded rather than silently dropped: `docs/RECORD.md` R-113.

### 13l. The table on head `7676b59` — HISTORICAL, superseded by r12/r14

> **This is not this ticket's final number.** It was final when written, and
> rounds 12 and 14 have since changed which rows are dated — §13n's date
> ownership rule and §13p's clock anchoring both move it, and §13p says so
> explicitly. Kept because the r7 → r8 → r8-corrected comparison inside it is
> the measurement that justified the r8 check, and that comparison is still
> true of those heads. The final table is §13q.

Run [34015650549](https://github.com/schubertsean-ui/onelive/actions/runs/34015650549)
on head `7676b59`, `--max-pages 3 --follow-budget 40`. This is the ticket's
answer to Must-do 4, and it is the first number this document publishes since
r8 — every earlier one was produced by a rule that has since been corrected.

| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 109 | **34** | 75 | 0 | **0** |
| `do512-today` | 0 | 0 | 0 | 1 | 0 |

**Why the rest are still NULL**, which is the part a count alone hides:

| pages opened | page stated no date | page could not be read | not asked (budget) | no followable address |
|---:|---:|---:|---:|---:|
| 40 | 6 | 0 | **69** | 0 |

34 of the 40 pages the budget reached are dated and 6 state no date. The 69
unopened rows are **unasked, not dateless** — `dated_n` is a floor and
`still_null_n` a ceiling.

Three sample rows, as the founder asked:

| listing_url | start_time | place |
|---|---|---|
| `/event/back-to-the-ranch-the-lbj-bbq-returns-14329073` | `2026-09-26` | Lyndon B. Johnson National Historical Park |
| `/event/texas-renaissance-festival-14311742` | `2026-10-10T09:00:00-05:00` | Texas Renaissance Festival |
| `/event/zz-fest-w-amplified-heat-zz-top-tribute-14325034` | `2026-09-12T14:00:00-05:00` | Lightnin' Bar |

**The first sample row is r10 firing on a real page on its first live run.** It
carries a DATE and no clock, and the desk's own words say why:

```
card-contradicts-its-own-markup — /event/back-to-the-ranch-the-lbj-bbq-returns-14329073:
  this happening's own card prints 10 pm while its structured data states
  2026-09-26T18:00:00-05:00 — the desk is contradicting itself about the time,
  so the day stands and the clock stays a hole
```

Before r10 that row published `18:00` under a page printing 10 pm. Now the
agreed day survives and only the contested clock is a hole — which is the whole
argument for holing the smallest thing that is actually in dispute.

**And the r8 correction is measured, not asserted:**

| head | rule | dated of 40 opened | `card-contradicts-its-own-markup` |
|---|---|---:|---:|
| `f436fe3` (r7) | no cross-tier check | 38 | — |
| `e3f5d7f` (r8 as first written) | fires on elaboration; card days read document-wide | 23 | 15 (37%) |
| `7676b59` (r8 corrected + r10) | fires only on contradiction; card days read from the card | **34** | **5 (12%)** |

So the residual is 12%, not 37%: three quarters of what r8 refused was the desk
agreeing with itself at two resolutions, and the remaining 5 pages are genuine
disagreement — runs and multi-day festivals, which the pipeline has no model
for. **That 12% is the input the run-modelling ticket needs**, and it is a
number nothing before this round could see.

Known and unchanged: row 16 of the write plan still carries a whole venue block
as its place ('Venue Details Ground Floor Theatre 979 Springdale #122, Austin
East groundfloortheatre.org 3 events') — §9c, place-text normalisation is the
neighbouring ticket. `do512-today` is still walled (403 on first contact, class
D, queued, nothing deleted).

### 13m. Round 11 — the guard that a second clock walks past, and an address the two modules spelled differently

Both openai seats blocking, both gemini APPROVE, both reproduced against the
shipped head `fc6cd6c` before a line changed. **Both are defects in code this
ticket added, one round after adding it.**

**(1) attacker-smuggle — r10's clock check compared against `page_clock`,
which is `None` the moment a card prints TWO clocks.** And the multi-clock
diagnostic underneath it is suppressed once a carrier states the whole instant
(that suppression is §13's own `diagnostics-as-data` fix). So the two rules had
a gap exactly between them:

```
card: "Friday, September 18, 2026 — 8:00PM; doors 7:00PM"
node: startDate 2026-09-18T19:30:00-05:00
PRE-FIX  when=2026-09-18T19:30:00-05:00  codes=()
```

19:30 is neither of the times the page prints, published as settled, with no
refusal at all — and adding a second clock is all it takes. **Membership, not
equality, is the rule that covers both counts:** the card's clocks are the
times this desk says are involved, and the markup's job is to say WHICH one
starts the show. That is the r8 lesson (elaboration is not contradiction)
applied to clocks instead of days.

| the card prints | the node states | result |
|---|---|---|
| `8:00PM; doors 7:00PM` | 19:30 | `card-contradicts-its-own-markup` + `clocks-ambiguous`, day stands |
| `7:30PM; doors 7:00PM` | 19:30 | `2026-09-18T19:30:00-05:00` — the markup settled which |
| `8:00PM` | 19:30 | refused (r10, unchanged) |
| `7:30PM` | 19:30 | dated (r10, unchanged) |
| nothing | 19:30 | dated |

Row 2 is a **coverage gain**: that page used to lose its clock to
`clocks-ambiguous` for no reason. Row 1 shows the two rules now composing —
the precision drops to `date`, so the row genuinely has a clock hole and the
multi-clock reason records beside the contradiction instead of being suppressed.
Clocks the date rule cannot resolve are dropped rather than counted against the
node: an unreadable statement is not a contradicting one.

**(2) absence-only — `_address()` dropped the query, and this repo had already
written down why that is wrong.** `desk_read._identity_of`, on the way IN, says
in its own docstring: *"The query is KEPT: two desks do use `?date=` to address
two instances of one series, and collapsing those would delete a night."* Two
modules, one question — what is an address — and opposite answers. That is
`one-rule-expressed-twice`, **the fifth instance in this ticket**, and the
first where the other half of the contradiction was not only already written
but already justified in prose.

For such a desk every night of a run shares one address here, so both things
the comparison guards fell open at once:

```
PRE-FIX  same_identity("…/event?id=other", "…/event?id=this")  ->  True
```

a redirect from one night to another passes, and a structured node naming a
different night reads as speaking for this one. **Runs are not hypothetical on
this desk** — they are the largest single cause of the refusals r8 exists for,
5 of 40 pages in §13l.

The tolerance that made the query droppable in the first place (r2's `?ref=`)
is kept, and moved to where it belongs — asymmetric, in `same_identity`:

| landed | asked | same page? |
|---|---|---|
| `/event?date=2026-09-19` | `/event?date=2026-09-18` | no — a changed parameter is another night |
| `/event` | `/event?date=2026-09-18` | no — a dropped one is too |
| `/event?date=2026-09-18&ref=cal` | `/event?date=2026-09-18` | yes — an added one cannot change which happening |
| `/event?ref=cal` | `/event` | yes (r2's case, unchanged) |

An ADDED parameter cannot change which happening the desk was addressing; a
CHANGED or DROPPED one can. Where the asked url carries no query, its desk's
identity lives in the path — which is precisely what `_identity_of` keeping the
query means. The refusal message carries the query too (`_shown`), because on a
run-addressing desk a message printing the path alone would say two nights have
the same address and make a correct refusal read like a bug.

**Both new tests were run against the pre-fix head and fail there:**

```
$ git checkout fc6cd6c -- worker/locale/desk_follow.py
$ python -m pytest tests/test_permalink_follow.py -q -k "second_clock or query_naming"
FAILED … test_a_second_clock_on_the_card_does_not_walk_a_node_past_the_check
FAILED … test_a_query_naming_another_night_is_another_page
2 failed, 117 deselected
$ # restored
2 passed, 117 deselected
```

**What round 11 says about rounds 8–10.** Both findings are in code this ticket
wrote, and both are the same shape: a rule stated for the case in front of me,
correct there, and silent one step outside it. r10 compared *the* clock because
the page I had printed one. r2 dropped the query because the redirect I had
added a tracking parameter. Neither was wrong about its own page. The question
that would have caught both is the one `hygiene-narrows-coverage` asks in
reverse — not "whose sites does this refuse?" but **"what does the input look
like one step past my example, and does the sentence I wrote still hold?"**

### 13n. Round 12 — a day is not a fingerprint, and a boundary that varied by markup style

Both openai seats blocking, both gemini APPROVE with one NIT that turned out to
be a coverage regression **round 11 introduced**. All three reproduced against
`bd5b2b9` before a line changed.

**(1) An unbound node could lend this row its clock.** `owned_by_this_happening`
had three arms, and the third was "a hit whose DAY appears among the days the
card states is ours". A day is not a fingerprint. R-030 reports each date under
the strongest carrier that stated it, so when a card prints a bare "September
18, 2026" and an unrelated sidebar node names `2026-09-18T23:00`, the document
scan returns **one** hit — kind `jsonld`, carrying the sidebar's clock:

```
PRE-FIX  when=2026-09-18T23:00:00  codes=('structured-not-bound', …)
POST-FIX when=2026-09-18  precision=date  carrier=visible-date  codes=('structured-not-bound', 'no-clock', …)
```

The other show's time, published as this row's, **beside a refusal saying none
of the nodes dates this row**. A behaviour and its own diagnostic disagreeing
about one page is `diagnostics-as-data` on top of the smuggle.

*And deleting that arm alone was wrong* — the suite said so in one run, before
any live run could. The arm was doing two jobs: rescuing an unbound node by day
(the defect), and recovering the card's own printed date when the document-wide
scan lost it (real). A page printing "Sat Sep 5 • 9:00PM" in its article beside
a 31-cell calendar widget comes back from the whole-document scan with the
widget's days and **not its own**. So the fix is two parts: `jsonld` is refused
outright (a `<script>` payload owns no statement — the comment has said so since
r4, and now it is a line), and `card_dates()` reads the card's segments
directly. **Third time in this ticket a document-wide scan had to become a
per-card one** — r8's card days, r10's clock comparison, this — always because
R-030 credits a date to its strongest carrier and the card's own words vanish
under it.

The r8 test then caught the fallback going too far: on a desk contradicting
itself, r8 empties both tiers, and the new fallback quietly re-supplied the
card's half of the disagreement as the answer. Gated on the contradiction flag.

**(2) The card boundary failed closed or open depending on markup STYLE.** r9
answered the heading-less page with `()` — "page level only, every section
excluded" — which is restrictive on a page built from sectioning elements and
the exact opposite on a page built from `<div>`s. `<div>` is a block boundary
and not a sectioning tag, so such a page has no top-level sections, every
statement sits at page level, and `()` admitted all of them:

```
PRE-FIX  when=2026-12-25T20:00:00  place='The Other Room'  codes=()
```

`()` and `None` were two different answers wearing one value. `()` now means
**the page level IS the subject** (a heading exists, in no section — r6,
tested); `None` means **no subject could be identified**, and admits nothing.

**Blast radius, stated rather than discovered later** (the `hygiene-narrows-coverage`
rule): the VISIBLE-TEXT path is now refused on a page with no visible heading
and no sectioning element. The STRUCTURED path is untouched — a title-only
div-soup page publishing its own schema.org node still fills both fields, which
the test pins. Three existing fixtures broke and all three were scaffolding for
other rules (cardinality, nested place markup, clock locality) that had been
relying on the permissive default; each now carries a heading, with the reason
written in.

**(3) The gemini NIT was a regression r11 introduced.** `field_read` was called
with the LANDED url. Harmless while `_address` dropped the query — and the
moment r11 stopped dropping it, a desk redirecting to `?ref=cal` made every node
naming the canonical address stop matching. Fail-closed, so a hole rather than a
wrong field, but a hole for no reason. The row's own address is the identity
inside `field_read`: `same_identity` has already established the landed page IS
this happening's page. Proven as a regression against `bd5b2b9`, and pinned.

**What rounds 10–12 have in common.** Six findings across three rounds, five of
them in code this ticket wrote, and every one is the same sentence: *a rule
correct about the example in front of me, silent one step outside it.* One clock
became two (r11). One query value became another (r11). One markup style became
another (r12). A day shared by two carriers became a day claimed by the wrong
one (r12). The counter-measure is not another guard — it is asking, of every
rule, **what the input looks like one step past the fixture that motivated it**.

### 13o. Round 13 — the record that did not cover its own harm

Both openai seats blocking, both gemini APPROVE. Three findings, all reproduced
against `d7a5c3e` first, and **the first one is the record I wrote at r10**.

**(1) R-113's bound did not cover the harm it named.** That row declined to
tighten single-token containment and bounded the risk as "a wrong FIELD on a
page that is otherwise the RIGHT happening". Reproduced, it is worse:

```
node: {"name":"Night","startDate":"2026-12-25T20:00:00-06:00",
       "location":{"name":"The Other Room"}}      (no url — a lone node)
page: <h1>Jazz Night</h1>                          (states no date at all)
PRE-FIX  when=2026-12-25T20:00:00-06:00  place='The Other Room'  codes=()
```

A whole fabricated instant and a venue the page never mentions, published with
no refusal — not a wrong detail on the right show. `deferred-trust-work` for the
**second time in this ticket** (R-112 was the first, at r5, and both seats
blocked on it then too). The class's own instruction is the lesson: *test the
bound against the harm before writing the row.*

The fix is the one R-113 declined, **narrowed to the case that carries the
defect**: a single-token name must OPEN the longer name; multi-token containment
is unchanged anywhere in the string. That answers every objection the record
raised, because all of them were about multi-token names:

| | binds? | why |
|---|---|---|
| "Night" ~ "Jazz Night" | no | one word, buried |
| "Gandahar" ~ "Gandahar (1988)" | yes | one word, opens it |
| "Кино" ~ "Кино Night" | yes | one word, opens it |
| "Continental Club" ~ "Live at the Continental Club" | yes | two words — r10's own counter-example |
| "A" ~ "A Show" | no | the r5 floor |

Headings are written `<name> <qualifier>` and never the reverse, which is why
position separates the benign case from the smuggle without a word list.

**(2) `PLACEISH_RE` matched `placeholder` and `replacement`.** A bare
alternation over class/id, so any attribute CONTAINING "place" read as the page
labelling a venue — an empty layout div inside the event's own card became the
page's one labelled place. Now a WORD test, with camelCase split first so
`venueName` still reads (refusing that would trade the defect for a coverage
hole on every desk using the convention). One definition, still shared with
`desk_read`: the list walk asks the same question of the same markup.

**(3) `same_identity` still tolerated ADDED query parameters — and my r11
reasoning for it was wrong in the way this ticket keeps being wrong.** I argued
that where the asked url carries no query, the desk's identity must live in the
path. But a list page can link a RUN's own page rather than one night's, and
then `/event/show` → `/event/show?date=2026-09-19` is the desk choosing a night
for us. Host, path and query now match exactly.

**The cost, stated:** a desk that redirects with an added tracking parameter is
QUEUED with its reason instead of read. Telling a tracking parameter from an
identifying one needs a registry of parameter names — the chrome-word list
refused at r1, one domain over — so the honest price is a hole we can see rather
than a field we cannot justify. The `?ref=calendar` case was always a
hypothetical: no run in this ticket's evidence has ever seen one. Two tests that
asserted the old tolerance now assert the new rule, with the premise change
written into them.

**Seven rounds, one sentence.** r10 through r13: nine findings, seven of them in
code this ticket wrote. Every one is a rule that was correct about the example
in front of me and silent one step outside it — and finding (3) is the same
argument I made at r11 being wrong for the third distinct reason. The record
that matters is not another guard; it is that **a residual I reason my way into
accepting deserves the reproduction I would give a finding.** R-112 and R-113
were both written confidently, and both were reproduced into blocking defects by
the next review round.

### 13p. Round 14 — a clock with no day of its own is still a clock

Three of four seats APPROVE. One blocking finding (openai/absence-only),
reproduced against `6b5b4ab` first.

**The clock comparison only counted tokens the date rule could turn into a full
INSTANT — and that needs a day.** A card printing "Show 8:00PM" and no date
produced nothing to compare against:

```
card: <p>Show 8:00PM</p>          (no date printed)
node: startDate 2026-09-18T19:30:00-05:00
PRE-FIX  when=2026-09-18T19:30:00-05:00  codes=()
```

The node's half past seven published as settled under a page visibly saying
eight o'clock. My own comment beneath that code said unreadable clocks are
dropped, and it conflated two different things: **"8:00PM" is perfectly
readable as a wall clock — it simply has no day of its own.**

Each printed clock is now anchored to the NODE'S day. The day is scaffolding
for the parser, never a claim, and the days are already known to agree because
r8's check empties both tiers before this point when they do not. Anchoring
rather than writing a clock regex is deliberate: `same_page_dates` is the one
place that knows what "doors 7 pm" means, and a second reader of the same thing
is the class this ticket has paid for five times.

**The fix has a coverage cost and it landed on the live table's own row.** The
existing test for `/event/boeing-boeing-14285657` went red: that page prints
"Matinees 4:45 pm. Late show 10:15 pm." while its node states 19:30. Those
clocks could not be anchored before; now they can, and the node's is none of
them, so the clock holes and the day stands.

| the card prints | the node states | before r14 | after r14 |
|---|---|---|---|
| `Show 8:00PM`, no date | 19:30 | **19:30 published** | day only + refusal |
| `Show 7:30PM`, no date | 19:30 | 19:30 | 19:30 |
| `Matinees 4:45 pm. Late show 10:15 pm.` | 19:30 | 19:30 | day only + refusal |
| `Doors 7:00 pm. Curtain 7:30 pm.` | 19:30 | 19:30 | 19:30 |
| `at noon` (unparseable) | 19:30 | 19:30 | 19:30 |

**That is a decision, not a surprise, and it is pinned in its own test.** It is
the same answer r8 gave for DAYS, kept as one rule rather than two: a
contradiction is the card not carrying the node's answer. Separating "matinees"
and "late show" (other performances) from "doors" and "curtain" (this one) needs
a list of label words — refused on the record at r1 — so the honest price of
never publishing a time the visible page does not state is holing the clock on a
desk that describes a RUN. Expect `dated_n` to fall again, and that fall is this
ticket's measurement of how much of this desk is runs.

The diagnostic rule the boeing fixture originally pinned (do not record
`clocks-ambiguous` against a row with no clock hole — §9a) is unchanged and now
stated on a page whose printed clocks include the node's.

### 13q. Round 15 — a finding that did not reproduce, and two the live run found instead

Three of four seats APPROVE. The blocking finding (openai/absence-only) says a
same-day carrier outside the card can supply this row's clock "because the check
accepts the carrier by matching only the date to the card".

**That check was removed at r12**, for exactly this class — a day is not a
fingerprint (§13n). Five shapes of the attack were run against the reviewed
head `52a5e30` and all five already behaved:

| the outside carrier | result |
|---|---|
| `<time>` in a sibling `<article>` | `2026-09-18` at `date` precision, `no-clock` |
| `<time>` in an `<aside>` | same |
| `<time>` at body level | same |
| visible `11:00PM` prose in a sibling card | same |
| `11:00PM` in the page footer | same |

**So the finding is answered rather than coded**, and the seat's own NIT is
taken: the invariant is real even though the defect is not, and it was not
PINNED. "It happens to work" and "it is pinned" are different states — the r5
lesson from the other side, where a test that WAS present had asserted the
defect for four rounds. `test_a_same_day_clock_outside_the_card_never_becomes_this_rows_time`
covers all five shapes plus the converse, and it is not vacuous: restoring the
arm r12 deleted turns it red.

Both documentation nits are taken too — §13l is retitled as historical, and a
duplicated bold run is removed.

**And then the live run of r14 found two defects in my own last two rounds.**
Run [34019858312](https://github.com/schubertsean-ui/onelive/actions/runs/34019858312)
on `52a5e30`, read in the desk's own words:

```
card-contradicts-its-own-markup — /event/boeing-boeing-14285657:
  this happening's own card prints 7:30, 10:15 pm, 4:45 pm while its structured
  data states 2026-09-18T19:30:00-05:00, which is none of them
```

**19:30 IS half past seven.** A bare "7:30" states a clock FACE, not an hour of
the day; r14's anchoring read it as 07:30 and called the desk a liar for
agreeing with itself. A token carrying no am/pm now agrees with either reading —
**an ambiguous statement is not a contradicting one**, which is the principle
r12 stated and r14 applied backwards. Cost, stated: a bare "9:00" no longer
contradicts markup saying 21:00, which is precisely the case where the card has
not said which it means. A token that DOES say am or pm is still compared
exactly, so r10's `8:00PM` finding is untouched.

```
card-contradicts-its-own-markup — /event/boeing-boeing-14285657:
  this happening's own card labels Venue Details TexARTS 1110 S RR 620, Lakeway
  West Austin and Lakeway tex-arts.org 2 events while the page's structured data
  for it states TexARTS
```

**That is r13's coverage cost arriving.** r13 tightened `_same_name` so a lone
token must OPEN the longer name — right for IDENTITY, where a false yes binds
another happening's node, and wrong for the PLACE check, where a false no
invents a contradiction and holes a place we had. The block CONTAINS "TexARTS";
it simply does not start with it.

**This repo had already written that lesson down.** `destructive-normalization`
r9: *"When one helper serves two callers, check whether their failure modes
point the same way; if they do not, they share a NAME rather than a helper.
Split on the QUESTION, not on the data."* Identity asks "are these the same
name"; a labelled block asks "does this text NAME this place". Split into
`_names_within`, and both directions pinned.

**Both were proven against `52a5e30` before fixing and after.** Neither was
reported by any seat: they came from reading the run's own sentences, which is
now the fourth, fifth and sixth defect this ticket's diagnostics found in its
own rules.

### The table, on the rules that ship

Run [34019858312](https://github.com/schubertsean-ui/onelive/actions/runs/34019858312)
on `52a5e30` — every rule through r14. **This is the last table produced before
the two r15 corrections above, and both of them RELEASE clocks and places this
run holed**, so the numbers below are a FLOOR in one more way than the budget
already makes them:

| desk | rows_n | dated_n | still_null_n | 403_n | mash_n |
|---|---:|---:|---:|---:|---:|
| `austin-chronicle-eventsearch` | 120 | 33 | 87 | 0 | **0** |
| `do512-today` | 0 | 0 | 0 | 1 | 0 |

| pages opened | page stated no date | could not be read | not asked (budget) | no followable address |
|---:|---:|---:|---:|---:|
| 40 | 7 | 0 | **80** | 0 |

| listing_url | start_time | place |
|---|---|---|
| `/event/back-to-the-ranch-…-14329073` | `2026-09-26` | Lyndon B. Johnson National Historical Park |
| `/event/texas-renaissance-festival-14311742` | `2026-10-10T09:00:00-05:00` | Texas Renaissance Festival |
| `/event/zz-fest-w-amplified-heat-…-14325034` | `2026-09-12T14:00:00-05:00` | Lightnin' Bar |

`mash_n` is **0**, which is the precondition for this tick being safe at all.

**The arc of `dated_n`, and what each step bought:**

| head | rule added | dated of 40 opened | `card-contradicts…` |
|---|---|---:|---:|
| `f436fe3` (r7) | no cross-tier check | 38 | — |
| `e3f5d7f` (r8, as first written) | fired on elaboration | 23 | 15 (37%) |
| `7676b59` (r8 corrected + r10) | contradiction only | 34 | 5 (12%) |
| `52a5e30` (r12 + r14) | clock anchoring, card-scoped dates | 33 | 14 (35%) |

The r14 rise from 12% to 35% is the clock check becoming able to see cards that
print a time and no date — and reading those 14 is what found the bare-face
defect. **A number is not a result until you read the sentences under it**: this
is the third time in this ticket that the count moved as predicted and the
prediction was still concealing a wrong rule.

### 13r. Round 16 — the boundary's inside, and a sentence that was true of the wrong case

Three of four seats APPROVE. Two blocking (openai/attacker-smuggle) and one NIT
(gemini/spec-vs-contract), all three reproduced against `c70f547` first.

**(1) The card boundary had no inside.** `sections[:len(subject)] == subject` is
a PREFIX test and that was deliberate at r6 — a card's own
`<section class="details">` holds its own date. It also meant a promo card
NESTED inside the main `<article>`, after the real `<h1>`, was this happening's:

```
PRE-FIX  when=2026-12-25T20:00:00  place='The Other Room'  codes=()
```

Told apart by the split ladder's own discriminator, the one r4 already uses for
places: **a card that links to another happening's permalink is that
happening's card.** Committed identity table, no chrome words, no title match,
no new data. Only sections nested INSIDE the card are eligible — the article's
own "see also" link would otherwise mark the whole article foreign and cost the
page everything, which is its own test arm.

| | result |
|---|---|
| nested promo linking to another happening | refused, both fields |
| the same, card states its own date too | the card's date wins; promo excluded |
| a link at the card's own level | the card keeps its date (its place is refused by r4's older rule) |
| the card's own `<section class="details">` | still the card's, r6 unchanged |

**Not closed, and recorded as R-114:** a nested block with NO link. That is
R-112's residual one level in, and the two substitutes are refused on this
record twice over. The row is bounded **against the harm** this time rather
than the mechanism — the `deferred-trust-work` lesson from R-112 and R-113,
both of which this ticket had to reopen — and it names the four live guards
that stand between the residual and a wrong field, plus the one shape that
survives all four.

**(2) A sentence that was true of the case it was written for and false of the
one it guarded.** `event_scoped` returned True for every `ics` hit, because "a
calendar file served at this address is this happening's". But
`same_page_dates` runs over the whole DOCUMENT, so a DTSTART printed inside an
HTML page — a download widget, an "add to calendar" block, a related event —
was scoped unconditionally and won the tier over every card and plumbing check:

```
PRE-FIX  when=2026-12-25T20:00:00  carrier='ics'  codes=()
```

The test is now what the BODY IS (`BEGIN:VCALENDAR`), not what a fragment
inside it looks like. A real `.ics` response still dates the row by
construction; an ICS-shaped date inside HTML is a document-level carrier like
any other and earns its scope positionally. **Third instance in this ticket of
a comment claiming a mechanism the code did not have** (r4's segment ownership,
r12's document-level carriers, this).

**(3) NIT taken:** `_names_within` was written in one direction at r15 — the
card's block containing the node's name — so a desk whose markup carries the
address (`location.name = "TexARTS 1110 S RR 620"`) beside a card printing plain
"TexARTS" would have read as contradicting itself. The question is "do these
name the same place" and neither side is privileged about how much it says, so
it is symmetric now.

**Housekeeping in the same pass:** `_href_of` is one definition of "is this a
link", used by both scanners, because they now both need it and two spellings
is the class this ticket has paid for six times; and `_labelled_places`, left
unused by the change, is deleted rather than kept as a second un-scoped way to
ask for a page's places.

## 14. What this ticket did NOT do

* No Tonight redesign, no catalog upsert, no `ai_extract` change, no new vendor,
  no login, no Planomato, no touching PRs #230/#231/#232.
* The LIST walk's 40-page cap is unchanged (`--max-pages`); the new
  `--follow-budget` is a separate cap on event pages.
* Nothing is written or promoted. `--write` still needs `--real` and a DSN, and
  neither this run nor that workflow passes either.
