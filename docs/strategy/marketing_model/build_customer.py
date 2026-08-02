# -*- coding: utf-8 -*-
# Customer/product story — 12 pages, per the external review's recommended sequence.
from weasyprint import HTML
import base64, pathlib

def img64(p): return "data:image/png;base64," + base64.b64encode(pathlib.Path(p).read_bytes()).decode()

css = """
@page { size: Letter landscape; margin: 1.2cm 1.6cm;
  @bottom-center { content: "OneLive — customer story v1 · CONFIDENTIAL DRAFT · page " counter(page) " of " counter(pages); font-size: 7.5pt; color: #888; } }
body { font-family: "DejaVu Sans", sans-serif; font-size: 12.4pt; line-height: 1.6; color: #0b0b0b; }
h1 { font-size: 30pt; border-bottom: none; margin: 6px 0 6px 0; }
h2 { font-size: 17pt; border-bottom: 1px solid #bbb; padding-bottom: 3px; margin-top: 8px; page-break-after: avoid; }
.big { font-size: 18pt; color: #0b0b0b; }
.sub { color: #52514e; font-size: 12.4pt; }
img.flow { width: 100%; max-height: 16.9cm; margin: 4px 0 2px 0; page-break-inside: avoid; display: block; }
.pg { page-break-before: always; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 11.2pt; }
table.compact { font-size: 10.4pt; }
table.compact td, table.compact th { padding: 4px 8px; }
th { background: #0b0b0b; color: #fff; padding: 5px 9px; text-align: left; }
td { border: 0.5pt solid #aaa; padding: 5px 9px; vertical-align: top; }
tr:nth-child(even) td { background: #f4f4f2; }
.rail { background: #f4f4f2; border-left: 4px solid #2a78d6; padding: 10px 14px; font-size: 11.6pt; margin: 8px 0; }
.warn { background: #fdeecb; border-left: 4px solid #eda100; padding: 12px 16px; font-size: 12pt; margin: 12px 0; }
.tiles { display: flex; gap: 12px; margin: 10px 0; }
.tile { flex: 1; border: 1px solid #ddd; border-top: 5px solid #2a78d6; padding: 10px 12px; background: #f9f9f7; }
.tile .n { font-size: 16pt; font-weight: bold; }
.tile .t { font-size: 11.8pt; color: #52514e; margin-top: 4px; }
ul { margin: 5px 0 5px 17px; } li { margin-bottom: 4px; }
.duo { display: flex; gap: 16px; } .duo > div { flex: 1; }
"""

body = f"""
<div style="margin-top:2.2cm">
<h1>One calendar in. More people through the door.</h1>
<p class="big">OneLive turns the event dates, photos, and voice you already have into accurate listings, ready-to-send campaigns, and measurable attendance — without another marketing dashboard. You keep control of every account, budget, and send.</p>
</div>
<div class="tiles">
<div class="tile"><div class="n">Hours back</div><div class="t">the repetitive channel work happens for you; you approve it in minutes</div></div>
<div class="tile"><div class="n">Right, everywhere</div><div class="t">dates, times, and hours stay correct on the places people actually check</div></div>
<div class="tile"><div class="n">An audience you own</div><div class="t">every campaign grows your list — it leaves with you, always</div></div>
<div class="tile"><div class="n">Results at the door</div><div class="t">attendance, signups, and sales — reported separately from likes</div></div>
</div>
<div class="rail"><b>Your accounts. Your audience. Your budget. Your approval.</b> Promotional sends require your tap. Nothing you pay for (or get free) ever changes how OneLive ranks events. Leave anytime and keep everything.</div>

<div class="pg"></div><h2>The problem — your events already exist; their marketing doesn't</h2>
<p class="big">You keep one calendar. The world checks a dozen places.</p>
<p>Every event you run has to be re-entered on your website, Google, the map apps, the event sites, your socials, and your email tool — or more often, it isn't. What actually happens in most rooms:</p>
<ul>
<li><b>One calendar, many channels:</b> the event lives on a chalkboard and one Instagram story; everywhere else is silent or stale.</li>
<li><b>Repeated manual entry:</b> the same date typed five times — or zero times after a busy week.</li>
<li><b>Stale facts:</b> last winter's hours on a map app; a promoter's flyer with the wrong start time; customers who stop trusting what they read.</li>
<li><b>Generic or missing promotion:</b> the best-returning channels (your email list, your search presence) sit unused because they take the most work.</li>
<li><b>No measurement:</b> likes get counted; nobody knows what filled the room.</li>
</ul>
<p>The constraint isn't intent or even money — it's hours. Marketing help that fixes this is priced for companies with marketing departments. OneLive's answer: do the repetitive layer for you, and leave every decision yours.</p>

<div class="pg"></div><h2>How it works</h2>
<img class="flow" src="{img64('flow_sixstep.png')}"/>

<div class="pg"></div><h2>Before and after</h2>
<table>
<tr><th style="width:50%">Before OneLive</th><th>With OneLive</th></tr>
<tr><td>Re-enter every event on every site — or skip it</td><td>Maintain one calendar, the one you already keep</td></tr>
<tr><td>Several logins, several dashboards</td><td>One approval thread that already did the work</td></tr>
<tr><td>Inconsistent dates, times, and hours across the web</td><td>An evidence-backed event record, kept consistent on connected channels</td></tr>
<tr><td>Generic promotion, or none</td><td>A complete event-specific campaign in your voice, staged for your tap</td></tr>
<tr><td>Followers on platforms you don't control</td><td>A growing email/text list you own and keep</td></tr>
<tr><td>Reach and likes</td><td>Attendance, signups, reservations, and sales — measured</td></tr>
</table>
<div class="rail">You can stop at any step and keep what it gave you: the preview, the corrected listings, the widget, the list. There is no lock-in by design.</div>

<div class="pg"></div><h2>A week with OneLive — Dana's bar</h2>
<img class="flow" src="{img64('phone_bar.png')}"/>

<div class="pg"></div><h2>The same week, step by step</h2>
<img class="flow" src="{img64('flow_bar.png')}"/>

<div class="pg"></div><h2>Who does what</h2>
<table>
<tr><th style="width:50%">You</th><th>OneLive</th></tr>
<tr><td>Add events to your calendar — the way you already do</td><td>Sees the change, assembles the event record, checks it against every public source</td></tr>
<tr><td>Answer the occasional question ("9pm or 10pm?")</td><td>Finds the conflicts worth asking about; fixes what you authorize</td></tr>
<tr><td>Approve, edit, or skip each campaign — a few minutes over coffee</td><td>Produces the whole campaign from your photos, your voice, your brand; stages it per channel</td></tr>
<tr><td>Tap send</td><td>Distributes to the channels you connected, tracks each platform's status until it's public, and reports results in your units</td></tr>
</table>
<div class="duo">
<div class="rail"><b>Wineries, breweries & distilleries:</b> the same loop carries three revenue lines — the visit, the bottle, the class. Classes become bookable listings through your existing ticketing; club signup attaches to everything; offers are tracked to redemption.</div>
<div class="rail"><b>Solo artists:</b> a person, not a place. OneLive gathers your dates from the venues' own calendars (one tap to confirm), keeps your bio and links right where AI tools answer, and builds the two assets that travel with you: your list and your provable draw. It never touches your music or artwork.</div>
</div>

<div class="pg"></div><h2>Control and trust — the rules that don't bend</h2>
<div class="tiles">
<div class="tile"><div class="n">Your accounts</div><div class="t">every channel is connected under your login, removable by you at any time</div></div>
<div class="tile"><div class="n">Your budget</div><div class="t">ads run on your ad account with your cap — OneLive takes no percentage of your ad spend at setup or during the free period</div></div>
<div class="tile"><div class="n">Your approval</div><div class="t">promotional sends happen on your tap; factual corrections follow rules you set</div></div>
<div class="tile"><div class="n">Your exit</div><div class="t">export everything; the widget, the corrected listings, and your list remain yours</div></div>
</div>
<ul>
<li><b>Evidence behind every fact:</b> each date, time, and detail carries its sources; conflicting information is flagged to you, never silently guessed.</li>
<li><b>Paid status never changes OneLive ranking.</b> Not for you, not for anyone, not at any price.</li>
<li><b>Channel status is transparent:</b> for each platform you always see published, staged, submitted-awaiting-review, or monitored — never a vague "done."</li>
</ul>

<div class="pg"></div><h2>What has actually been proven — and what hasn't yet</h2>
<div class="duo">
<div><h2 style="border:none">Demonstrated today</h2>
<ul>
<li>Reading a real venue's public web presence and assembling its calendar (run on a real Austin venue, 2026)</li>
<li>Cross-checking every fact against multiple sources with confidence levels</li>
<li>Catching a real error: one listing site had the wrong day of the week for a Saturday show</li>
<li>Holding back single-source facts as one question instead of publishing them</li>
<li>Drafting the full campaign and the search-readable event data</li>
</ul></div>
<div><h2 style="border:none">Still to validate (pilot)</h2>
<ul>
<li>Live publishing through connected accounts (several platforms require authorization or partner approval)</li>
<li>Connector reliability, moderation timing, and status tracking at scale</li>
<li>Learning voice and photos from your private library (only public material used so far)</li>
<li>Measured attendance lift, retention, and cost-to-serve</li>
</ul></div>
</div>
<div class="warn"><b>Honesty rule:</b> the worked examples in this document are illustrative pilot targets, not observed customer results. We publish observed numbers only from live campaigns with tracking and retained records.</div>

<div class="pg"></div><h2>Where your events can go</h2>
<div class="warn" style="font-size:11pt"><b>Where this stands today:</b> these channel connections are in build (each one's status is tracked in OneLive's connector registry) and are being validated with pilot partners — nothing publishes anywhere today. The table shows how each channel is <i>designed</i> to work once you connect it. Some integrations require your authorization, platform approval, or a final step in the platform's own app; search and AI visibility are eligibility outcomes, not guarantees. Reporting status honestly, channel by channel, is the product.</div>
<table class="compact">
<tr><th>Channel</th><th style="width:40%">How it's designed to work once you connect it</th></tr>
<tr><td>Your website event pages + OneLive listing + link-in-bio</td><td>Kept current automatically — the first channels a pilot turns on</td></tr>
<tr><td>Google Business Profile (posts, hours, events)</td><td>Publishes after your approval — needs you to authorize access to your profile</td></tr>
<tr><td>Instagram + Facebook Page posts · YouTube Shorts</td><td>Publishes after your approval — needs platform authorization and the platforms' app review</td></tr>
<tr><td>Facebook boost (your ad account)</td><td>Prepared as a two-tap recipe — you finish it in your own app, on your own budget</td></tr>
<tr><td>Email + text, through the tools you already use</td><td>Drafted into your existing tools — sends only on your approval</td></tr>
<tr><td>Bing + search indexing</td><td>Submitted, then monitored until public — indexing is always the engine's decision</td></tr>
<tr><td>City event calendars &amp; local press listings</td><td>Submitted on your behalf — then awaiting each editor's review</td></tr>
<tr><td>Apple Maps · Yelp · Nextdoor · Foursquare</td><td>Monitored for accuracy from day one — direct updates depend on platform partner programs</td></tr>
</table>


<div class="pg"></div><h2>Why this stays good for you — the OneLive loop</h2>
<p class="big">OneLive is a live-culture guide. Your agent is how your events become part of it — verified.</p>
<p>Every business and artist using the agent adds verified, first-hand event data to OneLive's consumer guide. A more complete, more accurate guide brings more people deciding what to do tonight. That demand flows back to the rooms and artists supplying the events — which is why the basics are free: your accuracy IS our product.</p>
<ul>
<li>Your events appear in the guide with their verification visible — never ranked for pay.</li>
<li>The better the guide gets, the more your listing is worth; the more businesses join, the better the guide gets.</li>
<li>You get the demand; OneLive gets the data quality. Nobody pays for position.</li>
</ul>

<div class="pg"></div><h2>The pilot — and what we'll measure</h2>
<p>We are recruiting a small group of recurring-event venues in one city for an eight-week pilot. Success is defined in advance, in your units:</p>
<table>
<tr><th>For you</th><th>For the product</th></tr>
<tr><td>Owner minutes per event (target: under 15/month) · directly tracked attendance, signups, reservations · list growth · fewer wrong-fact incidents reaching customers</td><td>Preview-to-claim rate · first and repeat campaign approval · publication success by channel · time-to-correction · retention after 8 weeks</td></tr>
</table>
<h2>What it costs</h2>
<p><b>The basics are free, permanently:</b> your claimed listing, the verified calendar and preview, corrected facts, the website widget, conflict alerts, and your exportable record. <b>Ongoing campaign generation is free for an initial period</b>; it may later carry a modest price — below what the same work costs from an agency or freelancer — and pricing will never include a percentage of your ad spend during setup or the free period, and will never affect how OneLive ranks anything.</p>
<div class="rail"><b>Next step:</b> paste your link. See your preview. Decide after.</div>
"""

html = f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{body}</body></html>"
HTML(string=html).write_pdf("OneLive_Customer_Story_v1.pdf")
from pypdf import PdfReader
r = PdfReader("OneLive_Customer_Story_v1.pdf")
t = "".join(p.extract_text() for p in r.pages)
t = " ".join(t.split())
for probe in ["More people through the door", "illustrative", "Your accounts", "pilot"]:
    assert probe in t, probe
print("pages:", len(r.pages), "- ok")
