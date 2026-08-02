# -*- coding: utf-8 -*-
# CASE STUDY: The Continental Club (Austin) — real public data gathered 2026-08-01.
# Renders the artifacts the agent would produce. Demonstration only; nothing published.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; LINE="#d8d7d3"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"
LBLUE="#cde2fb"; LORANGE="#fbe0d4"; LAQUA="#d2f0e4"; LYEL="#fdeecb"
RED="#8e2f22"; CREAM="#f6ead2"   # venue-flavored accents for the kit mocks

def esc(t): return t.replace("$","\\$")
def wr(t,w): return textwrap.wrap(t,w)
def W(t,w): return esc("\n".join(textwrap.wrap(t,w)))

FW,FH=14.2,9.7
def canvas(title, sub, badge="DEMONSTRATED", bcol=AQUA):
    fig,ax=plt.subplots(figsize=(FW,FH))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    ax.set_position((0,0,1,1)); ax.set_xlim(0,FW); ax.set_ylim(0,FH); ax.axis("off")
    # title wraps clear of the badge; sub wraps at the frame edge (PR #142 r1
    # visual QA — a longer caption clipped, and the title ran under the badge)
    ax.text(0.2,FH-0.38,title,fontsize=19,fontweight="bold",color=INK)
    ax.text(0.2,FH-0.62,W(sub,150),fontsize=11.8,color=INK2,va="top",linespacing=1.3)
    if badge:
        bw_=0.34+0.128*len(badge)
        ax.add_patch(FancyBboxPatch((FW-0.2-bw_,FH-0.52),bw_,0.4,boxstyle="round,pad=0.05",fc="white",ec=bcol,lw=2.0))
        ax.text(FW-0.2-bw_/2,FH-0.32,badge,fontsize=10.6,fontweight="bold",color=bcol,ha="center",va="center")
    return fig,ax

def statechip(ax,x,y,state):
    col={"CONFIRMED":AQUA,"LIKELY":YELLOW,"UNVERIFIED":ORANGE,"DRIFT":RED}[state]
    w=0.3+0.128*len(state)
    ax.add_patch(FancyBboxPatch((x,y-0.17),w,0.36,boxstyle="round,pad=0.04",fc="white",ec=col,lw=1.7))
    ax.text(x+w/2,y+0.01,state,fontsize=9.8,fontweight="bold",color=col,ha="center",va="center")
    return w

# ============ 1 · THE READ PASS ============
fig,ax=canvas("Artifact 1 — the read pass: what the agent extracted, with evidence and confidence",
 "Every fact carries its sources and a state — corroborated = CONFIRMED; single-source stays UNVERIFIED until the owner's tap. Gathered 2026-08-01.")

rows=[
 ("IDENTITY","The Continental Club — 1315 S Congress Ave, Austin, TX · (512) 441-2444 · since 1955","official site · Yelp · austintexas.org","CONFIRMED"),
 ("SECOND ROOM","The Continental Club Gallery — upstairs, 1313A S Congress","Yelp Gallery listing · official site","CONFIRMED"),
 ("HOURS","Mon 6pm–2am · Tue–Fri 4pm–2am · Sat 2pm–2am · Sun 2pm–12am","official site · Yelp — MATCH (no drift found)","CONFIRMED"),
 ("VOICE / BRAND","'legendary' roots room — rockabilly, country, swing, blues 'every night of the week'","official site copy · heyaustin.com · Playboy 'Best Bars in America'","CONFIRMED"),
 ("RESIDENCY","The Peterson Brothers — Texas blues/soul/funk — EVERY SATURDAY, 8:00 pm residency","Bandsintown · Eventbrite · Do512 · Spotify — Aug 1, 8, 22, 29 all listed","CONFIRMED"),
 ("EVENT","The Peterson Brothers — Sat Aug 29, 8:00–9:30 pm, ticketed (Eventbrite link captured)","Eventbrite (times) · Bandsintown","CONFIRMED"),
 ("EVENT","Hellbilly Playboy — Tue Aug 4","Bandsintown","LIKELY"),
 ("EVENT","Shannon McNally, Next of Kin, Buffalo Hunt — 9:30 pm, date NOT resolved","Do512 only — one source, no date","UNVERIFIED"),
 ("DRIFT CAUGHT","Do512 labels the Aug 1 show 'Friday' — Aug 1, 2026 is a SATURDAY; all other sources agree","Do512 vs Bandsintown/Eventbrite + calendar math","DRIFT"),
]
y=FH-1.2
for idx,(cat,fact,src,st) in enumerate(rows):
    h=0.88
    if idx%2==0:
        ax.add_patch(FancyBboxPatch((0.2,y-h+0.06),13.8,h-0.06,boxstyle="round,pad=0.02",fc="#f2f1ee",ec="#f2f1ee"))
    ax.text(0.38,y-0.24,cat,fontsize=10.6,fontweight="bold",color=INK2,va="center")
    statechip(ax,12.45,y-0.24,st)
    ax.text(0.38,y-0.52,esc(fact),fontsize=12.4,color=INK,va="center")
    ax.text(0.38,y-0.78,esc("sources: "+src),fontsize=9.8,color=INK2,style="italic",va="center")
    y-=h
ax.text(0.2,y-0.2,W("This table IS the product's spine: extraction → evidence → state. Nothing UNVERIFIED ever publishes; the open items become ONE question in the owner's thread (day one).",135),
 fontsize=11.4,color=INK2,style="italic",va="top")
plt.savefig("cs_extract.png",dpi=185,facecolor=SURFACE); plt.close()
print("cs_extract")

# ============ 2 · THE PREVIEW CARD ============
fig,ax=canvas("Artifact 2 — the onboarding preview: 'here's how you'll appear'",
 "This is what the owner glances at in minute 3 — their real calendar, already assembled. One question mark, one tap to answer it.")
px,pw=3.3,7.6
ax.add_patch(FancyBboxPatch((px,0.55),pw,8.15,boxstyle="round,pad=0.08",fc="white",ec=INK,lw=2.2))
ax.add_patch(FancyBboxPatch((px+0.25,7.55),pw-0.5,0.95,boxstyle="round,pad=0.04",fc=RED,ec=RED))
ax.text(px+pw/2,8.24,"THE CONTINENTAL CLUB",fontsize=17,fontweight="bold",color=CREAM,ha="center")
ax.text(px+pw/2,7.86,"1315 S Congress Ave · since 1955 · live roots every night",fontsize=11.4,color=CREAM,ha="center")
events=[
 ("SAT AUG 1","The Peterson Brothers — Saturday residency · 8:00 pm","conf"),
 ("TUE AUG 4","Hellbilly Playboy","conf"),
 ("SAT AUG 8","The Peterson Brothers — Saturday residency · 8:00 pm","conf"),
 ("SAT AUG 22","The Peterson Brothers — Saturday residency · 8:00 pm","conf"),
 ("SAT AUG 29","The Peterson Brothers · 8:00–9:30 pm · ticketed","conf"),
 ("DATE?","Shannon McNally · Next of Kin · Buffalo Hunt — 9:30 pm","ask"),
]
y=7.25
for d,t,k in events:
    ax.add_patch(FancyBboxPatch((px+0.25,y-0.78),pw-0.5,0.72,boxstyle="round,pad=0.03",
        fc=(LYEL if k=="ask" else "#faf9f6"),ec=(YELLOW if k=="ask" else LINE),lw=1.4))
    ax.text(px+0.45,y-0.30,d,fontsize=11.8,fontweight="bold",color=(ORANGE if k=="ask" else RED))
    ax.text(px+0.45,y-0.62,W(t,56),fontsize=12.2,color=INK)
    if k=="ask":
        ax.text(px+pw-0.45,y-0.46,"which date? →",fontsize=10.8,fontweight="bold",color=ORANGE,ha="right")
    y-=0.86
ax.add_patch(FancyBboxPatch((px+0.25,y-0.85),pw-0.5,0.75,boxstyle="round,pad=0.04",fc=LAQUA,ec=AQUA,lw=1.6))
ax.text(px+pw/2,y-0.28,"Deploys to: Google · Bing · Apple · Yelp · Nextdoor · city calendars · site + JSON-LD",fontsize=11.2,color=INK,ha="center")
ax.text(px+pw/2,y-0.60,"read from: site, Bandsintown, Songkick, Do512, Eventbrite, Yelp — one mislabel caught",fontsize=10.4,color=INK2,ha="center")
# side notes
for sx,txt in [(0.22,"Everything on this card\nwas assembled WITHOUT\nthe venue lifting a\nfinger — the 'glance at\nthe preview' step of\nonboarding."),
               (11.15,"The one yellow row is\nthe whole ask: single-\nsource event, one tap\nto confirm or dismiss.\nNothing unverified\npublishes.")]:
    ax.text(sx,5.8,txt,fontsize=12.2,color=INK2,va="top",linespacing=1.45)
plt.savefig("cs_preview.png",dpi=185,facecolor=SURFACE); plt.close()
print("cs_preview")

# ============ 3 · THE CAMPAIGN KIT ============
fig,ax=canvas("Artifact 3 — the campaign kit for the real Aug 29 show (drafted, never published)",
 "The Peterson Brothers · Sat Aug 29 · 8:00–9:30 pm — from the venue's public voice and real data. Their photos would fill the frames; every send is THEIR tap.")
# four carousel cards
slides=[
 ("SATURDAY\nNIGHT","THE PETERSON\nBROTHERS",CREAM,RED),
 ("TEXAS BLUES\nSOUL · FUNK","the standing\nSaturday residency",RED,CREAM),
 ("8:00 PM\nAUG 29","1315 S CONGRESS\nsince 1955",CREAM,RED),
 ("BE IN\nTHE ROOM","tickets → link in bio\n(or at the door)",RED,CREAM),
]
ax.text(0.2,8.35,"IG CAROUSEL — 4 cards, story + feed crops included",fontsize=11.4,fontweight="bold",color=INK2)
for i,(big,small,fc,tc) in enumerate(slides):
    x=0.2+i*1.85
    ax.add_patch(FancyBboxPatch((x,6.2),1.7,1.95,boxstyle="round,pad=0.03",fc=fc,ec=INK,lw=1.6))
    ax.text(x+0.85,7.62,big,fontsize=10.8,fontweight="bold",color=tc,ha="center",va="center",linespacing=1.15)
    ax.text(x+0.85,6.85,small,fontsize=8.0,color=tc,ha="center",va="center",linespacing=1.2)
    ax.text(x+0.85,6.32,"[ their photo ]",fontsize=6.8,color=tc,ha="center",style="italic")
# captions column
cap_x=8.0
blocks=[
 ("IG CAPTION (their voice — no hype, room-first)",
  "Saturday night at the Continental. The Peterson Brothers bring the blues, soul & funk back to the room — like every Saturday since the residency began. 8 o'clock. Doors on South Congress, same as 1955. Tickets at the link or at the door."),
 ("FB EVENT (longer, shareable)",
  "The Peterson Brothers — Saturday, August 29, 8:00–9:30 pm at The Continental Club, 1315 S Congress Ave. The standing Saturday-night residency: Texas blues, soul, and funk in Austin's longest-running club. Ticket link attached; the Gallery is open upstairs after."),
 ("GOOGLE BUSINESS POST (search-facing, plain facts first)",
  "Live this Saturday 8/29, 8 pm: The Peterson Brothers — blues/soul/funk residency. Open till 2 am. 1315 S Congress Ave."),
 ("SMS DRAFT (to their list, if they have one — or starts one)",
  "Continental Club: Peterson Brothers Saturday 8pm. Reply STOP to opt out."),
]
y=8.35
for h,t in blocks:
    ax.text(cap_x,y,h,fontsize=10.2,fontweight="bold",color=INK2); y-=0.30
    lines=wr(t,52)
    ax.add_patch(FancyBboxPatch((cap_x-0.12,y-0.26*len(lines)-0.18),6.1,0.26*len(lines)+0.3,boxstyle="round,pad=0.03",fc="white",ec=LINE,lw=1.2))
    for ln in lines:
        ax.text(cap_x,y-0.04,esc(ln),fontsize=10.6,color=INK,va="top"); y-=0.26
    y-=0.42
# ad recipe + schedule strip
ax.add_patch(FancyBboxPatch((0.2,3.4),7.4,2.4,boxstyle="round,pad=0.05",fc="white",ec=BLUE,lw=1.8))
ax.text(0.45,5.5,"AD RECIPE — 2-tap boost, THEIR account, THEIR cap",fontsize=11,fontweight="bold",color=BLUE)
for i,ln in enumerate(["Audience: live-music interests within 15 miles of 78704","Window: Wed 8/26 → Sat 8/29 · Budget: $40 cap (theirs)",
 "Creative: carousel card 1 · Destination: ticket link","Executed as a boost in their own Meta app — no API, no fees, no % of spend"]):
    ax.text(0.45,5.14-i*0.32,esc(ln),fontsize=10.8,color=INK)
ax.add_patch(FancyBboxPatch((0.2,0.95),7.4,2.25,boxstyle="round,pad=0.05",fc="white",ec=AQUA,lw=1.8))
ax.text(0.45,2.9,"SCHEDULE + MEASUREMENT (staged, owner-tapped)",fontsize=11,fontweight="bold",color=AQUA)
for i,ln in enumerate(["Mon 8/24 — carousel + FB event + GBP post staged","Thu 8/27 — reminder story staged · boost window opens",
 "Sat 8/29, 5 pm — day-of story with door info","After: taps · ticket clicks · door code count → next kit learns"]):
    ax.text(0.45,2.54-i*0.32,esc(ln),fontsize=10.8,color=INK)
ax.text(7.1,0.52,"Owner's total involvement: approve or edit, then tap — ~3–4 minutes. Today this is a freelancer's afternoon, or it doesn't happen.",
 fontsize=10.6,color=INK2,style="italic",ha="center",va="center")
plt.savefig("cs_kit.png",dpi=185,facecolor=SURFACE); plt.close()
print("cs_kit")

# ============ 4 · THE MACHINE-READABLE LAYER ============
fig,ax=canvas("Artifact 4 — the layer machines read: what search and AI assistants receive",
 "Generated from the same verified facts. Most local venues never publish this layer — in Uberall's 2026 benchmark, 83% of restaurant/QSR locations were invisible in AI recommendations (C-01: a proxy for the wider local gap, not a measurement of it).")
code = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "MusicEvent",
  "name": "The Peterson Brothers — Saturday Residency",
  "startDate": "2026-08-29T20:00:00-05:00",
  "endDate":   "2026-08-29T21:30:00-05:00",
  "eventStatus": "https://schema.org/EventScheduled",
  "url": "[unique per-event page URL]",
  "location": {
    "@type": "MusicVenue",
    "name": "The Continental Club",
    "address": { "@type": "PostalAddress",
      "streetAddress": "1315 S Congress Ave",
      "addressLocality": "Austin", "addressRegion": "TX",
      "postalCode": "78704", "addressCountry": "US" },
    "telephone": "(512) 441-2444"
  },
  "performer": { "@type": "MusicGroup",
                 "name": "The Peterson Brothers" },
  "offers": { "@type": "Offer",
              "url": "[their Eventbrite link]" }
}
</script>"""
ax.add_patch(FancyBboxPatch((0.2,0.45),7.6,7.95,boxstyle="round,pad=0.05",fc="#1c1c1a",ec=INK,lw=1.6))
ax.text(0.5,8.16,"event JSON-LD — emitted on a unique per-event page (site widget + 1Live)",fontsize=10.4,color="#9ec5f4",family="monospace")
ax.text(0.5,0.62,"price & availability OMITTED — not verified from the read; the agent does not invent",fontsize=9.4,color="#eda100",family="monospace")
yy=7.85
for ln in code.split("\n"):
    ax.text(0.5,yy,ln,fontsize=9.9,color="#e8e6e1",family="monospace",va="top"); yy-=0.292
who=[("Google / Bing","event rich results · 'things to do tonight' · Maps"),
     ("AI assistants","ChatGPT · Gemini · Perplexity — citable, structured, current"),
     ("1Live","enters the gate as verified first-party data — still corroborated"),
     ("Their own site","the events widget stays current with zero manual editing")]
y=7.55
ax.text(8.2,8.16,"WHO READS THIS",fontsize=12.6,fontweight="bold",color=INK2)
for t,d in who:
    ax.add_patch(FancyBboxPatch((8.2,y-1.18),5.75,1.08,boxstyle="round,pad=0.04",fc="white",ec=AQUA,lw=1.7))
    ax.text(8.45,y-0.42,t,fontsize=12.8,fontweight="bold",color=INK)
    ax.text(8.45,y-0.82,W(d,44),fontsize=11.2,color=INK2)
    y-=1.34
ax.text(8.2,2.18,W("Deployed with it: NAP held identical across Google, Yelp, Bing, Apple, Foursquare, Nextdoor · AI-crawler access (OAI-SearchBot for ChatGPT search · PerplexityBot · ClaudeBot; GPTBot managed separately as a training decision) · IndexNow submissions — notification, not guaranteed indexing · an llms.txt hedge. Same drift-watch that caught the 'Friday' mislabel.",52),
 fontsize=11.0,color=INK2,va="top",linespacing=1.38)
plt.savefig("cs_machine.png",dpi=185,facecolor=SURFACE); plt.close()
print("cs_machine")

# ============ 5 · THE OWNER'S THREAD (day one, real numbers) ============
fig,ax=canvas("Artifact 5 — day one, as the owner would see it (every number in this thread is real)",
 "The whole product surface is this thread. Two questions total; everything else already done and waiting on taps.")
msgs=[
 ("a","Read your site and public listings. Found the Saturday Peterson Brothers residency (Aug 1, 8, 22, 29 — 8 pm; the 29th ticketed), Hellbilly Playboy Tue Aug 4, plus hours, phone, the Gallery. Staged for Google, Yelp, Apple, Nextdoor, the city calendars, and your site.",["SEE THE PREVIEW"]),
 ("a","One catch already: Do512 lists your Aug 1 show as 'Friday' — Aug 1 is a Saturday. Every other source agrees. Want me to file the correction?",["FIX IT","LEAVE IT"]),
 ("o","Fix it",None),
 ("a","Done. One question: I can only find one source for 'Shannon McNally · Next of Kin · Buffalo Hunt, 9:30 pm' — no date. Is that show real, and when?",["PICK DATE","NOT OURS"]),
 ("a","The Aug 29 kit is drafted — carousel, reel + YouTube Short from your own clips, captions, Google post, $40 boost recipe on your account. Nothing moves without you.",["SEE THE KIT","LATER"]),
]
y=8.45; x0=2.9; colw=8.4
for who,text,chips in msgs:
    lines=wr(text,74)
    bh=0.28+0.27*len(lines)
    if who=="a":
        ax.add_patch(FancyBboxPatch((x0,y-bh),colw,bh,boxstyle="round,pad=0.06",fc="#efeeec",ec="#d8d6d2",lw=1))
        ax.text(x0+0.2,y-bh/2,esc("\n".join(lines)),fontsize=12.2,color=INK,va="center",linespacing=1.3)
    else:
        bw=1.6
        ax.add_patch(FancyBboxPatch((x0+colw-bw,y-0.5),bw,0.5,boxstyle="round,pad=0.06",fc=BLUE,ec=BLUE))
        ax.text(x0+colw-bw/2,y-0.25,text,fontsize=12.2,color="white",ha="center",va="center")
        bh=0.5
    y-=bh+0.10
    if chips:
        cx=x0+0.25
        for c in chips:
            cw=0.4+0.125*len(c)
            ax.add_patch(FancyBboxPatch((cx,y-0.38),cw,0.38,boxstyle="round,pad=0.05",fc="white",ec=BLUE,lw=1.4))
            ax.text(cx+cw/2,y-0.19,c,fontsize=10,color=BLUE,ha="center",va="center",fontweight="bold")
            cx+=cw+0.2
        y-=0.5
    y-=0.08
ax.add_patch(FancyBboxPatch((0.25,0.18),13.7,0.8,boxstyle="round,pad=0.05",fc=LYEL,ec=INK,lw=1.2))
ax.text(7.1,0.58,W("Owner's day-one effort for everything above: read this thread and tap. The read pass, the corroboration, the drift catch, the preview, and the kit were all done before the first message arrived.",145),
 fontsize=11.2,color=INK,ha="center",va="center",fontweight="bold")
plt.savefig("cs_thread.png",dpi=185,facecolor=SURFACE); plt.close()
print("cs_thread")
