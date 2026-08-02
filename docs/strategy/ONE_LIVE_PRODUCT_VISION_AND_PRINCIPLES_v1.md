# 1LIVE — Product Vision, Principles & Future Surfaces (v1)

**Status (2026-07-29):** Founder-supplied product canon, captured verbatim in
substance for use as **content work** begins and as the reference for **future
functionality builds**. Authority levels within this doc:

- **PRINCIPLES / RIGHTS / RULES / RED LINES** — governance canon. These are
  founder-stated commitments. Several already exist as enforced trust
  invariants (see "Mapping to existing canon" at the end); the rest are binding
  intent for anything built later.
- **FUTURE SURFACES** (night-out experiences, matching, transportation, AV
  integration, livestreaming, heartbeat analytics) — directional vision. Each
  is a **net-new build** that, when it comes, gets its own contract, trust
  review, and (where it touches money/new services/data/AV) a founder-crucial
  escalation. Nothing here is live yet, and **nothing here relaxes any existing
  gate**.
- **DIRECTIONAL TECHNICAL NOTES** — the founder's own words: *"not gospel but
  directional."* Implementation choices (libraries, thresholds) are subject to
  the normal engineering bar and may change; the intent is what's canon.

Related canon this complements: `CLAUDE.md` (trust invariants, no-pay-to-rank),
`docs/strategy/ONE_LIVE_EMOTION_VIBE_LAYER_SPEC_v1.md`,
`docs/strategy/ONE_LIVE_CATEGORY_TAXONOMY_v1.md`,
`docs/strategy/ONE_LIVE_CERTAINTY_DISPLAY_v1.md`, the design brief.

---

## The vision — "the ethical heartbeat of culture"

Beyond listings, 1LIVE curates **"night out" experiences** (pre-drinks →
dinner → gig → cocktails → munchies, with open tables **beyond Resy/OpenTable**),
**matches** artists / venues / bars / restaurants for gigs, practice, and
sessions on slow days, integrates **transportation** (Uber / Lyft / Waymo for
surges & bookings), enables **opt-in livestreaming** (e.g. 15 min free with pay
for full; private sessions), and provides **"heartbeat" analytics** on city
flows (event density, ride demand, open tables, surge alerts).

**Autonomous vehicles (AVs)** opt-in for in-ride suggestions (e.g. "Music
ideas?" pulling events / dining / exhibits / specials / chef meals / private
dining). In 2026's indie surge and AI-ethics focus, 1LIVE is the ethical
**heartbeat of culture**, extending to AVs for seamless mobility.

---

## Core Principles (governance canon)

- **No pay-to-rank.**
- **Artist sovereignty** — free data, instant corrections, **70% splits**.
- **Social validates, never defines.**
- **Amplification / livestreaming opt-in and separate.**
- **No artist-level data resale without consent.**
- **Aggregate insights only.**
- **Permission-first for AV integrations.**

## Artist Bill of Rights

1. **Listed by default if playing.**
2. **Never pay for discovery.**
3. **Instant corrections.**
4. **Proper genre representation.**
5. **Free access to your own data.**
6. **Opt-in monetization / livestreaming.**
7. **No data sold without consent.**
8. **Compete on music, not money.**

## Venue Principles

- **Appear based on activity** (not payment).
- **Instant corrections.**
- **Benefit from trust.**
- **Sharing for slow days / practice.**

## Platform Rules

- **No sponsored discovery.**
- **No hidden boosts.**
- **No algorithmic suppression.**
- **No social-only listings.**
- **AV prompts opt-in.**

## Red Lines (dissolution triggers)

Violations — e.g. **pay-to-rank**, **non-aggregate data resale** — trigger
**dissolution**. These are the hardest commitments in the product; treat any
proposed feature that approaches them as founder-crucial.

---

## Why 2026 (context & trends)

Fragmented discovery (social noise, ticketing bias); artists increasingly
independent; fans want local / personalized experiences; cities reinvesting in
culture (~25% budget increases); AVs expanding (Waymo in 5+ cities).

**Trends:** indie surge (~40% of releases); nostalgia marketing;
Afrofuturism / organic sounds; mystery campaigns; dynamic / decentralized
platforms; AI ethics in communities; demand for hybrid events / livestreams.

---

## Future surfaces (directional — each a later, separately-gated build)

### Night Out Experiences
AI-curated chains: pre-drinks bar → dinner restaurant → gig → cocktails bar →
munchies spot. Pull open tables from **venue claims** (details `jsonb`);
suggestions **beyond Resy/OpenTable** with specials / private / chef-curated via
an AI prompt.

### Matching Moat (sharing economy)
Venues / artists / bars / restaurants post **availability slots** (`jsonb` with
days / type / backline / genres / price); opt-in prefs; **score-based matching**
(genre 40%, location 30%, price 20%, reliability 10%); a daily Celery task
produces suggestions; notify via alerts. Purpose: fill slow days; enable
practice / sessions.

### Transportation Integration
Ride quotes / bookings / surge awareness (Uber / Lyft / Waymo APIs); predict
from event ends + heartbeat (e.g. "Show ending — surge alert").

### Autonomous Vehicle Integration (opt-in, permission-first)
Opt-in in-ride prompts ("Up for entertainment / dining ideas?"); an API for
personalized suggestions — music events (venue + music descriptions),
restaurants (open tables / specials / private / chef meals), museums /
exhibits, bars (specials) — based on location / prefs. **AV prompts are opt-in;
integrations are permission-first.**

### Amplification / Livestreaming (opt-in, separate)
Opt-in **post-confirmation** (preconditions: **confirmed, not disputed**; also
an **artist opt-in check**). 15-min free → paywall (Stripe) for full; private
sessions for fans. Amplification is a separate surface from the trust feed and
never affects ranking.

### Heartbeat Analytics
Aggregate, real-time analytics on flows — event density, ride demand, open
tables, surge alerts; predictive alerts (e.g. "Gig ending — notify Uber for
surge"). Monetized as **insights** (premium dashboards, city contracts) —
**aggregate only**, never artist-level resale without consent.

---

## Directional technical notes ("not gospel but directional")

4. **Normalize** — timezones (pytz), fingerprints for dedupe.
5. **Dedupe** — deterministic + fuzzy (rapidfuzz string similarity >80%; a
   dedupe-ML linkage path with training data for advanced cases).
6. **Confidence / SXSW** — weighted evidence; multi-confirms; **SXSW mode**
   (threshold 2.2, min 2 independent sources, surprise rule: venue/artist +
   proof); overrides lock.
7. **Distribution** — `/tonight` API for feeds; premium alerts / offline access
   (AsyncStorage).
8. **Amplification / Livestreaming** — opt-in post-confirmation (preconditions:
   confirmed, not disputed; 15-min free paywall via Stripe; private sessions).

**Social / Media policies:** treat social as **evidence / weak signal only
(weight 0.2)**; never create / override / rank / suppress; `validate_with_social`
checks existence / override-lock / corroboration before attaching; amplification
preconditions include the artist opt-in check.

---

## Who benefits & why it matters

- **Artists** — free listings, corrections, analytics, cosigns, nostalgia
  tools, matching / livestreaming for gigs / practice / sessions. *Builds
  exposure in the indie surge — compete on music.*
- **Fans** — personalized feeds, hidden gems, AR previews / parking, the
  experience builder, AV suggestions, livestream access. *Seamless culture
  discovery.*
- **Venues** — insights / badges, demand patterns, matching, livestream
  showcases. *Fills slow days.*
- **Partners (restaurants / bars / transport / AV providers)** — ads, ROI from
  flows / surges, affiliate bookings. *Ethical reach.*
- **Cities** — aggregate graphs / contracts for planning. *Cultural
  visibility.*

---

## Mapping to existing canon (what's already enforced vs. net-new)

**Already live / enforced today** (this doc reaffirms, doesn't change):
- No pay-to-rank — a hard trust invariant in `CLAUDE.md`, enforced by
  `trust_gate`.
- Social validates never defines; disputed shown-never-hidden; confidence
  states (`unverified | likely | confirmed | disputed`) — canon in `CLAUDE.md`.
- Listed-by-default and the AI-never-publishes gate — the extraction→gate→
  promote pipeline.
- `/tonight` feed distribution — live.

**Net-new (future builds, each separately gated):** night-out experience
chaining, the availability-slot matching moat, transportation/surge integration,
AV in-ride suggestions, opt-in livestreaming + Stripe paywall, and heartbeat
analytics / city dashboards. Each introduces new services, money flows, and/or
data surfaces — so each will arrive with its own contract, trust review, and a
founder-crucial escalation where it touches spend, new services, data resale,
or AV. The **70% artist split**, **consent-gated data**, and **aggregate-only
insights** commitments bind those builds from day one.
