# ONE LIVE — Agent Surfaces, Tools & Resources v1 (typed inventory)

**Compiled 2026-08-01 · Status: WORKING REFERENCE (research-grade companion to
the ratified canon; not itself a ratification). Requested by the founder
("a list of resources and tools and site used and deployed organized by type";
GEO + wider SEO surfaces added at founder direction the same day). This is the
single inventory every example, diagram, and campaign artifact draws from —
when a surface is added here, the examples must follow (founder directive:
"follow through so the examples show that all relevant sources are being
used").**

**SUPERSEDED IN PART (2026-08-01, same day):** for CAPABILITY claims the
flat legend below is superseded by `ONE_LIVE_CONNECTOR_REGISTRY_v1.md`
(capability classes, statuses, auth requirements, publication states) —
adopted from the external review at founder direction. This doc remains the
typed INVENTORY of surfaces and roles.

**Legend — how the agent touches a surface:** **READ** = source it extracts
from · **SYNC** = kept correct automatically (Tier 1) · **STAGE** = content
drafted, ships only on the owner's tap (Tier 2) · **MEASURE** = results read
back · **PHASE-C** = later, behind platform review. Costs shown are the
business's, not ours.

## 1 · Search & maps — where high-intent discovery happens
| Surface | Use | Role | Cost |
|---|---|---|---|
| Google Business Profile (Search · Maps · "Things to do" · posts) | READ · SYNC · STAGE | Highest-intent local surface; event posts, hours, "Buy tickets" buttons; 76% of local searchers visit within 24h | Free |
| Bing Places | SYNC | Feeds Bing/Copilot answers | Free |
| Apple Maps (Apple Business Connect) | READ · SYNC | The iPhone half of the audience; the winter-hours drift class | Free |
| Nextdoor Business | SYNC · STAGE | The neighborhood layer — events reach the streets that walk in | Free |

## 2 · Discovery apps & event databases — what AI tools actually pull from
| Surface | Use | Role | Cost |
|---|---|---|---|
| Yelp | READ · SYNC | NAP/hours consistency; a major source AI assistants draw on for local answers (C-03: share percentages retired) | Free listing |
| Foursquare | READ · SYNC | The location database many AI stacks license | Free |
| Bandsintown · Songkick | READ · SYNC | Artist/venue event databases; concert-discovery + artist-follow alerts | Free |
| City guides & press calendars (Do512-class per city; alt-weeklies; visitor bureaus) | READ · STAGE (submit) · drift-watch | Free editorial surfaces with real domain authority — foot traffic AND backlinks; where the case study caught a real day-of-week mislabel | Free |
| Event aggregators (AllEvents-class) | SYNC | Long-tail event indexing that search engines crawl | Free |
| Segment surfaces: TripAdvisor (venues/wineries) · Untappd (breweries) · Vivino (wineries) · Bandcamp/Spotify/SoundCloud profiles (artists) | SYNC · drift-watch | Category-specific discovery mapped to the 23-segment canon | Free |

## 3 · Their ticketing & commerce — always THEIR accounts, never brokered
| Tool | Use | Role | Cost |
|---|---|---|---|
| Eventbrite · Tock · Ticketmaster-class (whatever they already use) | READ · link-through | Tickets/reservations stay on their platform; the agent attaches links everywhere | Their existing fees |
| Their POS / door codes / QR cards | MEASURE | Redemption + attendance attribution, no new hardware | $0 |

## 4 · Social — staged by the agent, sent on their tap
| Surface | Use | Role | Cost |
|---|---|---|---|
| Instagram (feed · story · carousel · reel · Collab posts · licensed audio) | READ · STAGE | Engagement-canon carousel/reel from their OWN footage/audio; Collab posts double reach with the artist | Free organic |
| Facebook (events · page posts) | STAGE | Event objects with video attached; the invite graph | Free organic |
| YouTube / Shorts | STAGE | The reel cut re-posted — video results in Google search | Free |
| Meta boosts (their ad account, their cap) | STAGE (2-tap recipe) | v1 needs NO Meta API; no fees, no percentage of spend | Their optional budget |

## 5 · Their own property — the owned layer kept alive
| Tool | Use | Role | Cost |
|---|---|---|---|
| Website events widget | SYNC (deployed) | Always-current events, machine-readable underneath | Free (we deploy) |
| Link-in-bio page | SYNC (deployed) | The mobile front door | Free (we deploy) |
| Email — their ESP (Mailchimp/Klaviyo-class) | STAGE · MEASURE | The $36–42-per-$1 channel, drafted into the tool they already have | Their plan |
| SMS — their existing tool | STAGE | One-idea sends; capture via door QR | Their plan |

## 6 · SEO mechanics (on-site)
| Resource | Use | Role | Cost |
|---|---|---|---|
| One crawlable URL per event · sitemap · IndexNow pings · review responses (GBP/Yelp) | SYNC (deployed) | The hygiene layer: changes submitted immediately, then MONITORED until crawled — indexing is the engine's decision (C-14) | Free |

## 7 · GEO — generative-engine optimization, done mechanically
| Resource | Use | Role | Cost |
|---|---|---|---|
| AI-crawler access (robots.txt: OAI-SearchBot for ChatGPT search · PerplexityBot · ClaudeBot; GPTBot managed separately as a TRAINING decision; Google-Extended governs Gemini/Vertex grounding, NOT Google Search) | SYNC (deployed) | Step zero — many sites silently block the crawlers whose answers they want to appear in | Free |
| Bing index + IndexNow | SYNC | IndexNow is NOTIFICATION, not guaranteed indexing (C-04: the Bing-share architecture assumption is retired; ChatGPT search eligibility runs through OAI-SearchBot) | Free |
| Retrieval-source presence (the §1–§2 databases) | SYNC | AI assistants draw heavily on these — most of GEO is feeding the sources (C-03) | Free |
| Entity data (Wikidata; Wikipedia only where notability is real) | SYNC (where eligible) | The knowledge-graph identity AI systems resolve against | Free |
| AI-answer monitoring (what ChatGPT/Gemini/Perplexity actually say) | MEASURE · drift-watch | Catches stale facts (the artist's old band name); GEO tools charge $29–500/mo for this | Free |
| llms.txt | SYNC (deployed, hedged) | Deployed because it costs nothing — flagged per our own research correction: ~97% of AI crawls ignore it; Google states no AI system uses it. A hedge, never the strategy | Free |

**Commercial note:** agencies sell §6–§7 as GEO/AEO retainers at
$1,500–$25,000/month (sources in `ONE_LIVE_B2A_GEO_MARKET_ASSESSMENT_v1.md`).
Every row is mechanical over data the agent already holds — free-tier work.

## 8 · Machine-readable layer & AI-answer consumers
| Resource | Use | Role | Cost |
|---|---|---|---|
| schema.org JSON-LD (MusicEvent · MusicVenue · Offer) | SYNC (deployed) | The structured layer most local businesses never publish (C-01: the measured 83% figure is restaurant/QSR, Uberall 2026) | Free |
| ICS / calendar feeds | READ · SYNC | Their calendar in; subscribed calendars out | Free |
| NAP consistency layer | SYNC · drift-watch | Name–address–phone–hours identical across every surface above | Free |
| AI assistants (ChatGPT · Gemini · Perplexity · voice) | fed indirectly | Read the surfaces and markup above | — |
| OneLive gated endpoint (agent-readable) | PHASE-C | The citable verified source for AI agents — behind the gate, never pay-to-rank | Free |

## 9 · Measurement — read back in their units
| Tool | Use | Role | Cost |
|---|---|---|---|
| UTM-tagged links · door/promo codes | MEASURE | Campaign → door attribution | Free |
| Platform analytics (IG/FB/GBP insights, ESP reports, GA4 if present) | MEASURE | Numbers in; plain-language weekly note out; feeds "what worked last time" | Free |

## 10 · OneLive-side machinery (ours, not theirs)
| Component | Type | Role |
|---|---|---|
| Claude API extraction | AI (read-only) | Weak-signal extraction from fetched public text — reads, never publishes |
| Evidence → gate → promote pipeline (PostgreSQL/Supabase · FastAPI/Celery) | Trust machine | Six-state corroboration (Truth States v2, 2026-08-01; running pipeline implements the original four until R-064 lands); disputed always shown; human-custodied promotion |
| /tonight PWA (Next.js) · Clerk auth · Sentry + dead-man monitoring | Platform | The consumer feed and ops rails |

**Standing rules across every row (canon):** their accounts stay theirs · no
percentage of ad spend at setup or during the free period (Tier-2 pricing per
the 2026-08-01 monetization direction) · nothing here affects OneLive ranking,
at any price · leave anytime and keep everything deployed.
