# -*- coding: utf-8 -*-
# Content production mechanics as TWO full-page figures.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"
LBLUE="#cde2fb"; LORANGE="#fbe0d4"; LYEL="#fdeecb"

def wrap(t,w): return "\n".join(textwrap.wrap(t,w)).replace("$","\\$")

def card(ax,x,y,w,h,title,body,ec,fc="white",tfs=13.5,bfs=12.2,bw=None,tcol=None):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.05",fc=fc,ec=ec,lw=1.8))
    if body:
        ax.text(x+w/2,y+h-0.34,title,ha="center",fontsize=tfs,fontweight="bold",color=tcol or INK)
        ax.text(x+w/2,y+(h-0.5)/2,wrap(body,bw or 30),ha="center",va="center",fontsize=bfs,color=INK,linespacing=1.3)
    else:
        ax.text(x+w/2,y+h/2,wrap(title,bw or 20),ha="center",va="center",fontsize=tfs,fontweight="bold",color=tcol or INK)

def arrow(ax,p0,p1,c=INK2,lw=2.0,rad=0.0,ms=16):
    ax.add_patch(FancyArrowPatch(p0,p1,arrowstyle="-|>",mutation_scale=ms,color=c,lw=lw,connectionstyle=f"arc3,rad={rad}",zorder=6))

def canvas(title, sub):
    fig,ax=plt.subplots(figsize=(13.9,9.7))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    ax.set_position((0,0,1,1)); ax.set_xlim(0,13.9); ax.set_ylim(0,9.7); ax.axis("off")
    ax.text(0.2,9.32,title,fontsize=19,fontweight="bold",color=INK)
    ax.text(0.2,8.92,sub,fontsize=11.8,color=INK2)
    return fig,ax

# ================= PAGE 1 · DAY ONE =================
fig,ax = canvas("Where the content comes from — day one",
 "Nothing 'just appears.' One paste, and the agent learns from what the business already has. No forms, no uploads, no setup project.")

card(ax,0.2,6.3,3.7,2.0,"1 · THE PASTE","The owner pastes one URL — website or Instagram. Their only setup work, ever.",BLUE,LBLUE,bw=30)
card(ax,4.6,6.3,4.5,2.0,"2 · READS EVERYTHING PUBLIC","events page & calendar · Instagram posts and captions · photos · hours, menu, links · logo and colors",ORANGE,bw=38)
card(ax,9.8,6.3,3.9,2.0,"3 · OWNER CONFIRMS","Glances at the preview ('your next 14 events'), confirms identity. 3 taps total.",BLUE,LBLUE,bw=32)
arrow(ax,(3.9,7.3),(4.6,7.3)); arrow(ax,(9.1,7.3),(9.8,7.3))

ax.text(0.2,5.62,"DISTILLED INTO THE FOUR INGREDIENTS — every future campaign is built from these",fontsize=13,fontweight="bold",color=AQUA)
ing=[("EVENT CALENDAR","their dates and details — synced from wherever they already keep them"),
     ("PHOTO LIBRARY","their own pictures, organized by event and type — refreshed as they post new ones"),
     ("VOICE PROFILE","how THEY actually write — tone, phrasing, language — learned from their own captions"),
     ("BRAND KIT","logo, colors, look — captured once so every asset matches the room")]
for i,(t,b) in enumerate(ing):
    card(ax,0.2+i*3.45,3.1,3.25,2.25,t,b,AQUA,tfs=12.8,bfs=11.8,bw=26)
arrow(ax,(6.95,6.3),(6.95,5.85),rad=0)

card(ax,0.2,0.85,13.5,1.75,"WEEK ONE — THE MAINTENANCE PASS  (Tier 1: once, then quiet upkeep)",
 "listings corrected everywhere — maps, Yelp, Nextdoor, TripAdvisor-class, the city calendars · site widget live · machine-readable layer + AI-crawler access published — the foundation the growth engine runs on. Once, then invisible.",
 INK2,tfs=13.5,bfs=12.4,bw=105)
arrow(ax,(6.95,3.1),(6.95,2.6))
ax.text(6.95,0.42,"from here on, the agent watches for changes and drift — the owner never fills in a profile again",
 fontsize=11.2,color=INK2,style="italic",ha="center")
plt.savefig("flow_factory1.png",dpi=185,facecolor=SURFACE); plt.close()
print("factory1 done")

# ================= PAGE 2 · THE CONTENT FACTORY =================
fig,ax = canvas("Every event after that — the content factory (Tier 2, ongoing)",
 "Each campaign is assembled from THEIR ingredients — which is why it sounds like them and looks like them. It drafts; it never publishes.")

card(ax,0.2,5.4,3.7,2.9,"THIS EVENT'S FACTS","what's happening, when, who's playing, ticket link, the offer if any — from the calendar the agent watches",BLUE,LBLUE,bw=28)
card(ax,0.2,2.2,3.7,2.5,"WHAT WORKED LAST TIME","the learning loop: 'carousel beat the flyer 3-to-1' → lead with carousels next time",AQUA,bw=28)
card(ax,4.5,2.2,4.1,6.1,"THE AGENT ASSEMBLES","Combines the event's facts with their photos, their voice, and their brand — and drafts the whole campaign.\n\nEvery asset arrives ready. The send button belongs to the owner.",ORANGE,LORANGE,tfs=14.5,bfs=12.6,bw=28)
arrow(ax,(3.9,6.6),(4.5,6.2)); arrow(ax,(3.9,3.4),(4.5,3.8))

ax.text(11.2,8.55,"ONE EVENT → THE WHOLE CAMPAIGN, staged",fontsize=13,fontweight="bold",color=INK,ha="center")
outs=["IG carousel","IG story + reel","IG feed post","FB event","FB page post","Google Business post","YouTube Short","Email · SMS · ads (their account)"]
for i,t in enumerate(outs):
    r,c=divmod(i,2)
    card(ax,9.0+c*2.4,6.95-r*1.35,2.25,1.15,t,None,AQUA,tfs=11.8,bw=14)
arrow(ax,(8.6,5.2),(9.0,5.2))

ax.add_patch(Circle((9.55,1.6),0.26,fc=YELLOW,ec=INK,lw=1.2))
ax.text(9.55,1.6,"TAP",ha="center",va="center",fontsize=9,fontweight="bold",color=INK)
card(ax,10.1,0.95,3.6,1.5,"DISTRIBUTED, THEN MEASURED","socials + YouTube · their list · maps, Yelp, Nextdoor, city calendars · OneLive — then covers · signups · sales",INK2,tfs=12.2,bfs=11.4,bw=30)
arrow(ax,(10.1,2.55),(9.85,1.9),rad=0.15)
arrow(ax,(10.4,0.95),(2.1,2.2),c=AQUA,rad=-0.25,lw=2.2)
ax.text(5.6,0.5,"results flow back into 'what worked last time' — month three beats month one",
 fontsize=11.6,color=AQUA,style="italic",ha="center")
plt.savefig("flow_factory2.png",dpi=185,facecolor=SURFACE); plt.close()
print("factory2 done")
