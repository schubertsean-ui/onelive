# Tasting Trail — breweries, wineries & distilleries as an always-on section (v1 spec)

Founder-directed 2026-07-29. Verbatim intent: "I want all the breweries,
wineries and distilleries to be a kind of section that is always accessible
showing venue info even if we don't show the venue has anything special going
on … a 'section' or grouping that is an available search option. And ideally
either in pre-packaged or based on user selection or interest we could surface
2-4 nearby so a person or couple or group could make a fun time out of it. That
gives an opportunity to tie in later on with the tour companies. They may not
always have activities per se but they are a big part of our tourism and live
activities and culture."

## The shift this introduces

OneLive today is **event-first**: the surface shows events; venues are a field
on an event. This feature adds a **venue-first** surface for a specific,
tourism-heavy category — tasting rooms — that is worth browsing *even when no
event is scheduled*. It does NOT change the event trust pipeline; it adds a
directory view alongside it.

## What it is

1. **An always-accessible section** — "Tasting Trail" (working name; options:
   "Sip & Savor", "Tasting Rooms"). A browsable directory of breweries,
   wineries, and distilleries, reachable as its own section and as a **search /
   filter option** from the main feed.
2. **Venue-info-even-without-events** — each venue shows its name, kind
   (brewery/winery/distillery), area/county, and a first-party link, whether or
   not it currently has a listed event. When the pipeline HAS upcoming events
   for that venue, they surface on the card; when not, the card shows the venue
   and an honest "check their calendar" link — never a fabricated event.
3. **Nearby clusters for an outing** — surface **2–4 nearby** venues as a
   "trail" a person/couple/group can do in an afternoon. Pre-packaged trails
   (e.g. "Dripping Springs distilleries", "Hill Country wineries", "East Austin
   breweries") AND/OR user-interest/location-driven selection.
4. **Future: tour-company tie-in** — a trail is a natural partnership surface
   for tour operators (booking, transport). This is a LATER commerce hook.

## Trust invariants binding this feature (non-negotiable)

- **No fabricated activity.** A venue with no sourced event shows venue info +
  a first-party calendar link, never an invented "event tonight". Same
  truth-first rule as everywhere else.
- **No pay-to-rank — ever.** The "2–4 nearby" selection is by **geography and
  user interest ONLY**, never paid placement. The future tour-company tie-in is
  a SEPARATE commerce surface and must never influence which venues or events
  rank or surface on the trust feed. (This is the hardest line to hold as
  partnerships arrive — it is a trust invariant, founder-crucial to change.)
- **First-party only.** Venue records come from the curated source catalog
  (ranks 121–142, the 22 tasting rooms already added), all first-party and
  policy-railed. New venues follow the same catalog rails.
- Events shown on a venue card use the SAME `trustDisplay` as the main feed —
  a venue view never claims more certainty than the event pipeline asserts.

## Data

- **Source of venue records:** the source catalog's tasting-room entries
  (`sources/master_sources_catalog_120.json`, `cultural_domain: food-drink`,
  `entity_type: venue`, ranks 121–142). These carry name, base_url, county,
  kind (in notes), and are the honest first-party venue directory.
- **Events for a venue:** joined from the normal pipeline (`licensed_event` /
  promoted events) by venue name/host when present — display-only, gated as
  usual.
- **Geo for clustering:** county today (coarse but real); precise lat/lng is a
  later enrichment (many catalog entries carry county, not coordinates).

## Build increments (each shippable, trust-railed, testable)

1. **Venue directory read path** — a typed reader that returns the tasting-room
   venues from the catalog (name, kind, county, url, notes). No fabrication.
2. **The section UI** — a browsable "Tasting Trail" route/section on the web
   app: list of venues, filterable by kind (brewery/winery/distillery) and
   area/county; always visible; each card shows venue info + first-party link.
3. **Event integration** — when a venue has upcoming pipeline events, show them
   on its card via `trustDisplay`; otherwise the honest "see their calendar".
4. **Filter/search entry** — expose "Breweries, Wineries & Distilleries" as a
   category/filter from the main feed.
5. **Nearby clusters** — group 2–4 venues by area into "trail" suggestions
   (pre-packaged by county + interest-driven); geography-only ordering.
6. **(Later) tour-company hooks** — a partnership/booking surface, walled off
   from event ranking per the no-pay-to-rank invariant.

## Status

Spec captured. Increment 1 (venue directory read path) is the next build.
Design-brief alignment (card anatomy, trust display, WCAG/CWV) applies as to
any web surface; a designer pass on the section layout is worthwhile before the
UI increment lands.
