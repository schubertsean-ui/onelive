# -*- coding: utf-8 -*-
# The OneLive engine — clean three-column layout, straight pipeline, outside loop.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; LINE="#d8d7d3"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"; VIOLET="#4a3aa7"
LBLUE="#cde2fb"; LORANGE="#fbe0d4"; LAQUA="#d2f0e4"; LYEL="#fdeecb"

def wrap(t,w): return "\n".join(textwrap.wrap(t,w)).replace("$","\\$")
def card(ax,x,y,w,h,title,body,ec,fc="white",tfs=12.6,bfs=11.2,bw=None):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.05",fc=fc,ec=ec,lw=1.9))
    ax.text(x+w/2,y+h-0.32,title,ha="center",fontsize=tfs,fontweight="bold",color=INK)
    ax.text(x+w/2,y+(h-0.44)/2,wrap(body,bw or 34),ha="center",va="center",fontsize=bfs,color=INK,linespacing=1.3)
def arrow(ax,p0,p1,c=INK2,lw=2.0,rad=0.0,ms=15,z=6):
    ax.add_patch(FancyArrowPatch(p0,p1,arrowstyle="-|>",mutation_scale=ms,color=c,lw=lw,connectionstyle=f"arc3,rad={rad}",zorder=z))

FW,FH=13.9,9.7
fig,ax=plt.subplots(figsize=(FW,FH))
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.set_position((0,0,1,1)); ax.set_xlim(0,FW); ax.set_ylim(0,FH); ax.axis("off")
ax.text(0.2,FH-0.38,"The OneLive engine — ingestion, verification, distribution, and the loop",fontsize=19,fontweight="bold",color=INK)
ax.text(0.2,FH-0.76,"Two ways culture flows in — the open web (we read it) and the Owned Agent (they bring it, verified). One trust machine in the middle; demand flows back out.",fontsize=11.8,color=INK2)

# column geometry
LX,LW = 0.2, 4.35
CX,CW = 4.95, 3.9
RX,RW = 9.25, 4.45
HDR_Y = 8.35
ax.text(LX+LW/2,HDR_Y,"THE CITY'S LIVE CULTURE",fontsize=12.6,fontweight="bold",color=BLUE,ha="center")
ax.text(CX+CW/2,HDR_Y,"THE TRUST MACHINE",fontsize=12.6,fontweight="bold",color=AQUA,ha="center")
ax.text(RX+RW/2,HDR_Y,"WHERE DEMAND HAPPENS",fontsize=12.6,fontweight="bold",color=VIOLET,ha="center")
ax.plot([4.75,4.75],[1.45,8.15],color=LINE,lw=1)

# ---- LEFT column ----
card(ax,LX,6.15,LW,1.85,"23 SEGMENTS OF SUPPLY (canon)","venues & places (11) · organizers & groups (6) · artists & people (6) — the 150-cap room to the solo songwriter",BLUE,LBLUE,bw=36)
card(ax,LX,3.85,LW,1.85,"PATH 1 · THE OPEN WEB","websites, calendars, public socials, the city's event pages — we fetch and read them (266+ sources, growing)",INK2,bw=36)
card(ax,LX,1.5,LW,1.95,"PATH 2 · THE OWNED AGENT","free to start, 3 taps. Keeps their basics right; feeds their marketing to IG, FB, Google, YouTube, Nextdoor, the city calendars, AIs, and their list — their calendar becomes a VERIFIED first-party channel",ORANGE,LORANGE,tfs=12.6,bfs=10.6,bw=40)
arrow(ax,(LX+LW/2,6.15),(LX+LW/2,5.7))
arrow(ax,(LX+LW/2,3.85),(LX+LW/2,3.45))

# ---- CENTER: straight pipeline ----
steps=[("FETCH","raw pages & feeds"),
       ("AI EXTRACT","reads — never publishes"),
       ("CANDIDATES + EVIDENCE","every claim carries its sources"),
       ("THE GATE","corroboration decides: unverified · likely · confirmed · disputed (always shown)"),
       ("PROMOTE","human-custodied — only gated truth goes live")]
sy=7.95; sh=[1.0,1.0,1.15,1.55,1.15]
ys=[]
for (t,b),h in zip(steps,sh):
    sy-=h
    card(ax,CX,sy,CW,h-0.18,t,b,AQUA,tfs=12.0,bfs=10.4,bw=34)
    ys.append((sy,sy+h-0.18))
    if len(ys)>1:
        arrow(ax,(CX+CW/2,ys[-2][0]),(CX+CW/2,ys[-1][1]),c=AQUA)
arrow(ax,(LX+LW,4.8),(CX,ys[0][1]-0.28),c=INK2,rad=-0.2)
gy=(ys[3][0]+ys[3][1])/2
arrow(ax,(LX+LW,2.6),(CX,gy-0.3),c=ORANGE,rad=0.12,lw=2.2)
ax.text(CX+CW/2,1.85,"first-party: pre-corroborated — STILL passes the gate",fontsize=10.0,color=ORANGE,ha="center",va="center")

# ---- RIGHT column ----
card(ax,RX,6.15,RW,1.85,"/TONIGHT — THE CONSUMER FEED","night-of deciders choosing where to go; trust states visible; no pay-to-rank, no connect-to-rank — ever",VIOLET,bw=38)
card(ax,RX,3.85,RW,1.85,"THEIR OWN SURFACES","site widget · socials + YouTube (their tap) · Nextdoor + city calendars kept current · their growing list",VIOLET,bw=38)
card(ax,RX,1.5,RW,1.95,"THE AI-ANSWER LAYER","assistants & answer engines — fed via Bing/IndexNow, open AI-crawler access, the databases, and (Phase C) OneLive's gated endpoint",VIOLET,bw=38)
bus=9.05
arrow(ax,(CX+CW,ys[4][1]-0.35),(bus,ys[4][1]-0.35),c=AQUA)
ax.plot([bus,bus],[2.45,7.0],color=AQUA,lw=2.2)
arrow(ax,(bus,7.0),(RX,7.0),c=AQUA)
arrow(ax,(bus,4.75),(RX,4.75),c=AQUA)
arrow(ax,(bus,2.5),(RX,2.5),c=AQUA)
ax.text(bus-0.13,4.75,"verified truth flows out",fontsize=9.6,color=AQUA,style="italic",ha="center",va="center",rotation=90)

# ---- THE LOOP band ----
ax.add_patch(FancyBboxPatch((0.2,0.42),13.5,0.82,boxstyle="round,pad=0.05",fc=LYEL,ec=INK,lw=1.6))
ax.text(6.95,0.83,wrap("THE LOOP — demand returns as measured attendance, signups, and sales → results increase claiming and retention → each claim adds verified supply → accuracy and coverage rise → reliance and adoption rise further",145),
 fontsize=11.0,color=INK,ha="center",va="center",fontweight="bold")
arrow(ax,(RX+RW/2,1.5),(RX+RW/2,1.26),c=YELLOW,lw=2.4,ms=16)
arrow(ax,(LX+LW/2,1.26),(LX+LW/2,1.48),c=YELLOW,lw=2.4,ms=16)

ax.text(6.95,0.16,"physics, not policy:  AI never publishes — all data passes the gate · ranking is never for sale · disputed always shown · leave anytime, keep everything",
 fontsize=9.8,color=INK2,ha="center",style="italic")
plt.savefig("flow_model.png",dpi=185,facecolor=SURFACE); plt.close()
print("model done  aspect",round(FH/FW,2))
