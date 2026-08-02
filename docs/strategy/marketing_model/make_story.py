# -*- coding: utf-8 -*-
# "Filled Frame" storyboard system: dense step cards, no empty lanes.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle
import textwrap

SURFACE="#fcfcfb"; INK="#0b0b0b"; INK2="#52514e"; LINE="#d8d7d3"
BLUE="#2a78d6"; ORANGE="#eb6834"; AQUA="#1baf7a"; YELLOW="#eda100"
HDR="#efeeea"
ACTOR={"o":("THE OWNER",BLUE),"a":("THE AGENT",ORANGE),"w":("WHERE IT SHOWS UP",AQUA)}

def esc(t): return t.replace("$","\\$")
def wr(t,w): return textwrap.wrap(t,w)

BODY_FS=13.8; LABEL_FS=10.8; HDR_FS=13.4; TITLE_FS=19.5; SUB_FS=12.6
LINE_H=0.258          # vertical per body line (inches==data units)
LABEL_H=0.27          # vertical per actor-label line
PAD=0.17

def card_height(entries, wrap_w):
    h=0.50+PAD  # header band + top pad
    for actor,text,tap in entries:
        h+=LABEL_H
        h+=LINE_H*len(wr(text,wrap_w))
        h+=0.10
    return h+PAD-0.10

def storyboard(fname, title, subtitle, steps, ledger=None, actor_key=None, ncols=3, figw=14.2, badge=None):
    n=len(steps); nrows=(n+ncols-1)//ncols
    gut=0.22; m=0.18
    cw=(figw-2*m-(ncols-1)*gut)/ncols
    wrap_w=int((cw-2*PAD)/0.112)   # chars per line at BODY_FS
    row_h=[]
    for r in range(nrows):
        row=steps[r*ncols:(r+1)*ncols]
        row_h.append(max(card_height(e,wrap_w) for _,e in row))
    led_h=1.18 if ledger else 0.0
    top=1.08+0.38*(len(textwrap.wrap(title,64))-1)
    figh=m+top+sum(row_h)+(nrows-1)*gut+(0.24+led_h if ledger else 0.06)+m
    fig,ax=plt.subplots(figsize=(figw,figh))
    fig.patch.set_facecolor(SURFACE); ax.set_facecolor(SURFACE)
    ax.set_position((0,0,1,1))
    ax.set_xlim(0,figw); ax.set_ylim(0,figh); ax.axis("off")
    tl="\n".join(textwrap.wrap(title,64))   # wrap clear of the badge (visual QA)
    nl=tl.count("\n")+1
    ax.text(m,figh-m-0.02,tl,fontsize=TITLE_FS,fontweight="bold",color=INK,va="top",linespacing=1.18)
    ax.text(m,figh-m-0.70-0.38*(nl-1),esc(subtitle),fontsize=SUB_FS,color=INK2)
    if badge:
        _b1,_b2=(badge.split(" — ",1)+[""])[:2]
        bw_=0.3+0.082*max(len(_b1),len(_b2))
        ax.add_patch(FancyBboxPatch((figw-m-bw_,figh-m-0.62),bw_,0.56,boxstyle="round,pad=0.05",fc="white",ec="#eda100",lw=2.0))
        ax.text(figw-m-bw_/2,figh-m-0.25,_b1,fontsize=10.4,fontweight="bold",color="#b87e00",ha="center",va="center")
        ax.text(figw-m-bw_/2,figh-m-0.49,_b2,fontsize=8.8,fontweight="bold",color="#b87e00",ha="center",va="center")
    y_top=figh-m-top
    for r in range(nrows):
        ch=row_h[r]
        y0=y_top-sum(row_h[:r+1])-r*gut
        for c in range(ncols):
            i=r*ncols+c
            if i>=n: break
            hdr,entries=steps[i]
            x0=m+c*(cw+gut)
            ax.add_patch(FancyBboxPatch((x0,y0),cw,ch,boxstyle="round,pad=0.03",fc="white",ec=LINE,lw=1.4))
            ax.add_patch(FancyBboxPatch((x0+0.05,y0+ch-0.46),cw-0.10,0.38,boxstyle="round,pad=0.02",fc=HDR,ec=HDR))
            ax.text(x0+PAD,y0+ch-0.28,f"{i+1}",fontsize=HDR_FS+1,fontweight="bold",color=INK,va="center")
            ax.text(x0+PAD+0.35,y0+ch-0.28,hdr.upper(),fontsize=HDR_FS,fontweight="bold",color=INK2,va="center")
            y=y0+ch-0.50-PAD
            for actor,text,tap in entries:
                name,col=ACTOR[actor]
                if actor_key and actor in actor_key: name=actor_key[actor]
                ax.text(x0+PAD,y,name,fontsize=LABEL_FS,fontweight="bold",color=col,va="top")
                if tap:
                    tx=x0+PAD+0.13*len(name)+0.30
                    ax.add_patch(Circle((tx,y-0.08),0.13,fc=YELLOW,ec=INK,lw=0.8))
                    ax.text(tx,y-0.08,"TAP",ha="center",va="center",fontsize=6.6,fontweight="bold",color=INK)
                y-=LABEL_H
                for ln in wr(text,wrap_w):
                    ax.text(x0+PAD,y,esc(ln),fontsize=BODY_FS,color=INK,va="top")
                    y-=LINE_H
                y-=0.10
    if ledger:
        lw_=(figw-2*m-(len(ledger)-1)*0.18)/len(ledger)
        for i,(lab,val) in enumerate(ledger):
            x0=m+i*(lw_+0.18)
            ax.add_patch(FancyBboxPatch((x0,m),lw_,led_h,boxstyle="round,pad=0.03",fc="#f4f4f2",ec=INK,lw=1.0))
            ax.text(x0+lw_/2,m+led_h-0.27,lab,ha="center",fontsize=11.2,fontweight="bold",color=INK2)
            vl=wr(val,int((lw_-0.3)/0.098))
            ax.text(x0+lw_/2,m+(led_h-0.34)/2-0.02,esc("\n".join(vl)),ha="center",va="center",fontsize=11.9,color=INK,linespacing=1.3)
    plt.savefig(fname,dpi=185,facecolor=SURFACE)
    plt.close()
    print(fname, f"{figw:.1f}x{figh:.2f} aspect {figh/figw:.2f}")

# ---------------- 1 · ONBOARDING ----------------
storyboard("flow_onboard.png",
 "The first five minutes — onboarding (identical for every edition)",
 "The hard triviality bar (canon §9a): ≤3 taps end to end · one input · no reading. Yellow badge = an owner tap; everything else is the agent working.",
 [
  ("Minute 0",[("o","Pastes ONE thing: their website or Instagram URL.",True)]),
  ("Minutes 1–3",[("a","Reads what's already public: events page, calendar/ICS, posts, photos, hours, menu, links.",False)]),
  ("Minute 3",[("o","Glances at the preview card: 'Your next 14 events — here's how you'll appear.'",True)]),
  ("Minute 4",[("o","Confirms identity — instant with domain email; quick fallback otherwise.",True)]),
  ("Minute 5",[("a","Switches on safe defaults: sync, watch, alerts, weekly note. All changeable later; none decided up front.",False)]),
  ("From here on",[("w","Live: 1Live · site widget · Google, Bing, Yelp, Foursquare, Apple, Nextdoor, city calendars · machine-readable everywhere.",False)]),
 ])

# ---------------- 2 · STANDING LOOP ----------------
storyboard("flow_loop.png",
 "The standing loop — what 'ongoing' means",
 "Runs continuously for every claimed entity. The owner's tap is ALWAYS the send button; nothing posts itself; nothing here ever affects 1Live ranking.",
 [
  ("Continuously",[("o","Nothing. Runs the business; updates the calendar the way they already do.",False),
                   ("a","Watches their calendar, pages, and the pipes for changes and drift.",False)]),
  ("When something changes",[("a","Syncs it everywhere within ~the hour; re-emits the machine-readable data.",False),
                   ("w","Site widget · 1Live · maps & listings pipes · their socials (only ever after a tap).",False)]),
  ("When something's wrong",[("a","Short alert: 'Yelp says Tuesday hours differ' / 'feed quiet 9 days.'",False),
                   ("o","One-tap fix, or dismiss.",True)]),
  ("~2 weeks before each event",[("a","Campaign kit arrives: carousel, story crops, captions in their voice, ad recipe, schedule.",False),
                   ("o","Approves / edits / skips — over coffee.",True)]),
  ("Day of",[("a","Stages the day-of reminder story.",False),
                   ("o","Taps go.",True)]),
  ("Weekly",[("a","Plain-language note: what people saw, tapped, used — and what to do differently next time.",False)]),
 ])

# ---------------- 3 · BAR / NIGHTCLUB ----------------
storyboard("flow_bar.png",
 "Use case 1 — 'The Jackrabbit', a bar with Thursday trivia + Friday DJ nights",
 "Segments 2/7 (bars · nightlife). The recurring night is the strategy; the agent makes it findable and keeps the promoter honest.",
 [
  ("Monday",[("o","Adds 'DJ Mala — Friday 10pm' to the Google Calendar she already keeps.",True)]),
  ("Within the hour",[("a","Detects it; builds the listing; updates widget + pipes; publishes the recurring trivia night for the whole quarter.",False),
              ("w","Google Search/Maps · Yelp · Foursquare · Apple Maps · Nextdoor · the city calendars · 1Live · her site — all in agreement.",False)]),
  ("Tuesday",[("a","Catches drift: the promoter's flyer says 9pm, the calendar says 10pm — asks which is true.",False),
              ("o","Taps '10pm' — every surface corrects.",True)]),
  ("12 days out",[("a","Kit arrives: 4-card carousel from her photos, captions, $40 geo-boost recipe (her ad account, her cap), SMS draft to 214 regulars.",False),
              ("o","Approves; edits one caption.",True)]),
  ("Friday 6pm",[("a","Day-of story staged; guest-list link + door code 'MALA' embedded.",False),
              ("o","Taps go.",True),
              ("w","HER SOCIALS: IG post + story + carousel · FB event + page post · GBP post · YouTube Short — each written and sized per platform.",False)]),
  ("Saturday",[("a","'1,400 saw it · 310 tapped · 38 used MALA at the door. The carousel beat the flyer 3-to-1 — leading with carousels next time.'",False)]),
 ],
 ledger=[("OWNER TIME THIS CYCLE","~12 minutes · 4 taps + one caption edit (est.)"),
         ("CASH COST","$0 agent — optional $40 boost on HER ad account"),
         ("THE SAME WORK TODAY","6–10 DIY hours, or $500–$2,000/mo freelancer/shop"),
         ("SOCIAL OUTPUTS STAGED","IG post · story · carousel — FB event · post — GBP post — YouTube Short — SMS draft")],
 badge="ILLUSTRATIVE — pilot targets, not observed results")

# ---------------- 4 · WINERY ----------------
storyboard("flow_winery.png",
 "Use case 2 — 'Vista Oak Cellars', a winery with releases, tastings & classes",
 "Segment 3 (breweries · wineries · distilleries). Three revenue sides — the visit, the bottle, the experience — one accurate calendar.",
 [
  ("Season start",[("o","Adds Spring Release Party + monthly 'Blending 101' class ($45, tickets on their Tock page).",True)]),
  ("Same day",[("a","Publishes both; the class is BOOKABLE via their ticket link; fixes Apple Maps winter hours; club signup on every listing.",False),
              ("w","Google + Business Profile · Apple Maps (hours right) · Yelp · TripAdvisor · Vivino · city calendars · 1Live · their site.",False)]),
  ("Two weeks out",[("a","Release kit: carousel from bottle shots, a YouTube Short, drive-time ad recipe ('wine lovers within 45 min'), club early-access email.",False),
              ("o","Approves; bumps the ad cap to $60.",True)]),
  ("Release Saturday",[("a","Day-of 'we're pouring today' story staged; tasting-room QR card links to club signup.",False),
              ("o","Taps go.",True),
              ("w","THEIR SOCIALS: IG carousel + story + post · FB event + page post · GBP post · YouTube Short · club email — one release, 8 formats.",False)]),
  ("Sunday market",[("a","Family-day market listing tagged 'kid-friendly · no reservation' — reaches the daytime audience the enthusiast pipes miss.",False)]),
  ("Month end",[("a","'Class sold out (12 seats) · release day: 210 visitors · 9 new club signups traced to the QR · Tuesday is still quiet — try a locals' night?'",False)]),
 ],
 ledger=[("OWNER TIME THIS CYCLE","~15 minutes across the month · 3 taps (est.)"),
         ("CASH COST","$0 agent — optional $60 ads on THEIR account"),
         ("THE SAME WORK TODAY","agency package $1,000–$5,000/mo, or it simply doesn't happen"),
         ("SOCIAL OUTPUTS STAGED","IG carousel · story · post — FB event · post — GBP post — YouTube Short — club email")],
 badge="ILLUSTRATIVE — pilot targets, not observed results")

# ---------------- 5 · SOLO ARTIST ----------------
storyboard("flow_artist.png",
 "Use case 3 — 'Rosa M.', solo singer-songwriter (Artist edition, SOLO tier)",
 "Segment 19. A person-brand, not a place: her dates live across many rooms; the agent defends her facts and never touches her art.",
 [
  ("Tuesday",[("o","Gets booked at The Listening Room, May 14. Does nothing else — the venue posts its calendar.",False)]),
  ("Within the hour",[("a","Sees her name on the venue's listing; asks: 'Playing The Listening Room May 14?' One tap: yes.",True)]),
  ("Same week",[("a","Publishes to HER schedule: site, link-in-bio, 1Live, her Bandsintown artist page. Fixes a stale AI fact (her old band name) with her correct bio.",False),
              ("w","Search & AI answers about ROSA: right bio, right links, right next show — her words, everywhere.",False)]),
  ("10 days out",[("a","Announcement kit in her voice, from her photos: post + story + 'add to calendar' link + mailing-list signup. Nothing generated touches her music or artwork.",False),
              ("o","Approves from the bus.",True)]),
  ("Show night",[("o","Taps the staged day-of story; merch-table QR goes to her list.",True),
              ("w","HER SOCIALS: IG announcement post + story · FB event (cross-tagged with the venue) · link-in-bio updated · mailing-list email draft.",False)]),
  ("After",[("a","'62 taps on the listing · 12 new list signups · your Austin draw is now provable — want the booker one-pager updated?'",False)]),
 ],
 actor_key={"o":"ROSA"},
 ledger=[("ROSA'S TIME PER SHOW","~8 minutes · 3 taps (est.)"),
         ("CASH COST","$0 — basics free permanently; campaign work free for the initial period"),
         ("THE SAME WORK TODAY","4–8 DIY hours per announcement cycle — unpaid artist admin"),
         ("SOCIAL OUTPUTS STAGED","IG post · story — FB event w/ venue — YouTube Short — link-in-bio — list email")],
 badge="ILLUSTRATIVE — pilot targets, not observed results")

# ---------------- 6 · PROMOTION RIPPLE ----------------
storyboard("flow_promo.png",
 "The payoff — a promotion becomes ONE LINE: 'Sign up at the tasting, first pour free'",
 "Every surface is already connected, so promoting something new is a single edit that ripples everywhere — signup, redemption, and measurement come built.",
 [
  ("The idea",[("o","Adds ONE line to the tasting event: 'Newsletter signup at booking → first pour free.'",True)]),
  ("Within the hour",[("a","Attaches the offer everywhere the event lives; the signup link now carries the benefit; tasting-room QR card regenerated.",False),
              ("w","Google · Apple Maps · Yelp · Nextdoor · city calendars · 1Live · their site — ALL show the tasting WITH the offer; AI can cite it.",False)]),
  ("The kit",[("a","Offer-forward kit: carousel + GBP post with the benefit callout, captions, boost recipe (their ad account), club email draft.",False),
              ("o","Approves over coffee.",True)]),
  ("At the tasting",[("a","QR at the bar: signup captures to THEIR list; pour redemption logged with a code — no new hardware, no POS change.",False)]),
  ("Two weeks later",[("o","Decides it's working — 'extend two weeks, add Sundays.' Edits the one line.",True),
              ("a","Every surface updates within the hour — no platform logins, no re-posting, no chasing.",False)]),
  ("Measured",[("a","'41 signups (vs 6 baseline) · 33 pours redeemed · 9 became club members — the offer out-earned its cost ~4x (est.)'",False)]),
 ],
 ledger=[("OWNER TIME, WHOLE CAMPAIGN","~10 minutes over a month · 3 taps (est.)"),
         ("CASH COST","$0 agent — ads optional, on their account, their cap"),
         ("THE SAME CAMPAIGN TODAY","an agency project ($1–3k) plus list tooling — or never attempted"),
         ("WHY THIS OFFER","email is the $36–42-per-$1 channel the research found sitting unused")],
 badge="ILLUSTRATIVE — pilot targets, not observed results")

print("storyboards done")


# ---------------- MERGED: onboarding + standing loop, one page ----------------
storyboard("flow_onboardloop.png",
 "From the first paste to the standing loop",
 "Steps 1–6: the first five minutes (≤3 taps, one input). Steps 7–12: ongoing — nothing posts itself; nothing affects ranking.",
 [
  ("Minute 0",[("o","Pastes ONE thing: their website or Instagram URL.",True)]),
  ("Minutes 1–3",[("a","Reads what's public: events, calendar, posts, photos, hours, links.",False)]),
  ("Minute 3–4",[("o","Glances at the preview card; confirms identity.",True)]),
  ("Minute 5",[("a","Switches on safe defaults: sync, watch, alerts, weekly note — all changeable later.",False)]),
  ("From here on",[("w","Live: 1Live · site widget · Google, Bing, Yelp, Foursquare, Apple, Nextdoor + city calendars — machine-readable everywhere.",False)]),
  ("Continuously",[("a","Watches their calendar, pages, and the pipes for changes and drift.",False)]),
  ("Something changes",[("a","Syncs it everywhere within ~the hour.",False),
                   ("w","Widget · 1Live · pipes · socials (after a tap).",False)]),
  ("Something's wrong",[("a","Alert: 'Yelp says Tuesday hours differ.'",False),
                   ("o","One-tap fix, or dismiss.",True)]),
  ("~2 weeks out",[("a","Campaign kit arrives: carousel, crops, captions, ad recipe, schedule.",False),
                   ("o","Approves / edits / skips.",True)]),
  ("Day of",[("a","Stages the day-of story.",False),
                   ("o","Taps go.",True)]),
  ("Weekly",[("a","Plain-language note: what people saw, tapped, used — and what to try next.",False)]),
  ("Always",[("w","Their basics stay right everywhere — and every send needed their tap.",False)]),
 ], ncols=4)
