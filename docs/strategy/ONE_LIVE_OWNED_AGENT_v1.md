# ONE LIVE — The Owned Agent v1 (an AI agent artists, venues, and event organizers own and control)

**Compiled 2026-07-22 · Status: PROPOSAL — research response to the founder's 2026-07-22 question ("How might we create an AI agent that is 'owned' by and 'works for' artists and events and venues?"). Nothing here is license to build; every build item is gated below. Builds directly on RATIFIED canon: `ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md` (first-party fast lane, watcher records, scoped authority + dispute override).**

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
That is OneLive's consumer thesis stated from the supply side. What
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
OneLive the source consumer agents (Claude, ChatGPT, Gemini surfaces) query
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

## 10. Consolidated founder questions (the ONLY asks in this doc)

1. **Ratify the concept?** The three-layer decomposition (pipe = ratified
   sensor canon, gift = F0–F4, skin = agent-framed onboarding) as the
   direction for the owned agent — yes/no/amend. Includes the working name
   question ("your OneLive agent"? partner-facing name can come later).
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

## 11. Sources

- [Billboard — Bandsintown launches free analytics tools for artists](https://www.billboard.com/music/music-news/bandsintown-launches-analytics-tools-for-artists-exclusive-6458292/)
- [The Music Universe — Bandsintown for Artists (510k artists, free)](https://themusicuniverse.com/bandsintown-unveils-bandsintown-artists/)
- [Bandsintown for Artists — integrations marketplace](https://www.artist.bandsintown.com/integrations) · [Linktree sync](https://artists.bandsintown.com/support/blog/new-integration-sync-your-bandsintown-events-with-your-linktree) · [Bandzoogle website widget](https://bandzoogle.com/blog/new-easily-integrate-your-bandsintown-tour-dates-into-your-website)
- [Google — verify your Business Profile (methods menu)](https://support.google.com/business/answer/7107242?hl=en) · [BrightLocal guide](https://www.brightlocal.com/learn/google-business-profile/getting-started/verifying-google-business-profile/)
- [Gatilab — event schema markup adoption and practice, 2026](https://gatilab.com/event-schema-markup/) · [VenueQuoter — venue event schema CTR effects](https://venuequoter.com/blog/the-proven-way-to-boost-event-visibility-for-venues) · [Schema.dev — Event markup guide](https://schema.dev/blog/your-complete-guide-to-getting-started-with-event-schema-mark-up/)
- [WP Event Aggregator — commodity ICS/feed ingestion](https://wordpress.org/plugins/wp-event-aggregator/)
- [Elfsight — Instagram Graph API developer guide 2026 (requirements, review, limits)](https://elfsight.com/blog/instagram-graph-api-complete-developer-guide-for-2026/) · [Storrito — Instagram API changes 2026](https://storrito.com/resources/instagram-api-2026/) · [Meta — Instagram Platform overview](https://developers.facebook.com/docs/instagram-platform/overview/)
- [Digital Applied — AI agent protocol ecosystem map 2026 (MCP/A2A/ACP/UCP)](https://www.digitalapplied.com/blog/ai-agent-protocol-ecosystem-map-2026-mcp-a2a-acp-ucp) · [State of agentic AI standards 2026](https://amdatalakehouse.substack.com/p/the-state-of-agentic-ai-standards)
