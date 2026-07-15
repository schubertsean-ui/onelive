# Golden set — conventions and key-change log

`golden_set_v1.jsonl` is the extraction exam (runner: `python -m ai.golden_exam`,
thresholds in `ai/golden_exam.py`, workflow: `.github/workflows/extraction-eval.yml`).
74 hand-authored examples, ~305 expected field-level facts. Row shape:
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
3. **Titles**: an explicit distinct event name, whole and verbatim, artist/
   promoter prefixes included when written as part of the name; a leading
   "<venue> presents:" label is stripped; bare artist names, billing lines,
   and re-capitalized prose phrases are never titles.
4. **Times**: clock time only; show/music time over doors; doors-only means
   no start time; vague ("late", "TBA") is null.
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
