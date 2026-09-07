# One Live — Locale Launch Law
## A locale is a query. The catalog is the world. Demand starts gather. A pack is cache.

Ratified: 2026-09-06. Status: in force.
If CLAUDE.md, STATE.md, or a session contract disagrees with this file on locale, go-live, gather-on-demand, place search, location privacy, or anti-attention, this file wins.
Coverage Law still wins on catalog vs view, source classes, and "do not invent."
Operating Law still wins on speed, effectiveness, and "a search snippet is never a listing."
Entity Split Law still wins on identity.

## Outcome
Anyone, anywhere, can type a place — or opt in to "here" — and 1Live shows what is on, or honestly gathers it.
We do not pre-launch cities as products. We do not wait for a founder pack before a person may ask.
CAPCOG is locale 1: the first rehearsal of this process, a default VIEW, never a catalog border.

## Repealed as product or ingest law
- Founder must "launch" each city before it may appear
- Locale = a market we sell, a code fork, or an `if austin`
- IP address as consent to locate a person
- Search-engine snippet, SERP, or "AI overview" as a listing
- Programmatic empty city pages / SEO location spam
- Infinite feed, streak, unread badge, or notification-by-default as growth
- Pay-to-rank, pay-to-place, or "boosted" in any locale
- Treating "Austin looks full" as done

Still in force: no login/paywall/bot bypass; disputed shown-never-hidden; holes stay holes; no invented dates, places, or events.

## 1. Locale is a query
A locale is how a person says *where*: a typed place, an opted-in "here", a URL `?place=`, a last-used place.
It is not a tenant, not a database, not a reason to drop a row.
The catalog is global. Views may default to a place. Views must not delete.

## 2. Two paths — Show and Gather
Show (instant): rows we already have for that place. If none, the surface says we are gathering — never "0 events in this city" as if we finished reading it. Same law as an unread desk: 403 is unknown, not empty.

Gather (a job, not a page view): a typed place or an opted-in here is a trigger to run the pipe.
1. Resolve the place to a timezone + a bounded query grammar (city / region / "near {place}").
2. Propose official doors (civic calendar, local desk, venue ICS, library, campus). A search hit is a LEAD. It is not a listing.
3. Classify A–F. Fetch only what Coverage Law allows.
4. Split identities (Entity Split Law). Fill when+place from the event's own page when the list did not state them.
5. Write only rows with title + when + place. Label `via`. Holes stay off the default view.
6. Persist the doors and identity patterns as a pack cache so the next person in that place is instant.

First visitor may wait on gather. Second visitor must not start from zero.

## 3. Pack is cache, not permission
`sources/locale_packs/<id>.json` is compiled coverage: timezone, places, kinds, doors, selectors.
- No pack yet: thin gather is still allowed (class A + known desk patterns + query grammar).
- Pack exists: skip rediscovery; refresh on due_at / skip-unchanged.
- A second locale is a second file. Python that names a locale id in an `if` is a defect.

## 4. Go-live process (every place, including locale 1)
Mechanical. Skip nothing; do not add ceremony.

1. Name the place (pack file if we are keeping doors; otherwise a gather job id).
2. Universe / TAM: licenses, civic bodies, campuses, aggregators — existence, not listings.
3. Classify every door A–F.
4. Class A sweep (ICS / JSON-LD / RSS / public API).
5. Desk walk, dry-run table: rows_n, dated_n, placed_n, mash_n, 403_n. Mash must be 0 before write.
6. Event-page fill under a tick cap (budget is a tick, not a universe).
7. First write: dated + placed only, on current master, founder-authorized.
8. View default may point at this place; `region=all` / a typed other place still works.
9. Go-live checklist (all true, or it is not live):
   - mash_n = 0 on walked desks
   - default view shows real dated rows or an honest gathering state
   - N of M is true
   - walls queued, not empty lists
   - `via` on the card
   - no TBA dump
   - dry-run plan and write plan agree on that head
10. Keep it true: schedule after a clean write; listing-update fail-closed; claim path for D; class B venue-direct as the majority over time.

Demand can start this process. A founder session can too. The steps do not change.

## 5. Peculiarities — data first, then a generic ladder step
If Austin (or any place) is named in code, the ticket failed.

| Peculiarity | Lives in | Never in |
|---|---|---|
| Places, kinds, timezone | pack JSON | Python |
| Door URL, intake, wall | pack `doors[]` | a bypass |
| Permalink shape `/event/{id}` | identity_patterns.json + pack | CSS "event card" heuristic |
| Card CSS fallback | pack `listing_selectors`, last resort | global substring `event` |
| Clock + "Sat Sep 6" | shared parsers + pack timezone | "assume tonight" |
| Late-night rollover | one pack flag, one shared rule | hardcoded Austin |
| Robots / crawl-delay | fetcher per host | ignoring robots |
| New HTML *shape* | one new ladder *tier* + fixtures, used by any locale | `if locale ==` |
| Credential / partner | class D + claim, or a named secret | scraping a wall |

Expected code for a new place: none.
Expected code for a new shape: a generic tier.

## 6. Gather job — world-class ops, not a scrape
- Focused: only geospatially relevant doors. Not the whole web.
- Finite tick: pages, wall-clock, dollars. Stop on first bound. Skip unchanged.
- Resume: a killed job continues; it does not republish.
- Retrieval of EVENTS may use a hierarchical cell index (H3 or equal) so "what's on in this place" is a cell read, not a fan-out of every venue. That index is about public happenings, never about a person.
- No thin generated city page with no listings. Gathering UI is a state of Tonight, not a fake calendar.

## 6a. Shared live data — one gather, many readers
A validated, pushed-to-live place (Miami FL, Lexington KY, DFW, …) is one dataset. Readers share it.

- Page load MUST NOT start a crawl, extract, or gather. Page load is Show: catalog + cache.
- Gather is a single-flight job keyed by canonical place_id. Concurrent visitors attach to the job that is already running. They do not spawn another.
- After go-live, refresh is the scheduler (due_at, skip-unchanged, event-proximity). One tick per door bound, not one tick per user.
- Cache Tonight/list JSON by place_id + time window. Short TTL. Public listings only. A person's coordinates MUST NOT be part of the cache key.
- Ambiguous names are different places until a pack or geocode says otherwise: Miami FL ≠ Miami OH; Dallas ≠ Fort Worth unless a metro pack unifies them.
- Cost and latency come from cache hits and indexed reads. A zillion calls for the same locale is a defect.

## 7. Privacy — Apple-level in force; stricter is a later switch

Location of a PERSON is not location of an EVENT. Event coordinates are public facts. Person coordinates are not.

We ship Apple's four pillars: data minimisation, on-device processing, transparency and control, security.
Legal floor: precise geolocation is sensitive under US state privacy laws; location data is personal data under GDPR. IP is not consent.

### In force (Apple-level)

| User choice | What we do |
|---|---|
| Nothing tapped | Type a place. No GPS. No IP-as-location. |
| Use my location | Native OS prompt. Approximate vs Precise is the OS control. While Using, not Always, unless they later opt into a reminder. |
| Approximate | Send city / metro (coarse). Enough to Show / Gather. Disclose Coarse Location. |
| Precise | Use on-device to sort "near me." What we send is still the city. We do not implement precise-on-the-wire. |
| Night-out / day-out / messaging | On-device. Not on our servers. |
| Heartbeat | Schema may exist. No person-level rows. Product later. |
| Last place | On-device. Account-sync of last place is a separate explicit opt-in. |

Forbidden now:
- Sale or share of location to brokers, ads, or social SDKs
- Ad pixels or analytics SDKs receiving location
- Silent Always-on tracking
- Precise lat/lng in our DB, logs, Sentry, or model prompts
- Using a person's location to rank or boost a listing they did not ask to boost
- Mixing person-location columns into event tables

App Store / privacy label: on-device precise is not "collected." Sending a city is Coarse Location — disclose that, and nothing finer.

### One module, so we can tighten later without a rewrite

Precision enum, one client, never bypassed:

`none → coarse → precise_on_device → precise_egress`

Today we implement `none`, `coarse`, and `precise_on_device`.
`precise_egress` does not exist. Do not add it "for later" as a hidden path.

Hard rules that make the next level a policy flip:
1. Person location and event location never share a column.
2. No user GPS in logs, Sentry, or prompts.
3. Server Show / Gather / rank must work on a city (or a typed place). A pin must not be required.
4. On-device first for last-place, calm-mode, night-out; sync is opt-in.

### Later (not in force — do not build in this law's implementing tickets)
- Refuse even a city-cell if they only granted Precise-for-device (access is not egress)
- Heartbeat k-anonymous counts that fail closed on small buckets (EDPB: no isolation, no linkage, no inference)
- Differential privacy noise
- An API that physically rejects lat/lng of a person

When the founder wants that: turn a policy, do not migrate tables.

## 8. Anti-attention (mechanical, not a vibe)
1Live is the fastest way to decide and leave. Time on site is not a KPI.

Must:
- One primary question: what's on, here, when. Answer on the first screen.
- Card: title, when, place, who (act + venue one-liners), `via`, one next step out (tickets / info / map). Every other element must pay rent or it is cut.
- N of M. Held-back named. Disputed shown. Path-(b) unverified note on card AND detail; everyone else presumed verified — no trust-prose wallpaper.
- Beautiful, not dense. One visual system. Motion only for a change that matters. Persist a calm mode on-device (no motion, no autoplay) without an account.
- Default: no push, no email, no badge. Reminders are opt-in per listing, on-device.

Must not:
- Infinite scroll as the product
- For-you feed that hides the rest of the catalog
- Streaks, recap-you-missed-it, dark patterns to re-open
- Interstitial signup before the river
- Design that spends the user's mind on the chrome

Traffic to Chronicle / venue / ticketor is a feature. We are not their garden.

## 9. Heartbeat (structure now)
Heartbeat is de-identified demand: which cells, kinds, and hours are hot — not who went.
Schema may exist before the product. It may not ingest person-level rows "for later."
k-anonymous fail-closed is Later (§7), not this ship.

## 10. Agent rules
Must run Show for any typed place without asking permission for the locale.
Must start Gather as a bounded job, not as an unbounded crawl, when Show is thin.
Must not refuse a city because the design is unfinished or CAPCOG is the test locale.
Must put peculiarities in pack / identity JSON first.
Must not send precise person-location off device.
Must not merge gather writes that lack title+when+place.
Must not implement `precise_egress`.
Stop and ask founder only for: money/new vendor, legal, credentials, trust-invariant change, or "raise this gather's budget."
