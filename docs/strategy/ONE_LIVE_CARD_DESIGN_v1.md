# ONE LIVE — Card Design & Progressive Disclosure: World-Class Techniques — v1

**Status:** PROPOSAL / RESEARCH SYNTHESIS (2026-08-01). PROPOSAL ≠ license to build — awaits
founder ratification. Answers the founder's 2026-08-01 question: *"Look at how the card performs
and operates — which data is shown at first vs. a 'zoom in' / unfurling of all the card content?
I need world-class design functionality and techniques."*

**How this relates to existing canon:** The `/tonight` UI Canon
(`docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md`) already ratifies *what* the card contains (two
doors, Spark Line, Emotion Glyph, contextual preview, quiet trust marker) and *that* disclosure is
the anti-clutter engine. This doc is the **evidence layer underneath it** — the outside research on
how the best teams decide what to show at rest vs. on expand, which unfurl interaction to use, and
how to make it feel instant. Where the two touch, the UI Canon wins on product specifics; this doc
supplies the science and the exemplars. Trust-first framing is non-negotiable throughout: no
pay-to-rank on the card, confidence as a quiet peripheral cue (never a badge or "confirmed"),
disputed shown-never-hidden, honest gaps beat filler.

---

## §0 · The one-paragraph answer

A world-class card is a **slightly-open door, not a summary.** At rest it shows the *minimum that
lets a person decide or lean in* — for an event: the act, when, where, price, one image, one vibe
cue, and a quiet confidence whisper — and defers everything else to an on-demand expand. This is
Shneiderman's mantra ("overview first, zoom and filter, details on demand") and Nielsen's
progressive disclosure applied to a single card. The *magic* is in the expand: the best teams use a
**shared-element / container-transform** transition (the card's own image grows into the detail
surface) or a **multi-stop bottom sheet** (Google Maps' peek → half → full) so the motion feels
*continuous and spatial* — the thing you tapped becomes the thing you're looking at, never a jarring
new page. Underneath, **perceived speed** (skeletons, blurred image placeholders, prefetch-on-intent,
optimistic UI, zero layout shift) keeps every interaction under the ~400ms Doherty threshold so it
feels like an extension of thought. ONE LIVE's ratified pieces — the two-door card, the slide-out
lens, Spark Line, Emotion Glyph — are already the right shape; this doc pins each to the technique
that makes it world-class.

---

## §1 · The progressive-disclosure science — what to show at rest vs. on expand

### The three foundational ideas

- **Shneiderman's Visual Information-Seeking Mantra:** *"Overview first, zoom and filter, then
  details-on-demand."* The user should see the whole set simply first, narrow to their interest,
  and pull exact detail only for the item they care about — maximum freedom to explore while never
  losing context ([InfoVis-Wiki](https://infovis-wiki.net/wiki/Visual_Information-Seeking_Mantra),
  [Shneiderman 1996 PDF](https://www.cs.umd.edu/~ben/papers/Shneiderman1996eyes.pdf)).
- **Progressive disclosure (Nielsen, NN/g):** defer advanced or rarely-used content to a secondary
  layer so the primary surface stays easy to learn and hard to get wrong — *without removing
  capability*. It is **hierarchical**: many users finish in the core layer and never open the
  advanced one ([NN/g video](https://www.nngroup.com/videos/progressive-disclosure/),
  [Wikipedia](https://en.wikipedia.org/wiki/Progressive_disclosure)).
- **Staged disclosure** is different and mostly *not* what a card wants: it's **linear** (wizard
  steps), where every step is required to finish. A card is progressive (peek → optional depth),
  not staged ([UXPin](https://www.uxpin.com/studio/blog/what-is-progressive-disclosure/)).

### The deciding principle: information scent

What earns a place in the *at-rest* tier is decided by **information scent** — the cues a person
uses to predict "will opening this get me what I want, and how much effort will it cost?" Users
forage like animals following a scent; they commit to an item (or a click) when the visible cues
promise they're getting *warmer* ([NN/g: Information
Scent](https://www.nngroup.com/articles/information-scent/), [NN/g: Information
Foraging](https://www.nngroup.com/articles/information-foraging/)). **The rest-tier's job is to emit
just enough scent to support a decision or a confident tap — and no more.** Piling on fields doesn't
add scent; it dilutes it and taxes working memory.

### A concrete three-tier model for an EVENT card

| Tier | Purpose | What belongs here (event card) | Governing law |
|---|---|---|---|
| **Tier 1 — Glanceable (at rest)** | Decide or lean-in at a glance; emit scent | **Act/artist name · start time (+ "on now"/doors when relevant) · venue · price · one image · one vibe cue · one quiet confidence marker.** One curiosity hook, not a recap. | Overview-first; scent; working memory ~3–4 items |
| **Tier 2 — In-context expand / peek** | Answer "tell me a bit more" without leaving the feed | Venue character line + mini-map, distance, the contextual preview (listen/watch), secondary media, "see nearby," specials — revealed by opening a door/sheet | Zoom & filter; progressive disclosure |
| **Tier 3 — Full detail (destination)** | Commit: full logistics + outward action | Long-form when/where/price/kind, "check the venue" (own site/phone), tickets ↗, share, embedded preview, disputed disclosure open-by-default | Details-on-demand |

**How the best teams choose Tier 1:** they ask "what is the *single decision* this card supports,
and what is the *least* that supports it?" Everything that doesn't move that decision drops to Tier
2/3. For a live-events card the decision is *"is this my night?"* — answered by act + time + place +
price + a feel + a trust whisper. (This matches the UI Canon's "calm over clutter / curiosity over
completeness / a row of slightly-open doors.")

---

## §2 · The expand / unfurl interaction patterns

The choice of *how the card opens* is the biggest lever on whether the product feels "magical." The
governing quality is **perceived continuity**: the element you touched should visibly become the
detail you're now reading, preserving spatial context.

| Pattern | What it is | Best when | Tradeoffs / cost |
|---|---|---|---|
| **Tap-to-expand in place (accordion / expandable card)** | Card grows on the same screen to reveal more | Most users want only a peek; content is short; keeping list context matters | Pushes siblings around (layout shift, lost scroll position); bad for long/complex content or if *every* card gets expanded ([UX Patterns](https://uxpatterns.dev/patterns/content-management/accordion), [Design for Ducks](https://designforducks.com/expandable-card-ui-best-practice-and-examples/)) |
| **Bottom sheet, multi-stop (Material) / sheet with detents (Apple HIG)** | Panel rises from the bottom; stops at peek / half / full; background stays visible & (often) interactive | Supplementary detail without leaving context; user controls how much they want; the Maps pattern | Modal vs non-modal must be deliberate; a never-dismissible sheet can trap focus if done carelessly ([NN/g: Bottom Sheets](https://www.nngroup.com/articles/bottom-sheet/), [M3](https://m3.material.io/components/bottom-sheets/guidelines), [Apple detents](https://www.createwithswift.com/exploring-interactive-bottom-sheets-in-swiftui/)) |
| **Shared-element / hero "container transform" (Material Motion)** | The card's container (image + shape) morphs seamlessly into the detail view | The transition includes a persistent container (a card → its detail); you want maximum continuity | Highest engineering effort; must honor reduced-motion; needs matched start/end elements ([M3 blog](https://m3.material.io/blog/android-material-motion), [MDC Medium](https://medium.com/androiddevelopers/material-motion-with-mdc-c1f09bb90bf9)) |
| **Peek-and-commit / long-press preview (iOS context menu)** | Long-press floats a preview + actions above the list; release to commit or dismiss | Fast preview without navigating; power-user shortcut to actions | Discoverability is low (hidden gesture); must not be the *only* path to detail ([Apple HIG: Context Menus](https://developer.apple.com/design/human-interface-guidelines/components/menus-and-actions/context-menus/), [Luis Abreu](https://lmjabreu.com/post/ios13contextualmenus/)) |
| **Modal dialog / full-screen** | Blocks the background entirely | Content needs full attention (forms, confirmations) or full space | Breaks browse flow; heaviest interruption — reserve for Tier-3 commit, not a peek ([Design for Ducks](https://designforducks.com/expandable-card-ui-best-practice-and-examples/)) |
| **Hover-preview (desktop only)** | Detail appears on hover; often paired with prefetch | Desktop/pointer; low-cost preview + instant navigation | No touch equivalent — never the sole mechanism on a mobile-first PWA ([Simon Hearne](https://simonhearne.com/2021/optimistic-ui-patterns/)) |

### Which feel most "magical," and why

The **container transform** and the **multi-stop bottom sheet** win on *perceived continuity and
spatial consistency* — the thing you tapped grows into the thing you're reading, so your mental map
never resets. Container transform "creates a visible connection between two UI elements by seamlessly
transforming one into the other," giving "immediate context to the new layout"
([Styling Android](https://blog.stylingandroid.com/material-motion-container/)). Google Maps' sheet
shows *different content at each stop* — name when peeked, photos/ratings when half, reviews when
full — while the map behind stays live and the panel is never fully dismissed
([ProAndroidDev](https://proandroiddev.com/building-a-google-maps-style-bottom-sheet-with-jetpack-compose-eccc1f3cf578)).
**This is exactly the ONE LIVE "lens" model** — a forward-expanding overlay of the same surface, not
a page load.

### Motion & accessibility (non-negotiable)

- **Keep it short:** 200–300ms for entrance/expansion; focus is set *after* the animation completes
  ([TestParty](https://testparty.ai/blog/modal-dialog-accessibility)).
- **Honor `prefers-reduced-motion`:** provide a reduced variant for *every* animation — e.g. fade
  instead of scale/morph — rather than removing all feedback. Motion can trigger vestibular illness
  ([BOIA](https://www.boia.org/blog/what-to-know-about-the-css-prefers-reduced-motion-feature),
  [CSS-Tricks](https://css-tricks.com/almanac/rules/m/media/prefers-reduced-motion/)).
- **Focus & dismissal:** any modal-type surface traps focus, supports Escape/swipe-down, and
  restores focus to the triggering card on close; the native `<dialog>` handles much of this
  ([UXPin](https://www.uxpin.com/studio/blog/how-to-build-accessible-modals-with-focus-traps/)).

---

## §3 · Card anatomy best practices

- **One object, one primary action per card.** A card should represent a single entity, with one
  primary action and at most two quieter secondary ones (multiple CTAs reduce clarity)
  ([Eleken](https://www.eleken.co/blog-posts/card-ui-examples-and-best-practices-for-product-owners),
  [UX Collective](https://uxdesign.cc/8-best-practices-for-ui-card-design-898f45bb60cc)).
- **Visual hierarchy: the most decision-relevant thing is largest/first.** "The headline or a
  critical number should be the largest thing on the card"; secondary actions (share/bookmark) are
  visually quieter and grouped consistently ([Eleken](https://www.eleken.co/blog-posts/card-ui-examples-and-best-practices-for-product-owners)).
- **Scannability + consistent templates (Jakob's Law).** Users spend most of their time on *other*
  apps and expect yours to work the same way; a consistent card template ("title, one line of
  metadata, one visual, one action") lets them scan without re-learning each row
  ([UX Design Institute](https://www.uxdesigninstitute.com/blog/laws-of-ux/)).
- **Recognition over recall.** Show the cue (a genre chip, a glyph, a photo) rather than making
  people remember or type it (see `docs/strategy/ONE_LIVE_EFFORTLESS_UX_METRICS_v1.md` §5).
- **Image/media as the hero, chrome stays quiet.** Airbnb leads with the photo, then location, then
  price, then rating — a clean sequence with generous whitespace; the photo does the work and the UI
  chrome recedes ([Superdesign](https://superdesign.dev/blog/airbnb-design-system)).
- **Density vs. whitespace.** Even internal padding, clear header/body/footer sections, no crowding;
  marketplace feeds tune spacing for high card-density-per-scroll without clutter
  ([UX Design World](https://uxdworld.com/designing-ui-cards/)).
- **Touch targets (Fitts's Law).** Every tappable control ≥44×44pt (Apple) / 48×48dp (Material);
  bigger, closer, thumb-reachable targets are faster and less error-prone
  ([UX Design Institute](https://www.uxdesigninstitute.com/blog/laws-of-ux/)).
- **Cognitive load per card.** Working memory holds ~4 items (Miller ~7±2, more conservatively 3–4);
  a card that forces the eye to process a dozen fields costs more than it returns
  ([Laws of UX summary](https://www.uxdesigninstitute.com/blog/laws-of-ux/)).
- **Platform guidance:** Material 3 cards "display content and actions about a single subject" in
  elevated/filled/outlined variants ([M3 Cards](https://m3.material.io/components/cards/guidelines)).
  Apple HIG: lean on native sheets/modals and conventional bars so users reuse what they already
  understand ([HIG overview](https://www.bitcot.com/ios-human-interface-guidelines/)).

---

## §4 · Polymorphic / type-adaptive cards

A single card *grammar* can foreground different first-glance data by entity type — same skeleton,
type-aware slots. Precedent: **Google rich results / Knowledge Panels** render a different shape per
entity (Event, Product, Recipe, Person, Movie…), and an artist's card can embed upcoming events as
its own sub-card ([Google: Introducing Rich
Cards](https://developers.google.com/search/blog/2016/05/introducing-rich-cards),
[Rich Results guide](https://aischema.dk/en/articles/rich-results)). Microsoft's **Adaptive Cards**
framework is the same idea generalized: one JSON grammar, host-adapted rendering
([adaptivecards.io](https://adaptivecards.io/explorer/RichTextBlock.html)).

**For ONE LIVE this is already ratified as the contextual preview** (UI Canon §3): the preview slot
is *not* music-only — it becomes listen-chips for a music act, the speaker's past talks for a
lecture, last year's media for a festival, a trailer for a film, the works for a museum. The rule is
**dynamic** (chosen at render from what actually exists), **contextually accurate** (real, sourced,
provenance-checked — never a generic stand-in), and **curiosity-inducing** (a door, not a summary).
The *type signal already exists* via the category resolver. The grammar stays constant (photo →
time line → hook → glyph → preview → venue block); only the preview and the primary-glance emphasis
adapt.

**Design rule for polymorphism:** keep the *structure* identical (Jakob's Law — one learnable
template) and vary only the *content of a few typed slots*. Never fabricate to fill a slot an entity
lacks — an absent preview is omitted, honest gaps beat filler.

---

## §5 · Performance & perceived speed of the card

The target is the **Doherty threshold (~400ms)**: below it the brain stays in "doing" mode and the
interaction feels continuous; above it the brain switches to "waiting," breaks flow, and re-evaluates
effort ([Laws of UX: Doherty](https://lawsofux.com/doherty-threshold/),
[LogRocket](https://blog.logrocket.com/ux-design/designing-instant-feedback-doherty-threshold/)).
Since not every fetch finishes in 400ms, world-class cards *manufacture* the feeling of instant:

- **Skeleton screens** (not spinners): show the card's shape from the first frame. Users perceive
  skeleton-loaded UIs as faster than spinner-loaded ones even at identical real load times; they
  help most when real load is ~400ms–3s ([The Hangline](https://www.thehangline.com/skeleton-screens-vs-loading-spinners-which-improves-perceived-performance/),
  [Pravin Kumar](https://www.pravinkumar.co/blog/loading-skeleton-screens-webflow-design-2026)).
- **BlurHash / LQIP image placeholders:** a ~20–30 char hash renders a smooth blur in <5ms while the
  photo loads — the card never flashes empty where its hero image goes
  ([VirtusLab](https://virtuslab.com/blog/frontend/ux-patterns-beyond-raw-performance)).
- **Zero Cumulative Layout Shift (CLS):** skeletons *reserve the exact dimensions* so nothing jumps
  when real content arrives — critical for a scrollable feed where a late-loading image shoving cards
  down is a top irritant ([Calibre](https://calibreapp.com/blog/cumulative-layout-shift)).
- **Prefetch on intent:** fetch the detail/expand payload on hover (desktop) or touch-start / when a
  card scrolls into view (mobile), cached briefly so the actual open feels instant — one marketplace
  cut time-to-usable-controls ~35% this way ([Simon Hearne](https://simonhearne.com/2021/optimistic-ui-patterns/)) *(vendor-reported, directional — unverified)*.
- **Optimistic UI:** reflect the expected result immediately (save/going toggles, filter applies),
  then reconcile with the server — "tricks the brain into perceiving the interface as faster"
  ([Modexa](https://medium.com/@Modexa/12-react-19-data-fetching-patterns-that-feel-instant-6b87965ff32b)).

**What makes a card feel instant, in one line:** never show a blank frame (skeleton + blurhash),
never let it jump (reserved space = zero CLS), respond to every touch inside 400ms (optimistic +
prefetch).

---

## §6 · Exemplars — what to learn, what to reject

| Product | What its card does well | Trust-compatible for ONE LIVE? |
|---|---|---|
| **Airbnb listing card** | Photo-hero; clean sequence photo → place → price → rating; restraint lets the image carry it; high density without clutter | **Yes** — the photo-first, quiet-chrome model is our template |
| **Apple Maps / App Store place cards** | Native sheet detents; conventional bars; the card *becomes* the sheet | **Yes** — sheet-with-detents = the lens; reject the promotional "Showcase" slot (that's pay-to-surface) |
| **Google Maps place sheet** | Multi-stop peek→half→full; different content per stop; map stays live behind; never fully dismissed | **Yes, strongly** — the canonical model for the ONE LIVE lens/nearby surface |
| **Arc / Dia** | Fast, spatial, continuous transitions; low chrome | Pattern yes (continuity/motion), no data-trust stakes |
| **Spotify** | Type-adaptive cards (track/album/artist/playlist share one grammar); strong art | Pattern yes (polymorphism); reject engagement-maximization framing |
| **Things / Linear** | Extreme calm; one object per row; keyboard-fast; nothing decorative | **Yes** — the "calm, self-evident" bar |
| **Eventbrite / Luma** | Event cards lead with a strong 2:1 image + key facts; Luma = clean single page, overlays for detail, one-tap RSVP | **Yes** — Luma is our closest analog ([Eventbrite tips](https://www.eventbrite.com/blog/eventbrite-listing-marketing-tools-tips/), [Luma](https://party.pro/luma/)) |
| **Pinterest** | Masonry, image-first, low text, endless browse | Pattern (image-first scannability) **yes**; **reject** the infinite-scroll-without-stopping-points loop |

**Reject on trust grounds** (all consistent with FTC's July-2024 dark-patterns findings — ~76% of
sites reviewed used at least one): **fake urgency** ("limited time!"), **fake scarcity** ("only 2
left!"), **fabricated social proof** (fake counts/reviews), forced continuity, confirm-shaming, and
any **pay-to-rank / promoted** slot on the card. ONE LIVE never fabricates urgency or social proof,
and money never decides what's seen ([FTC 2024](https://www.ftc.gov/news-events/news/press-releases/2024/07/ftc-icpen-gpen-announce-results-review-use-dark-patterns-affecting-subscription-services-privacy),
[FTC dark-pattern types](https://www.agg.com/news-insights/publications/the-ftc-blacklists-dark-patterns/)).

---

## §7 · Concrete recommendation for the ONE LIVE card

### Tier-by-tier content model (event card)

| Tier | Interaction to reach it | Content | ONE LIVE elements that live here |
|---|---|---|---|
| **Tier 1 — Glanceable (at rest)** | Nothing — visible in the feed | Artist photo + name · time line (start · doors · price pill · "on now") · **one** curiosity hook · **one** vibe cue · **one** quiet confidence marker | **Spark Line** (the primary curiosity gap), **Emotion Glyph** (one SVG, emotional weather), price pill (mint = Free), the quiet **"?"** uncertainty control |
| **Tier 2 — Peek / in-context expand** | Tap a **door** → the **lens** slides forward (overlay, not page load); or a bottom-sheet peek | Venue character line + mini-map chip · distance · **contextual preview** (listen/watch/past-media, type-adaptive) · "from the venue" specials (attributed, never ranked) · "see nearby ›" | The **two-door card** (artist ›/ venue ›), the **slide-out lens**, the **artist↔venue switch**, the **contextual preview**, the **nearby lens** |
| **Tier 3 — Full detail (destination)** | Open from the card/lens | Long-form when/where/price/kind · "check the venue" (own site/phone) · tickets ↗ · native share · embedded preview · **disputed disclosure open-by-default** | Event detail page; trust "rides into" the shared artifact |

**Density adaptation** (already ratified, keep it): *This week* = full rich card; *Later this month*
= compact chronological row; *Beyond 30d* = one scannable line (`date · act · venue · price`). The
confidence marker rides even the tersest line.

### The chosen expand interaction

**Primary: the shared-element "lens" = a container-transform overlay.** Tapping a door morphs that
card's surface forward into its detail lens — this is the most continuous, spatial pattern and
already matches the FLOW "swipe in / release back, not a page load" model. **Secondary, for the map
surface: a Google-Maps-style multi-stop bottom sheet** for the nearby lens (peek = venue name, half
= walk-ring + POIs, full = detail) with the map live behind it. **Avoid** full-screen modals for
peeks (reserve modality for genuine Tier-3 commit) and never make a hidden long-press the *only*
path to anything.

### Motion & performance approach

- Expansions 200–300ms; a **reduced-motion variant (fade, no morph) for every transition**; focus
  set after animation; Escape/swipe-down dismiss; focus restored to the originating card.
- **Skeleton cards** with **BlurHash** hero placeholders on first paint; **reserved dimensions = zero
  CLS** in the scrolling river; **prefetch the lens payload** when a card enters the viewport;
  **optimistic** filter-apply and save toggles. Everything under the 400ms Doherty line.

### How the trust display fits each tier

- **Tier 1:** confidence is a *whisper* — one small quiet "?" icon, no label, no alarm color, never
  the word "confirmed" and never a badge. It is a courtesy, not a warning.
- **Tap the "?":** a one-tap-in / one-tap-gone sheet in calm plain language — "details for this show
  may change; here's the venue's own site to be sure." (This is itself a tiny progressive-disclosure
  moment.)
- **Disputed is the exception to "quiet":** shown honestly with a slightly stronger "sources
  disagree" marker at Tier 1, and its disclosure **opens by default** at Tier 3. The feed never
  filters on confidence — a disputed on-now show still appears.
- **No pay-to-rank ever touches the card** — specials are venue-owned display space, clearly
  attributed, and never affect order.

### Connecting card tiers to the four success-states

| Success state (Effortless-UX §4) | The tier that serves it | Card behavior |
|---|---|---|
| **Decide** ("pick tonight") | Tier 1 → light Tier 2 | Glanceable card + Spark Line + glyph give enough scent to decide in 1–2 forward taps |
| **Act / convert** (directions, tickets, RSVP) | Tier 3 | "Check the venue," tickets ↗, share — the outward actions, reached in 2–3 taps |
| **Share** (bring friends) | Tier 1 or Tier 3 | Native share from card/detail; **trust rides into the shared text** (cancellation + confidence) |
| **Satisfy curiosity** (just see what's on) | Tier 1 + optional Tier 2 | A calm, scannable river of slightly-open doors; a satisfied browse with no conversion is a **success**, never a bounce |

### What is offline-testable in the Discovery Exam (persona × query gate)

These card behaviors are assertable on the golden persona×query set *before* launch:

- **Tier-1 sufficiency:** for persona X / query Y, a decision is reachable in **≤2 forward taps** and
  the glanceable tier carries act + time + venue + price (metric 1).
- **Time-to-first-meaningful-result** within budget (metric 2).
- **Trust-comprehension (the veto):** the confidence/disputed state is **present and legible** on the
  card and its expansion (metric 8) — any effortlessness "win" that reduces trust legibility is a
  regression.
- **Dead/false-affordance friction:** no Tier-1 element promises an expand that has no content
  (honest gaps — an absent field is omitted, never faked) (metric 5, offline portion).

*(Runtime-only, measured online: curiosity depth, pogo/rage reversals, CES, return rate.)*

---

## §8 · Open questions / forks for the founder

1. **Container-transform vs. bottom-sheet as the *primary* card expand.** Recommendation:
   container-transform "lens" primary, Maps-style sheet for the map/nearby surface. Tradeoff: the
   morph is the higher engineering cost but the bigger continuity payoff; the sheet is cheaper and
   familiar but less "one continuous surface." *Founder call before Phase-1 build.*
2. **BlurHash vs. dominant-color vs. plain skeleton** for image placeholders — a small
   implementation choice with a real feel difference; recommend BlurHash for the hero, plain skeleton
   for text rows.
3. **Prefetch aggressiveness** trades perceived speed against data/battery on mobile — recommend
   prefetch-on-viewport-enter for the *next* few cards only, not the whole river.

---

## Sources

**Progressive disclosure & information-seeking**
- Shneiderman — [Visual Information-Seeking Mantra (InfoVis-Wiki)](https://infovis-wiki.net/wiki/Visual_Information-Seeking_Mantra) · [The Eyes Have It, 1996 (PDF)](https://www.cs.umd.edu/~ben/papers/Shneiderman1996eyes.pdf)
- NN/g — [Progressive Disclosure (video)](https://www.nngroup.com/videos/progressive-disclosure/) · [Information Scent](https://www.nngroup.com/articles/information-scent/) · [Information Foraging](https://www.nngroup.com/articles/information-foraging/)
- [Wikipedia: Progressive disclosure](https://en.wikipedia.org/wiki/Progressive_disclosure) · [UXPin: progressive vs staged disclosure](https://www.uxpin.com/studio/blog/what-is-progressive-disclosure/)

**Expand / unfurl interactions & motion**
- Material — [Bottom sheets (M3)](https://m3.material.io/components/bottom-sheets/guidelines) · [Cards (M3)](https://m3.material.io/components/cards/guidelines) · [Android Material Motion (M3 blog)](https://m3.material.io/blog/android-material-motion) · [Container transform (Styling Android)](https://blog.stylingandroid.com/material-motion-container/) · [Material Motion with MDC](https://medium.com/androiddevelopers/material-motion-with-mdc-c1f09bb90bf9)
- Apple HIG — [Context Menus](https://developer.apple.com/design/human-interface-guidelines/components/menus-and-actions/context-menus/) · [Sheet detents (Create with Swift)](https://www.createwithswift.com/exploring-interactive-bottom-sheets-in-swiftui/) · [iOS 13 contextual menus (Luis Abreu)](https://lmjabreu.com/post/ios13contextualmenus/)
- NN/g — [Bottom Sheets](https://www.nngroup.com/articles/bottom-sheet/)
- Google Maps sheet pattern — [ProAndroidDev](https://proandroiddev.com/building-a-google-maps-style-bottom-sheet-with-jetpack-compose-eccc1f3cf578)
- Expandable vs modal — [UX Patterns: Accordion](https://uxpatterns.dev/patterns/content-management/accordion) · [Design for Ducks](https://designforducks.com/expandable-card-ui-best-practice-and-examples/)

**Card anatomy & the laws**
- [Eleken: card UI best practices](https://www.eleken.co/blog-posts/card-ui-examples-and-best-practices-for-product-owners) · [UX Collective: 8 best practices](https://uxdesign.cc/8-best-practices-for-ui-card-design-898f45bb60cc) · [UX Design World](https://uxdworld.com/designing-ui-cards/)
- [UX Design Institute: Laws of UX (Jakob's, Fitts's, Hick's, Miller's)](https://www.uxdesigninstitute.com/blog/laws-of-ux/)
- Airbnb card — [Superdesign breakdown](https://superdesign.dev/blog/airbnb-design-system)

**Polymorphic / type-adaptive**
- [Google: Introducing Rich Cards](https://developers.google.com/search/blog/2016/05/introducing-rich-cards) · [Rich Results guide](https://aischema.dk/en/articles/rich-results) · [Microsoft Adaptive Cards](https://adaptivecards.io/explorer/RichTextBlock.html)

**Performance & perceived speed**
- [Laws of UX: Doherty Threshold](https://lawsofux.com/doherty-threshold/) · [LogRocket: Doherty](https://blog.logrocket.com/ux-design/designing-instant-feedback-doherty-threshold/)
- [The Hangline: skeletons vs spinners](https://www.thehangline.com/skeleton-screens-vs-loading-spinners-which-improves-perceived-performance/) · [Pravin Kumar: skeletons 2026](https://www.pravinkumar.co/blog/loading-skeleton-screens-webflow-design-2026)
- [VirtusLab: UX beyond raw performance (BlurHash/LQIP)](https://virtuslab.com/blog/frontend/ux-patterns-beyond-raw-performance) · [Calibre: Cumulative Layout Shift](https://calibreapp.com/blog/cumulative-layout-shift)
- [Simon Hearne: Optimistic UI patterns / prefetch](https://simonhearne.com/2021/optimistic-ui-patterns/) · [Modexa: data patterns that feel instant](https://medium.com/@Modexa/12-react-19-data-fetching-patterns-that-feel-instant-6b87965ff32b)

**Accessibility**
- [BOIA: prefers-reduced-motion](https://www.boia.org/blog/what-to-know-about-the-css-prefers-reduced-motion-feature) · [CSS-Tricks: prefers-reduced-motion](https://css-tricks.com/almanac/rules/m/media/prefers-reduced-motion/) · [TestParty: accessible modals](https://testparty.ai/blog/modal-dialog-accessibility) · [UXPin: focus traps](https://www.uxpin.com/studio/blog/how-to-build-accessible-modals-with-focus-traps/)

**Exemplars & anti-patterns**
- [Eventbrite listing tips](https://www.eventbrite.com/blog/eventbrite-listing-marketing-tools-tips/) · [Luma review](https://party.pro/luma/)
- [FTC 2024 dark-patterns review](https://www.ftc.gov/news-events/news/press-releases/2024/07/ftc-icpen-gpen-announce-results-review-use-dark-patterns-affecting-subscription-services-privacy) · [FTC blacklists dark patterns (AGG)](https://www.agg.com/news-insights/publications/the-ftc-blacklists-dark-patterns/)

**ONE LIVE internal canon**
- `docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md` · `docs/strategy/ONE_LIVE_EFFORTLESS_UX_METRICS_v1.md` · `docs/design/ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4.md`

> **Unverified notes:** The "~35% faster time-to-usable-controls" prefetch figure and Luma's
> "effortless" are vendor/qualitative claims, not independent studies — directional only. Several
> NN/g pages are cited from public summaries where direct fetch was blocked. FTC "~76% used at least
> one dark pattern" is the ICPEN/GPEN sweep's self-reported figure.
