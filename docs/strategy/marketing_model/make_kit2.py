# -*- coding: utf-8 -*-
# Campaign kit v2: carousel + channel posts rebuilt on the ratified behavioral
# architecture (design brief v2.4 §3 + §6): hook, emotion, one idea per card,
# curiosity gap, investment — white-hat only. Overwrites cs_kit.png; adds cs_channels.png.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Polygon
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; LINE="#d8d7d3"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"
LYEL="#fdeecb"; RED="#8e2f22"; CREAM="#f6ead2"; DARK="#2a1613"

def esc(t): return t.replace("$","\\$")
def W(t,w): return esc("\n".join(textwrap.wrap(t,w)))

FW,FH=14.2,9.7
def canvas(title, sub, badge="DEMONSTRATED (drafted, never published)", bcol=AQUA):
    fig,ax=plt.subplots(figsize=(FW,FH))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    ax.set_position((0,0,1,1)); ax.set_xlim(0,FW); ax.set_ylim(0,FH); ax.axis("off")
    ax.text(0.2,FH-0.38,title,fontsize=19,fontweight="bold",color=INK)
    ax.text(0.2,FH-0.76,esc(sub),fontsize=11.8,color=INK2)
    if badge:
        bw_=0.3+0.104*len(badge)
        ax.add_patch(FancyBboxPatch((FW-0.2-bw_,FH-0.52),bw_,0.4,boxstyle="round,pad=0.05",fc="white",ec=bcol,lw=2.0))
        ax.text(FW-0.2-bw_/2,FH-0.32,badge,fontsize=9.6,fontweight="bold",color=bcol,ha="center",va="center")
    return fig,ax

def chip(ax,x,y,label,col):
    w=0.3+0.112*len(label)
    ax.add_patch(FancyBboxPatch((x,y-0.17),w,0.36,boxstyle="round,pad=0.04",fc="white",ec=col,lw=1.7))
    ax.text(x+w/2,y+0.01,label,fontsize=9.8,fontweight="bold",color=col,ha="center",va="center")
    return w

def play(ax,cx,cy,r=0.22,col="white"):
    ax.add_patch(Circle((cx,cy),r,fc="none",ec=col,lw=2.0))
    ax.add_patch(Polygon([(cx-r*0.32,cy+r*0.5),(cx-r*0.32,cy-r*0.5),(cx+r*0.55,cy)],fc=col,ec=col))

# ================= PAGE: THE CAROUSEL, v2 =================
fig,ax=canvas("Artifact 3 — the carousel on the engagement structure (video-first, sound on)",
 "One idea per card · attention → emotion → fact → curiosity → action (brief v2.4 §3/§6). Media: their OWN footage and live audio, via an IG Collab post.")

SW,SH=2.55,3.3; y0=4.95; gap=0.22
slides=[
 # (frame color, is_video, headline, subline, principle chip, why line)
 (DARK,True,"[ 0–3 s: their live clip,\nhorns hit, crowd up ]","SOUND ON",
  ("ATTENTION · THE HOOK",ORANGE),
  "Motion + their real live audio in frame one — the scroll-stopper. Honestly earned: it IS the show."),
 (RED,False,"Saturday night\nin the oldest club\non South Congress.","[ the room, mid-set ]",
  ("EMOTION",BLUE),
  "One sensory line — anticipation + calm certainty (§3). No adjectives sold; the room does the work."),
 (CREAM,False,"THE PETERSON\nBROTHERS","SAT AUG 29 · 8 PM",
  ("ONE IDEA PER CARD",AQUA),
  "The fact card: who, when — nothing else. A card is a hook, not a summary (§6C)."),
 (DARK,True,"blues, soul & funk —\nthe Saturday residency\nAustin lines up for","▶ hear 30 seconds",
  ("CURIOSITY GAP",YELLOW),
  "Spark-line built from THEIR own genre words opens a question only the preview or the night answers (§6C)."),
 (RED,False,"BE IN\nTHE ROOM","tickets → link in bio\n· or the door · save this",
  ("ACTION + INVESTMENT",ORANGE),
  "One thumb, one tap (§6A). 'Save this for Saturday' = the small investment that compounds."),
]
for i,(fc_,vid,head,sub_,pr,why) in enumerate(slides):
    x=0.2+i*(SW+gap)
    tcol = CREAM if fc_ in (DARK,RED) else RED
    ax.add_patch(FancyBboxPatch((x,y0),SW,SH,boxstyle="round,pad=0.03",fc=fc_,ec=INK,lw=1.8))
    ax.text(x+SW/2,y0+SH-0.24,f"{i+1}/5",fontsize=9.6,color=tcol,ha="center")
    if vid:
        play(ax,x+SW/2,y0+SH-0.95,0.26,tcol)
        ax.text(x+SW/2,y0+SH-1.85,head,fontsize=10.4,color=tcol,ha="center",va="center",linespacing=1.35,style="italic" if i==0 else "normal",fontweight="normal" if i==0 else "bold")
    else:
        ax.text(x+SW/2,y0+SH-1.55,head,fontsize=11.8 if i!=2 else 13.4,fontweight="bold",color=tcol,ha="center",va="center",linespacing=1.3)
    ax.text(x+SW/2,y0+0.46,sub_,fontsize=10.0,color=tcol,ha="center",va="center",linespacing=1.25,fontweight="bold" if i in (0,4) else "normal")
    if vid and i==0:
        ax.text(x+SW-0.16,y0+SH-0.24,"((( )))",fontsize=6.8,color=tcol,ha="right",fontweight="bold")
    # principle chip + why, under the slide
    chip(ax,x,y0-0.36,pr[0],pr[1])
    yy=y0-0.76
    for ln in textwrap.wrap(why,31):
        ax.text(x,yy,esc(ln),fontsize=10.2,color=INK2,va="top"); yy-=0.26

# media & rights strip
ax.add_patch(FancyBboxPatch((0.2,1.15),8.3,1.9,boxstyle="round,pad=0.05",fc="white",ec=BLUE,lw=1.8))
ax.text(0.45,2.78,"WHERE THE AUDIO & VIDEO COME FROM (never generated)",fontsize=12.2,fontweight="bold",color=BLUE)
for i,ln in enumerate(["Clips 1 & 4: the band's and the club's own posted live footage + live audio, via an IG COLLAB post","with @ the band — their approval built in, posts to BOTH audiences at once (their fans + the club's).",
 "No usable clip? Fallback: their photos + IG's licensed-audio picker (their released track). The agent","never fabricates the band's sound or image — artist rule: nothing generated touches their art."]):
    ax.text(0.45,2.46-i*0.33,esc(ln),fontsize=11.0,color=INK)
ax.add_patch(FancyBboxPatch((8.8,1.15),5.2,1.9,boxstyle="round,pad=0.05",fc=LYEL,ec=INK,lw=1.4))
ax.text(9.0,2.78,"THE REFLECTION TEST (charter)",fontsize=12.2,fontweight="bold",color=INK)
ax.text(9.0,2.5,W("Shown how each card influences them, a viewer would say 'that's what I wanted anyway': the hook is the actual band, the emotion the actual room, the CTA the actual door. No scarcity theater.",56),fontsize=10.6,color=INK,va="top",linespacing=1.35)
ax.text(0.2,0.62,"Owner's involvement unchanged: approve or edit, then tap — the structure is the agent's job, not theirs.",fontsize=11.4,color=INK2,style="italic")
plt.savefig("cs_kit.png",dpi=185,facecolor=SURFACE); plt.close()
print("cs_kit v2")

# ================= PAGE: EVERY CHANNEL, SAME SPINE =================
fig,ax=canvas("Artifact 3b — the same engagement spine on every channel (and when each one fires)",
 "Attention · emotion · one idea · one action — re-expressed per platform, never copy-pasted. Every send staged for the owner's tap, timed to the canon's 6–9 pm window.")

def block(x,y,w,title,tcol,rows,chips_):
    # rows: list of (label, text); chips_: list of (label,col)
    hh=0.56
    for lab,txt in rows: hh+=0.27+0.27*len(textwrap.wrap(txt,int(w*6.6)))
    hh+=0.5
    ax.add_patch(FancyBboxPatch((x,y-hh),w,hh,boxstyle="round,pad=0.04",fc="white",ec=tcol,lw=1.8))
    ax.text(x+0.2,y-0.36,title,fontsize=12.4,fontweight="bold",color=tcol)
    yy=y-0.72
    for lab,txt in rows:
        ax.text(x+0.2,yy,lab,fontsize=9.8,fontweight="bold",color=INK2,va="top"); yy-=0.27
        for ln in textwrap.wrap(txt,int(w*6.6)):
            ax.text(x+0.2,yy,esc(ln),fontsize=11.6,color=INK,va="top"); yy-=0.27
        yy-=0.03
    cx=x+0.2
    for lab,col in chips_:
        cx+=chip(ax,cx,yy-0.14,lab,col)+0.14
    return hh

colw=6.75
h1=block(0.2,8.5,colw,"REEL — 15-second cut of THEIR live clip (also posts as a YouTube Short)",RED,
 [("0–2 s · ATTENTION","horns hit mid-phrase, sound on — no intro card, no logo"),
  ("2–8 s · EMOTION","one slow pan of the packed room; overlay: 'Saturday night, since 1955'"),
  ("8–15 s · ONE IDEA → ACTION","'THE PETERSON BROTHERS · SAT AUG 29 · 8 PM' — then 'tickets: link in bio · or the door' + save")],
 [("THEIR FOOTAGE + AUDIO",BLUE),("COLLAB POST",AQUA)])
h2=block(0.2,8.5-h1-0.25,colw,"FACEBOOK EVENT — the hook lives in the first line",BLUE,
 [("LINE 1 · ATTENTION+EMOTION","The oldest club on South Congress, on a Saturday night."),
  ("BODY · ONE IDEA → ACTION","The Peterson Brothers — blues, soul & funk. Sat Aug 29, 8–9:30 pm · ticket link · their live clip as the event video")],
 [("VIDEO ATTACHED",RED),("ONE CTA",ORANGE)])
x2=0.2+colw+0.3
h3=block(x2,8.5,colw,"GOOGLE BUSINESS POST — attention = the photo + first four words",AQUA,
 [("OPEN · ATTENTION","'Live Saturday: blues & soul' — the four words search shows first"),
  ("BODY · ONE IDEA","The Peterson Brothers residency, 8 pm Aug 29. Open till 2 am. 1315 S Congress."),
  ("ACTION","'Buy tickets' button → their Eventbrite (takes video or their stage photo)")],
 [("SEARCH-FACING",BLUE)])
h4=block(x2,8.5-h3-0.25,colw,"SMS + EMAIL — one idea, sent when the itch starts",ORANGE,
 [("SMS · SAT ~5 PM","'Peterson Brothers tonight, 8pm. The Saturday one. — Continental Club'"),
  ("EMAIL SUBJECT · CURIOSITY","'Saturday, 8pm — you know the one' · poster image, one paragraph, one button"),
  ("TIMING RULE","every channel staged into the 6–9 pm decision window (Thu reminder · Sat ~5 pm)")],
 [("6–9 PM WINDOW",YELLOW),("ONE IDEA",AQUA)])
ax.add_patch(FancyBboxPatch((0.2,0.18),13.6,0.8,boxstyle="round,pad=0.05",fc=LYEL,ec=INK,lw=1.2))
ax.text(7.0,0.58,W("Same spine, every surface, zero copy-paste — plus the synced layer underneath: maps, Yelp, Nextdoor, city calendars, and the AI indexes kept current automatically. Every posted piece ships only on the owner's tap.",130),
 fontsize=11.4,color=INK,ha="center",va="center",fontweight="bold")
plt.savefig("cs_channels.png",dpi=185,facecolor=SURFACE); plt.close()
print("cs_channels")
