# 1LIVE — Scale-Out Sensor Architecture v1 (watchers, three modes, provenance-weighted gate)

**Compiled 2026-07-14 · Status: RATIFIED 2026-07-14 — founder decisions (verbatim anchors below). Supersedes nothing; extends the pipeline architecture (CLAUDE.md) past the current critical path. Build triggers per section — RATIFIED ≠ build-now.**

Greppable summary: founder-directed design for entity-scale coverage.
Accountability = cheap watcher RECORDS (not persistent LLM agents); three
engagement modes (proactive pull / responsive push / investigative
escalation); provenance-weighted gate with a validated FIRST-PARTY fast
lane entering at `confirmed` (both channels: verified external channels
and authorized in-product accounts); scoped authority + dispute override;
scout swarm for discovery. AI engages per-change, never per-entity-idle.
Every mode feeds the same gate; AI never publishes — unchanged physics.

## Founder decision anchors (verbatim)
1. Agent-per-entity intent: "dozens and hundreds and thousands … of dedicated agents whose job is to be an assigned actionee" + swarm "to scout and scour … 24hrs/day" (2026-07-14).
2. Engagement modes: "proactive: active search, noticed a change that warrants investigation for relevance; responsive: change pushed to them (subscribed to a newsletter or fan club or what have you)" (2026-07-14).
3. First-party split: "if it comes from the venue/artist/club/group/entity, and we validate domain and other aspects, we should give that a high value of truth" (2026-07-14).
4. Ratification: "I'm good with the proposed rule" + "if the information is in the system via their authorized account, it's also confirmed" + "Record it." (2026-07-14).

## 1. Watcher records — assignment without idle agents
Every identified entity (venue, artist, club, group, performance series,
activity) gets a **watcher record**: identity, registered sources, verified
first-party channels, last-checked / last-verified timestamps, staleness
alarm, lifecycle state. This delivers the founder's "assigned actionee" as
an auditable database fact at any scale (10² to 10⁵ entities) for the cost
of rows and schedules. The expensive AI mind engages **per change**, routed
per docs/MODEL_ROUTING.md — never per entity per tick. (Rejected
alternative, costed: persistent LLM agent per entity ≈ $1k+/day at 10⁵
entities mostly discovering nothing changed; watcher records + on-demand
extraction produce the identical user-visible result for ~pennies/10³
entities/day. Charter Cost discipline §1.)

## 2. Three engagement modes (all feed the same gate)
- **Proactive (pull):** scheduled fetch + diff of registered sources
  (Sprint Step 5 machinery); discovery scouts (§5). Pays per look; cadence
  matched to the domain's pulse (hourly known-source ingest; tightening
  day-of; daily→weekly discovery).
- **Responsive (push):** subscriptions — newsletters into a dedicated
  ingest mailbox, RSS/ICS feeds, official social follows, webhooks where
  offered. Zero cost while quiet, instant on change. Requires ONE founder
  service decision when built: the ingest mailbox (founder-crucial: new
  service + credential). Push content is untrusted input like all input —
  Step 6's injection golden-set cases apply verbatim.
- **Investigative (escalation):** a change (from either mode) that warrants
  judgment → relevance check, cross-source corroboration, evidence
  assembly → confidence state. This formalizes the existing Evidence →
  Gate stages; the verdict IS the product.

## 2b. Channel sign-up playbook (founder ask 2026-07-14: "how do we best 'sign up'?")
The channel registry is an OPEN taxonomy — each watcher record holds any
number of channels, each with a TYPE, a subscription method, a validation
method, and a trust class. New channel types are config, not code rewrites
("any number of other unnamed channels" — founder). Priority: cheapest
reliable first, per entity:

| Priority | Channel | Sign-up mechanics | Trust class |
|---|---|---|---|
| 1 | ICS/RSS feeds (venue calendars, univ. press offices, civic calendars) | one-time feed registration; free, structured, push-shaped | First-party when served from the entity's canonical domain |
| 2 | Newsletters (venue/artist/fan-club email) | subscribe the dedicated ingest mailbox (founder decision, §2) | First-party when DMARC-aligned with the registered domain; else third-party |
| 3 | Canonical website | fetch+diff on cadence (§2 pull) | First-party (their domain) |
| 4 | Instagram / Facebook / socials | register the entity's OFFICIAL handles on the watcher record; platform accounts/API access founder-minted | First-party from registered official handles (hijack caveat §3.2 applies); everything else third-party |
| 5 | Industry aggregators (Bandsintown, Songkick, ticketing platforms, Do512-class local listers, vertical sources per category — food, campus, civic) | API where offered; **ToS/data-licensing review is FOUNDER-CRUCIAL (legal posture) before scale use** | THIRD-party always (they aggregate) — high-quality corroboration + discovery, never the fast lane |
| 6 | LinkedIn / press offices / PR distribution | mostly a DISCOVERY lens for the scout swarm (bookers, promoters, openings), not a per-event watch channel | Third-party |

Notes: (1) most entities need only their 1–2 cheapest channels most days —
channel count follows entity value, not maximalism (Cost discipline §1);
(2) aggregators double as corroboration engines for third-party claims —
they make the `unverified → likely/confirmed` climb cheap; (3) the two
standing founder decisions this table creates when push channels build:
the ingest mailbox, and aggregator ToS/licensing review.

## 3. The provenance-weighted gate (RATIFIED trust policy)
**First-party provenance is a weight INSIDE the gate, never a bypass.**
Two validated first-party channels, equal rank:
- **Verified external channel:** content arriving via a channel registered
  on the watcher record and mechanically validated — email whose
  DKIM/SPF authentication is DMARC-ALIGNED with the entity's registered
  domain (alignment required: a generic SPF/DKIM pass on a forwarding or
  vendor domain proves nothing about entity control); content fetched from
  the entity's own canonical domain; posts from its registered official
  handles. Validation is cryptographic/mechanical code, never vibes.
- **Authorized in-product account:** the entity (or designee) enters the
  information in 1Live through its claimed, authenticated account (the
  existing venue/creator claim flow; auth checks per CODING_CONVENTIONS).

**The rule (founder-ratified):** a validated first-party assertion about the
entity's OWN event logistics (time, date, lineup, cancellation, venue-side
facts) enters at **`confirmed`**. Third-party claims enter at `unverified`
and climb via corroboration, as today. Cost effect: the corroboration
machinery is reserved for third-party claims; day-of first-party changes
(the highest-value facts) skip third-party-style corroboration — validate
mechanically, extract, CHECK AGAINST EXISTING CONTRADICTORY EVIDENCE (a
standing cheap check, so a live dispute is never steamrolled by the fast
lane), promote.

**Boundaries (all three load-bearing):**
1. **Scoped authority:** first-party weight applies field-by-field to the
   entity's own logistics. Never to claims about OTHER entities, never to
   subjective/quality content. (Marketing copy is not data; and tastemaker
   / opinion content remains a fully separate trust category that never
   touches this pipeline — unchanged.)
2. **High truth ≠ command authority:** validated first-party input asserts
   facts only; it can never instruct the system (injection rule). Basic
   sanity checks (schema, plausibility, mass-change alarms) still run on
   the fast lane — cheap checks, not investigations — because verified
   channels can be hijacked.
3. **Disputed still wins:** a credibly contradicted first-party fact goes
   to `disputed`, shown-never-hidden. First-party raises the entry point;
   it grants no immunity. The 4-state model is unchanged.

## 4. Dedup & multi-source identity
The same show will arrive via pull, newsletter, and fan post — a feature
(corroboration), if the matching engine recognizes "same event". Matching
quality is load-bearing for this whole design; its eval cases join the
golden set when push channels build.

## 5. Scout swarm — discovery, gated
A small set of scheduled scout agents with distinct lenses (new venues,
artist socials, ticketing platforms, city permits, neighborhood
newsletters) proposing CANDIDATE sources/entities. Scouts propose, the
gate disposes; admin review before any watcher record is created. Grows
from the existing weekly source-backfill workflow (which attacks R-007).
Every scheduled scout carries the charter's budget cap + dead-man ping.

## 6. Build triggers (RATIFIED ≠ build-now; current critical path unchanged)
| Piece | Builds when |
|---|---|
| Watcher records (schema + freshness SLOs) | Sprint Step 7 (gate→candidate flow on real data) |
| First-party `confirmed` rule in gate code | With watcher records (same PR as channel verification; evaluator mandatory — trust-critical) |
| Push channels + ingest mailbox | After Step 7; mailbox = founder decision (new service) |
| Scout swarm (multi-lens) | After Step 7; extends source-backfill; caps + dead-man first |
| Authorized-account entry = confirmed | Phase 2 claim flows (already designed); rule recorded now |

## Appendix — Po harvest (battery run 2026-07-14, seed 20260714, word: "beehive")
CANDIDATE ideas only — each traceable to its provocation; none ratified;
they feed normal planning through normal gates (M6 ledger row filed):
- **P1 ESCAPE** ("Po: venues do not know their own schedules") → sometimes TRUE: promoters/bookers know first. Harvest: watcher records support MULTIPLE authorized parties per entity/event (founder's "designee" made structural). When validated first-party signals conflict, the newer one may become the PREFERRED value, but the conflict is never silently collapsed — it surfaces per §3 boundary 3 (disputed, shown-never-hidden), with provenance recorded for both signals.
- **P3 EXAGGERATION** ("Po: 10,000 events tonight" — SXSW is real) → ingestion must degrade gracefully under burst: priority queue by user-relevance under budget caps. Down-version ("one event a year") → watcher lifecycle states incl. HIBERNATED — stop/slow POLLING only: the record still accepts push, manual, and contradiction signals (a dormant entity must never become invisible), and any such signal wakes it.
- **P4 DISTORTION** ("Po: review happens before extraction") → per-source extraction templates: once a source's format is reviewed, subsequent extractions get cheaper/deterministic — review once, extract cheaply forever.
- **P5 WISHFUL** ("Po: every event verifies itself") → the ratified fast lane IS this; extension harvested: "confirm your listing" outreach emails to venues — the link INITIATES the verified claim/auth flow (§3: claimed authenticated account or mechanical domain-control validation; single-use, expiring, replay-protected, audited). Link possession alone confirms NOTHING — a forwarded link must be worthless. Only after verification completes do the entity's assertions carry first-party weight. Candidate growth+trust loop in one.
- **P7/P8 RANDOM "beehive"** (scouts/foragers dance to recruit; hive throttles foragers by nectar flow) → attention allocation by expected change rate: sources that keep yielding changes get watched harder; quiet ones decay to slower cadence — the "rotating beam" instead of flat polling.
