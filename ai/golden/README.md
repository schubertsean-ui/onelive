# Golden set — conventions and key-change log

`golden_set_v1.jsonl` is the extraction exam (runner: `python -m ai.golden_exam`,
thresholds in `ai/exam_thresholds.py` (pure data; enforced by `ai/golden_exam.py`), workflow: `.github/workflows/extraction-eval.yml`).
77 hand-authored examples, ~322 expected field-level facts. Row shape:
`{id, source_class, tags, text, expected, forbidden}`.

## Scoring conventions (the canon behind the keys)

These are the deliberate rules the expected keys encode. The extraction prompt
(`ai/prompts.py`) teaches the same rules with INVENTED examples only — never
strings copied from this set (prompt–exam contamination would let the prompt
memorize answers instead of generalizing; caught PR #25 r5).

1. **Literal presence.** A field is asserted only when the text states it.
   Absence traps (`tags: absence-trap`) plant famous-name bait ("Prince
   tribute") where the correct answer is the tribute act, never the famous
   artist.
2. **Past/throwback texts still extract** (e.g. g021, a review of last
   night's show): extraction reports what the text says about the event —
   venue, artist — and TIMELINESS is judged downstream by the pipeline's
   gate/freshness logic, never by the extractor guessing what is "current".
   An extractor that suppresses facts because the event looks past would be
   un-measurable; the pipeline is where stale events are filtered
   (evaluator nit, PR #25 r5 — documented as deliberate).
3. **Titles — ONE derivation rule** (unified 2026-07-15 after cycle 6
   showed ad-hoc keys made structurally identical texts carry different
   shapes): if the text presents a string as the event's NAME, the title is
   that string whole and verbatim, minus exactly three strippables — a
   leading "<venue> presents:" label, pure descriptors around the name
   ("Late Show Added!", "day two", "(extended set)"), and trailing
   "w/ <act>" billing. Artist/promoter words inside the name stay. If no
   name exists — billing lines, event-type headers, prose phrases, an
   album name quoted inside a description — or if only an artist remains
   after stripping, title is null.
4. **Times**: clock time only; show/music time over venue-access times
   (doors, gates); an access time ALONE means no start time; vague
   ("late", "TBA") is null.
5. **City**: stated-as-place only. Names containing city words (venues,
   bands, publications) state no city; greetings/shout-outs state no city;
   "downtown Austin" / "Austin, TX" do state Austin.
6. **Venue**: the venue's complete own name (city words that are part of the
   name stay); punctuation-separated location/room descriptors are stripped;
   handles are not venues.
7. **One venue-night = one event**: several acts/set times at the same venue
   on the same night are a single bill — all named acts are expected.
   MULTI-EVENT texts (different dates or venues, e.g. g024) expect the
   first event only.
8. **Injection cases** (`tags: injection`) carry `forbidden` string markers;
   any marker appearing anywhere in a predicted value fails the exam
   regardless of rate math.

## Key-change log (calibration is evidence-based, never model-appeasing)

Every expected-key change must cite the convention it corrects toward.

- **2026-07-15 (cycles 1–3, haiku):** clock-only times; series titles
  accepted; g035 all-null per hard rule 7; g048 title "Second Sunrise";
  g058 city "Austin"; g067 venue "Scoot Inn & Historic Grounds"; g074 city
  "Luckenbach".
- **2026-07-15 (cycle 4, sonnet, PR #25 r5):**
  - g044 city null → "Austin": "downtown Austin" literally names the city
    as a place (convention 5); the old key punished a true assertion.
  - g066 artists + "The Nueces Strays", g037 artists + "The Reckless
    Years", "Motel Mirrors ATX": g004 (both acts expected) vs g037/g066
    (first act only) encoded the same venue-night shape with opposite
    keys — incoherent canon no model can satisfy. Unified on convention 7
    (venue-night = one bill, all acts).
- **2026-07-15 (cycle 6, sonnet, PR #25):**
  - g048 title "Second Sunrise" → null: 'Second Sunrise' names the RECORD
    being released, not the event; "Artist — 'Album' record release" is a
    billing-plus-description line with no event name (convention 3 unified
    rule). The old key forced a quoted-album exception that contradicted
    g007/g032's whole-name keys — the source of the cycle-5/6 title
    whack-a-mole.
  - g064 title "Midnight Cartography (extended set)" → null: an artist
    name plus a set descriptor is not an event name; keeping it
    contradicted g031/g023 (artist-as-title = null).
- **2026-07-15 (cycle 9, opus, PR #25):**
  - g009 title "Purple Reign" → null: the title exactly duplicated the
    artist name. Production extraction now nulls any title equal to an
    artist/venue name (provider `_drop_redundant_title` — a duplicate
    title asserts nothing the bill doesn't already assert, and would
    render as a doubled line on the event card), so the canon is: such
    titles are null everywhere. The tribute-trap's real teeth (artist =
    "Purple Reign", never Prince) are untouched.

- **2026-07-17 (evaluator r25, PR #28):**
  - g007 start_time "6:00PM" → removed: "gates 6:00PM" is a venue-access
    time with no show time stated — convention 4 says access-only means
    no start time, so the old key punished the production rule and
    rewarded extracting an access time as an event start. The prompt's
    time rule now names gates explicitly alongside doors (v.10), and the
    access-time convention is mechanically enforced (below).

## Mechanical enforcement (added after r25 — conventions must not drift)

Unambiguous conventions are enforced by `tools/golden_lint.py`, which the
release gate runs base-owned over the subject's golden set and prompt:
row shape and field types, both sample floors, trap minimums, surface-form
and 5-word-shingle contamination, convention 4's access-time rule
(an expected start_time that the text presents only as a doors/gates
time is a lint error), and convention 6's handle rule (no expected venue,
title, or artist may be a raw @handle). Judgment conventions (3's title
derivation, 5's stated-as-place, 7's venue-night) cannot be decided
mechanically; they are enforced by the evaluator's review of every
key change plus the citation discipline of the log below.

## Prompt hygiene rule (added after the g060 own-goal, cycle 6)

The extraction prompt's conventions and worked examples must share NO
surface form with this set — no golden venue, artist, title, or distinctive
text phrase, not even paraphrased ("Gruene Hall presents: The Fall Ramble"
as a prompt example taught the wrong answer shape for g060's real text).
Mechanical check: `tests/test_golden_exam.py::test_prompt_shares_no_surface_forms_with_golden_set`.

## Sample floors (corrected after evaluator r6, PR #25)

Two floors, both 300: the set must CARRY >= 300 expected facts (else any
run is INVALID), and a PASS requires >= 300 ASSERTED facts — asserted
facts are the 1% claim's statistical denominator. g075–g077 (dense,
ordinary listing shapes, collision- and echo-scanned) were added
2026-07-15 to give the asserted floor honest headroom after a rate-passing
run asserted 295; trap density obligations (injection/absence/non-event
minimums) are unchanged and enforced by the structural lint.
