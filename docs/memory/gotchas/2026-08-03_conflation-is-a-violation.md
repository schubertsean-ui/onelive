# Gotcha — conflation is a violation: keep distinct concepts distinct, and cite each

One-line: collapsing two different things into one loses the constraint that lived in the distinction — keep these pairs apart and reason about each on its own terms.

Retrieve this before reasoning about trust, media/rights, identity, or authority —
any place two nearby ideas are easy to merge.

## The distinctions that must not be merged

1. **Trust-in-a-fact ≠ right-to-reproduce-an-image.** Believing an event's
   date/venue is true (a corroboration question) says nothing about whether we may
   display someone's photo (a rights/licensing question). Verifying the fact does
   not grant the image.
2. **Grounding-text ≠ displayed-media.** Text an extractor reads to GROUND a claim
   (the source we cite for a fact) is not the same as media we SHOW a user. A
   descriptor may be grounded in the artist's own words without us publishing those
   words or any image verbatim.
3. **Resolve-identity ≠ crawl-a-site.** Matching an entity to a canonical id
   (MusicBrainz/Wikidata lookup, a `sameAs` link) is a cheap, bounded identity
   operation — it is NOT permission or intent to crawl that entity's whole website.
   The two have different cost, legal, and quota profiles.
4. **"Own domain" includes the venue/organizer as host.** "First-party / their own
   domain" is not only the artist — the venue or organizer hosting an event is a
   first-party source for that event. Treating only the performer as first-party
   drops legitimate authoritative sources.

## Why this is a §1-class defect

Each merge silently deletes a constraint: the rights question, the licensing
boundary, the crawl-authorization line, the source-authority scope. The plan then
proceeds as if the deleted constraint were satisfied, when it was never even
considered. Conflation reads as efficiency and behaves as a missed requirement.

## The rule

When two ideas sit close together, name them separately and answer each: what does
THIS one require, independent of the other? If a sentence would still be true after
swapping one concept for the other, you have probably conflated them — split it.
Also avoid the mirror-image error: don't frame a choice against an impossible
absolute ("risk-free", "perfect", "true by construction"). State the trade-off and
the live procedure that manages it.
