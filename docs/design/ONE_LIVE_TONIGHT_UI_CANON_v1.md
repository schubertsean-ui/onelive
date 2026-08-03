# 1LIVE — `/tonight` UI Canon (v1)

**Status:** RATIFIED consolidation — the single source of truth for the consumer `/tonight`
experience. This document does not invent design; it **consolidates** design that was
already ratified but scattered across the Master Design Brief, fifteen founder review
rounds of the FLOW prototype, and a dozen satellite specs — plus two founder directives
issued 2026-07-31 (the contextual preview principle; the calm/cognitive-load mandate).
Where this doc and a source disagree, **this doc wins going forward**; the source is cited
so any change is traceable.

**Why this exists:** the live `/tonight` feed drifted "several designs behind" not because
the design was lost, but because it lived in fragments and its rich content layer was never
wired to data. Fragmentation caused the drift. One canonical doc is the fix.

**Authority chain (what this consolidates):**
- `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md` — RATIFIED principles (trust display,
  Spark Line, Emotion Glyph, calm/curiosity, WCAG/CWV).
- FLOW prototype **v3.8** — the spatial/layout canon, reached through founder rounds 1–15
  (`docs/ONE_LIVE_CHANGE_LOG.md:715–735`; render: `design/proposals/direction-4-flow.html`).
- Satellite specs: Night Out, Tasting Trail, Emotion/Vibe, Non-music Expansion,
  Geo-Identity draw-to-search, Growth Loops, Product Vision (see §12 for each one's status).
- Founder directives, 2026-07-31 (this session): the **contextual preview** principle (§4)
  and the **calm / cognitive-load** governing law (§1).

**The standard this holds to (founder, 2026-07-31):** *"World-class UX requires world-class
UI. Speed, clarity, beauty. Keep in mind how much information a human brain absorbs at a
time."* And: *"recognized as one of the best and easiest app/site/tool/platform in the
world."* Every rule below serves that.

---

## §0 · North Star

A person feels the 6–9 PM restlessness — *"what's happening tonight?"* — opens 1LIVE,
and in **under ten seconds, with no account and a sub-2-second load**, has a real answer
they trust. The product is *"about finding and engaging in experiences, helping individuals
and the culture thrive"* (founder, round 6, `CHANGELOG:722`).

The feeling to engineer (founder's original FLOW redirect, `CHANGELOG:716`): *"flowing up
down back forward, easy, cool, awesome, fast, satisfaction."*

---

## §1 · Governing principles (the laws every screen obeys)

These are non-negotiable. A design choice that violates one of these is wrong even if it
"looks nice."

1. **Calm over clutter — respect working memory.** A person holds ~3–4 things at once. A
   card shows a *few* things beautifully; everything else is one tap away. **Never pile
   fields onto the card.** Richness lives behind disclosure (§6), never on the surface.
2. **Curiosity over completeness.** *"Cards show enough to activate the question, never so
   much that there's no reason to tap… a row of slightly-open doors"* (`BRIEF:86`). One
   hook per card, not a summary.
3. **Speed is a feature.** Answer in <10s; LCP <2.5s; the feed renders immediately with no
   login. Perceived speed (instant filter apply, no page loads) matters as much as raw load.
4. **Beauty is not decoration — it is trust.** *"Competence shown, not told."* The proof of
   trustworthiness is that listings are simply right, complete, fast, and lovely — every time
   (`BRIEF:48`).
5. **Trust by construction, never by badge.** The interface never says "verified,"
   "confirmed," or "trusted." No shields, checkmarks, stars, or trust chrome, ever
   (`BRIEF:48, 100`). Uncertainty gets *one quiet icon* (§8), nothing louder.
6. **Nothing real is hidden; nothing is for sale.** Disputed shows still appear, marked as
   disputed. Money never decides what is seen or how it ranks — **no pay-to-rank, ever**,
   including via specials, nearby listings, or analytics (`BRIEF:51`; `CHANGELOG:721`).
7. **Honest gaps beat filler.** When we don't have something, show nothing (or an honest
   "check the venue") — never a fabricated stand-in (Night Out anti-loathing rule;
   `TASTING_TRAIL_SECTION_v1.md`).
8. **Accessibility is table stakes.** WCAG 2.2 AA; every glyph has a text equivalent; every
   tappable control ≥44px; reduced-motion honored (`BRIEF`).

---

## §2 · The card — anatomy at rest

A card is **one "room."** It has **two coequal, tappable doors — the artist and the
venue** — each of which opens its own slide-in lens (§6). This "dual-anchor" is the core of
FLOW: a person may want to decide by *who's playing* or by *where the room is*, in either
order (`CHANGELOG:717`).

At rest the card shows a spare, beautiful hook — **not** every element below at full weight.
The elements, in render order (canonical layout: `direction-4-flow.html:263–294`):

**Artist zone — the "artist ›" door:**
1. **Artist photo tile** (with the artist's name as caption).
2. **The time line, one row:** start time · **"doors X:XX"** when relevant · **price pill**
   (mint for Free) · **"on now"** live tag when in progress (`CHANGELOG:721, 732`).
3. **Spark Line** — a 3/5/7-word vivid hook (§3). This is the card's primary curiosity gap.
4. **Emotion Glyph** — one small SVG symbol, emotional weather (§5).
5. **The contextual preview hook** — the type-aware "hear/see it" (§4).

**Venue zone — the "venue ›" door (its own bordered, slightly-darker block, separated by
~14px of air so it reads as its own object):**
6. **Venue photo cap.**
7. **Venue name + a one-line character line** (*"basement jazz cellar, candle-dark,
   standing"*) beside a **mini-map chip** (Austin outline + Colorado River + venue locale
   dot) (`CHANGELOG:717, 719`).
8. **Address as a map link + distance** (*"315 Congress Ave ↗ · 0.4 mi"*) (`CHANGELOG:729,
   730`).
9. **"From the venue" specials slot** — venue-owned display space, clearly attributed
   (*"Happy hour til 8"*). **Never affects ranking** (§7).
10. **"See nearby ›"** — opens the nearby lens (§7).
11. **Venue's own site link.**

**Rail (one thumb row):**
12. **Genre chip** with citywide count in the ratified wording **"N more ‹Genre›"** (count +
    genre large, "more" small — *"2 more Gospel-punk"*); opens the nearest-first list of that
    genre tonight (`CHANGELOG:735`).
13. **One quiet "?"** uncertainty control (≥44px) → dismissible sheet (§8).

**Density tiers (sum-preserving — every event lands in exactly one bucket, nothing hidden;
`web/lib/feed.ts` `bucketByDate`):**
- **This week (≤7d):** full rich card as above.
- **Later this month (8–30d):** compact chronological row.
- **Beyond (>30d):** one scannable line — `date · act · venue · price`, date-only (the exact
  minute months out is noise). The trust marker still rides even the tersest line.

---

## §3 · The contextual preview hook (the generalized "3 music options")

**Founder directive, 2026-07-31 — this is now canon:** the preview slot is **not
music-only. It is a polymorphic, contextual curiosity hook that adapts to what the event
actually is.**

| Event type | The preview becomes |
|---|---|
| **Music act** | Up to **3 named-track listen chips** ("SnipTunes"), count honest 3/2/1 (`CHANGELOG:721`); today shipped as 3 service **search** links — Spotify / Apple Music / YouTube (`web/lib/listen.ts`) pending the embedded-player upgrade |
| **Lecture / talk** | The speaker's videos / past talks on the topic |
| **Recurring event / festival** | Last year's photos, video, and write-ups |
| **Comedy** | A clip or set |
| **Film** | The trailer |
| **Visual art / museum** | The works, or the artist's pieces |
| **Food / tasting** | The dishes, or the room |

**Three non-negotiable rules (founder):**
1. **Dynamic** — chosen at render time from what actually exists for *this* entity, not a
   fixed template.
2. **Contextually accurate** — the *real* speaker's real lecture, the *real* event's real
   past media. Sourced and provenance-checked. **Never fabricated, never a generic
   stand-in.** Same faithfulness discipline as the Spark Line: preview only what's real, and
   it passes validation before it shows (the gate-custodied-publication invariant —
   "AI never publishes unvalidated" — governs previews too).
3. **Curiosity-inducing** — the point is to make a person *lean in*, not to summarize. It is
   the slightly-open door.

The **type signal already exists** — the category resolver reads what an event *is*
("museum → visual-arts", `RECORD.md R-047`). The **per-type preview media is new** and is
the single richest unbuilt piece of the experience. Data + provenance requirements: §11.

---

## §4 · Spark Line

A **3, 5, or 7-word** vivid, sensory, emotional description of the act's work — the card's
primary curiosity gap. *Not* a sentence; may be fragments, punctuation, typographic play
(*"brass. menace. amen."*). Never generic marketing language (`BRIEF:65`).

**Source waterfall (tiers, in priority order):**
- **Tier A — the artist's own words.**
- **Tier B — a named critic/tastemaker**, with a tiny attribution (*"— Austin Chronicle"*).
- **Tier C — AI-drafted last resort**, composed *only* from the artist's own public
  materials, faithfulness-gated by the eval harness, rendered in a slightly distinct register
  (italic, one shade quieter) with a small **"✳"** and *"— first notes"*. Tapping opens a
  one-tap-dismiss sheet: *"Drafted from [artist]'s own materials. [Artist] can make it theirs
  anytime."* The moment a creator claims, their words replace ours (`BRIEF:65`).

Every AI Spark Line goes through the **Descriptor Foundry** (6 candidates → pairwise knockout
→ fusion-of-N synthesis with *style new, facts never* → independent judge → provenance +
golden-set regression). No single-shot generation ever reaches a fan (`BRIEF:151–163`).

---

## §5 · Emotion Glyph

One small expressive SVG symbol (or a sanctioned two-glyph pair) that conveys the *emotional
experience* a fan will have — **"emotional weather, not a rating and not a brand mark"**
(`BRIEF:65, 132–147`).

- **Derived only** from the creator's own description (claim-flow "describe your sound in
  seven words," bio, or consented materials). **No description → no glyph.** Never inferred
  from third-party scraping or biometrics.
- Pipeline: description → Plutchik coordinates (8 emotions × 3 intensities + dyads) →
  **deterministic lookup** into a curated ~40–60-glyph lexicon (auditable, regression-tested).
- **Self-rendered SVG set, never native emoji.** **Banned:** any glyph read as a rating or
  endorsement (🔥 ⭐ 💯 👑 ❤️ 👍). The glyph must never create a visible hierarchy between
  listings — discovery neutrality applies to feelings too.
- Every glyph carries a text equivalent (aria-label, e.g. *"mood: slow-burning, tender"*).
- **Creator override always beats the engine.**

---

## §6 · The interaction & disclosure model (the anti-clutter engine)

This is how a spare card carries deep richness without clutter: **progressive disclosure.**
The card is the doorway; the depth lives in lenses that slide out on demand.

1. **Two doors per card.** The artist zone and the venue zone are each a tappable door
   (*"artist ›"* / *"venue ›"*). Tapping opens that entity's **lens** — a forward-expanding
   overlay of the *same* surface (swipe in / release back), **not a page load**
   (`CHANGELOG:716, 717`).
2. **The switch.** Inside either lens, a control flips **artist ↔ venue** so a person can
   explore in either order without backing out (`CHANGELOG:717`).
3. **The nearby lens** ("See nearby ›") — the map surface (§7), also a lens, hidden until
   asked for.
4. **Uncertainty is a whisper, not a banner.** One quiet **"?"** (≥44px) opens a small,
   **one-tap-in / one-tap-gone** sheet in calm plain language, with the venue's own site
   linked right there (`BRIEF:50`). Never a warning tone — *a courtesy.*
5. **Filters slide in** and apply **instantly** (no reload), with an obvious clear
   (`BRIEF:66`).
6. **Detail is a destination, not a dead end** — reached from the card; carries the full
   logistics, the embedded preview, share, and the same quiet uncertainty pattern (§10).

**The disclosure discipline:** default to *hidden*. The card surfaces the hook (time, act,
Spark Line, one glyph, price, one preview affordance). Venue character, specials, nearby map,
full address, and secondary media appear **only** when a person opens the relevant door. This
is the mechanism that makes "add all the missing features" and "make it less cluttered"
the *same* instruction.

---

## §7 · The venue block & nearby

**Venue block** (below the artist, its own object): photo → name + character line → mini-map
chip → address (map link) + distance → specials slot → "See nearby ›" → venue site.

**"From the venue" specials** are **venue-owned display space**, always clearly attributed,
and **never touch ranking** — the no-pay-to-rank invariant governs (`CHANGELOG:721`). We do
*not* fabricate specials; a venue with none simply shows none.

**The nearby lens** (opened by "See nearby ›"): a **street-level map** with a **5-minute-walk
ring**, the venue at center, and surrounding bars/restaurants/clubs — each row carrying
**transport guidance by distance** (walk / pedicab / ride) (`CHANGELOG:721`). Governing spec:
**Night Out** (`ONE_LIVE_NIGHT_OUT_v1.md`) — its anti-loathing rules are canon for this
surface: **pull never push · sparse (2–4, never a firehose) · un-ranked & un-buyable · no
FOMO mechanics · the anchor event stays the star · honest gaps · ephemeral (dies at sunrise,
no profile).** Bars/restaurants shown as **counts + distance, never ratings** (menus/deals
are not our verified data).

**Draw-to-search map** (Geo-Identity spec §5): a person may **draw a loop on the map with a
finger** — any size, block to region — and get the events inside it; the loop names the area
by the layer its size implies ("East Austin" / "Hill Country") and is shareable. *Proposal,
founder-gated* (§12).

**Draw-to-search prototype bench (RATIFIED 2026-08-03, part of the UI/UX design formality):**
before any native build — and available earlier, to inform the gate decision itself — the
draw-to-search UX is prototyped in **GeoLibre** (open-source MIT GIS; in-browser draw tools +
DuckDB-WASM spatial) against exported real event points: $0, off-product, data stays local.
Bench findings are design inputs logged to the canon, never gate evidence; the feature build
itself stays founder-gated. Decision record:
`docs/memory/decisions/2026-08-03_geolibre-draw-to-search-prototype-bench.md`.

---

## §8 · Trust display rules (verbatim canon)

- **No badges of any kind.** Never "verified," "confirmed," "trusted." No shields,
  checkmarks, star ratings, trust-score chrome (`BRIEF:48, 100`).
- **Low-confidence = one small, quiet icon only** (no label, no color alarm). Tap → an
  instantly dismissible sheet in calm plain language: details for this show may change, here's
  the venue's own site to be sure. One tap in, one tap gone. *A courtesy, never a warning*
  (`BRIEF:50`).
- **Disputed is shown, never hidden** — a slightly stronger marker ("sources disagree"); on
  the detail page its disclosure opens by default (`BRIEF:51`; `web/lib/trust.ts`).
- **The feed never filters on confidence.** Ended events leave by a *time* filter, never a
  confidence filter; a disputed on-now show still appears (`CHANGELOG:749`).
- **Trust rides into every artifact** — a shared/texted show carries its cancellation status
  and any non-confirmed confidence into the shared text (`web/lib/share.ts`).

---

## §9 · Feed structure

- **Title:** "Tonight in Austin." Masthead carries the honest count line (*"N shown · by
  start time · no pay-to-rank"*).
- **Order:** chronological by start time from the phone's real clock; over shows leave the
  river (dimmed "ended" in lists); a started-but-live show stays, tagged "on now"
  (`CHANGELOG:720`).
- **Date tabs:** All upcoming / Today / Tomorrow / next dated days.
- **Filters (slide-in, instant):** cultural-domain (the 22 categories) · genre · venue-area ·
  Free-only · clear.
- **Ask mode** (*"Tell me what you're interested in"*): type/tap/speak a desire; results are
  a **filtered lens, never a ranked gate**, each row carrying a plain "why:" line. Built on
  the member-preferences canon: **a lens never a gate · provenance on every suggestion ·
  preferences never sold, never shape anyone else's feed** (`CHANGELOG:728`).
- **Plan mode** (*"Plan a day / night / weekend"*): builds a time-ordered itinerary of real
  listings, each stop with a "why:".
- **Content classes** (comedy, theater, museums, tasting trail, …) appear as **member-default
  lenses over ONE river, never separate tabs** — a separate tab "fragments the edition and
  the bounded-night feeling" (`ONE_LIVE_NONMUSIC_EXPANSION_v1.md`).
- **Works without any account.**

---

## §10 · Event detail

Reached from a card. Renders: event image · title · performer · status note
(cancelled/postponed/moved) · a facts list (**When** long-form · **Where** = venue + area +
map link · **Price** · **Kind** = category · subsegment) · **"Check the venue"** (tap-to-call
when the number is real + the venue's *own* site — never a ticketing host presented as the
venue site) · **actions** (Tickets ↗ opens externally · Share via native OS sheet) · the
**contextual preview** (§4) · the quiet uncertainty disclosure (§8). *(Current build:
`web/app/(public)/tonight/[id]/page.tsx`.)*

---

## §11 · Data requirements (what each element needs — the bridge to the build)

The live feed is **data-starved, not broken.** Every missing element below is missing because
its data field doesn't exist yet. This table is the spec for the ingestion work in §13.

| Element | Data it needs | Exists today? |
|---|---|---|
| Time line, price, tickets, venue name/area/address, map link | `start_time`, price fields, `ticket_url`, `venue_*` incl. lat/lng | ✅ (in `licensed_event`) |
| Venue contact ("check the venue") | `venue_url` (own-domain), `venue_phone` | ✅ |
| **doors time** | a `doors_time` field | ❌ |
| **Spark Line** (+ tier, ✳) | `spark_line` text, `spark_source` (tier A/B/C), `spark_provenance` | ❌ |
| **Emotion Glyph** | `emotion_glyph_id` + Plutchik coords + source ref (Emotion Glyph engine) | ❌ |
| **Contextual preview** (music tracks / lecture video / past-year media / trailer / works) | a typed `preview_media[]` — {type, url, title, provenance, event_type-matched} | ❌ (music = 3 search links only) |
| **Venue photo + character line** | `venue_photo_url`, `venue_character` (≤1 line) | ❌ |
| **"From the venue" specials** | `venue_specials[]` (venue-claimed, attributed) | ❌ |
| **Nearby lens** (map + walk-ring + POIs + transit) | venue geo (have) + nearby-POI dataset (bars/restaurants w/ distance) + own-events proximity | ❌ (only a point exists) |
| **Draw-to-search** | point-in-polygon over event geo (have geo; need the query surface) | ❌ (proposal) |

---

## §12 · Status of every piece (so nothing is ambiguous)

| Piece | Status | Where |
|---|---|---|
| Card shell, time-order, buckets, filters, Ask/Plan, trust marker, share, venue contact, music **search** links | **BUILT (on master)** | `web/app/(public)/tonight/` |
| Spark Line + tier-C ✳ | **RATIFIED, unbuilt** (data-starved) | `BRIEF:65` |
| Emotion Glyph | **RATIFIED, unbuilt** | `BRIEF:132–147` |
| Slide-out artist/venue lenses + switch | **RATIFIED (FLOW), unbuilt** in the real app | `CHANGELOG:717` |
| Venue block (photo, character, specials) | **RATIFIED (FLOW), unbuilt** | `CHANGELOG:721` |
| Nearby lens (map, walk-ring, transit) | **RATIFIED layout / Night Out spec** — *feature build founder-gated* | `CHANGELOG:721`; `ONE_LIVE_NIGHT_OUT_v1.md` |
| Contextual preview (polymorphic) | **NEW founder directive (2026-07-31)** — now canon, unbuilt | §3, §4 |
| Calm / cognitive-load governing law | **NEW founder directive (2026-07-31)** — now canon | §1 |
| Emotion/Vibe "Feel" search mode | **PROPOSAL** (Gap G-VT) | `ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md` |
| Draw-to-search map | **PROPOSAL, founder-gated** — UX prototype bench **RATIFIED 2026-08-03** (GeoLibre: $0, off-product, pre-build formality step) | `ONE_LIVE_GEO_IDENTITY_v1.md §5` (citation unresolved — R-068); `docs/memory/decisions/2026-08-03_geolibre-draw-to-search-prototype-bench.md` |
| Tasting Trail section UI | **RATIFIED intent, unbuilt** (read path merged) | `TASTING_TRAIL_SECTION_v1.md` |

**Founder-gated / spend-or-service decisions before build:** an embedded music player (music
API key), a nearby-POI dataset (Google Places / OSM), any map tiles (Mapbox), and any
analytics service are money/new-service decisions — **founder-crucial**, per the charter.

---

## §13 · Build sequence (data-first — the UI is starved, not broken)

Rebuilding the *look* without the *data* just paints an empty frame. Sequence:

**Phase 1 — Foundation (make the current feed world-class at what it already has).**
Rebuild the card + the two-door / lens interaction model (§2, §6) against *existing* data:
spare card, venue block (name/character-from-what-we-have/address/map/distance), slide-out
lenses, the quiet uncertainty pattern, instant filters. This alone fixes "cluttered" and
"several designs behind" using zero new data — it is the FLOW v3.8 skeleton done right.

**Phase 2 — The content layer (ingest the fields the design needs).** In rough value order:
1. **Contextual preview media** (§3) — the single biggest curiosity lift; start with music
   (upgrade search-links → real tracks) then lecture video / past-year media, each provenance-
   gated.
2. **Spark Line** — stand up the Descriptor Foundry pipeline + `spark_line` fields.
3. **Venue enrichment** — `venue_photo`, `venue_character`, and the claim-flow **specials**
   slot.
4. **Emotion Glyph** — the Plutchik → lexicon engine + `emotion_glyph` fields.

**Phase 3 — Spatial & social (founder-gated surfaces).** Nearby lens (Night Out), draw-to-
search map (Geo-Identity), "Feel" mode (Emotion/Vibe), Tasting Trail section — each behind its
own founder go/no-go and any service/spend decision.

**Discipline for every phase:** each element ships only when its data is *real and validated*
(honest gaps beat filler, §1.7); no element ever feeds ranking; each is measured (see the
companion analytics canon) so we know it's actually making the product easier and more loved.

---

## Appendix · Source map

- Principles, Spark Line, Emotion Glyph, trust rules, detail, filters, Descriptor Foundry:
  `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md`.
- FLOW spatial model, card anatomy, lenses, nearby, specials, rounds 1–15 (v3.8):
  `docs/ONE_LIVE_CHANGE_LOG.md:715–735`; render `design/proposals/direction-4-flow.html`.
- Nearby/night-out rules: `docs/strategy/ONE_LIVE_NIGHT_OUT_v1.md`.
- Draw-to-search: `docs/strategy/ONE_LIVE_GEO_IDENTITY_v1.md §5` (branch
  `claude/geo-identity-spec`).
- Feel mode / taxonomy: `docs/strategy/ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md`.
- One-river content classes: `docs/strategy/ONE_LIVE_NONMUSIC_EXPANSION_v1.md`.
- Tasting Trail: `docs/design/TASTING_TRAIL_SECTION_v1.md`.
- Current implementation: `web/app/(public)/tonight/` (`FeedApp.tsx`, `flow.css`,
  `[id]/page.tsx`, `web/lib/{feed,licensed,listen,trust,share,detail}.ts`).
- Founder directives 2026-07-31 (this session): contextual preview (§3/§4); calm/cognitive-
  load law (§1).
