# Genre taxonomy v1 — standards-based core, fine-grained on top (RATIFIED — founder 2026-07-29, "ratify-and-wire the 18 genres"; supersedes the flat 8)

> **STATUS: RATIFIED & WIRED (2026-07-29).** The founder ratified the Layer-1
> eighteen verbatim. Layer 1 is live in the product as `web/lib/genres.ts`
> (the 18 + the lossless today's-8 map + the synonym lexicon seed +
> `canonicalGenre()` normalizer) and surfaced as the derived Layer-0 genre rail
> on `/tonight` (`genreFacet` in `web/lib/feed.ts`). Layer 2 + the full lexicon
> proceed as config under normal gates. The hard pre-ratification Spotify
> recheck was completed (see Sources) and the citation upgraded. Decision
> record: `docs/memory/decisions/2026-07-29_genre-taxonomy-ratified.md`.

Greppable summary: founder-directed (2026-07-15: "start with what's common
or standard and architect it so we can improve on it… more fine grained and
targeted"). Three-layer architecture: LAYER 1 = 18 canonical top genres
aligned to the industry-common set (Apple Music's hierarchical genre codes,
Spotify's browse layer, Bandsintown's live-event tags — sources below);
LAYER 2 = open, curated subgenre/style tags that always map up to Layer 1
(the fine-grained targeting: two-step, doom-blues, corridos, house…);
LAYER 0 = the UI rail (8–12 chips per market, chosen from Layer 1 by local
inventory — Austin's rail ≠ Nashville's rail). Search synonyms map spoken/
typed vocabulary onto all layers. Unmatched search terms feed taxonomy
growth (the voice-persona H5 loop). Everything is CONFIG, not code.
STATUS: RATIFIED & WIRED (2026-07-29) — resolves the G-VT taxonomy gap with the
R&B/Soul absence (exposed by voice persona #7) as its first proof case, now an
exact home (canonicalGenre("R&B") === "rnb-soul").

## Layer 1 — the canonical 18 (the "common standard" core)

Chosen as the working intersection of the three references for LIVE music
(dropping recorded-music-only categories like Soundtrack/Children's):

Rock · Pop · Hip-Hop/Rap · **R&B/Soul** · Electronic/Dance · Country ·
Latin · Jazz · **Blues** · **Folk/Americana** · Metal · **Punk** ·
**Reggae** · **Classical** · **World** · **Singer-Songwriter** ·
**Indie/Alternative** · Experimental

(Bold = new vs. today's 8. Today's 8 map losslessly into this set; no
migration pain — `Hip-Hop`→`Hip-Hop/Rap`, `Electronic`→`Electronic/Dance`,
rest identical.)

Why 18 and not 8 or 6,000: 8 was too coarse the first time a real spoken
search arrived ("R&B" had no home); 6,000 (Spotify's microgenre layer) is
an analysis layer, not a choice layer — no fan picks from 6,000 chips.
Eighteen is the tier every major platform's top level converges on, and it
is the layer artists/venues already use to describe themselves, which
matters because OUR genre data comes from extraction of their words.

## Layer 2 — fine-grained styles (where "more targeted" lives)

Open, curated tag vocabulary; every tag maps to ≥1 Layer-1 parent; a show
carries any number. Examples: two-step & western swing (→Country),
honky-tonk (→Country), doom/desert blues (→Blues, Rock), corridos &
norteño (→Latin), salsa/cumbia nights (→Latin, Electronic/Dance),
house/techno/DnB (→Electronic/Dance), bluegrass (→Folk/Americana),
neo-soul (→R&B/Soul), hardcore (→Punk, Metal), mariachi (→Latin, World).
Tags enter the vocabulary by evidence (artist self-description, venue
copy, unmatched searches) through normal review — never auto-created by
extraction on its own (the gate applies to taxonomy writes like any
candidate data).

## Layer 0 — the UI rail (what the thumb sees)

The genre rail and filter grid show 8–12 Layer-1 chips per market, picked
by actual local inventory share (Austin certainly surfaces Country and
Latin; a Berlin launch would surface Electronic/Dance's subgenres
differently). "All" always exists; every Layer-1 genre remains reachable
via search/voice even when not a chip. Rail composition is market config.

## Search & voice mapping

The synonym lexicon (voice-personas harvest item 1) targets ALL layers:
"R&B" → Layer-1 R&B/Soul (exact, once ratified — no more "closest to");
"dance music" → Electronic/Dance + dance-night tags; "Americana" →
Folk/Americana; "two-step" → the Layer-2 tag AND lesson-type events.
Every unmatched term is logged (count + verbatim) and reviewed weekly —
the taxonomy improves from what people actually say, which is the
founder's "improve on it re: searches people do" made mechanical.

## Data & pipeline impact

- `event.genres` becomes Layer-1 array + Layer-2 tag array (extraction
  captures the artist/venue's OWN words; mapping to canon is deterministic
  config the eval harness can regression-test).
- Golden set (Step 6) gains genre-mapping assertions.
- Trust screen: genre data is descriptive, from the act's/venue's own
  materials — never inferred sentiment, never a ranking dimension; the
  no-hierarchy rules are untouched.

## Sources

Apple Music genre codes (hierarchical, partner docs): https://itunespartner.apple.com/music/support/5318-updated-genre-codes ·
https://developer.apple.com/documentation/applemusicapi/music-genres —
Spotify's two-tier reality (a small official BROWSE layer over thousands of
microgenres). RECHECK 2026-07-29 (the hard pre-ratification gate, now cleared):
the "thousands of microgenres" claim is confirmed against the AUTHORITATIVE
source — Every Noise at Once (built by Glenn McDonald, Spotify's own genre-data
lead), which maps ~6,000 named genres: https://everynoise.com/ (background:
https://ca.billboard.com/business/streaming/spotify-s-former-data-alchemist-gives-every-song-a-genre).
The honest correction to the prior draft: that 6,000 figure comes from Every
Noise / Spotify's own data, NOT a "Spotify publishes 6,000 genres" doc page —
Spotify's OFFICIAL API surface is the smaller browse-categories layer
(https://developer.spotify.com/documentation/web-api). This STRENGTHENS the
design: 6,000 is an analysis layer, not a choice layer; 18 is the choose-from
tier. The earlier blog citation (spudart.org) is superseded by the two sources
above. Bandsintown live-event genre tagging + Spotify live-events integration:
https://www.artist.bandsintown.com/integrations/spotify

## Ratification (G-VT partial resolution) — CLOSED 2026-07-29

RESOLVED. The founder ratified the Layer-1 eighteen verbatim
("ratify-and-wire the 18 genres"). The HARD pre-ratification check — re-verify
the Spotify microgenre claim against authoritative data and upgrade the
citation — was completed (see Sources: Every Noise at Once + the official
browse API; the spudart blog is superseded). Layer 2 + Layer 0 + the lexicon
now proceed as config under normal gates. Wiring landed in the same change:
`web/lib/genres.ts` (18 + lossless today's-8 map + synonym lexicon +
`canonicalGenre`) and the derived Layer-0 rail on `/tonight`
(`genreFacet`/`applyFilters` in `web/lib/feed.ts`).
