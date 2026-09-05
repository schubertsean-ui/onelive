# Ticket B — identity split: what changed, and how it was proven

Date: 2026-09-05 · Branch `claude/identity-split-patterns-ppi4uk` · Law:
`ONE-LIVE-ENTITY-SPLIT-LAW.md` §2 (split) and §6 (ticket B) · No `--write`,
no merge.

Every number below was printed by a command that is named beside it. Nothing
here is retyped from memory.

## 1. The defect, reproduced against the code on master

One list page: a text blob with no identity anywhere on it, two links (the
masthead and a "More" pagination link), and four events run together in prose —
the shape of the live Chronicle run this law was written from.

```
$ git show origin/master:worker/locale/desk_read.py > /tmp/desk_read_master.py
$ python /tmp/mash_repro.py      # reads that ONE page with master's reader
rows: 1
  title:       'Promoted Events'
  listing_url: https://desk.test/
notes: ['HTML rows selected by the class tier']
```

One row. Titled a heading with the events concatenated behind it. Addressed to
the SITE ROOT. That is the mash the law names (§2 live evidence: Chronicle
opened 40 pages and emitted 1 row keyed `url:https://www.austinchronicle.com`),
and "the class tier" is the splitter §2 lists under Forbidden.

## 2. What the split ladder does with the same page

`worker/locale/desk_read.py` now runs §2's ladder. On that page: no schema.org
Event, no href matching a committed identity pattern, no listing selector
committed for that door — so **zero rows** and `unsplit` in the notes, with the
note saying it is a coverage defect on that DOOR, to be answered by a pattern or
a claim.

`tests/test_identity_split.py` holds the three cases the ticket names and 28
more:

| ticket case | test |
|---|---|
| (a) two `/event/foo-1` + `/event/bar-2` -> two rows, those listing_urls | `test_two_permalinks_become_two_happenings_with_those_listing_urls` |
| (b) list page, no identity, giant blob -> zero rows, `unsplit` | `test_a_blob_with_no_identity_yields_zero_happenings_and_says_unsplit` |
| (c) a test accepting the blob as one row must go red | see §3 |

## 3. The tests that accepted the blob, and what happened to them

Two committed tests passed on master BECAUSE the guessing splitters existed.
Both went red the moment the ladder landed, before any test was touched:

```
FAILED tests/test_desk_read.py::test_a_non_iso_datetime_attribute_is_not_coerced
    read(doors["visit-austin-events"], '<ul><li><time datetime="next friday">…')
    IndexError: list index out of range        # zero rows: the page declares no identity

FAILED tests/test_desk_read.py::test_a_single_kind_door_states_that_kind_for_its_rows
    read(doors["kutx-concert-calendar"], desk_listing.html)
    AssertionError: assert set() == {'music'}  # that door commits no selector
```

Neither test was about splitting, so both were rewritten to state their own
subject on a page that declares an identity — the date rule on a `<ul
class="calendar">` (that door's committed selector), the door-scope kind rule on
a JSON-LD page. The mash itself is now pinned by
`test_the_blob_is_not_accepted_as_one_row`, which asserts `count != 1` directly,
so it cannot come back green.

## 4. Dry ingest — FIXTURE run

`$ python tools/desk_ingest.py --dry-run`

| desk | rows_n | identities | unsplit_n | mash_n | mash_blocked | 403_n | unread_n | pages read | split by |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `austin-chronicle-eventsearch` | 17 | 17 | 0 | 0 | 0 | 0 | 0 | 3 | `structured+desk_selector`, `desk_selector` |
| `do512-today` | 16 | 15 | 0 | 0 | 0 | 0 | 0 | 3 | `structured+desk_selector`, `desk_selector` |

Both desks split on rung 3, on a selector committed for that door and graded
`fixture_shape` — and every read says so in its own note ("split by the
`structured+desk_selector` rung on `div.event` (fixture_shape)"). A
`fixture_shape` reading still splits, because refusing to split until somebody
has fetched a page would make the FIRST read of every new desk a mash; what it
never does is arrive looking like a shape somebody has seen live.

These are FIXTURE counts over committed shape fixtures, and the fixtures'
manifests say every title, venue and date in them is invented. What they prove
is the SHAPE: 33 pages-worth of cards become 33 rows, not 6, and `mash_n` is 0.
Do512's `identities` (15) is one short of its `rows_n` (16) because one fixture
card states no address of its own — a row that exists without an identity, which
is Trust doctrine, not a miss.

## 5. Dry ingest — LIVE run from this sandbox

`$ python tools/desk_ingest.py --real --dry-run`

| desk | rows_n | identities | unsplit_n | mash_n | mash_blocked | 403_n | unread_n | pages read | split by |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `austin-chronicle-eventsearch` | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | — |
| `do512-today` | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | — |

**No page was read.** The sandbox's egress proxy answers 403 to CONNECT for both
hosts:

```
$ curl -sS "$HTTPS_PROXY/__agentproxy/status"
"recentRelayFailures": [{"kind": "connect_rejected",
  "detail": "gateway answered 403 to CONNECT (policy denial or upstream failure)",
  "host": "calendar.austinchronicle.com:443"}]
```

So this table is NOT evidence that Chronicle splits and NOT evidence that either
desk is empty. Both doors stay queued. The founder's acceptance numbers —
Chronicle rows ≈ events on the page, every `listing_url` a `/event/…`, `mash_n`
= 0 — need a runner with egress, and `.github/workflows/desk-split-dryrun.yml`
(added by this PR: manual dispatch, any branch, no secrets, cannot write) is the
one command that produces them.

Note the `403_n` column was 0 for Chronicle on the first run of this table and
1 for Do512, from the same wall. The reason: the transport error is truncated
for display at 200 characters, and Chronicle's URL is longer, so the digits
"403" fell off the end. A wall that reads as `0` is exactly how a walled desk
gets reported as an empty calendar, so the classification now happens on the
full error text at the fetcher, before truncation
(`tools/desk_coverage.py::live_fetcher`, `PageFetch.walled`), with a test that
only passes while the displayed reason IS truncated.

## 6. Evaluator round 1 — a real defect, in my own fix

`adversarial-review` (GPT-5.5, `attacker-smuggle` lens) returned REQUEST-CHANGES
on `worker/locale/desk_read.py:343`: the permalink rung climbed past the card to
the OUTERMOST row-shaped ancestor holding that identity alone. On a page
declaring ONE identity — a filtered page, a last page — no second identity is
there to stop the climb, so the row grew to the page wrapper.

Reproduced before fixing, on one such page:

```
rows: 1
  title:       'Promoted Events The Only Event'      <- the page heading, concatenated
  place_text:  'The Hall'
  listing_url: https://desk.test/event/only-one-1
```

That is this law's own mash, arriving on the pages nobody thinks to check. The
row is now the NEAREST row-shaped ancestor that declares this identity alone and
holds no page-level structure (`main`, `nav`, `header`, `footer`, `aside`, `h1`
— HTML's own page-level elements, not anyone's CSS convention); when none
qualifies, the anchor itself is the row, with honest holes. Same page after:

```
title: 'The Only Event' | place: 'The Hall' | when: 2026-09-11T20:00
```

Pinned by `test_a_page_declaring_ONE_identity_is_read_from_its_card_not_its_wrapper`
and `test_a_row_never_grows_to_hold_page_level_structure`. The dry-ingest tables
are unchanged by the fix — it touches only where a permalink row ENDS.

The other three panel lenses (`absence-only`, `dataflow-taint`,
`spec-vs-contract`) returned APPROVE on the same head.

## 7. Evaluator round 2 — two more, both real, both in the permalink rung

Same panel, new head. `dataflow-taint` and `spec-vs-contract` APPROVE (and both
verified the r1 fix by name); the two openai lenses each found a distinct way to
manufacture a happening that does not exist.

**(a) A pattern matched a PREFIX of a path, so an event's own subpages became
events** (`attacker-smuggle`). Reproduced:

```
IDENTITY  .../austin/event/foo-1234567/comments
IDENTITY  .../events/2026/9/12/bright-room-quartet/tickets
IDENTITY  .../e/show-987654/refunds
```

Each has a different URL, so each entered as its own identity — one happening
published three times. A committed pattern now has to name the WHOLE path
(`IdentityPattern.matches_path`, every match position tried, one trailing slash
trimmed first). Anchoring in the matcher rather than in the table keeps the
committed rows readable — `/event/[^/]+-\d+`, exactly as the law writes it —
and applies the rule to every row anyone adds later. `_identity_of` trims the
trailing slash too, so the matcher and identity agree about what one address is.

**(b) The table covers several hosts, and any of them could declare an identity
on any page** (`absence-only`). A desk card carrying a ticket vendor's link
split into two:

```
rows: 2
   'Real Show' | None      | .../austin/event/real-show-1234567
   'tickets'   | None      | https://www.eventbrite.com/e/real-show-tickets-987654321
```

Note the second cost: `place_text` is None on the REAL row too, because a card
holding two identities can be claimed by neither. §2 tier 2 says a pattern
declares an identity "for that host family" — the PAGE's — so tier 2 now
considers only patterns covering the desk being read. After:

```
rows: 1
   'Real Show' | The Hall | .../austin/event/real-show-1234567
```

No row is demoted by this: a vendor's own pattern still splits a page on that
host when it is the door being read, and there is a test for exactly that.

Five tests pin this round. The repo's own brand guard
(`test_no_brand_from_the_pack_appears_in_the_locale_modules`) then caught a desk
name in the comment explaining the fix — that guard's remedy text was followed
rather than the guard worked around.

## 8. Evaluator round 3 — the page's own plumbing

Three of four lenses APPROVE. `attacker-smuggle` found the last one, and it is
the mirror image of round 1: r1 bounded where a row GROWS, and that is no help
when the link should never have been a row at all.

```
<nav><li><a href="/event/foo-1">tickets</a></li></nav>
<footer><a href="/event/bar-2">Advertise with us</a></footer>
<aside><a href="/event/baz-3">Sponsored</a></aside>
```

Reproduced: **three rows**, titled "tickets", "Advertise with us", "Sponsored".
The `<li>` inside the `<nav>` is row-shaped and holds one identity, so the row
stopped there — correctly — and published anyway. A same-host permalink in the
page's plumbing is navigation, whatever it points at, so the LINK is now
refused, counted (`furniture_skipped`) and reported.

`<header>` and `<footer>` needed care rather than a blanket rule: HTML scopes
both to their nearest sectioning ancestor, so `<article class="card"><header>`
is a listing's own title bar. Treating them unconditionally as page structure
refused real cards; the first cut of this fix did exactly that and dropped the
venue printed as the header's sibling. Both the refusal and the row bound now
use the scoped rule (`_is_page_structure`):

```
furniture only         rows=0 skipped=3
card <header>          rows=1 skipped=0 -> [('Real Show', 'The Hall')]
page header + card     rows=1 skipped=1 -> [('Real Show', 'The Hall')]
```

The NIT all three approving lenses raised was real too: a non-raw docstring
holding `\d` emitted `SyntaxWarning` on every import (pytest warnings 2 -> 9).
Fixed, swept across the package, and pinned by a test so the next regex in a
docstring cannot re-bury the validate output. Warnings are back to 2.

Five tests pin this round; both dry-ingest tables are unchanged.

## 9. A red `db-integration` that was NOT this PR's, fixed anyway

`db-integration` failed once, on head `f20effb`, in
`test_a_claim_locked_row_is_not_disputed_by_a_desk`. This PR's diff touches none
of the files that test exercises (`worker/locale/desk_publish.py`,
`worker/promote.py`, `worker/candidate_store.py`,
`tests/integration/test_desk_ingest_pg.py`), and the same test passed on the two
earlier heads of this same PR. The difference between those runs was the CLOCK.

Proven without a database, because the failing assertion turns entirely on the
union key, which is pure:

```
at the CI instant (2026-09-05 22:17:58Z):
   first    : 2026-09-05~claimed room~claimed show
   corrected: 2026-09-06~claimed room~claimed show
   SAME KEY : False   <- the test asserts 'changed', which needs True
```

The test bases its instant on `now + 6h` and then corrects the clock by 45
minutes. The ingest key carries the LOCAL NIGHT, so when the base lands in the
last 45 minutes of a local day the correction crosses midnight, the key changes,
and the row publishes as a second listing instead of registering as a change.
Sweeping all 1440 UTC minutes of a day, three tests carry this shape:

```
+4h then +90m: fails at 90 of 1440 UTC minutes
+5h then +90m: fails at 90 of 1440 UTC minutes
+6h then +45m: fails at 45 of 1440 UTC minutes  (22:15Z..22:59Z — CI ran at 22:17:58Z)
```

225 minutes a day, about one run in six. "Flake" is not a root cause and a
failing test is never skipped, so the three now take their base from
`_clock_correction_base()`, which anchors to 19:00 LOCAL — five hours of margin,
a fixed hour rather than a derived one, and always at least the requested hours
ahead. Re-swept every 5 minutes across a full year of start days, crossing both
DST transitions: **0 night-crossings, 0 bases too close to now.** No assertion
is weakened; only the instant the tests start from is made deterministic.

## 10. Gates

```
$ bash tools/validate
check: trust_gate = PASS      check: lint = PASS
check: deferral_scan = PASS   check: pytest (full suite) = PASS   (2978 passed, 55 skipped)
check: staleness_check = FAIL (STATE.md not yet committed on this branch; see the PR body)
```

The full evidence block is in the PR body, pasted verbatim from
`.validate-evidence.txt`.
