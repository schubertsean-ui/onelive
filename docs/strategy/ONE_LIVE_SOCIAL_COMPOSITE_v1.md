# ONE LIVE — Social Composite v1: progressive enrichment into a solid picture (PROPOSAL)

Greppable summary: founder-directed 2026-07-22, verbatim brief: "closely
investigate what fields we can access and think in terms of progressive
data analysis via ingestion… How can we leverage a (potentially limited)
data set and using inference and patterns, build up a more robust data
set that goes thru structured enhancement processes that learn over time
how to interpret and define and search for other pieces of data to
enhance what we have until a solid picture comes together? This gets at
our confidence scoring in the background and foreground to be consistent
with our trust principles." STATUS: PROPOSAL. Companion reference (the
field-level platform investigation, verified against official docs
2026-07-22 with unverified items flagged):
`ONE_LIVE_PLATFORM_API_INVENTORY_2026-07.md`. Po harvest H2/H5/H6/H7/
H9/H10 land here (ONE_LIVE_SIGNAL_ACQUISITION_PO_NOTES_v1.md).

## 1. The object at the center: the entity dossier

A **dossier** is the composite picture for one entity (artist or venue).
It is not a row of facts — it is a set of FIELDS, each carrying its own
provenance:

    field = (value, source, source_record_id, fetched_at,
             license_class, agreement_score)

Nothing in a dossier is "true"; everything is *attributed*. The dossier
is BACKGROUND data (entity knowledge) and is structurally separate from
FOREGROUND event confidence (the ratified 4-state model on candidates) —
the same physics as Tastemaker separation: background never silently
becomes foreground.

## 2. The progressive enrichment engine (the founder's question, made mechanical)

**Seed → resolve → link-walk → quantify → verify → converge**, run
BETWEEN ingest cycles, off the hot path (po H5):

- **Seed (tier 0):** the first time an unknown artist/venue name appears
  in any candidate, a dossier STUB is created and an enrichment job is
  queued. The second sighting of that name lands corroboration-ready.
- **Resolve (tier 1):** match the name against the open identity spine —
  **MusicBrainz** (URL-relationships, MBID) and **Wikidata** (external-ID
  properties) — plus name-variant clustering (aliases, "y Los…", "The"
  stripping). Output: canonical identity + a fan-out of PROFILE LINKS.
- **Link-walk (tier 2):** the discovered links ARE the "search for other
  pieces of data" loop. Each cross-platform link field (MB url-rels;
  Wikidata P-IDs; Ticketmaster attraction `externalLinks`; Instagram
  Business Discovery `website`; X bio urls; Bandsintown
  `facebook_page_url` + `mbid`) yields new sources for THIS entity, and
  each fetched profile can expose further links — a bounded graph walk
  (depth-capped, per-entity budget).
- **Quantify (tier 3):** per-platform metrics land as fields: Spotify
  `genres[]`/`followers`/`popularity`; YouTube subscriber/video counts +
  descriptions (tour dates hide here); IG follower count + bio; Twitch
  live cadence; venue side: Google Places hours/geo/`businessStatus`/
  website, capacity from Wikidata. Soft ACTIVITY signals (po H10 — e.g.
  posting cadence, places business-status changes) are context fields,
  never event assertions.
- **Verify (tier 4):** cross-source agreement per field. Genre =
  weighted vote across Spotify genres, MusicBrainz tags, Last.fm tags →
  our taxonomy mapping. A venue address asserted by Places + its own
  site + Ticketmaster venue data three ways gets a high
  `agreement_score`; a single-source claim stays low. THIS is the
  background confidence number.
- **Converge (the stop rule, po H2):** every dossier carries a
  COMPLETENESS score (weighted coverage of the field checklist). Passes
  stop when marginal expected gain falls below threshold — the system
  polishes no star while the tail starves. The **wind vane** (po H7):
  enrichment attention re-points toward entities with rising signal
  (new sightings, upcoming candidates), ceiling-capped so the tail is
  never starved.

**"Learns over time," concretely and honestly:** (1) per-source
RELIABILITY PRIORS — when a source's claims keep agreeing with the
cross-source consensus, its weight rises; when it keeps losing votes,
it falls — learning as updated weights, fully inspectable, no black
box; (2) interpreter improvements are Kaizen-ledgered (a
mis-mapped genre class gets a counter-measure row like any other
defect); (3) query templates that yield join keys get promoted (the
standing-search library below). No model training on platform data —
several ToS forbid it and we don't need it.

## 3. Confidence: background and foreground, consistent with trust

- **Foreground (unchanged, ratified):** events are `unverified | likely
  | confirmed | disputed`, moved ONLY by the corroboration gate over
  candidate evidence. Dossier scores NEVER move an event state
  directly.
- **Background:** dossier fields carry `agreement_score` + provenance;
  displayed entity facts (artist links, venue hours) show their source
  the same way event uncertainty shows its "?" panel.
- **The one legitimate coupling — and it is founder-crucial:** using
  dossier data INSIDE gate3 (e.g. "the artist's own linked site lists
  this date" counting as a corroborating source class) changes gate
  inputs, which is a gate-custody/threshold decision. This spec
  PROPOSES that coupling as valuable (an artist's verified own-channel
  is a legitimate second source) but it ships only with explicit
  founder ratification, per the charter.
- Display rules inherit canon: lens-never-gate, provenance on every
  recommendation, no pay-to-rank, disputed shown never hidden.

## 4. Keyword search on API datasets — yes; the standing-search library

Direct answer to "Are there key word searches we can perform on the API
datasets?": the searchable surfaces, from the verified inventory:

| Platform | Search shape | Example standing query |
|---|---|---|
| Ticketmaster Discovery | keyword + city/geo/DMA + genre + date | `keyword=*, city=Austin, classificationName=Music, startDateTime=tonight` |
| YouTube Data API | free-text + location radius | `q="Austin" "live" tour, location=30.27,-97.74, radius=50km` |
| Threads | keyword + tag search (2,200 q/day) | `"just announced" Austin`, `#atxmusic` |
| SeatGeek | free-text + venue.city + taxonomy | `q=*, venue.city=Austin, taxonomies.name=concert` |
| MusicBrainz | Lucene on artist/place/event | `place:(Austin) AND type:venue` |
| Wikidata SPARQL | arbitrary structured queries | "all Austin music venues with coordinates + websites" |
| Spotify | artist name search | resolve-time only |
| Instagram | hashtag search (30 tags / 7 days) | `#atxlivemusic` top/recent — budget-precious |
| Reddit | sub-scoped full text | `r/Austin "tonight" flair:events` (commercial tier $) |
| X v2 | full operators, pay-per-read | bounded artist-list lookups only, not monitoring |
| Twitch | channel/category search | music category live in Austin (thin) |

Standing queries run on schedules with per-platform budget ceilings
(same §14.3 discipline as extraction spend), and their yield feeds the
same source-rotation lifecycle — a query that stops producing gets
demoted.

## 5. The platform map in one view (detail: the inventory doc)

- **Open-signup spine (Phase A, build first):** MusicBrainz · Wikidata ·
  Ticketmaster Discovery · Spotify · Google Places · YouTube · Wayback
  CDX (historical backfill) · Eventbrite venue-ID polling. Covers ~90%
  of the cross-platform link graph with instant keys.
- **Application-gated (Phase B, apply early — lead times):** Instagram/
  Threads (Meta app review) · Bandsintown partnership (THE artist-events
  feed; ToS requires written consent) · SeatGeek · Setlist.fm
  (commercial terms) · SoundCloud (Artist Pro + review).
- **Opt-in / claimed-channel (Phase C, product features not crawlers):**
  Facebook Page events via venue-granted tokens (the richest closed
  source — build as "connect your Facebook Page" in venue claiming) ·
  TikTok Display API via artist-connects-account · Discord bot by
  invitation · TixR per-venue authorization.
- **Partnership conversations (founder-led when ripe):** Do512/DoStuff
  (Austin-native, high value) · Dice.fm · Resident Advisor · AXS
  (Moody Center!).
- **Skip for now:** Snapchat (allowlist, thin), Bandcamp (no discovery
  API — get Bandcamp URLs from MusicBrainz instead), Last.fm events
  (removed), Songkick (closed to new keys — revisit via partnership).

## 6. Compliance as data (po H9)

Every API source row carries `license_class` fields: display allowed?
cache/retention window (Google Places ~30 days on most fields; YouTube
statistics refresh windows)? attribution required (Ticketmaster display
rules)? training prohibited (Spotify)? The pipeline REFUSES to persist
or surface a field whose license row forbids it — compliance enforced
mechanically, not remembered. Scraping-prohibited platforms are never
fetched outside their APIs; the Linktree-as-public-webpage question is
flagged as a legal-posture decision for the founder, default NO until
decided.

## 7. Build phases and the founder decision list

Phase A needs only founder-minted keys (Ticketmaster, Google Cloud,
Spotify, YouTube — each self-serve, minutes each) and ships: dossier
schema + migration, resolve/link-walk/quantify/verify workers on the
enrichment queue, completeness scoring, the first standing queries
(Ticketmaster Austin nightly sweep is instantly a new top-tier event
source alongside scraping-free provenance).

**Founder decisions:**
1. Mint Phase-A keys (list above — all free tiers; Google requires a
   billing account with the free-tier caps noted in the inventory).
2. Approve the Bandsintown partnership application (we apply in
   OneLive's name — their stated partner category fits us).
3. Legal posture: Linktree-page fetching (default no), and the standing
   rule "official APIs only, opt-in for closed platforms" — say the
   word and it's the recorded posture.
4. Ratify (or defer) the gate-coupling: artist/venue OWN-channel claims
   as a corroborating source class in gate3 — a gate-input change,
   yours alone.
