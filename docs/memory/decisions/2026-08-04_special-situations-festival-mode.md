# Decision: 'Special Situations' festival mode — founder-directed (2026-08-04)

**Founder, verbatim:**
> "We need a 'special situations' mode for festivals, pop up events, etc where
> new activities may be noted in a website or somewhere. Think South By
> Southwest. That will be great proving ground for us. Festivals may require
> their own model to ensure we're capturing all of the adjacent events and
> activities that accompany a festival. So these are things that may not be a
> formal part of the festival, but a Venue or an organization or a group or an
> individual may choose to set something up and invite people to attend or a
> Venue may be booking artists that otherwise can't or aren't part of the
> large event, etc.."

Same message ratified: the cap-30 freshness posture and "let the queued
adaptive cadence build make the whole question obsolete" (adaptive cadence
build approved).

**What already exists (the trust half).** `sxsw_mode` is live through the
whole pipeline (event_candidate column → multi_confirm_gate → derive_confidence
→ publish_policy): during festival windows, non-first-party corroboration
requires 3 independent sources instead of 2, because copy-paste noise is
cheaper that week. First-party voices still publish alone. The trust model is
festival-ready; what's missing is the SOURCING surge.

**The build (queued, design-first):** a festival window is DATA (name,
date-range, geography, keyword pack), and while one is active:
1. **Cadence surge** — sources inside the window's geography get checked at
   festival tempo (hooks into the approved adaptive-cadence build).
2. **Adjacent-event discovery sweep** — scheduled scanner queries for the
   festival's keyword pack (unofficial/day-party/pop-up/anti-showcase terms +
   venue names) via the licensed search-API lane; found pages become source
   CANDIDATES for human curation, exactly like the Eventbrite lanes.
3. **Pop-up source class** — short-lived sources (a pop-up's Instagram page,
   a one-off RSVP page) enter the catalog with an expiry, so festival-week
   noise doesn't permanently bloat the catalog.
4. **Unofficial-vs-official honesty** — adjacent events are never labeled as
   part of the festival; they carry their own provenance (the venue/organizer
   that actually announced them). No gate, threshold, or custody changes —
   the mode is sourcing breadth + cadence, judged by the same physics.

SXSW (March) is the proving ground; Austin's fall season (ACL, F1 weekend)
arrives first and exercises the same machinery.
