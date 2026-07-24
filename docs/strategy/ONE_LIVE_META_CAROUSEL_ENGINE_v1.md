# ONE LIVE — Meta Carousel Engine v1 (spec + shipped engine, 2026-07-24)

Greppable summary: founder-directed 2026-07-24 ("configure Meta carousel
options. True world class … trust model framework … human perception …
bits … positive emotions that drive action … Nir Eyal and Duhigg Atomic
Habits … maximal learning and improvement toward 100% interaction … easy
to share … tiered toward the content categories that have the most
content … agent-driven … learns and revises and reposts … continuously
optimized for [SEO/GEO] discovery"). STATUS: the ENGINE (generation,
tiering, learning, gate physics, GEO artifacts — `social/carousel/`) is
CODE in this PR, tested; the POSTING POSTURE (live Meta publishing,
credentials, cadence) is PROPOSAL pending the founder decisions in §9.
Companion canon: design brief §6 Behavioral Architecture (ratified),
`ONE_LIVE_GROWTH_LOOPS_AND_DESIGN_TOOLS_v1.md` (PROPOSAL, artifact loop),
`ONE_LIVE_CATEGORY_TAXONOMY_v1.md` (the 22 domains),
`ONE_LIVE_PLATFORM_API_INVENTORY_2026-07.md` (Meta API surfaces).

## 1. Trust physics first — what "AI never publishes" means here

A Meta carousel is an outward-facing product surface. The charter's scope
note is explicit: "AI never publishes" governs every outward-facing
product surface, not just the event pipeline. So the engine is built with
the same physics as `worker/promote.py`:

- **The autonomous loop cannot post.** `social/carousel/agent_loop.py`
  generates, learns, revises, and re-proposes — and is STRUCTURALLY
  unable to import the publisher (`publish_gate`); a test reads the
  module's imports and fails if that ever changes, exactly like the
  orchestrator-cannot-import-promote guard.
- **Publishing is gate-custodied and approvals are AUTHENTICATED.**
  `publish_gate.approve()` requires a human reviewer identity (AI author
  identities are refused, fail-closed) AND the founder-held signing key
  (`ONELIVE_APPROVAL_KEY` — never in the repo, never in agent sessions):
  the approval is an HMAC-SHA256 signature over the draft's SHA-256
  content hash, so a name string alone approves nothing and an agent
  cannot forge a sign-off. `publish_gate.release_for_publish()` verifies
  the signature, recomputes the hash, re-checks every featured event's
  CURRENT confidence and event_status (`scheduled` only — a
  cancellation after drafting blocks the post), and rescans the entire
  draft text surface for banned claim language. Edit after approval →
  the approval is void, mechanically.
- **What carousels may feature** (selection, not hiding — product
  surfaces keep showing everything per canon):
  - CANONICAL PUBLISHED rows only: every event must carry the
    canonical-read-path origin marker — candidate/pipeline rows are
    structurally refused, so marketing can never amplify what has not
    been promoted.
  - `confirmed` events: yes, freely. `likely`: only with the quiet
    uncertainty affordance the design brief mandates (no "confirmed"
    language, ever). `unverified` / `disputed`: never featured. On the
    product surface disputed stays visible-as-disputed (canon,
    unchanged); marketing simply does not amplify what the gate has not
    settled.
  - `event_status` is its own axis (Certainty Display Stack canon):
    only `scheduled` events are featured; cancelled/moved are excluded
    at selection and re-checked at release.
  - TRUTHFUL TIME FRAMING: each series claims exactly its verified
    window (tonight / this week / this month, from its cadence); events
    outside the window are excluded, so copy can never say "tonight"
    about a show next month.
- **No fabrication.** Slide copy is verbatim event facts (name, venue,
  time, price) from canonical rows, plus optional descriptor text that
  must carry Descriptor Foundry provenance. There is no free-text LLM
  slot anywhere in the render path. Provenance (event id + source) rides
  every slide.
- **No pay-to-rank leakage.** Carousel selection orders by trust state,
  recency, and data completeness — no paid placement input exists in the
  scoring function, and adding one is a trust-invariant change
  (founder-crucial, full stop).

## 2. The perception science the format encodes (bits, images, the 3-second gate)

Design choices below are constraints in code (`config.py`), not taste:

- **Vision is the widest pipe; conscious attention is the narrowest.**
  The retina delivers on the order of 10^7 bits/s; deliberate conscious
  throughput is measured in tens of bits/s. The implication: every slide
  leads with IMAGE, and text exists to be *recognized*, not read. MIT
  vision work shows scene gist extraction in ~13 ms; picture-superiority
  and dual-coding research (Paivio) show image+word memory beating
  word-only by large margins. Encoded: hook slide headline ≤ 8 words;
  per-slide overlay ≤ 12 words; one idea per slide; image mandatory.
- **The 3-second gate.** Feed scrolling decides in the first ~1–3 s.
  Slide 1 is a dedicated HOOK slide — it sells the *swipe*, not the
  event: curiosity gap (Loewenstein — open a specific question the next
  slide answers), a number promise ("7 shows under $20 tonight"), awe
  ("the room 2,000 people will be in at 9pm"), or humor. Encoded as the
  `hook_type` factor the bandit learns over.
- **Chunking (Miller/Cowan).** Working memory holds ~4 chunks
  comfortably. One event per slide; carousels default to 5–10 slides
  (Meta allows up to 20 on IG feed, 10 on FB carousel units — encoded as
  per-surface hard constraints); the bandit learns the count band that
  actually maximizes completion.
- **Motion and sound** (video slides, music/audio) are the
  highest-bandwidth attention hooks the format offers; v1 ships
  image-first with the media-type factor present (`video` levels exist
  in the factor space) so learning extends to Reels-style media the
  moment asset supply exists. Music selection on IG additionally feeds
  discovery (audio pages) — flagged in §8.

## 3. Emotion → action (why positive-emotion design is the sharing engine)

- **High-arousal positive emotion drives sharing.** Berger &
  Milkman's virality research: awe, excitement, and amusement raise
  sharing; low-arousal states (contentment, sadness) suppress it.
  Fredrickson's broaden-and-build: positive affect widens the
  action repertoire — exactly the "I could actually go to this"
  activation OneLive needs. Encoded: the `emotion_register` factor
  {excitement, awe, amusement, belonging, anticipation} chooses the
  creative register per carousel; negative-valence registers do not
  exist in the factor space (there is nothing for the optimizer to
  drift toward).
- **Berger's STEPPS** operationalized: Social currency (sharing a great
  night plan makes the sharer look plugged-in — the share line is
  designed to flatter the *sender*), Triggers (tonight/this-weekend
  timing anchors), Emotion (above), Public (branded visual signature),
  Practical value (real events, prices, times — the carousel is USEFUL),
  Stories (the night as a narrative arc across slides).
- **Humor and curiosity** are factor levels, not mandates — the bandit
  measures whether Austin audiences swipe for funny or for awe per
  category, instead of anyone guessing.
- **White-hat line (design brief §6, binding here too):** positive
  emotion in service of a real good night out, with real facts. No
  manufactured FOMO ("selling out!!" without a sourced signal), no dark
  patterns, no engagement bait that Meta's own guidelines penalize.

## 4. Habit architecture (Eyal · Duhigg · Clear), applied to a *feed* surface

The carousel program is the EXTERNAL TRIGGER arm of the ratified Hook
cycle — its job is to hand off into the product's own loop:

- **Eyal (Trigger → Action → Variable Reward → Investment):** the
  carousel is the trigger; the action is one swipe (smallest possible
  ask); the variable reward is real — *tonight is a genuinely new
  edition every day* (growth-loops doc: the reward needs no
  manufacturing); investment = save the post / follow / share to a
  friend ("who's in?" — the plan-share loop), each making the next
  trigger more likely to land.
- **Duhigg (cue → routine → reward):** publishing rhythm builds the cue.
  Same slot, same recognizable visual signature, per tier — e.g. the
  "Tonight in Austin" carousel at the same late-afternoon slot daily —
  so checking becomes the routine and the reward (a plan for tonight)
  reinforces it. Posting-time slots are a learned factor *within* a
  stable, recognizable cadence.
- **Clear (obvious / attractive / easy / satisfying):** obvious =
  consistent branded template + predictable series; attractive =
  emotion-led hook slide; easy = every CTA is one tap (save, share,
  follow; link-in-bio for the feed); satisfying = the final slide closes
  the loop ("screenshot this / send it to the friend who's always
  down") so acting feels complete. The share CTA is designed at *peak
  delight* (end of a great lineup), per the growth-loops evidence rule.

## 5. Tiered category carousels (the founder's "most content first" idea, mechanical)

`tiers.py` reads confirmed-event volume per domain (the 22-domain
taxonomy) over a rolling window and assigns cadence by supply — content
volume IS the tier key, exactly as directed:

| Tier | Rule (defaults, founder-tunable) | Cadence | Shape |
|---|---|---|---|
| T1 flagship | top domains ≥ 12 confirmed events/wk | daily/near-daily | "Tonight in Austin" + per-domain ("Live Music Tonight") |
| T2 strong | ≥ 5/wk | weekly | domain roundup ("This week in Comedy") |
| T3 long tail | ≥ 1/wk | bi-weekly/monthly | combined "Everything else worth leaving the house for" |
| below floor | < 1/wk | none | events ride T1/T3 combined carousels — no starved solo carousel ever posts thin |

Tiering is re-derived every cycle from live counts, so the portfolio
follows the data as new domains fill in (same "wind vane" logic as the
enrichment engine). A minimum-supply floor prevents the classic failure
of thin carousels for empty categories.

## 6. The learning loop (how "toward 100% interaction" is made honest and mechanical)

**North star: interaction rate = unique accounts that took ANY action
(swipe past slide 1, like, comment, save, share, profile visit, link
click) / accounts reached.** Supporting: save rate and share rate (the
two Meta's ranking rewards most and the two that map to OneLive's growth
loops), completion rate, follows per reach, and link CTR. 100% is an
asymptote, not a claim — the enforced property is CONTINUOUS MEASURED
IMPROVEMENT: the metrics ledger keeps a rolling baseline per (surface ×
tier) and flags any period that regresses against it, Kaizen-style; the
ratchet is monotone-improvement-or-explained.

**Why a bandit, not classic A/B.** Fixed-horizon A/B burns most
impressions on losing variants and answers one question per cycle. For
continuously-generated creative, current practice (and Meta's own
delivery machinery) is adaptive allocation. `bandit.py` implements
Thompson sampling over per-factor Beta posteriors — the standard,
inspectable, regret-optimal-in-class choice — with:

- **Factored design space** (hook_type × emotion_register × slide-count
  band × caption_style × cta_type × post_slot × media_type): each factor
  learns independently, so ~30 posts already teach real structure
  (a full factorial would need thousands).
- **Reward = interaction rate in [0,1]**, updated as fractional
  pseudo-counts scaled by reach (so a 50k-reach post teaches more than a
  500-reach post, capped to keep one viral post from freezing learning).
- **Exploration floor** so no factor level is ever starved (the ledger
  can always answer "did humor start working?").
- **Determinism for tests/audit:** seeded RNG; the whole learner is
  serializable state (JSON), inspectable — learning as updated weights,
  no black box, same posture as source-reliability priors.
- **Decay** on old evidence so the learner tracks a moving culture
  instead of averaging 2026 with 2027.

The loop the founder asked for — create → post → measure → learn →
revise → repost — runs as: `agent_loop.run_cycle()` (tier → sample
factors → generate drafts → queue for human approval) and
`agent_loop.ingest_results()` (Insights metrics → ledger → bandit
update). Only the approve/post step is human; everything else is the
agent, every cycle.

## 7. Share mechanics ("easy for people to share … coolly promote OneLive")

- Final-slide CTA rotates through learned share framings; the default
  set is designed on social currency, e.g. "Send this to the friend
  who's always down" — the share flatters the sender, not the brand.
- Every carousel's caption carries a clean short link (UTM-tagged
  per-post so link CTR is attributable in the ledger).
- Story-reshare is the cheapest share on IG: the template reserves
  safe margins so a reshared slide crops cleanly — a mechanical
  constraint in `config.py`, not a designer memo.
- The product-side artifact loop (growth-loops doc: the Wordle-style
  share card) is the long-term pair to this: carousels recruit in,
  artifacts share out. Cross-referenced, not rebuilt here.

## 8. GEO/SEO — optimized for machine discovery, continuously

Every carousel ships with a machine-discovery bundle (`geo.py`),
because "#1 in every criteria" is earned by being the most *citable*
structured source, for classic crawlers and answer engines alike:

- **schema.org JSON-LD**: `Event` markup for every featured event
  (name, venue w/ address, startDate, offers, performer) — the same
  markup the /tonight pages should carry (one generator, two surfaces),
  plus `SocialMediaPosting` for the carousel itself.
- **Alt text on every slide** — accessibility (WCAG canon) and machine
  legibility are the same artifact.
- **Caption keyword frame**: city + category + timeframe in natural
  language ("Live music in Austin tonight"), 3–5 hashtags (research
  consensus: small, specific tag sets outperform tag walls), venue/
  artist handle mentions (which also notify the supply-side loop).
- **llms.txt block + OG tags** for the linked landing page, so the
  destination answers AI-crawler questions with gate-verified facts.
- **The GEO flywheel is the trust model itself**: answer engines rank
  verifiable, attributed, fresh, structured data — OneLive's provenance
  chain is precisely that. We ship attribution-rich markup everywhere
  and never cloak; being the gate-verified source IS the moat.
- Continuous: the discovery bundle regenerates with every carousel and
  every event change; freshness is a property of the pipeline, not a
  campaign.

## 9. Founder decisions (the ONLY blockers — everything else in this doc is built)

1. **Meta assets + credentials (new service + credential minting =
   founder-crucial):** create/confirm the IG professional account + FB
   Page, a Meta app, and mint Graph API tokens (content publishing +
   insights) with spend/rate caps — agents never mint keys. There is
   deliberately NO Graph API client in the codebase until then (R-026;
   nothing stubbed — the posting boundary is built at this trigger, and
   metrics ingestion takes exported JSON meanwhile).
2. **Mint the approval signing key** (`ONELIVE_APPROVAL_KEY`): the
   secret the approving surface uses to sign approvals and autonomy
   records (HMAC-SHA256 over the draft hash / record payload).
   Founder-held: it lives wherever approvals happen (your machine, the
   ops console backend), NEVER in the repo and NEVER in agent-session
   env — that is what makes an agent-forged approval cryptographically
   impossible rather than merely filtered.
3. **Posting posture (go-live class):** ratify gate-custodied posting —
   founder (or founder-delegated human) approves per carousel in v1
   with a signed approval. A future "standing approval for T1
   templates" is a separate, explicit ratification; it is NOT assumed
   anywhere in code.
4. **Cadence + Sentinel wiring:** approve the tier cadences (§5) and,
   before any scheduled cycle, the healthchecks.io check + budget caps
   (charter: no scheduled loop without both — R-027).
5. **Optional:** ratify the interaction-rate north-star definition (§6)
   as the standing KPI for the program.

## 10. Autonomy ratification protocol (founder-directed 2026-07-24: "at some point soon I will want the AI to do everything and remove the human from the loop. So set up a process for me to sign off on that.")

The removal of the human from the posting loop is a TRUST-INVARIANT
CHANGE ("AI never publishes" on an outward-facing surface), so it can
only ever happen by explicit founder ratification — and per the
directive, the sign-off path is now BUILT, mechanical, and fail-closed
(`social/carousel/autonomy.py`), so when the founder says "go" it is a
recorded flip, not a code rewrite:

- **Autonomy levels** (staged, so trust is extended the way the gate
  extends confidence — on evidence):
  - **L0 (default, and the state whenever no valid record exists):**
    a human approves every carousel. This is today.
  - **L1 (standing approval):** the engine auto-releases carousels for
    founder-enumerated (surface × tier) combinations whose template and
    trust rules are frozen; anything outside the enumeration still
    requires per-post approval. Recommended first step out of L0.
  - **L2 (full autonomy):** the engine posts everything it generates,
    within budget caps and the unchanged trust selection rules
    (confirmed/likely-only, provenance, no fabrication — those NEVER
    relax at any level; autonomy changes WHO clicks post, never what may
    be said).
- **The sign-off process (the founder's three steps, one sitting):**
  1. Review the evidence pack the agent must assemble: last N posts'
     ledger rows (interaction/save/share trends vs baseline), zero
     trust-rule violations, and the exact template set to be frozen.
  2. Sign the decision record (`docs/memory/decisions/`) with the
     verbatim directive, the target level, and its scope.
  3. Approve the PR that commits the ratification file
     (`social/carousel/AUTONOMY_RATIFICATION.json`) citing that record
     — the file names the level, scope, founder identity, date, and
     decision-record path, and carries the founder's SIGNATURE: an
     HMAC-SHA256 over the record payload under `ONELIVE_APPROVAL_KEY`
     (produced by `sign_autonomy_record()`, run by the founder with the
     founder-held key — agents never hold it, so an agent cannot mint a
     grant that verifies).
- **Fail-closed physics:** no file → L0. Malformed, incomplete,
  UNSIGNED, or wrong-signature file → the publisher refuses to release
  ANYTHING (loud), because a broken or unauthenticated ratification
  must never fail open into autonomy. The gate re-validates the record
  (signature included) on every release. Any PR touching `autonomy.py`
  or the record is trust-path → mandatory non-Claude evaluator review,
  like every gate-custody change.
- **Reversibility:** the founder can revoke by deleting the record or
  committing `{"level": "L0"}` — one commit, immediate, no negotiation
  surface for the agent.

## 11. Cost discipline

v1 generation is deterministic templates over verified data: zero
marginal LLM cost per carousel. Descriptor text, when used, comes from
the Descriptor Foundry pipeline (already-gated spend). The bandit is
arithmetic. The only new spend this program can ever incur is Meta ad
budget, which does not exist in v1 (organic only) and would be a
founder money decision anyway.
