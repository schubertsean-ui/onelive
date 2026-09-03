# One Live — Trust, existence, fields, mutation

Ratified: 2026-09-02. Status: in force with Vision and Coverage Law.
If a gate answers existence with a field or mutation test, the gate is wrong.

## Trusted door (existence)

Trusted means: a source a reasonable local would treat as “this is actually on,” not a source that survived a parser.

**One trusted door is enough for the entity to exist.** List it with honest holes. Later ticks and other doors fill holes. Do not wait for multi-confirm to exist.

### Trusted (existence: yes)

| Door | Examples |
|---|---|
| Official place / presenter | Venue, museum, festival, church, school, parks — public `/events`, ICS, JSON-LD |
| Official people | Artist / company / promoter public calendar |
| Established local desk | Chronicle, KUT, station “what’s on,” serious local listings desk |
| Civic public calendar | City, campus Localist, parks, tourism board |
| Organizer claim | ICS/CSV/mail they sent us (class E), via the claim path |
| Partner / licensed feed | Only when the contract exists |

Card grade: `via [door]`. That is the trust statement.

### Not enough to exist alone

| Door | Do |
|---|---|
| One unofficial social post | Hunt; do not list on that alone |
| SEO scrapers / copy farms | Lead only |
| Login wall we did not enter | Claim / subscribe / publisher |
| The extractor guessing | Never a door |

Path (b): two apparent independents, no official word → rare; visible warning if shown. Not the default.

### Common-sense tests

- Friend sends the URL as “here’s the calendar” → trusted door.
- Comment thread / random blog / Facebook-only with no venue page → not enough.
- Chronicle and the venue both list it → better fields, not “now it may exist.”
- Parser got two times → still a trusted door. Hole on the clock.
- We 403 → we failed; the venue did not become untrusted.

Trusted does **not** mean: perfect schema, multi-confirm, ready_to_promote, a relationship with them, every field filled, or a good extract day.

## Three questions (keep them separate)

1. **Existence** — Did a trusted door or publisher state a happening? If yes, list it.
2. **Field** — Is this title/time/place confirmed enough to print as fact, or is it a hole / uncertain?
3. **Mutation** — May we overwrite a value already on a published row? Only on confirmed same-page evidence for *that* field.

Holes are expected. Subsequent runs and other doors fill them before the show. A missing minute is not a missing night.

## Mutation (fail-closed) — shipped intent of #214

- Confirmed same-page change → update time / cancel / postpone evidence. Row is never deleted.
- Unconfirmed (timeout, 429, cap, empty, ambiguous parse) → no mutation.
- Confirmed gone → `cancelled` (or equivalent), row remains.
- Two listings at the same minute with different titles → collision; do not rename A to B; do not cancel on that confusion.
- Title rewrite needs a permalink (R-095). Until then, do not write title.
- Uncertain time must not overwrite a confirmed published time.

## Existence must not use mutation tests

Wrong: conflicting `start_time` / dedupe-ambiguity / not `ready_to_promote` ⇒ source banned, zero listings, or “verdict no” for the whole door.

Right: candidates from a trusted door stay listable; the messy field is `time_uncertain` (or existing equivalent); next t-minus may tighten.

Scoot Inn / Blanton shape: many events, two clocks → rows exist, door not banned, mutation of the uncertain field refused.

## Crawl (context, not this file’s implementation)

Unlimited catalog. Bounded tick (wall clock, model $, host politeness). Discover vs refresh. `next_due_at`. Skip extract on 304 / same hash. Refresh = 1 best URL. Event-proximity rungs T-30/14/7/3/1/day-of. Intensity follows the happening. Round-robin is a tie-break among due sources. No category weighting.
