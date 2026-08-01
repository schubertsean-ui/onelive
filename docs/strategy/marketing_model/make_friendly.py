# -*- coding: utf-8 -*-
# Full-page "what it actually feels like" sheets: thread over two columns + research panel.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; LINE="#d8d7d3"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"
AGENTBUB="#efeeec"; CHIP="#ffffff"

def esc(t): return t.replace("$","\\$")

src = open("build_paper.py").read()
ns = {}
exec(src[:src.index("def esc")], ns)
CATS = {c["n"].split(" · ")[0]: c for c in ns["CATS"]}

FW, FH = 14.2, 9.7
M = 0.18
COLW = 4.62          # each phone column
RX = 2*M + 2*COLW + 0.35   # research panel x
RW = FW - RX - M

def thread(fname, title, sub, msgs, footer, cat_snap, ch3, gr3, fit):
    # auto-fit: measure at base sizes, scale down if the two columns overflow
    base_fs, base_lh = 13.0, 0.295
    avail = FH - 1.02 - 0.92     # title block + footer strip
    def measure(fs_scale):
        lh = base_lh*fs_scale
        tot = 0
        for who,day,text,chips in msgs:
            w = int((COLW-0.55)/(0.108*fs_scale)) if who=='a' else int(2.6/(0.108*fs_scale))
            lines = len(textwrap.wrap(text,w))
            tot += (0.36*fs_scale if day else 0) + 0.26*fs_scale + lines*lh + (0.52*fs_scale if chips else 0) + 0.24
        return tot
    s = 1.0
    while measure(s) > 2*avail - 1.6 and s > 0.76:
        s -= 0.02
    fs = base_fs*s; lh = base_lh*s
    wa = int((COLW-0.55)/(0.108*s)); wo = int(2.6/(0.108*s))

    fig,ax = plt.subplots(figsize=(FW,FH))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    ax.set_position((0,0,1,1)); ax.set_xlim(0,FW); ax.set_ylim(0,FH); ax.axis("off")
    ax.text(M+0.05,FH-0.34,title,fontsize=17.5,fontweight="bold",color=INK)
    ax.text(M+0.05,FH-0.72,sub,fontsize=11.8,color=INK2)
    _b="ILLUSTRATIVE — pilot targets, not observed results"
    _bw=0.3+0.104*len(_b)
    ax.add_patch(FancyBboxPatch((FW-M-_bw,FH-0.5),_bw,0.4,boxstyle="round,pad=0.05",fc="white",ec="#eda100",lw=2.0))
    ax.text(FW-M-_bw/2,FH-0.3,_b,fontsize=9.6,fontweight="bold",color="#b87e00",ha="center",va="center")

    col_x = [M, M+COLW+0.25]
    ax.plot([col_x[1]-0.12,col_x[1]-0.12],[1.05,FH-1.0],color=LINE,lw=1)
    ax.plot([RX-0.18,RX-0.18],[1.05,FH-1.0],color=LINE,lw=1)
    ci = 0
    y = FH-1.08
    for who,day,text,chips in msgs:
        lines = textwrap.wrap(text, wa if who=='a' else wo)
        need = (0.36*s if day else 0) + 0.26*s + len(lines)*lh + (0.52*s if chips else 0) + 0.14
        if y - need < 1.05 and ci == 0:
            ci = 1; y = FH-1.08
        x0 = col_x[ci]
        if day:
            ax.text(x0+COLW/2-0.1,y-0.10,day,fontsize=9.8,color=INK2,ha="center",fontweight="bold")
            y -= 0.36*s
        bh = 0.26*s + len(lines)*lh
        if who=='a':
            bw = COLW-0.5
            ax.add_patch(FancyBboxPatch((x0,y-bh),bw,bh,boxstyle="round,pad=0.06",fc=AGENTBUB,ec="#d8d6d2",lw=1))
            ax.text(x0+0.16,y-bh/2,esc("\n".join(lines)),fontsize=fs,color=INK,va="center",linespacing=1.28)
        else:
            bw = max(1.1, 0.4+0.115*s*max(len(l) for l in lines))
            bx = x0+COLW-0.5-bw
            ax.add_patch(FancyBboxPatch((bx,y-bh),bw,bh,boxstyle="round,pad=0.06",fc=BLUE,ec=BLUE,lw=1))
            ax.text(bx+bw/2,y-bh/2,esc("\n".join(lines)),fontsize=fs,color="white",va="center",ha="center",linespacing=1.28)
        y -= bh+0.10
        if chips:
            cx = x0+0.2
            for c in chips:
                cw = 0.34+len(c)*0.105*s
                ax.add_patch(FancyBboxPatch((cx,y-0.36),cw,0.36,boxstyle="round,pad=0.05",fc=CHIP,ec=BLUE,lw=1.3))
                ax.text(cx+cw/2,y-0.18,c,fontsize=9.6*s+0.5,color=BLUE,ha="center",va="center",fontweight="bold")
                cx += cw+0.18
            y -= 0.52*s
        y -= 0.14

    # research panel
    ax.add_patch(FancyBboxPatch((RX,1.05),RW,FH-2.07,boxstyle="round,pad=0.04",fc="white",ec=AQUA,lw=1.6))
    py = FH-1.32
    ax.text(RX+0.2,py,"WHY THIS LANDS — THE RESEARCH",fontsize=11.6,fontweight="bold",color=AQUA); py-=0.44
    ax.text(RX+0.2,py,"THE CATEGORY",fontsize=10.6,fontweight="bold",color=INK2); py-=0.30
    ls = textwrap.wrap(cat_snap,int((RW-0.44)/0.096))
    ax.text(RX+0.2,py,esc("\n".join(ls)),fontsize=11.0,color=INK,va="top",linespacing=1.3)
    py -= 0.245*len(ls)+0.26
    def bullets(hdr, items):
        nonlocal py
        ax.text(RX+0.2,py,hdr,fontsize=10.6,fontweight="bold",color=INK2); py-=0.30
        for it in items:
            ls = textwrap.wrap(it,int((RW-0.5)/0.096))
            ax.text(RX+0.28,py,esc("· "+"\n  ".join(ls)),fontsize=11.0,color=INK,va="top",linespacing=1.3)
            py -= 0.245*len(ls)+0.12
        py -= 0.12
    bullets("DOCUMENTED CHALLENGES", ch3)
    bullets("DOCUMENTED GOALS", gr3)
    ax.text(RX+0.2,py,"THE FIT",fontsize=10.6,fontweight="bold",color=INK2); py-=0.30
    ls = textwrap.wrap(fit,int((RW-0.44)/0.096))
    ax.text(RX+0.2,py,esc("\n".join(ls)),fontsize=11.0,color=INK,va="top",linespacing=1.3)

    ax.add_patch(FancyBboxPatch((M,0.16),FW-2*M,0.70,boxstyle="round,pad=0.05",fc="#fdeecb",ec=INK,lw=1.2))
    ax.text(FW/2,0.51,esc("\n".join(textwrap.wrap(footer,150))),fontsize=11.4,color=INK,ha="center",va="center",fontweight="bold",linespacing=1.25)
    plt.savefig(fname,dpi=185,facecolor=SURFACE); plt.close()
    print(fname,"scale",round(s,2),"aspect",round(FH/FW,2))

# ---------- BAR ----------
thread("phone_bar.png",
 "What it actually feels like — Dana, who owns The Jackrabbit",
 "No dashboard. No logins. The agent is a text thread that already did the work and just needs a yes.",
 [
  ("a","MONDAY","Saw you added DJ Mala for Friday 10pm. She's now on Google, Yelp, Apple Maps, Nextdoor, the city event calendars, your website, and OneLive. Nothing for you to do.",None),
  ("a","TUESDAY","Heads up: the promoter's flyer says 9pm but your calendar says 10pm. Which is right?",["9 PM","10 PM"]),
  ("o",None,"10pm",None),
  ("a",None,"Done. Website + OneLive: public. Google post, Instagram, Facebook: staged for your approval. City calendar: submitted, awaiting review. Yelp: monitored (partner update not active).",None),
  ("a","TWO WEEKS OUT","I made Friday's promo from your photos: an Instagram carousel, a story, a Facebook event, a Google post, a YouTube Short, and a text to your 214 regulars. There's also a $40 ad option — your account, only if you want it.",["SEE IT","POST AS PLANNED","SKIP"]),
  ("o",None,"Post as planned",None),
  ("a","FRIDAY 6PM","Tonight's reminder story is ready. One tap and it's up — door code MALA is on it so we can count who came from it.",["POST IT"]),
  ("o",None,"Done",None),
  ("a","SATURDAY","Last night: 1,400 people saw it, 310 tapped for details, 38 used MALA at the door. The carousel worked 3x better than the flyer — I'll lead with carousels next time.",None),
 ],
 "Dana's total time this week: about 12 minutes. Cost: $0 (plus the $40 she chose for her own ad). The same work from an agency: $500–$2,000/month.",
 cat_snap="Bars and nightlife rooms fighting declining default drinking — programming is the strategy, but events rarely leave the chalkboard.",
 ch3=["Events live on a chalkboard and an IG story — invisible to search and AI","No one owns marketing; the 'events person' tends bar","The NIGHT must sell now, not just the drink"],
 gr3=["Make recurring nights reliable traffic","Capture regulars into an owned list","Prove which events move the register"],
 fit="The agent publishes the programming once, catches drift, produces per-event campaigns, and reports results as door counts.")

# ---------- WINERY ----------
thread("phone_winery.png",
 "What it actually feels like — Marcus, who runs Vista Oak Cellars",
 "The visit, the bottle, and the tasting class — one calendar, one thread, everything findable.",
 [
  ("a","SEASON START","Got your Spring Release Party and the Blending 101 class. Both are now everywhere people look — Google to TripAdvisor to Vivino — and the class links to your Tock page so seats sell there. Also: Apple Maps still had your winter hours. Fixed.",None),
  ("a",None,"One idea: want to add 'join the newsletter when you book, first pour is on us'? People who join your list tend to become club members — and almost all club signups happen in the tasting room.",["YES, ADD IT","NOT NOW"]),
  ("o",None,"Yes, add it",None),
  ("a","TWO WEEKS OUT","Release-day promo is ready: carousel from your bottle shots, a story, a Facebook event, a Google post, a YouTube Short, and a club early-access email. Plus an ad option: wine lovers within 45 minutes, your account.",["SEE IT","GO","SKIP"]),
  ("o",None,"Go — and bump the ad to $60",None),
  ("a","RELEASE DAY","'We're pouring today' story is staged. The QR card by the register signs people up and gives them their free pour.",["POST IT"]),
  ("o",None,"Done",None),
  ("a","MONTH END","This month: the class sold out (12 seats), release day brought about 210 visitors, and 41 people joined your newsletter — 9 already became club members. A normal month: 6 signups. Same offer on next month's release?",["YES","LET ME THINK"]),
 ],
 "Marcus's total time this month: about 15 minutes. Cost: $0 (plus $60 he chose for ads). A comparable agency package: $1,000–$5,000/month — or this never getting done at all.",
 cat_snap="Three-sided revenue — the visit, the bottle, the experience — while tasting-room traffic declines across wine regions.",
 ch3=["Fewer default trips: every visit must be manufactured","~90% of club signups happen on premises — falling traffic starves the club","Classes and dinners: high-margin, marketed worst"],
 gr3=["Rebuild visit traffic with bookable occasions","Grow club and membership signups","Sell more experience inventory"],
 fit="One calendar feeds all three revenue lines: classes bookable via their ticketing, map hours right, club signup on every listing, offers with tracked redemption.")

# ---------- ARTIST ----------
thread("phone_artist.png",
 "What it actually feels like — Rosa, singer-songwriter",
 "She plays the shows. The agent keeps her world in order — and never touches her music.",
 [
  ("a","TUESDAY","The Listening Room just posted May 14 with your name on it. Playing that one?",["YES","NO"]),
  ("o",None,"Yes!",None),
  ("a",None,"Added. Your website, link-in-bio, OneLive, and your Bandsintown + Songkick pages all show it now. One more thing: some AI answers still use your old band name — I've re-published your correct bio and pinged the indexes so they pick up the right story.",None),
  ("a","10 DAYS OUT","Show announcement is ready — a post and story from your photos, a YouTube Short from your own clip, a Facebook event shared with the venue, and an email draft for your list. Nothing here writes your songs. Promise.",["SEE IT","POST","SKIP"]),
  ("o",None,"Post",None),
  ("a","SHOW NIGHT","Day-of story staged. The QR on your merch table adds people to YOUR mailing list — it goes with you wherever you play.",["POST IT"]),
  ("o",None,"Done",None),
  ("a","AFTER","62 people tapped the listing this week and 12 joined your list at the show. Your Austin draw is getting provable — want me to update the one-pager you send bookers?",["YES","LATER"]),
 ],
 "Rosa's time per show: about 8 minutes. Cost: $0 — basics free permanently; campaign work free for the initial period. By hand: 4–8 hours of unpaid admin per show.",
 cat_snap="The largest population in live culture: solo performers with no team, whose admin hours come straight out of the art.",
 ch3=["Admin hours come straight out of the art","Facts scattered and stale across platforms and AI answers","No owned audience — the algorithm decides"],
 gr3=["More people at the next show","A mailing list that travels with her","Provable draw for bookers"],
 fit="The agent aggregates dates from venues' calendars, corrects stale facts, and builds two portable assets: the list and documented draw.")

print("phone sheets done")
