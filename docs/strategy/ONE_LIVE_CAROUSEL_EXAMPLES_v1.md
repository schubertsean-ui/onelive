# ONE LIVE — Carousel Examples, Cadence & Metrics v1 (2026-07-24)

Greppable summary: founder-directed same-day follow-up to the Meta
carousel engine ("The carousels should be '5' or '7' 'blank' to
experience Today or Tonight or This Weekend … only ever show content
that is to happen … Create a world class cadre of actual carousel
content for 5 different categories/combos … date night, music and
dancing … What are world class practices for how many run per day? What
are key metrics we'll gather and analyze?"). This doc: (A) the five
scenario carousels RENDERED BY THE SHIPPED ENGINE, (B) the
posts-per-day research answer, (C) the metrics answer. Engine spec:
`ONE_LIVE_META_CAROUSEL_ENGINE_v1.md`; scenario definitions:
`social/carousel/scenarios.py` (grounded in the voice-search personas
doc); fixtures: `social/carousel/example_fixtures.py`.

**Honesty header, before anything else:** every event below is
**SYNTHETIC** — invented artists and venues in plausible Austin shapes,
clearly sentinel-marked in the fixture file, used only to demonstrate
format and to regression-test the scenario path. No real listing is
implied. The moment real canonical events exist in volume, these same
five scenarios render from live data with zero code changes. What IS
real: every slide you see was produced by the actual shipped generator
(test-pinned), under the real trust rules — future-only windows, exact
listicle promises, provenance-required descriptors, banned-claim scans.

## A. The five scenario carousels (engine output, verbatim)

All rendered at the reference moment **Friday 2026-07-24, 4:00 pm
Austin** — so Tonight = this evening, Today = the rest of Friday, This
weekend = Fri–Sun. The fixture set deliberately includes a 12:00 pm show (`ex-28`): it
appears in NO carousel below — an end-to-end demonstration of
already-started exclusion at the 4:00 pm reference. The exact
6pm-excludes-5:30 boundary (and the starts-at-this-instant edge) is
pinned by unit tests in `tests/test_social_carousel.py`.

### 1 · Date Night (personas #11 "The Date Night" + #8 "The Jazz Date")
Domains: live music · symphony/opera · theater · food & drink; starts ≥ 8pm
(the "dinner first" bias — mood filtering stays out until the Emotion &
Vibe proposal is ratified).

- **Slide 1 (hook):** 5 date nights to experience Tonight
- **Slide 2:** Two-Hander: 'The Lighthouse Keepers' — Pocket Stage ATX · 20:00 — From $22
- **Slide 3:** Rooftop Strings: Duo Luna — The Perch at 6th · 20:00 — From $25
- **Slide 4:** Wine Flight + Vinyl Night — Cork & Groove · 20:30 — From $18
- **Slide 5:** The Midnight Brass — Red River Room · 21:00 — From $15 — *"Horns that start a party"* (Foundry descriptor, provenance-carried)
- **Slide 6:** Late Bites & Bossa Nova — Verdine's Courtyard · 21:00 — Free
- **Slide 7 (CTA):** Send this to the friend who's always down
- **Caption:** "Somewhere in Austin tonight there's a room that's about to go off. 5 candidates inside. / Real listings, real sources. [UTM link]"
- **Hashtags:** #austin #austinevents #austintheater #austinsymphony #austinfoodie

### 2 · Music & Dancing (persona #7 — the founder's own example — + #9 "The Cheap Dancer")
Domains: live music · nightlife · dance.

- **Slide 1 (hook):** 7 couch-defeating plans to experience Tonight
- **Slide 2:** Two-Step Tuesday's Friday Edition — Broken Wheel Hall · 20:00 — From $10
- **Slide 3:** Salsa Social + Beginner Lesson — Plaza Azul · 20:30 — Free
- **Slide 4:** The Midnight Brass — Red River Room · 21:00 — From $15
- **Slide 5:** Porch Songs: Open Stage — The Front Steps · 21:00 — Free
- **Slide 6:** Casa de Cumbia — La Esquina Patio · 22:00 — Free — *"Cumbia until the lights come up"*
- **Slide 7:** DJ Meridian: Motown to House — The Basement Line · 22:30 — From $5
- **Slide 8:** Analog Synth Night — Circuit Chapel · 23:00 — From $12
- **Slide 9 (CTA):** Tag who you're taking
- **Caption:** "Tonight in Austin. 7 real ones. / Real listings, real sources. [UTM link]"
- **Hashtags:** #austin #austinevents #austindance #austinlivemusic #austinnightlife

### 3 · Weekend Planner (persona #5 "The Planner")
Cross-domain best-of, window = Fri–Sun, dates on every slide (beyond a
same-day window the date is part of the fact).

- **Slide 1 (hook):** 7 weekend plans to experience This weekend
- **Slides 2–8:** Gallery Crawl (Fri 18:00, Free) · 'The Lighthouse Keepers' (Fri 20:00, $22) · Open-Air Comedy Hour (Fri 20:00, Free) · Wine Flight + Vinyl (Fri 20:30, $18) · The Midnight Brass (Fri 21:00, $15) · Late Bites & Bossa Nova (Fri 21:00, Free) · Porch Songs (Fri 21:00, Free)
- **Slide 9 (CTA):** Save this for the plan
- **Caption:** list-style — "7 events. This weekend, Austin:" + the first five as bullets + link
- **Hashtags:** #austin #austinevents #austinartopening #austintheater #austincomedy

### 4 · Free Tonight (the price axis — personas #9/#14)
All domains where free happens; price filter `== $0`, mechanical.

- **Slide 1 (hook):** 5 free nights to experience Tonight
- **Slides 2–6:** Gallery Crawl (18:00) · Neighborhood Night Market (18:30) · Open-Air Comedy Hour (20:00) · Porch Songs: Open Stage (21:00) · Casa de Cumbia (22:00) — all marked Free
- **Slide 7 (CTA):** Send this to the friend who's always down
- **Hashtags:** #austin #austinevents #austinartopening #austincommunity #austincomedy

### 5 · Family Day (Family & Youth + Place-based + Library + Seasonal — a DAYTIME window)
Timeframe **Today**, not Tonight — a 4:15 pm storytime is honest here
and would be refused from a "Tonight" carousel.

- **Slide 1 (hook):** 5 family adventures to experience Today
- **Slides 2–6:** Storytime Under the Oaks (16:15, Free) · Dino Dig Pop-Up (16:30, Free) · Family Puppet Matinee (17:00, $8) · Junior Ranger Creek Walk (17:30, Free) · Sunset Kite Hour (19:00, Free)
- **Slide 7 (CTA):** Save this for the plan
- **Hashtags:** #austin #austinevents #austinlibrary #austinfamilyfun #austinexplore

## B. How many per day — the world-class cadence answer

What the research consistently shows (and what the engine encodes):

1. **Consistency beats volume.** Platform guidance and the large
   posting-frequency studies (Socialinsider, Hootsuite, Buffer,
   2024–2026) converge on: brand accounts see engagement-per-post decline
   past ~1–2 feed posts/day; Instagram's own leadership has repeatedly
   said a few quality feed posts per week plus daily Stories outperforms
   feed-flooding. BUT —
2. **Local-media accounts are the exception that fits us.** Accounts
   whose product IS fresh daily inventory (city guides, "tonight in
   <city>" media) sustain 1–3 feed posts/day because every post is a new
   edition, not a repeat ask. OneLive is structurally this case: tonight
   is a genuinely new edition every day.
3. **The recommendation (founder dial, spec §9.4):**
   - **Start: 1–2/day.** The Tonight flagship every day at the learned
     late-afternoon slot (the Duhigg cue), plus ONE rotating scenario
     (Date Night Thu/Fri, Music & Dancing Fri/Sat, Free Tonight
     mid-week, Family Day weekend mornings). Weekend Planner posts
     Thursday or Friday.
   - **Hard cap 2 feed carousels/day + Stories reshares** until the data
     says otherwise. Scale only when the fatigue dials stay healthy for
     2+ weeks: reach-per-post trend flat-or-rising AND
     impressions/reach ratio not decaying (both in the ledger).
   - Every cadence change is founder-ratified; the bandit learns the
     *slot within* the ratified cadence, never the cadence itself.

## C. Key metrics — what we gather and analyze

Gathered per post (Meta Insights → `PostMetrics`, all modeled in
`social/carousel/metrics.py`):

| Metric | Why it matters |
|---|---|
| **Interaction rate** (unique interactors ÷ reach) | THE north star — the founder's "toward 100% interaction," measured honestly |
| **Save rate** | Meta's strongest ranking signal; equals "I'm considering going" — the highest-intent act short of a click |
| **Share/send rate** | The growth loop itself (the plan-share loop); every send is a recruitment at peak intent |
| Reach + follows-per-post | Distribution health; audience compounding |
| **Impressions ÷ reach** | The fatigue dial the cadence decision reads (§B) |
| Link CTR (UTM per post) | Carousel → /tonight handoff; ties social to product sessions |
| Profile visits | Brand-curiosity intermediate |
| Comments/likes | Supporting engagement (weighted below saves/shares deliberately) |

Analyzed continuously (already mechanical in the engine):
- **Per-factor learning** — Thompson posteriors per hook type, emotion
  register, listicle size (5 vs 7!), caption style, CTA, post slot:
  every question the founder could ask ("does humor beat awe in
  Austin?", "5 or 7?") becomes a posterior we can read off.
- **The improvement ratchet** — rolling baseline per surface × tier;
  `improved`/`regressed` flags per post; a regressing period is a
  Kaizen defect to explain, never averaged away.
- **Program level** — follower growth, share→signup conversion (UTM),
  cost per incremental visitor (≈ $0 organic; the denominator that
  keeps this honest when ads are ever considered — a founder money
  decision).

What we deliberately do NOT chase: raw follower count as a goal,
like-count vanity, engagement-bait mechanics (Meta down-ranks them, the
white-hat line forbids them, and they poison the learning signal).

## Status
The format rules in this doc (listicle canon, future-only windows,
Today/Tonight/This weekend) are CODE, test-pinned. The cadence in §B is
a recommendation awaiting the founder's dial-set (spec §9.4); the
metrics in §C are modeled and awaiting live Insights (R-026).
