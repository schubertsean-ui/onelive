# Night Out v1 — "make a night of it" around any anchor (PROPOSAL, founder-directed 2026-07-29)

Greppable summary: founder-directed — Night Out is a universal, tasteful add-on
to ANY anchor event (a lecture, a tasting, a show, an exhibition, a run club):
"what else is nearby, before or after — more events, a bite, a drink?" The whole
design problem is RESTRAINT: the reason people loathe the existing versions
(Yelp/Google/social "things nearby") is that they are pushed, ranked/pay-to-play,
FOMO-driven, cluttered, and presumptuous. OneLive's Night Out is the deliberate
opposite: opt-in, sparse, un-ranked, ephemeral, honest. STATUS: PROPOSAL —
founder-gated (opening new data domains and any new surface is a founder
decision); this doc is the standing playbook for WHEN it is greenlit. It unifies
three already-ratified threads: the voice-personas Evening Planner class
(ONE_LIVE_VOICE_SEARCH_PERSONAS_v1 §21–23), Group Plans (ONE_LIVE_GROUP_PLANS_v1),
and dining-density (voice persona #21). No invariant is relaxed; Night Out is a
LENS around tonight's real events, never a feed, never engagement mechanics.

## The anti-loathing table (why theirs is hated → what ours does instead)

This is the spec, stated in the negative — each row is a hard rule.

| Why the incumbents are loathed | OneLive's rule |
|---|---|
| Pushed at you (notifications, auto-injected lists) | **Pull, never push** — a quiet, optional "Make a night of it?" affordance ON the event page; never a notification, never auto-expanded. |
| A firehose of options | **Sparse** — 2–4 nearby things, curated by proximity + timing, never an endless list. |
| Ranked / pay-to-play / "sponsored" | **Un-ranked and un-buyable** — nearest and time-compatible, stated plainly ("within a few blocks, opens after your show"); never "recommended," never sold. Pay-for-placement here is pay-to-rank — a Red Line. |
| FOMO / engagement manipulation | **No FOMO mechanics** — no "don't miss," no streaks, no counts ticking to pressure. |
| Clutter competing with the thing you came for | **The anchor stays the star** — Night Out is a secondary lens BELOW the decision, never above it. |
| Assumes what you want | **You pick the intent** — "a bite before," "a drink after," "more like this," "make a night of it." We never guess. |
| Pads with weak matches | **Honest gaps** — if we lack good nearby data, we say so or show nothing. Never filler. |
| Lives forever, accretes a profile | **Ephemeral** — like the group-plan card, it helps you plan then gets out of the way. No history feed, no profile accretion. |

## Deployment, in order of what we can HONESTLY do

1. **Start with what we OWN — "nearby & after this."** From our own event data:
   proximity + time. Zero new data, zero nuisance — one quiet expander on the
   detail page. A lecture at 6 → "two things nearby after 8." This is buildable
   the moment it's greenlit; it needs no new source.
2. **Add venue types — a bite, a drink.** Bars/restaurants via factual map data
   (OSM Tier-2 counts / Google Places), as COUNTS and DISTANCE, never ratings —
   the same "we count and locate, we never rate" rule the voice personas set for
   dining-density (#21). Meetup (clubs/hobby/social) is a candidate source here,
   founder-gated on its Pro-tier cost (ONE_LIVE_PLATFORM_API_INVENTORY_2026-07).
3. **The shareable "night plan" card.** Chain by time + walking distance into one
   forwardable plan (lesson → show → food, per voice personas v1.1). This is where
   Night Out meets Group Plans — the share card already shipped is step one; the
   plan object + itinerary chainer is Group Plans P2.

## Venue identity resolution (founder note, 2026-07-29: "use the venue's actual info, cross-reference via Ticketmaster")

Night Out is only as good as the venue facts under it, so a venue's IDENTITY is
resolved by CROSS-REFERENCING sources, never trusting one blindly:
- **Ticketmaster venue records** give a venue's name/address/geo (and a venue
  page) — a cross-reference anchor, but its `url` is a ticketing-provider page,
  NOT the venue's own site, so it is never presented as "the venue's website"
  (adversarial-review #101; the box-office PHONE is the real confirm channel).
- **Google Places** resolves the venue's OWN website, phone, and hours by
  matching name + geo — the authoritative venue-identity source.
- **TABC** authoritatively types alcohol producers (brewery/winery/distillery)
  by permit, independent of name (PR #104).
Cross-referencing these (same venue across TM + Places + TABC by name/geo) yields
the venue's ACTUAL info — real website, phone, hours, type — which is what a
Night Out "grab a drink nearby" or "confirm with the venue" needs. Nothing is
fabricated: a field we can't resolve from a real source stays blank, with the
phone as the always-available confirm path.

## The hard boundary (what keeps this OneLive)

- **Utility, not a network.** No profiles, no followers, no public feed of plans,
  no engagement mechanics. A Night Out plan is a tool that dies at sunrise.
- **Nearby signals never rank the public feed.** How many people build a Night
  Out around a show must NOT reorder discovery — herd-ranking is pay-to-rank's
  free cousin (Group Plans trust screen #3).
- **Cross-domain honesty.** Restaurant hours, drink specials, menus = not our
  verified data. The honest handoff (a link, a factual count) + demand logging
  (H5) is v1; the venue-self-reported channel is a separate founder decision.
- **Opening any new data domain (Meetup, deals, presence) is founder-crucial.**

## Disposition

PROPOSAL — greenlight is a founder decision. When greenlit, build order is the
three deployment steps above, each gated on the prior step's real usage (the same
evidence discipline as Nearby's tiers and Group Plans' phases). Step 1 ("nearby &
after" from our own events) is the smallest and needs no new source; steps 2–3
open the venue-type and plan-chaining surfaces already seeded in Group Plans and
the dining-density note.
