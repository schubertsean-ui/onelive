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
`city_calendar`, `university_calendar`, `university`, `library_calendar`,
`theater_arts`, `gallery_museum`, `food_culinary`,
`claimed_upload`, `email_opt_in`, **`local_media`** (newspapers,
periodicals, radio, TV — added by the second directive above).

**Needs ONE corroborating source (two in SXSW/chaos mode)** — third-party
republishers who are not the event, artist, or venue speaking for
themselves: `social`, `blog`, `artist_aggregator`, `artist_directory`,
`music_platform`, `link_hub`, `directory`, `community`, and any
unrecognized class (unknown ⇒ cautious tier, never the anchor tier — the
fail-closed direction is preserved for classes nobody has ruled on), which
now also WARNS loudly rather than holding in silence.

### Two amendments to this record, made 2026-08-05 after PR #191

Both come from the same discovery and neither changes the founder's ruling —
they change which classes the ruling reaches.

**`theater_arts`, `gallery_museum`, `food_culinary`, `university` added to
the anchor tier.** These classes exist in the LIVE database, seeded outside
this repo: the committed catalog carries 180 sources while the ingest run
log for run 31048812960 reports *"processing 5 of 266 enabled sources this
run."* No code in this repo defined them, so every one fell through to the
corroboration branch and waited for a second museum to confirm the first —
a wait that never ends. A theater's own site announcing its own season is
the horse's mouth by the founder's own test, so the ruling already covered
them; only the code did not know their names.

**`community` moved OUT of the anchor tier**, reversing this record's first
pass. A community PLATFORM (Meetup-style) is not the host of what it lists,
so it fails the founder's "comes from the source site" test — the platform
is not the source site, the group is. The live rows are also unaudited.
Being wrong in this direction costs one corroborating source; being wrong
the other way asserts an authority we cannot back.

Both halves of the vocabulary are now pinned against each other by a test
(`test_gate_and_confidence_never_disagree_about_first_party`), and against
the importer's `KNOWN_SOURCE_CLASSES` by the pre-existing drift guard —
an anchor the importer would reject is an anchor no source can ever have.

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
