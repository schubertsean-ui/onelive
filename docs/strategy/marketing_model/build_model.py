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
@page { size: Letter landscape; margin: 1.4cm 1.6cm; @bottom-center { content: "Marketing Research & AI Agent Model v2 · CONFIDENTIAL DRAFT · page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #888; } }
body { font-family: "DejaVu Sans", sans-serif; font-size: 9.7pt; line-height: 1.5; color: #0b0b0b; }
h1 { font-size: 16pt; border-bottom: 3px solid #0b0b0b; padding-bottom: 6px; }
h2 { font-size: 11.5pt; border-bottom: 1px solid #bbb; padding-bottom: 3px; margin-top: 4px; page-break-after: avoid; }
h3 { font-size: 10pt; margin: 8px 0 3px 0; }
.sub { color: #52514e; font-size: 9.1pt; }
img.flow { width: 100%; max-height: 16.0cm; margin: 2px 0 2px 0; page-break-inside: avoid; display: block; }
.pgdesc { color: #52514e; font-size: 10.6pt; font-style: italic; margin: 0 0 4px 0; }
.guide { font-size: 13pt; } .guide li { margin: 8px 0; }
.guideintro { font-size: 13pt; }
img.phone { height: 15.8cm; width: auto; display: block; margin: 2px auto; }
table.duo { width: 100%; border-collapse: collapse; margin: 4px 0; page-break-inside: avoid; }
table.duo td { border: none; padding: 0 10px 0 0; vertical-align: top; background: none; font-size: 10.3pt; }
table.duo ul { margin: 2px 0 2px 13px; } table.duo li { margin-bottom: 1px; } table.duo p { margin: 4px 0; } table.duo h3 { margin: 0 0 3px 0; }
img.phone2 { height: 14.4cm; width: auto; display: block; margin: 0 auto; }
img.phone2sm { height: 13.1cm; width: auto; display: block; margin: 0 auto; }
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
<p class="sub">Structure (canon, 2026-08-01): WHAT · HOW · WHY · WHY THAT WHY MATTERS · EXPECTED OUTCOMES — then flows, mechanics, three worked examples, the full data model — and proof: the pipeline run on a real venue's real public data. Sources: the segment analysis and 23-category research; every load-bearing number carries an evidence badge and a row in the claim ledger (§11). Model v2 — evidence-badged per external review, 2026-08-01.</p>
<h2>Summary</h2>
<div class="rail"><b>Reading the evidence — every number in this document carries one badge:</b> <b>OBSERVED</b> (live campaign, records) · <b>DEMONSTRATED</b> (the system produced the artifact in a controlled run) · <b>ESTIMATED</b> (calculated from stated assumptions) · <b>EXTERNAL BENCHMARK</b> (cited third-party research, population preserved) · <b>PILOT TARGET</b> (success criterion, not a result) · <b>HYPOTHESIS</b> (to be tested). The three worked examples are <b>ILLUSTRATIVE — pilot targets, not observed results</b>; only the Continental Club section is DEMONSTRATED, and it excludes live publishing and measurement.</div>
<table>
<tr><th style="width:16%"></th><th>Statement</th></tr>
<tr><td><b>WHAT</b></td><td>A free-to-adopt agent for businesses, organizations, and artists. It does two distinct things: (1) MAINTENANCE — gets their basic presence correct everywhere and keeps it correct (one-time value, then background); (2) DEMAND GENERATION — produces and distributes marketing content (social posts, stories, carousels, events, emails, ads; structured data for search engines and AI assistants) from their own calendar, photos, and voice.</td></tr>
<tr><td><b>HOW</b></td><td>Paste one link → a complete PREVIEW in minutes, with no accounts connected. Activation is progressive: the owner connects only the channels they choose (some require platform authorization or approval — see the connector registry, §11). The agent learns four inputs — calendar, photo library, writing voice, brand — then drafts campaigns per event. Every send requires the owner's tap; ads run on their accounts and budgets. Data flows into OneLive as a verified first-party channel that still passes the gate.</td></tr>
<tr><td><b>WHY</b></td><td>The research shows the constraint is labor, not intent: owners have 5–15 hrs/wk of leftover attention, so only the easiest channel (social ads, indicative ~$5 return per $1) gets worked while the better-returning channels (email ~$36–42, local SEO ~$13 — benchmark roundups, not precise constants) and the surfaces AI reads sit idle. 83% of restaurant/QSR locations are invisible in AI recommendations (Uberall 2026) — the measured proxy for the wider local gap. <i>[EXTERNAL BENCHMARK — claim ledger C-01/C-06/C-07]</i></td></tr>
<tr><td><b>WHY THAT WHY MATTERS</b></td><td>Discovery is shifting to search+AI surfaces fed by exactly the layers nobody maintains, and every commercial fix is priced above the tiers that need it ($300–$5,000/mo). Removing the execution cost of the high-return channels changes the outcome without new spend. For OneLive: each adopting business adds verified supply, which improves the consumer feed, which increases the value of adopting — a compounding loop.</td></tr>
<tr><td><b>EXPECTED OUTCOMES</b></td><td><i>[PILOT TARGETS — illustrative, not observed]</i> For them: higher event attendance (bar: 38 tracked door entries from one campaign), list growth (winery: 41 signups vs 6 baseline/mo), sales (class sold out; 9 club conversions), at ~8–15 minutes/month of owner time and $0 cost during the initial free period. For OneLive: rising claimed-entity count, feed accuracy, and consumer reliance — measured via claim rate, coverage, and accuracy metrics. These become OBSERVED only after a live pilot with tracking and retained records.</td></tr>
</table>
<div class="rail"><b>Constraints (invariant unless marked):</b> every send requires the owner's tap · promotion runs on their accounts and budgets — no percentage of ad spend at setup or during the free period · the agent is a data source into OneLive's gate, never a publisher · nothing paid or free affects OneLive ranking · leaving preserves everything they built. <b>Pricing (direction, 2026-08-01):</b> Tier 1 maintenance &amp; standards is free permanently; Tier 2 ongoing demand generation is free for an initial period and may then be priced (flat monthly or percentage-based) below the documented market alternatives — model, rate, and timing are open founder decisions.</div>

<div class="pg"></div><h2>How to read this document</h2>
<p class="guideintro">This document makes one argument in three layers, in plain terms: the <b>research</b> (why local event marketing mostly doesn't happen, and what it costs), the <b>agent</b> (what OneLive builds for the businesses and artists who supply events), and the <b>proof</b> (the same machinery run on a real venue's public data). Fictional examples are stamped ILLUSTRATIVE; the one real run is stamped DEMONSTRATED; every number carries a claim-ledger badge.</p>
<ol class="guide">
<li><b>Summary</b> (previous pages) — the whole argument in five parts: what we do, how, why, why that why matters, and the outcomes we target.</li>
<li><b>§1 Both sides, summarized</b> — the research findings and the agent's answer on one canvas.</li>
<li><b>§2 The flows, at a glance</b> — everything the agent runs, in one map.</li>
<li><b>§3 How content is produced</b> (two pages) — the day-one cleanup, then the factory that runs for every event after.</li>
<li><b>§4 Where content goes</b> — every destination a verified fact fans out to, from Google to the AI assistants.</li>
<li><b>§5 Onboarding and the operating loop</b> — from the first pasted link to the weekly rhythm.</li>
<li><b>§6–8 Three worked examples</b> — a bar, a winery, a solo artist: each as the week the owner would feel, then the same week as a step-by-step process (the winery adds an offer-campaign page). All ILLUSTRATIVE.</li>
<li><b>§9 The full OneLive data model</b> — how a fact becomes verified truth and where that truth flows.</li>
<li><b>§10 (+10a–10f) Proof on a real venue</b> — the Continental Club, Austin: what the agent extracted, previewed, drafted, and structured from real public data. DEMONSTRATED; nothing was published.</li>
<li><b>§11 Appendix</b> — the connector registry (what each channel integration really is), resources, and the claim ledger behind every number.</li>
</ol>
<div class="pg"></div><h2>1 · Both sides, summarized</h2><p class="pgdesc">The research on the left, the agent on the right — one page to see how the findings map to what we build.</p><img class="flow" src="{img64('flow_glance.png')}"/>
<div class="pg"></div><h2>2 · The flows, at a glance</h2><p class="pgdesc">Every flow the agent runs — maintenance, content, distribution, measurement — in one map.</p><img class="flow" src="{img64('flow_highlevel.png')}"/>
<div class="pg"></div><h2>3 · Mechanics: how content is produced — day one</h2><p class="pgdesc">What happens in the first session: read, verify, fix, deploy the owned layer.</p><img class="flow" src="{img64('flow_factory1.png')}"/>
<div class="pg"></div><h2>3 · Mechanics: how content is produced — every event after</h2><p class="pgdesc">The content factory that runs for each new event: inputs, drafts, approvals, outputs.</p><img class="flow" src="{img64('flow_factory2.png')}"/>
<div class="pg"></div><h2>4 · Mechanics: where content goes</h2><p class="pgdesc">The destinations: search and maps, event databases, social, their own site and list, and the AI assistants that read it all.</p><img class="flow" src="{img64('flow_fanout.png')}"/>
<div class="pg"></div><h2>5 · Mechanics: onboarding and the operating loop</h2><p class="pgdesc">From one pasted link to a steady weekly rhythm — twelve steps, most of them the agent's.</p><img class="flow" src="{img64('flow_onboardloop.png')}"/>
<div class="pg"></div><h2>6 · Worked example 1 — bar / nightclub (categories 2 · 7)</h2><p class="pgdesc">A bar owner's week, as the message thread she'd actually see. Fictional, badged.</p><img class="flow" src="{img64('phone_bar.png')}"/>
<div class="pg"></div><h3>The process, with time and cost</h3><p class="pgdesc">The bar week as a process: each move, whose it was, where it showed up, the time and the cost.</p><img class="flow" src="{img64('flow_bar.png')}"/>
<div class="pg"></div><h2>7 · Worked example 2 — winery / brewery / distillery (category 3)</h2><p class="pgdesc">The same product on a tasting-room calendar: visits, bottles, classes. Fictional, badged.</p><img class="flow" src="{img64('phone_winery.png')}"/>
<div class="pg"></div><h3>The process, with time and cost</h3><p class="pgdesc">The winery month as a process — three revenue lines from one calendar.</p><img class="flow" src="{img64('flow_winery.png')}"/>
<div class="pg"></div><h3>The offer campaign in detail</h3><p class="pgdesc">One offer, end to end: drafted, approved, distributed, and measured at redemption. Fictional, badged.</p><img class="flow" src="{img64('flow_promo.png')}"/>
<div class="pg"></div><h2>8 · Worked example 3 — solo artist (categories 18–19)</h2><p class="pgdesc">A working musician: dates gathered from venues' calendars, a bio kept correct where AI answers. Fictional, badged.</p><img class="flow" src="{img64('phone_artist.png')}"/>
<div class="pg"></div><h3>The process, with time and cost</h3><p class="pgdesc">The artist's season as a process — the list and the documented draw are the assets.</p><img class="flow" src="{img64('flow_artist.png')}"/>
<div class="pg"></div><h2>9 · The full OneLive data model — ingestion, verification, distribution, and the loop</h2><p class="pgdesc">How a fact travels: read from public sources, corroborated, gated, then distributed as verified truth.</p><img class="flow" src="{img64('flow_model.png')}"/>

<div class="pg"></div><h2>10 · Proof, on a real venue — case study: The Continental Club, Austin</h2><p class="pgdesc">The same machinery pointed at a real venue's public data — what it found, what it drafted, and the honesty rules it kept.</p>
<p>The claim under test: paste one URL and the agent assembles the calendar, verifies the facts, catches drift, and drafts the campaign — before the owner does anything. The pipeline was run on a real venue's real public data, gathered 2026-08-01. Nothing was published; the venue is not affiliated and did not participate.</p>
<table>
<tr><th style="width:22%">Step</th><th>What happened</th><th style="width:32%">Production equivalent</th></tr>
<tr><td><b>Read pass</b></td><td>Public data gathered via search-index snapshots of the venue's official site and listing surfaces — Bandsintown, Songkick, Do512, Eventbrite, Yelp, austintexas.org, Spotify. (The build sandbox blocks direct page fetches; production reads the same public surfaces directly.)</td><td>F1 read pass: site + calendar + the pipes</td></tr>
<tr><td><b>Corroboration</b></td><td>Every fact cross-checked and assigned a truth state — CONFIRMED / LIKELY / UNVERIFIED observed in this run (six-state model per Truth States v2, 2026-08-01). One real cross-source error surfaced: Do512 labels the Aug 1 Saturday show 'Friday'.</td><td>Candidate → evidence → gate</td></tr>
<tr><td><b>Drafting</b></td><td>Preview card, engagement-canon campaign kit (video-first carousel + per-channel posts), and machine-readable markup generated from the verified facts and the venue's public voice.</td><td>Tier-2 content factory</td></tr>
<tr><td><b>Publishing</b></td><td><b>Nothing</b> — every artifact is a draft; the send button belongs to the owner. Ticket prices were not verifiable and are absent: the agent does not invent.</td><td>Owner-tapped distribution</td></tr>
</table>
<div class="rail"><b>Not proven here (named):</b> live posting via connected accounts (Phase-C, behind platform review); voice-learning from private libraries (public copy only); results measurement (needs a live campaign). Build items, not extraction claims — the data spine is what's demonstrated, and it ran on the first venue tried.</div>

<div class="pg"></div><h2>10a · The read pass — extraction, evidence, and confidence states</h2><p class="pgdesc">Every fact the agent extracted from the venue's public presence, with its sources and truth state — including one real error caught.</p><img class="flow" src="{img64('cs_extract.png')}"/>
<div class="pg"></div><h2>10b · The onboarding preview — the owner's minute-3 glance</h2><p class="pgdesc">What the venue would see three minutes after pasting a link: their real calendar, already assembled, one question flagged.</p><img class="flow" src="{img64('cs_preview.png')}"/>
<div class="pg"></div><h2>10c · The campaign kit — the carousel on the engagement canon</h2><p class="pgdesc">The five-card carousel the agent drafted for the real Aug 29 show — built on the engagement rules, never published.</p><img class="flow" src="{img64('cs_kit.png')}"/>
<div class="pg"></div><h2>10d · The same engagement spine on every channel</h2><p class="pgdesc">The one idea repackaged per channel: reel, event page, Google post, email, text.</p><img class="flow" src="{img64('cs_channels.png')}"/>
<div class="pg"></div><h2>10e · The machine-readable layer</h2><p class="pgdesc">The structured data search engines and AI assistants receive — the layer most venues never publish.</p><img class="flow" src="{img64('cs_machine.png')}"/>
<div class="pg"></div><h2>10f · Day one, as the owner would see it</h2><p class="pgdesc">The whole first day as one message thread: found, verified, fixed, deployed, one question asked.</p><img class="flow" src="{img64('cs_thread.png')}"/>

<div class="pg"></div><h2>11 · Appendix — connector capability registry, resources & claim ledger</h2><p class="pgdesc">The receipts: what each channel connection really is today, every tool and surface by type, and the ledger behind every number.</p>
<p><b>Capability classes replace the earlier flat READ/SYNC/STAGE legend</b> (platforms differ materially in authorization, moderation, terms, and cost — marketing copy never outruns the registry, `docs/strategy/ONE_LIVE_CONNECTOR_REGISTRY_v1.md`): <b>DIRECT PUBLISH</b> "Connected — publishes after your approval" · <b>AUTHORIZED SYNC</b> "Connected — kept current" · <b>NATIVE HANDOFF</b> "Ready — one tap to finish" · <b>ASSISTED SUBMISSION</b> "Submitted — awaiting review" · <b>READ &amp; MONITOR</b> "Monitored" · <b>PARTNER-DEPENDENT</b> "Planned — partner access required". Status today for every connector: <b>PLANNED</b> — nothing is live; a connector is presented as live only after its sandbox tests pass. Publication is a state machine (DRAFTED → APPROVED → SUBMITTED → ACCEPTED → PUBLIC → INDEXED, with REJECTED/MODERATED/EXPIRED/AUTH-LOST/RETRYING) and every write returns a receipt; "published" is never claimed from an API success alone.</p>
<table>
<tr><th>Connector</th><th style="width:22%">Capability class (target)</th><th style="width:20%">Authorization</th><th>Constraints worth knowing</th></tr>
<tr><td>OneLive listing · hosted event pages · site widget + JSON-LD · link-in-bio</td><td>DIRECT PUBLISH (our surfaces)</td><td>claim verification; site install</td><td>unique URL per event; validated markup; visible page must match structured data; gated as ever</td></tr>
<tr><td>Google Business Profile (posts · hours · events)</td><td>DIRECT PUBLISH</td><td>owner OAuth, registered app</td><td>supported API; account-type eligibility varies</td></tr>
<tr><td>Bing Places + IndexNow</td><td>AUTHORIZED SYNC</td><td>site verification</td><td>IndexNow is notification — crawling/indexing not guaranteed</td></tr>
<tr><td>Apple Business Connect</td><td>PARTNER-DEPENDENT → AUTHORIZED SYNC</td><td>Apple partner approval + delegation</td><td>NATIVE HANDOFF until partner status</td></tr>
<tr><td>Yelp</td><td>READ &amp; MONITOR; listing mgmt PARTNER-DEPENDENT</td><td>Yelp partner program (per-location, may bill)</td><td>some updates moderated up to ~2 weeks — never "instant"</td></tr>
<tr><td>Nextdoor</td><td>PARTNER-DEPENDENT → DIRECT PUBLISH</td><td>API approval + authenticated business profile</td><td>content attributable to the business, not OneLive</td></tr>
<tr><td>Foursquare</td><td>READ &amp; MONITOR; contribution PARTNER-DEPENDENT</td><td>API contract</td><td>pricing beyond small free tier</td></tr>
<tr><td>Bandsintown (artist)</td><td>AUTHORIZED SYNC</td><td>artist claims their page</td><td>artist edition</td></tr>
<tr><td>Songkick</td><td>READ &amp; MONITOR only — HELD</td><td>—</td><td>restrictive noncommercial API terms; <b>legal review required before any product use (founder-crucial)</b>; never a write surface</td></tr>
<tr><td>City/press calendars · aggregators</td><td>ASSISTED SUBMISSION (+READ drift-watch)</td><td>per-site forms/accounts</td><td>editorial review timing is theirs</td></tr>
<tr><td>Instagram · Facebook Page posts</td><td>DIRECT PUBLISH</td><td>professional account/Page + Meta app review + OAuth</td><td>publishing limits, token expiry; NATIVE HANDOFF (v1 boost recipe) before review. Facebook EVENTS tracked separately: PARTNER-DEPENDENT</td></tr>
<tr><td>YouTube / Shorts</td><td>DIRECT PUBLISH</td><td>owner OAuth</td><td>unverified API projects may be limited to private pending audit</td></tr>
<tr><td>Meta boost (their ad account)</td><td>NATIVE HANDOFF (v1) → DIRECT (Phase-C)</td><td>none (v1) / ad-account OAuth</td><td>their budget, their cap; no % of spend</td></tr>
<tr><td>Email (their ESP) · SMS (their tool)</td><td>DIRECT PUBLISH via their account</td><td>their credentials; consent lists</td><td>suppression/consent respected</td></tr>
<tr><td>Ticketing (Eventbrite/Tock-class)</td><td>READ &amp; link-through</td><td>none (public links)</td><td>never brokered</td></tr>
<tr><td>AI crawlers (robots.txt)</td><td>AUTHORIZED SYNC (config)</td><td>site control</td><td>OAI-SearchBot = ChatGPT search · GPTBot = training (managed separately) · Google-Extended governs Gemini/Vertex grounding, NOT Google Search inclusion · PerplexityBot, ClaudeBot</td></tr>
<tr><td>Wikidata · llms.txt</td><td>ASSISTED SUBMISSION · deployed hedge</td><td>site control</td><td>Wikidata only where notability is real; llms.txt largely ignored by AI crawls (C-05) — hedge, not strategy</td></tr>
<tr><td>Measurement (UTM · door/QR codes · platform analytics)</td><td>READ &amp; MONITOR</td><td>their analytics access</td><td>attribution is classified (tracked/attributed/assisted/modeled/incremental) — never presented as causal lift without a comparison</td></tr>
</table>
<div class="rail"><b>Claim ledger:</b> every load-bearing number above and in the body has a row in `docs/strategy/CLAIM_LEDGER.md` (source, population, approved wording, badge, review date). Retired wordings (C-03, C-04): the unsourced ChatGPT source-share percentages and the Bing-share architecture assumption — replaced by documented mechanisms (OAI-SearchBot; database presence). <b>Standing rules (canon):</b> their accounts stay theirs · no percentage of ad spend at setup or during the free period · nothing paid or free affects OneLive ranking · leave anytime, keep everything deployed.</div>
"""

html = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"
HTML(string=html).write_pdf("Marketing_Research_and_AI_Agent_Model_v2.pdf")
from pypdf import PdfReader
r = PdfReader("Marketing_Research_and_AI_Agent_Model_v2.pdf"); t = "".join(p.extract_text() for p in r.pages)
for probe in ["MATTERS", "EXPECTED", "free permanently", "initial period", "Worked example", "data model"]:
    assert probe in t, probe
print("pages:", len(r.pages), "- ok")
