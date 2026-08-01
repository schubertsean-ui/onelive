# -*- coding: utf-8 -*-
# The demand engine as a full-page hub-band + destination grid.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"; LYEL="#fdeecb"

def wrap(t,w): return "\n".join(textwrap.wrap(t,w)).replace("$","\\$")

fig,ax=plt.subplots(figsize=(13.9,9.7))
fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
ax.set_position((0,0,1,1)); ax.set_xlim(0,13.9); ax.set_ylim(0,9.7); ax.axis("off")
ax.text(0.2,9.32,"The demand engine — one calendar in, content out where demand forms",fontsize=19,fontweight="bold",color=INK)
ax.text(0.2,9.0,wrap("Cleanup of existing listings happens once, as the floor. The ongoing product is outbound: the agent MAKES marketing content from their calendar, photos, and voice, and FEEDS it to every channel that creates demand — growth, attendance, sales.",125),fontsize=11.8,color=INK2,va="top")

# hub band
ax.add_patch(FancyBboxPatch((0.2,6.75),13.5,1.3,boxstyle="round,pad=0.05",fc=LYEL,ec=INK,lw=2.2))
ax.text(6.95,7.62,"ONE SOURCE OF TRUTH — their calendar + photos + voice",fontsize=15.5,fontweight="bold",color=INK,ha="center")
ax.text(6.95,7.14,"raw material the agent turns into listings, posts, stories, ads, and emails — synced and re-checked continuously",fontsize=12.2,color=INK,ha="center")

cards=[
 ("SEARCH & MAPS","Google Business Profile · Search · Maps · 'Things to do' · Bing Places · Apple Maps · Nextdoor","fresh event content = high-intent discovery tonight; 76% of local searchers visit within 24h"),
 ("DISCOVERY APPS & DATABASES","Yelp · Foursquare · Bandsintown · city calendars (Do512-class) · TripAdvisor / Untappd / Vivino by segment","the databases AI tools pull from — ~70% of ChatGPT local draws on them; feed them and you ARE the answer"),
 ("AI ASSISTANTS & ANSWER ENGINES","ChatGPT · Gemini · Perplexity · voice — fed via Bing/IndexNow, open AI-crawler access, and the databases at left","45% of consumers now ask AI where to go — GEO is mechanical: feed the sources, stay crawlable, stay fresh"),
 ("THEIR OWN PROPERTY","website events widget (always current, machine-readable) · link-in-bio · email/SMS list","email returns $36–42 per $1 — the list the agent grows at every touch"),
 ("ONELIVE","verified listing · confirmed states · agent-readable endpoint (Phase C)","night-of deciders in the city, seeing your events as verified"),
 ("THEIR SOCIALS (staged)","Instagram: feed post · story · carousel — Facebook: event + page post — Google Business posts — YouTube Short — ad variants","one event, 8+ formats, written and sized per platform — sent ONLY on their tap"),
]
cw=4.43; gap=0.11
for i,(t,items,note) in enumerate(cards):
    r,c=divmod(i,3)
    x=0.2+c*(cw+gap); y=3.5-r*3.05
    h=2.9
    ax.add_patch(FancyBboxPatch((x,y),cw,h,boxstyle="round,pad=0.04",fc="white",ec=AQUA,lw=1.8))
    ax.text(x+cw/2,y+h-0.32,t,ha="center",fontsize=13,fontweight="bold",color=INK)
    ax.text(x+cw/2,y+h-0.62,wrap(items,34),ha="center",va="top",fontsize=11.8,color=INK,linespacing=1.3)
    ax.text(x+cw/2,y+0.16,wrap("→ "+note,40),ha="center",va="bottom",fontsize=10.6,color=INK2,style="italic",linespacing=1.25)
    if r==0:
        ax.add_patch(FancyArrowPatch((x+cw/2,6.75),(x+cw/2,y+h+0.02),arrowstyle="-|>",mutation_scale=15,color=ORANGE,lw=2.0))
plt.savefig("flow_fanout.png",dpi=185,facecolor=SURFACE); plt.close()
print("fanout grid done")
