# Source Catalog — Coverage Gap

`master_sources_catalog_120.json` currently has real, populated entries for ranks 1-76 and 119-120 (ticketing, venue_calendar, university_calendar, library_calendar, city_calendar, local_media, artist_aggregator, social, music_platform, link_hub, claimed_upload, email_opt_in, calendar_feed, community, directory, and search_benchmark categories, all Austin/CAPCOG-focused).

**Institutional non-music expansion (2026-07-24):** ranks 42-59 add real,
first-party, publicly-viewable structured event sources beyond live music —
universities (UT Austin Texas Performing Arts + the Localist master calendar,
Texas State Presents + main events, Austin Community College), Austin Public
Library, the City of Austin civic calendar, museums/visual arts (Blanton, The
Contemporary Austin, Mexic-Arte), theater/performing arts (ZACH, the Long
Center), film (Austin Film Society), literary (BookPeople), comedy (Cap City,
The Hideout, The Velveeta Room), and public-radio events (KUTX Presents). Every
one is the institution's OWN official events page/feed — no partner-gated APIs,
no login/paywall/bot-protection bypass (`explicitly_disallowed` rails preserved).
Structured-data method (ICS / Localist JSON / schema.org) is noted per entry via
`access_method`; where the exact structured-feed path was not confirmed the entry
points at the known first-party events page and is marked for verification. Two
additive honest fields carry the founder-requested detail: `cultural_domain` (the
OneLive domain hint — performing-arts, ideas, library, community, visual-arts,
theater, film, literary, comedy, live-music) and `county` (read by
`tools/real_source_probe.py`). Paramount/Stateside is already covered by rank 20
(austintheatre.org) and was not duplicated.

**Broadcast / periodical / venue expansion (2026-07-25):** ranks 60-76 add
17 more real, first-party, publicly-viewable Austin/Travis-county event sources
the founder catalogued — the "radio and tv stations and periodicals and all the
stuff we've previously discussed":
- **Radio (5):** KUT 90.5 events, KOOP 91.7 community radio, KLBJ 93.7 concerts,
  101X (KROX-FM) events, Austin City Limits Radio (fmr KGSR). Public-radio
  entries (KUT/KOOP) are non-commercial first-party; the three commercial
  stations are their OWN concert/events pages, flagged with a commercial-ToS
  caveat.
- **TV (4):** KVUE (ABC), KXAN (NBC), CBS Austin (KEYE), FOX 7 Austin (KTBC) —
  each station's OWN community-calendar page. These are USER-SUBMITTED calendars
  (low `verification_anchor_score`) on commercial sites; flagged accordingly.
- **Periodical (1):** CultureMap Austin events. (Austin Chronicle events is
  already rank 26 and was NOT duplicated.)
- **Venues (7):** Historic Scoot Inn, Cheer Up Charlies, The Far Out Lounge &
  Stage, Come and Take It Live, Elephant Room, C-Boy's Heart & Soul, and 3TEN
  ACL Live (distinct from the Moody Theater already at rank 14). Mohawk (12),
  Stubb's (13), Antone's (15), Empire (16), Continental Club (17), The Parish
  (18), Emo's (19), Saxon Pub (21), and Hotel Vegas (23) were already present and
  NOT duplicated.

Every one is the station's / publication's / venue's OWN official events page —
publicly viewable, no login, no paywall/bot-protection bypass
(`explicitly_disallowed` rails preserved; commercial-site entries additionally
carry a `tos_violation` disallow token pending an automated-access ToS check).
Structured-feed capability (ICS / schema.org JSON-LD) is honestly recorded as
`structured_feed_verify` (and `ics_feed_if_offered` / `jsonld_if_offered` where a
WordPress/Squarespace stack makes a feed likely) rather than assumed — where the
exact structured path was not confirmed the entry points at the known first-party
events page and is marked for verification. One additive honest field, `notes`,
carries the per-source legal / first-party posture. `cultural_domain` and `county`
follow the rank-42-59 convention.

**ToS-gated / partner-only aggregators are DELIBERATELY not added as crawl
targets** (and are already represented as KNOWN, non-crawlable entries): Do512 /
DoStuff (rank 25, partner data deal), Bandsintown (rank 27) and Songkick (rank 28,
partner-gated), and Eventbrite / Ticketmaster / SeatGeek (ranks 3 / 2 / 10, API
access only, not crawl). Austin American-Statesman / Austin360 was left out: it is
a Gannett property with a paywall and ToS-restrictive posture and no confirmable
first-party public event calendar. Austin Monthly was left out: no first-party
public structured events calendar could be confirmed (editorial "things to do"
roundups only). KUTX 98.9 is already covered as KUTX Presents (rank 59).

**Ranks 77-118 remain an explicit TODO gap** inherited from the reference build. Per the original spec note:

> "For a real production catalog you will expand ranks 42–118 with additional venue calendars (Austin + top target cities), ticketing platforms, local media, newsletters, and social APIs. The schema and policy rails above are the enforced contract."

When expanding, follow the same schema and priority-scoring model in `worker/source_rank.py`, and respect the `explicitly_disallowed` policy rails (no login/paywall/bot-protection bypass).

**Full-catalog / all-22-category / artist-spine expansion (2026-07-25):** ranks
77-114 add 38 more real, first-party, publicly-viewable Austin/CAPCOG sources
covering **every one of the 22 OneLive cultural categories** (live-music,
performing-arts, theater, comedy, visual-arts, film, literary, ideas,
festivals, food-drink, nightlife, dance, community, heritage, family,
place-based, sports, library, fairs-expos, seasonal, wellness, fashion-design)
plus the two founder-named entity types beyond venues: **orgs/institutions**
and **artists**. Each entry additively carries `entity_type`
(`"venue"` | `"org"` | `"artist"`) alongside the existing `county` /
`cultural_domain` / `notes` fields; `.get()`-only consumers
(`worker/importers/run_structured_import.py`, `brain/seed_acquisition.py`,
`tools/real_source_probe.py`) are unaffected by the new field.

- **Artist spine (1):** MusicBrainz (rank 77, `musicbrainz.org/ws/2/`) — the
  OPEN, no-key, 1-req/s artist/place/event data spine named in the founder's
  spec. Its `url-rels` are the cross-platform join; the artist -> upcoming-events
  join itself still runs through Bandsintown/Songkick, both already flagged
  PARTNER-GATED / non-crawlable at ranks 27-28 — MusicBrainz supplies artist
  identity (MBID), never a bypass of that gate.
- **Notable local performing-arts orgs (6):** Austin Symphony Orchestra, Ballet
  Austin, Austin Opera, Fusebox Festival (now biennial), Austin Chamber Music
  Center, Golden Hornet — each institution's own ticketing/events page.
- **Sports (4):** Round Rock Express (MiLB), Austin FC (MLS), Circuit of the
  Americas, Austin Spurs (NBA G League) — each on the team's/venue's own or
  league-sanctioned official schedule page (MiLB.com and NBA G League team
  pages are the sanctioned first-party host for every affiliated club, not a
  third-party aggregator).
- **Food & drink (3):** Austin Food & Wine Festival, SFC Farmers' Market
  (Sustainable Food Center, weekly Downtown + Sunset Valley), Texas Craft
  Brewers Festival.
- **Nightlife (3):** Elysium, Kingdom Nightclub, The Concourse Project — each
  venue's own dedicated events page (not a homepage).
- **Dance (1 new + Ballet Austin above):** Tapestry Dance Company.
- **Heritage (5):** Bullock Texas State History Museum, LBJ Presidential
  Library, Austin History Center Association, George Washington Carver Museum
  Cultural & Genealogy Center (City of Austin), Asian American Resource Center
  (City of Austin).
- **Family (2):** Thinkery (children's museum), Austin Nature & Science
  Center.
- **Visual arts (2 more):** UMLAUF Sculpture Garden & Museum, Elisabet Ney
  Museum (museum building is closed for renovation into spring 2027 — noted
  honestly; the programs/education page is recorded for when programming
  resumes).
- **Place-based (3):** Republic Square (Downtown Austin Alliance), Waterloo
  Greenway Conservancy / Waterloo Park (distinct from the commercial Moody
  Amphitheater box office, not duplicated), Mueller Austin parks & events.
- **Fairs & expos (3):** Rodeo Austin (Star of Texas Fair & Rodeo), Maker
  Faire Austin, Texas Book Festival.
- **Seasonal (2):** Austin Trail of Lights, Eeyore's Birthday Party.
- **Wellness (2):** Austin Yoga Festival (inaugural 2026), HAAM (Health
  Alliance for Austin Musicians).
- **Fashion & design (1):** Austin Fashion Week — its official schedule is
  hosted on Sched.com as the org's own chosen first-party platform (not a
  third-party aggregator of it).

Every entry's structured-feed capability is honestly recorded as
`structured_feed_verify` (ICS/JSON-LD not yet confirmed by fetch, since
WebFetch is blocked in this environment — only WebSearch results/snippets were
used to confirm the URL itself is real and first-party) rather than assumed.

**Honest gaps — could NOT fill with a verified first-party feed:**
- **Fashion & design** stays thin (1 source): no other first-party public
  structured events calendar could be found for an Austin-area fashion
  org/venue beyond Austin Fashion Week itself; Fashion Group International's
  Austin-specific chapter page could not be confirmed to exist.
- **Texas State Cemetery** was investigated for heritage but has no recurring
  public events calendar (tour scheduling only) — left out rather than padded.
- **Sharir + Bustamante Danceworks** (dance) is defunct (archived at UT
  Libraries) — not added.
- **Barton Springs Pool** (place-based) is a facility page, not an events
  calendar — left out.
- **The Belmont** (nightlife) has no confirmed dedicated events/calendar page
  on its own site (thebelmontaustin.com) beyond an "info" page — left out
  rather than guessing a path.
- **Container Bar** (nightlife) status is ambiguous in current search results
  (possible closure) — left out pending confirmation.
- Every new venue/org/festival entry recorded `structured_feed_verify`
  honestly rather than assuming ICS/JSON-LD support — this is a live TODO for
  whoever runs `worker/importers/run_structured_import.py` against them.

Of the original 77-118 gap, ranks 77-114 are now filled (38 entries); ranks
115-118 remain open for a future expansion pass (e.g. additional target cities
beyond Austin proper, or a second wave of artist-level entries once the
MusicBrainz -> local-artist join is built).
