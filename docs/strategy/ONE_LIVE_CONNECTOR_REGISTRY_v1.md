# ONE LIVE — Connector Capability Registry v1

**Created 2026-08-01 at founder direction ("Go with 1–4"). Supersedes the flat
READ/SYNC/STAGE legend of `ONE_LIVE_AGENT_SURFACES_v1.md` for CAPABILITY
claims: platforms differ materially in authorization, moderation, terms, and
cost, and marketing copy must never outrun this registry. Every connector
carries a capability CLASS (what the integration can be), a current STATUS
(what is true today — nothing is built yet, so nothing is LIVE), and the
honest UI language. NOTE (unchanged): none of this is license to build;
platform-credential minting and new services remain founder-crucial.**

**Capability classes:**
- **DIRECT PUBLISH** — supported API, approved app, user authorization → "Connected — publishes after your approval"
- **AUTHORIZED SYNC** — factual updates through a supported/partner connection → "Connected — kept current"
- **NATIVE HANDOFF** — OneLive prepares everything, the platform's own app finishes → "Ready — one tap to finish"
- **ASSISTED SUBMISSION** — OneLive fills the packet; platform review or manual step remains → "Submitted — awaiting review"
- **READ & MONITOR** — observe and drift-watch only → "Monitored"
- **PARTNER-DEPENDENT** — feasible only after platform/commercial approval → "Planned — partner access required"
- **UNSUPPORTED** — no reliable compliant workflow → not claimed

**Publication states (all write-class connectors):**
`DRAFTED → APPROVED → SUBMITTED → ACCEPTED → PUBLIC → INDEXED`, with
exceptions `REJECTED · MODERATED · EXPIRED · AUTH-LOST · RETRYING`. Every
write returns a receipt (platform, account, object id, submitted-at, status,
public URL when available, last verification, error, retries). "Published"
is never claimed from an API success alone; a reconciliation loop compares
intended vs. public state.

| Connector | Capability class (target) | Status today | Authorization required | Notes / constraints |
|---|---|---|---|---|
| OneLive listing + hosted event pages | DIRECT PUBLISH | PLANNED (our surface) | claim verification | gated by the trust pipeline as ever |
| Website events widget + JSON-LD | DIRECT PUBLISH | PLANNED (we deploy) | site install (script/DNS) | unique URL per event; validated structured data; visible page must match markup |
| Link-in-bio page | DIRECT PUBLISH | PLANNED (we host) | claim | — |
| Google Business Profile (posts, hours, events) | DIRECT PUBLISH | PLANNED | owner OAuth; registered app | supported API; eligibility varies by account type |
| Bing Places + IndexNow | AUTHORIZED SYNC | PLANNED | site verification | IndexNow = notification, NOT guaranteed crawling/indexing |
| Apple (Business Connect) | PARTNER-DEPENDENT → AUTHORIZED SYNC | PLANNED | Apple partner approval + business delegation | NATIVE HANDOFF available before partner status |
| Yelp | READ & MONITOR now; PARTNER-DEPENDENT for listing management | PLANNED | Yelp partner program (per-location, may bill) | some updates moderated up to ~2 weeks; never "instant" |
| Nextdoor | PARTNER-DEPENDENT → DIRECT PUBLISH | PLANNED | API approval + authenticated business profile | content attributable to the business, not to OneLive |
| Foursquare | READ & MONITOR; contribution PARTNER-DEPENDENT | PLANNED | API contract | API pricing beyond small free tier |
| Bandsintown | AUTHORIZED SYNC (artist-claimed) | PLANNED | artist claims their page | artist edition |
| Songkick | READ & MONITOR only | ON HOLD (founder-decided 2026-08-02: "Put Songkick on hold but don't lose it") | — | RETAINED, not removed — the value case (artist/venue event database, concert-discovery + artist-follow alerts) is preserved here and in the surfaces inventory. API terms are retrieval-oriented, noncommercial, restrictive — **no product use until a founder-commissioned legal review of the API terms clears it (legal posture)**; never depicted as a write surface. Reopen trigger: that legal review |
| City/press event calendars (Do512-class, alt-weeklies, visitor bureaus) | ASSISTED SUBMISSION | PLANNED | per-site forms/accounts | editorial review timing is theirs; also READ for drift-watch |
| Event aggregators (AllEvents-class) | ASSISTED SUBMISSION / AUTHORIZED SYNC | PLANNED | per-platform | long-tail indexing |
| Instagram (feed/story/carousel/reel, Collab) | DIRECT PUBLISH | PLANNED | professional account + Meta app review + OAuth | publishing limits; token expiry handling; NATIVE HANDOFF (v1 boost recipe) before review |
| Facebook Page posts | DIRECT PUBLISH | PLANNED | Page + app review + OAuth | — |
| Facebook Events | PARTNER-DEPENDENT | PLANNED | restricted API access | tracked separately from Page posts |
| YouTube / Shorts | DIRECT PUBLISH | PLANNED | owner OAuth | unverified API projects may be limited to private until audit; verify before claiming |
| Meta boost (their ad account) | NATIVE HANDOFF (v1 recipe) → DIRECT (Phase-C) | PLANNED | none (v1) / ad account OAuth (Phase-C) | their budget, their cap; no % of spend |
| Email (their ESP) / SMS (their tool) | DIRECT PUBLISH via their account | PLANNED | their ESP/SMS credentials, consent lists | suppression/consent state respected |
| Eventbrite / Tock / ticketing | READ & link-through | PLANNED | none (public links) | never brokered |
| AI crawlers (robots.txt allowances) | AUTHORIZED SYNC (config we deploy) | PLANNED | site control | OAI-SearchBot = ChatGPT search; GPTBot = training (managed separately); PerplexityBot, ClaudeBot; Google-Extended governs Gemini/Vertex grounding, NOT Google Search inclusion |
| Wikidata (entity) | ASSISTED SUBMISSION | PLANNED | community norms | only where notability is real |
| llms.txt | AUTHORIZED SYNC (deployed file) | PLANNED | site control | zero-cost hedge; ~97% of AI crawls ignore it (C-05) |
| UTM/door codes/QR + platform analytics | READ & MONITOR (measurement) | PLANNED | their analytics access | attribution classified per claim ledger, never presented as causal lift without a comparison |

**Registry rules:** (1) a platform is presented at a class only when this
registry supports it, and at LIVE only after sandbox tests (authorization,
expiry, approved/rejected write, moderation, duplicate, retry, revocation,
public-state verification, deletion) pass for that connector; (2) status
changes land here first, marketing copy second; (3) the "reviewed as of"
date below is a standing trigger. **Reviewed as of: 2026-08-01** (against the
external review's platform-documentation citations; next review before pilot).
