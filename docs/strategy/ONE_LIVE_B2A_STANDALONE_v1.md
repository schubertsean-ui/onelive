# ONE LIVE — Alternative S v1: the standalone B2A agent (no OneLive pipes in the picture)

**Compiled 2026-07-22 · Status: PROPOSAL — research response to the founder's sixth 2026-07-22 directive: draft the alternative where our pipes are not in the picture — why is a B2A agent good for people and orgs in the ABSENCE of OneLive; run SWOT and deep competitive analysis for that standalone model; then evaluate that SWOT back to OneLive if it is truly separate and standalone. Strategic intent stated by the founder: widespread use of the agents should facilitate our ability to gather the relevant data we want. Companion to the three prior docs; questions Q18–Q20. Nothing here is license to build.**

Greppable summary: Alternative S = a B2A agent whose ENTIRE output lives on
the business's own property (their domain, their feeds, their pipe
accounts) — valuable with zero OneLive coupling. The substrate thesis: if
thousands of entities publish clean, structured, domain-hosted truth, ANY
consumer — including OneLive — reads it; and under the RATIFIED sensor
canon, domain provenance alone qualifies for the first-party fast lane (no
claim/account relationship required). Standalone SWOT: neutrality and
standard-setting power vs no distribution, no verification story, no
funding logic, and a commons that equally feeds our competitors. Deep
competitive read: in the standalone frame the rivals become site builders
(Squarespace AIO Scanner, Wix AI Visibility Overview, Shopify agentic
storefronts) and the CDN layer (Cloudflare) — actors who own distribution
we don't. Evaluation back to OneLive: the decoupled ARCHITECTURE is worth
adopting wholesale ("works without us, better with us"); the decoupled
VENTURE is worth rejecting — it funds a commons our better-distributed
competitors harvest, loses the claim flywheel, and hands the mantle to a
brand that isn't ours unless we steward it.

---

## 1. The ask (verbatim anchors, 2026-07-22)

1. "Draft an alternative where our pipes are not even in the picture …
   why is a B2A good for the people and orgs in the absence of OneLive."
2. "We want the widespread use of the agents to facilitate our ability to
   grab the relevant data we want."
3. "Run SWOT and deep competitive analysis for that kind of model and
   then evaluate the SWOT to OneLive if it is truly 'separate' and
   stand alone."

## 2. Alternative S — the standalone agent, specified

**What it is with OneLive deleted from the universe:** a free agent any
venue/artist/organizer points at their own web presence. It then:

- **S-1 Emits domain-hosted truth:** correct schema.org/JSON-LD event and
  business markup INTO their own site (widget or plugin), a standards-
  compliant calendar feed (ICS) at a well-known URL on THEIR domain, and
  (as a zero-cost hedge) agent-briefing files. Their domain becomes the
  machine-readable source of record for themselves.
- **S-2 Maintains pipe consistency:** guided/API-assisted claiming and
  syncing of the 5–6 databases AI actually reads (Google Business
  Profile, Bing Places, Foursquare, Yelp, Apple Maps) — NAP + hours +
  events identical everywhere.
- **S-3 Watches and alerts:** detects drift (site says Friday, Yelp says
  Saturday), silence (feed went stale), and breakage (site blocks AI
  crawlers; wrong Cloudflare signals for a business that WANTS to be
  read — the inverse of publisher paywalling: culture supply wants
  maximal legitimate agent access).
- **S-4 Serves their own doorman:** an agent endpoint ON THEIR DOMAIN
  (static JSON or lightweight MCP) answering machine questions from
  their published truth — owner-revocable (the H2 "you hold the string"
  token), with provenance stamps.

**Why this is genuinely good for them with nobody's platform attached:**
every output lands on property they own. No lock-in is even POSSIBLE —
delete the agent and the markup, feeds, and pipe accounts remain theirs.
It is the "get your affairs in order for the AI era" tool: presence
basics handled, on their turf, free.

**Form factors** (if it were its own venture): (a) open-source
self-hostable tool; (b) free hosted service under a neutral brand; (c)
open STANDARD + reference implementation (the Presence Standard with a
tool attached). The strongest standalone form is (c)+(b): standards
create the durable asset; hosting creates reach beyond the technical few.

## 3. The substrate thesis — how OneLive wins with no pipes at all

The founder's stated intent works mechanically: if thousands of entities
run Alternative S, the open web's event data becomes CLEAN — structured,
current, domain-hosted, consistent across pipes. Then:

1. **Our extraction gets cheaper and sharper with no relationship
   required.** Deterministic JSON-LD/ICS parsing replaces LLM extraction
   on every S-running source (cost-discipline rule 1 compounding at
   metro scale), and cross-pipe consistency gives the gate more
   corroboration signal per entity.
2. **The fast lane survives the decoupling.** The RATIFIED sensor canon
   (2026-07-14) already recognizes VERIFIED EXTERNAL CHANNELS: "if it
   comes from the venue/artist/…, and we validate domain and other
   aspects, we should give that a high value of truth." Domain-hosted
   agent output IS a first-party external channel — validated by domain
   provenance, not by holding an account with us. Elevated trust without
   a claim flow.
3. **What does NOT survive:** everything account-shaped — the dispute-
   aware owner relationship, destructive-change corroboration holds tied
   to claim age, the agent-traffic log we'd host, digest emails, the
   re-engagement channel, and the acquisition flywheel itself (magic-link
   claims, "how you appeared" — the CAC weapon). The substrate feeds our
   PIPELINE; it does not feed our RELATIONSHIPS.

## 4. SWOT — Alternative S as a genuinely separate, standalone thing

**Strengths:** perfect neutrality (chambers, arts councils, even agencies
and consultants can adopt/endorse it — no platform agenda to resist); no
two-sided cold start (value is complete without any consumer audience);
inherently anti-lock-in (all output on owner property) — the credibility
position money can't buy; standard-setting power in a standards vacuum;
open-source community leverage possible.

**Weaknesses:** no distribution of its own — a free tool with no audience
attached must be FOUND, and standalone tools are found via app stores,
site builders, and word of mouth we don't control; no funding logic (who
pays maintainers? donations/grants are slow and fragile); no verification
story — S is self-attested by design: it makes a business's claims
CONSISTENT everywhere, not TRUE (no gate, no dispute mechanism, no
corroboration), which caps how much answer engines should trust it; no
feedback surface ("get found" — where? it cannot show outcomes); support
burden with zero revenue.

**Opportunities:** become the category's Let's Encrypt (the purest
version of the mantle — but the mantle then belongs to the standalone
brand); foundation/civic funding (arts + digital-equity money exists for
exactly this); adoption by OTHER platforms and aggregators as their
intake standard (network effects beyond any one consumer); integration
into site builders as the neutral implementation.

**Threats:** platform capture — the site builders are ALREADY shipping
this natively ([Squarespace's AIO Scanner, announced to track AI mentions
and recommend fixes](https://abz.global/squarespace-blog/ai-moves-by-traditional-website-builders-in-2025-and-what-to-expect-in-2026);
[Wix's AI Visibility Overview + schema tooling](https://www.websitebuilderexpert.com/website-builders/comparisons/wix-vs-squarespace/);
[Shopify's "agentic storefronts"](https://abz.global/squarespace-blog/ai-moves-by-traditional-website-builders-in-2025-and-what-to-expect-in-2026))
— for any business ON those platforms, a standalone agent is redundant
the day the builder ships the feature; CDN-layer capture ([Cloudflare now
mediates AI crawler access economically — pay-per-crawl evolving to
pay-per-use, default agent-blocking on ad pages from Sept
2026](https://techcrunch.com/2026/07/01/cloudflares-new-policy-pushes-ai-companies-to-pay-for-publishers-content/))
— the read-path is being tolled and defaulted by infrastructure we don't
control; spam capture — a free, ungated consistency tool is ALSO a spam
cannon (fake businesses emitting perfectly-structured fictions), and one
abuse wave destroys the neutral brand AND degrades the substrate's
credibility with answer engines (the exact opposite of the intent);
open-source rot/fork-and-extend by better-funded actors.

## 5. Deep competitive analysis (the standalone frame changes who we fight)

In the integrated model, competitors were GEO tools and agencies. In the
standalone frame, the competition is EVERY DEFAULT SURFACE a business
already touches:

| Competitor class | Who | Their position vs Alternative S |
|---|---|---|
| Site builders (native) | Squarespace AIO Scanner, Wix AI Visibility Overview + schema, Shopify agentic storefronts | **The killer threat.** They own the surface where the business already edits its site; a native toggle beats an external tool for their tenants. S survives only where they aren't: custom sites, WordPress long tail, businesses with no real site, multi-surface consistency ACROSS platforms — and live-event data depth no generic builder models well |
| Platform consoles | Google Business Profile, Bing Places, Yelp for Business, Meta | Free, default, first-party to the pipes — but single-surface, no cross-pipe consistency, no event depth, and each has an agenda (their surface first). S's cross-pipe consistency is real differentiation |
| CMS plugins | Yoast/RankMath (schema), WP event plugins | Cover S-1 partially for WordPress; fragmented, technical, no pipe sync, no monitoring |
| GEO tool free tiers | Otterly-class monitors, one-shot audit tools | Monitoring without fixing; upsell-driven; no publishing side |
| CDN/infra layer | Cloudflare (crawl control, signals) | Controls the read-path economics; could ship "agent-ready presence" for its customers tomorrow. More plausible partner/rail than direct rival for SMB culture — but a structural dependency either way |
| Open standards/OSS | schema.org itself, indie llms.txt tooling | The commons S would join; fragmented, no steward focused on local culture |
| Do-nothing default | The 83% | The real market leader, as always |

**The standalone strategic bind, stated plainly:** S's differentiation
(cross-pipe consistency + event depth + monitoring, free and neutral) is
real, but its DISTRIBUTION is nonexistent exactly where its rivals'
distribution is total. Standalone utilities win only by becoming a
standard others carry (Let's Encrypt rode hosting panels and certbot into
every server) — which for S means the site builders and CMS plugins
adopting the Presence Standard as their implementation target. That is a
standards play, not a product play, and it takes years and a credible
neutral steward.

## 6. The evaluation the founder asked for: that SWOT, read back to OneLive if S is TRULY separate

| Dimension | If S is truly separate/standalone | Consequence for OneLive |
|---|---|---|
| Data substrate | Clean domain-hosted truth spreads | **WIN** — cheaper deterministic extraction, more corroboration, fast lane via domain provenance (§3.2), zero support burden on us |
| Competitive symmetry | The substrate is OPEN | **LOSS (the big one)** — Google, Eventbrite, site builders, and every future rival read the SAME clean substrate with more distribution than us. A truly separate S is a commons we'd fund whose largest harvesters would be our better-distributed competitors. Our residual edge shrinks to the gate + consumer experience — real, but we'd have spent our building capacity strengthening everyone's pipeline |
| Acquisition flywheel | No claim relationship, no magic links, no digests | **LOSS** — the CAC weapon (assessment §4) disappears; OneLive acquires supply relationships from zero, separately |
| Trust machinery | Self-attested consistency, no gate | **MIXED** — domain provenance still feeds OUR gate (win), but S itself can spread confident fictions (spam capture, §4 Threats), which pollutes the substrate we planned to drink from; without us, nobody disputes anything |
| Mantle/brand | The Standard's credibility accrues to the neutral brand | **LOSS unless stewarded** — "default" status lands on S, not OneLive; the founder's mantle strategy (MANTLE_v1) transfers to an entity that, if TRULY separate, we don't control |
| Focus/capacity | Two products, two brands, one tiny team | **LOSS** — the charter's scarcest resource is build capacity on the critical path (Steps 6–10); a separate venture forks it |
| Openness credibility | Nobody can call it a walled garden | **WIN** — the strongest possible answer to the §7-of-MANTLE attack, IF we can claim association |

**Net evaluation:** as a SEPARATE VENTURE, Alternative S is strategically
generous to our competitors and starves our own flywheel — the founder's
stated goal ("widespread agents facilitate OUR data gathering") is served
only in the same breath that it serves every rival with better
distribution, while the things that make OneLive defensible (claim
relationships, dispute-aware trust, the consumer surface, the mantle) are
all left on the table. As an ARCHITECTURE, however, S is simply correct:
everything it prescribes (output on the owner's domain, open formats,
pipe consistency, revocable authority, no lock-in possible) is what makes
the integrated agent's "free forever, you hold the string" promise TRUE
rather than rhetorical.

## 7. Synthesis — "works without us, better with us" (the recommended resolution)

Adopt S's architecture inside the integrated product; decline S as a
separate venture; keep the stewardship door open:

1. **Build the owned agent S-compliant from day one:** every artifact the
   agent produces lives on or belongs to the business (their markup,
   their feeds, their pipe accounts, their revocable tokens). Deleting
   OneLive leaves them whole. This is the provable version of "they
   control the content" — and it makes the walled-garden attack
   unanswerable.
2. **The OneLive coupling is an UPGRADE, never a requirement:** claiming
   inside OneLive adds the gate relationship, dispute handling, the
   digest, the Mirror re-scans, the consumer surface, and (Phase C) the
   hosted Doorman + agent-traffic log. Free either way; the upgrade is
   where the flywheel lives.
3. **The Standard is the piece that goes truly standalone** (this is
   MANTLE_v1 Q16, now with sharper rationale): publish E1–E7 openly and
   court the site builders and CMS plugins — the actors §5 shows will
   ship SOMETHING natively — to implement it. Their distribution then
   spreads OUR definition of the basics, and their tenants' output lands
   on the open substrate we read. We don't need to own the tool the
   whole world uses; we need the world's tools to emit the substrate,
   and OneLive to be its best-verified consumer.
4. **Re-evaluate a spun-out steward** (Let's Encrypt-style nonprofit for
   the Standard + reference implementation) ONLY at scale signals: a
   second metro live, external platforms actually implementing the
   Standard, or civic/foundation funding materializing — founder
   decision, not before.

## 8. Additions to the consolidated founder list (Q18–Q20)

- **Q18 — S-compliance as a build constraint:** ratify §7.1 — every
  owned-agent artifact lives on/belongs to the business, verified by an
  acceptance test in Phase A ("delete OneLive, they keep everything")?
- **Q19 — Separate venture: declined?** confirm Alternative S is NOT
  pursued as a separate product/brand now, per §6's evaluation (the
  commons-funds-competitors problem + flywheel loss + capacity fork) —
  recorded as a decision, revisitable at §7.4's scale signals?
- **Q20 — Standards-into-builders motion:** approve courting site
  builders/CMS plugins to implement the open Presence Standard (cheap,
  post-publication, founder-fronted introductions) as the distribution
  strategy for the Standard — accepting the tradeoff that their tenants'
  improved data is equally readable by our competitors?

## 9. Sources

- [abZ Global — AI moves by website builders 2025→2026 (Squarespace AIO Scanner, Shopify agentic storefronts)](https://abz.global/squarespace-blog/ai-moves-by-traditional-website-builders-in-2025-and-what-to-expect-in-2026) · [WebsiteBuilderExpert — Wix vs Squarespace 2026 (Wix AI Visibility Overview, schema tooling)](https://www.websitebuilderexpert.com/website-builders/comparisons/wix-vs-squarespace/)
- [TechCrunch — Cloudflare's policy pushing AI companies to pay for content](https://techcrunch.com/2026/07/01/cloudflares-new-policy-pushes-ai-companies-to-pay-for-publishers-content/) · [PPC Land — pay-per-crawl → pay-per-answer](https://ppc.land/cloudflare-stops-charging-ai-per-crawl-and-starts-paying-per-answer/) · [Cloudflare press — "your content, your rules"](https://www.cloudflare.com/press/press-releases/2026/cloudflare-allows-the-agentic-internet-to-flourish-with-a-simple-philosophy-your-content-your-rules/)
- Foundations: `ONE_LIVE_B2A_GEO_MARKET_ASSESSMENT_v1.md` §§3–5 (pipes, actors, forces), `ONE_LIVE_MANTLE_v1.md` (Standard/stewardship), `ONE_LIVE_SCALEOUT_SENSOR_ARCHITECTURE_v1.md` (verified external channels — the ratified rule §3.2 leans on), Let's Encrypt/HubSpot sources in MANTLE_v1 §10.
