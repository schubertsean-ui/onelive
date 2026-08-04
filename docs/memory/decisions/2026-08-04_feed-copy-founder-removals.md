# Decision: four feed-copy edits — founder-directed (2026-08-04, live-site review)

**Founder, verbatim, four directives in sequence while reviewing the deployed feed:**
1. "remove: · no pay-to-rank"
2. "remove this: \"Long-tail domains (libraries, lectures, readings, block parties) are being added from 1Live's own pipeline; what you see here is the ticketed spine.\""
3. "remove this \" — never fabricated\""
4. "this is too specific to 'ticketing' - just make it \"Real listings from validated sources\"" — the footer's first sentence is now exactly that; the times-change/venue-last-word sentence stays.

**What changed (living surfaces only, same pattern as the 2026-08-04 spark-disclosure
edit).** `web/app/(public)/tonight/FeedApp.tsx`: the count line drops the
"· no pay-to-rank" text (now "N shown · by category, soonest first" / "… soonest first
within each section"); the footer drops the long-tail/ticketed-spine sentence and the
" — never fabricated" fragment (now "Real, licensed listings from authoritative
ticketing sources. Times and prices can change; each listing links to the
venue/ticket source as the last word."). Pinning tests updated
(`calm-surface.test.tsx` now asserts the ABSENCE of "no pay-to-rank" in the rendered
surface); UI canon §9 count-line passage updated with the verbatim directive. Historical
records keep the original copy (append-only).

**What did NOT change — stated precisely because two of these touch trust language.**
The no-pay-to-rank INVARIANT is behavior, not copy: money still never decides
visibility or order anywhere in the feed code, the ranking remains time/category
driven, `web/lib/trust.test.ts` and the evaluator mandate still guard it, and canon §1's
"no pay-to-rank, ever" invariant statement is untouched. Likewise "never fabricated"
was descriptive copy over an unchanged data path: listings still come only from
licensed provider APIs and the gate-custodied pipeline; nothing about sourcing or
fabrication-prevention mechanics moved. These are copy edits at founder direction —
quieter surface, identical physics. The site meta description (layout.tsx) retains its
own wording; the founder's directives pointed at the on-page feed copy.

**Authority.** Founder-ratified canon copy is edited at the founder's written
direction (quoted verbatim above), swept across living surfaces in the same change,
history untouched — the standing pattern (2026-08-03 invariant rewording; 2026-08-04
spark-disclosure edit).
