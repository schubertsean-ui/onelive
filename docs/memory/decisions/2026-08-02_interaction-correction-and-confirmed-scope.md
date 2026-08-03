# 2026-08-02 — Interaction correction + confirmed scope (founder-directed)

**Status:** RATIFIED (founder-directed this session). **Decider:** founder.
**Trigger (verbatim):** *"You are failing to review the entire report and canon
and most recent decisions on how to proceed and what has been approved. Re read
the entire repo and canon. Then come back to me with what I have clearly
confirmed I want and how you are to interact with me."*

This record is the session handoff. A new session reads it after
`session_reconcile` and before acting.

## The failure (this session) — three canon violations

1. **Asked permission for already-ratified work.** Proposed the Spark Line /
   Emotion Glyph / Descriptor Foundry content layer as "needs your go-ahead"
   when it is founder-RATIFIED canon (Phase 2 of the data-first `/tonight`
   plan). This is the EXACT mistake the founder already corrected on
   2026-07-31 (`2026-07-31_earned-confidence-engine-unbuilt.md`: *"Work the
   process!!"* — the design is decided; execute it). Repeat of a corrected
   class.
2. **Asked the founder to click merges and narrated CI status.** Violates the
   silent-merge directive 2026-07-25 (*"I don't want to know about merge — just
   get the job done at a world class level."*) and gates-advise/founder-decides
   2026-07-29.
3. **Delivered spiel + option-menus instead of doing the work.** Violates the
   comms canon 2026-08-01 (*"go easy on the marketing spiel — stick to what,
   how, why, why that why matters, expected outcomes"*).

## How the agent interacts with this founder (the contract)

1. **Proceed on ratified/authorized work. Decide → log a decision record → do
   it.** Do NOT ask permission for what canon already ratified. "RATIFIED,
   unbuilt" = build it; it is not a pending question.
2. **Interrupt ONLY for founder-crucial items, and BEFORE the work, as a
   decision:** money / new services / model-API spend at scale · legal posture ·
   trust-invariant CHANGES (altering/relaxing the invariants themselves) ·
   gate-threshold relaxations · go-live / allowlist · credential minting. These
   are the ONLY interrupts.
3. **Merge silently** under the ratified protocol (independent non-Claude
   evaluator APPROVE + every required check green on the final head, no
   founder-crucial content). No merge notices, no "click merge" asks. The
   evidence chain, changelog SHA, Kaizen row, STATE update go to disk.
4. **Communicate in what / how / why / why-that-why-matters / expected-outcomes.**
   No spiel, no superlatives, no menus for decisions that are the agent's to
   make. A message to the founder delivers a FINISHED thing, a decision only the
   founder can make, or a blocker + its smallest unblock. Intermediate state
   goes to disk (status-narration-not-progress).
5. **Disk is truth.** Reconcile at start; bookend STATE/TODOS/changelog at close.

## What the founder has confirmed he wants (scope — cited)

- **Current mission = Session Contract #32** (`STATE.md`; `2026-07-29_process-
  scaleback-ship-capcog.md`, verbatim *"Go — do both, then CAPCOG"*): CAPCOG
  live behind the Clerk stealth gate — licensed importers (Ticketmaster +
  SeatGeek, confirmed-tier, no AI) for the ticketed spine + crawl/AI pipeline
  for the long tail → real events → production Vercel deploy → allowlist testers
  → founder go/no-go. Then replicate for Lexington KY.
- **`/tonight` design = ratified FLOW v3.8 / Master Design Brief v2.4**, built
  DATA-FIRST in phases (`ONE_LIVE_TONIGHT_UI_CANON_v1.md` §13; the feed is
  *"data-starved, not broken"* §11; R-049). Phase 1 = card/two-door/lens on
  existing data; **Phase 2 = the content layer (contextual preview → Spark Line
  via Descriptor Foundry → venue enrichment → Emotion Glyph) — RATIFIED,
  unbuilt; BUILD IT, no fresh go-ahead needed**; Phase 3 = spatial/social
  (founder-gated).
- **Spark Line** (tiers A artist / B critic / C AI-drafted through the Descriptor
  Foundry: 6 candidates → knockout → Fusion-of-N → judge → provenance +
  golden-set regression; ✳ + "— first notes") and **Emotion Glyph** (Plutchik →
  deterministic ~40–60 SVG lexicon; creator self-description only; override beats
  engine) — RATIFIED product features. Building + running the Foundry is
  authorized. **"AI never publishes" is honored BY the eval-harness/gate on
  Foundry output (blank on sub-threshold), NOT by refusing to build.**
- **Earned-confidence / auto-publish engine** — design RATIFIED, engine
  half-built + dormant; the SWITCH flip is a founder trigger after safeguards are
  live (`2026-07-25_auto-publish-earned-confidence-ratification.md`).
- **Meta carousel engine** — RATIFIED, built, fail-closed OFF; live posting
  blocked on founder-minted credentials.

## What still needs the founder (narrow — do NOT build past these)

- The **auto-publish switch** flip.
- Any **new spend/service**: embedded music player (API key), map tiles
  (Mapbox), nearby-POI dataset, analytics service, model-API budget at scale
  (`ONE_LIVE_TONIGHT_UI_CANON_v1.md` §12 "founder-gated / spend-or-service").
- Still-PROPOSAL items: Feel/Vibe search mode (G-VT), draw-to-search map,
  Emotion-Glyph AI-disclosure treatment (G-EG), deep-review §10–§15, taxonomy.

## Session outcomes to carry forward

- **Go-live COMPLETE:** `1live.co` public, `auth.mode: "disabled"`, GoDaddy DNS →
  Vercel, SSL valid, `/api/health` green (#146, founder-merged).
- **OPERATING_RULES §4b** (API frugality / event-driven, no busy-poll) +
  Kaizen row — PR #145.
- **`/tonight` Phase 1 card** (on-card preview hook + real image-less cover) —
  PR #147 (draft, Vercel preview up). Part of finishing Phase 1.

## Next session's first move

`session_reconcile` → read this record + `ONE_LIVE_TONIGHT_UI_CANON_v1.md`
§11–§13 + Contract #32 → BUILD (finish Phase 1, then Phase 2 content layer per
canon), escalating ONLY the narrow founder-gated items above. Do not ask whether
to build ratified work.
