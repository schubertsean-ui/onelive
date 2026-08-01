# ONE LIVE — Community & Events Platform Growth Mechanics — v1

**Status:** PROPOSAL (research-backed, 2026-08-01). PROPOSAL ≠ license to build — this is the
acquisition-side research companion to the ratified-in-part
`ONE_LIVE_GROWTH_LOOPS_AND_DESIGN_TOOLS_v1.md`; every loop here still passes that doc's adoption
gates (founder ratifies → po battery + Friction pre-work → white-hat reflection test) before any
implementation. Founder directive (verbatim, 2026-08-01): the meeting/community/events apps "are
all worth adding - and researching for what they are doing to drive growth that we believe would
be world class in terms of helping us grow fast."

**What this adds over the existing growth doc.** That doc encodes OneLive's four native loops
(plan-share, artifact, supply-side, seeding) and the timing rules (fire at peak delight; reward
with status/features, never cash; peak-end memory card). This survey studies **13 real
platforms** in depth and surfaces **five loops not yet in our canon** — event-schema SEO,
follow-a-venue + waitlist demand signal, the coverage/gap map, the credible-data content engine,
and anti-vanity positioning-as-growth — plus an explicit **trust-invariant conflict table** that
marks the sleazy mechanics as non-starters. §5 reconciles the two docs so nothing is duplicated.

**The decisive difference from every platform below.** OneLive keeps the supply-side / owned-page
loop that powers most event platforms — **but runs it the trust-first way.** An org, venue, or
artist **owns its OneLive page** and publishes its *own* events through the **Owned Agent** — the
dead-simple "easy button" (stupid-simple: **≤3 clicks, no reading, no multi-field entry, zero
friction**) that broadcasts their content **1:many to social AND feeds OneLive as a clean,
first-party ingestion source at the same time.** This is *not* the "anyone types unverified hype"
version of the loop: **a venue/artist/org posting its own event is the highest-authority
first-party signal in our model** (`worker/authority.py`), so it enters the gate as *authoritative*,
not as noise. So we get the dominant growth loop **and** the trust asset — because the publisher is
the authority, the AI is only their easy button, and the gate still holds. It is in fact a **triple
loop** — supply + 1:many distribution + our cleanest ingestion feed — that no pure event platform
can run. The synthesis below optimizes for *fast growth that compounds that trust asset.*

**Method / caveats.** 2024–2026 web sources, 2–3 searches per platform. Third-party "business
model" write-ups reporting internal metrics that could not be independently confirmed are marked
**(unverified)** — directional, not citable fact.

---

## Loop-type legend

| Type | What it means |
|---|---|
| **Invite / viral** | Existing users pull in new users as a side-effect of core use (RSVP, share link, invite) |
| **Content / SEO** | Pages the platform generates rank in Google and pull in organic search traffic |
| **Supply loop (host-side)** | Making hosts/organizers successful causes them to bring *their own* audience, who become users |
| **Network effect** | Product gets more valuable as density rises in a place/interest, which itself attracts more people |
| **Incentive / referral** | Explicit reward (cash, credit, status) for bringing others |
| **Partnership / channel** | Deals with venues, promoters, cities, or platforms that inject supply or distribution |

---

# Part 1 — Event-first platforms

## Luma (lu.ma)
**What it is:** A clean, fast event-page + RSVP + ticketing tool that became the default for tech
meetups, and increasingly a *discovery* surface (browse by city/category, follow calendars).
**Primary growth loops:**
- **Host supply loop (primary).** Luma makes it trivial to spin up a beautiful page and manage a
  community; the host brings their existing audience, who sign up *on Luma* and become the next
  hosts. Reported 5× user growth 2023→2024, ~2M monthly signups, ~250k active hosts **(unverified).**
- **Content/SEO.** Public event pages are indexed by Google, so people searching an event/topic
  land on Luma directly.
- **Network effect via follow/subscribe.** Users *follow calendars* and *subscribe to a city or
  category*, so each new host and event thickens the local graph and feeds recommendations.
**Most replicable for us:** the **follow-a-calendar / subscribe-to-a-city-or-category** primitive
— a low-friction, non-spammy retention+discovery loop that fits a discovery app perfectly.
**Riskiest / least applicable:** Luma's engine is **host-created supply**; ours is *verified/
extracted* data, so we can't copy "anyone publishes a page" without colliding with "AI never
publishes."

## Partiful
**What it is:** A Gen-Z, playful party-invite app — build an event page, blast the invite by
text; guests RSVP with **no app download and no account.**
**Primary growth loops:**
- **Invite/viral (textbook).** Every event is an outbound invite to the host's phone contacts;
  RSVP requires nothing, so friends convert with near-zero friction and then host their own.
  ~500k MAU (+~400% YoY), 5M new users H1 2025; Google Play Best App 2024 **(press figures).**
- **Zero-friction guest onboarding** is the multiplier — no install wall means the viral
  coefficient isn't taxed.
**Most replicable for us:** **frictionless share → view without a signup wall.** Anyone should be
able to open a shared OneLive event/plan link, see it fully, and act, before making an account.
**Riskiest:** the **contact-book text blast** is exactly the mechanic that becomes spam if
automated — a **non-starter** unless it's a user manually sharing a specific event (Part 3, #2/#5).

## Posh (posh.vip)
**What it is:** A nightlife/social event ticketing + discovery app (find events near you, see the
"vibe" and who's going, buy in seconds).
**Primary growth loops:**
- **Incentive/referral — "Posh Kickback."** Attendees earn commission for **selling tickets to
  friends** ($250k+ collectively earned, unverified). Every attendee becomes a paid micro-promoter.
- **Host affiliate program** (organizers earn for referring other organizers — supply-side referral).
- **Discovery/ML loop.** A 2024 "Discovery" rollout used social-graph + attendance history:
  reported +25% organic ticket discovery, +14% day-of conversion **(unverified).**
- **Partnerships** with festival circuits / nightlife collectives for exclusive inventory.
**Most replicable for us:** **"who's going / the vibe" social proof on the card** — a
discovery-native signal distinct from paid promotion (and only if the signal is *real*).
**Riskiest:** **pay-attendees-to-sell-tickets** rewards selling volume and imports promoter hype
— grafting cash-for-referrals onto a *trust* brand risks the exact distortions we exist to avoid.

## Peatix
**What it is:** A global (Asia-strong) event ticketing + discovery platform for independent
organizers building communities through recurring events; **no attendee fees.**
**Primary growth loops:**
- **Host supply loop + community repeat-attendance.** Attendees of one event are the audience for
  the next. 850k+ lifetime events, 27 countries; $7.3M revenue 2024 (from $5.1M) **(third-party).**
- **No attendee fees** as an acquisition/retention lever (removes checkout friction).
**Most replicable for us:** **"attendees of one event are the best audience for the next"** — for
us, *follow this venue/series and we'll surface the next verified one.*
**Riskiest:** an undifferentiated ticketing tool; slow organizer accretion, not the fast engine
the founder wants.

## Eventbrite
**What it is:** The largest general-purpose event ticketing + discovery marketplace.
**Primary growth loops:**
- **Content/SEO at massive scale (its signature).** Pioneered Event structured-data markup
  (2015), partners in Google Events, very high domain authority — its event pages routinely rank
  top of Google for an event name, pulling organic buyers to *any* organizer's event.
- **Two-sided marketplace network effect:** organizers bring attendees; the attendee base
  attracts organizers.
**Most replicable for us:** **structured-data / Event schema so our verified pages win Google**
for "[event] Austin," "[venue] tonight," "things to do in [neighborhood] tonight." The
highest-leverage, most trust-compatible loop in the whole survey.
**Riskiest:** Eventbrite's paid "boost" / homepage placement is essentially **pay-to-rank** — a
hard non-starter for us.

## Dice (dice.fm)
**What it is:** A fan-first live-music ticketing app built to kill scalping — mobile tickets,
curation for independent music-goers.
**Primary growth loops:**
- **Fan-fairness as brand/word-of-mouth.** No markup resale; a **Waitlist** returns sold-out
  tickets to fans at **face value.** The anti-scalping ethic is itself the acquisition story.
- **Waitlist as a demand signal** that also drives supply (tells promoters how many fans want a
  show → they add dates/allocation → more inventory → more fans).
- **Curation/recommendation** for a defined taste community.
**Most replicable for us:** **waitlist-as-demand-signal**, translated to discovery — let users tap
"I want to go / notify me," aggregate that interest *honestly*, and surface it to venues.
**Riskiest:** Dice's engine is *transactions* (ticket sales); we're intro/discovery-first (Stripe
deferred to Phase 3), so the resale machinery isn't ours to copy yet.

## Meetup
**What it is:** The original interest-based, in-person group platform — organizers create
recurring groups; the platform routes nearby matching people in.
**Primary growth loops:**
- **Interest-graph network effect (its defining loop).** A new group in a big city can pick up
  its first ~50 members with no outside marketing because Meetup auto-routes nearby matching
  users. 300k+ groups, 10k+ cities, 100k+ events/week.
- **Free-organizer plan (2024 "Meetup Starter") + AI recommendations** re-accelerated new
  registrations (+20% YoY reported) post-acquisition.
**Most replicable for us:** the **"we bring you the first 50" promise** — the platform doing
audience-matching *for* the supply side. For us: a venue's first verified listing automatically
reaches the right nearby, interested locals via our interest+geo graph.
**Riskiest:** Meetup's supply is **organizer-declared, unverified by design** — the network effect
is the lesson, not the data model.

---

# Part 2 — Community / network-first platforms

## Nextdoor
**What it is:** The verified-neighborhood social network — you must prove you live at an address.
**Primary growth loops:**
- **Verified-invite viral loop (best-in-class for local).** Onboarding unlocks USPS-verified
  nearby addresses; users invite neighbors via **postcards** with unique codes, plus address-book
  invites. A neighborhood map shows which houses are members / recently invited / not yet — **social
  proof that also prevents wasted invites.**
- **Address verification as a trust *and* growth primitive** — legitimacy makes the invite feel
  safe and worth accepting.
**Most replicable for us:** the **"your area is X% covered — here's what's missing" map** as an
honest, gap-driven invitation to subscribe or contribute. Fits "honest gaps beat filler" and our
Austin/Central-Texas geo focus exactly.
**Riskiest:** **postcard mass-mail is capital-intensive**, and Nextdoor's aggressive address-book
harvesting drew spam criticism — copy the *social-proof map*, never the mass-mail or contact scrape.

## Mobilize (mobilize.us)
**What it is:** An events + volunteer-recruitment platform for mission-driven orgs — people sign
up to attend or *host* actions.
**Primary growth loops:**
- **Distributed-organizing / volunteer-host supply loop (its signature).** ~1 in 5 signups come
  from volunteer hosts (3,000+ new hosts/month); a "Host Hub" lets supporters start one. Ordinary
  supporters become supply. 5.5M+ supporters, 22M+ actions since 2017.
- **Cross-org network:** a shared pool any partner org can reach.
**Most replicable for us:** the **"engaged users → local scouts"** ladder — a structured path from
*attendee → trusted local contributor* who flags/corroborates events **feeding the gate, never
bypassing it.**
**Riskiest:** the shared-supporter network relies on **orgs sharing contact lists** — clashes with
our privacy posture (TDPSA/TRAIGA context in our own deep-review docs). Don't import list-sharing.

## Circle (circle.so)
**What it is:** An all-in-one paid-community platform for creators — the "owned" alternative to
Facebook Groups/Slack.
**Primary growth loops:**
- **Creator-brings-audience supply loop + paid-access intent filter.** Charging for entry raises
  intent/commitment/engagement → better retention and word-of-mouth. $21M ARR May 2024 (+75% YoY),
  18,000+ active communities.
- **Content-marketing loop:** Circle publishes benchmark reports that rank and pull in prospects.
**Most replicable for us:** the **credible-data-report content engine** — OneLive is uniquely
positioned to publish honest "State of Austin live events" data (real verified numbers, not hype),
earning links, press, and SEO. A trust-native content loop.
**Riskiest:** a **walled paid community** is philosophically opposite to open, honest discovery for
the core surface.

## Mighty Networks
**What it is:** A community platform whose thesis is "**People Magic**" — value comes from members
meeting *each other*, aided by AI-made introductions.
**Primary growth loops:**
- **Member-to-member connection loop.** AI surfaces **double-opt-in** introductions and relevant
  programming from members' *stated goals*; relationships (not content) drive stickiness/referral.
**Most replicable for us:** **goal/intent-based matching with double opt-in** — match people to
*events* (and optionally to each other around a shared plan) from stated intent, always opt-in.
**Riskiest:** heavy AI people-matching brushes our "AI never publishes / never exposes unverified"
line if it ever surfaced people or claims without consent — keep any matching strictly opt-in and
**out of the verified-data path.**

## Geneva
**What it is:** A group-chat/community app (chat, forum, audio/video, broadcast rooms) for
real-world groups and clubs; deliberately **no likes, no follower counts.** Acquired by Bumble.
**Primary growth loops:**
- **Invite-gated group formation ("Gates" and "House Keys").** Creators vet members via
  questionnaires; trusted members get keys to invite/moderate — growth via **curated invitation**,
  not open virality.
- **"No vanity metrics"** as a Gen-Z word-of-mouth differentiator.
**Most replicable for us:** the **anti-vanity-metric stance** (no like-counts, no pay-to-boost
signals) aligns cleanly with "no pay-to-rank" — confirming our design instinct is *also* a
growth-positioning asset.
**Riskiest:** private group chat, not public discovery; invite-gating limits reach — not a
fast-growth mechanic for an open discovery app.

## BAND (band.us)
**What it is:** A Naver-built group-communication app (shared calendar, albums, polls, to-dos) for
closed groups — teams, classes, faith groups, families.
**Primary growth loops:**
- **Whole-group migration via shared URL.** One **join URL** shared over SMS/messenger moves the
  *entire existing offline group* in at once — group-level (not individual) acquisition.
- **Utility lock-in:** shared calendar + polls make the group depend on it.
**Most replicable for us:** **one shareable join/plan URL that moves a whole friend-group at once**
— a shared "Austin this weekend" plan link an organizer drops into their existing chat.
**Riskiest:** a closed-group utility with weak *public discovery*; growth doesn't compound across
strangers, so it won't drive city-level density.

## Skool
**What it is:** A gamified community-course platform (Alex Hormozi-backed) — communities with
built-in courses, discussion, and a points/leaderboard game layer.
**Primary growth loops:**
- **Gamified viral contest ("The Skool Games") + per-community referral virality.** A transparent,
  time-boxed leaderboard drives creators to compete and recruit; referral mechanics compound inside
  each community. Loop type: incentive/referral + creator-supply.
**Most replicable for us:** a **time-boxed, transparent "leaderboard of honest contribution"** —
recognizing users who corroborate/flag verified events well.
**Riskiest:** contests that reward **raw volume** invite the exact hype/gaming our gate exists to
stop — a leaderboard must reward **verified quality, never referral counts**, or it's a non-starter.

---

# Part 3 — Synthesis: world-class growth loops for OneLive

The ranking optimizes for *fast growth that compounds our trust asset instead of eroding it.*
"New?" marks loops not in `ONE_LIVE_GROWTH_LOOPS_AND_DESIGN_TOOLS_v1.md`; the rest map to an
existing native loop (see §5).

### The supply engine, first: owned pages + the Owned Agent (Luma-trivial)

Before the ranked list — the single most important loop is the **owned-page + Owned Agent supply
engine**, because it is the one loop that is *also* our ingestion. **The UX bar is Luma-trivial.**
Luma grew by making it effortless for a host to spin up a page and reach their audience; the Owned
Agent must clear that same bar **and go lower — stupid-simple: ≤3 clicks, no reading, no
multi-field entry, zero friction** (founder directive 2026-08-01, "it has to be the epitome of
simple and easy… no friction," "similar to Luma we need to make the AI agent trivial"). What the
org gets: a one-tap way to broadcast an event **1:many** to its socials. What OneLive gets: the same
tap delivers a clean, **first-party authoritative** event straight into the gate. The org is the
authority; the AI is only the easy button; the gate still holds. Design + build spec lives in the
**Owned Agent** research (PR #48, unmerged) — **this triviality bar (Luma-trivial / ≤3 clicks / no
friction) must be adopted as a hard acceptance criterion there when that spec is next touched.** The
ranked table below covers the *additional* loops that compound on top of this engine.

| # | Loop | Type | New? | Why it fits OneLive | Honest tradeoff / risk | Build |
|---|---|---|---|---|---|---|
| 1 | **Event-schema SEO: our verified pages win Google for "[event/venue] tonight in [neighborhood]"** | Content/SEO | **NEW** | Our data is *more accurate* than competitors'; structured data + honest canonical pages should out-rank hype. Compounding, cheap, on-brand (Eventbrite proves the ceiling). | Slow to compound (months); needs disciplined canonical URLs, schema, dedupe; Google-algo dependence. | Medium |
| 2 | **Frictionless shared-link viewing (no signup wall to see an event/plan)** | Invite/viral | partial (extends plan-share) | Partiful's core unlock; trust is *shown*, not gated. Multiplies every other loop. | Protect write/claim behind auth; manage anonymous-abuse surface. | Low–Med |
| 3 | **Follow-a-venue / subscribe-to-a-neighborhood-or-vibe + "notify me / I want to go"** | Network effect + demand signal | **NEW** | Luma follow × Dice waitlist, both trust-native — retention *and* an honest public demand signal to show venues (supply pull). | Notification fatigue; demand counts must be *real* (no inflation) to stay trustworthy. | Medium |
| 4 | **Coverage/gap map: "Austin is X% covered — here's what's missing tonight"** | Invite/viral + content | **NEW** | Nextdoor's social-proof map fused with "honest gaps beat filler" — turns honesty about gaps into a call to subscribe/tip/share. | Gaps can read as "incomplete" to first-timers; needs confident framing. | Medium |
| 5 | **Shared group "plan" URL — move a whole friend-group in one link** | Invite/viral | maps to plan-share (canon) | BAND migration × Partiful link — one link lands a whole group on verified data. | Needs a genuinely useful "plan/night-out" object; not core to v1 feed. | Medium |
| 6 | **Trusted local scout ladder: engaged users → corroborate/flag events feeding the gate (never bypassing it)** | Supply loop | extends supply-side (canon) | Mobilize's host ladder, adapted so contributions enter the gate *as evidence*, not as publishes — grows verified density without violating "AI never publishes." | Moderation + Sybil load; must be genuinely gate-custodied, not a backdoor. | Med–High |
| 7 | **Credible-data content engine: publish honest "State of Austin live events" reports** | Content/SEO + PR | **NEW** | Circle's report loop, but with *real verified data nobody else has* — earns links, press, authority. | Needs enough data volume to be non-trivial; ongoing editorial effort. | Low–Med |
| 8 | **Anti-vanity, no-pay-to-rank positioning as an explicit growth message** | Positioning/word-of-mouth | **NEW** | Geneva/Dice prove "we don't do the sleazy thing" is itself acquisition — our invariants become the marketing. | Only converts if the product visibly delivers; not a mechanical loop alone. | Low |

**Recommended sequencing.** Start with **#1 (SEO/schema)** and **#2 (no-wall sharing)** — both
foundational, compounding, and reinforcing every other loop. Layer **#3** and **#4** as the feed
matures. Treat **#6** as a later, carefully-gated supply loop once moderation tooling is solid.
(#5 is our already-canon plan-share engine; #8 is positioning we already hold — make it explicit.)

---

# Part 4 — Trust-invariant conflicts (NON-STARTERS and cautions)

Invariants are the charter's, verbatim (CLAUDE.md Prime Directive 1 + canon): *AI never publishes ·
orchestrator cannot import the promote path · **no pay-to-rank surface, ever** · disputed
shown-never-hidden · RLS fail-closed*; plus *honest gaps beat filler* and *ToS-respecting, no fake
accounts* (harvest spec / hiQ). Any mechanic that requires spammy invites, fake activity, or
pay-to-rank is a **NON-STARTER**, not a recommendation.

| Mechanic (and who does it) | Verdict | Why |
|---|---|---|
| **Paid event promotion / "boost" / homepage placement** (Eventbrite) | **NON-STARTER** | Direct "no pay-to-rank surface, ever" violation. Ranking reflects verification + relevance, never spend. |
| **Contact-book mass text/email blasts; auto-harvested address books** (Partiful blast, Nextdoor, BAND) | **NON-STARTER as automated growth** | Violates ToS-respecting / no-spam growth. Allowed *only* as a user manually sharing one specific event/plan link they chose to send. |
| **Physical postcard mass-mailing to unverified addresses** (Nextdoor) | **Caution / defer** | Not a trust violation, but capital-heavy and slow — copy the *coverage-map social proof*, not the mailing. |
| **Pay-attendees-cash-to-sell-tickets** (Posh Kickback) | **Caution → likely NON-STARTER for core** | Rewards selling volume/hype, imports promoter incentives that distort trust. Any referral rewards *honest contribution*, never sales volume, and never ranking. |
| **Fake activity / seeded "who's going" / inflated demand counts** (industry dark pattern) | **NON-STARTER** | Fabricated social proof = fake-data territory; collides with "AI never publishes [unverified]" and "disputed shown-never-hidden." Crowd/interest counts must be *real* or not shown. |
| **AI auto-surfacing people or unverified event claims without opt-in** (Mighty/Circle taken too far) | **NON-STARTER in the data path** | "AI never publishes" + privacy. Matching is strictly opt-in and lives *outside* the verified-event pipeline. |
| **Cross-org contact-list sharing** (Mobilize) | **NON-STARTER** | Conflicts with the privacy posture (TDPSA/TRAIGA). |
| **Walled paid-access gating of the core discovery feed** (Circle/Skool) | **Off-mission for core** | Our value is open honest discovery; paid gating belongs (if anywhere) to premium tooling, never the verified feed. |
| **Volume-rewarding referral leaderboards** (Skool Games) | **Conditional** | A "leaderboard of honest contribution" is fine *only* if it rewards verified quality; rewarding raw referral/invite counts is a non-starter. |

**The through-line:** almost every *fast* loop in this survey has a clean version and a sleazy
version. The sleazy version (buy rank, blast contacts, fake the crowd) is precisely what OneLive
exists to *not* be — so the honest version is both our constraint and our differentiator.

---

# Part 5 — Reconciliation with the existing growth canon

`ONE_LIVE_GROWTH_LOOPS_AND_DESIGN_TOOLS_v1.md` already holds four native loops and the timing
rules. This survey does not replace them — it maps onto and extends them:

| Existing native loop (canon) | This survey's corresponding / extending loop |
|---|---|
| **Plan-share loop** (Partiful analog, "the growth engine") | #2 no-wall viewing + #5 whole-group plan URL — sharpen it with Partiful's *no-account-to-view* and BAND's *one-link-moves-the-group* |
| **Artifact loop** (Wordle share card, §6.D5) | reinforced by #8 anti-vanity positioning + the peak-end memory card already in canon |
| **Supply-side loop** (claimed venues promote their pages) | **The Owned Agent** — owned pages + a Luma-trivial ≤3-click broadcast that *is* first-party authoritative ingestion (the primary supply engine, see the §3 callout + PR #48); plus #6 trusted-scout ladder (Mobilize) as the gate-custodied community-contributor extension |
| **Seeding loop** (Tastemaker organic / ambassador paid) | Skool's transparent contribution leaderboard — status-not-cash, consistent with the canon's "reward with status, not cash" rule |
| *(not in canon)* | **#1 SEO/event-schema, #3 follow+waitlist demand signal, #4 coverage-gap map, #7 credible-data report engine** — the four genuinely new loops to evaluate |

**Timing rules carry over unchanged:** fire share prompts at peak delight (never signup); reward
with status/feature unlocks, not cash; design the peak-end (morning-after "your night" card). All
four new loops pass the white-hat reflection test as written.

**Adoption gates carry over unchanged** (from the existing doc): founder ratifies (PROPOSAL ≠
license to build) → each loop runs the full po battery + Friction attack pre-work → analytics
(PostHog, founder-minted at Step 9) instrument the activation/referral moments before tuning.

**Ingestion vs. growth (a note on "add them").** The event-first platforms (Luma, Posh, Peatix,
Dice) are *also* candidate ingestion sources and warrant an ingestion-posture line in
`ONE_LIVE_PLATFORM_API_INVENTORY_2026-07.md` (most expose only host-opted-in or paid APIs — assess
per platform); the community-first apps (Nextdoor, Circle, Mighty, Geneva, BAND, Skool, Mobilize)
are **growth references, not ingestion sources.** That inventory pass is a separate follow-up.

---

## Sources

- Luma: [Social Discovery Insights — user growth (2024)](https://www.socialdiscoveryinsights.com/2024/05/16/luma-event-planning-app-sees-impressive-user-growth/) · [Luma Help — Discovering Events](https://help.luma.com/p/discovering-events) · [Luma Help — Promote Your Event](https://help.luma.com/p/promote-your-event)
- Partiful: [CNBC (2025)](https://www.cnbc.com/2025/04/19/meet-partiful-the-gen-z-party-planning-staple-thats-taking-on-apple.html) · [TechCrunch — Best App of 2024](https://techcrunch.com/2024/11/18/partiful-is-googles-best-app-of-2024) · [Wikipedia](https://en.wikipedia.org/wiki/Partiful)
- Posh: [Digital Music News — $22M raise](https://www.digitalmusicnews.com/2024/07/24/posh-raises-22-million-with-small-events-platform-model/) · [Posh Support — Kickback](https://support.posh.vip/en/articles/10723700-creating-a-public-kickback-affiliate-offer) · [Posh University — Affiliate](https://posh.vip/university/post/posh-affiliate-program)
- Eventbrite: [Google Search Central — Eventbrite case study](https://developers.google.com/search/case-studies/eventbrite-case-study) · [Eventbrite Blog — SEO for events](https://www.eventbrite.com/blog/how-to-rank-on-google-seo-for-events-ds0c/)
- Dice: [Wikipedia](https://en.wikipedia.org/wiki/Dice_(ticketing_company)) · [DICE Help — wait list](https://dicefm.zendesk.com/hc/en-gb/articles/19958073128849-The-wait-list-explained) · [Trapital — fan-focused ticketing](https://www.trapital.com/episodes/how-dice-makes-ticketing-more-fan-focused)
- Peatix: [GetLatka](https://getlatka.com/companies/peatix) · [About Peatix](https://about.peatix.com/en/aboutus)
- Meetup: [2025 progress report](https://www.meetup.com/blog/2025-meetup-progress-report/) · [BusinessWire — redesign (2025)](https://www.businesswire.com/news/home/20250930663024/en/Meetup-Unveils-Fresh-New-Design-as-Gen-Z-and-Millennials-Crave-More-In-Person-Interactions) · [Vizologi — business model](https://vizologi.com/business-strategy-canvas/meetup-business-model-canvas/)
- Nextdoor: [CloudSponge — viral growth](https://www.cloudsponge.com/customers/nextdoor/) · [CloudSponge — invitation teardown](https://www.cloudsponge.com/blog/nextdoor-invitation-experience-teardown/) · [Nextdoor Help — grow your neighborhood](https://help.nextdoor.com/s/article/Growing-the-neighborhood?language=en_US)
- Mobilize: [NGP VAN — volunteer-host features (2025)](https://www.ngpvan.com/resources/newsroom/ngp-van-launches-new-mobilize-features-to-power-the-next-era-of-volunteer-led-organizing/) · [Mobilize — platform](https://join.mobilize.us/platform/) · [Wikipedia](https://en.wikipedia.org/wiki/Mobilize_(company))
- Circle: [Sacra — revenue & funding](https://sacra.com/c/circle-so/) · [Circle — 2024 Creator Community Benchmark](https://circle.so/2024-creator-community-report)
- Mighty Networks: [People Magic](https://www.mightynetworks.com/resources/people-magic) · [People Magic GPT docs](https://docs.mightynetworks.com/for-hosts/setting-up-your-network/what-is-the-people-magic-gpt)
- Geneva: [Geneva — About](https://www.geneva.com/about) · [Semiconductor Things — Geneva & Gen-Z community](https://www.semiconductorthings.com/p/geneva-is-the-future-of-community)
- BAND: [Wikipedia](https://en.wikipedia.org/wiki/Band_(software)) · [SmartSocial — BAND guide](https://www.smartsocial.com/post/band-app)
- Skool: [Medium — Skool vs. the rest](https://weare0ne.medium.com/future-of-community-course-platforms-skool-vs-rest-of-the-world-1162a2a4b38e) · [Black Swan Media — Skool review](https://blackswanmedia.co/skool-review/)
