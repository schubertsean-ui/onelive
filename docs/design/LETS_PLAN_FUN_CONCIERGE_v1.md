# "Let's Plan Fun" — concierge planning, v1 PLAN (awaiting founder approval)

Status: **PLAN ONLY — not built.** Presented under OPERATING_RULES §4a (plan-first).
Directive record: `docs/memory/decisions/2026-08-05_lets-plan-fun-concierge.md`
(founder, verbatim, 2026-08-05) plus the follow-up "use these existing to build
it out — 'Plan a day / night / weekend'".

---

## WHAT

Turn the existing **Plan a day / night / weekend** panel from a one-shot
suggestion into a concierge: the user checks off what sounds fun, and 1Live
returns **two or three complete packages** — sequenced stops with real travel
time between them — rather than a single take-it-or-leave-it itinerary.

Concretely, three changes to one surface:

1. **A preference step.** Before the plan builds, the user picks from checkable
   chips — what kind of fun (live music, food, comedy, outdoors, art, sports),
   the budget shape (free / cheap / splurge), and the vibe (loud / mellow /
   somewhere new). Nothing is required; skipping straight to "plan it" gives
   exactly today's behavior.
2. **Packages, not a package.** The builder returns up to three distinct
   itineraries — e.g. one that stays in one neighborhood, one that is all-free,
   one that leans into the strongest single event of the night — each labeled
   with what makes it different, so the choice is legible instead of arbitrary.
3. **Sequencing with real gaps.** Stops are ordered so the user can actually
   make them: each hand-off shows the gap between the end of one and the start
   of the next, and flags a stop as tight when the gap is too small. Where a
   stop has a ticket or reservation link, the package surfaces it inline as a
   new-tab hand-off (the 2026-08-05 external-link ruling — never a full-screen
   takeover).

## HOW

All of it lands in code that already exists, which is why this is a small build
rather than a new subsystem:

- `web/lib/feed.ts` — `buildPlan(events, scope, nowMs)` already walks time
  blocks from `planBlocks(scope)` and picks one event per block with a
  neighborhood/domain bias. v1 generalizes it to
  `buildPackages(events, scope, nowMs, prefs)`: the same block walk, run three
  times under three different scoring weightings, deduped so two packages that
  come out identical collapse to one. `buildPlan` stays as a thin wrapper so
  nothing that calls it today changes behavior.
- `web/app/(public)/tonight/FeedApp.tsx` — `PlanPanel` gains the chip row above
  the existing scope buttons and renders a package switcher instead of a single
  `.plan` list. `TrustMark` stays on every headline exactly as it is now (trust
  rides every surface — the 2026-08-04 adversarial catch).
- Tests: `web/lib/feed.test.ts` gets cases for package distinctness, preference
  filtering, gap computation, and the tight-connection flag; a component test
  covers the empty-preference path returning today's behavior unchanged.

**The sequencing honesty rule.** We show the *time* gap between stops, because
we have both timestamps, and the straight-line *distance*, because we have
coordinates. We do **not** show travel time, "12 min away", or a mode word
like "walkable" — those need routing data we do not have, and 0.4 miles across
I-35 is not a walk.

> **Correction, same day.** An earlier draft of this plan said we have no
> venue coordinates and proposed leaning on `venue_area` instead. That is
> backwards. `worker/importers/normalize.py` writes real `venue_lat`/`venue_lng`
> for Ticketmaster (L168–169), SeatGeek (L221–222) and Eventbrite (L312–313),
> and writes `"venue_area": None` for all three (L166, L219, L310) — as does
> `structured_feed.py:573`. Only promoted rows carry an area, from the venue
> catalog. So coordinates are the live signal and `venue_area` is the dead one,
> which also means `buildPlan`'s existing same-neighborhood bias is inert on
> imported events today. The build uses coordinates; the honesty rule now
> constrains the *mode word*, not the number.

The distance type carries miles and never minutes, so there is no field from
which a travel duration could be rendered — the no-fabrication rule is a
property of the type, not a discipline someone has to remember. Where a venue
has no coordinates we say so by name and give no distance at all, rather than
quietly omitting the leg.

**Where preferences filter, and where they only rank.** A checked "free"
filters — the user asked for free, showing a $40 show is a wrong answer. A
checked "live music" *ranks* rather than filters, so a night with thin music
listings still returns a package instead of an empty state. Every package says
which preferences it honored and which it could not, so a compromise is never
silent.

**No new data, no new service, no spend.** v1 reads the licensed-event feed the
page already fetches. No API, no model call, no cost.

## WHY

The founder's frame is a concierge, and a concierge does not hand you one
itinerary — it offers you a couple of shaped options and tells you what
distinguishes them. Today's panel is closer to a lucky-dip: it silently makes
every choice for you, gives one answer, and the only recourse is "try Browse."
Preference chips plus a small set of packages is the smallest change that turns
that into an actual service.

Building it inside the existing surface (the founder's explicit instruction)
rather than as a new mode also means it inherits everything already proven
there: trust marks on every headline, price honesty, the disputed-shown-never-
hidden rule, and the new-tab external hand-off.

### Why that matters

The whole product bet is that 1Live answers "what should I do tonight" better
than a search box. A feed answers "what is happening"; a plan answers "what
should I do." The plan surface is therefore the feature the bet actually rides
on, and it is currently the least developed thing on the page. Making it
concierge-grade is the difference between a listings site and the thing the
founder described.

The honesty constraint matters just as hard: a concierge that invents travel
times is worse than no concierge, because the first missed connection teaches
the user the whole plan is guesswork. Shipping the two numbers we actually
hold — the time gap and the straight-line distance — and refusing the one we
don't is what keeps the feature trustworthy. The correction above is the
argument in miniature: the first draft of this plan got the data inventory
backwards in both directions, and only reading the importers settled it.
Whatever the panel renders has to trace to a field, not to a recollection.

## Alternatives considered

- **A conversational planner (free-text "plan my Friday").** Rejected for v1:
  it needs a model call on every request, which is spend on a surface with no
  usage data yet, and it makes the output unpredictable right where trust
  matters most. Chips are legible, free, and testable. Revisit once the surface
  has real traffic.
- **A separate "Concierge" mode next to Browse / Ask / Plan.** Rejected — the
  founder said to build it into the existing plan surface, and a fourth mode
  splits a small feature across two places.
- **Ranking by ticket availability or partner status.** Rejected permanently:
  pay-to-rank is a charter invariant, and availability data would come from
  third parties whose incentives are not the user's.

## EXPECTED OUTCOMES

When this is done:

1. Selecting any combination of chips and a scope returns between one and three
   labeled packages, each a sequence of real upcoming events showing both the
   time gap and the straight-line distance between stops.
2. Selecting nothing and picking a scope returns exactly what the panel returns
   today — the change is additive, proven by a regression test.
3. No package ever renders a travel duration or a mode word ("walk", "drive",
   "walkable"); a test asserts the absence of those strings, and the distance
   type carries no minutes field for one to be computed from.
4. A leg whose venue lacks coordinates says so by name and shows no distance,
   rather than silently dropping the leg.
5. Every headline in every package carries the same trust mark as the feed, and
   any ticket link opens in a new tab rather than taking over the screen.
6. A tight connection (gap below the threshold) is visibly flagged rather than
   quietly presented as feasible.

## Not in v1 (named, not forgotten)

Reservations and bookings placed *through* 1Live; routed travel time (needs a
routing service, which is spend); saving or sharing a package; a package that
spans multiple days beyond
the existing weekend scope; personalization that remembers past choices. Each
needs either data or a service we do not have yet; none is blocked by this
design.
