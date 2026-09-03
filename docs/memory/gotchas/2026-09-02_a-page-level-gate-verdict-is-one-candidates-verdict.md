# A page's gate verdict is its FIRST candidate's verdict — never the page's

`worker/orchestrator.py::_process_fetched_page` extracts N candidates from a
page, then gates ONE of them: `candidate_id = outcome.candidate_ids[0]`. That
single verdict becomes `PageOutcome.decision` (`held` / `escalated` /
`ready_to_promote`) and everything downstream reads it as if it described the
page. The rest of the candidates are stamped later, by the backlog sweep, and
at the moment the loop is looking at them they may carry no verdict at all.

This is fine for what it was built for — the run report's terminal bucket — and
wrong for anything that acts per LISTING. A calendar of forty shows carries one
PASS that says nothing about the other thirty-nine, so a page-level PASS can
authorize a change to a row whose own evidence the gate would have escalated.

**The rule that came out of it (Session Contract #55):** treat a page-level
verdict as a PRECONDITION and never as a licence. Anything that acts on one
listing asks the gate about THAT listing —
`worker/listing_update.py::gate_passes_for` re-runs the same `evaluate_gate`
over the candidate's real stored extraction and evidence signals, and fails
closed (returns False) on any error.

**And do not read `event_candidate.status` instead.** It is a stamped value: it
can be stale, an ops action can have moved it, and for every candidate after
the first on a multi-event page it may never have been written. Re-compute.

Related: the same session found that `event.title` exists (migration 0010, not
0001) and that the two published-event readers disagree about which statuses
are visible (R-093) — both are the kind of thing worth checking against the
schema and the reader rather than assumed from a nearby file.

## Two more from the same PR, both caught by the panel and not by me

**A repeated title is not an identity.** Normalized-title equality looks like a
safe match until you remember that recurring listings — "Open Mic", "Trivia
Night", "Sunday Service" — publish that exact title on every occurrence. Match
on title alone and the moment the published night rolls off a calendar, the
next occurrence becomes a single confident hit and you rewrite the published
row to the wrong night. Any matcher keyed on a human-readable label needs a
second axis (here: time proximity, `MAX_TITLE_ONLY_RETIME`), and "too far to be
the same one" must be its own outcome — neither a match nor an absence.

**"The extractor returned nothing" is not "the source says nothing".**
Extraction is the one probabilistic stage in this pipeline, so a model that
skips a listing produces a result byte-identical to a genuinely removed one.
Any inference FROM ABSENCE has to be corroborated against the deterministic
artifact — here the raw fetched page text (`title_still_on_page`), checked
without a model. The general rule: never let a negative conclusion rest on an
AI's silence when the raw input is still in hand.

Both defects had passing tests around them. The tests asserted the guard I had
thought of (a truncated calendar cannot cancel) and said nothing about the two
I had not. A green suite is evidence about the cases you imagined.

## And a third, which is the pattern behind the other two

**Gate the evidence for the BIGGER action at least as hard as for the smaller
one.** The update path required the matched listing's own gate PASS from the
start. The cancel path — which takes a row off the live feed, a strictly larger
user-visible action — rested on bracket timestamps that came straight out of
the extractor with no gate at all. Nobody designed that asymmetry; it appeared
because the two branches were written at different moments and only the first
one had "what licenses this?" in mind.

The check that would have caught all three findings, and is worth running on
any guard: **list every input the decision rests on, and ask of each one
whether it is validated to the standard the decision deserves.** A guard is
only as strong as its least-validated input, and the inputs that get missed are
the ones that feel like context rather than evidence — the other listings on
the page, the raw text, the title.

## Round three: a shared key is not an identity

Two events at the same venue at 8pm is not a collision to design around — it is
Tuesday at a multi-room venue. Matching a published row to a freshly parsed one
on start-time equality treated that as identity, so a *different* band's
listing could rewrite the published row under its name. The gate PASS on the
parsed listing proves that IT is real; it proves nothing about it being OURS.

The general shape, and it is the same one as the recurring-title finding a
round earlier: **when you match two records on a field that is not unique,
"one hit" is not "the right hit".** Titles repeat across occurrences; start
times repeat across rooms. Either way the fix is the same — a non-unique match
needs a second axis, and when no second axis exists the honest answer is
ambiguous, not a guess.

Following it through cost a feature: `title` is in the founder's enumeration
and the loop now never writes it, because a rename and a replacement are
indistinguishable on same-page evidence alone (R-095). That is the right trade
— one of the two possible outcomes puts a fabricated name on a public listing —
but it is worth noticing that the guard was only reachable by giving something
up, and that "keep the feature and add a heuristic" was the tempting wrong turn.

## And a reminder about raw HTML

Any text check against a fetched page must resolve the markup first. `Rock &amp;
Roll` does not contain "Rock & Roll" once punctuation is stripped — `&amp;`
normalizes to the word "amp". Titles with an ampersand are ordinary, so this was
the common case, not an exotic one. Tags become SPACES, never nothing, or a
title split across two table cells fuses with its neighbour's words into a match
that was never there.

## Round four: an evidence row is an attestation, so every column must be real

Two findings, one lesson. The `candidate_evidence` row this path wrote on an
update had a `quote` column filled with the adjudicator's own sentence
("re-check <run>: <why>") and a `source_class` that fell back to
`"venue_calendar"` when the caller supplied none.

Both looked like reasonable defaults while writing them. Both were fabrications
in a table whose entire purpose is to attest to something that happened:

- `quote` holds text FROM THE PAGE — `worker/ai_extract.py` puts the listing's
  own block there. Filling it with system prose means anything that surfaces a
  quote shows a person words the venue never published. Empty is honest; the
  reason belongs in `audit_log`.
- `"venue_calendar"` is an ANCHOR class in `worker/gating.py`. Defaulting to it
  silently upgraded unknown provenance to the strongest tier in the trust
  vocabulary, on a row attached to a published-data mutation. The listing's own
  class is the only honest value, and when there is none the honest move is to
  write no row at all.

**The rule: never reach for a default in a table that attests.** A plausible
default in a provenance record is a claim nobody made. "No row" and "empty
field" are both available and both true; a filled-in guess is neither.

## Round six: identity was checked in one direction, and in one alphabet

Two findings, and the same underlying habit: a rule that reads correctly for
one row, one page, one script — and turns into a *confident wrong answer* the
moment reality is slightly wider than the fixture that shaped it.

**Cardinality has two directions.** The adjudicator asked "how many listings on
this page match this published row?" and refused when the answer was more than
one. It never asked the mirror question: "how many published rows does this
listing match?" A page holding two occurrences of a recurring night that
returns only the later one gives BOTH rows exactly one match — the same one.
Each row passes the one-way check alone, so the earlier row reads it as "the
page moved me" and is retimed onto an event that is not it. The one-way check
did not just miss the case; it *certified* it.

**Deleting a character is not normalizing it.** The title reduction was
`[^0-9a-z]+ -> space`, applied to both sides, which reads as symmetric and
therefore safe. It is not: it deletes information rather than folding it, so
`Beyoncé` reduced to `beyonc` while `Beyonce` reduced to `beyonce`, and the two
sides disagreed about a name a CMS prints either way. The absence guard then
answered a confident False about a page naming the event in plain sight — and
False is the single answer that can license a cancellation. Symmetric
destruction is still destruction.

**The rule: a guard whose failure mode is a CONFIDENT answer needs its inputs
attacked, not just its logic.** Both of these had correct logic over inputs
that had already lost the distinction the logic depended on. Ask of any
identity test: what pairs does my normalization make indistinguishable, and
what happens when one page shows me fewer of something than the catalog holds?

The fixture that hid both was the same shape — one published row, one page, one
alphabet. A fixture with two rows would have caught the first; a fixture with
one accent would have caught the second. Neither needed a cleverer test, only a
less tidy one.

## Round seven: I recorded a limitation instead of fixing it, and the reasoning was wrong

The r6 fix folded accents by deleting the combining marks in the Unicode
combining-diacritic *blocks* — Latin, Greek, Cyrillic. Marks outside them
(Hebrew niqqud, Arabic harakat, Indic matras) still fell through to the
punctuation pass and became spaces, splitting a word in half.

I noticed that, judged it a coverage defect, and opened **R-096** saying it was
"in the safe direction... never a wrong mutation". The seat blocked on it and
was right: a needle split by a mark-turned-space produces a confident
`title_still_on_page` **False**, and with a gate-passed bracket that marks a
still-listed event `cancelled`. It was a wrong mutation, on the cancel path,
in the exact class this PR exists to prevent.

Two lessons, and the second is the one that generalizes:

**The register is for limitations you have PROVEN bounded, not for ones you have
argued are bounded.** Recording is a real mechanism and it did its job — the
entry named the residual precisely enough for a reviewer to attack it. But the
entry also carried a conclusion ("never a wrong mutation") that I had reasoned
to rather than tested. If a residual's safety claim has no test behind it, the
honest options are to write the test or to fix the residual, not to write the
claim down and move on.

**An enumeration that looks complete is the defect.** Twice on this file: first
`[^0-9a-z]` ("the letters I can think of"), then a list of combining blocks
("the marks I can think of"). Both looked exhaustive while reading them. The
fix both times was to stop enumerating and ask the library: `unicodedata` knows
what a mark is. And the trap inside that fix — `unicodedata.combining()`
returns **0** for spacing (Mc) and enclosing (Me) marks, so the obvious test
silently covers Latin and misses the scripts that need it most. The *category*
is the right question, and Mc must be KEPT rather than folded, because a
Devanagari vowel sign carries a vowel.

## Round seven, second half: `coalesce` means a partial write is a whole row

`_UPDATE_SQL` writes with `coalesce`, so a diff naming only `start_time` keeps
the published `end_time`. Every test asked "is this field right?" and none
asked "is the ROW right afterwards?" — so a row published 20:00-22:00, moved by
its page to 23:00 with no new end, would have been written as 23:00-22:00.

The table in `docs/evidence/` had been demonstrating that very mutation as a
headline `yes` row for five rounds, and I had read it many times.

**The rule: when a write is partial, assert the invariant on the RESULT, not on
the delta.** The test that catches this is not another fixture; it is the one
that enumerates published/parsed combinations and asserts that whatever an
update writes, the pair the row ends up with is a window the page stated.

## Round eight: three records ending at the same unlock was the finding

Both openai seats blocked on one defect from opposite sides — a same-title
listing at a different hour moving a published `start_time`, and a same-title
listing with no time attaching an `end_time`. Both reduce to: **a title is not
an occurrence.** A venue that runs the same show twice in an evening makes "the
page moved it" and "this is the other one" indistinguishable, and the r6
one-to-one rule only catches it when both occurrences are already published,
which a young catalog rarely has.

The fix removed a capability: a title-only match now writes nothing, and
`start_time` became unwritable by construction. Eighteen existing tests went
red, which is an honest measure of how much of the module had been resting on
that identity.

**The lesson is not in the fix, it is in the pattern nobody read.** Three
separate records — R-094 (no retime beyond 12h), R-095 (no title ever written),
R-097 (no retime when two rows claim one listing) — had already been opened over
five rounds, each with a different proximate cause, and *every one of them ended
at the same resolution trigger: a stable per-listing identifier*. Three entries
converging on one unlock was the design telling us the anchor was missing, and
it was legible after the second. Instead each round treated its finding as
local, patched the case in front of it, and opened another record ending in the
same place. The panel found the fourth instance before we read the pattern.

**The rule: when a second record resolves to the same trigger as an earlier one,
stop and ask what is actually missing.** Records are a register, but they are
also data about the design. Two entries sharing an unlock is a coincidence worth
noting; three is a missing primitive, and continuing to add narrow guards around
it is more expensive than building it. `docs/RECORD.md` should be read
column-wise — down the resolution triggers — not only row-wise when something
breaks.

The counter-move is mechanical, not a resolution: before opening a record, grep
the register for its trigger. If the trigger already appears, say so in the new
entry and name what the shared unlock is, so the next reader sees the cluster
instead of three unrelated-looking rows.

## Round nine: one function, two questions, opposite safe directions

Third finding on the same title reduction in three rounds. r6: it deleted
non-ASCII letters. r7: it folded only the combining ranges I had listed. r9:
it called every `Mn` mark optional — but the Devanagari virama and nukta are
`Mn` and carry meaning, so `नुक्कड़` and `नुक्कड`, different words, collapsed
to one identity and could write an end time onto the wrong published event.

The first two fixes were both *better answers to the wrong question*. There was
never one right amount of folding, because the reduction served two callers
whose dangerous answers point in opposite directions:

- The **absence guard** fails badly on a false NO: a page naming the event reads
  as silent, and with a gated bracket that cancels a live row. Fold hard.
- **Identity** fails badly on a false YES: two listings that are not the same
  event get treated as one, and something gets written to a published row. Keep
  everything.

Folding harder fixed the first and worsened the second; that is why each round's
fix produced the next round's finding. The answer was to stop asking the text
what it should be reduced to and start asking the caller what it is deciding.

**The rule: when one helper serves two callers, check whether their failure
modes point the same way.** If a false positive is cheap for one and expensive
for the other, they do not share a helper — they share a NAME, which is worse,
because the shared name hides the conflict and every tuning of it trades one
caller's safety for the other's. Split on the question, not on the data.

The signal was available without the panel: three consecutive findings on one
function is not three bugs, it is one design error being approached from
different sides.
