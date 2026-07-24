# ONE LIVE — Category Taxonomy & Volume Architecture v1 (PROPOSAL, 2026-07-24)

Founder directive (2026-07-24): "we probably need a genre equivalent for the
other 20+ categories and sub categories — research those. The categorization and
architecture will be important to manage volume going forward [or] lose UX value."
Plus: a less-detailed card / 2-line listing for events far out in time.

This doc is the research answer: (A) the genre-equivalent SUB-CATEGORY taxonomy
for every one of the 22 cultural domains, (B) how external provider taxonomies
(Ticketmaster now, SeatGeek/others later) map into it, and (C) the volume
architecture — time-tiered card density + facet model — that keeps a
high-volume feed legible. Code source of truth for the machine mapping:
`worker/importers/domain_map.py`; this doc is the human reference it mirrors.

## A. The 22 domains and their genre-equivalents (sub-categories)

Music already has "genres" (jazz, rock, cumbia…). Each domain below gets the
same: a small, human-meaningful set of sub-categories that (1) match how that
field describes itself, (2) are stable enough to filter on, and (3) map cleanly
from provider taxonomy. These are the FILTER facets and the card's "focus" line.

1. **Live Music** — Rock · Pop · Hip-Hop/Rap · Country/Honky-tonk · Jazz ·
   Blues · R&B/Soul · Funk · Folk/Americana · Bluegrass · Electronic/Dance ·
   Latin/Cumbia · Metal · Punk · Reggae · Gospel · World · Indie/Alternative ·
   Classical-crossover · Experimental
2. **Symphony · Opera · Ballet** — Symphony/Orchestral · Opera · Ballet ·
   Chamber · Choral · Early/Baroque · Contemporary-classical · Recital/Art-song
3. **Theater** — Play/Drama · Comedy · Musical · Shakespeare/Classical ·
   Experimental/Avant-garde · Immersive · Solo/Monologue · Youth (TYA) ·
   Touring Broadway · Performance Art
4. **Comedy** — Stand-up · Improv · Sketch · Open Mic · Storytelling ·
   Variety/Magic · Roast · Live Podcast
5. **Visual Arts & Museums** — Painting · Sculpture · Photography ·
   New-Media/Digital · Installation · Mixed-Media · Craft/Ceramics ·
   Exhibition Opening · Open Studios · Public Art · Gallery Talk
6. **Film & Cinema** — Premiere/First-run · Repertory/Classic · Documentary ·
   Foreign/World · Experimental/Short · Animation · Festival · Outdoor/Drive-in ·
   Screening + Q&A
7. **Literary & Readings** — Author Talk/Reading · Poetry · Book Launch ·
   Book Club · Storytelling · Spoken-Word/Slam · Writing Workshop · Zine/Small-press
8. **Lectures · Debates · Ideas** — University Lecture · Public Forum ·
   Science/Tech · Civic/Policy · History/Heritage · Philosophy · Debate · Panel ·
   Business/Economics
9. **Festivals** — Music · Arts · Film · Food/Drink · Cultural/Heritage ·
   Street/Community · Craft/Maker · Seasonal
10. **Food & Drink** — Tasting/Pairing · Restaurant Week · Brewery/Distillery/Winery ·
    Farmers Market · Pop-up/Supper Club · Food Truck · Cooking Class · Food Festival
11. **Nightlife & Clubs** — DJ Night · Dance Party · Rooftop/Lounge ·
    Themed Night · Drag/Cabaret · Karaoke · Late-night
12. **Dance** — Concert/Contemporary · Ballet · Social/Partner (Salsa/Swing/Tango) ·
    Folk/Traditional · Hip-hop/Street · Tap · Ballroom · Class/Workshop
13. **Community & Block Parties** — Block Party · Neighborhood Market · Street Fair ·
    Parade · Volunteer/Mutual-aid · Civic Meeting · Service/Cleanup
14. **Heritage & Identity** — Cultural Celebration · Indigenous · LGBTQ+ ·
    Faith/Spiritual · Immigrant/Diaspora · Historical Commemoration · Language/Culture
15. **Family & Youth** — Children's Museum · Storytime · All-ages Show ·
    Youth Program/Camp · Zoo/Aquarium · Puppetry/Magic · Carnival/Fair · Educational Play
16. **Place-based & Tours** — Walking Tour · Nature Program · Historic Site ·
    Garden/Arboretum · Night Sky/Observatory · Boat/Bike Tour · Food Tour · Themed Tour
17. **Sports & Spectacle** — Pro Game · College Game · Racing (horse/auto) ·
    Marathon/Run · Amateur/Rec · Motorsport · Combat (MMA/Boxing) · Extreme ·
    Esports · Spectacle (circus/ice show)
18. **Library Programs** — Author Event · Film Series · Maker/Tech · ESL/Citizenship ·
    Kids' Program · Book Club · Job/Skills · Genealogy
19. **Fairs · Expos · Cons** — Convention · Comic/Anime Con · County/State Fair ·
    Trade Show · Craft Market · Home/Garden Expo · Job Fair · Collector/Hobby Expo
20. **Seasonal & Ritual** — Holiday Lights · Seasonal Market · Civic Ritual ·
    First Night/NYE · Nature Ritual (bloom/migration) · Religious Observance ·
    Harvest/Solstice
21. **Wellness & Outdoor** — Yoga/Meditation · Run Club · Sound Bath ·
    Outdoor Adventure/Hike · Fitness Class · Wellness Market · Cycling · Retreat
22. **Fashion · Design · Maker** — Fashion Show · Design Week · Maker Market ·
    Craft Fair · Pop-up Shop · Vintage/Flea · Textile/Jewelry · Product Launch

**The gap we resolved:** magic, circus, and "specialty acts" don't fit music or
theater cleanly. Rather than invent a 23rd domain, they route by audience —
family-oriented spectacle (circus, puppetry, ice shows) → **Family & Youth**;
adult variety/magic → **Comedy** (Variety/Magic); large arena spectacle →
**Sports & Spectacle** (Spectacle). This is a mapping decision, logged here so it
is not silent. Genuinely unclassifiable provider taxonomy stays **`unmapped`**
(shown as "Other"), never force-fit — the honest floor.

## B. Provider taxonomy → our domains (the mapping layer)

External feeds carry their own taxonomy; the importer translates deterministically
(`domain_map.py`), never by AI, with visible `UNMAPPED[...]` markers for gaps:

- **Ticketmaster**: segment (Music/Sports/Arts&Theatre/Film/Miscellaneous) →
  coarse domain; genre refines Arts&Theatre + Miscellaneous (Theatre→Theater,
  Classical/Opera→Symphony·Opera·Ballet, Comedy→Comedy, Dance/Ballet→Dance,
  Children's Theatre/Circus→Family, Fine Art→Visual Arts, Fairs&Festivals→
  Festivals, Lecture/Seminar→Ideas, Health/Wellness→Wellness, …). Music genre =
  the sub-category directly (Jazz, Rock…).
- **SeatGeek**: event `type` → domain; primary performer's first genre → sub-category.
- **Our pipeline (long tail)**: the extractor assigns (domain, sub-category) from
  source context; anything uncertain is `unmapped`, surfaced for review — never
  fabricated.

## C. Volume architecture — keep a big feed legible

At 800 ticketed events for one metro (and far more once the long tail lands), raw
volume will bury value. Two mechanisms:

### C1. Time-tiered card density (founder's "2-line listing" idea)
Card richness scales INVERSELY with how far out an event is — attention is
scarcest for tonight, and far-future events need only enough to decide "save it?":

| Time band | Card | Fields shown |
|---|---|---|
| **Tonight / this week** | Full card | image, name, spark line, genre, venue + address, time, price, "hear it", trust affordance |
| **~1 week → ~1 month** | Compact card | name, genre/focus, venue name, time, price |
| **> ~1 month out** | 2-line listing | name · genre/focus — venue name · date · price |

Thresholds are a FOUNDER-SET dial (recommended default: rich ≤ 7 days, compact
8–30 days, line > 30 days). The data model already carries `start_time`, so this
is a pure presentation tier — no schema change.

### C2. Facet model (how filtering stays sane at volume)
Every event is addressable by a small, orthogonal facet set so the feed can slice
without a combinatorial menu: **domain** (the 22) → **sub-category** (this doc) ·
**date/time band** · **area/neighborhood** (from geo) · **price** (free/ticketed/range)
· **provenance/confidence** (trust). "Focus" on a card = domain + sub-category in
one phrase ("Jazz", "Symphony", "University Lecture"). This is what makes 800+
events feel like "everything, findable" instead of a wall.

## Status & next
PROPOSAL. C encodes the founder's time-tiered idea; the sub-category lists are
mirrored into `domain_map.py` (`DOMAINS` sub-tuples). Open founder dial: the
time-band thresholds (C1). Coverage metric to watch: the `unmapped` share per
import (logged every run) trends toward zero as the mapping tables fill.
