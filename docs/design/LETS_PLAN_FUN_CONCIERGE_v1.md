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

**The sequencing honesty rule.** We show the *time* gap between stops because
we have both timestamps. We do **not** show travel time, distance, or "12 min
away" — we do not have venue coordinates, so any such number would be invented.
The panel says the gap and, when two stops share a `venue_area`, says they're
in the same area, which is a fact we hold. When we later ingest coordinates,
travel time replaces the gap; until then the copy stays honest, matching the
existing note on the Ask panel ("we won't guess it").

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
the user the whole plan is guesswork. Shipping gaps-we-know instead of
distances-we-don't is what keeps the feature trustworthy while the coordinate
data catches up.

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
   labeled packages, each a sequence of real upcoming events with the gap
   between stops shown.
2. Selecting nothing and picking a scope returns exactly what the panel returns
   today — the change is additive, proven by a regression test.
3. No package ever claims a distance, travel time, or "walkable" without
   coordinate data behind it; a test asserts the absence of those strings.
4. Every headline in every package carries the same trust mark as the feed, and
   any ticket link opens in a new tab rather than taking over the screen.
5. A tight connection (gap below the threshold) is visibly flagged rather than
   quietly presented as feasible.

## Not in v1 (named, not forgotten)

Reservations and bookings placed *through* 1Live; travel time and mapped
routing; saving or sharing a package; a package that spans multiple days beyond
the existing weekend scope; personalization that remembers past choices. Each
needs either data or a service we do not have yet; none is blocked by this
design.
