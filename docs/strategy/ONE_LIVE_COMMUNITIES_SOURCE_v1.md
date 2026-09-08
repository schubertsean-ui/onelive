# ONE LIVE — Communities as a Source (Meetup, clubs, groups) v1 — PROPOSAL

Greppable summary: founder-directed 2026-07-29 — "how can we include Meetup
data … book clubs, other clubs or groups on Facebook or Next Door … we'd still
point people to those sites to sign up but they'd find it on ours … design and
honoring our foundational operating beliefs and principles become crucial."
This proposes a THIRD content category — *communities* (ongoing groups/clubs) —
alongside verified events and tastemaker posts, with its own trust category,
card, placement, source tiers, safety line, and founder-decision list.

STATUS: **PARTIALLY RATIFIED (2026-07-29).** The founder BLESSED "communities"
as a new trust category and RATIFIED the **"Find your people"** lens name
("Good with Communities as the category. I like find my people — it's a nice
play in the Find My in an iphone. New trust category — bless communities"). The
remaining §9 decisions (scope/timing, Meetup licensing, FB/Nextdoor posture,
feed integration, safety line) are STILL PENDING — this is not yet a license to
build the ingestion path. Verbatim directives recorded at
`docs/memory/decisions/2026-07-29_communities-source-directive.md`.

---

## 0. The one-paragraph version

A "community" is an **ongoing group** — a Tuesday-night book club, a trail-run
crew, a boardgame meetup, a birding society. It is NOT a single dated event and
NOT a claim OneLive verifies the way it verifies a show. The right move is to
make communities a **first-class discovery layer that points OUTWARD**: we help
someone find the group here, then hand them to the group's real home (Meetup,
the library, the rec center) to actually join. We assert only what we can stand
behind — "this group is listed on Meetup, here's the link" — and never
manufacture facts, never lock people in, never rank by payment. Meetup (which
has a real, licensable API) is the honest beachhead; Facebook Groups and
Nextdoor are a legal/posture decision, not a scraping project.

## 1. Why this fits the mission — and where it must NOT bleed

The mission is "finding and engaging in experiences, helping individuals and the
culture thrive." Recurring communities are a huge, under-served slice of local
culture that a tonight-oriented event feed misses entirely. Including them is
on-mission. But it introduces a **new trust category**, and the charter is
explicit that categories don't bleed:

- **Communities are NOT verified events.** Same discipline as tastemaker posts
  (CLAUDE.md coding standards): community listings must **never touch the event
  candidate / gating / promotion pipeline**. A group is not an `event_candidate`
  and never becomes a canonical `event`. They live in a separate store with
  their own (lighter, clearly-labeled) trust model.
- **AI never publishes.** Any AI-written community blurb goes through the
  Descriptor Foundry (style new, facts never) and is gate-custodied like all
  descriptor copy; the group's factual fields (name, cadence, link) come from
  the source, never invented.
- **No pay-to-rank, ever.** A group's placement is by relevance / proximity /
  freshness — never by an organizer paying. Organizers may *claim* a listing
  (like a venue claim) but claiming never boosts rank.
- **Point out, don't wall in.** We deliberately send sign-ups to the group's
  real home. OneLive is the citable discovery layer (the GEO flywheel: be the
  best-attributed structured source), not a walled garden that intercepts the
  relationship.

## 2. The core distinction: a GROUP vs. a dated INSTANCE

This is the design crux. Two different objects, two different trust postures:

| | **Group** (the community) | **Instance** (one dated meeting) |
|---|---|---|
| Example | "East Austin Book Club" | "Book club — Thu Jul 31, 7pm, Cenote" |
| What we assert | "This group exists & is listed on \<platform\>" | "\<platform\> says this specific meeting is on" |
| Verification | freshness/active-signal only — never a "confirmed" claim | provenance = the licensed platform (confirmed-tier, like Ticketmaster) |
| Where it lives | the **communities layer** (a "Find your people" lens) | MAY surface in the main feed, rendered as a community card |
| Call to action | "See the group on Meetup →" | "RSVP on Meetup →" (never a OneLive ticket) |

**Recommendation (why this, not the alternatives):** keep the GROUP as the
primary object in a dedicated communities lens, and let a dated INSTANCE from a
**licensed API** surface in the main feed *only* when it's public and open —
always with the community card treatment and an external RSVP, never mixed
indistinguishably with verified ticketed events.

- *Alternative A — instances flow into the event feed as normal events:*
  rejected. It would blur the trust category (a Meetup RSVP is not a
  gate-verified show) and risk the pipeline-bleed the charter forbids.
- *Alternative B — communities never appear in the main feed, lens-only:*
  safe but under-delivers; a great open meetup tonight is exactly what someone
  scanning the feed wants. The hybrid keeps the wall (distinct card, external
  RSVP) while still surfacing the value.
- *Tradeoff of the hybrid:* one more card type to design and one more rule
  ("licensed + public + open" is the only instance that reaches the feed). Worth
  it; the wall stays crisp because the card itself signals the category.

## 3. Card anatomy (honoring the design brief's trust-display rules)

A community card must be **visibly a different kind of thing** than an event
card — that visual difference *is* the trust boundary made legible. Proposed
anatomy (final visual language is the Stitch/design loop's call):

- **Group name** + a one-line, fact-derived topic ("Contemporary fiction,
  monthly").
- **Cadence** — only if the source states it ("Meets every 2nd Tuesday"); else
  a quieter "Listed on Meetup," never an invented frequency.
- **Neighborhood / area** (coarse — a community is a *where-ish*, not a pin) and
  an optional rough scale if the platform provides it ("120+ members").
- **Platform provenance line**, quiet, always present: "Listing from Meetup"
  (the GEO/attribution principle — we never cloak the source).
- **External CTA**: "See the group on Meetup →" / "RSVP on Meetup →". No OneLive
  sign-up, no OneLive RSVP, no ticket.
- **Freshness affordance**: a quiet "active recently" / decay when a group goes
  quiet — the community analogue of the event freshness dial.
- **What's forbidden on the card** (design brief §3 white-hat line, extended):
  no "confirmed"/"verified" badge language, no manufactured scarcity ("spots
  filling!"), no negative-valence hooks. Same banned-claim discipline as the
  carousel/generator.

## 4. Placement in the product

- **A dedicated lens — "Find your people"** — parallel to the FLOW genre / area
  / nearby lenses. This is the home of the communities layer: browse ongoing
  groups by interest and neighborhood.
- **A labeled band in the main feed** — e.g. "Ongoing groups near you" — where
  community cards can appear inline but **under a header that names the
  category**, never silently interleaved with tonight's dated events.
- **Cross-link from events** — a jazz show can suggest the jazz-listening
  society; a trail race can suggest the run crew. Discovery reinforcing
  discovery, all pointing to real homes.
- **Voice + a11y** carry over unchanged (the Step 9 voice-navigation founder
  requirement, WCAG 2.2 AA): every community control is voice-addressable and
  keyboard-operable.

## 5. Source tiers & the legal line (the honest part)

Not all "communities" are equally licit to ingest. Tiered by how we're allowed
to get the data — cheapest-*and-cleanest* first (charter cost + legal
discipline):

1. **Meetup — the beachhead.** Meetup exposes a real API (GraphQL; Pro/API
   licensing). This is deterministic, **confirmed-tier by provenance** (the
   platform is the authority on its own groups/events), needs **no AI
   extraction**, and comes with ToS + attribution + rate limits we can honor.
   It is the same shape as the Ticketmaster/SeatGeek licensed spine already in
   the plan. **This is where we start.**
2. **Public civic / library / rec-center groups.** Many already flow through our
   existing licensed/public ingestion (library calendars, parks & rec). A
   standing "storytime," "maker night," or "senior walking club" is a community
   we can list from a source we already lawfully read.
3. **Organizer/community-submitted + claim flow.** A "submit your group" path
   and an organizer *claim* (identity-verified, like venue claim) — the lawful
   way to include groups that have no ingestible feed, including many Facebook /
   Nextdoor groups: **the organizer gives us the link; we never scrape it.**
4. **Facebook Groups & Nextdoor via scraping — NO.** Both platforms' ToS
   broadly prohibit automated collection, and neither offers a public "discover
   groups" API. Scraping them is a **legal-posture decision, founder-crucial,
   and the recommendation is: don't.** Reach these communities through tier 3
   (submitted/claimed links) instead — we still "point people to those sites,"
   we just don't harvest them.

## 6. Trust & safety — the duty of care pointing outward creates

Sending someone toward an external group is a small act of endorsement, so
communities need a content line the event feed doesn't:

- **Values exclusion.** No hate / harassment / extremist groups, consistent
  with the emotion-layer's negative-valence exclusion principle. This is a
  policy the **founder ratifies** (where exactly the line sits), enforced at
  ingestion and re-checked at display.
- **No verification of safety or outcome.** Copy must not imply OneLive vouches
  for who's in a group or that a meeting will happen — we assert existence +
  provenance + freshness, nothing more.
- **Freshness over deletion.** A dormant group decays out of surfacing rather
  than being asserted as "disputed." (The events-only rule "disputed shown as
  disputed, never hidden" is about verified events; communities use an
  active-signal/decay model instead — a different category, a different rule,
  stated so it's never conflated.)
- **RLS fail-closed** on the communities store, same posture as every other
  table.

## 7. Data model sketch (separate tables, no pipeline bleed)

Illustrative only — the real migration is a build-time decision:

- `community_source` — a licensed/public/submitted origin (mirrors the event
  `source` catalog discipline: reliability, ToS/attribution, cadence).
- `community` — the group entity: name, topic tags, cadence, area, external_url,
  platform, provenance, freshness/last-seen, claim state. **No FK into `event`.**
- `community_instance` (optional) — a dated meeting from a licensed source:
  start_time, place, external_rsvp_url, back-reference to its `community`.
- `community_provenance` — per-field origin + fetch record (auditable, same as
  event evidence — attribution is the moat).

trust_gate's existing invariant already forbids ads/tastemaker code from
importing the promote path; the communities module inherits the same structural
guard (a `communities/` module may not import `worker.gating`/`worker.promote`).

## 8. How this honors each foundational belief (the checklist)

| Principle | How communities honors it |
|---|---|
| AI never publishes | Facts from the source; AI blurbs via Descriptor Foundry + gate; no auto-publish |
| Categories don't bleed | Separate store, separate card, structural import guard — never an `event_candidate` |
| No pay-to-rank | Placement by relevance/proximity/freshness; claim ≠ boost |
| Trust display (no badges) | Quiet provenance line, no "confirmed"/scarcity language, freshness affordance |
| Point out, don't wall in | External sign-up/RSVP always; we are the discovery layer, not the destination |
| GEO/attribution moat | Structured, attributed, never cloaked — the most citable local community index |
| Cost discipline | Licensed API first (no scraping infra); reuse existing public feeds; submit/claim for the rest |
| Legal posture | Meetup licensed; FB/Nextdoor via submitted links only — scraping is off the table |

## 9. Founder decisions (the blockers — nothing builds until these are ratified)

Consolidated so it's one sitting, not a dribble:

1. **Scope & timing** — is communities a v1-stealth surface, or a fast-follow
   after CAPCOG go-live? (Recommendation: **fast-follow** — it's additive and
   shouldn't slow the ticketed-spine launch.)
2. **Meetup licensing** (money + new service = founder-crucial) — approve
   pursuing Meetup API access, with cost/rate caps set before any ingestion
   code, same discipline as every other paid source.
3. **Facebook / Nextdoor posture** (legal) — ratify the recommendation:
   **submitted/claimed links only, no scraping.** If you want more, that's a
   partnerships/legal conversation, not an agent build.
4. **Feed integration** — do licensed, public, open dated instances surface in
   the main feed (with the community card + external RSVP), or stay lens-only?
   (Recommendation: **hybrid**, §2.)
5. **Community content/safety line** — ratify where the values-exclusion line
   sits (§6); this is a judgment only you should set.
6. **The verbatim design intent** — ✅ **RATIFIED 2026-07-29**: "communities" is
   the trust-category name and **"Find your people"** is the lens name (a
   deliberate echo of the iPhone "Find My"). The labeled feed band remains part
   of the §9.4 feed-integration decision. This is the placement direction the
   Stitch/design loop renders against.

## 10. If ratified — the smallest first increment

A read-only, licensed, lens-only beachhead (mirrors how the Tasting Trail and
CAPCOG spine started — one honest slice, then widen):

1. Meetup licensed read → `community` rows for one metro (Austin), confirmed-tier
   by provenance, attribution stored.
2. The "Find your people" lens on `/tonight` (or its FLOW equivalent) rendering
   community cards — external CTA only, no feed interleave yet.
3. Freshness/decay + the values-exclusion filter live from day one.
4. Evaluator pass against this doc + the design brief's trust-display rubric;
   deltas recorded, never silent.

Everything past that (feed band, submit/claim flow, second metro, dated
instances in the feed) is a later, separately-ratified increment.
