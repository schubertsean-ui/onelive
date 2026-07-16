# Group plans v1 — from "what should I do?" to "what should WE do?" (PROPOSAL)

Greppable summary: founder-directed (2026-07-15: single person, couple,
small group, large group, huge group, and mixed collections who want to
connect or have someone open with "hey what if we do this?" / "here are a
few options…" — they come to OneLive for the answer). Architecture: the
SHORTLIST → VOTE → PLAN object — ephemeral, link-shared, no accounts
needed to respond, dead after the night — phased P0–P3, with fan-to-fan
CONNECT (strangers meeting strangers) explicitly split out as its own
founder-gated future decision (safety/legal weight of its own). The
charter line this must never cross: OneLive is NOT a social network — group
planning is a UTILITY around tonight's real shows, never a feed, never
profiles, never engagement mechanics. STATUS: PROPOSAL for ratification;
P0 is already implied by the ratified design brief (§6.D5 share card).

## The party-size ladder (who is asking, and what "the answer" means)

| Size | The moment | What OneLive must hand them |
|---|---|---|
| **1 — Solo** | "What should I do tonight?" | The current product, whole. (Solo is already served; everything below builds ON this, never replaces it.) |
| **2 — Couple** | "What are we doing?" — two phones, one decision | A 2–3 show SHORTLIST sent as one link; the other person taps what they prefer; done in under a minute. |
| **3–8 — Small group** | The group-chat spiral ("idk, what do you want to do?") | Same shortlist link dropped into the existing group chat; everyone taps a preference (no app, no account); the proposer sees the tally; the winner becomes the PLAN with time/venue/map/calendar for all. |
| **9–30 — Large group** | Birthday, team night, visiting friends | Shortlist + headcount: "will you be there" counts, and shows carry GROUP-FIT facts (room size class, standing vs tables, reservable?) so a 20-person pick is realistic, not hopeful. |
| **30+ — Huge group** | Organizer territory | Venue DISCOVERY by capacity + direct venue contact handoff. OneLive finds the room and makes the introduction; running a 200-person event is the venue's business, not ours. |
| **Mixed — several singles/couples/small groups** | "Who's in?" across circles | One plan, multiple sub-parties: forwardable link, each circle responds; the plan shows combined headcount. CONNECTING STRANGERS is deliberately NOT this row — see the boundary below. |

## The object: SHORTLIST → VOTE → PLAN

One data object carries every row of the ladder:

- **Shortlist** ("here are a few options…"): 2–5 real shows picked from the
  feed into a single share link. Creating one requires nothing beyond the
  session; it is the brief's share card, pluralized.
- **Vote**: recipients open the link (no account, no install) and tap a
  preference. Votes are visible to the invitees only.
- **Plan** ("hey what if we do this?" → "we're doing this"): the pick
  becomes a single card — artist, time, venue, map, add-to-calendar for
  everyone, itinerary chaining when the evening has stages (lesson →
  show → food, per voice personas v1.1).
- **Ephemeral by design**: plans expire after the night. No archive
  surface, no history feed, no profile accretion. The city resets daily;
  so do plans.

## Phases (cost/consent-ordered, same discipline as the member layer)

- **P0 — Share card (Step 9 scope, already ratified via brief §6.D5):**
  one show or one night-plan as a beautiful, compact, forwardable card.
  This alone answers the couple case.
- **P1 — Shortlist + vote:** the plan object, share tokens, tap-to-vote
  with zero voter accounts. Server-side state is minimal and anonymous
  (a token, picks, an expiry). The single highest-leverage group feature.
- **P2 — Plan + headcount + chaining:** winner card, "I'll be there"
  counts, multi-stop evenings.
- **P3 — Group-fit facts:** venue capacity class / seating style /
  reservable as EXTRACTED or venue-asserted fields (Step 6/7 schema +
  sensor architecture first-party channel) powering "works for 12 of us"
  filtering — and the voice grammar gains PARTY SIZE ("options for six of
  us near downtown" → persona #24, added to the golden set at build).

## The hard boundary: CONNECT is its own future decision

"Multiple singles and couples who want to connect" — when that means
people who ALREADY know each other coordinating across circles, the plan
object above serves it fully. When it means STRANGERS meeting strangers
around shows, that is a different product with a different risk class:
real-world safety, harassment and moderation duty, minors, privacy of
presence data ("who else is going" reveals where a person will physically
be), and §10 legal posture. Decision recorded here: fan-to-fan discovery
of other attendees is OUT of this proposal; if the founder wants it, it
gets its own ratification with a safety design at its center (opt-in
everything, no presence visibility by default, venue-level aggregates
only, abuse reporting before launch — the floor, not the spec).

## Trust screens (what keeps this OneLive)

1. **Utility, not network:** no profiles, no followers, no public feed of
   plans, no engagement mechanics (streaks/likes/leaderboards). A plan is
   a tool that dies at sunrise. ("Not a social feed" is charter text.)
2. **Private by link:** a plan is visible to holders of its link, full
   stop. Nothing a group does is ever public inventory.
3. **Group signals never rank the public feed:** how many people
   shortlist a show must NOT reorder discovery — herd-ranking is
   pay-to-rank's free cousin. Aggregate plan data may inform COVERAGE
   (which neighborhoods/sizes we underserve, H5-style), never ranking.
4. **Presence privacy:** headcounts live inside the plan's link audience;
   OneLive never shows anyone "who is going" beyond what a plan's own
   invitees shared with each other.
5. **The invariants ride along unchanged:** disputed-shown-never-hidden
   inside shortlists too; uncertainty sheets travel with the card; no
   badges anywhere; tastemaker separation untouched.

## Disposition

P0 folds into Step 9 (small). P1–P3 are post-launch build order, each
gated on the prior phase's real usage (same evidence discipline as
Nearby's tiers). CONNECT waits for its own founder-initiated ratification.
Schema seeds (plan object, share token, capacity-class field) join the
Step 7 design round so nothing here requires rework later.
