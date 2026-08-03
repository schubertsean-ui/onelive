# Research report — KPI calibration: per-window TM denominators, real-event universe, Coverage@Window recommendation, honest-count canon

Produced 2026-08-03 by a session research agent; committed verbatim as the
companion evidence cited by docs/strategy/SOURCING_SCALE_PLAN_v1.md.

---

Research complete. Here is the full report.

---

# 1Live Coverage North-Star KPI — Empirical Derivation & Recommended Design

**Scope note per founder directive (2026-08-03):** every number below is stated per bounded time window — Today / next 2 days / next 3 days / Weekend (Fri–Sun) / Week / Month — never as an unbounded catalog total. Catalog-snapshot comparisons (e.g. TM's "230K+ events" global catalog) are used only as sanity checks, never as locale-window measures.

## Part A — The empirical numbers

### A1. The denominator: what Ticketmaster actually lists for Austin, per window

**Our own DB is the best primary source here.** The `import-licensed` run (30600612981, 2026-07-31) pulled **1,317 TM events for the 14-county CAPCOG region sweeping 6 rolling ~30-day windows ≈ 180 days forward** (`worker/importers/ticketmaster.py` lines 119–150 confirm the 6×30-day sweep; segment mix at `docs/strategy/ONE_LIVE_DATA_INGESTION_REPORT_2026-07-31.md`: live-music 572, theater 236, comedy 133, sports 129, other ~247).

Public sanity checks:
- TM's Discovery API advertises **230K+ events** in the live catalog across ~7 countries at any time. Austin metro is ~0.7% of US population; a naive share of a ~60%-US catalog gives ~1,000 forward events — same order of magnitude as our 1,317. **The 1,317 figure passes the sanity check.**
- Songkick (which tracks TM *plus* independent ticketing) shows for Austin metro: **11 events tonight, 27 this weekend, 264 this month, 1,047 all-upcoming** — i.e. month-1 holds ~25% of the full forward concert catalog. Applying that decay shape to TM's 1,317/180-days gives a front-loaded month 1.

**TM per-window estimates, Austin CAPCOG (medium-high confidence — derivable exactly from our `licensed_event` table, which I recommend as the standing computation):**

| Window | TM events (est.) | Basis |
|---|---|---|
| Today | 8–20 (weekday low, Fri/Sat high) | month-1 ÷ 30 with weekend skew |
| Next 2 days | 20–45 | |
| Next 3 days | 30–65 | |
| Weekend (Fri–Sun) | 35–75 | Songkick weekend:month ratio ~10% |
| Week | 70–130 | ~25–30% of catalog in month 1 → 330–400 ÷ 4.3 |
| Month | 300–450 | front-loaded share of 1,317 |

### A2. The numerator: how many live events actually happen in Austin, per window

Bottom-up components (each with source and confidence):

| Component | Volume | Source / confidence |
|---|---|---|
| Do512 listings | **1,000–1,500 events/week** | Wikipedia's Do512 article + search corroboration; HIGH that this is what Do512 lists; it is curated toward music/nightlife and already occurrence-counted |
| Live music venues | 250+ venues, music "every night of the week" → est. 800–1,500 performances/week | Visit Austin (venue count HIGH; performance count derived, MEDIUM) |
| Bar trivia | **88 venues with weekly trivia** (Geeks Who Drink alone runs 32) → ~88 occurrences/week | TriviaNearMe.net, geekswhodrink.com — HIGH |
| Karaoke + open mics | 15+ dedicated karaoke venues + recurring open mics → est. 50–120/week | Yelp/austinsings — MEDIUM |
| Austin Public Library | 20 branches + Central; FY25 program attendance ~198K/yr → at 20–30 avg attendance ≈ 6,600–9,900 programs/yr ≈ **130–190/week** | City of Austin open-data program-attendance story — attendance HIGH, program-count derived MEDIUM |
| Eventbrite | 4.6–4.7M events/yr globally → Austin share est. 15–30K/yr ≈ **300–600/week** | Eventbrite 10-K/press (global figure HIGH; Austin allocation MEDIUM-LOW) |
| Meetup | 100K+ events/week globally, 300K+ groups, 10K cities → Austin est. **300–800/week** | Meetup measurement report (global HIGH; Austin allocation MEDIUM-LOW) |
| Churches/congregations | ARDA 2020 census: 300+ congregations in Travis County across just 4 traditions (Catholic 32, Baptist 157, non-denom 87, +33); full-census metro plausibly 1,500–2,500 → non-worship public events est. 200–600/week (excluding regular services; including them adds 2,000+) | thearda.com — congregation base HIGH, event derivation LOW-MEDIUM |
| UT Austin | central calendar + 1,000+ student orgs; in-term est. 150–400/week | calendar.utexas.edu — LOW-MEDIUM |
| Everything else (parks/rec, ~10–15 farmers markets, galleries, museums, run clubs, comedy mics, 131 Hill Country winery/brewery sources already in our own catalog) | est. 200–500/week | derived — LOW-MEDIUM |

**Union with overlap discount** (Do512/Eventbrite/Meetup/venue calendars overlap heavily; PredictHQ's published pipeline numbers justify aggressive discounting — they **delete up to 45% of raw source events** as spam/duplicates/add-ons; duplicates alone run 10–30% per source; ~30% of raw event-API items are spam or add-ons like parking/VIP):

**Austin metro, deduplicated occurrence-counted totals (MEDIUM confidence):**
- **Week: 2,500–6,000 distinct events (central ~3,500–4,500)**
- Today: 250–600 weekday, 500–1,000 Fri/Sat
- Weekend (Fri–Sun): 900–2,500
- Month: 11,000–22,000
- Series-collapsed (a weekly trivia = 1 per week regardless): week drops to ~1,200–3,000 unique event-programs.

### A3. The honest ratio, per window

**Events basis (occurrence-counted, deduped, near-term windows) — MEDIUM confidence:**

| Window | Total : TM ratio | Central |
|---|---|---|
| Today | 20:1 – 60:1 | ~30:1 |
| Weekend | 15:1 – 45:1 | ~28:1 |
| Week | 25:1 – 55:1 | ~35:1 |
| Month | 30:1 – 55:1 | ~40:1 |
| Series-collapsed (any window) | 12:1 – 30:1 | ~20:1 |
| **Far-future window** (e.g. a week 3 months out, measured today) | **2:1 – 8:1** | community postings don't exist yet |

**The lead-time skew, quantified as far as sources allow:** TM/major-concert inventory posts 3–18 months ahead (local acts 1–3 months; superstars 12–18), while ticket-purchase data shows 29% of performance tickets sell day-of/day-before and 59% inside 4 weeks — community/free events post on that same compressed cycle. So the observable ratio is a strong function of *when you measure relative to the window*: near-term windows are long-tail-dominated (~30:1+), far-out windows are TM-dominated (single digits). **Any KPI must therefore fix both the window AND the measurement time (measure at window start, T-0).**

**Venues basis (MEDIUM-LOW confidence):** TM sells for an estimated **40–80 distinct venues** in the CAPCOG region (Moody Center/Theater/Amphitheater, Bass, ACL Live, Live Nation clubs like Emo's/Scoot Inn/Stubb's, HEB Center, COTA…— the exact count is one `SELECT count(DISTINCT venue)` on our `licensed_event` table; recommend running it). Distinct places hosting ≥1 public event/month metro-wide: 250+ music venues, 88 trivia bars, 20+ libraries, 1,500–2,500 congregations, 300+ city parks, ~100 museums/galleries, 100+ wineries/breweries, campuses, community centers → **1,500–3,000 places**. **Venues ratio: ~25:1 – 60:1** — same magnitude as the events ratio.

**Verdict on the proposed 50:1–100:1:** the empirically defensible near-term range is **~20:1–60:1**. 50:1 sits at the *optimistic edge* of true (reachable only at near-total coverage). **100:1 is not supported** — it becomes reachable only by counting rules we should ban (every church service, every fitness class, every parking add-on, zero dedup). Locking 100:1 as canon would build a structural incentive to inflate, which is exactly what PredictHQ's delete-rate data says ruins event datasets.

## Part B — KPI design

### B4. Critique of local:TM as north star, and the recommended stack

The ratio fails four tests of world-class metric design:
1. **Uncontrolled, noisy denominator** — TM's Austin count (~10–20/day) is small and volatile; the ratio swings on their inventory, not our work.
2. **Goodhart-gameable numerator** — rewards recurring-inflation, add-on junk, duplicates, and far-future stuffing; the raw-aggregator failure mode PredictHQ documents (30% spam/add-ons, 10–30% dupes) *maximizes* this ratio.
3. **Doesn't measure user value** — you can beat TM 100:1 and still miss tonight's best events. The user question is *recall against reality*, not multiple-of-a-competitor.
4. **No ground truth** — it never asks what percentage of real events we captured. Search engines solved exactly this: Lawrence & Giles (Science 1998, Nature 1999) measured engine *coverage* against an estimated true web size using overlap between independent sources (capture–recapture) — no engine exceeded ~16%. That is the right template.

**Recommended KPI stack (one north star + 4 guardrails), all computed per window {Today, 2-day, 3-day, Weekend Fri–Sun, Week, Month} × per market × per segment:**

**NORTH STAR — Verified Coverage@Window:** trust-weighted share of all real, public, attendable events in (market, window) that appear on 1Live with correct core facts (venue + start time), **measured at window start (T-0)**.
- *Numerator:* deduped 1Live events in-window, weighted by trust state (confirmed 1.0 / likely 0.6 / unverified 0.25 / disputed 0 — identical weights to the existing FOUNDER-RATIFY proposal in `docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md` §2, so the two proposals merge rather than compete).
- *Denominator:* ground-truth census, two methods triangulated: (a) **hand census** — each month, one randomly drawn neighborhood × one window is exhaustively audited by a human (walk the flyers, the venue Instagrams, the church boards) and coverage% computed against it; (b) **capture–recapture estimate** (Lincoln–Petersen on the overlap between independent source families — TM-family, Eventbrite/Meetup, Do512/Chronicle, venue-direct) to estimate the unobserved tail continuously.
- *Daily is the flagship cut* — /tonight is a tonight-first product, and by T-0 morning all information exists, so daily coverage is fully measurable and entirely on us (crawl freshness — our 20-min cycle — not lead-time — is the binding constraint).

**Guardrails:**
1. **Unique-supply share** — % of in-window published events found on none of {TM, Eventbrite, Do512, Meetup, AllEvents} at T-0. This is the moat metric; ratio-to-TM is retired to a *reported context stat* ("coverage multiple", same dedup rules, never a target).
2. **False-event rate** (precision twin) — sampled % of in-window listings that did not actually happen as stated (the PredictHQ delete-rate analog; feeds the existing zero-escaped-defects M3).
3. **Discovery lead time** — % of window events already live on 1Live at T-24h (median lead time trended). Guards the skew in A3.
4. **Per-segment floors** — coverage floors per ratified segment (music, comedy, community/civic, food-drink, family, arts…); no cross-segment averaging (music alone could hit 80% while community sits at 5% — the mission inverted).

**Anti-gaming counting rules (the honest-count canon):**
- **Identity:** one event = (canonical venue, local calendar date, title-cluster). Cross-source duplicates merge before counting.
- **Recurring events:** occurrence-counted within window — weekly trivia counts **1** in a daily window, **1** in a weekly window, **~4** in a monthly window (it genuinely is something to do 4 times that month). It never counts 52× except in a 52-week window nobody uses. A single series contributes max 1 occurrence per day. **Recurring-series share of feed is monitored** and reported beside every coverage number; the paired series-collapsed count is always published so recurrence can never masquerade as breadth.
- **Add-ons/spam:** parking, VIP upgrades, ticket-tier variants, watch-parties of the same event: never counted (PredictHQ's ~30% raw-junk figure is the cautionary base rate).
- **Umbrella events:** a festival counts as its independently-attendable sub-events only when each has its own time+place; otherwise 1/day.
- **Window integrity:** all counts at T-0 for the window; no credit for far-future stuffing; no unbounded catalog totals, ever.

### B5. Staged targets (honest about uncertainty)

Current state (from `ONE_LIVE_DATA_INGESTION_REPORT_2026-07-31.md`): feed is ~94% TM (1,403 events/~6mo → roughly TM-parity in any window; est. daily-window coverage of reality: **2–5%**).

| Stage | Sources live | Daily-window events (est.) | Coverage@Daily (est.) | Context multiple vs TM | Confidence |
|---|---|---|---|---|---|
| Now | 1 (TM) + fragments | ~10–20 | 2–5% | ~1:1 | HIGH |
| M1: current 180-source catalog actually flowing (Gaps A–D closed) | ~150–180 | 150–300 | 25–40% | 8–15:1 | MEDIUM |
| M2: ~1,000 sources (venue-direct + platforms + submissions) | 1,000 | 300–600 | 50–70% | 20–40:1 | MEDIUM-LOW |
| M3: ~5,000 sources (full AI-extract long tail + partner/venue self-serve) | 5,000 | 500–900 | 75–90% | 30–60:1 | LOW-MEDIUM |

**Recommended canon numbers:** north star = **Coverage@Daily ≥ 80% (trust-weighted) in the launch market**, guardrails ≥40% unique-supply, false-event rate at the existing zero-escape bar, ≥90% of daily-window events live by T-24h, no ratified segment below 50% at M3. The TM multiple that *falls out* of hitting those is ~30–60:1 occurrence-counted — i.e. the founder's 50:1 instinct is roughly what near-total coverage looks like, but it should be the *consequence*, not the target; 100:1 should not be canonized (only reachable via banned counting). Per prime directive: adopting/locking any of this is a founder-ratify decision; this report is the empirical input.

**Sources:** [TM Discovery API portal (230K+ events)](https://developer.ticketmaster.com/products-and-docs/apis/getting-started/) · [Live Nation 10-K/results (646M tickets 2025, 12K clients)](https://newsroom.livenation.com/news/live-nation-entertainment-full-year-and-fourth-quarter-2025-results/) · [Songkick Austin metro (1,047 upcoming / 264 month / 27 weekend / 11 tonight)](https://www.songkick.com/metro-areas/9179-us-austin) · [Do512 1,000–1,500 events/week (Wikipedia)](https://en.wikipedia.org/wiki/Do512) · [Visit Austin 250+ live music venues](https://www.austintexas.org/things-to-do/music/venue-guide/) · [TriviaNearMe Austin — 88 venues](https://trivianearme.net/austin) · [Geeks Who Drink venues](https://www.geekswhodrink.com/venues/) · [APL program attendance (City of Austin open data)](https://data.austintexas.gov/stories/s/Library-Program-Attendance-per-Capita/npnp-mfkb) · [Eventbrite 4.6–4.7M events/yr (10-K coverage)](https://www.stocktitan.net/sec-filings/EB/10-k-eventbrite-inc-files-annual-report-1eb4f39d73ae.html) · [Meetup 100K events/week, 300K+ groups](https://www.meetup.com/media/) · [ARDA Travis County congregations (2020 Religion Census)](https://www.thearda.com/us-religion/census/congregational-membership?y=2020&y2=0&t=0&c=48453) · [PredictHQ data quality (up to 45% deleted; 30% spam/add-ons; 10–30% dupes)](https://www.predicthq.com/intelligence/data-quality) · [PredictHQ spam detection](https://www.predicthq.com/blog/detecting-and-eliminating-spam-events) · [PredictHQ event categories (19 categories)](https://www.predicthq.com/intelligence/data-enrichment/event-categories) · [Lawrence & Giles, Nature 1999 — engine coverage ≤16% via overlap estimation](https://www.nature.com/nature/journal/v400/n6740/abs/400107a0.html) · [Lawrence & Giles, Science 1998](https://www.science.org/doi/10.1126/science.280.5360.98) · [Ticket purchase lead times (29% day-of/day-before)](https://medium.com/@GetInHere/when-do-people-buy-event-tickets-we-have-the-answers-f99c2a2c1ff4) · [Artist booking lead times](https://breakthroughdxb.com/news/how-far-in-advance-should-you-book-a-headlining-act-a-strategic-guide/) · Repo primary data: `/home/user/onelive/docs/strategy/ONE_LIVE_DATA_INGESTION_REPORT_2026-07-31.md`, `/home/user/onelive/worker/importers/ticketmaster.py`, `/home/user/onelive/docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md`.

**Key caveats:** WebFetch/direct page fetches were proxy-blocked (403) this session, so platform-page live counts (Eventbrite/AllEvents Austin result totals) came via search-result summaries rather than direct page reads — the Austin allocations of Eventbrite/Meetup global volumes are the weakest links (MEDIUM-LOW). Two cheap firm-ups for a follow-up session: (1) run `SELECT count(DISTINCT venue)` and per-window counts on our own `licensed_event` table to replace the A1 estimates with exact numbers; (2) one scripted pull of Eventbrite/AllEvents Austin result counts per window from a network-open environment.
