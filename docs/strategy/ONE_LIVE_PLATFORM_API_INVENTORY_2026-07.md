# Platform API inventory — snapshot 2026-07-22 (reference for ONE_LIVE_SOCIAL_COMPOSITE_v1)

Greppable summary: field-level investigation of official programmatic
access across social, music-native, event, and web-presence platforms,
compiled 2026-07-22 by agent research against official docs; every claim
that could not be verified from a fetchable official page is FLAGGED.
Official APIs and sanctioned access only. This is a dated SNAPSHOT —
platform terms move; re-verify flagged items before building on them.

## Social

- **TikTok** — Display API (open signup; OAuth per-user: reads only for
  users who authorize — i.e. artist-connects-account): user info
  `display_name, avatar_url, bio_description, profile_deep_link,
  follower/likes/video counts (stats scope)`, own-video lists. No
  events/location/cross-links; no public keyword search for commercial
  devs (Research API = academics only; Commercial Content API = ad
  library only). Scraping prohibited. Role: opt-in enrichment only.
- **Instagram (Graph/Platform)** — Meta app + review; **Business
  Discovery** reads any PROFESSIONAL account's public
  `username, name, biography, website (often Linktree!),
  followers_count, media (captions, timestamps, counts)`. **Hashtag
  search**: 30 unique tags per 7 days per user. No user/event search.
  Scraping prohibited (aggressively enforced).
- **Facebook (Graph)** — the richest venue-event source is effectively
  CLOSED: no public event search since 2018; `/{page}/events` needs the
  venue's own Page token or the review-gated Page Public Content
  Access. Fields if granted: full event objects (name, start/end,
  place+geo, ticket_uri, counts). Role: venue-opt-in feature
  ("connect your Facebook Page"), not a crawler.
- **X / Twitter v2** — 2026: pay-per-use default (~$0.005/post read;
  free read tier gone; Basic/Pro closed to new signups) — UNVERIFIED
  against developer.x.com directly, check before budgeting. User
  objects expose bio `url`/entities urls (Linktree). Recent search has
  full operators but is metered. Role: bounded artist-list bio-link
  enrichment only.
- **YouTube Data API** — open; `channels.list` (subs/views/topic
  categories≈genre), `videos.list` (descriptions carry tour dates),
  and REAL free-text `search.list` with location+radius. 10k units/day
  (search=100 units). Stored stats have refresh/delete windows.
- **Threads** — Meta app; public **keyword + tag search** (2,200
  q/24h/user) — the most open Meta full-text surface.
- **Reddit** — Nov-2025 policy: all devs pre-approved; commercial
  ~$0.24/1k calls (UNVERIFIED exact terms). Sub-scoped full-text
  search. Role: r/Austin chatter as soft signal.
- **Discord** — bot sees only servers it's INVITED to (Guild Events
  incl. location). Developer Policy prohibits mining. Role: venue
  invites the 1Live bot, opt-in only.
- **Twitch** — open Helix API; channel/category search, live status,
  music category. Thin for events.
- **Snapchat** — allowlist-gated Public Profile API. Skip v1.

## Music-native

- **MusicBrainz** — OPEN (no key; 1 req/s; dumps). Artist/place/event
  entities; **`url-rels` = the cross-platform spine** (homepage,
  Bandcamp, SoundCloud, YouTube, Spotify, IG/FB/X/TikTok, Songkick,
  Bandsintown, setlist.fm, Discogs, Wikidata, Last.fm). Lucene search
  on everything. START HERE.
- **Spotify Web API** — open key; artist `name, genres[], popularity,
  followers` (best genre signal anywhere); artist search. Post-2024
  lockdown killed related-artists/recommendations/audio-features for
  new apps. No cross-links, no events. ML training on data prohibited.
- **Apple Music** — $99/yr program; genreNames, editorial notes; no
  followers/events/links. Secondary.
- **Bandcamp** — NO discovery API (label/merch partners only). Get
  Bandcamp URLs from MusicBrainz instead.
- **SoundCloud** — API reopened but gated (Artist Pro subscription +
  manual review). Users incl. `city`, followers; track search.
- **Last.fm** — open key; tags (crowd-genre), listeners, similar;
  events endpoints REMOVED years ago. Non-commercial default terms.
- **Bandsintown** — THE artist→upcoming-events feed (`datetime, venue
  {name,city,lat,long}, lineup[], offers[ticket urls]`, artist
  `facebook_page_url, mbid, tracker_count`) but ToS gates use to
  artists/partners: **apply for partnership** (event-discovery apps are
  their stated category). No keyword/location search publicly.
- **Songkick** — CLOSED to new API keys (support confirms; partnerships
  only). Plan around it.
- **Setlist.fm** — free key, NON-COMMERCIAL default (commercial by
  arrangement); setlists keyed by MBID (MusicBrainz join), venue
  entities with geo; historical who-played-where, not upcoming.

## Event platforms

- **Ticketmaster Discovery** — open instant key; **the best open event
  search**: `keyword, city, latlong+radius, dmaId (Austin=222 —
  verify), classificationName/genreId, startDateTime…`; events carry
  venues (geo) + attractions; **attraction `externalLinks`** exposes
  the artist's other profiles (twitter/instagram/facebook/wiki/homepage
  confirmed; youtube/spotify/itunes/lastfm/musicbrainz per live
  responses — VERIFY with one call). 5k calls/day, 5 rps free.
  Display/attribution rules apply.
- **Eventbrite** — public event SEARCH REMOVED (2020, never restored);
  can still poll KNOWN venue/organizer IDs for full event objects.
  Rate ~1k/hr/token (UNVERIFIED).
- **SeatGeek** — self-serve key (issuance status UNVERIFIED — test);
  event search `q, venue.city, taxonomies.name, geo`; performers carry
  `genres[]`, popularity `score`. Second open event search.
- **Dice.fm / Resident Advisor / AXS / TixR** — no public APIs;
  partner/venue-scoped only. Partnership conversations (AXS matters:
  Moody Center; TixR: several Austin rooms). RA GraphQL is unsanctioned.
- **Do512 / DoStuff** — no documented public API (legacy references
  exist, UNVERIFIED); Austin-native — direct data partnership is the
  realistic, high-value route.
- **Meetup** — GraphQL behind Meetup Pro; keyword+geo search. Marginal
  (open mics/jams).

## Web-presence

- **Google Places (new)** — venue ground truth: `displayName,
  formattedAddress, location, types/primaryType (night_club, bar,
  performing_arts_theater), regularOpeningHours, websiteUri,
  businessStatus (CLOSED_PERMANENTLY!), rating, userRatingCount`; Text/
  Nearby search. Post-2025 pricing: per-SKU free tiers (10k Essentials
  /5k Pro/1k Enterprise per month) — field-mask discipline decides the
  SKU. Retention: most content ≤30 days (place IDs indefinitely).
- **Yelp Fusion** — free tier ENDED; $7.99+/1k calls. Google Places
  covers the need cheaper. Skip.
- **Foursquare** — v3 deprecated May 2026; free tier shrinking to 500
  Pro calls/mo. NOTE: FSQ Open Source Places dataset (100M+ POI, free
  download — verify at opensource.foursquare.com) may be the useful
  artifact, not the API.
- **Linktree** — NO read API; scraping against ToS. Sanctioned reach:
  the IG/X `website` field POINTS at it; fetching the page itself is a
  legal-posture decision (default NO until the founder rules).
- **Wikipedia/Wikidata** — OPEN; SPARQL over external-ID properties
  (Spotify P1902, X P2002, Instagram P2003, Facebook P2013, YouTube
  P2397, MusicBrainz P434, Apple Music P2850, SoundCloud P3040,
  Bandcamp P3283, TikTok P7085; Songkick/Bandsintown/setlist.fm
  P-numbers UNVERIFIED — query "external identifiers"). Venues:
  coordinates, capacity, official website. CC0. The second spine.
- **Internet Archive Wayback CDX** — open; enumerate + retrieve
  historical snapshots of venue calendars (`/cdx/search/cdx?url=…`),
  ~1 req/s courtesy. Sanctioned backfill/provenance source.

## Ranking (composite-profile value × accessibility)

1 MusicBrainz · 2 Ticketmaster Discovery · 3 Wikidata · 4 Spotify ·
5 Google Places · 6 Bandsintown (conditional on partnership) ·
7 Setlist.fm+SeatGeek pair · 8 YouTube · 9 Instagram Business
Discovery · 10 Threads keyword search. (Facebook Events would rank #1
on value but is venue-opt-in only. Wayback CDX: backfill workhorse.)

**Key joins:** MBID ties MusicBrainz ↔ setlist.fm ↔ Bandsintown ↔
Wikidata; Wikidata ties everything else. Starting from MusicBrainz +
Wikidata and enriching via Ticketmaster + Spotify + IG Business
Discovery covers ~90% of the link graph on open-signup APIs alone.

## Explicitly unverified (one test call / dashboard visit each)

X pay-per-use exact terms · Meta Page Public Content Access current
review criteria · SeatGeek new-credential issuance · Ticketmaster
externalLinks full provider list · Do512/DoStuff API existence ·
Wikidata P-numbers for Songkick/Bandsintown/setlist.fm · Eventbrite
per-token rate limit · TikTok Display API exact quotas · FSQ OS Places
dataset terms.
