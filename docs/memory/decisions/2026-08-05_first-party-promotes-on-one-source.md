# 2026-08-05 — First-party and published sources promote on ONE source

## Founder directives (verbatim, 2026-08-05)

Asked whether "source site is authoritative" extends to the promotion gate's
corroboration hold:

> Yes, and I e said this before. […]
> For god sake only if it's a social media site first that is not the event
> itself or the artist themselves or the venue itself or on and on
> Then it gets a secondary source.
> Repeat back to me what the rules are

And, confirming the repeat-back and settling the published-media question:

> correct and yes, newspapers, periodicals, radio and tv stations, etc are
> all first party authoritative. We are tracking the sources internally so
> we can learn which may wind up having issues over time.

## The rules, as implemented

**Promotes on ONE source (anchor tier)** — principals publishing their own
events, and published media under their own masthead:
`venue_calendar`, `ticketing`, `festival_feed`, `calendar_feed`,
`city_calendar`, `university_calendar`, `library_calendar`, `community`,
`claimed_upload`, `email_opt_in`, **`local_media`** (newspapers,
periodicals, radio, TV — added by the second directive above).

**Needs ONE corroborating source (two in SXSW/chaos mode)** — third-party
republishers who are not the event, artist, or venue speaking for
themselves: `social`, `artist_aggregator`, `artist_directory`, `link_hub`,
`directory`, and any unrecognized class (unknown ⇒ cautious tier, never the
anchor tier — the fail-closed direction is preserved for classes nobody has
ruled on).

The moment ANY second source corroborates a third-party-social event it
promotes; a first-party second source promotes it immediately as an anchor.

## What did NOT change

- Confidence derivation follows the same tiers (anchor ⇒ `confirmed`), so
  display copy and the 4-state model are untouched.
- Disputed remains a moderation decision, always shown, never inferred.
- Every candidate still records each source's class in evidence rows — the
  founder's tracking requirement: per-source credibility is measurable over
  time from the data already stored, so a source that "winds up having
  issues" can be found and re-classed without guesswork.

## Practical effect

The "Insufficient corroboration (have 1; need 2)" hold that was stopping
~4 of every 5 sources in live verification runs applies only to third-party
social/aggregator intake from here. Venue calendars, theater seasons, city
and chamber calendars, and local media promote on first sight.
