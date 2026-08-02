# 1LIVE — Non-Music Expansion v1: the game plan for everything else happening tonight (PROPOSAL)

Greppable summary: founder-directed 2026-07-22 ("we need a game plan to
gather / ingest information from non-music events and venues"). How the
existing pipeline generalizes beyond live music: content-class taxonomy,
pilot order, source mechanics, display posture, and the demand-evidence
loop that earns each expansion. STATUS: PROPOSAL — content-scope
expansion is a FOUNDER decision by standing canon (member-preferences
doc: "comedy LISTINGS remain out of content scope until the founder
expands it"); this spec makes each expansion a one-line ratification.

## The architecture already generalizes — deliberately

Nothing in fetch→extract→gate3→promote is music-specific: a museum's
events page parses exactly like a club's calendar; corroboration,
confidence states, and disputed-shown-never-hidden apply unchanged. The
ratified venue-type taxonomy (music venue · bar · restaurant · dance
hall · theater · auditorium/PAC · museum · gallery · school venue ·
comedy club · outdoor stage · church/community hall · …) anticipated
this. What expansion actually requires is small and structural:

1. **`content_class` on sources and candidates** (config vocabulary,
   never code): `music.live` (today) · `comedy` · `theater` ·
   `museum.gallery` (openings, late nights, exhibits-with-dates) ·
   `film` (rep screenings, festivals) · `talks.literary` ·
   `food.drink.events` (not menus — ticketed/dated events) ·
   `market.community` · `family` · `sports.local`. Every class is a
   catalog attribute; the pipeline stays one pipeline.
2. **Per-class category mapping**: the extraction schema's genre field
   maps through a per-class vocabulary (comedy: stand-up/improv/open
   mic; theater: play/musical/dance; …) — a mapping TABLE, not new
   prompts. The extraction prompt is already class-agnostic (who/where/
   when/price are universal).
3. **Display posture** (canon-consistent): classes appear as LENSES,
   never dilution — the /tonight river defaults to the classes the
   member cares about (their "My defaults"), the city start screen's
   genre constellation grows class clusters, and the full-city view
   remains one tap away. No class is ranked above another for money,
   ever (no-pay-to-rank).

## Pilot order and why

**Wave 1 — comedy + theater + museums/galleries.** Highest
calendar-density (venues publish structured seasons), source shapes
identical to today's parsers, and the audiences overlap music-goers
(same night-out decision). Austin seed sources: Cap City Comedy, The
Creek and the Cave, Velveeta Room, Hideout Theatre, ZACH, Paramount/
Stateside, Bass Concert Hall (non-music program), Blanton, The
Contemporary, Mexic-Arte — correction (2026-07-24, source-completeness
review): Blanton and The Contemporary are NOT yet in the catalog; they
are being ADDED now (with Mexic-Arte, Texas Performing Arts, the Long
Center, ZACH, Austin Film Society, BookPeople, the comedy clubs, the UT/
Texas State/ACC calendars, Austin Public Library, and the City of Austin
civic calendar) as first-party public sources. An earlier draft of this
paragraph wrongly stated the catalog already carried them; wave 1 is
partly net-new source plumbing, not only tagging and widening.

**Wave 2 — film + talks/literary** (Austin Film Society, Alamo
rep programming, BookPeople, Texas Book Festival cadence).

**Wave 3 — markets/community/family/local sports** — high volume,
lower per-event value; earns its place by wave-1/2 engagement data.

## The demand-evidence loop (expansion is earned, not assumed)

Per standing canon the demand log is the evidence stream. Mechanically:
1. Ask-layer misses are logged as demand rows ("comedy tonight" asked,
   zero results — the highest-signal expansion vote a member can cast).
2. Each ratified class ships with a review gate at +30 days: sources
   fetched, candidates produced, promote rate, member engagement
   (class-lens opens, saves). A class that underperforms is paused by
   the same evidence, not by taste.
3. Kaizen rows per class launch (M-measures on yield and escape
   classes), so expansion quality is measured the same way pipeline
   quality is.

## Trust notes specific to non-music

- Museums/galleries: EXHIBITS have date RANGES — the river is
  event-shaped, so exhibits enter as their dated events (openings,
  closings, late nights) unless/until a "ongoing" surface is designed
  (out of scope here; recorded as a boundary, not built).
- Theater: performance runs = recurring events; the recurrence sensors
  built for residencies apply unchanged.
- Family/community classes: no new PII surface (events, not people).

## Founder decisions this spec needs

1. Ratify the `content_class` vocabulary above (edit freely — it's
   config).
2. Ratify Wave 1 (comedy + theater + museums/galleries) or reorder.
3. Confirm display posture: classes as member-default lenses over one
   river (recommended), vs. separate tabs (rejected: fragments the
   edition and the bounded-night feeling).
