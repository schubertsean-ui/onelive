# ONE LIVE — THE EMOTION & VIBE LAYER (Concept Spec v1)
**Compiled 2026-07-12 · Status: PROPOSAL — taxonomy and guardrails await founder ratification (Gap G-VT).**
**Founder concept thread:** Spark Line → Emotion Glyph → Emotion Cloud images (multiple per artist/event) → applied to venues & locations → **"Feel" search mode** ("what do I want to feel tonight?") → per-user concierge experience → deep analytics moat.

---

## 1 · THE TWO-AXIS TAXONOMY (the ask: emotions AND vibes)

The layer needs two distinct vocabularies, because they answer two different fan questions:

**AXIS 1 — EMOTIONS: "What will I feel?"** (grounded in Plutchik's wheel: 8 primaries × 3 intensities + dyads ≈ 56+ states — sources in Emotion Glyph appendix)
Fan-facing emotion vocabulary, each pinned to Plutchik coordinates so the engine stays auditable:

| Fan word | Plutchik coordinates |
|---|---|
| Euphoria | joy (intense) |
| Warmth / Love | joy + trust |
| Serenity | joy (mild) |
| Awe | fear + surprise |
| Wonder | surprise + trust |
| Thrill | anticipation + fear |
| Nostalgia | joy + sadness |
| Melancholy | sadness (mild–mid) |
| Catharsis | sadness + joy (release arc) |
| Tenderness | trust (mild) + joy |
| Defiance | anger + anticipation |
| Menace (delicious) | fear (mild, chosen) |
| Longing | sadness + anticipation |
| Transcendence | awe + joy |
| Mischief | joy + surprise |
| Grit / Resolve | anger + trust |

**AXIS 2 — VIBES: "What is the room?"** Vibes are atmospheric, not psychological — they describe the scene a body walks into. Seven dimensions, each a slider, each with fan-facing vocabulary (structure follows the locked "global taxonomy with local mappings" strategy — dimensions are global; vocabulary can localize per city):

1. **Energy:** still → swaying → nodding → moving → dancing → frenzied
2. **Intimacy:** solo-in-the-dark → close → communal → packed → gloriously anonymous
3. **Texture:** raw → gritty → DIY → worn-in → polished → plush
4. **Light:** candlelit → dim → neon → stage-lit → golden-hour → daylight
5. **Sound pressure:** hushed → warm → loud → chest-rattling
6. **Hour:** early → prime → late-night → after-hours
7. **Social mode:** seated-listening → bar-lean → sing-along → dance-floor → mosh → mingle

**Fan-facing vibe words** (each maps to a dimension vector, ~40 at launch, locally extensible): sweaty · holy · rowdy · velvet · dusty · cosmic · swampy · feral · dreamy · thunderous · candlelit · cavernous · scrappy · slick · woozy · honky-tonk · basement · rooftop · chapel-quiet · block-party …

**Composition rule:** *Artists carry an emotion signature. Venues carry a vibe signature. An event's cloud = artist emotion × venue vibe × the hour.* This is why the same band reads differently at a listening room vs. a warehouse — and why the layer applies to venues, restaurants, galleries, and every future cultural vertical (a dish, a gallery show, and a poetry night all have emotion × vibe coordinates). Venue vibe signatures are stable and claim-flow-sourced ("describe your room in seven words"); event clouds are composed nightly.

## 2 · THE EMOTION CLOUD (the visual)

Like a word cloud, but of feelings: a small generative image per artist/venue/event where emotion and vibe words (and glyphs) size by strength of signal. Multiple variants per subject are allowed and desirable — the cloud is weather, not a logo. Rendering follows Emotion Glyph rules: self-rendered single visual language, no rating-adjacent symbols, text equivalents for accessibility, deterministic from the underlying coordinates (auditable, regression-tested), creator/venue one-tap edit-or-remove.

**Signal sources (trust-first waterfall):** (A) creator/venue self-description via claim flow → (B) attributed critic/tastemaker language → (C) opt-in one-tap post-event fan feels ("How did it feel? [3 taps max]") which accrete over time → never biometric, never scraped inference, never invented. No signal → no cloud.

## 3 · "FEEL" — THE SEARCH MODE (the differentiator)

A second discovery mode beside Tonight: the fan declares an emotional intent — *feeling now / want to feel / want to experience* — by tapping emotion + vibe words (the Plutchik wheel itself is a beautiful candidate input control). Results are **filtered, never ranked**: within a feel-match, order remains chronological. This keeps the feature inside the locked "no algorithmic ranking beyond time order" and discovery-neutrality invariants — the user pulls; the algorithm never pushes. No competitor searches by feeling; everyone searches by genre. Genre says what the music is; this says what the night will do to you.

## 4 · CONCIERGE & THE EMOTION GRAPH (the moat)

Accreted signals form the **Emotion Graph** — city × venue × artist × hour × felt-emotion — a third Intelligence-tier moat beside Heartbeat and Predictive (it compounds identically: every night adds labeled data no competitor can reconstruct). Per-user concierge ("crafted just for them") ships as an **explicit opt-in lens** with three hard rules: (1) default experience stays the neutral chronological feed; (2) user emotional data is consent-gated, retention-limited, never sold, never shared at individual level — partners get aggregates only (existing canon extended from creators to fans); (3) money never touches feel-results. Post-use emotional check-ins ("how do you feel now?") double as the wellbeing metric the founder wants: the product should measurably leave people better than it found them.

## 5 · LEGAL GUARDRAILS (researched; counsel ratification under G1)

The design deliberately stays on the safe side of the emotion-AI regulatory line:
- **EU AI Act Art. 5(1)(f)** prohibits AI *inferring* emotions **from biometric data** in workplace/education contexts (in force; penalties to €35M/7% turnover), and **Art. 50(3)** imposes transparency duties on emotion-recognition deployers generally. Our layer performs **no biometric processing and no inference of a user's current emotional state** — users *declare* what they want to feel (a preference, like a genre tap), creators self-describe, and fans self-report voluntarily. Declared preference ≠ emotion recognition. Sources: https://fpf.org/blog/red-lines-under-eu-ai-act-unpacking-the-prohibition-of-emotion-recognition-in-the-workplace-and-education-institutions/ · https://www.williamfry.com/knowledge/the-time-to-ai-act-is-now-a-practical-guide-to-emotion-recognition-systems-under-the-ai-act/ · https://www.teamed.global/insights/is-emotion-recognition-at-work-legal-in-eu
- **GDPR:** self-reported feeling data tied to a user is personal data warranting granular consent, dashboards, easy deletion, and short default retention (per compliant-emotion-system practice: https://secureprivacy.ai/blog/gdpr-compliant-emotion-recognition ). Build Berlin/London-ready from day one (already locked strategy).
- **Hard bans (charter-grade):** no biometric emotion inference, ever; no mood inference from passive behavior without explicit opt-in and disclosure; no individual-level emotional data in any partner product.

## 6 · REQUIRED COMPARISON — A: Declared-feel search vs B: Inferred-mood personalization

| Dimension | A: User declares the feeling (recommended) | B: System infers mood from behavior |
|---|---|---|
| Speed | Ships with taxonomy — weeks | Months + model risk |
| Accuracy | High — intent from the source | Noisy proxy, silent failures |
| Cost | Low (filtering + taxonomy) | High (modeling, monitoring, compliance) |
| Complexity | Low; no regulatory gravity | EU AI Act/GDPR gravity; consent architecture |
| Maintenance | Taxonomy curation only | Drift, audits, disclosure duties |

**Recommendation: A now; B never by default** — revisit only as explicit opt-in with counsel sign-off.

## 7 · PHASING
- **P1 (with launch):** taxonomy ratified; claim flows gain the seven-words fields (artist sound + venue room); Spark Line + Emotion Glyph on cards; "Feel" filter chips.
- **P2:** Emotion Cloud visuals; post-event one-tap feels; Feel mode as full surface.
- **P3:** Emotion Graph analytics products (aggregate-only); opt-in concierge lens; multi-vertical extension (food, art, theater) using the same two axes.

## 8 · OPEN GAPS FOR FOUNDER (review one-by-one)
- **G-VT-1:** Ratify the two-axis structure (16 emotions / 7 vibe dimensions / ~40 vibe words) — add/cut vocabulary?
- **G-VT-2:** Confirm composition rule (artist=emotion, venue=vibe, event=product)?
- **G-VT-3:** Post-event feels — opt-in prompt copy and 3-tap cap OK?
- **G-VT-4:** Concierge = opt-in lens, never default — confirm as charter-grade rule?
- (Outstanding: G-EG glyph disclosure · G-SL waterfall · Q11 credentials · G1–G6 · G-F)
