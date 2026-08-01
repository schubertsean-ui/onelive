# -*- coding: utf-8 -*-
from weasyprint import HTML
import base64, pathlib

def img64(p): return "data:image/png;base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()

src = open("build_paper.py").read()
ns = {}
exec(src[:src.index("def esc")], ns)
CATS = {c["n"].split(" · ")[0]: c for c in ns["CATS"]}
bar, prod, artist = CATS["2"], CATS["3"], CATS["19"]

def briefblock(c, fit, socials, n=4):
    ch = "".join(f"<li>{x}</li>" for x in c["ch"][:n]); gr = "".join(f"<li>{x}</li>" for x in c["gr"][:n])
    return f"""<p><b>Documented challenges (category research)</b></p><ul>{ch}</ul><p><b>Documented goals</b></p><ul>{gr}</ul><p><b>Fit:</b> {fit}</p><p><b>Content the agent produces for this segment:</b> {socials}</p>"""

css = """
@page { size: Letter landscape; margin: 1.4cm 1.6cm; @bottom-center { content: "Marketing Research & AI Agent Model v1 · CONFIDENTIAL DRAFT · page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #888; } }
body { font-family: "DejaVu Sans", sans-serif; font-size: 9.7pt; line-height: 1.5; color: #0b0b0b; }
h1 { font-size: 16pt; border-bottom: 3px solid #0b0b0b; padding-bottom: 6px; }
h2 { font-size: 11.5pt; border-bottom: 1px solid #bbb; padding-bottom: 3px; margin-top: 4px; page-break-after: avoid; }
h3 { font-size: 10pt; margin: 8px 0 3px 0; }
.sub { color: #52514e; font-size: 9.1pt; }
img.flow { width: 100%; max-height: 16.9cm; margin: 4px 0 2px 0; page-break-inside: avoid; display: block; }
img.phone { height: 16.6cm; width: auto; display: block; margin: 4px auto; }
table.duo { width: 100%; border-collapse: collapse; margin: 4px 0; page-break-inside: avoid; }
table.duo td { border: none; padding: 0 10px 0 0; vertical-align: top; background: none; font-size: 10.3pt; }
table.duo ul { margin: 2px 0 2px 13px; } table.duo li { margin-bottom: 1px; } table.duo p { margin: 4px 0; } table.duo h3 { margin: 0 0 3px 0; }
img.phone2 { height: 15.0cm; width: auto; display: block; margin: 0 auto; }
img.phone2sm { height: 13.6cm; width: auto; display: block; margin: 0 auto; }
.cap { font-size: 9pt; color: #333; margin: 3px 0 0 0; }
.pg { page-break-before: always; }
ul { margin: 3px 0 3px 15px; } li { margin-bottom: 2px; }
.rail { background: #f4f4f2; border-left: 4px solid #2a78d6; padding: 7px 11px; font-size: 9.4pt; margin: 7px 0; }
table { border-collapse: collapse; width: 100%; margin: 7px 0; font-size: 8.9pt; }
th { background: #0b0b0b; color: #fff; padding: 5px 7px; text-align: left; }
td { border: 0.5pt solid #aaa; padding: 5px 7px; vertical-align: top; }
tr:nth-child(even) td { background: #f4f4f2; }
table.two td { border: 0.5pt solid #ccc; }
"""

body = f"""
<h1>Marketing Research &amp; AI Agent Model</h1>
<p class="sub">Structure (canon, 2026-08-01): WHAT · HOW · WHY · WHY THAT WHY MATTERS · EXPECTED OUTCOMES — then flows, mechanics, three worked examples, the full data model — and proof: the pipeline run on a real venue's real public data. Sources: the segment analysis and 23-category research. Model v1.</p>
<h2>Summary</h2>
<table>
<tr><th style="width:16%"></th><th>Statement</th></tr>
<tr><td><b>WHAT</b></td><td>A free-to-adopt agent for businesses, organizations, and artists. It does two distinct things: (1) MAINTENANCE — gets their basic presence correct everywhere and keeps it correct (one-time value, then background); (2) DEMAND GENERATION — produces and distributes marketing content (social posts, stories, carousels, events, emails, ads; structured data for search engines and AI assistants) from their own calendar, photos, and voice.</td></tr>
<tr><td><b>HOW</b></td><td>Setup from one pasted URL (≤3 taps). The agent learns four inputs — calendar, photo library, writing voice, brand — then drafts campaigns per event. Every send requires the owner's tap; ads run on their accounts and budgets. Data flows into OneLive as a verified first-party channel that still passes the gate.</td></tr>
<tr><td><b>WHY</b></td><td>The research shows the constraint is labor, not intent: owners have 5–15 hrs/wk of leftover attention, so only the easiest channel (social, ~$5 return per $1) gets worked while the best channels (email $36–42, local SEO ~$13) and the surfaces AI reads sit idle. 83% of local businesses are invisible in AI answers.</td></tr>
<tr><td><b>WHY THAT WHY MATTERS</b></td><td>Discovery is shifting to search+AI surfaces fed by exactly the layers nobody maintains, and every commercial fix is priced above the tiers that need it ($300–$5,000/mo). Removing the execution cost of the high-return channels changes the outcome without new spend. For OneLive: each adopting business adds verified supply, which improves the consumer feed, which increases the value of adopting — a compounding loop.</td></tr>
<tr><td><b>EXPECTED OUTCOMES</b></td><td>For them (worked examples below; est.): higher event attendance (bar: 38 tracked door entries from one campaign), list growth (winery: 41 signups vs 6 baseline/mo), sales (class sold out; 9 club conversions), at ~8–15 minutes/month of owner time and $0 cost during the initial free period. For OneLive: rising claimed-entity count, feed accuracy, and consumer reliance — measured via claim rate, coverage, and accuracy metrics.</td></tr>
</table>
<div class="rail"><b>Constraints (invariant unless marked):</b> every send requires the owner's tap · promotion runs on their accounts and budgets — no percentage of ad spend at setup or during the free period · the agent is a data source into OneLive's gate, never a publisher · nothing paid or free affects OneLive ranking · leaving preserves everything they built. <b>Pricing (direction, 2026-08-01):</b> Tier 1 maintenance &amp; standards is free permanently; Tier 2 ongoing demand generation is free for an initial period and may then be priced (flat monthly or percentage-based) below the documented market alternatives — model, rate, and timing are open founder decisions.</div>
<div class="pg"></div><h2>1 · Both sides, summarized</h2><img class="flow" src="{img64('flow_glance.png')}"/>
<div class="pg"></div><h2>2 · The flows, at a glance</h2><img class="flow" src="{img64('flow_highlevel.png')}"/>
<div class="pg"></div><h2>3 · Mechanics: how content is produced — day one</h2><img class="flow" src="{img64('flow_factory1.png')}"/>
<div class="pg"></div><h2>3 · Mechanics: how content is produced — every event after</h2><img class="flow" src="{img64('flow_factory2.png')}"/>
<div class="pg"></div><h2>4 · Mechanics: where content goes</h2><img class="flow" src="{img64('flow_fanout.png')}"/>
<div class="pg"></div><h2>5 · Mechanics: onboarding and the operating loop</h2><img class="flow" src="{img64('flow_onboardloop.png')}"/>
<div class="pg"></div><h2>6 · Worked example 1 — bar / nightclub (categories 2 · 7)</h2><img class="flow" src="{img64('phone_bar.png')}"/>
<div class="pg"></div><h3>The process, with time and cost</h3><img class="flow" src="{img64('flow_bar.png')}"/>
<div class="pg"></div><h2>7 · Worked example 2 — winery / brewery / distillery (category 3)</h2><img class="flow" src="{img64('phone_winery.png')}"/>
<div class="pg"></div><h3>The process, with time and cost</h3><img class="flow" src="{img64('flow_winery.png')}"/>
<div class="pg"></div><h3>The offer campaign in detail</h3><img class="flow" src="{img64('flow_promo.png')}"/>
<div class="pg"></div><h2>8 · Worked example 3 — solo artist (categories 18–19)</h2><img class="flow" src="{img64('phone_artist.png')}"/>
<div class="pg"></div><h3>The process, with time and cost</h3><img class="flow" src="{img64('flow_artist.png')}"/>
<div class="pg"></div><h2>9 · The full OneLive data model — ingestion, verification, distribution, and the loop</h2><img class="flow" src="{img64('flow_model.png')}"/>

<div class="pg"></div><h2>10 · Proof, on a real venue — case study: The Continental Club, Austin</h2>
<p>The claim under test: paste one URL and the agent assembles the calendar, verifies the facts, catches drift, and drafts the campaign — before the owner does anything. The pipeline was run on a real venue's real public data, gathered 2026-08-01. Nothing was published; the venue is not affiliated and did not participate.</p>
<table>
<tr><th style="width:22%">Step</th><th>What happened</th><th style="width:32%">Production equivalent</th></tr>
<tr><td><b>Read pass</b></td><td>Public data gathered via search-index snapshots of the venue's official site and listing surfaces — Bandsintown, Songkick, Do512, Eventbrite, Yelp, austintexas.org, Spotify. (The build sandbox blocks direct page fetches; production reads the same public surfaces directly.)</td><td>F1 read pass: site + calendar + the pipes</td></tr>
<tr><td><b>Corroboration</b></td><td>Every fact cross-checked and assigned a state — CONFIRMED / LIKELY / UNVERIFIED — the gate's 4-state logic. One real cross-source error surfaced: Do512 labels the Aug 1 Saturday show 'Friday'.</td><td>Candidate → evidence → gate</td></tr>
<tr><td><b>Drafting</b></td><td>Preview card, engagement-canon campaign kit (video-first carousel + per-channel posts), and machine-readable markup generated from the verified facts and the venue's public voice.</td><td>Tier-2 content factory</td></tr>
<tr><td><b>Publishing</b></td><td><b>Nothing</b> — every artifact is a draft; the send button belongs to the owner. Ticket prices were not verifiable and are absent: the agent does not invent.</td><td>Owner-tapped distribution</td></tr>
</table>
<div class="rail"><b>Not proven here (named):</b> live posting via connected accounts (Phase-C, behind platform review); voice-learning from private libraries (public copy only); results measurement (needs a live campaign). Build items, not extraction claims — the data spine is what's demonstrated, and it ran on the first venue tried.</div>

<div class="pg"></div><h2>10a · The read pass — extraction, evidence, and confidence states</h2><img class="flow" src="{img64('cs_extract.png')}"/>
<div class="pg"></div><h2>10b · The onboarding preview — the owner's minute-3 glance</h2><img class="flow" src="{img64('cs_preview.png')}"/>
<div class="pg"></div><h2>10c · The campaign kit — the carousel on the engagement canon</h2><img class="flow" src="{img64('cs_kit.png')}"/>
<div class="pg"></div><h2>10d · The same engagement spine on every channel</h2><img class="flow" src="{img64('cs_channels.png')}"/>
<div class="pg"></div><h2>10e · The machine-readable layer</h2><img class="flow" src="{img64('cs_machine.png')}"/>
<div class="pg"></div><h2>10f · Day one, as the owner would see it</h2><img class="flow" src="{img64('cs_thread.png')}"/>

<div class="pg"></div><h2>11 · Appendix — resources, tools &amp; surfaces, organized by type</h2>
<p>Everything the agent reads, feeds, stages, or runs on. <b>Legend — how the agent touches it:</b> <b>READ</b> = source it extracts from · <b>SYNC</b> = kept correct automatically (Tier 1) · <b>STAGE</b> = content drafted, ships only on the owner's tap (Tier 2) · <b>MEASURE</b> = results read back · <b>PHASE-C</b> = later, behind platform review. Costs shown are the business's, not ours.</p>

<h3>Search &amp; maps — where high-intent discovery happens</h3>
<table>
<tr><th style="width:24%">Surface</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>Google Business Profile (Search · Maps · 'Things to do' · posts)</td><td>READ · SYNC · STAGE</td><td>The highest-intent local surface; event posts + hours + 'Buy tickets' buttons; 76% of local searchers visit within 24h</td><td>Free</td></tr>
<tr><td>Bing Places</td><td>SYNC</td><td>Feeds Bing/Copilot answers</td><td>Free</td></tr>
<tr><td>Apple Maps (Apple Business Connect)</td><td>READ · SYNC</td><td>Hours/place data for the iPhone half of the audience — the winter-hours drift class</td><td>Free</td></tr>
</table>

<h3>Discovery apps &amp; event databases — what AI tools actually pull from</h3>
<table>
<tr><th style="width:24%">Surface</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>Yelp</td><td>READ · SYNC</td><td>NAP + hours consistency; a major AI-recommendation source (~70% of ChatGPT local draws on Yelp/Foursquare-class data)</td><td>Free listing</td></tr>
<tr><td>Foursquare</td><td>READ · SYNC</td><td>The location database many AI stacks license</td><td>Free</td></tr>
<tr><td>Bandsintown · Songkick</td><td>READ · SYNC</td><td>Artist/venue event databases; concert-discovery apps and artist-follow alerts</td><td>Free</td></tr>
<tr><td>City guides (Do512-class, per city)</td><td>READ · drift-watch</td><td>Local what's-on surfaces — the layer where the case study caught the real 'Friday' mislabel</td><td>Free</td></tr>
</table>

<h3>Their ticketing &amp; commerce — always THEIR accounts, never brokered</h3>
<table>
<tr><th style="width:24%">Tool</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>Eventbrite · Tock · Ticketmaster-class (whichever they already use)</td><td>READ · link-through</td><td>Tickets/reservations stay on their existing platform; the agent attaches the links everywhere</td><td>Their existing fees</td></tr>
<tr><td>Their POS / door codes / QR cards</td><td>MEASURE</td><td>Redemption + attendance attribution without new hardware</td><td>$0</td></tr>
</table>

<h3>Social — staged by the agent, sent on their tap</h3>
<table>
<tr><th style="width:24%">Surface</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>Instagram (feed · story · carousel · reel · Collab posts · licensed audio)</td><td>READ · STAGE</td><td>The engagement-canon carousel/reel with their own footage and audio; Collab posts double reach with the artist</td><td>Free organic</td></tr>
<tr><td>Facebook (events · page posts)</td><td>STAGE</td><td>Event objects with video attached; the invite graph</td><td>Free organic</td></tr>
<tr><td>Meta boosts (their ad account, their cap)</td><td>STAGE (2-tap recipe)</td><td>v1 needs NO Meta API — recipe executed in their own app; no fees, no percentage of spend</td><td>Their optional budget ($20–60 typical)</td></tr>
</table>

<h3>Their own property — the owned layer the agent keeps alive</h3>
<table>
<tr><th style="width:24%">Tool</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>Website events widget</td><td>SYNC (deployed)</td><td>Always-current events on their site, machine-readable underneath</td><td>Free (we deploy)</td></tr>
<tr><td>Link-in-bio page</td><td>SYNC (deployed)</td><td>The mobile front door, always pointing at the next show</td><td>Free (we deploy)</td></tr>
<tr><td>Email — their ESP (Mailchimp/Klaviyo-class)</td><td>STAGE · MEASURE</td><td>The $36–42-per-$1 channel; drafts into the tool they already have</td><td>Their existing plan ($0–300/mo)</td></tr>
<tr><td>SMS — their existing texting tool</td><td>STAGE</td><td>One-idea sends to the list; capture via QR at the door</td><td>Their existing plan</td></tr>
</table>

<h3>The machine-readable / AI-answer layer — what gets deployed under the hood</h3>
<table>
<tr><th style="width:24%">Resource</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>schema.org JSON-LD (MusicEvent · MusicVenue · Offer)</td><td>SYNC (deployed)</td><td>The structured layer 83% of local businesses never publish — event rich results + AI citability (Artifact 10e)</td><td>Free</td></tr>
<tr><td>ICS / calendar feeds</td><td>READ · SYNC</td><td>Their calendar in, subscribed calendars out</td><td>Free</td></tr>
<tr><td>NAP consistency layer</td><td>SYNC · drift-watch</td><td>Name–address–phone–hours held identical across every surface above</td><td>Free</td></tr>
<tr><td>AI assistants (ChatGPT · Gemini · Perplexity · voice)</td><td>fed indirectly</td><td>Read the surfaces and markup above — the 45%-of-consumers answer layer</td><td>—</td></tr>
<tr><td>OneLive gated endpoint (agent-readable)</td><td>PHASE-C</td><td>The citable, verified source for AI agents — behind the gate, never pay-to-rank</td><td>Free</td></tr>
</table>

<h3>SEO — the wider set of posting &amp; indexing surfaces (beyond the big three)</h3>
<table>
<tr><th style="width:24%">Surface</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>Nextdoor Business</td><td>SYNC · STAGE</td><td>The neighborhood layer — local events reach the streets that actually walk in</td><td>Free</td></tr>
<tr><td>City &amp; press event calendars (Austin Chronicle-class alt-weeklies · visitor bureaus like austintexas.org · community calendars)</td><td>STAGE (submit)</td><td>Free editorial surfaces with real domain authority — both foot traffic AND backlinks; the case-study read found the venue on two of these</td><td>Free</td></tr>
<tr><td>Event aggregators (AllEvents-class)</td><td>SYNC</td><td>Long-tail event indexing that search engines crawl</td><td>Free</td></tr>
<tr><td>YouTube / Shorts</td><td>STAGE</td><td>The reel cut re-posted — video results in Google search; their channel, their tap</td><td>Free</td></tr>
<tr><td>Segment surfaces: TripAdvisor (venues · wineries) · Untappd (breweries) · Vivino (wineries) · Bandcamp/Spotify/SoundCloud profiles (artists)</td><td>SYNC · drift-watch</td><td>Category-specific discovery where their buyers already search — matched to the 23-segment canon</td><td>Free</td></tr>
<tr><td>On-site SEO mechanics: one crawlable URL per event · sitemap · IndexNow pings · review responses on GBP/Yelp</td><td>SYNC (deployed)</td><td>The hygiene layer that makes everything above indexable the hour it changes</td><td>Free</td></tr>
</table>

<h3>GEO — generative-engine optimization (the AI-answer discipline, done mechanically)</h3>
<table>
<tr><th style="width:24%">Resource</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>AI-crawler access (robots.txt allowances: GPTBot · ClaudeBot · PerplexityBot · Google-Extended)</td><td>SYNC (deployed)</td><td>Step zero of GEO — many sites silently block the crawlers whose answers they want to appear in</td><td>Free</td></tr>
<tr><td>Bing index + IndexNow</td><td>SYNC</td><td>ChatGPT and Copilot retrieval runs largely on Bing's index — being fresh there IS ChatGPT visibility</td><td>Free</td></tr>
<tr><td>Retrieval-source presence (Yelp · Foursquare · GBP · the databases above)</td><td>SYNC</td><td>~70% of AI local recommendations draw on these — GEO is mostly feeding the sources, done in the earlier tables</td><td>Free</td></tr>
<tr><td>Entity data (Wikidata; Wikipedia only where notability is real)</td><td>SYNC (where eligible)</td><td>The knowledge-graph identity AI systems resolve entities against</td><td>Free</td></tr>
<tr><td>AI-answer monitoring (what ChatGPT/Gemini/Perplexity actually say about them)</td><td>MEASURE · drift-watch</td><td>The check that caught the artist's stale band name; re-publishes correct facts when answers drift</td><td>Free (GEO tools charge $29–500/mo for this)</td></tr>
<tr><td>llms.txt</td><td>SYNC (deployed, hedged)</td><td>Deployed because it costs nothing — flagged honestly: our research found ~97% of AI crawls ignore it and Google states no AI system uses it. A hedge, never the strategy</td><td>Free</td></tr>
</table>
<p><b>Why this table matters commercially:</b> agencies sell exactly this list as GEO/AEO retainers at $1,500–$25,000/month. Every row above is mechanical over data the agent already holds — it ships in the free tier, which is the arbitrage the whole document describes.</p>

<h3>Measurement — read back in their units</h3>
<table>
<tr><th style="width:24%">Tool</th><th style="width:14%">Agent's use</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>UTM-tagged links · door/promo codes</td><td>MEASURE</td><td>Campaign → door attribution ('38 used MALA')</td><td>Free</td></tr>
<tr><td>Platform analytics (IG/FB/GBP insights, their ESP reports, GA4 if present)</td><td>MEASURE</td><td>Raw numbers in; plain-language weekly note out; feeds 'what worked last time'</td><td>Free</td></tr>
</table>

<h3>OneLive-side machinery (ours, not theirs — listed for completeness)</h3>
<table>
<tr><th style="width:24%">Component</th><th style="width:14%">Type</th><th>Role</th><th style="width:16%">Cost to business</th></tr>
<tr><td>Claude API extraction</td><td>AI (read-only)</td><td>Weak-signal extraction from fetched public text — reads, never publishes</td><td>$0 (our COGS)</td></tr>
<tr><td>Evidence → gate → promote pipeline (PostgreSQL/Supabase · FastAPI/Celery)</td><td>Trust machine</td><td>4-state corroboration; disputed always shown; human-custodied promotion</td><td>$0</td></tr>
<tr><td>/tonight PWA (Next.js) · Clerk auth · Sentry + dead-man monitoring</td><td>Platform</td><td>The consumer feed and ops rails the verified data flows into</td><td>$0</td></tr>
</table>
<div class="rail"><b>Standing rules across every row:</b> their accounts stay theirs · no percentage of ad spend at setup or during the free period · nothing here affects OneLive ranking, at any price · leave anytime and keep everything deployed.</div>
"""

html = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"
HTML(string=html).write_pdf("Marketing_Research_and_AI_Agent_Model_v1.pdf")
from pypdf import PdfReader
r = PdfReader("Marketing_Research_and_AI_Agent_Model_v1.pdf"); t = "".join(p.extract_text() for p in r.pages)
for probe in ["MATTERS", "EXPECTED", "free permanently", "initial period", "Worked example", "data model"]:
    assert probe in t, probe
print("pages:", len(r.pages), "- ok")
