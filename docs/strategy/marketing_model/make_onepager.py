# -*- coding: utf-8 -*-
# 1Live Agent — client-facing one-pager (founder-directed 2026-08-02):
# entirely outside-in, minimal text, max images, full page. Letter landscape,
# figsize == page size so every fontsize is true printed size.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle, Polygon
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"
LBLUE="#cde2fb"; LORANGE="#fbe0d4"; LAQUA="#d2f0e4"; LYEL="#fdeecb"
def W(t,w): return "\n".join(textwrap.wrap(t,w)).replace("$","\\$")

FW,FH=11.0,8.5
fig,ax=plt.subplots(figsize=(FW,FH))
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.set_position((0,0,1,1)); ax.set_xlim(0,FW); ax.set_ylim(0,FH); ax.axis("off")

def card(x,y,w,h,ec,fc="white",lw=1.9):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.045",fc=fc,ec=ec,lw=lw))

# ---------- header ----------
ax.add_patch(Rectangle((0,FH-1.06),FW,1.06,fc=INK,ec=INK))
ax.text(0.35,FH-0.50,"1LIVE",fontsize=27,fontweight="bold",color="white")
ax.text(0.37,FH-0.88,"AGENT",fontsize=12.5,fontweight="bold",color=YELLOW)
ax.text(2.45,FH-0.48,"Your events, everywhere people look.",fontsize=20,fontweight="bold",color="white")
ax.text(2.45,FH-0.86,"Built for the rooms and artists that make live culture — not for marketing departments.",
        fontsize=11.2,color="#d8d7d3")

LX=0.35; LR=7.40          # left column bounds
PX=7.58                    # phone column start

# ---------- Row A: the problems ----------
ax.text(LX,7.12,"THE PROBLEM — YOUR EVENTS EXIST. THEIR MARKETING DOESN'T.",
        fontsize=11.8,fontweight="bold",color=INK)
probs=[
 ("findme","People Want A\nGreat Night Out","Don't be hard to find —\nor worse, invisible."),
 ("retype","Multiple Sites.\n(Almost) No Time.","Re-typing every event everywhere\nis a job. Nobody's."),
 ("likes","Likes, not\ndoor counts","You never learn what actually\nfilled the room."),
]
pw=2.23; gap=0.115; py=5.32; ph=1.62
for i,(icon,head,why) in enumerate(probs):
    x=LX+i*(pw+gap)
    card(x,py,pw,ph,"#d8d7d3","#f6f5f2")
    cx=x+pw/2; iy=py+ph-0.42
    if icon=="findme":
        ax.add_patch(FancyBboxPatch((cx-0.17,iy-0.14),0.34,0.5,boxstyle="round,pad=0.03",fc="white",ec=INK,lw=2.0))
        ax.add_patch(Circle((cx,iy+0.18),0.09,fc=AQUA,ec=AQUA))
        ax.add_patch(Polygon([(cx-0.075,iy+0.14),(cx+0.075,iy+0.14),(cx,iy-0.02)],fc=AQUA))
        ax.add_patch(Circle((cx,iy+0.18),0.035,fc="white"))
    if icon=="retype":
        for k in range(5):
            ax.add_patch(FancyBboxPatch((cx-0.5+k*0.19,iy-0.16+(k%2)*0.07),0.26,0.34,
                boxstyle="round,pad=0.02",fc="white",ec=INK2,lw=1.4))
        ax.text(cx,iy,"✎",fontsize=15,color=ORANGE,ha="center",va="center")
    if icon=="likes":
        ax.text(cx-0.35,iy+0.04,"♥",fontsize=22,color="#cf5b74",ha="center",va="center")
        ax.text(cx-0.35,iy-0.3,"1,400",fontsize=8.2,color=INK2,ha="center")
        ax.add_patch(Rectangle((cx+0.16,iy-0.22),0.28,0.5,fc="#e9e7e2",ec=INK,lw=1.6))
        ax.text(cx+0.3,iy+0.03,"?",fontsize=13,fontweight="bold",color=ORANGE,ha="center",va="center")
    ax.text(cx,py+0.76,head,fontsize=11.2,fontweight="bold",color=INK,ha="center",va="center",linespacing=1.12)
    ax.text(cx,py+0.32,why,fontsize=8.7,color=INK2,ha="center",va="center",linespacing=1.3)

# ---------- Row B: how it works — two lanes, weight tells the story ----------
ax.text(LX,5.06,"HOW IT WORKS — YOU: A FEW TAPS. 1LIVE: ALL THE WORK.",fontsize=11.8,fontweight="bold",color=INK)

# YOU lane: thin, light, three tiny actions
uy=4.50; uh=0.44
ax.add_patch(FancyBboxPatch((LX,uy),LR-LX,uh,boxstyle="round,pad=0.03",fc=LBLUE,ec=BLUE,lw=1.6))
ax.text(LX+0.14,uy+uh/2,"YOU",fontsize=11,fontweight="bold",color=BLUE,va="center")
# pressable-keycap styling (founder question 2026-08-02: "stronger with an
# Enter button?" — answer: keycap FEEL, phone-tap truth; three real decisions)
you=[("1 · paste one link",1.55),("2 · choose your channels",3.30),("3 · tap approve",5.28)]
for label,x in you:
    wch=0.30+0.066*len(label)
    ax.add_patch(FancyBboxPatch((x+0.02,uy+0.045),wch,uh-0.14,boxstyle="round,pad=0.03",fc="#9dbede",ec="#9dbede"))
    ax.add_patch(FancyBboxPatch((x,uy+0.085),wch,uh-0.14,boxstyle="round,pad=0.03",fc="white",ec=BLUE,lw=1.7))
    ax.text(x+wch/2,uy+uh/2+0.025,label,fontsize=8.6,fontweight="bold",color=BLUE,ha="center",va="center")
ax.text(LR-0.10,uy+uh/2,"that's all —\n≈ minutes",fontsize=7.8,fontweight="bold",color=BLUE,ha="right",va="center",linespacing=1.15)

# 1LIVE lane: thick, saturated, five work cards
ly=3.46; lh=0.92
ax.add_patch(FancyBboxPatch((LX,ly),LR-LX,lh,boxstyle="round,pad=0.03",fc=ORANGE,ec=ORANGE))
ax.text(LX+0.14,ly+lh/2,"1\nL\nI\nV\nE",fontsize=8.6,fontweight="bold",color="white",va="center",linespacing=0.95)
work=[
 ("VERIFIES","every fact,\nevery source"),
 ("BUILDS","your campaign —\nyour photos, your voice"),
 ("PUBLISHES","to the channels\nyou approved"),
 ("MEASURES","the door,\nnot the likes"),
 ("IMPROVES","the next event,\nautomatically"),
]
wx0=LX+0.42; ww=(LR-0.14-wx0-4*0.10)/5
for i,(head,sub) in enumerate(work):
    x=wx0+i*(ww+0.10)
    ax.add_patch(FancyBboxPatch((x,ly+0.08),ww,lh-0.16,boxstyle="round,pad=0.03",fc="white",ec="white"))
    ax.text(x+ww/2,ly+lh-0.28,head,fontsize=9.8,fontweight="bold",color=ORANGE,ha="center",va="center")
    ax.text(x+ww/2,ly+0.32,sub,fontsize=7.6,color=INK2,ha="center",va="center",linespacing=1.2)
    if i<4:
        ax.annotate("",xy=(x+ww+0.105,ly+lh/2),xytext=(x+ww+0.015,ly+lh/2),
            arrowprops=dict(arrowstyle="-|>",color="white",lw=2.0,mutation_scale=13))
# taps drop into the work lane
for xx in (2.05,4.05,5.95):
    ax.annotate("",xy=(xx,ly+lh+0.005),xytext=(xx,uy-0.005),
        arrowprops=dict(arrowstyle="-|>",color=BLUE,lw=1.5,mutation_scale=11,linestyle=(0,(2,2))))

# ---------- Row C: what you get ----------
ax.text(LX,3.28,"WHAT IT'S WORTH TO YOU",fontsize=11.8,fontweight="bold",color=INK)
vals=[
 ("clock","Hours\nback","the repetitive work\nhappens for you",BLUE),
 ("pin","Right,\neverywhere","dates & hours correct\nwhere people check —\n& what's happening",AQUA),
 ("list","An audience\nyou own","your list grows with\nevery campaign",ORANGE),
 ("door","People through\nthe door","attendance & sales,\nmeasured honestly",YELLOW),
]
vw=1.645; vgap=0.115; vy=1.52; vh=1.58
for i,(icon,head,sub,ec) in enumerate(vals):
    x=LX+i*(vw+vgap)
    card(x,vy,vw,vh,ec)
    cx=x+vw/2; iy=vy+vh-0.36
    if icon=="clock":
        ax.add_patch(Circle((cx,iy),0.18,fc="white",ec=ec,lw=2.4))
        ax.plot([cx,cx],[iy,iy+0.12],color=ec,lw=2.0); ax.plot([cx,cx+0.09],[iy,iy],color=ec,lw=2.0)
    if icon=="pin":
        ax.add_patch(Circle((cx,iy+0.06),0.14,fc=ec,ec=ec))
        ax.add_patch(Polygon([(cx-0.115,iy),(cx+0.115,iy),(cx,iy-0.24)],fc=ec))
        ax.add_patch(Circle((cx,iy+0.06),0.055,fc="white"))
    if icon=="list":
        for k in range(3):
            yy=iy+0.13-0.13*k
            ax.add_patch(Circle((cx-0.2,yy),0.04,fc=ec))
            ax.plot([cx-0.09,cx+0.24],[yy,yy],color=ec,lw=2.2)
    if icon=="door":
        ax.add_patch(Rectangle((cx-0.08,iy-0.22),0.26,0.46,fc="white",ec=ec,lw=2.2))
        ax.add_patch(Circle((cx+0.12,iy),0.026,fc=ec))
        ax.annotate("",xy=(cx-0.11,iy),xytext=(cx-0.38,iy),
            arrowprops=dict(arrowstyle="-|>",color=ec,lw=2.2,mutation_scale=15))
    ax.text(cx,vy+0.74,head,fontsize=10.6,fontweight="bold",color=INK,ha="center",va="center",linespacing=1.1)
    ax.text(cx,vy+0.30,sub,fontsize=8.4,color=INK2,ha="center",va="center",linespacing=1.25)

ax.text((LX+LR)/2,1.22,"Product preview — channel connections are in build with pilot partners; each reports its true status.",
        fontsize=7.4,color=INK2,ha="center")

# ---------- right column: the product is a text thread ----------
card(PX,1.42,FW-PX-0.28,7.30-1.42,INK,lw=2.2)
px2=PX+0.17; bw=FW-PX-0.28-0.34
ax.text(px2,7.02,"NO DASHBOARD.",fontsize=12,fontweight="bold",color=INK)
ax.text(px2,6.80,"A text thread that already did the work.",fontsize=9.0,color=INK2)
msgs=[
 ("a","Saw you added Friday's show. It's now on Google, the map apps, the event sites, your website — done."),
 ("a","The promoter's flyer says 9pm; your calendar says 10pm. Which is right?"),
 ("y","10pm"),
 ("a","Fixed everywhere. Friday's promo kit is ready — made from your photos, in your voice. Want it?"),
 ("b","Post as planned"),
 ("a","Saturday: 310 tapped for details, 38 used the door code. Next time I'll lead with the carousel."),
]
y=6.58
prev=None
for kind,t in msgs:
    sender="1Live" if kind=="a" else "You"
    if sender!=prev:
        if kind=="a":
            ax.text(px2+0.04,y-0.02,sender,fontsize=7.2,fontweight="bold",color=INK2,va="top")
        else:
            ax.text(px2+bw*0.94,y-0.02,sender,fontsize=7.2,fontweight="bold",color=BLUE,ha="right",va="top")
        y-=0.14
    prev=sender
    if kind=="a":
        lines=W(t,38); n=lines.count("\n")+1; bh=0.19*n+0.13
        ax.add_patch(FancyBboxPatch((px2,y-bh),bw*0.95,bh,boxstyle="round,pad=0.04",fc="#efedea",ec="#efedea"))
        ax.text(px2+0.12,y-bh/2,lines,fontsize=8.8,color=INK,va="center",linespacing=1.24)
        y-=bh+0.10
    elif kind=="y":
        bh=0.36
        ax.add_patch(FancyBboxPatch((px2+bw*0.58,y-bh),bw*0.36,bh,boxstyle="round,pad=0.04",fc=BLUE,ec=BLUE))
        ax.text(px2+bw*0.76,y-bh/2,t,fontsize=9.4,fontweight="bold",color="white",ha="center",va="center")
        y-=bh+0.10
    else:
        bh=0.40
        ax.add_patch(FancyBboxPatch((px2+bw*0.42,y-bh),bw*0.53,bh,boxstyle="round,pad=0.04",fc=BLUE,ec=BLUE))
        ax.text(px2+bw*0.685,y-bh/2,t,fontsize=9.6,fontweight="bold",color="white",ha="center",va="center")
        y-=bh+0.10
ax.text(px2,max(y-0.06,1.86),"Your week with the agent: minutes, not hours.",fontsize=8.2,style="italic",color=INK2,va="top")

# ---------- bottom band: yours forever ----------
ax.add_patch(Rectangle((0,0),FW,1.06,fc=AQUA,ec=AQUA))
ax.text(0.35,0.70,"YOURS. FOREVER.",fontsize=15.5,fontweight="bold",color="white")
ax.text(0.35,0.40,"Everything the agent builds — your corrected listings, your calendar, your website widget, your customer list —",
        fontsize=9.8,color="white")
ax.text(0.35,0.16,"belongs to you.",fontsize=9.8,fontweight="bold",color="white")
ax.text(FW-0.35,0.44,"You approve\nevery send.",fontsize=12.5,fontweight="bold",color="white",ha="right",va="center",linespacing=1.25)

plt.savefig("onepager.png",dpi=200,facecolor=SURFACE)
plt.savefig("1Live_Agent_One_Pager_v1.pdf",facecolor=SURFACE)
plt.close()
print("onepager done")
