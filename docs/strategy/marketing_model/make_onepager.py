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
 ("chalk","Great night, invisible","People ask their phones — your\nchalkboard can't answer."),
 ("retype","Five sites, zero hours","Re-typing every event everywhere\nis a job. Nobody's."),
 ("likes","Likes, not door counts","You never learn what actually\nfilled the room."),
]
pw=2.23; gap=0.115; py=5.32; ph=1.62
for i,(icon,head,why) in enumerate(probs):
    x=LX+i*(pw+gap)
    card(x,py,pw,ph,"#d8d7d3","#f6f5f2")
    cx=x+pw/2; iy=py+ph-0.42
    if icon=="chalk":
        ax.add_patch(Rectangle((cx-0.4,iy-0.2),0.8,0.44,fc="#2f3b33",ec="#8a6f4d",lw=2.2))
        for k in range(3):
            ax.plot([cx-0.28,cx+0.08+0.05*k],[iy+0.1-0.12*k]*2,color="white",lw=1.4,alpha=0.85)
    if icon=="retype":
        for k in range(5):
            ax.add_patch(FancyBboxPatch((cx-0.5+k*0.19,iy-0.16+(k%2)*0.07),0.26,0.34,
                boxstyle="round,pad=0.02",fc="white",ec=INK2,lw=1.4))
        ax.text(cx,iy,"✎",fontsize=15,color=ORANGE,ha="center",va="center")
    if icon=="likes":
        ax.text(cx-0.35,iy+0.04,"♥",fontsize=22,color="#cf5b74",ha="center",va="center")
        ax.text(cx-0.35,iy-0.26,"1,400",fontsize=8.2,color=INK2,ha="center")
        ax.add_patch(Rectangle((cx+0.16,iy-0.22),0.28,0.5,fc="#e9e7e2",ec=INK,lw=1.6))
        ax.text(cx+0.3,iy+0.03,"?",fontsize=13,fontweight="bold",color=ORANGE,ha="center",va="center")
    ax.text(cx,py+0.72,head,fontsize=11.6,fontweight="bold",color=INK,ha="center",va="center")
    ax.text(cx,py+0.34,why,fontsize=8.7,color=INK2,ha="center",va="center",linespacing=1.3)

# ---------- Row B: how it works ----------
ax.text(LX,5.02,"HOW IT WORKS — YOU DECIDE. IT DOES THE WORK.",fontsize=11.8,fontweight="bold",color=INK)
steps=[
 ("link","PASTE","one link in",BLUE,LBLUE),
 ("check","VERIFY","every fact sourced",AQUA,LAQUA),
 ("plug","CONNECT","only what you choose",ORANGE,LORANGE),
 ("tap","APPROVE","every send is your tap",YELLOW,LYEL),
 ("bars","MEASURE","door results, not likes",AQUA,LAQUA),
 ("up","IMPROVE","next event starts smarter",BLUE,LBLUE),
]
sw=1.045; sgap=0.115; sy=3.58; sh=1.30
for i,(icon,name,capt,ec,fc) in enumerate(steps):
    x=LX+i*(sw+sgap)
    card(x,sy,sw,sh,ec,fc)
    cx=x+sw/2; iy=sy+sh-0.36
    if icon=="link":
        ax.add_patch(FancyBboxPatch((cx-0.26,iy-0.09),0.26,0.18,boxstyle="round,pad=0.04",fc="none",ec=ec,lw=2.4))
        ax.add_patch(FancyBboxPatch((cx,iy-0.09),0.26,0.18,boxstyle="round,pad=0.04",fc="none",ec=ec,lw=2.4))
    if icon=="check": ax.text(cx,iy,"✓",fontsize=21,fontweight="bold",color=ec,ha="center",va="center")
    if icon=="plug":
        ax.add_patch(FancyBboxPatch((cx-0.14,iy-0.12),0.28,0.26,boxstyle="round,pad=0.03",fc="white",ec=ec,lw=2.2))
        ax.plot([cx-0.06,cx-0.06],[iy+0.14,iy+0.28],color=ec,lw=2.4)
        ax.plot([cx+0.06,cx+0.06],[iy+0.14,iy+0.28],color=ec,lw=2.4)
    if icon=="tap":
        ax.add_patch(Circle((cx,iy),0.18,fc="white",ec=ec,lw=2.4))
        ax.text(cx,iy,"TAP",fontsize=8,fontweight="bold",color="#8a5f00",ha="center",va="center")
    if icon=="bars":
        for k,hh in enumerate((0.12,0.22,0.34)):
            ax.add_patch(Rectangle((cx-0.21+k*0.15,iy-0.15),0.11,hh,fc=ec,ec=ec))
    if icon=="up":
        ax.annotate("",xy=(cx+0.17,iy+0.15),xytext=(cx-0.17,iy-0.13),
            arrowprops=dict(arrowstyle="-|>",color=ec,lw=2.6,mutation_scale=20))
    ax.text(cx,sy+0.46,name,fontsize=10.6,fontweight="bold",color=ec,ha="center")
    ax.text(cx,sy+0.21,W(capt,13),fontsize=7.6,color=INK2,ha="center",va="center",linespacing=1.15)
    if i<5:
        ax.annotate("",xy=(x+sw+sgap+0.02,sy+sh/2),xytext=(x+sw+0.03,sy+sh/2),
            arrowprops=dict(arrowstyle="-|>",color=INK2,lw=1.6,mutation_scale=12))

# ---------- Row C: what you get ----------
ax.text(LX,3.28,"WHAT IT'S WORTH TO YOU",fontsize=11.8,fontweight="bold",color=INK)
vals=[
 ("clock","Hours\nback","the repetitive work\nhappens for you",BLUE),
 ("pin","Right,\neverywhere","dates & hours correct\nwhere people check",AQUA),
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
for kind,t in msgs:
    if kind=="a":
        lines=W(t,38); n=lines.count("\n")+1; bh=0.20*n+0.16
        ax.add_patch(FancyBboxPatch((px2,y-bh),bw*0.95,bh,boxstyle="round,pad=0.04",fc="#efedea",ec="#efedea"))
        ax.text(px2+0.12,y-bh/2,lines,fontsize=8.8,color=INK,va="center",linespacing=1.28)
        y-=bh+0.14
    elif kind=="y":
        bh=0.36
        ax.add_patch(FancyBboxPatch((px2+bw*0.58,y-bh),bw*0.36,bh,boxstyle="round,pad=0.04",fc=BLUE,ec=BLUE))
        ax.text(px2+bw*0.76,y-bh/2,t,fontsize=9.4,fontweight="bold",color="white",ha="center",va="center")
        y-=bh+0.14
    else:
        bh=0.40
        ax.add_patch(FancyBboxPatch((px2+bw*0.42,y-bh),bw*0.53,bh,boxstyle="round,pad=0.04",fc=BLUE,ec=BLUE))
        ax.text(px2+bw*0.685,y-bh/2,t,fontsize=9.6,fontweight="bold",color="white",ha="center",va="center")
        y-=bh+0.16
ax.text(px2,y-0.08,"Your week with the agent:\nminutes, not hours.",fontsize=9.0,style="italic",color=INK2,va="top",linespacing=1.3)

# ---------- bottom band: yours forever ----------
ax.add_patch(Rectangle((0,0),FW,1.06,fc=AQUA,ec=AQUA))
ax.text(0.35,0.70,"YOURS. FOREVER.",fontsize=15.5,fontweight="bold",color="white")
ax.text(0.35,0.40,"Everything the agent builds — your corrected listings, your calendar, your website widget, your customer list —",
        fontsize=9.8,color="white")
ax.text(0.35,0.16,"belongs to you, whether or not you ever do more marketing with 1Live.",
        fontsize=9.8,fontweight="bold",color="white")
ax.text(FW-0.35,0.44,"You approve\nevery send.",fontsize=12.5,fontweight="bold",color="white",ha="right",va="center",linespacing=1.25)

plt.savefig("onepager.png",dpi=200,facecolor=SURFACE)
plt.savefig("1Live_Agent_One_Pager_v1.pdf",facecolor=SURFACE)
plt.close()
print("onepager done")
