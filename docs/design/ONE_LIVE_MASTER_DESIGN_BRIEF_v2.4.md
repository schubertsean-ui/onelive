# ONE LIVE — MASTER DESIGN BRIEF for AI Design Tool Intake (v2.4)
**Purpose:** Feed this brief to an AI design tool to generate **3 distinct visual/UX directions** for the ONE LIVE consumer product (Tonight feed → Filters → Event Detail), each deliberately differentiated from every existing competitor.
**Compiled:** 2026-07-12 · Built from ratified ONE LIVE canon (Master Business Plan, Charter, PRD wireframe, founder trust-display rules of 2026-07-12). Copy strings are verbatim canon.
**Note:** The internal Trust Equation formula stays internal per Part VII governance ("internal-only, never exposed"); its philosophy is expressed below in plain language instead.

---

## HOW TO RUN (selected tool + steps)

**Selected tool: Google Stitch** (stitch.withgoogle.com — Google Labs)
Why this tool over others (researched 2026-07-12):
- Built precisely for this job: brief in → multiple UI concepts out; its 2026 update added "vibe design" (describe look/feel/mood in plain language) and an agent that explores **multiple design directions in parallel** — exactly the 3-option ask. (https://www.nxcode.io/resources/news/google-stitch-vs-figma-ai-design-comparison-2026 · https://ortemtech.com/blog/ai-design-tools-comparison-2026-figma-v0-google-stitch/)
- **Free** (~350 standard + ~200 higher-quality "experimental" generations/month) — no key to mint, no founder-crucial spend decision. (https://flowstep.ai/blog/best-ai-ui-design-tools/ · https://www.nxcode.io/resources/news/google-stitch-vs-v0-vs-lovable-ai-app-builder-2026)
- Exports to **Figma** with editable layers for refinement, and to HTML/Tailwind — feeding straight into our Next.js/Tailwind stack. (https://www.imagine.art/blogs/google-stitch-alternatives · https://www.banani.co/blog/12-stitch-ai-alternatives)
Access: sign in with a Google account at stitch.withgoogle.com. No API key required.
Fallbacks: **Figma Make** (from ~$20/mo, Figma-native) and **v0 by Vercel** (~$20/mo, production React/shadcn output) — same brief works in both. (https://flowstep.ai/blog/best-ai-ui-design-tools/ · https://www.nxcode.io/resources/news/google-stitch-vs-v0-vs-lovable-ai-app-builder-2026)

**Steps:**
1. Open Stitch → new project → Experimental (high-quality) mode → mobile web app.
2. Paste PART A below as the project prompt. Ask for **Direction 1 of 3** and include PART B's direction-splitting instruction.
3. Repeat in two parallel canvases for Directions 2 and 3 (Stitch's agent manager supports parallel directions).
4. For each direction, generate the three screens: Tonight feed · Filter panel · Event Detail.
5. Export all three to Figma (or screenshots) and bring them back to me — I'll score them against PART C's rubric and we choose together.

---

## PART A — THE MASTER PROMPT (paste everything between the lines)

---------------------------------------------------------------

You are designing the consumer face of **ONE LIVE** — a live-music discovery platform launching in Austin, Texas. You are being asked for world-class, category-defining work. Read all of this before designing; every constraint is intentional.

### 1 · VISION, MISSION, OBJECTIVES

**Vision:** A world where live music is easy to find, fairly represented, and culturally valued. At scale: to let culture grow without being stripped of its soul.
**Mission:** To assemble truth about live music, protect discovery from distortion, and help real culture travel.
**What ONE LIVE is:** a system of record for what's really happening tonight — artist-first by structure, trust-driven, calm, useful, real. Culture becomes infrastructure, not content.
**What ONE LIVE is not:** not ticketing, not a social feed, not pay-to-play, not an algorithm chasing engagement.
**Objectives this design must serve:**
- A fan answers "what should I do tonight?" in **under 10 seconds**, no account, no login, loads in under 2 seconds.
- Every show that's really happening is findable; nothing is promoted because someone paid. Discovery is never for sale.
- The product feels inevitable in Austin at SXSW and equally at home on a quiet Tuesday.

### 2 · THE TRUST-FOUNDED PHILOSOPHY — AND WHY IT IS FOUNDATIONAL

Trust is not a feature of this product; it is the product's load-bearing wall. The company's competitive analysis is explicit: if discovery integrity breaks, every other advantage collapses and the platform becomes just another listings clone. So the design must *embody* trust rather than *claim* it:

- **Trust is earned by delivered value, never by badges.** The interface never says "verified," "confirmed," or "trusted." No shields, no checkmarks, no trust-score chrome. The proof is that the listings are simply right, complete, and fast — every time. Competence shown, not told.
- **Automagic.** The human conscious mind processes only a trickle of what the senses take in (on the order of tens of bits per second against millions arriving). Design for that bottleneck: the right answer appears with near-zero conscious effort. Minimal choices, instant comprehension, no onboarding, no cognitive tax. Everything easy. Everything simple.
- **Honesty in the rare uncertain case:** when a listing's details are less certain, mark it with **one small, quiet icon only** (no label, no color alarm). Tapping it opens a small, instantly dismissible sheet that says, in calm plain language, that details for this show may change and the fan may want to double-check with the venue — with the venue's own site linked right there. One tap in, one tap gone. Never a warning tone; a courtesy.
- **Nothing real is ever hidden.** Uncertain shows still appear. Money never decides what is seen. Sponsored anything, if it ever exists, is separate, labeled, and never inside discovery.
- **Consistency is sacred:** the same rules every day, for every artist, at every scale. The brand should *feel* like something that keeps its word.

### 3 · EMOTION · FEEL · MOOD (design to these words)

**The moment:** It's 9:04 PM on a warm Austin night. You're on a sidewalk on East 6th, phone in one hand, a friend saying "so what are we doing?" Neon spills from a bar window. Somewhere a kick drum is already going. You have about ten seconds of everyone's patience.
**The emotion to create:** the small thrill of *anticipation* — the night is still unwritten and full of real options — fused with *calm certainty*: this thing knows, and it's right. No FOMO anxiety, no doomscroll dread, no decision fatigue. The feeling of a friend who always knows what's on and has never once been wrong — and never makes it about themselves.
**The feel in the hand:** effortless, immediate, warm. One thumb. The list *is* the interface. Scrolling feels like walking down a street of open doors. Tapping "Hear it" is leaning your ear toward a doorway for three seconds. Nothing ever asks the user to work.
**The mood of the surfaces:** night-native. The palette should feel like Austin after dark — stage light, marquee glow, warm air, human — never corporate, never clinical, never crypto-neon, never nostalgia-kitsch. Daylight mode exists but the soul is nocturnal. Typography is confident and a little loud (it's live music) yet never at the cost of instant scanability. Motion is minimal and physical — a soft settle, a gentle press — never showy; respect reduced-motion preferences.
**The personality in words:** calm, useful, real. Understated confidence. Zero hype. The tagline is: **"Less chaos. Real shows."** — the design is that sentence made visual.
**What it must never feel like:** an ad platform, a ticket kiosk, a social network, an algorithm's opinion, a brand shouting.

### 4 · FUNCTIONALITY (fixed product spec — do not redesign the logic, design its expression)

Screen 1 — **Tonight feed** (default, titled "Tonight in Austin"): chronological list by start time; each row: artist name(s), genre tag(s), venue, start time, Free vs Ticketed indicator, and a "Hear it" control that plays an inline music preview without leaving the list. **Each card may also carry a "Spark Line" — a 3, 5, or 7-word vivid, emotional description of the act's work (e.g., a self-described "doom-laden desert blues, slow and holy") — drawn either from the artist's own words or from a named critic/tastemaker with a tiny attribution ("— Austin Chronicle"). The Spark Line is NOT required to be a sentence: it may be words, fragments, letters, punctuation, or typographic play ("brass. menace. amen." / "loud——then unbearably tender"). It is the card's curiosity hook: sensory, specific, never generic marketing language. Alongside it, each card may carry an "Emotion Glyph" — one small expressive symbol (or two-glyph pair) that conveys the emotional experience the fan will have, derived from the creator's own description of their work. The glyph is emotional weather, not a rating and not a brand mark: two listings may feel melancholy and euphoric respectively, and both are equally beautiful. Where no sourced line or creator description exists, a quiet **AI-drafted Spark Line** may appear as last resort — composed only from the artist's own public materials (their bio, their site, their words elsewhere), faithfulness-gated by the eval harness, and carrying a very subtle mark that identifies it as machine-drafted without shouting: the line renders in a slightly distinct register (italic, one shade quieter) with a small "✳" and the attribution "— first notes"; tapping it opens the same one-tap-dismiss sheet pattern used elsewhere: "Drafted from [artist]'s own materials. [Artist] can make it theirs anytime." The moment a creator claims, their words replace ours — the AI draft is a placeholder and a reason to claim, never a voice that competes with the artist's. Never invent facts; describe only.** Date tabs: Today / Tomorrow / This Week. A quiet entry point to filters. Works without any account.
Screen 2 — **Filter panel** (slide-in): Genre multi-select (Rock, Hip-Hop, Jazz, Electronic, Country, Metal, Experimental, Latin) · Show type (Free / Ticketed) · Venue search · Neighborhood (Downtown, East Austin, South Austin). Instant apply, obvious clear.
Screen 3 — **Event Detail:** artist name(s); embedded music player (loads without redirect); genre(s); date; exact start time; estimated duration; venue name + address; map link; parking info; ticket link (opens externally); Add to calendar; Share; a small quiet "Something off?" link for corrections. If details are uncertain: the single small icon + dismissible explainer sheet with the venue's site link, as described in §2.
Accessibility & performance are part of the design, not after it: WCAG 2.2 AA contrast, comfortable ~44px touch targets, one-hand reach, fast-feeling (LCP ≤ 2.5s budget), light + dark themes.

### 5 · THE PAYOFF (what success looks and feels like)

The fan locks their phone within ten seconds holding a decision they feel good about, and the show is exactly as promised when they walk in. That kept promise, repeated nightly, is the entire brand. For artists it means being findable without paying; for venues it means full rooms on honest information; for the city it means its culture is visible. The design's job is to make keeping that promise feel effortless, warm, and quietly premium — value first, trust as the residue of value delivered.

### 6 · MAKE ME WANT TO CLICK — BEHAVIORAL ARCHITECTURE (apply deliberately, ethically)

Design every surface so the next tap feels irresistible — using the following frameworks by name, and only in their white-hat form. ONE LIVE's charter forbids engagement-chasing for its own sake; every mechanism below must pass the reflection test: if the user saw exactly how the screen influenced them, they'd say "yes, that's what I wanted anyway."

**A. The Hook (Nir Eyal — Trigger → Action → Variable Reward → Investment).**
- *Internal trigger to own:* the 6–9 PM feeling — restlessness, "what's happening tonight?" The design should become the automatic answer to that feeling, the way boredom summons certain apps. External triggers stay minimal and earned.
- *Action:* one thumb, one tap, zero friction — easier to act than to wonder.
- *Variable reward — the honest kind:* the city itself is the slot machine. Tonight's lineup is genuinely different every single day, so the feed delivers all three of Eyal's reward types without manufacturing anything: the **hunt** (finding the show), the **tribe** (a scene to belong to), the **self** (taste — "I found it first"). Design the feed reveal to honor that nightly freshness: opening the app should feel like lifting the needle onto a new record.
- *Investment:* every small act — saving a show, tapping a genre, playing a preview, filing a correction — visibly makes tomorrow's ten seconds even better. Show the compounding.

**B. Choice architecture (Thaler & Sunstein).** Defaults do the deciding: default view is tonight, sorted by time, nearby — roughly 80% of users live in the default, so the default must already be the perfect answer. Structure complex choice: eight genres as bounded, tappable categories, never an open-ended search burden. Use position and salience honestly (top of list = soonest show, an ordering the user would endorse). Zero dark patterns — no fake scarcity, no guilt, no confirm-shaming, nothing the user would call a trick on reflection.

**C. Sparking curiosity (Loewenstein's information-gap theory).** Curiosity ignites when a specific question opens and the answer sits one gesture away. Engineer these gaps on purpose: a band name you don't know + a genre tag you love = an itch; "Hear it" scratches it in three seconds. **The Spark Line is the primary gap-opener: seven words of vivid description ("swamp-gospel stomp with brass and menace") activate a question only the preview or the show itself can answer.** Cards show *enough to activate the question, never so much that there's no reason to tap.* Let one detail per card be a hook, not a summary. The interface should feel like a row of slightly-open doors.

**D. Common structure of the world's most returned-to products** (synthesized: TikTok/social feeds, Duolingo, Wordle, Spotify — the designer should echo the structure, never the skins):
1. **Near-zero activation energy** — the first rewarding moment arrives in seconds, no login, nothing to learn.
2. **A natural daily reset** — Wordle's one-a-day and Duolingo's daily loop create ritual; ONE LIVE gets this *for free* because tonight only happens once. Treat "Tonight" as the daily edition: dated, fresh, gone tomorrow. Anticipation over dread — celebrate showing up, never guilt absence.
3. **Genuinely variable rewards in an endless-but-bounded feed** — different every visit, yet finite (tonight ends), which is calmer than infinite scroll and even more precious.
4. **Visible compounding investment** — the product demonstrably gets more *mine* with use.
5. **A shareable artifact** — Wordle's grid taught the world: give people a beautiful, compact way to show their night (a share card for a show or a night plan) that markets the product socially without discovery ever being social-driven.
6. **Liveness** — subtle signals that the surface is alive *right now* ("just announced," counts ticking, tonight's pulse), because dynamic beats static for return visits.
7. **Identity, gently** — over time the product reflects who the user is (their genres, their venues, their nights) — belonging without leaderboards, memory without streak-guilt.

### 7 · DIFFERENTIATION MANDATE — 3 DISTINCT DIRECTIONS

Produce **three named, fully distinct design directions**, each with: a name; a complete color system in hex (dark + light); typography pairing; one *signature element* unique to ONE LIVE (a visual device no competitor uses); all three screens; a 3-sentence rationale tying it to the emotion/mood above; and a one-line statement of what it deliberately avoids.
The three directions must be genuinely different **from each other** (not one palette in three tints) and **from every competitor's visual language**. Explicitly avoid: Spotify's neutral charcoal + single green accent; DICE's stark black/white poster-type minimalism; Resident Advisor's gray editorial austerity; Bandsintown's teal + photo-grid; Ticketmaster/Eventbrite/AXS corporate blue ecommerce chrome; Songkick's utility beige; Luma's pastel gradient softness; generic AI-gradient purple. No checkmarks, no shields, no star ratings, no trust badges of any kind.

---------------------------------------------------------------

## PART B — DIRECTION-SPLITTING INSTRUCTION (append one line per run)

Run 1: "Direction 1 of 3 — lean warm/analog-human (night warmth, human texture)."
Run 2: "Direction 2 of 3 — lean electric/kinetic (city energy, motion implied in stillness)."
Run 3: "Direction 3 of 3 — lean editorial/monumental (quiet authority, type-led, archival confidence)."
(These are mood *leans*, not templates — the tool still owns the design choices within each.)

## PART C — EVALUATION RUBRIC (how we'll judge the 3 returned options)

Score each direction 1–5 on: (1) 10-second answer test on the feed screen; (2) night-sidewalk legibility (contrast, glare, one-thumb); (3) trust-by-craft — zero badges yet feels dependable; (4) distinctiveness vs the named competitors (would a screenshot be recognized as ONE LIVE?); (5) emotional fidelity to §3 (anticipation + calm certainty); (6) accessibility compliance evident in the comps; (7) survivability — will this look right in year 3, across cities, in light mode; (8) **click-pull** — does each card open a curiosity gap that makes the tap feel inevitable, and does the whole screen pass the white-hat reflection test? Highest honest total wins; ties broken by the signature element's strength.

## SOURCES (behavioral architecture research)
- Hook Model: https://www.nirandfar.com/how-to-manufacture-desire/ · https://amplitude.com/blog/the-hook-model · https://www.productplan.com/glossary/hook-model
- Choice architecture: Thaler, Sunstein & Balz, "Choice Architecture" — https://www.researchgate.net/publication/269517913_Choice_Architecture · https://www.behavioraleconomics.com/resources/mini-encyclopedia-of-be/choice-architecture/ · white-hat/dark-pattern reflection test: https://yukaichou.com/behavioral-analysis/nudge-theory-thaler-sunstein-choice-architecture/
- Curiosity / information gap: Golman & Loewenstein — https://www.cmu.edu/dietrich/sds/docs/golman/golman_loewenstein_curiosity.pdf · https://psychologyfanatic.com/information-gap-theory/
- Return-habit patterns: Duolingo streak research (7-day streak → 3.6× course completion) — https://blog.duolingo.com/how-duolingo-streak-builds-habit/ · https://uxmag.com/articles/the-psychology-of-hot-streak-game-design-how-to-keep-players-coming-back-every-day-without-shame · Wordle mechanics (daily scarcity, variable reward, shareable artifact) — https://uxmag.com/articles/the-fascinating-psychology-tricks-that-make-wordle-so-addictive · ethical streak restraint ("celebrate the return, never guilt") — https://yukaichou.com/gamification-study/master-the-art-of-streak-design-for-short-term-engagement-and-long-term-success/

## SOURCES (tool selection research)
- https://www.nxcode.io/resources/news/google-stitch-vs-figma-ai-design-comparison-2026
- https://ortemtech.com/blog/ai-design-tools-comparison-2026-figma-v0-google-stitch/
- https://www.nxcode.io/resources/news/google-stitch-vs-v0-vs-lovable-ai-app-builder-2026
- https://flowstep.ai/blog/best-ai-ui-design-tools/
- https://www.banani.co/blog/12-stitch-ai-alternatives
- https://www.imagine.art/blogs/google-stitch-alternatives
- https://frontman.sh/blog/best-ai-tools-ui-ux-designers-2026/

---

## APPENDIX — EMOTION GLYPH ENGINE (backend spec; context for the designer, built by us)

**Concept (founder, 2026-07-12):** an invisible backend engine attaches one small expressive glyph to each listing, derived from the creator's own description of their work — conveying the emotion the fan will experience. Not branding; emotional weather.

**Pipeline:**
1. **Input:** creator's self-description (claim-flow "describe your sound in seven words" field, bio, or consented uploaded materials). No description → no glyph. Never inferred from third-party scraping.
2. **Emotion mapping:** AI (existing Claude extraction layer) maps the description onto **Plutchik coordinates** — 8 primary emotions (joy, trust, fear, surprise, sadness, disgust, anger, anticipation) × 3 intensity levels, plus 24 dyads/triads (~56+ nameable states: "love = joy+trust," "awe = fear+surprise"). Output: `{primary, secondary, intensity, confidence}`. Sources: https://en.wikipedia.org/wiki/Emotion_classification · https://www.simonwhatley.co.uk/writing/plutchik-wheel-of-emotion/ · https://pmc.ncbi.nlm.nih.gov/articles/PMC8409663/
3. **Deterministic glyph lookup — not free-form generation:** coordinates resolve into a curated **Emotion Glyph Lexicon** (~40–60 glyphs + sanctioned pairs). Deterministic mapping = auditable, consistent, regression-testable via the existing eval harness.
4. **Lexicon rules:**
   - Only glyphs with empirically **low sentiment ambiguity** (per the Emoji Sentiment Ranking, Novak et al. 2015) are admitted — research shows only ~4.5% of emoji carry consistently low interpretation variance, so the lexicon is small on purpose. https://www.npr.org/sections/thetwo-way/2016/04/12/473965971/lost-in-translation-study-finds-interpretation-of-emojis-can-vary-widely · https://link.springer.com/article/10.1007/s10919-022-00421-6
   - **Self-rendered single glyph set** (open-licensed, shipped as SVG) — never native platform emoji, because identical codepoints render and read differently on Apple vs Google vs Samsung (Miller et al. 2016: cross-platform interpretation variance, some emoji flipping sentiment polarity entirely). One set, every device, one meaning. https://arxiv.org/pdf/1709.04969 · https://pmc.ncbi.nlm.nih.gov/articles/PMC6803511/
   - **Banned:** any glyph culturally read as a rating or endorsement (🔥 ⭐ 💯 👑 ❤️ 👍 and kin). The glyph must never create a visible hierarchy between listings — discovery neutrality applies to feelings too.
   - Every glyph carries an accessible text equivalent (aria-label, e.g., "mood: slow-burning, tender") — WCAG 2.2 non-text content rule.
5. **Creator control (canon):** the assigned glyph appears in the creator dashboard with one-tap replace/remove from the sanctioned lexicon. Creator override beats the engine, always, and override events feed the eval loop as labeled training data.
6. **Provenance:** `emotion_glyph {glyph_id, plutchik: {primary, secondary, intensity}, source_text_ref, model, prompt_version, creator_override: bool}` — rides the existing provenance architecture; AI-disclosure treatment pending founder ratification (G-EG).
7. **Phase 2 option:** unique generated micro-glyph art per act (true one-of-one), deferred — cost, moderation, and consistency burdens not justified pre-launch.

---

## APPENDIX — THE DESCRIPTOR FOUNDRY (mandatory pipeline for ALL AI-created descriptors)

Applies to every machine-drafted descriptor: Spark Lines (tier C), Emotion Glyph assignments, Emotion Cloud compositions, and any future AI-authored surface text. No single-shot generation ever reaches a fan.

**Stage 1 — Generate wide.** N = 6 candidates per descriptor, produced with deliberately varied style seeds (spare/lyrical/percussive/deadpan/sensory/fragmentary), all constrained to the creator's own source materials. Best-of-N with even small N materially beats single-shot (Stiennon et al. 2020; AlphaCode-style filtering — https://github.com/NousResearch/hermes-agent/issues/479 · https://arxiv.org/pdf/2501.01668 ).

**Stage 2 — Judge by tournament, not scores.** Candidates meet in a pairwise knockout judged against a fixed checklist (faithfulness to source · sensory vividness · 3/5/7 brevity · distinctiveness vs generic marketing · fit to the assigned Plutchik coordinates · calm-real brand register). Pairwise comparison is used because pointwise judge scores demonstrably fail at best-of-N selection — ties in ~67% of comparisons; explicit pairwise judging nearly triples selection recovery (21%→61%) — https://arxiv.org/abs/2603.12520 . Checklist-based judging further improves selection reliability (TICK — https://arxiv.org/pdf/2410.03608 ).

**Stage 3 — Fuse, don't just pick.** The top 2–3 survivors go to a synthesis pass that may combine fragments across candidates and add new connective tissue — style may be new; **facts may not** — producing the best-of-the-best final. This is the Fusion-of-N pattern: synthesis over selection measurably outperforms pure best-of-N by exploiting complementary strengths ("making, not taking, the best of N" — https://arxiv.org/pdf/2510.00931 ).

**Stage 4 — Independent verification.** The fused final is graded by a judge that did not generate it (Chairman pattern: independent judge, never self-evaluation — https://github.com/NousResearch/hermes-agent/issues/479 ; consistent with the repo's §0.2 generator/evaluator separation). Gates: every content word traceable to source materials; checklist re-pass; below threshold → descriptor is blank, never "good enough."

**Stage 5 — Provenance & regression.** All 6 candidates, the tournament bracket, the fusion diff, judge verdicts, model + prompt_version are logged. Golden-set regression in the existing eval harness on every prompt/model change. Creator override remains supreme and feeds back as labeled data.
