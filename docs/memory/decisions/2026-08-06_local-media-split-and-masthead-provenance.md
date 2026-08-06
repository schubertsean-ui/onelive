# Local media splits into masthead vs UGC — and the standing question of how
# first-party status is DECIDED at scale

**Date:** 2026-08-06
**Status:** Founder-approved (the split). The strategic question it opened is
OPEN and unanswered — recorded here verbatim so it cannot lapse.

## The founder's words, verbatim

> "I'm ok with the split, however… Are you thinking long term and
> strategically that as we roll this out we will encounter these issues and
> more complexity so what is the best solution to ensure that radon [radio]
> stations, tv stations, periodicals, newspapers, community bulletins, etc are
> appropriately identified and treated correctly as first party sources? Show
> me examples of a community calendar. And have you looked at the listings?
> They may contain websites or links to the org we can then verify as a first
> party."

## What was approved

`local_media` is ONE class today and carries two different kinds of row:

- **Masthead** — the outlet's own editorial calendar. A newspaper's or radio
  station's staff-curated listings. This is genuinely first-party to the
  outlet: a real editor put it there.
- **UGC** — a submission widget (Trumba and similar) embedded on the outlet's
  domain. Anyone with a browser fills in a form and the listing appears. The
  domain says "newspaper"; the provenance says "a stranger typed this."

The approved change: split the class so masthead rows can anchor (promote on
one source) and UGC rows cannot (they need corroboration like any third
party). NOT YET BUILT — queued behind PR #191.

## Why this mattered enough to stop for

I had recommended the UNION — anchoring all of `local_media`. The adversarial
pass proved 4 of the 14 rows in that class are user-submitted Trumba widgets
that **our own source catalog already annotates "treat unverified."** Under my
recommendation, anyone filling in a TV station's public submission form would
have published to the live site alone, marked `confirmed`. The catalog knew;
the gate did not. I was wrong and the review caught it.

## The strategic question — OPEN, founder-raised, unanswered

The founder's point is that this is not a one-off. Radio, TV, periodicals,
newspapers, community bulletins — the whole media tier — will keep presenting
this exact ambiguity, and hand-classifying each one does not scale. Deciding
first-party status by DOMAIN is the flaw: the domain is the outlet, but the
provenance lives in the individual listing.

The founder's own proposed direction, recorded because it is the most
promising lead we have: **the listings themselves frequently link out to the
organizing venue or org.** A community-calendar entry for a show at a named
venue usually carries that venue's URL. If we follow that link and it resolves
to a domain already in the catalog as first-party — or to a site that declares
the same event in schema.org markup — then the listing is corroborated by the
ORG ITSELF, not by the outlet that republished it. That converts a
per-domain judgment call into a per-listing evidence check, which is the
shape the trust pipeline already has.

**Status of that idea:** I proposed building a read-only probe to measure how
often listings actually carry such links (the whole idea rests on that
frequency, which nobody has measured). The founder has not yet answered
whether to build it. Nothing is being built on this until they do.

Also unanswered from the same exchange: showing worked examples of a real
community calendar, which is what would make the masthead/UGC distinction
concrete rather than abstract.

## What does NOT change

Nothing about gate custody. A masthead anchor still passes the full gate;
`disputed` is still shown-never-hidden; an unclassified class still HOLDS and
logs loudly. The split makes one class stricter, not looser — it is a
tightening, so it is not a gate-threshold relaxation.
