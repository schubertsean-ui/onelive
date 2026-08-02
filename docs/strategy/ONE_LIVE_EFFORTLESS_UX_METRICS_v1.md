# ONE LIVE — Effortless / Automagical UX: organizing the choice space & measuring it — v1

**Status:** PROPOSAL / RESEARCH SYNTHESIS (2026-08-01). PROPOSAL ≠ license to build — awaits founder
ratification, then feeds the Discovery Exam (`ONE_LIVE_SAVED_ALERTS_AND_PROACTIVE_SURFACING_v1.md` §8)
and the "Heartbeat" analytics canon. Answers two linked founder questions from the 2026-08-01 thread:

1. **"22 categories × multiple timeframes × locales — there's a science to how options are organized
   for selection. Choice overload is real here, but *earlier* in the process — choice in designing what
   results I get, not choice from the results I get. What do the best designers do?"**
2. **"≤3 clicks is the ceiling; the goal/metric is a UI so automagical it feels effortless — except
   curiosity makes users click around more, so 1–2 clicks is more common than 3 in *yielding results*…
   to do what? Research what world-class looks like."**

They're two halves of one answer: **§1 is how to organize the choice space so it never overwhelms
(input-stage IA); §2–§7 are how to make it feel effortless and how to measure that.**

**Trust-first framing throughout:** effortlessness is achieved by clarity, speed, and smart defaults —
**never** by pay-to-rank, fabricated engagement, addiction loops, or hiding uncertainty. Honest gaps
beat filler; disputed shown-never-hidden.

---

## §0 · The one-paragraph answer

The founder's instincts are backed by the research. **"≤3 clicks" is a ceiling, and click-counting
alone is a discredited metric** — NN/g formally debunked the 3-click rule: users quit when they lose
the *scent* of heading toward what they want, not at a click count. And the deeper problem is
**upstream** — the tax of *designing the query* across 22 categories × time × place. World-class design
beats that tax by **not making the user build the query at all**: pre-compose a sensible default
(context + personalization), start them at *results*, and make choosing *optional refinement*, not a
required gate. Then measure **effort + confidence + scent**, not raw clicks, and — critically —
**separate "clicks I was forced to make" (friction) from "clicks I chose to make" (curiosity)**, driving
the first down while treating the second as a positive engagement signal.

---

## §1 · Input-stage choice architecture — organizing the 22 × time × locale space

The founder's distinction is the important one: choice overload **at the "design my query" stage** is
worse than choice among results, because it's *a tax paid before any payoff* — and it's where most
discovery apps lose people. The discipline is **Information Architecture + choice architecture.**

**Core principle: don't make the user *build* the query.** Pre-compose it and start them at results;
choice becomes *optional refinement* (curiosity), never a *required gate* (friction). Every technique
below serves that one move.

| Technique | What it does | Law / why |
|---|---|---|
| **Pre-composed default view** | Open straight into results using **context + personalization**: time-of-day → "tonight," location → their city, tastes → their saved axes. Zero taps to something good. | Removes the empty-form tax; "results-first, not filter-first" |
| **Collapse 22 → a few top buckets** | Never show 22 flat categories. Group into ~5–7 Layer-1 buckets ("Music · Ideas · Comedy · Arts · Food & Markets…"), drill to subcategory only on demand. | **Hick's Law** (fewer choices = faster) + **Miller's 7±2** + progressive disclosure |
| **Preset "intents"** | A few human starting points that each *encode a whole multi-facet query*: "Free tonight," "Date night," "Live music near me," "Family this weekend." One tap = category + time + place + price, pre-composed. | Collapses the combinatorial space into recognizable goals (Netflix rows, Airbnb categories, Spotify moods) |
| **One-tap chips, not forms** | Common refinements as toggle pills (Tonight · Weekend · Free · Near me · Live music) — recognition, not recall; tap, not type. | Recognition-over-recall; the chip row *is* the filter UI |
| **Space & time as the organizers** | Locale → a **map**; time → a **timeline / river**. Browsing space and time offloads "filtering" into a natural gesture. (The FLOW design already has the time-ordered river + city start + area/nearby lenses.) | Turns 2 of the 3 axes into browse, not filter |
| **Live, inline, non-modal filtering** | Filters update results instantly (no "Apply"), ideally with counts ("Comedy · 6 tonight"). User sees consequences, feels in control. | Reduces "did I pick right?" anxiety; **Doherty threshold** (<400ms) |
| **Search box = power-user escape hatch** | One natural-language input collapses *all* facets for people who know exactly what they want ("cumbia south austin tonight"). | The "one input" ideal; serves experts without burdening novices |

**The shape this gives `/tonight`:** land on **results** (pre-composed from context + tastes). A slim row
of **intent presets + chips** on top for one-tap re-aiming. The **22 categories live behind a Layer-1 →
Layer-2 drill**, never dumped flat. **Time = the river, place = the map.** Power users type. Result:
**effort taps to a result = 0–1**; **curiosity taps = unlimited and encouraged** (and measured
separately, §3).

---

## §2 · The measurement framework — how to quantify "effortless"

The best teams combine **behavioral** metrics (what users *do*, logged) with **attitudinal** metrics
(what users *say*, via micro-surveys), and **always pair an efficiency metric with a success metric** so
"fast" can never masquerade as "gave up."

| Metric | What it is | Limitation |
|---|---|---|
| **Taps-to-completion** | Interactions from entry to the success event | Ignores *cognitive* cost; a myth as a standalone goal ([NN/g](https://www.nngroup.com/articles/3-click-rule/)) |
| **Time-to-first-meaningful-result / Time-to-Value** | How fast to a real outcome (not a loaded screen) | Only meaningful if "value" = a real outcome, never "setup complete" |
| **Task success rate** | % who complete the intended task | Needs a crisp "success" definition — the hard part for *browse* (§4) |
| **Customer Effort Score (CES)** / **Single Ease Question (SEQ)** | Self-reported ease of a task (1–7); SEQ industry avg ≈ 5.3–5.6 | Single-interaction; pair with CSAT/return |
| **NASA-TLX** | 6-dimension perceived workload | **Too heavy for a consumer browse app** — skip it |
| **Behavioral friction tells** | pogo-stick, rage-click, dead-click, hesitation | Must be read against intent (§3) |

**Google's HEART + Goals-Signals-Metrics** is the de-facto standard for *choosing* UX metrics, applied
**per-flow** (Happiness · Engagement · Adoption · Retention · Task-success). It maps directly onto our
"Heartbeat" canon: run a Goals→Signals→Metrics pass on `/tonight` specifically.

---

## §3 · The heart of it — EFFORT clicks vs. CURIOSITY clicks

A metric that just minimizes clicks would **punish a delighted user who browses.** World-class teams
classify *why* a click happened:

- **Information scent / foraging** ([NN/g](https://www.nngroup.com/articles/information-scent/)): users
  forage by "scent" — do the labels promise they're getting warmer? **Strong scent + moving forward =
  flow** (engaged, even at 5 clicks). **Weak scent + backtracking = friction.** The distinction is
  *directionality and confidence*, not click count.
- **Successful vs. unsuccessful *sessions*** (path analysis): judge whole sessions, not clicks. *Time
  between steps* distinguishes intentional navigation from confused wandering; loop-revisits signal
  confusion.
- **Dwell time as an intent classifier:** a click where the user lingers (>~30s) or acts = *successful*;
  a fast bounce-back = *unsuccessful*. Opening an event and staying/saving = good; opening and bailing
  in 2s repeatedly = pogo-sticking.
- **Engaged-time vs. required-time:** *required* taps → trend **down** (effortlessness); *engaged/
  voluntary* taps → a **positive** signal tracked **separately**, never inflating "effort."
- **Positive vs. negative signals (the TikTok primitive):** watched-to-end/save/share (positive) vs.
  skip-fast/not-interested (negative) — the same split lets us tag curiosity vs. friction.

> **Rule for our metric:** count a tap as **friction** only when it's a *reversal* (pogo-stick, back
> within N seconds, rage/dead click). Count it as **curiosity** when it goes *deeper with dwell*. Report
> the two as separate metrics that move in opposite desired directions.

---

## §4 · "Yielded a result — to do what?" The success-state taxonomy

A discovery app has **multiple legitimate goals**; forcing everything into "conversion" is the classic
mistake. Each gets its own taps-to-success measurement:

| Success state | What the user wanted | Detect via | Taps target |
|---|---|---|---|
| **Decide** | Pick what to do tonight | Detail dwell > threshold, "save/going" tap | Lowest — 1–2 |
| **Act / convert** | Outward action (venue link, directions, RSVP) | Outbound click, calendar add | 2–3 |
| **Share** | Bring friends in | Share sheet invoked from a card | 1–2 |
| **Satisfy curiosity / inform** | Just see what's on | Multiple card impressions + reasonable dwell, no rage/pogo | N/A — success = *quality of browse* |

**The trust-first point:** **a satisfied browse with no conversion is a success, not a bounce.** A user
who opens the app, sees "here's what's real tonight," and closes it *satisfied* is a win — measured by
**return rate** and **CES**, never by whether they tapped a monetizable button. We define "value" as *a
confident decision or a satisfied browse*. This is doctrinally important: we **never** optimize for
forced conversion or engagement-maximization.

---

## §5 · The design patterns that CREATE the "automagical" feeling (with the law behind each)

| Pattern | Law / principle | Why it feels effortless |
|---|---|---|
| **Fewer, well-chosen options** | **Hick's Law** | Fewer choices = faster decisions |
| **Progressive disclosure** | Hick's, as a pattern | Front screen stays calm; depth is opt-in (that's *curiosity*, not forced effort) |
| **Big, thumb-reachable targets** | **Fitts's Law** | Primary action trivially easy to hit |
| **Instant response (<400ms)** | **Doherty Threshold** | Interaction feels like an extension of thought |
| **Smart defaults** | Reduce decisions to zero where a good guess exists | The right thing is pre-selected |
| **Recognition over recall** | Nielsen heuristic | No memory load — show, don't make them remember |
| **Strong zero-state** | Give scent from the first screen | `/tonight` opens already showing real events, never a blank search box |
| **Anticipatory / zero-query discovery** | Surface answers before the user asks | No query effort at all (interest-based, never manipulative) |
| **"Don't make me think" / calm interface** | Krug; Calm Technology | Self-evident cards; quiet trust cues in the periphery |

**Most load-bearing for a browse-and-decide feed:** Doherty (<400ms), Hick's Law (curation), strong
zero-state, and zero-query relevance.

---

## §6 · Exemplars — and what we must REJECT

| Product | The effortless move | Trust-compatible? |
|---|---|---|
| **Amazon 1-Click** | Collapse checkout to one tap from stored context | Pattern yes (one-tap add/share from context) |
| **Superhuman** | Onboarding as a *measured product* — TTV, activation cohorts, the "40% would be very disappointed" PMF metric | **Yes — the measurement discipline is our model** |
| **Luma** | Create/RSVP in seconds; single page, overlays for detail, one-tap RSVP | **Yes — closest analog** |
| **Perplexity** | One query → a direct **cited** answer | **Yes, strongly — effortless *with* provenance shown = our trust ideal** |
| **Google "I'm Feeling Lucky" / instant answers** | Skip the results page for high-confidence intent | Partial — only where confidence is genuinely high |
| **TikTok / Spotify "for you"** | Zero-query interest feed; lightweight actions; positive+negative signals | Pattern split — *relevance* yes; **addiction loop NO** |

**REJECT (trust-first is non-negotiable):** infinite-scroll engagement loops that remove stopping points;
dark patterns (forced continuity, confirm-shaming, fake scarcity, disguised ads); pay-to-rank /
fabricated engagement / filler-over-honest-gaps; **vanity engagement maximization** — long sessions are
NOT our goal, a fast satisfied browse beats a sticky one.

---

## §7 · Recommended metric set for ONE LIVE (8 metrics)

Designed so **effortlessness and curiosity are measured separately** and **trust is never traded for
stickiness.** Several are testable in the Discovery Exam *before* launch.

| # | Metric | HEART | Measures | Testability |
|---|---|---|---|---|
| 1 | **Median effort-taps-to-decision** | Task | *Required* forward (non-reversal) taps from open to a decision/save; target mode = 1–2 | **Offline** (Discovery Exam counts taps on golden persona×query paths) |
| 2 | **Time-to-first-meaningful-result (TTV)** | Adoption/Task | Seconds from open to first relevant event surfaced | **Offline** + online |
| 3 | **Task success rate, per success-state** | Task | Separate rates for Decide / Act / Share / Satisfied-browse | **Offline** for Decide/Act/Share; browse-satisfaction online |
| 4 | **Curiosity depth (SEPARATE positive metric)** | Engagement | Voluntary extra taps/dwell *after* the success event — good, never counted as effort | **Online** |
| 5 | **Friction-reversal rate** | Task | Pogo-stick + rage + dead + fast-back per session | Partly offline (dead/false-affordance); pogo/rage online |
| 6 | **CES / SEQ micro-survey** | Happiness | Self-reported ease of "finding something to do tonight" | Online (pilot in moderated tests offline) |
| 7 | **Return rate (satisfied-browse retention)** | Retention | Do satisfied browsers come back? | Online — the anti-dark-pattern north star |
| 8 | **Trust-comprehension rate** (ONE LIVE-specific) | Happiness/Task | % who correctly read a confidence/disputed state | **Offline** (Discovery Exam asserts the state is present + legible) |

**Guardrails so a metric never becomes a dark pattern:** never optimize curiosity depth *upward* as a
goal (it's a health signal, not a target); never treat a satisfied non-conversion as failure; pair every
efficiency metric with a success metric; **trust-comprehension (metric 8) is a veto** — any
effortlessness "win" that reduces trust legibility is a regression.

---

## §8 · How this slots into existing canon

- **Discovery Exam (offline gate, `ONE_LIVE_SAVED_ALERTS…` §8):** metrics 1, 2, 3 (Decide/Act/Share), 5
  (partial), and 8 are assertable on the persona×query golden set *before* launch — e.g., "for persona X,
  query Y, a satisfying result is reachable in ≤2 forward taps, TTV under budget, and the confidence/
  disputed state is present and legible." This makes "effortless" a **gate**, not a hope.
- **Heartbeat analytics canon:** the 8 metrics run as a HEART Goals-Signals-Metrics pass on `/tonight`.
- **Genre taxonomy layers** (`ONE_LIVE_GENRE_TAXONOMY_v1`): the Layer-0/1/2 structure IS the "collapse 22
  → few, drill on demand" mechanism in §1.
- **FLOW design** (river + city start + genre/area/nearby lenses): already the space/time organizers.
- **Saved Alerts / member preferences:** the personalization that pre-composes the default view.
- **Trust invariants:** disputed shown-never-hidden (metric 8), no pay-to-rank, honest gaps beat filler
  — all preserved as vetoes over any effortlessness optimization.

---

## Sources

- NN/g — [The 3-Click Rule Is False](https://www.nngroup.com/articles/3-click-rule/) · [Information Scent](https://www.nngroup.com/articles/information-scent/) · [Information Foraging](https://www.nngroup.com/articles/information-foraging/) · [Measuring Perceived Usability (SUS/NASA-TLX/SEQ)](https://www.nngroup.com/articles/measuring-perceived-usability/)
- HEART / GSM — [Statsig: HEART framework](https://www.statsig.com/perspectives/heart-framework-measuring-ux) · [Fountain Institute: Goals-Signals-Metrics](https://www.thefountaininstitute.com/blog/goals-signals-metrics)
- Effort scores — [Contentsquare: CES](https://contentsquare.com/blog/customer-effort-score/) · [HubSpot: CES](https://blog.hubspot.com/service/customer-effort-score) · [MeasuringU: SEQ](https://measuringu.com/evolution-of-seq/) · [MeasuringU: NASA-TLX](https://measuringu.com/nasa-tlx/)
- Time-to-value — [Amplitude: TTV](https://amplitude.com/explore/analytics/time-to-value) · [Product School: TTV](https://productschool.com/blog/product-strategy/time-to-value)
- Friction signals — [Amplitude: Rage Clicks](https://amplitude.com/explore/analytics/rage-clicks) · [Userpilot: Dead Clicks](https://userpilot.com/blog/dead-click/) · [Embarque: Pogo-Sticking](https://www.embarque.io/glossary/pogo-sticking) · [Userpilot: UX metrics](https://userpilot.com/blog/how-to-measure-user-experience/)
- Path/intent — [Kissmetrics: Path Analysis](https://kissmetrics.io/blog/path-analysis-user-flows) · [arXiv: Product Intents / dwell-time](https://arxiv.org/pdf/2005.08591)
- Laws of UX — [Doherty Threshold](https://lawsofux.com/doherty-threshold/) · [Hick's Law](https://lawsofux.com/hicks-law/) · [LogRocket: cognitive principles (Fitts, recognition-over-recall)](https://blog.logrocket.com/ux-design/cognitive-principles-for-ux-designers/)
- Calm/clarity — [Merkle: Invisible Experiences / Calm Tech](https://www.merkle.com/en/merkle-now/articles-blogs/2026/the-strategic-power-of-invisible-experiences.html) · [Krug "Don't Make Me Think" review](https://medium.com/@bonny.bakshi/dont-make-me-think-revisited-by-steve-krug-book-review-53dee1ee6d7f)
- Exemplars — [Amazon 1-Click case study](https://rockpaperscissors.studio/amazon-one-click-checkout-the-ux-case-study-that-revolutionized-e-commerce/) · [First Round: Superhuman PMF engine](https://review.firstround.com/how-superhuman-built-an-engine-to-find-product-market-fit/) · [Lenny: Superhuman](https://www.lennysnewsletter.com/p/superhumans-secret-to-success-rahul-vohra) · [Luma review](https://party.pro/luma/) · [How-To Geek: I'm Feeling Lucky](https://www.howtogeek.com/847170/googles-im-feeling-lucky-explained/) · [Perplexity: answer engine](https://www.perplexity.ai/help-center/en/articles/10354917-what-is-an-answer-engine-and-how-does-perplexity-work-as-one) · [TikTok Newsroom: #ForYou](https://newsroom.tiktok.com/en-us/how-tiktok-recommends-videos-for-you) · [GetStream: TikTok feed lessons](https://getstream.io/blog/tiktok-feed-lessons/)
- Bounce / browse-as-success — [Terakeet: Bounce Rate](https://terakeet.com/blog/bounce-rate/) · [Cufinder: Bounce Rate](https://cufinder.io/blog/wiki/marketing-metrics/bounce-rate/)
- Anti-patterns — [Scalable Path: Dark Patterns](https://www.scalablepath.com/ui-ux-design/dark-pattern-examples) · [Eliza Ng: Ethics of infinite scroll](https://www.eliza-ng.me/post/thetwosidentifi_19/)

> **Unverified notes:** Amazon's "~40–45% abandonment reduction" and Luma's "effortless" are vendor/
> qualitative claims, not independent studies — directional only. NN/g pages cited from public summaries
> (their server blocked direct fetch).
