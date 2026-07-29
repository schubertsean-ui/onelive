# Founder directive — communities (Meetup/clubs/groups) as a source (2026-07-29)

## Retrieval token
**"Communities are a third trust category — discovery that points OUTWARD, never a verified event."** Before touching this, recall: a group is not an `event_candidate`, we link to the group's real home (Meetup/library) instead of intercepting sign-up, Meetup is the licensed beachhead, and Facebook/Nextdoor are a legal decision (submitted/claimed links only, never scrape).

## Verbatim directive
"How can we include meetup data? We'd need to think through a number of things like 'card' design, placement, etc but it does capture some important elements of local culture, just as there may be book clubs, other 'clubs' or 'groups' or such on Facebook or Next Door, etc. we would still point people to those sites to sign up but they would be able to find it on ours. Design and honoring our foundational operating beliefs and principles become crucial when considering things like this."

## What was produced
A PROPOSAL (not a build): `docs/strategy/ONE_LIVE_COMMUNITIES_SOURCE_v1.md` — the
third trust category (communities), the group-vs-dated-instance split, card
anatomy under the trust-display rules, the "Find your people" lens + labeled
feed band placement, source tiers (Meetup licensed → public civic feeds →
submitted/claimed → NO scraping of FB/Nextdoor), a trust-&-safety/values-
exclusion line, a separate data model with the same no-pipeline-bleed guard,
and a consolidated founder-decision list (§9). Status: PROPOSAL — nothing builds
until the founder ratifies §9. First increment if ratified is a read-only,
licensed, lens-only Meetup beachhead for Austin.

## Founder ratification (2026-07-29, follow-up)
"Good with Communities as the category. I like find my people — it's a nice play
in the Find My in an iphone. New trust category — bless communities."
→ RATIFIED: **"communities"** is a new first-class trust category, and the lens
is named **"Find your people"** (echoing iPhone "Find My"). STILL PENDING (do
NOT build the ingestion path until ratified): scope/timing, Meetup licensing,
FB/Nextdoor posture, feed integration, the values-exclusion safety line (§9 of
the proposal).

## Foundational principles this must never violate
AI never publishes · categories don't bleed (no `event` pipeline contact) ·
no pay-to-rank (claim ≠ boost) · trust display (no badges, quiet provenance) ·
point out don't wall in · GEO/attribution moat · cost + legal discipline.
