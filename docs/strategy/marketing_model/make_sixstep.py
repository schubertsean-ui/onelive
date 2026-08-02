# -*- coding: utf-8 -*-
# The canonical six-step customer flow: PASTE -> VERIFY -> CONNECT -> APPROVE -> MEASURE -> IMPROVE
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"
LBLUE="#cde2fb"; LORANGE="#fbe0d4"; LAQUA="#d2f0e4"; LYEL="#fdeecb"
def W(t,w): return "\n".join(textwrap.wrap(t,w)).replace("$","\\$")

FW,FH=13.9,9.5
fig,ax=plt.subplots(figsize=(FW,FH))
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.set_position((0,0,1,1)); ax.set_xlim(0,FW); ax.set_ylim(0,FH); ax.axis("off")
ax.text(0.2,FH-0.4,"How it works — six steps, and what you get at each one",fontsize=19,fontweight="bold",color=INK)
ax.text(0.2,FH-0.78,"You can stop after any step and keep the basics it built — listings, calendar, widget, list. Nothing posts anywhere without your approval.",fontsize=11.8,color=INK2)

steps=[
 ("1 · PASTE","Paste your website, events page, or Instagram link.","You immediately see what 1Live found — your events, your facts, their sources — before connecting anything.",BLUE,LBLUE),
 ("2 · VERIFY","1Live assembles your calendar and identity, shows every source, and asks only about what's uncertain.","Wrong dates, stale hours, and conflicts get found before your customers find them.",AQUA,LAQUA),
 ("3 · CONNECT","You claim your listing and connect only the channels you choose. Some need your authorization or the platform's approval.","No re-typing events into five sites; your existing calendar and tools stay in charge.",ORANGE,LORANGE),
 ("4 · APPROVE","For each event, a complete campaign arrives in your voice — posts, event pages, email, ads. Edit, approve, or skip.","Hours of repetitive channel work become one decision.",BLUE,LBLUE),
 ("5 · MEASURE","Results come back in your units — attendance, signups, reservations, ticket activity — separately from views and clicks.","You see what actually reached the door, not just what got likes.",AQUA,LAQUA),
 ("6 · IMPROVE","The next event starts from what worked last time. Changes stay explainable and reversible.","Your recurring nights get easier to fill every month.",YELLOW,LYEL),
]
cw,ch,gap=4.35,3.35,0.25
for i,(t,how,val,ec,fc) in enumerate(steps):
    r,c=divmod(i,3)
    x=0.2+c*(cw+gap); y=4.55-r*(ch+0.35)
    ax.add_patch(FancyBboxPatch((x,y),cw,ch,boxstyle="round,pad=0.05",fc="white",ec=ec,lw=2.2))
    ax.text(x+0.25,y+ch-0.4,t,fontsize=15,fontweight="bold",color=ec)
    ax.text(x+0.25,y+ch-0.78,W(how,42),fontsize=11.6,color=INK,va="top",linespacing=1.35)
    ax.add_patch(FancyBboxPatch((x+0.15,y+0.15),cw-0.3,1.02,boxstyle="round,pad=0.04",fc=fc,ec=fc))
    ax.text(x+0.3,y+1.0,"WHAT YOU GET",fontsize=8.8,fontweight="bold",color=INK2)
    ax.text(x+0.3,y+0.78,W(val,44),fontsize=10.8,color=INK,va="top",linespacing=1.3)
    if c<2:
        ax.add_patch(FancyArrowPatch((x+cw,y+ch/2),(x+cw+gap,y+ch/2),arrowstyle="-|>",mutation_scale=18,color=INK2,lw=2.2))
ax.text(FW/2,0.42,"Save hours  ·  Prevent wrong dates  ·  Reach customers where they look  ·  Grow an audience you own  ·  Measure what reaches the door",
 fontsize=12.2,fontweight="bold",color=INK,ha="center")
plt.savefig("flow_sixstep.png",dpi=185,facecolor=SURFACE); plt.close()
print("sixstep done aspect",round(FH/FW,2))
