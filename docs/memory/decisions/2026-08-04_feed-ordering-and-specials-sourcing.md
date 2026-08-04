# Decision: feed ordering founder directives + specials sourcing widened (2026-08-04)

**Founder, verbatim (on the live feed):**
- "The timeframe ordering wrong. Start with today."
- "Look at Thursday - it's flowing out of the screen - I have to slide for the rest of the weekly dates."
- "Move all upcoming to be last."
- "Because there is no separation of dates or segments or have you it's so cluttered a person doesn't know where to start."
- "Specials don't need to be venue claimed now's if it's in their website we can show it."

## Decided and executed (UI lane, same day)

1. **Today is the default view and leads the tab row; "All upcoming" is last.**
   (Also restores the brief's own choice-architecture rule — "default view is
   tonight" — which the build had deviated from by defaulting to All upcoming.)
   URL semantics: `when=today` is now the bare default; `when=all` travels
   explicitly; old shared links with an explicit `when` keep their meaning.
2. **Date tabs wrap** — nothing scrolls off-screen; every day visible without sliding.
3. **Single-day tabs render ONE river** (rich cards, domain-grouped) with no
   This-week/Later/Beyond bucket chrome — those headers only mean something
   across time spans, and on a day view they read as clutter.
4. **Timezone defect fixed en route:** day boundaries were computed in the
   RUNTIME timezone, so production SSR (UTC) ended "Today" at 7 PM Austin time
   and bucketed later shows as Tomorrow in the server-rendered HTML. Boundaries
   are now pinned to the market timezone (America/Chicago) on server and client
   alike; the viewer's real clock still governs what has ENDED.

## Specials sourcing WIDENED (canon amendment, founder-directed)

Canon §7 / R-049 treated "From the venue" specials as venue-CLAIMED content.
The founder widens the source: **a special published on the venue's own website
may be shown**, attributed to the venue, exactly like other venue-own-domain
facts. Still venue-authored words (never fabricated, never third-party),
display-only, never ranking. ROUTING: acquisition is pipeline work (venue-site
crawl → specials extraction under the same gates as other crawl content —
sourcing lane); the display slot already exists in the canon card. Queued in
TODOS; the trust boundary "venue's own words, attributed" is unchanged — only
the CHANNEL (their website, not only the claim flow) widened.
