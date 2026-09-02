# CAPCOG Entity Census

Universe of entities already known to One Live, plus their official doors. One-time, read-only census of every row already committed in `sources/master_sources_catalog_120.json` (180 entries) — no source was added, removed, or re-scored to build this table, no site was fetched, and nothing here changes ingest, the orchestrator, or the catalog file itself.

Per ONE-LIVE-COVERAGE-LAW.md, CAPCOG is the test locale and a view filter, not a catalog border — this census is the whole catalog, not a filtered subset. Every row already committed appears below; none was dropped.

**Method:** `bucket` is read directly off the catalog's own declared `access_method`/`allowed`/`explicitly_disallowed` fields via the existing `worker/sourcing/source_class.py::classify_entry()` — the same classifier `tools/class_d_queue.py` already uses to produce `docs/CLASS_D_CLAIM_QUEUE.md`, reused here rather than re-derived, so this census cannot silently disagree with that document about what class D means. `grade` and `next_action` are new to this document: a small rule table keyed on the catalog's `category`/`access_method`/`allowed` fields (full mapping in the Legend), with two named-row overrides where a catalog `category` doesn't match the row's real function, and one row graded `unknown` rather than forced into a poor fit. See STATE.md Session Contract #53 for the complete rule table and the reasoning behind every non-obvious call.

## Legend

**Bucket** (ONE-LIVE-COVERAGE-LAW.md, "Source classes" — reused verbatim, not redefined here):

| bucket | meaning |
| --- | --- |
| A | structured open — ICS, RSS, public API, CSV, JSON-LD |
| B | public HTML — loads without login |
| C | public visual — flyer/PDF/public poster (deferred by Coverage Law, "later"; zero rows today) |
| D | closed door — login/paywall/bot wall; do not fetch, claim/submit path only |
| E | first party — claimed ICS/calendar/CSV, or an opt-in social/email link |
| F | human report — link or photo submit (a submission channel, not a catalog entity; zero rows today) |

**Grade** (new to this census — answers "whose truth is this row?", independent of bucket):

| grade | meaning |
| --- | --- |
| official | the entity's own first-party presence (venue, org, artist, city/civic, or a claimed feed) |
| trusted_publisher | local journalism/broadcast covering events, not hosting them |
| aggregator_lead | a ticketing/listing/identity platform that republishes or points at other sources |
| social | a social-platform API (Instagram/Facebook/TikTok/YouTube) |
| unknown | doesn't fit the other four honestly |

**next_action** (answers "what does a human/agent do with this row next?"):

| next_action | meaning | how it's assigned |
| --- | --- | --- |
| fetch | ready to ingest as a primary source | bucket A/B, grade official or trusted_publisher |
| follow | use as a lead, never as the listing itself (Coverage Law: search/aggregators may only propose official URLs) | bucket A/B, grade aggregator_lead or social |
| claim | needs a person to run the existing `/ops/claim` flow (paste a feed URL, upload a CSV, or link a claimed account) | bucket E, non-email |
| subscribe-inbox | needs a person to subscribe the newsletter into the shared inbox (see below) | bucket E, email-forward |
| blocked-D | closed door — do not fetch; already tracked in `docs/CLASS_D_CLAIM_QUEUE.md` | bucket D, always |
| unknown | not enough signal to assign the above | bucket C/F, or grade unknown |

## Newsletter path

For the one `subscribe-inbox` row below ("Opt-in Email Forwarding (Venue Schedules)") and any future venue newsletter subscription: **one shared inbox, foldered by source — never a per-venue account.** A person subscribes the venue's newsletter using that one inbox address, files it into a folder named for the source (matching its catalog `id`), and the existing claim intake (`worker/claim/intake.py`, `docs/CLASS_D_CLAIM_QUEUE.md` appendix E) picks it up from there. This is the manual, zero-new-service interim: no venue login, credential, or account is ever created to read a newsletter. The founder-scoped future state (many addresses, one per subscription, routed automatically) is already specced in `docs/strategy/ONE_LIVE_INGEST_INBOX_v1.md` — still a PROPOSAL, standing on its own founder decisions (new service + domain custody), and out of scope for this docs-only session.

## Summary

**180 entities total** (catalog cap — nothing added beyond what was already committed).

| bucket | count | | grade | count | | next_action | count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 21 | | aggregator_lead | 21 | | blocked-D | 14 |
| B | 140 | | official | 142 | | claim | 4 |
| D | 14 | | social | 4 | | fetch | 151 |
| E | 5 | | trusted_publisher | 12 | | follow | 10 |
|  |  | | unknown | 1 | | subscribe-inbox | 1 |

**CAPCOG/Hill-Country boundary** (`worker/region/capcog.py::CAPCOG_COUNTIES`, 14 counties): 135 rows carry a county already inside that boundary. 44 rows carry no county at all (mostly non-venue rows — publishers, aggregators, platform APIs — that aren't tied to one place). 1 row names a county the boundary module doesn't decide either way: rank 141, Wedding Oak Winery, `county: "san saba"` — San Saba is a real, legally-seen source and Coverage Law keeps it (CAPCOG is a view filter, not a catalog border); it simply sits outside the current 14-county module, same as any other honestly-unknown place (`worker/region/capcog.py`'s tri-state design reports this rather than guessing). Not a defect to fix in this session — Must-not covers catalog edits — noted here so it isn't rediscovered as a surprise.

## Official first-party sources (142)

The entity's own calendar, box office, ticketing page, civic page, or claimed feed — the venue/org/artist telling us about itself, directly.

| name | official_url | bucket | grade | next_action |
| --- | --- | --- | --- | --- |
| SXSW Official Schedule | <https://schedule.sxsw.com/> | A | official | fetch |
| Mohawk Austin | <https://mohawkaustin.com/> | A | official | fetch |
| Stubb's Austin | <https://www.stubbsaustin.com/> | B | official | fetch |
| ACL Live at The Moody Theater | <https://www.acllive.com/> | B | official | fetch |
| Antone's Nightclub | <https://antonesnightclub.com/> | B | official | fetch |
| Empire Control Room & Garage | <https://empireatx.com/> | B | official | fetch |
| The Continental Club (Austin) | <https://continentalclub.com/austin> | B | official | fetch |
| The Parish Austin | <https://parishaustin.com/> | B | official | fetch |
| Emo's Austin | <https://emosaustin.com/> | B | official | fetch |
| Paramount Theatre (Austin) | <https://www.austintheatre.org/> | B | official | fetch |
| The Saxon Pub | <https://saxonpub.com/> | B | official | fetch |
| The White Horse (Austin) | <https://thewhitehorseaustin.com/> | B | official | fetch |
| Hotel Vegas | <https://hotelvegasaustin.com/> | B | official | fetch |
| Visit Austin Events | <https://www.austintexas.org/events/> | A | official | fetch |
| Claimed Venue Upload (ICS/CSV) | _(none — first-party intake, no URL)_ | E | official | claim |
| Opt-in Email Forwarding (Venue Schedules) | _(none — first-party intake, no URL)_ | E | official | subscribe-inbox |
| Google Calendar (Claimed OAuth) | <https://developers.google.com/calendar> | D | official | blocked-D |
| Texas Performing Arts (UT Austin) | <https://texasperformingarts.org/events/calendar/> | A | official | fetch |
| UT Austin Events Calendar (Texas Today, Localist) | <https://calendar.utexas.edu/> | A | official | fetch |
| Texas State Presents (Texas State University) | <https://txstatepresents.universitytickets.com/> | B | official | fetch |
| Texas State University Main Events | <https://events.txst.edu/> | A | official | fetch |
| Austin Community College Events Calendar | <https://students.austincc.edu/calendars/acc-events-calendar/> | B | official | fetch |
| Austin Public Library Events | <https://library.austintexas.gov/events/calendar> | A | official | fetch |
| City of Austin Events (austintexas.gov) | <https://www.austintexas.gov/events> | A | official | fetch |
| Blanton Museum of Art | <https://blantonmuseum.org/calendar_events> | B | official | fetch |
| The Contemporary Austin | <https://thecontemporaryaustin.org/> | B | official | fetch |
| Mexic-Arte Museum | <https://mexic-artemuseum.org/upcoming-events-calendar/> | B | official | fetch |
| ZACH Theatre | <https://www.zachtheatre.org/> | B | official | fetch |
| The Long Center for the Performing Arts | <https://thelongcenter.org/calendar/> | B | official | fetch |
| Austin Film Society (AFS Cinema) | <https://www.austinfilm.org/calendar/> | B | official | fetch |
| BookPeople Events | <https://bookpeople.com/upcoming-events> | A | official | fetch |
| Cap City Comedy Club | <https://www.capcitycomedy.com/> | B | official | fetch |
| The Hideout Theatre | <https://hideouttheatre.com/> | B | official | fetch |
| The Velveeta Room | <https://www.thevelveetaroom.com/shows> | B | official | fetch |
| Historic Scoot Inn | <https://www.scootinnaustin.com/> | B | official | fetch |
| Cheer Up Charlies | <https://cheerupcharlies.com/> | A | official | fetch |
| The Far Out Lounge & Stage | <https://www.thefaroutaustin.com/events.html> | B | official | fetch |
| Come and Take It Live | <https://www.comeandtakeitlive.com/> | B | official | fetch |
| Elephant Room | <https://elephantroom.com/calendar> | B | official | fetch |
| C-Boy's Heart & Soul | <https://www.cboys.com/calendar> | A | official | fetch |
| 3TEN ACL Live (Austin City Limits Live) | <https://www.acllive.com/events/venue/acl-live-at-3ten> | B | official | fetch |
| Austin Symphony Orchestra | <https://my.austinsymphony.org/events?view=list> | B | official | fetch |
| Ballet Austin | <https://my.balletaustin.org/events> | B | official | fetch |
| Austin Opera | <https://my.austinopera.org/events?view=list> | B | official | fetch |
| Fusebox Festival | <https://fuseboxlive.com/> | B | official | fetch |
| Austin Chamber Music Center / Festival | <https://austinchambermusic.org/concert-season/> | B | official | fetch |
| Golden Hornet | <https://www.goldenhornet.org/calendar> | B | official | fetch |
| Round Rock Express (MiLB) | <https://www.milb.com/round-rock/schedule> | B | official | fetch |
| Austin FC (MLS) | <https://www.austinfc.com/schedule/> | B | official | fetch |
| Circuit of the Americas (COTA) | <https://circuitoftheamericas.com/events/> | B | official | fetch |
| Austin Spurs (NBA G League) | <https://austin.gleague.nba.com/schedule> | B | official | fetch |
| Austin Food & Wine Festival | <https://www.austinfoodandwinefestival.com/> | B | official | fetch |
| SFC Farmers' Market (Sustainable Food Center) | <https://sustainablefoodcenter.org/farmers-markets-support/sfc-farmers-markets/> | B | official | fetch |
| Texas Craft Brewers Festival | <https://texascraftbrewersfestival.org/> | B | official | fetch |
| Elysium | <https://www.elysiumonline.net/events.html> | B | official | fetch |
| Kingdom Nightclub | <https://kingdomnightclub.com/events/> | B | official | fetch |
| The Concourse Project | <https://concourseproject.com/calendar/> | B | official | fetch |
| Tapestry Dance Company | <https://tapestry.org/season-shows> | B | official | fetch |
| Bullock Texas State History Museum | <https://www.thestoryoftexas.com/calendar/> | B | official | fetch |
| LBJ Presidential Library | <https://www.lbjlibrary.org/events> | B | official | fetch |
| Austin History Center Association | <https://austinhistory.org/events/> | B | official | fetch |
| George Washington Carver Museum, Cultural & Genealogy Center | <https://www.austintexas.gov/carver/events> | B | official | fetch |
| Asian American Resource Center (AARC) | <https://www.austintexas.gov/aarc/asian-american-resource-center-event-calendar> | B | official | fetch |
| Thinkery (Austin Children's Museum) | <https://my.thinkeryaustin.org/events> | B | official | fetch |
| Austin Nature & Science Center | <https://www.austintexas.gov/parks/austin-nature-science-center-camps-events-and-community-programs> | B | official | fetch |
| UMLAUF Sculpture Garden & Museum | <https://www.umlaufsculpture.org/programs> | B | official | fetch |
| Elisabet Ney Museum | <https://www.austintexas.gov/ney/programs-education> | B | official | fetch |
| Republic Square (Downtown Austin Alliance) | <https://downtownaustin.com/republic-square-events/> | B | official | fetch |
| Waterloo Greenway Conservancy (Waterloo Park) | <https://waterloogreenway.org/events/> | B | official | fetch |
| Mueller Austin (Parks & Events) | <https://muelleraustin.com/events-at-mueller/> | B | official | fetch |
| Rodeo Austin (Star of Texas Fair & Rodeo) | <https://rodeoaustin.com/events/> | B | official | fetch |
| Maker Faire Austin | <https://austin.makerfaire.com/schedule/> | B | official | fetch |
| Texas Book Festival | <https://texasbookfestival.org/schedule/> | B | official | fetch |
| Austin Trail of Lights | <https://austintrailoflights.org/the-event> | B | official | fetch |
| Eeyore's Birthday Party | <https://eeyores.org/> | B | official | fetch |
| Austin Yoga Festival | <http://www.austinyogafestival.com/> | B | official | fetch |
| HAAM (Health Alliance for Austin Musicians) | <https://www.myhaam.org/calendar-of-events> | B | official | fetch |
| Austin Fashion Week | <https://austinfashionweek.sched.com/> | B | official | fetch |
| Meanwhile Brewing Co. | <https://www.meanwhilebeer.com/events> | B | official | fetch |
| Central Machine Works Brewery | <https://www.cmwbrewery.com/live-music> | B | official | fetch |
| Austin Beerworks | <https://austinbeerworks.com/calendar> | B | official | fetch |
| Jester King Brewery | <https://jesterkingbrewery.com/events-calendar> | B | official | fetch |
| Still Austin Whiskey Co. | <https://www.stillaustin.com/tasting-room-events> | B | official | fetch |
| Oasis Texas Brewing Company | <https://www.otxbc.com/events> | B | official | fetch |
| Whitestone Brewery | <https://whitestonebrewery.com/> | B | official | fetch |
| Rentsch Brewery | <https://rentschbrewery.com/> | B | official | fetch |
| Barking Armadillo Brewing | <https://barkingarmadillo.com/> | B | official | fetch |
| Vista Brewing | <https://www.vistabrewingtx.com/calendars> | B | official | fetch |
| Fitzhugh Brewing | <https://www.fitzhughbrewing.com/upcoming-events> | B | official | fetch |
| Treaty Oak Distilling | <https://www.treatyoakdistilling.com/events> | B | official | fetch |
| Dripping Springs Distilling | <https://drippingspringsdistilling.com/events/list/> | B | official | fetch |
| Bell Springs Winery | <https://www.bellsprings.co/events> | B | official | fetch |
| Yegua Creek Brewery & Restaurant | <https://www.yeguacreekbrewery.com/events> | B | official | fetch |
| Rising Sun Vineyard | <https://www.risingsunvineyard.com/> | B | official | fetch |
| Garrison Brothers Distillery | <https://www.garrisonbros.com/events> | B | official | fetch |
| Carter Creek Winery Resort & Spa | <https://www.cartercreek.com/calendar-of-events> | B | official | fetch |
| Iron Wolf Ranch & Distillery | <https://ironwolfranch.com/events/> | B | official | fetch |
| Fall Creek Vineyards (Tow) | <https://fcv.com/events/> | B | official | fetch |
| Wedding Oak Winery | <http://www.weddingoakwinery.com/events> | B | official | fetch |
| Round Top Brewing Co. | <http://www.roundtopbrewing.com/new-events-1> | B | official | fetch |
| Becker Vineyards | <https://beckervineyards.com/events> | B | official | fetch |
| Pedernales Cellars | <https://www.pedernalescellars.com/events-calendar/> | B | official | fetch |
| Signor Vineyards | <https://www.signorvineyards.com/events> | B | official | fetch |
| Augusta Vin Winery | <https://augustavin.com/events/> | B | official | fetch |
| Longhorn Cellars | <https://longhorncellars.com/calendar/> | B | official | fetch |
| Ab Astris Winery | <https://www.abastriswinery.com/events> | B | official | fetch |
| Meierstone Vineyards | <https://www.meierstonevineyards.com/events/> | B | official | fetch |
| Barons Creek Vineyards | <https://baronscreekvineyards.com/events/> | B | official | fetch |
| 4.0 Cellars | <https://www.fourpointwine.com> | B | official | fetch |
| Fiesta Winery | <https://www.fiestawinery.com> | B | official | fetch |
| Fredericksburg Winery | <https://fbgwinery.com> | B | official | fetch |
| Hilmy Cellars | <https://hilmywine.com> | B | official | fetch |
| Slate Theory Winery | <https://slatetheory.com> | B | official | fetch |
| Texas Wine Collective | <https://www.texaswinecollective.com> | B | official | fetch |
| Adega Vinho Winery | <https://adegavinho.com/events/> | B | official | fetch |
| K Estate Winery (Kuhlman Cellars) | <https://kuhlmancellars.com> | B | official | fetch |
| Messina Hof Hill Country Winery | <https://messinahof.com/fredericksburg/> | B | official | fetch |
| Grape Creek Vineyards | <https://grapecreek.com> | B | official | fetch |
| William Chris Vineyards | <https://williamchriswines.com/events/> | B | official | fetch |
| Wildseed Farms | <https://wildseedfarms.com/events/> | B | official | fetch |
| Salvation Spirits / The Speakeasy | <https://salvationspeakeasy.com> | B | official | fetch |
| Altstadt Brewery | <https://altstadtbeer.com/happenings/> | B | official | fetch |
| Altdorf Biergarten | <https://www.altdorfs.com/events/> | B | official | fetch |
| Silver Creek Beer Garden & Grille | <https://silvercreekfbg.com> | B | official | fetch |
| Lewis Wines | <https://www.lewiswines.com/events> | B | official | fetch |
| Texas Hills Vineyard | <https://texashillsvineyard.com/events/> | B | official | fetch |
| Siboney Cellars | <https://siboneycellars.com/events/> | B | official | fetch |
| Vinovium | <https://www.vinovium.wine/events> | B | official | fetch |
| Sandy Road Vineyards | <https://sandyroadvineyards.com/pages/events> | B | official | fetch |
| Westcave Cellars Winery & Brewery | <https://www.westcavecellars.com/events/category/westcave-cellars/list/> | B | official | fetch |
| 290 Wine Castle | <https://www.290winecastle.com/Events> | B | official | fetch |
| Esperanza Winery | <https://www.esperanzawinery.com/events-1> | B | official | fetch |
| Hye Meadow Winery | <https://www.hyemeadow.com/pages/events> | B | official | fetch |
| Ron Yates Wines | <https://www.ronyateswines.com/events> | B | official | fetch |
| Pebble Rock Cellars | <https://www.pebblerockcellars.wine/> | B | official | fetch |
| Real Ale Brewing Company | <https://realalebrewing.com/events/> | B | official | fetch |
| Pecan Street Brewing | <https://www.pecanstreetbrewing.com/events> | B | official | fetch |
| Texas Cannon Brewing Company | <https://www.texascannonbrewing.com/> | B | official | fetch |
| Andalusia Whiskey Co. | <https://www.andalusiawhiskey.com/event-calendar> | B | official | fetch |
| Milam & Greene Whiskey | <https://milamandgreenewhiskey.com/pages/events> | B | official | fetch |
| Redbud Cafe | <https://redbudcafetx.com/music/> | B | official | fetch |
| Uptown Blanco Arts & Entertainment | <https://www.uptownblanco.com/ballroom> | B | official | fetch |

## Trusted publishers (12)

Local journalism and broadcast — Austin Chronicle, the public-radio and commercial-radio event pages, the TV community calendars, CultureMap. First-class rows here, not a footnote: they cover events no single venue calendar does, and Coverage Law's "publishers trusted until wrong" applies to every one of them.

| name | official_url | bucket | grade | next_action |
| --- | --- | --- | --- | --- |
| Austin Chronicle Events | <https://www.austinchronicle.com/events/> | B | trusted_publisher | fetch |
| KUTX Presents (KUT/KUTX Public Radio Events) | <https://kutx.org/kutx-presents/> | A | trusted_publisher | fetch |
| KUT 90.5 Events (Austin's NPR Station) | <https://www.kut.org/tags/kut-events> | A | trusted_publisher | fetch |
| KOOP 91.7 FM (Austin Community Radio) Events | <https://koop.org/> | A | trusted_publisher | fetch |
| KLBJ 93.7 FM Concerts (The Rock of Austin) | <https://www.klbjfm.com/events/klbj-concerts> | B | trusted_publisher | fetch |
| 101X (KROX-FM) Events | <https://www.101x.com/events> | B | trusted_publisher | fetch |
| Austin City Limits Radio (ACL Radio, fmr KGSR) | <https://acl-radio.com/> | B | trusted_publisher | fetch |
| KVUE (ABC) Community Calendar | <https://events.kvue.com/> | A | trusted_publisher | fetch |
| KXAN (NBC) Community Calendar | <https://www.kxan.com/calendar/> | A | trusted_publisher | fetch |
| CBS Austin (KEYE) Community Calendar | <https://cbsaustin.com/features/community-calendar> | A | trusted_publisher | fetch |
| FOX 7 Austin (KTBC) Community Calendar | <https://www.fox7austin.com/community> | A | trusted_publisher | fetch |
| CultureMap Austin Events | <https://austin.culturemap.com/events/> | A | trusted_publisher | fetch |

## Aggregators & leads (21)

Ticketing platforms, listing aggregators, and identity/search spines that republish or point at other people's events rather than being the primary source themselves. Coverage Law rule: search/aggregator output may only ever propose an official URL, never stand in as the listing.

| name | official_url | bucket | grade | next_action |
| --- | --- | --- | --- | --- |
| Ticketmaster Discovery API | <https://developer.ticketmaster.com/> | D | aggregator_lead | blocked-D |
| Eventbrite API | <https://www.eventbrite.com/platform/api> | D | aggregator_lead | blocked-D |
| AXS | <https://www.axs.com/> | D | aggregator_lead | blocked-D |
| DICE | <https://dice.fm/> | D | aggregator_lead | blocked-D |
| See Tickets | <https://www.seetickets.us/> | D | aggregator_lead | blocked-D |
| Tixr | <https://www.tixr.com/> | D | aggregator_lead | blocked-D |
| TicketWeb | <https://www.ticketweb.com/> | D | aggregator_lead | blocked-D |
| Universe (Ticketmaster) | <https://www.universe.com/> | B | aggregator_lead | follow |
| SeatGeek | <https://seatgeek.com/> | B | aggregator_lead | follow |
| StubHub | <https://www.stubhub.com/> | D | aggregator_lead | blocked-D |
| Do512 | <https://do512.com/> | B | aggregator_lead | follow |
| Bandsintown | <https://artists.bandsintown.com/> | B | aggregator_lead | follow |
| Songkick | <https://www.songkick.com/> | A | aggregator_lead | follow |
| Spotify Web API | <https://developer.spotify.com/documentation/web-api> | D | aggregator_lead | blocked-D |
| SoundCloud | <https://soundcloud.com/> | B | aggregator_lead | follow |
| Linktree | <https://linktr.ee/> | B | aggregator_lead | follow |
| Resident Advisor | <https://ra.co/> | B | aggregator_lead | follow |
| Meetup | <https://www.meetup.com/> | B | aggregator_lead | follow |
| MusicBrainz (Artist/Event/Place Spine) | <https://musicbrainz.org/ws/2/> | A | aggregator_lead | follow |
| Bing Search (Benchmark Only) | <https://www.bing.com/> | D | aggregator_lead | blocked-D |
| DuckDuckGo Search (Benchmark Only) | <https://duckduckgo.com/> | D | aggregator_lead | blocked-D |

## Social (4)

Social-platform APIs (Instagram, Facebook, TikTok, YouTube). Any listing sourced through this path is path (b) social and carries the shown-on-card-and-detail verification warning per the ticket's Effectiveness rule — never presented as equivalent to a first-party or publisher row.

| name | official_url | bucket | grade | next_action |
| --- | --- | --- | --- | --- |
| Instagram Graph API | <https://developers.facebook.com/docs/instagram-api/> | E | social | claim |
| Facebook Graph API | <https://developers.facebook.com/docs/graph-api/> | E | social | claim |
| TikTok for Developers | <https://developers.tiktok.com/> | E | social | claim |
| YouTube Data API | <https://developers.google.com/youtube/v3> | D | social | blocked-D |

## Unknown / needs a human look (1)

Doesn't fit the other four honestly. One row: Google Places API is venue-identity/geocoding infrastructure, not an event source at all.

| name | official_url | bucket | grade | next_action |
| --- | --- | --- | --- | --- |
| Google Places API (Venue Identity) | <https://developers.google.com/maps/documentation/places> | D | unknown | blocked-D |

## Provenance

Every row traces to `sources/master_sources_catalog_120.json` (see that file's own `rank`/`id` for the join key back to it) and, for the historical why-this-source-was-added narrative, `sources/README.md`. `bucket` is recomputed from live code (`classify_entry()`), not hand-copied, so it cannot drift from `docs/CLASS_D_CLAIM_QUEUE.md`'s D/E rows — cross-check any bucket-D or bucket-E row against that document for the suggested claim path. This file is a snapshot, not a generated-and-regenerated artifact: unlike `CLASS_D_CLAIM_QUEUE.md` it carries no "do not hand-edit" notice, because no `tools/` generator for it was added in this session (Must-not: no new importer/taxonomy/service). Re-running the same method against a later catalog would need a fresh pass.

`docs/CENSUS_CAPCOG.csv` quotes every field that contains a comma per RFC 4180 (e.g. the row for "George Washington Carver Museum, Cultural & Genealogy Center") — confirmed by parsing the committed file with Python's `csv` module: all 180 data rows read back as exactly 5 fields, no exceptions.
