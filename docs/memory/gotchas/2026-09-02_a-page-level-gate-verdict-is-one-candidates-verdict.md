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
