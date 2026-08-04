# 1LIVE — The Owned Agent v1 (an AI agent artists, venues, and event organizers own and control)

**Compiled 2026-07-22 · Status: PROPOSAL — research response to the founder's 2026-07-22 question ("How might we create an AI agent that is 'owned' by and 'works for' artists and events and venues?"). Part II added same day from the founder's follow-up (agent-facing representation, the adoption-gap belief, essential needs, open + private). Nothing here is license to build; every build item is gated below. Builds directly on RATIFIED canon: `ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md` (first-party fast lane, watcher records, scoped authority + dispute override).**

Greppable summary: the founder's "owned agent" decomposes into three layers —
(1) the PIPE: verified first-party channels feeding the existing pipeline
(already ratified canon, no new trust physics); (2) the GIFT: free
amplification features (widget with JSON-LD, syndication, digest, health
alerts) that make businesses WANT to connect; (3) the SKIN: an agent-shaped
onboarding and control experience ("paste your website, I'll find the rest").
Precedents: Bandsintown for Artists (free tools → 510k+ artists feeding the
platform), Google Business Profile (claim + verify menu), vertical SaaS
(own a workflow, the data is exhaust). Trust invariants unchanged: the owned
agent is a SOURCE and an OWNER CHANNEL, never a publisher — everything still
enters at extraction → candidate → gate → promote. Phases A/B/C gated on
Steps 6–7. One consolidated founder question list at the end.

---

## 1. The founder's ask (verbatim anchors, 2026-07-22)

1. "How might we create an AI agent that is 'owned' by and 'works for' artists and events and venues?"
2. "We empower cultural component data to auto flow into our system. And our system ensures they are accurately represented."
3. "Offer the agent to any business at no cost and they can choose what it performs from a discrete set of functions that help them amplify their event(s) and activities."
4. "We build and giveaway an agent that also feeds our site with the data it needs."
5. "They control the content and we display it and help them promote what's going on."
6. "The execution would need to be super super simple and elegant."

## 2. The honest read: this is three products in one sentence, and we already ratified the hard one

The phrase "an agent they own" bundles three separable layers. Separating
them is what makes execution "super super simple" — because two of the three
are cheap, and the expensive-sounding one is already ratified canon.

**Layer 1 — the PIPE (data flowing in).** A venue that connects its calendar
feed, website pages, and social handles is, in our existing architecture, a
**verified first-party channel** attached to a **watcher record**. That is
not new design — it is the RATIFIED sensor architecture (2026-07-14 founder
decisions: "if it comes from the venue/artist/club/group/entity, and we
validate domain and other aspects, we should give that a high value of
truth"; validated first-party enters at `confirmed`). The owned agent is the
consumer-friendly FACE of that ratified machinery. No new trust physics is
needed, and none is proposed.

**Layer 2 — the GIFT (why they bother).** Nobody adopts a tool because it
feeds *our* site. They adopt it because it solves *their* problem: publish
the calendar once, appear everywhere, correctly. The giveaway features
(section 5) are chosen so that every one of them is genuinely valuable to
the business on its own AND produces or improves the data we need as a side
effect. This is the vertical-SaaS lesson (OpenTable, Toast, Mindbody): own
a workflow the business already needs; the data is exhaust, not the pitch.

**Layer 3 — the SKIN (the agent experience).** "Agent" is the interface and
the promise, not a fleet of always-on LLMs. The ratified sensor architecture
already settled this: accountability lives in cheap watcher RECORDS; "AI
engages per-change, never per-entity-idle." The owner-facing experience —
"paste your website URL; I found your calendar, 14 upcoming events, and your
Instagram; here's exactly how you'll appear; which of these five jobs do you
want me to do?" — is an onboarding flow plus a per-entity control panel,
powered by the extraction pipeline we already run. The agent framing is real
(it acts on their behalf, on their schedule, under their control) but its
marginal cost per business must round to zero, or free-forever breaks.

## 3. What the research says (precedents, with links)

**Bandsintown for Artists is the closest proven playbook.** Free dashboard
for artists; add or update a show once and it syncs everywhere the artist's
widget and integrations reach (30+ integrations, Linktree, band websites);
free insights on fans and ticket progression. Result: [510,000+ registered
artists](https://themusicuniverse.com/bandsintown-unveils-bandsintown-artists/)
voluntarily feeding the consumer platform's supply, because the free tools
solve the artist's own problem — their stat: [~40% of concert tickets go
unsold because fans don't know their favorite artist is in
town](https://www.billboard.com/music/music-news/bandsintown-launches-analytics-tools-for-artists-exclusive-6458292/).
That is 1Live's consumer thesis stated from the supply side. What
Bandsintown does NOT do is verification-grade trust (its data is
artist-asserted and unaudited) or local non-music culture — both are our
differentiation, not gaps we must close to copy the mechanic.
([Integrations marketplace](https://www.artist.bandsintown.com/integrations),
[widget syncing](https://artists.bandsintown.com/support/blog/new-integration-sync-your-bandsintown-events-with-your-linktree),
[Bandzoogle example](https://bandzoogle.com/blog/new-easily-integrate-your-bandsintown-tour-dates-into-your-website))

**Google Business Profile is the claim-and-verify pattern to copy.** A menu
of verification methods matched to what the business can easily prove:
[postcard, phone, email, video, and instant verification when the claimant
already controls the domain in Search
Console](https://support.google.com/business/answer/7107242?hl=en). The
lesson: verification is a MENU, not a single method, and domain control is
the cheapest strong signal.
([overview of methods](https://www.brightlocal.com/learn/google-business-profile/getting-started/verifying-google-business-profile/))

**Structured event data is a real gift we can give.** Schema.org adoption is
mainstream ([~31% of 10B pages carry some schema.org
markup](https://gatilab.com/event-schema-markup/)) and venues with proper
Event JSON-LD get surfaced in Google's "Things to do" and Maps event
listings, with [materially higher click-through reported for marked-up
events](https://venuequoter.com/blog/the-proven-way-to-boost-event-visibility-for-venues).
Most small venues cannot produce correct JSON-LD. Our widget can emit it for
them (section 5, F3) — a genuinely valuable SEO gift that costs us nothing
and, as a side effect, makes the open web's event data (including ours to
re-read) cleaner. ([spec guide](https://schema.dev/blog/your-complete-guide-to-getting-started-with-event-schema-mark-up/))

**Calendar plumbing is commodity.** ICS/iCal feeds are exported by
WordPress, Squarespace, Wix, Google Calendar, Eventbrite, etc., and
[aggregator plugins routinely ingest them](https://wordpress.org/plugins/wp-event-aggregator/).
Phase A ingestion is mostly deterministic parsing, not LLM extraction —
a direct cost-discipline win (cheapest-capable method first).

**Meta (Instagram/Facebook) APIs are the trap to avoid in v1.** Official
access requires the business to have a Business/Creator account connected to
a Facebook Page, per-account authorization, [app review measured in weeks
with frequent rejection, and ~200 calls/hour rate
limits](https://elfsight.com/blog/instagram-graph-api-complete-developer-guide-for-2026/).
Reading a venue's public IG via our existing extraction path (as today)
stays the v1 method; authorized Graph API access is a Phase C upgrade for
businesses that complete Meta's own hoops.
([2026 API state](https://storrito.com/resources/instagram-api-2026/),
[platform overview](https://developers.facebook.com/docs/instagram-platform/overview/))

**The agent-protocol wave is real but early.** MCP is now the de facto
tool-access standard ([10,000+ public servers, protocol stack maturing
through 2026](https://www.digitalapplied.com/blog/ai-agent-protocol-ecosystem-map-2026-mcp-a2a-acp-ucp)).
The strategic implication for us is Phase C, not Phase A: once we hold
verified, gated event truth for a metro, exposing it as an MCP server makes
1Live the source consumer agents (Claude, ChatGPT, Gemini surfaces) query
— "be where the agents look" is the 2027 version of "be where Google looks."
([standards overview](https://amdatalakehouse.substack.com/p/the-state-of-agentic-ai-standards))

## 4. Trust physics — what changes (nothing) and what must be said out loud

1. **The owned agent is a source and an owner channel, never a publisher.**
   Everything it brings in enters at Sources → Raw Fetch → Extract →
   Candidate → Gate → Promote, identical to every other source. The ratified
   first-party fast lane (validated first-party → `confirmed`) is a GATE
   rule, not a bypass — the gate still runs, provenance is still stamped,
   dispute override still wins.
2. **Owner control cuts both ways and the dispute rule is the boundary.**
   "They control the content" is true for their claims about their own
   events (title, time, description, images, which pages we watch). It is
   NOT true for the trust frame around those claims: if credible
   contradicting evidence appears (venue says 8pm, ticketing says cancelled),
   the event shows as `disputed` — shown, never hidden, and not
   owner-suppressible. This must be in the partner-facing terms from day
   one, in plain language, or the first dispute becomes a betrayal story.
3. **No connect-to-rank.** The no-pay-to-rank invariant has a free-tier
   shadow: connecting the agent must never buy ranking. Connected entities
   will legitimately LOOK better (fresher data, richer fields, `confirmed`
   state) because their data is better — that is accuracy, not promotion.
   The line to hold: connection affects data quality attributes the ranking
   already reads; it must never be a direct ranking feature. Stated here so
   it can be ratified as an explicit corollary rather than drifting.
4. **Impersonation is the new attack surface** (the price of the fast lane).
   A successful fake claim turns first-party trust into a poisoning vector.
   Defenses, all existing canon or standard practice: verification menu with
   domain control as the strong path (section 5, F0), scoped authority +
   dispute override (ratified), disputed-never-hidden, and destructive
   changes (cancellation, venue change) from a freshly-claimed account get a
   corroboration hold (open question Q3). The golden set must grow
   impersonation and poisoned-first-party cases when this ships.

## 5. The discrete function set (the founder's "they choose what it performs")

Each function is independently toggleable by the owner, valuable to them on
its own, and feeds or improves our data as a side effect. F0 is mandatory
(it is identity); everything else is opt-in checkboxes.

- **F0 · Claim & verify** — claim the entity (pre-seeded from our existing
  source catalog — the "confirm your listing" magic-link idea already in the
  po-harvest backlog); verify via a menu: domain-email or DNS/meta-tag proof
  (strong, instant), phone/manual fallback (weaker, slower). Output: a
  verified watcher record with an authorized in-product account (ratified =
  `confirmed` channel).
- **F1 · Calendar sync (the spine).** They point us at what they already
  maintain — ICS/Google Calendar feed, events page URL, or (last resort)
  typing events into our simple form. We ingest on their schedule, show a
  live preview of exactly how each event appears on /tonight, and every
  change flows automatically. Deterministic parsing where possible; LLM
  extraction only for unstructured pages (existing pipeline).
- **F2 · Page & social watch.** They select which of their pages/handles we
  watch (website pages, public IG/FB). Our existing watchers fetch and
  extract; being owner-selected upgrades the source's provenance and tells
  us which surface the business considers authoritative.
- **F3 · The give-back widget.** One embed line gives their site a clean,
  fast event list rendered from THEIR data as it exists in our system —
  with correct schema.org Event JSON-LD emitted for them, improving their
  own Google/"Things to do" visibility. This is the Bandsintown-widget
  mechanic plus an SEO gift most small venues cannot build themselves. It
  also makes accuracy self-policing: they see what we see, on their own site.
- **F4 · Accuracy alerts & health digest.** "Your Friday show has no start
  time." "Two sources disagree on your Saturday event." "Your feed went
  silent 9 days ago." Plus a weekly plain-language digest: how they appeared,
  what was viewed. This is the agent "working for them" most visibly, and it
  recruits the owner as a free accuracy sensor for us.
- **F5 · Promotion drafts (Phase C only).** The agent DRAFTS social posts /
  captions / links for their events; the OWNER publishes (their accounts,
  their button, or an explicit per-platform authorization). Note the deliberate
  symmetry with our own physics: their agent never publishes either — it
  prepares, the human owns the send. Blocked on Meta app review realities
  and a founder new-service decision (Q5).

Everything above the line F0–F4 requires zero new external services, zero
new credentials beyond what exists, and no Meta developer account.

## 6. Execution phases (gated; nothing jumps the critical path)

- **Phase A — the pipe + the skin (after Step 7's watcher records land).**
  Claim flow (F0), calendar sync (F1), page/social watch (F2), the
  agent-shaped onboarding ("paste your URL → we discover feeds/pages/handles
  → preview → choose functions → verify"). Rides the watcher-record schema
  already queued P1-gated-on-Step-7 in TODOS; the claim flow is the
  productization of the same PR family. Cheap: discovery is fetch + parse +
  one extraction pass; onboarding is a web flow.
- **Phase B — the gift (fast follow).** Widget with JSON-LD (F3), alerts +
  digest (F4). Digest email needs the ingest-mailbox/outbound-email service
  decision only if we send email (Q4 notes the cheap alternative: in-product
  + the existing weekly founder-digest machinery pattern).
- **Phase C — the outbound agent (separate founder decision).** Promotion
  drafts (F5), authorized Meta Graph access for businesses that complete
  Meta's requirements, MCP server exposing gated event truth to consumer
  agents. Each is its own decision record; Meta and email are new services
  (founder-crucial).

**Why this order:** Phase A is where "feeds our site with the data it needs"
lives — it directly serves the current mission (real candidates flowing for
steps 6–10) and the ratified sensor architecture. Phase B is retention and
the reason word spreads. Phase C is reach, and it is the only phase with
platform risk, so it goes last and behind explicit decisions.

## 7. Why this, not that (alternatives considered)

1. **Keep scraping only; no owned agent.** Cheaper now, and it is the
   current path. But it caps accuracy (we infer what owners could state),
   keeps the relationship adversarial (fetching around them instead of
   working for them), and builds no moat — anyone can scrape; a network of
   verified first-party channels is earned. Rejected as the end state;
   scraping remains the floor and the discovery mechanism.
2. **A real persistent LLM agent per business.** Matches the words of the
   ask, fails the ratified architecture ("cheap watcher RECORDS, not
   persistent LLM agents") and cost discipline — thousands of idle agents at
   $0/business is a margin fire. Rejected; the agent EXPERIENCE is the skin
   over watcher records, LLM spend stays per-change.
3. **Meta-API-first social agent** (lead with "we post to your Instagram").
   The flashiest pitch and the fastest way to strand v1 behind Meta app
   review (weeks, frequent rejection, per-account hoops) and rate limits.
   Deferred to Phase C, opt-in per business.
4. **A plain dashboard/portal, no agent framing.** Functionally almost
   Phase A. But the agent framing is not decoration: "you own an agent that
   works for you" is the pitch a musician retells, it sets up Phase C
   honestly, and the auto-discovery onboarding genuinely IS agentic (it
   does the work; the owner approves). Adopted as skin over the same
   substance — with the discipline that nothing in the framing promises
   autonomy we do not ship.

## 8. Tradeoffs, honestly

1. **Impersonation risk rises with the value of the fast lane** — the whole
   point of claiming is elevated trust, so fake claims become worth
   attempting. Mitigations in section 4.4; residual risk never reaches zero
   and one incident, handled by the dispute mechanics, should be assumed.
2. **Free-forever is a cost commitment.** F0–F4 marginal cost per business
   is near zero by design (deterministic parsing, per-change LLM,
   widget from cached reads), but support/abuse handling is human time that
   scales with adoption. The mitigation is ruthless simplicity (fewer
   functions, self-serve everything), not a paid tier — a paid tier
   anywhere near visibility would read as pay-to-rank-adjacent.
3. **Owner control vs. trust display will collide.** Some owner will demand
   we hide a `disputed` badge on their event. The answer is contractual
   plain language up front (section 4.2) and it will still cost us some
   partners. That cost is the invariant working as intended.
4. **Platform dependence in Phase C.** Meta terms, rate limits, and review
   outcomes are outside our control; any Phase C social feature must degrade
   gracefully to F5-drafts-only (owner copies/pastes) when APIs are denied.
5. **Legal surface grows** (TDPSA/TRAIGA posture per the deep-review §10
   PROPOSAL): consented first-party ingestion is a cleaner posture than
   scraping, but partner terms need drafting (content license to display,
   deletion on unclaim, AI-disclosure if F5 drafts content). One-time legal
   cost, founder-visible before Phase A ships publicly.

## 9. What "super super simple" means concretely (the bar for Phase A)

1. One field: "Paste your website (or Instagram) URL."
2. The agent discovers: ICS feeds, JSON-LD, event pages, social handles —
   and shows a preview: "Here's what I found. Here's how you'll appear."
3. One verification step, instant when they control the domain or the
   listed business email; a fallback path otherwise.
4. Five checkboxes (F1–F4 + notification preference). No settings pages
   beyond that.
5. Total time for a venue with a working website: under five minutes, no
   password creation beyond the auth we already use (Clerk), nothing to
   install, nothing to learn.
Anything the flow cannot auto-discover, it asks for in one consolidated
step — the same one-question-set discipline we hold for the founder.

### 9a. The hard triviality bar (founder directive 2026-08-01 — TIGHTENS §9)

Founder, verbatim: *"this tool needs to be the epitome of simple and easy and
no more than 3 clicks and no reading or entering multiple items. It has to be
stupid simple - no friction!"* and *"similar to Luma we need to make the AI
agent trivial."* This turns the §9 bar into a **hard, quantified Phase-A
acceptance criterion**, tighter than §9's softer numbers where they conflict:

1. **≤3 clicks, end to end**, for the core loop (claim → confirm → broadcast the
   first event). Not "under five minutes" — three taps.
2. **No reading.** No walls of text, no settings to study. The discovered
   preview is *glanceable* — a card that already looks like the finished result
   — never a document the partner must read in order to proceed.
3. **No entering multiple items. One input, maximum** — the URL (website or
   Instagram). Everything else (ICS/JSON-LD/handles, notification defaults, the
   F1–F4 functions) is **auto-discovered or set to a safe default the partner
   can change later**, never a decision they must make up front. The §9 "five
   checkboxes" become **defaults-on with a one-tap 'change these later,'** not
   five decisions on the critical path.
4. **Luma-trivial** is the UX benchmark: spinning up and broadcasting must feel
   as effortless as creating a Luma event page — and *lower*, because the partner
   starts from a URL we already read, not a blank form.

**Acceptance test (mechanical, Phase A):** a venue with a working website
completes claim + first broadcast in **≤3 taps and zero free-text fields beyond
the single URL**, with **no required reading step**. Any flow that needs a fourth
decision-tap or a second typed field fails this bar and must push that decision
to a post-onboarding "refine" surface. The trust physics (§4) and the discrete
function set (§5) are unchanged — this bar governs the *interaction cost*, never
the gate.

## 10. Consolidated founder questions (Q1–Q5; the same-day addendum adds Q6–Q8 in §17 — one combined list, nothing else asked anywhere in this doc)

1. **Ratify the concept?** The three-layer decomposition (pipe = ratified
   sensor canon, gift = F0–F4, skin = agent-framed onboarding) as the
   direction for the owned agent — yes/no/amend. Includes the working name
   question ("your 1Live agent"? partner-facing name can come later).
2. **Sequencing:** agree Phase A gates on Steps 6–7 (golden-set gate, then
   watcher records with real candidate flow) and does NOT preempt the
   current critical path? (Recommended: yes — the claim flow without a live
   /tonight surface gives partners nothing to see.)
3. **Trust edge:** the ratified rule sends validated first-party to
   `confirmed`. Should DESTRUCTIVE owner changes (cancellation, venue/time
   change) from an account claimed less than N days ago carry a short
   corroboration hold before display-state changes, or apply immediately?
   (Recommended: hold for new claims only — bounded blast radius at near-zero
   friction for established partners; tradeoff: a genuinely urgent
   cancellation from a brand-new partner could lag.)
4. **Free-forever as public promise:** commit publicly that the agent is
   free and that neither payment nor connection affects ranking (the
   no-connect-to-rank corollary in section 4.3)? This is a trust asset but
   it constrains future monetization to non-rank surfaces — consistent with
   the existing invariant, stated to be chosen rather than drifted into.
5. **Phase C pre-authorization is NOT requested now.** Flagged only so the
   dependency is visible: outbound social (Meta developer account) and
   outbound email are new services and will come back as separate
   decision records with friction attacks when Phase B proves demand.

---

# Part II — Addendum (2026-07-22, same day): the founder's follow-up, researched

## 12. The follow-up ask (verbatim anchors, 2026-07-22)

1. "The agent should be the venue/artist/events 'agent' to interact with the coming wave of AI agents who will be [doing] work on other people and orgs behalf, including 1Live … We can help them ensure their brand, their content, etc is represented as they choose."
2. "My belief is that — research to verify or dispute or enhance understanding — most small businesses and artists have no real understanding of how to use AI or they think it may cost a lot or they may be charged a setup and ongoing monthly fee by someone to 'manage' the 'AI' capabilities."
3. "We should be able to deliver so much value that we are seen as the 80/20 or even 90/10 of basic needs — need to define (research) basic or essential needs and then build to that standard."
4. "We, as an open platform and not a closed or walled off platform like Facebook … and that activity can stay on device and really emphasize our privacy focus, should also be attractive to consumers."

## 13. The agent-facing layer (B2A): representing the business to other agents

The follow-up names something the v1 sections underweighted: the owned agent
is not only a pipe INTO 1Live — it is the business's REPRESENTATIVE to
every OTHER agent now arriving on the web. The industry has a name for this:
[Business-to-Agent (B2A)](https://www.averi.ai/blog/business-to-agent-b2a-agentic-web)
— making a brand legible and actionable to AI agents acting on users'
behalf, so that when an agent browses, evaluates, or books, it reads the
business's data correctly and can select it. The standards are forming NOW:

- **llms.txt** — a plain-text agent briefing at the domain root. CLAIM
  CORRECTED 2026-07-22 (same day, deeper research for the B2A market
  assessment — see `ONE_LIVE_B2A_GEO_MARKET_ASSESSMENT_v1.md` §1): the
  adoption/Lighthouse framing here came from a vendor source and is
  contradicted by stronger evidence — [Ahrefs' 137k-site study found 97%
  of llms.txt files get zero AI-bot reads](https://ahrefs.com/blog/llmstxt-study/)
  and [Google states no AI system currently uses
  llms.txt](https://www.seroundtable.com/google-ai-llms-txt-39607.html).
  Status accordingly: a zero-cost HEDGE we can emit for free, never a
  promise or a headline feature. The real B2A levers are entity
  consistency across the pipes agents actually read (Foursquare, Yelp,
  Bing Places) + JSON-LD + our own citable verified surface — assessment
  doc §3.4.
- **NLWeb** — [an emerging convention for exposing a site as a
  conversational endpoint agents can query](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/the-future-of-ai-optimize-your-site-for-agents---its-cool-to-be-a-tool/4434189)
  (MCP-compatible under the hood).
- **WebMCP** — [a browser-level standard in development at Google letting
  pages register callable tools](https://www.platinum.ai/ai-agent-web-standards)
  ("check_dates", "get_events") that browsing agents discover live.

**Proposed function F6 · Agent-readable presence.** The owned agent
generates and maintains the business's agent-facing artifacts from their
verified, gated data: (a) an llms.txt-style profile + correct Event JSON-LD
(extends F3) they host with one paste — cheap, static, Phase B; (b) 1Live's
own agent endpoint (MCP and/or NLWeb-style) that answers any consumer
agent's question about the entity with the owner-approved, gate-verified
version — Phase C, and the strategic prize: **1Live becomes the trust
anchor other agents cite.** A consumer agent planning someone's Friday night
gets the venue's events as the venue chose to state them, certified by our
gate, instead of a hallucinated summary of a stale webpage.

Two trust notes, stated before anyone asks: (1) "represented as they choose"
ends where the dispute rule begins — the agent endpoint serves `disputed` as
disputed, to machines as to humans (§4.2 applies verbatim; an agent-facing
surface that hid disputes would be a second, dishonest product surface).
(2) The endpoint serves the same gated truth the site serves — no
agent-only fast path around the gate, ever (it is a READ surface of
promoted data, nothing more).

## 14. The adoption-gap belief: VERIFIED, with one artist-shaped nuance

**Verified — the understanding gap is real and large.** Among small-business
non-adopters, [77% see no applicable use case, 62% cite lack of
understanding, 60% no in-house expertise](https://www.omago.ai/blog/sme-ai-adoption-2026-data);
[34% name lack of technical knowledge as the primary barrier and 38% name
cost](https://epiphanydynamics.ai/blog/state-of-ai-adoption-us-small-business-2026/);
even among adopters, [45% cite lack of expertise and 47% say choosing tools
is hard](https://capsulecrm.com/blog/small-business-ai-adoption-statistics/).
Roughly [half of owners are "Explorers" — at the cusp, waiting on clearer
ROI and easier tools](https://www.bluevine.com/blog/small-business-ai-trends-report-2026).
The cost FEAR outruns the cost reality (median small-business AI spend has
fallen to ~$28/month) — which is exactly a perception gap a free,
no-setup agent walks straight through.

**Verified hard — the "someone will charge them monthly to manage the AI"
fear is already an industry.** Generative-engine-optimization (GEO/AEO)
agencies now sell AI-visibility retainers at
[$1,500–$5,000/month for small businesses](https://www.webfx.com/blog/ai/generative-engine-optimization-cost/),
with [typical engagements $3,000–$25,000/month](https://thedigitalelevator.com/blog/aeo-and-geo-pricing-guide/).
This is the fee wave about to hit venues. The owned agent's F3/F4/F6 —
correct structured data, accuracy monitoring, agent-readable presence — IS
the essential core of what those retainers sell, delivered free. "The
80/20 of what a GEO agency would charge you $2,000/month for, free, from
the platform that verifies your events anyway" is a pitch a venue owner
understands in one sentence.

**The nuance — artists are not SMBs on this topic.** Artist sentiment on AI
is split and emotionally loaded: in one industry survey [60% of independent
artists had never used AI in their process, with the top fears being
devaluation of human creativity (42%) and copyright infringement
(31%)](https://info.xposuremusic.com/article/music-industry-report-2025),
while workflow-focused surveys find [87% use AI somewhere, led by younger
artists](https://www.hypebot.com/new-survey-reveals-how-87-of-artists-really-use-ai/).
Practical implication, adopted into this proposal: **artist-facing copy
leads with representation, accuracy, and control — never "AI-powered."**
The agent protects how they're represented (including against sloppy
AI summaries elsewhere — it is partly a defense AGAINST the AI wave);
it does not generate their art or their voice. Descriptor Foundry rules
already govern any AI-generated descriptor text; nothing here touches that.
Exact naming/wording goes to copy testing at design time with this
sensitivity pre-registered.

## 15. Essential needs — defining the 80/20 we build to (E1–E7)

From the small-business marketing research ([channel usage and
lowest-cost-essentials data](https://localiq.com/blog/small-business-marketing-trends-report-2026/);
[consistency/accuracy effects on customer trust](https://www.hookle.net/post/grow-your-small-business-by-combining-google-business-profile-with-social-media)),
the essential presence needs of a venue/artist/organizer, ranked:

| # | Essential need | Owned-agent coverage |
|---|---|---|
| E1 | Be findable with accurate basics — hours, location, dates consistent everywhere (inconsistency measurably drives customers away) | F1 + F2 (one source of truth, synced out) |
| E2 | Events published once, appearing everywhere | F1 + F3 widget + 1Live surfaces |
| E3 | Look alive — recent activity signals a reliable business | F3 (widget always current) + F4 (silence alerts) |
| E4 | Be represented correctly in search AND in AI answers | F3 (JSON-LD) + F6 (agent-readable presence) |
| E5 | Know what's working, in plain language | F4 digest |
| E6 | Maintained social presence (the most-used channel: ~66% unpaid social; 90%+ of social-active SMBs on Facebook, 74% Instagram) | Partial by design — F5 drafts, Phase C; v1 assists, never posts |
| E7 | Not getting ripped off — free, plain language, no lock-in, data exportable | The model itself (free-forever, Q4) |

Read: **F0–F4 + F6 covers E1–E5 and E7 — that IS the 80/20** (arguably
90/10 for a venue whose bottleneck is presence, not content). E6 is the
deliberately deferred tail: it is the most labor-intensive need, the most
platform-dependent (Meta), and the one where "assist, owner publishes"
is the only posture consistent with our physics. **"Build to that
standard" becomes mechanical:** each E above turns into an acceptance
criterion in the Phase A/B build contracts (e.g. E1: a venue's canonical
hours/dates change propagates to every 1Live surface and the widget
within one sync cycle; E5: digest readable by a smart non-engineer —
same bar as founder comms). The E-list is the rubric evaluators review
Phase A/B PRs against, alongside the design brief's rubric.

## 16. Open platform + privacy: the consumer-side mirror

The research supports privacy-forward positioning as genuinely
differentiating, not just virtuous: [65% of consumers are concerned about
big-tech assistants collecting their data; 27% currently refuse to share
any data with AI agents](https://sqmagazine.co.uk/consumer-trust-in-technology-statistics/);
[74% would switch to a competitor over a privacy line-crossing, and 47%
took a revenue-consequence action in the past six months over AI data
use](https://www.einpresswire.com/article/917170714/state-of-consumer-data-2026-americans-want-big-tech-to-come-clean-on-smart-device-tracking);
[only ~23% trust companies using AI with their data, and 51% want the
ability to limit AI features](https://usercentrics.com/press/usercentrics-state-of-digital-trust-2026-report/).

Proposed positioning, stated with its costs:

1. **Open where Facebook is walled:** event truth is public, exportable,
   and agent-readable (F6). The business's data remains theirs — leaving
   takes their data with them (E7). Tradeoff, honestly: openness means
   competitors can consume our verified feed. The moat is the verified
   first-party NETWORK and the gate's trust record, not a data hoard —
   consistent with how we already treat the pipeline. Attribution/licensing
   terms on the open feed are a design decision at Phase B (flagged, not
   decided here).
2. **On-device-first personalization for consumers:** taste preferences and
   browsing behavior stay on the device by default; the feed personalizes
   client-side against the public event stream. Precedent in canon: the
   voice-navigation requirement already prefers on-device recognition with
   plain-language disclosure. Tradeoff, honestly: default-local
   personalization limits cross-device sync and our own analytics; any
   sync-across-devices feature becomes opt-in with the same plain-language
   disclosure. Detailed design belongs with the member-preferences work
   (`ONE_LIVE_MEMBER_PREFERENCES_v1.md`), not this doc.
3. **The two sides reinforce:** businesses get an agent that never charges
   them and represents them faithfully; consumers get an open feed that
   never profiles them by default. Both are the same sentence: *the
   platform's incentives point at accurate representation, not attention
   capture.* That sentence is only true while no-pay-to-rank and
   no-connect-to-rank hold — which is why Q4 asks to make them a public
   promise.

## 17. Additions to the consolidated founder questions

- **Q6 — F6 ratification:** adopt "agent-readable presence" (llms.txt-style
  profile + JSON-LD in Phase B; 1Live agent endpoint serving gated truth
  in Phase C) into the function set, with the two trust notes in §13
  (disputes served to machines as to humans; read-only surface of promoted
  data) as binding conditions?
- **Q7 — the E-standard:** adopt E1–E7 (§15) as the definition of "essential
  needs" and the acceptance rubric Phase A/B build contracts are written
  and evaluated against?
- **Q8 — open + private as canon:** ratify the §16 positioning (open/
  exportable event truth; on-device-first consumer personalization with
  opt-in sync; the honest tradeoffs listed) as product canon guiding
  Step 9+ design — knowing it constrains analytics and monetization to
  consent-based, non-rank surfaces?

## 18. Sources (Parts I and II)

- [Billboard — Bandsintown launches free analytics tools for artists](https://www.billboard.com/music/music-news/bandsintown-launches-analytics-tools-for-artists-exclusive-6458292/)
- [The Music Universe — Bandsintown for Artists (510k artists, free)](https://themusicuniverse.com/bandsintown-unveils-bandsintown-artists/)
- [Bandsintown for Artists — integrations marketplace](https://www.artist.bandsintown.com/integrations) · [Linktree sync](https://artists.bandsintown.com/support/blog/new-integration-sync-your-bandsintown-events-with-your-linktree) · [Bandzoogle website widget](https://bandzoogle.com/blog/new-easily-integrate-your-bandsintown-tour-dates-into-your-website)
- [Google — verify your Business Profile (methods menu)](https://support.google.com/business/answer/7107242?hl=en) · [BrightLocal guide](https://www.brightlocal.com/learn/google-business-profile/getting-started/verifying-google-business-profile/)
- [Gatilab — event schema markup adoption and practice, 2026](https://gatilab.com/event-schema-markup/) · [VenueQuoter — venue event schema CTR effects](https://venuequoter.com/blog/the-proven-way-to-boost-event-visibility-for-venues) · [Schema.dev — Event markup guide](https://schema.dev/blog/your-complete-guide-to-getting-started-with-event-schema-mark-up/)
- [WP Event Aggregator — commodity ICS/feed ingestion](https://wordpress.org/plugins/wp-event-aggregator/)
- [Elfsight — Instagram Graph API developer guide 2026 (requirements, review, limits)](https://elfsight.com/blog/instagram-graph-api-complete-developer-guide-for-2026/) · [Storrito — Instagram API changes 2026](https://storrito.com/resources/instagram-api-2026/) · [Meta — Instagram Platform overview](https://developers.facebook.com/docs/instagram-platform/overview/)
- [Digital Applied — AI agent protocol ecosystem map 2026 (MCP/A2A/ACP/UCP)](https://www.digitalapplied.com/blog/ai-agent-protocol-ecosystem-map-2026-mcp-a2a-acp-ucp) · [State of agentic AI standards 2026](https://amdatalakehouse.substack.com/p/the-state-of-agentic-ai-standards)

Part II additions:

- [Averi — Business-to-Agent (B2A): preparing a brand for the agentic web](https://www.averi.ai/blog/business-to-agent-b2a-agentic-web) · [Platinum.ai — what is llms.txt (adoption, Lighthouse)](https://www.platinum.ai/what-is-llms-txt) · [Platinum.ai — llms.txt vs WebMCP vs SDF vs CAP compared](https://www.platinum.ai/ai-agent-web-standards) · [Microsoft — making your website agent-ready with NLWeb and MCP](https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/the-future-of-ai-optimize-your-site-for-agents---its-cool-to-be-a-tool/4434189) · [Wix — llms.txt guide](https://www.wix.com/studio/ai-search-lab/llms-txt) · [Search Engine Journal — the agentic web's identity/capability split](https://www.searchenginejournal.com/the-agentic-web-is-splitting-into-two-bets-identity-and-capability/578685/)
- [Epiphany Dynamics — US small-business AI adoption 2026 (barrier percentages)](https://epiphanydynamics.ai/blog/state-of-ai-adoption-us-small-business-2026/) · [Omago — SME AI adoption 2026 (non-adopter reasons)](https://www.omago.ai/blog/sme-ai-adoption-2026-data) · [Capsule — small-business AI adoption statistics](https://capsulecrm.com/blog/small-business-ai-adoption-statistics/) · [Bluevine — 2026 small-business AI trends report](https://www.bluevine.com/blog/small-business-ai-trends-report-2026)
- [WebFX — GEO cost guide](https://www.webfx.com/blog/ai/generative-engine-optimization-cost/) · [Digital Elevator — AEO/GEO pricing guide 2026](https://thedigitalelevator.com/blog/aeo-and-geo-pricing-guide/) · [TeamAI — cost of GEO 2026](https://teamai.com/blog/generative-ai-and-business/what-is-the-cost-of-geo/)
- [Xposure Music — Independent Music Industry Report 2025 (artist AI sentiment)](https://info.xposuremusic.com/article/music-industry-report-2025) · [Hypebot — how 87% of artists really use AI](https://www.hypebot.com/new-survey-reveals-how-87-of-artists-really-use-ai/) · [Ditto Music — 60% of musicians using AI](https://press.dittomusic.com/60-of-musicians-are-already-using-ai-to-make-music)
- [LocaliQ — small-business marketing trends report 2026 (channel usage)](https://localiq.com/blog/small-business-marketing-trends-report-2026/) · [Hookle — Google Business Profile + social consistency effects](https://www.hookle.net/post/grow-your-small-business-by-combining-google-business-profile-with-social-media)
- [SQ Magazine — consumer trust in technology statistics 2026](https://sqmagazine.co.uk/consumer-trust-in-technology-statistics/) · [State of Consumer Data 2026 (smart-device tracking, switching behavior)](https://www.einpresswire.com/article/917170714/state-of-consumer-data-2026-americans-want-big-tech-to-come-clean-on-smart-device-tracking) · [Usercentrics — State of Digital Trust 2026](https://usercentrics.com/press/usercentrics-state-of-digital-trust-2026-report/)

---

## Addendum 2026-08-04 — founder directive: the client value ledger, weekly ROI, and where the agent lives

**Founder-directed 2026-08-04, verbatim (message "Re: AI Agent…."; decision
record `docs/memory/decisions/2026-08-04_agent-value-ledger-directive.md`):**

> *"Give the agent a value ledger. It logs every task and sends a weekly ROI report to the contact: hours saved, $ value*
> *Put the agent in the group chat.*
> *Uptime is a selling point.*
> *Free work is the referral engine.*
> *Make the agent write to Excel, not its own markdown. A shared source of truth is the difference between a demo and a system.*
> *Visible ROI is the retention strategy. A weekly "you saved $" report."*

Subject clarified by the founder same day: these apply to THIS agent product —
the agent's clients — not to the repo's internal agent org. Mapping into the
existing three-layer model, with build status stated honestly:

1. **Client value ledger + weekly "you saved $" report → the GIFT layer's
   retention spine.** The agent logs every task it performs for a business
   (hours saved, $ value, estimate basis required) into that client's ledger
   and reports weekly to the client's contact. **ENGINE BUILT** (PR #159:
   `tools/value_ledger.py` — client-generic xlsx writer + Weekly ROI sheet +
   plain-language report + audit mirror; committed demo:
   `docs/strategy/examples/AGENT_CLIENT_VALUE_LEDGER_DEMO.xlsx`). Honesty
   physics baked in: $ figures are estimates (hours x the client's own rate,
   set by them in their workbook), every row carries its basis, rates freeze
   per row. E-needs fit: E5 (proof it's working) and E7 (not getting ripped
   off) — the report IS the retention surface.
2. **"Write to Excel, not its own markdown" → the client's shared spreadsheet
   is the source of truth.** Registered in `ONE_LIVE_CONNECTOR_REGISTRY_v1.md`
   as a PLANNED AUTHORIZED-SYNC connector (their file, their share grant).
   Until that connector is founder-greenlit, the engine produces the workbook
   locally; nothing claims a live sync.
3. **"Put the agent in the group chat" → a SKIN-layer presence surface.**
   Registered as a PLANNED connector (their invite, their platform). Scope,
   identity, and platform are onboarding decisions; credentials founder-crucial.
4. **"Uptime is a selling point" → an ops bar for the agent product**: the
   Sentinel rule (dead-man + monitoring on every scheduled loop) is what makes
   an uptime claim honest; any external uptime CLAIM enters the claim ledger
   with evidence before it ships in copy.
5. **"Free work is the referral engine" → growth posture**, consistent with
   free-forever (Q4) and no-connect-to-rank: the free tier is the referral
   motion, never a ranking lever.

Gating unchanged: this addendum adds ZERO license to build connectors, mint
credentials, or open the client pilot — Phase A/B/C gates and the Q1–Q22
ratification list stand exactly as written above.
