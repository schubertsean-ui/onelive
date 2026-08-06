# Decision: date recovery is a CALLBACK to the source, not a logic guess — founder-directed (2026-08-05)

**Founder, verbatim (session chat, on the 836 published-but-dateless
discovered events):**

> "This must have an easy fix - you must not be ingesting all the relevant
> information. No one will post or announce event with just a time - do a
> better mode through job searching."

and, ratifying the year rule while ordering the method:

> "Yes in the year rule but you have to do a better job search g so it really
> is more of a call back position than a logic process"

**What the founder saw that the pipeline missed.** The dates ARE on the
pages. Diagnosis (all verified in code): (1) the segmenter splits calendar
pages into per-event blocks and orphans the day-header ("Tuesday, August 5")
that governs the listings under it, so the certified extractor honestly saw
"10:00 AM" with no date; (2) year-less full dates ("August 9") failed the
strict full-date-evidence bar even though every calendar reader resolves the
year from context.

**The build (one PR, all in the UN-certified shaping layer — extraction
certification untouched, extraction stays ON; smoke re-bind required since
worker/segment.py, worker/datetime_normalize.py, worker/ai_extract.py are in
the armed-cron runtime closure):**
1. **Segmenter date-context carry-forward** (worker/segment.py): each split
   block that lacks its own full date gets the nearest page-published date
   line above it prepended VERBATIM — re-attachment of the source's own text,
   never synthesis.
2. **Callback recovery** (worker/date_callback.py, new — the founder's
   "call back position"): a refused date claim triggers ONE bounded fetch of
   the event's own linked page (ticket/RSVP link), reading only
   machine-declared dates — JSON-LD Event startDate/endDate iff exactly one
   Event is declared, else microdata itemprop content attrs. Any failure or
   ambiguity returns nothing; recovered strings re-enter the STRICT
   normalizer; method + source URL recorded in candidate provenance.
3. **Year rule, last resort** (resolve_yearless_claim): a claim that is a
   full date minus the year resolves to the unique year within [-30, +300)
   days of the fetch date — a window narrower than a year, so no tie exists
   to guess. Resolution basis recorded in provenance. Time-only, ambiguous
   numeric, and unparseable claims stay refused exactly as before.

**Order of preference, per the directive:** page's own date context →
callback evidence → year rule. Fabrication remains impossible at every step;
what changed is that evidence the source published is no longer thrown away.

**Standing consequence.** The 836 already-published dateless events stay
dateless; the 3-hourly ingest re-reads every source through the fixed path,
so dated candidates flow within hours of merge. A supersede rule (retire a
dateless event when its dated twin publishes) is a separate follow-up PR.
