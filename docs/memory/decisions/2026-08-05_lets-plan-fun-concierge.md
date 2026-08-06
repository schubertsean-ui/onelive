# 2026-08-05 — "Let's Plan Fun": the concierge packages feature

## Founder directive (verbatim, 2026-08-05)

> ONe UI feature related to the Date Night or what have you is 'Let's Plan
> Fun' and then offer several items for user to select/check and then the
> site finds criteria that matches and provides them with 'packages' that
> are sequenced based on timing distances, etc. so a full on conceirge
> service - we even get them to external ticketing sources if needed for
> reservations, etc..

## What already exists (this is composition, not invention)

- `web/lib/feed.ts` `buildPlan(events, scope, nowMs)` — sequences one pick
  per time block with same-neighborhood / different-domain bias. Produces a
  single plan.
- `DESIRES` — multi-select-ready criteria chips (free, easy on the wallet,
  starting late, somewhere to dance, quiet & intimate, …) with per-event
  `match()` and an honest `why()` line each.
- `LicensedEvent` carries `venue_lat` / `venue_lng` (real distance is
  computable, not guessed), `venue_address`, `venue_phone`, `venue_url`,
  `ticket_url`.
- The existing surface already offers "Plan a day / night / weekend".

## What the directive adds

1. MULTI-SELECT criteria (today a desire is a single lens).
2. PACKAGES — several alternative sequenced plans to choose between, not
   one plan.
3. Sequencing by REAL timing + distance (haversine on stored lat/lng,
   travel-time feasibility between consecutive stops), not just time blocks.
4. Explicit handoffs at each stop: tickets where a ticket link exists,
   phone/website for reservations where it does not — per the 2026-08-05
   handoff ruling, opening in a new tab so 1live keeps its place.

## Trust rules that bind this feature

- A package is a SUGGESTION assembled from real listings; every stop states
  why it was picked, and the full night stays one tap away (existing "lens,
  never a gate" rule).
- No pay-to-rank, ever: package ordering may never be sold or influenced by
  a venue's commercial relationship.
- Travel feasibility is computed from stored coordinates; when coordinates
  are missing the stop is still offered but the leg is stated as unknown —
  never a fabricated travel time.

## Status

Design panel run 2026-08-05; scoped for build as its own PR after the
in-flight date-recovery / display / gate work lands.
