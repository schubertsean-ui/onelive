# Confirmed listing update — the fail-closed decision table

**Session Contract #55, 2026-09-02.** Generated from fixtures, not typed:
every row below is a real `worker.listing_update.adjudicate_page` decision,
rendered by `worker.listing_update.render_decision_table`. Regenerating it is
`tests/test_fair_crawl.py::test_the_founders_listing_table_from_fixtures`
(four of these rows, driven end to end through `run_loop`) plus
`tests/test_listing_update.py` (all of them, at the adjudicator).

Fixtures rather than a smoke run, per Operating Law rule 4 ("Sandbox 403 is
not a product failure. Use fixtures + CI") and the founder's own "Table from
fixtures or smoke". The armed-cron smoke run that re-binds this head's runtime
is a separate artifact (`docs/evidence/ARMING_SMOKE_RUN.json`) and proves the
runtime EXECUTES; this table proves what it DECIDES.

`check result` is the fail-closed verdict from
`worker.crawl_state.classify_recheck` — `present`, `absent`, or `no` (nothing
was learned). Read the three "yes" rows against the twenty-seven "no" rows: the
default is no mutation, and confirmation is the exception that has to be earned.

**Round 8 removed a capability, and it should be read before the table.** Both
openai seats blocked on the same thing from opposite sides: a listing matched
only by its TITLE had been treated as the same occurrence — enough to move a
published start time, or to attach an end time when the page stated no time at
all. A venue that runs the same show twice in an evening (a screening, an early
and late set, a repeating tour slot) makes "the page moved it" and "this is the
other one" indistinguishable, and a catalog holding one of the two occurrences
sees a single clean match for the other. The one-to-one rule from round 6 only
catches this when BOTH occurrences are published.

So a title-only match now writes nothing. It still keeps a row from reading as
absent — which is what it is genuinely evidence of — and that is all it does.
**The consequence is that `start_time` is unwritable by construction**, since
the only writing match is a shared start minute and a shared minute has no start
change. The founder's "update time" survives as an end-time correction on a
listing that agrees with us on both title and start minute; cancel, postpone and
the whole refusal machinery are untouched. Recorded as R-099, with the unlock
(a stable per-listing identifier) that R-095 and R-097 are already waiting on.

**Count correction, stated rather than quietly fixed:** earlier versions of this
page said "three yes rows against the nineteen no rows" while the table below
them held four and eighteen. The table was right and the sentence was wrong,
twice, in opposite directions. Nothing about the decisions changed; the
arithmetic describing them did. The table below was regenerated from scratch
this round by a fixture script written independently of the one that produced
the earlier version, and it reproduces all twenty-two of the original rows
character-for-character — which is the check that says the regeneration is
faithful rather than merely new. The three rows it adds are the round-6 refusal
class, an accent case, and the off-site verdict, which `classify_recheck` has
always produced and this enumeration had simply never listed.

**Round 7 changed two of its own rows, which is the point of regenerating it.**
The table's headline mutation — "page moved it to 3am" — was published
20:00-23:00 and moved to 03:00 by a page that stated no new end. That row was
demonstrating a mutation this PR should never have made: written through
`coalesce` it becomes 03:00-23:00, a window that ends before it begins. The
adjudicator now refuses it, so the row moved from `yes` to `no` and two honest
mutation rows replaced it — one where the page states the whole window, one
where the published row carries no end to contradict.

```
event                                                 | check result | mutated? | why
------------------------------------------------------+--------------+----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Nightjar — page states a later end for tonight's show | present      | yes      | confirmed same-page change, gate PASS on that listing: end_time
Nightjar — page moved it to 3am and says when it ends | present      | no       | the page carries this row's title at a different time, and a repeat cannot be told from a move on same-page evidence — last good row stands
Nightjar — moved, but the page states no end          | present      | no       | the page carries this row's title at a different time, and a repeat cannot be told from a move on same-page evidence — last good row stands
Nightjar — the page's own times are not a window      | present      | no       | the page's own times do not make a window (it would end at or before it starts) — last good row stands
Nightjar — an untitled listing holds its 8pm slot     | present      | no       | something on the page holds this row's start time with no title to check it against, so its absence cannot be read cleanly — ambiguous; last good row stands
Nightjar — page renamed it at the same time           | present      | no       | a different event holds this row's start time on the page, so its absence cannot be read cleanly — ambiguous; last good row stands
Nightjar — a different band holds its 8pm slot        | present      | no       | a different event holds this row's start time on the page, so its absence cannot be read cleanly — ambiguous; last good row stands
Nightjar — page unchanged                             | present      | no       | the page still says exactly what we published — no change
Nightjar — page dropped its end time                  | present      | no       | the page still says exactly what we published — no change
Nightjar — moved, but the gate declined that listing  | present      | no       | the page states a change, but the trust gate did not PASS that listing's own evidence — last good row stands
Nightjar — two listings match it                      | present      | no       | 2 listings on the page match this row on title or time — ambiguous; last good row stands
Nightjar — absent, page brackets its date             | present      | yes      | absent from a clean parse of the page that defines it, its title is absent from the page's own raw text, and the page's GATE-PASSED listings bracket its date — confirmed gone; marked cancelled, row kept with its evidence
Nightjar — extraction missed it, page still names it  | present      | no       | the page still names this listing but the extraction did not return it — an extraction miss is not a cancellation; last good row stands
Nightjär — the page spells it with an umlaut          | present      | no       | the page still names this listing but the extraction did not return it — an extraction miss is not a cancellation; last good row stands
Open Mic — only next week's occurrence listed         | present      | no       | the page still lists this title, but at a date too far off to be the same occurrence — ambiguous; last good row stands
Open Mic — one listing, two published nights          | present      | no       | another published row on this page matches the same listing — one listing cannot be two rows; ambiguous; last good row stands
Nightjar (no published end) — doors moved one hour    | present      | no       | the page carries this row's title at a different time, and a repeat cannot be told from a move on same-page evidence — last good row stands
Nightjar — page states no time for it at all          | present      | no       | the page carries this row's title at a different time, and a repeat cannot be told from a move on same-page evidence — last good row stands
Nightjar — absent, calendar stops before its date     | present      | no       | not on the page, but the page's own gate-passed listings do not reach this date — a short calendar, or one the gate did not confirm, has not said this event is gone; last good row stands
Nightjar — page loaded but listed nothing             | present      | no       | page verified but it produced no listings this read — nothing to compare; last good row stands
Nightjar — absent, but the bracket failed the gate    | present      | no       | not on the page, but the page's own gate-passed listings do not reach this date — a short calendar, or one the gate did not confirm, has not said this event is gone; last good row stands
Nightjar — defining page 404                          | absent       | yes      | the defining page returned a clean 404 — confirmed gone; marked cancelled, row kept with its evidence
Nightjar — fetch timed out                            | no           | no       | unconfirmed — fetch failed (no status) — last good row stands
Nightjar — rate limited (429/503)                     | no           | no       | unconfirmed — rate-limited (429/503) — last good row stands
Nightjar — closed door (401/403)                      | no           | no       | unconfirmed — closed door (401/403) — last good row stands
Nightjar — tick budget deferred it                    | no           | no       | unconfirmed — budget or politeness deferred the check — last good row stands
Nightjar — landed off-site                            | no           | no       | unconfirmed — landed off-site — a different source; last good row stands
Nightjar — page parsed, gate HELD                     | no           | no       | unconfirmed — page fetched and parsed, but the trust gate did not confirm it (held) — last good row stands
Nightjar — page parsed, gate ESCALATED                | no           | no       | unconfirmed — page fetched and parsed, but the trust gate did not confirm it (escalated) — last good row stands
Nightjar — sensor rejected the page                   | no           | no       | unconfirmed — page fetched but never reached the gate (sensor_rejected) — last good row stands
```

## Reading the three mutations

| row | why it is allowed to change a published listing |
|---|---|
| page states a later end for tonight's show | The page agrees with us on the title AND the start minute — two events at one venue sharing both are the same event by any reading — and states a different end. The MATCHED listing's own trust-gate verdict was re-computed and PASSed, and the resulting window is one the page stated. Writes `end_time`; the row stays `scheduled` and visible. |
| absent, page brackets its date | Four things at once: the page loads, the raw page text no longer names the listing, its own listings bracket this date, and **those bracketing listings each pass the trust gate**. Writes `status='cancelled'`; the row is KEPT. |
| defining page 404 | The founder's 2026-09-02 overrule (`docs/memory/decisions/2026-09-02_404-of-defining-url-marks-the-listing-gone.md`). Writes `status='cancelled'` and nothing else — a page that is gone cannot state a new time or title. The row is KEPT. |

## Reading the twenty-seven refusals

Fourteen of them are the ones worth arguing about, because each is a case where
something DID change and the loop still refused. **Thirteen of the fourteen were
caught by the adversarial panel on this PR, not by me** — every one was a real
defect on the published-data path, all are fixed here, and all are pinned by
tests:

- **"moved, but the gate declined that listing"** — R-091(a). A page's gate
  verdict is the verdict of its FIRST extracted candidate, so on a
  forty-listing calendar it says nothing about the other thirty-nine. The
  page-level PASS is a precondition; the licence is the matched listing's own
  verdict.
- **"absent, calendar stops before its date"** — the false-absence guard. A
  calendar showing the next ten shows legitimately stops mentioning a show
  three months out. Cancelling on that would take a real event off the live
  feed on evidence that was never about it.
- **"page parsed, gate ESCALATED"** — the exact case the adversarial panel
  named on PR #213. Conflicting start times, a schema-invalid extraction, a
  private/RSVP listing or dedupe ambiguity are all reasons to distrust what
  this read says a listing now is.
- **"only next week's occurrence listed"** — normalized-title equality alone
  was treated as identity. `Open Mic` repeats its exact title weekly, so once
  the published night rolls off the calendar a title-only match is a single
  hit, and the row was retimed to the wrong night. A title match beyond
  `MAX_TITLE_ONLY_RETIME` (12h — a *daily* series' next occurrence is exactly
  24h away) is not an identity, and it is not an absence either.
- **"extraction missed it, page still names it"** — the absence branch read
  "the extractor did not return this event" as "the page no longer says it".
  Extraction is the one probabilistic stage in the pipeline; a model that skips
  a listing looks exactly like a removed show. Absence is now corroborated
  against the raw fetched text, deterministically and without a model.
- **"page renamed it at the same time"** and **"a different band holds its 8pm
  slot"** — the same finding from both sides. A shared minute was treated as
  identity even when the titles contradicted, so a *different* event at 8pm
  could rewrite the published row under its identity; a multi-room venue does
  that nightly. Both are `MATCH_COLLISION` now: no rewrite, and no cancel
  either, because an event we cannot distinguish from what the page shows has
  not been shown to be gone. The cost is that `title` is never written at all
  (R-095) — a rename and a replacement are indistinguishable without a stable
  per-listing identifier.
- **"absent, but the bracket failed the gate"** — the asymmetry pointed the
  wrong way. An update already needed the matched listing's own gate PASS,
  while a cancel — the larger, user-visible action — rested on bracket
  timestamps straight from the extractor. A garbled or hostile extraction that
  omits the real event and emits plausible earlier+later listings around its
  date would manufacture the very coverage window the guard demands. The
  bracket must now be gate-passed on both sides.
- **"one listing, two published nights"** — cardinality was checked in one
  direction only: how many listings match this row, never how many rows match
  this listing. A page holding two occurrences of a recurring night that
  returns only the later one gives BOTH published rows exactly one match — the
  same one. The earlier row reads it as "the page moved me" and is retimed onto
  an event that is not it, while the later row keeps its own time, so the
  catalog publishes a real show at an hour nobody announced. A page listing is
  one listing: if two rows claim it, it identifies neither.
- **"the page spells it with an umlaut"** — the title reduction DELETED every
  non-ASCII letter rather than folding it, so a published `Beyoncé` reduced to
  `beyonc` while the page's `Beyonce` reduced to `beyonce`. The absence guard
  then answered a confident *False* about a page that was naming the event in
  plain sight — and a confident False is the single answer that can license a
  cancellation. Accents now fold onto the letters they are written with, and
  letters with no ASCII form (Cyrillic, CJK) are kept instead of erased, so
  `Кино Night` stops reducing to the needle `night`. **Fixed twice**: the first
  fix enumerated the combining ranges I could think of and still turned Hebrew,
  Arabic and Indic marks into spaces, splitting those words in half. The rule is
  now asked of Unicode rather than listed — optional marks (Mn, Me) fold away,
  spacing vowel signs (Mc) are kept because they carry a vowel — and a test
  fails if a hand-listed range ever comes back.
- **"moved, but the page states no end"** — `_UPDATE_SQL` writes with
  `coalesce`, so a change naming only `start_time` KEEPS the published end. A
  row published 20:00-22:00 whose page now says 23:00 would be written as
  23:00-22:00: an event that ends before it begins, which a reader using
  `end_time` treats as already over. The page must state the whole window it is
  changing — and the test is what the page STATED, not what changed, so a read
  that restates an unchanged end still updates.
- **"the page's own times are not a window"** — a gate PASS proves a listing's
  evidence was corroborated, not that its fields are sane. An extraction that
  emits an end before its own start passes a gate that never asked the question.
- **"page moved it to 3am and says when it ends"**, **"moved, but the page
  states no end"** and **"page states no time for it at all"** — the round-8
  narrowing above, in its three shapes. A title is not an occurrence. Note the
  first of the three was a `yes` row one round ago and the second was refused
  for the WRONG reason (the window rule) while the identity underneath went
  unexamined; the window rule was right about its case and simply not the
  deepest thing wrong.
- **"an untitled listing holds its 8pm slot"** — a shared minute was an identity
  whenever nothing *contradicted* it, and a listing with no title contradicts
  nothing. But it confirms nothing either: the gate PASS proves the anonymous
  listing is real, never that it is ours, and a multi-room page produces
  untitled listings as a matter of course. It now identifies nothing AND blocks
  the cancel, because something sitting on our start time that we cannot tell
  apart from us is a reason to say nothing.

## What no row can do

No verdict, no evidence and no confidence level deletes a published row.
`worker.crawl_state.may_delete_listing` returns False for every input
including ones nobody has written yet, `worker/listing_update.py` contains no
`DELETE` and no `INSERT INTO event`, and both facts are pinned structurally
rather than by prose.

## The live re-bind runs

Nine founder-authorized dry smokes, one per adversarial round, each binding
the head the panel had just judged. All recorded in
`docs/evidence/ARMING_SMOKE_RUN.json`; the current binding is the last.

| run | head | shape | what it showed |
|---|---|---|---|
| [33696784882](https://github.com/schubertsean-ui/onelive/actions/runs/33696784882) | `6231147` | 2 sources, 29 candidates, $0.0986→$0.2457, 75.4s | the dry switch resolves and prints; runtime loads the listing path |
| [33698783298](https://github.com/schubertsean-ui/onelive/actions/runs/33698783298) | `d29dc5c` | 2 sources, 26 candidates, $0.5991, 123.3s | **the R-091(a) tightening fired live** |
| [33700477027](https://github.com/schubertsean-ui/onelive/actions/runs/33700477027) | `9632882` | 2 sources, 50 candidates, $0.2336, 167.5s | **a real HTTP 304**, and the discover queue |
| [33702677748](https://github.com/schubertsean-ui/onelive/actions/runs/33702677748) | `0d013e1` | 2 sources, 60 candidates, $0.3196, 177.1s | **the gate's HOLD branch** — the last outcome |
| [33704092379](https://github.com/schubertsean-ui/onelive/actions/runs/33704092379) | `70a5b42` | 2 sources, 8 candidates, $0.0426, 35.0s | HOLD and the fingerprint skip again, on new sources |
| [33705264950](https://github.com/schubertsean-ui/onelive/actions/runs/33705264950) | `42b17b3` | 2 sources, 39 candidates, $0.1895, 132.0s | ESCALATE again, on a new source — no skip, both pages read |
| [33707495850](https://github.com/schubertsean-ui/onelive/actions/runs/33707495850) | `1a0f12b` | 2 sources, 13 candidates, $0.0561, 44.4s | ESCALATE on a third venue type, and a **second live 304** |
| [33708942367](https://github.com/schubertsean-ui/onelive/actions/runs/33708942367) | `18d9de4` | 2 sources, 36 candidates, $0.2710, 112.3s | a fourth ESCALATE, a third 304, and **14 live date refusals** |
| [33710564656](https://github.com/schubertsean-ui/onelive/actions/runs/33710564656) | `23ad24e` | 2 sources, 67 candidates, $0.2580, 224.8s | a **PASS control beside a fifth ESCALATE**, and 24 date refusals |

Every one printed the switch, from the resolved env and then from the loop:

```
LISTING_UPDATE_MODE: dry
listing-update writer DISABLED for this run (dry): no published row can be
updated or marked, whatever any page says.
```

The `listings_updated: 0 / listings_marked_gone: 0` counters agree, and remain
**consistency rather than evidence**: every tick reported `0 event-proximity
page(s)` due, so they would read zero with the writer armed too. The DISABLED
line is the proof.

### All three gate outcomes, observed on real pages

This is the R-091(a) fix demonstrated live rather than in fixtures, and it took
two runs to collect because each tick only shows what its own sources did.

```
run 33698783298   Thinkery                       | present | gate PASS
run 33698783298   Historic Scoot Inn             | no      | gate ESCALATED
run 33702677748   Waterloo Greenway Conservancy  | present | gate PASS
run 33702677748   Meetup                         | no      | gate HELD
run 33704092379   Asian American Resource Center | no      | gate HELD
run 33705264950   Paramount Theatre (Austin)     | present | gate PASS
run 33705264950   Blanton Museum of Art          | no      | gate ESCALATED
run 33707495850   The Contemporary Austin        | present | 304, unchanged
run 33707495850   Kingdom Nightclub              | no      | gate ESCALATED
run 33708942367   Come and Take It Live          | present | 304, unchanged
run 33708942367   Emo's Austin                   | no      | gate ESCALATED
run 33710564656   Ballet Austin                  | present | gate PASS
run 33710564656   Elephant Room                  | no      | gate ESCALATED
```

The later rows are repeats, and repeats are worth recording: a behaviour seen
once on one venue could be that venue. **Both** declining outcomes are now
ordinary — HOLD on a community platform and on a city-hosted calendar,
ESCALATE on a music hall, an art museum, a nightclub, a large music venue and a
jazz club — five venue types with nothing structurally in common. R-091(a) rests on exactly that: a
declining verdict has to be a common thing live pages produce, or the fix
guards nothing.

The Contemporary Austin row is the other half of the same point, from the
opposite direction: a **real HTTP 304** (`not_modified: 1`,
`skipped_unchanged: 1`, zero model calls for that source) reading as
`verified_present` through the byte-identical branch. That is the second live
304 after run 33700477027's Bandsintown, and a third followed on Come and Take
It Live, so the cheap-confirmation path is ordinary too.

One more thing runs 33708942367 and 33710564656 show, on a mechanism this ticket
did not build but depends on: the same-page-date resolver refused **fourteen**
separate `start_time` claims on the Emo's Austin page and **twenty-four** on
Ballet Austin's summer-intensive schedule, most of the latter refusing start and
end together, with `ambiguous-same-page-dates` — storing NULL and keeping each
raw value and reason in provenance. A page whose listings do not pin their own
dates yields no times rather than guessed ones: the fail-closed path running
loudly, at volume, on two real calendars.

Run 33710564656 also carries the **PASS control** the previous two bindings
lacked, and its own wording is worth quoting: Ballet Austin came back
`PASS (trust gate); awaiting authenticated ops promote`. That trailing clause is
the publication invariant stating itself in live output — a gate PASS does not
publish, it waits for the authenticated promote.

**Historic Scoot Inn** fetched fine, parsed fine, produced **25** candidates —
then escalated: *"conflicting start_time across evidence; dedupe-ambiguity hint
present."* **Meetup** fetched fine, parsed fine, produced **12** candidates —
then held: *"Insufficient corroboration (have 1; need 2)"*, because a community
platform is third-party in `worker/gating.py` and one of it alone is hearsay.
**The Blanton** fetched fine, parsed fine, produced **15** candidates — then
escalated on the same conflicting-`start_time` reason, on a museum tour
calendar that has nothing structurally in common with a music hall.

**Under the rule this PR replaced, both would have read `verified_present`,**
because both parsed cleanly — and either could have licensed a published
update. That is exactly the case the PR #213 panel named: "a parsed-but-
escalated page cannot accidentally authorize a misleading published update."
Both arrived unprompted, on real Austin pages, on ordinary two-source ticks.

### What the third run closed (33700477027)

Two scope limits every earlier binding had carried **in writing**:

- **The 304 half fired live.** Previous evidence said the skip-unchanged saving
  had only ever been shown by a body-fingerprint match, and that the 304 half
  "still rests on hermetic and real-Postgres coverage only". Bandsintown
  answered a genuine `304 Not Modified` — `not_modified: 1`,
  `skipped_unchanged: 1`, and zero extract calls spent on it.
- **The discover queue ran.** Earlier bindings were refresh-only and said so.
  This tick reports `fetches: 2 (discovery probes: 1)`.

It also showed the per-page cost cap behaving as documented on a real page:
Mexic-Arte Museum segmented into 148 event blocks, the cap took the first 50,
and 98 were **deferred rather than dropped** (R-043).

### What none of them show

The listing-update path acting on real data. The writer was disabled in all
nine and no event-proximity page was ever due, so no published row was read
for adjudication and none could have been written. That coverage is the table
above, `tests/test_listing_update.py`, and section 8 of
`tests/test_fair_crawl.py` — the first armed tick that finds a defining page
due will be the first live exercise of it.
