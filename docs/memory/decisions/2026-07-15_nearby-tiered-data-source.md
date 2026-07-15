# Nearby (restaurants/bars/venues around an event) ships as maps deep links first; richer data climbs a logged escalation ladder.

**Directed:** 2026-07-15, founder: "Make this happen: '5. Nearby'".

## The decision (least-costly-method-first, charter Cost discipline #1)

- **Tier 1 — NOW (chosen, built):** the Nearby chips on the event-detail
  screen are real deep links into a maps search anchored to the venue's
  street address ("restaurants near 1502 E 6th St Austin TX"). Zero API,
  zero key, zero spend, zero new service — works on every phone today,
  computed per venue at Step 9. "More venues" links to OUR OWN Tonight
  feed — OneLive's inventory is the more-venues answer, no third party
  needed.
- **Tier 2 — objective trigger:** in-app nearby places from OpenStreetMap
  data (ODbL attribution required; real build: fetch + cache + POI
  schema). NOTE: the public Overpass API is a shared courtesy service,
  not a production backend — Tier 2 means aggressive caching plus either
  self-hosted extracts or a managed OSM provider, costed at design time. Trigger: Step 9 is live AND usage evidence
  that fans want nearby without leaving the app (e.g. Nearby tap-through
  becomes a top-5 detail-screen action). Not before — building POI
  infrastructure for a stealth-gated site is spend without signal.
- **Tier 3 — FOUNDER-CRUCIAL:** commercial Places API (Google/Foursquare)
  only if Tier 2's measured coverage/quality falls short in real use.
  Money + credential minting = founder interrupt by charter.

## Why this and not alternatives

Jumping straight to a Places API (the "obvious" choice) fails cost
discipline twice: recurring per-call spend and a founder credential for a
feature with zero usage data. OSM-first-now fails it once: real build
effort ahead of any signal. The deep link delivers the founder's intent —
"an easy way to see nearby restaurants, other venues, bars" — at literally
zero marginal cost, and the maps app's results are BETTER than a v1
in-app list (reviews, hours, photos).

## Trust screen

Stated at its true width (corrected per evaluator, PR #20): OneLive does
not rank, filter, or sell placement in Tier 1 results — but the external
maps provider controls its own ranking and may include ITS OWN sponsored
placements. OneLive's guarantee covers OneLive's surfaces; the link-out
destination is disclosed as the provider's, not ours. If Tier 2+ ever
renders nearby lists in-app, the full guarantee applies to that surface:
distance sort only, no sponsorship, disputed-venue rules unchanged.
