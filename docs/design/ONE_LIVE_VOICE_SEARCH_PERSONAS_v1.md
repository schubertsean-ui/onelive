# Voice search personas v1 — 20 spoken searches the product must handle (founder-directed 2026-07-15)

Greppable summary: founder-directed catalog ("imagine someone says 'find me
R&B or good dance music with no or low cover charge'") of 20 spoken search
personas spanning 1→5+ combined filters plus the common edge shapes
(OR-logic, negation, synonyms, subjective terms, price bands, time
granularity, surprise-me, artist lookup, certainty queries, out-of-scope).
Each persona = a GOLDEN TEST CASE for the Step 9 voice parser (TODOS: voice
navigation, P1). The "what this teaches the build" section at the bottom is
the requirements harvest — several items feed extraction fields (Step 6)
and the taxonomy proposal (G-VT), not just the parser. STATUS: working
spec; parse targets use today's canonical filters (8 genres, Free/Ticketed,
Today/Tomorrow/This Week, 3 neighborhoods, venue, distance) and FLAG where
a persona needs data we don't capture yet.

Canonical filter dimensions today: GENRE (Rock, Hip-Hop, Jazz, Electronic,
Country, Metal, Experimental, Latin) · PRICE (Free/Ticketed) · DAY
(Today/Tomorrow/This Week) · NEIGHBORHOOD (Downtown, East Austin, South
Austin) · VENUE (search) · DISTANCE (from current location). Emotion/mood
filtering rides the Emotion & Vibe layer (PROPOSAL, G-EG/G-VT) — personas
using it are marked ⚑mood.

Honesty rules that bind every response (trust invariants, restated for
voice): never invent a ranking ("good/best" gets what matches, soonest
first, plus a plain statement that OneLive doesn't rate acts); never
pretend a synonym is an exact match (say "closest to R&B tonight:");
uncertain shows are included and said in plain words, never excluded;
nothing is promoted for money in any spoken answer.

## The ladder: one filter → five+

### One filter (one thing on their mind)

| # | Persona | They say | The app hears | What they get |
|---|---|---|---|---|
| 1 | **The Genre Loyalist** | "Show me jazz tonight." | genre=Jazz · day=Today | The feed filtered to jazz, soonest first; spoken echo: "Six jazz shows tonight — first one's 8 PM at the Elephant Room." |
| 2 | **The Broke Student** | "What's free tonight?" | price=Free · day=Today | Free shows only, count spoken first. |
| 3 | **The Neighborhood Local** | "What's happening on the east side?" | neighborhood=East Austin · day=Today | East Austin filtered feed. ("East side" → synonym map.) |
| 4 | **The Venue Regular** | "What's on at the Continental Club this week?" | venue=Continental Club · day=This Week | That venue's week, chronological. |
| 5 | **The Planner** | "What's going on this weekend?" | day=weekend ⚑day-granularity | This-Week view scoped to Fri–Sun. FLAG: "weekend" is finer than our 3 tabs — parser needs day-range math, no new data. |
| 6 | **The Mood Seeker** ⚑mood | "I want something chill tonight." | mood=low-intensity/calm · day=Today | Feed filtered by emotion coordinates (glyph layer). Gated on the Emotion & Vibe proposal; until ratified, honest fallback: "I can't filter by feel yet — here's everything tonight." |

### Two filters

| # | Persona | They say | The app hears | What they get |
|---|---|---|---|---|
| 7 | **The Founder's Example** | "Find me R&B or good dance music with no or low cover charge." | genre≈{R&B→nearest: Hip-Hop, Electronic} OR-set · price={Free + low-ticket} ⚑synonym ⚑price-band ⚑subjective | "Closest to R&B and dance tonight — free ones first, then cheapest tickets." Never claims R&B is a category we have; never ranks "good." |
| 8 | **The Jazz Date** | "Jazz downtown, please." | genre=Jazz · neighborhood=Downtown | Two-filter feed, spoken count. |
| 9 | **The Cheap Dancer** | "Free dance music tonight." | genre≈Electronic · price=Free ⚑synonym | Synonym-mapped, filtered, honest phrasing ("dance-closest: electronic"). |
| 10 | **The Last-Minute** | "Anything starting in the next hour near me?" | time-window=now+60min · distance=near ⚑time-granularity | Shows with start times inside the window, nearest first. FLAG: needs start-time window filtering (data exists) + geo sort (exists as distance). |

### Three filters

| # | Persona | They say | The app hears | What they get |
|---|---|---|---|---|
| 11 | **The Date Night** ⚑mood | "Something mellow tomorrow night downtown — we'll do dinner first." | mood=mellow · day=Tomorrow · neighborhood=Downtown (+implied later start) | Mood-gated like #6; "dinner first" biases to ≥9 PM starts. |
| 12 | **The Out-of-Towner** | "Country or Americana within walking distance of my hotel tonight." | genre={Country + Americana→nearest Country/Rock} · distance≤1mi · day=Today ⚑synonym | OR-set + tight radius; walking distance = ~1 mile default, said aloud so it's correctable ("within a mile — say 'farther' for more"). |
| 13 | **The Picky Punk** | "Loud rock tonight, but not metal." | genre=Rock · NOT genre=Metal · day=Today (+mood=loud ⚑mood) | Negation honored literally; "loud" waits on the emotion layer, stated honestly. |

### Four filters

| # | Persona | They say | The app hears | What they get |
|---|---|---|---|---|
| 14 | **The Organizer** | "Free jazz or blues in East Austin on Thursday." | price=Free · genre={Jazz + blues→nearest Jazz} · neighborhood=East Austin · day=Thursday ⚑synonym ⚑day-granularity | Four filters + a named weekday inside This Week. |
| 15 | **The Night Owl** | "Ticketed electronic downtown that starts after ten." | price=Ticketed · genre=Electronic · neighborhood=Downtown · time≥10PM ⚑time-granularity | Late-start filtering on existing start-time data. |

### Five-plus filters (the stress case)

| # | Persona | They say | The app hears | What they get |
|---|---|---|---|---|
| 16 | **The Maximalist** | "Find a free experimental or jazz show in East Austin tonight starting after nine, within a couple of miles." | price=Free · genre={Experimental, Jazz} · neighborhood=East Austin · day=Today · time≥9PM · distance≤2mi | Six constraints parsed in one breath. If the result is zero, the answer says WHICH constraint to relax: "Nothing matches all of that — dropping 'after nine' gives you two." Zero-result answers always name the loosening lever (and feed the H5 coverage-gap queue). |

### The common edges (just as likely as the ladder)

| # | Persona | They say | The app hears | What they get |
|---|---|---|---|---|
| 17 | **The Surprise Seeker** | "Surprise me." | surprise=tonight | One show, picked at random from tonight (the brief's honest variable-reward: the CITY is the slot machine, we never weight the wheel). Say it again, get another. |
| 18 | **The Artist Tracker** | "Is Sister Neon playing anywhere this week?" | artist lookup · day=This Week | Direct answer: "Yes — Saturday at Sahara Lounge, 8 PM. Want it on your calendar?" |
| 19 | **The Skeptic** | "Is the 10:30 show at the Elephant Room still happening?" | certainty query for one listing | Trust surface, spoken in the product's plain-words register: "It's listed, and details for this one may still change — the venue's site is the sure check. Want the link?" Never "verified," never a hedge-dodge. |
| 20 | **The Overreacher** | "Find me a comedy show." | out-of-scope (v1 = live music) | Honest boundary: "OneLive covers live music right now — comedy's not in yet. Tonight's music is here if you want it." Logged as demand signal (H5). |

## What this exercise teaches the build (the requirements harvest)

1. **Synonym / adjacent-genre lexicon** (#7, 9, 12, 14): spoken genre
   vocabulary is bigger than any taxonomy — R&B, dance, blues, Americana,
   indie, punk, DJ… Parser needs a curated mapping to the canonical 8 with
   HONEST phrasing ("closest to R&B tonight"), never silent substitution.
   Feeds the G-VT taxonomy proposal: the lexicon doubles as evidence for
   which genres the taxonomy is missing (R&B/Soul is already visibly
   absent). Lexicon lives as config; every entry is a test case.
2. **OR-sets and negation** (#7, 12, 13, 14, 16): the filter engine must
   take genre unions and exclusions — the UI's multi-select already
   implies OR; voice makes NOT explicit. Cheap in the query layer; must be
   in the parser grammar from day one.
3. **Price is a band, not a binary** (#7): "no or low cover" needs ticket
   PRICE as an extracted field, not just Free/Ticketed. → Step 6
   extraction schema: capture price when the source states it (never
   guess); voice sorts free → cheapest-known → price-unknown (said as
   "price not listed", never hidden).
4. **Time granularity** (#5, 10, 11, 15, 16): weekend, after-ten,
   next-hour, late — all computable from start times we already extract;
   the parser needs time-window vocabulary. No new data, real grammar.
5. **Subjective terms get honesty, not fake ranking** (#7): "good/best"
   never invents an ordering — discovery is not for sale and not faked.
   Fixed response pattern: give what matches, soonest first, one plain
   sentence that OneLive doesn't rate acts. This is a TRUST-SURFACE rule
   for voice, same bar as no-badges.
6. **Zero results name the lever** (#16): every empty answer says which
   constraint to relax and what that yields; misses feed the coverage-gap
   queue (research-note H5).
7. **Mood search rides the Emotion layer** (#6, 11, 13): the demand is
   real and conversational; capability is gated on the Emotion & Vibe
   proposal (G-EG/G-VT). Until ratified: honest fallback, never a fake
   mood filter.
8. **Certainty queries are a spoken trust surface** (#19): the 4-state
   model must have a VOICE register — plain words, venue link offered,
   never "verified", never silent dropping of uncertain shows.
9. **Out-of-scope honesty + demand logging** (#20): say what OneLive is,
   log what people asked for; the ask-log is roadmap evidence.

## Disposition

Personas #1–20 become the voice parser's golden test set at Step 9 (TODOS
P1 voice item references this doc). Harvest items 1–4 add concrete fields/
grammar to Step 6 (price capture) and Step 9 (parser). Items 5, 8, 9 are
voice-register trust rules — they go wherever the parser goes, enforced by
the same tests. Item 7 waits on founder ratification of the Emotion layer.
