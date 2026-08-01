# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"
LBLUE="#cde2fb"; LORANGE="#fbe0d4"; LYEL="#fdeecb"; LAQUA="#d2f0e4"
def wrap(t,w): return "\n".join(textwrap.wrap(t,w)).replace("$","\\$")

# ---------- GLANCE: both sides, full page ----------
FW,FH=13.6,9.5
fig,ax=plt.subplots(figsize=(FW,FH))
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.set_position((0,0,1,1)); ax.set_xlim(0,FW); ax.set_ylim(0,FH); ax.axis("off")

def card(x0, ec, header, rows):
    ax.add_patch(FancyBboxPatch((x0,0.85),6.25,8.05,boxstyle="round,pad=0.1",fc="white",ec=ec,lw=2.6))
    ax.text(x0+3.125,8.28,header,ha="center",fontsize=16,fontweight="bold",color=ec)
    y=7.55
    for lab,txt in rows:
        ax.text(x0+0.42,y,lab,fontsize=12.5,fontweight="bold",color=INK2)
        lines=wrap(txt,46)
        n=len(lines.split("\n"))
        ax.text(x0+0.42,y-0.46,lines,fontsize=14.2,color=INK,va="top",linespacing=1.42)
        y-=0.72+0.475*n
card(0.35, BLUE, "FOR A BUSINESS, ORG, OR ARTIST", [
 ("WHAT","A free agent that publishes their events everywhere people look, and drafts their marketing."),
 ("HOW","Set up from one pasted link. Every send needs their approval; everything runs on their accounts."),
 ("EXPECTED OUTCOMES","Higher attendance, a larger direct list, more sales — for minutes of their time per week. Basics free permanently; ongoing campaign work free for an initial period."),
])
card(7.0, AQUA, "FOR ONELIVE", [
 ("WHAT","Verified, first-party event data from claimed businesses and artists."),
 ("HOW","Claimed calendars enter the verification pipeline as a trusted channel — still gated, never auto-published."),
 ("EXPECTED OUTCOMES","A more accurate, more complete feed; growing supply and consumer use. Each side's growth feeds the other."),
])
ax.add_patch(FancyArrowPatch((6.72,5.7),(7.18,5.7),arrowstyle="-|>",mutation_scale=20,color=YELLOW,lw=3.0,connectionstyle="arc3,rad=-0.5"))
ax.add_patch(FancyArrowPatch((7.18,3.6),(6.72,3.6),arrowstyle="-|>",mutation_scale=20,color=YELLOW,lw=3.0,connectionstyle="arc3,rad=-0.5"))
ax.text(6.8,0.4,"detail on the following pages: the flows, the mechanics, three worked examples, the full data model",ha="center",fontsize=11.5,color=INK2,style="italic")
plt.savefig("flow_glance.png",dpi=185,facecolor=SURFACE); plt.close()
print("glance done  aspect", round(FH/FW,2))

# ---------- HIGH LEVEL: the two flows, full page ----------
FW,FH=13.6,9.5
fig,ax=plt.subplots(figsize=(FW,FH))
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.set_position((0,0,1,1)); ax.set_xlim(0,FW); ax.set_ylim(0,FH); ax.axis("off")
ax.text(0.2,9.05,"The flows, at a glance",fontsize=19.5,fontweight="bold",color=INK)

ax.text(0.2,8.25,"FOR THE BUSINESS OR ARTIST — five steps, three taps",fontsize=13.5,fontweight="bold",color=BLUE)
owner=[("PASTE","one URL — website or Instagram","1 minute"),
       ("IT LEARNS THEM","their calendar, photos, voice, look","minutes, automatic"),
       ("BASICS HANDLED","correct everywhere people check — once, then kept","week one, then background"),
       ("MARKETING FLOWS","posts, stories, video, events, emails, ads — drafted, sent on their tap","every event, ~3 taps"),
       ("MEASURED RESULTS","attendance · list growth · sales, in their numbers","every week")]
cw=2.56; x0=0.2
for i,(t,b,tag) in enumerate(owner):
    x=x0+i*(cw+0.12)
    ax.add_patch(FancyBboxPatch((x,5.35),cw,2.55,boxstyle="round,pad=0.05",fc=(LORANGE if i==3 else LBLUE if i<3 else LYEL),ec=(ORANGE if i==3 else BLUE if i<3 else YELLOW),lw=2.0))
    ax.text(x+cw/2,7.5,t,ha="center",fontsize=12.2,fontweight="bold",color=INK)
    ax.text(x+cw/2,6.5,wrap(b,19),ha="center",va="center",fontsize=12.4,color=INK,linespacing=1.35)
    ax.text(x+cw/2,5.08,tag,ha="center",fontsize=10.2,color=INK2,style="italic")
    if i: ax.add_patch(FancyArrowPatch((x-0.12,6.6),(x,6.6),arrowstyle="-|>",mutation_scale=16,color=INK2,lw=2.0))

ax.text(0.2,4.5,"FOR ONELIVE — four steps, one loop",fontsize=13.5,fontweight="bold",color=AQUA)
ol=[("CULTURE FLOWS IN","two paths: the open web we read + calendars businesses connect through the agent (verified, first-party)"),
    ("VERIFICATION","AI extracts, never publishes; corroboration sets the confidence state; disputed always shown"),
    ("DISTRIBUTION","/tonight · their sites & socials · the AI-answer layer — verified data where people decide"),
    ("RESULTS RETURN","measured attendance and sales increase claiming and retention — supply and accuracy compound")]
cw2=3.23
for i,(t,b) in enumerate(ol):
    x=x0+i*(cw2+0.12)
    ax.add_patch(FancyBboxPatch((x,1.55),cw2,2.6,boxstyle="round,pad=0.05",fc=(LYEL if i==3 else LAQUA),ec=(YELLOW if i==3 else AQUA),lw=2.0))
    ax.text(x+cw2/2,3.75,t,ha="center",fontsize=12.6,fontweight="bold",color=INK)
    ax.text(x+cw2/2,2.75,wrap(b,30),ha="center",va="center",fontsize=12.2,color=INK,linespacing=1.35)
    if i: ax.add_patch(FancyArrowPatch((x-0.12,2.85),(x,2.85),arrowstyle="-|>",mutation_scale=16,color=INK2,lw=2.0))
ax.add_patch(FancyArrowPatch((13.15,1.5),(1.3,1.0),arrowstyle="-|>",mutation_scale=20,color=YELLOW,lw=2.8,connectionstyle="arc3,rad=-0.1"))
ax.text(6.9,0.5,"step four feeds step one — a compounding loop",fontsize=11.5,color=INK2,style="italic",ha="center")
plt.savefig("flow_highlevel.png",dpi=185,facecolor=SURFACE); plt.close()
print("highlevel done  aspect", round(FH/FW,2))
