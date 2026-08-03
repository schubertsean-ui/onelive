# 2026-08-02 — Design direction: execute the developed UI Canon, not the desktop critique

## Context

On viewing the live `/tonight` on desktop, the founder gave a sharp set of
reactions to the current card/feed. I initially proposed to "take your critique
as the brief and rebuild it." The founder corrected that framing directly.

**Founder, verbatim (desktop reactions, 2026-08-02):**
> "I'm on desktop. I don't like that a new window opens for Artist or Venue — one
> card is better than two ... I don't like not seeing the text box for the venue ...
> no map ... no Nearby ... no links to content ... 'Live Music' is not descriptive
> enough — it needs the genre and description ... top of the page is so cluttered ...
> no way this incorporates world class design principles."

**Founder, verbatim (the correction that governs, 2026-08-02):**
> "NO!! do not take this as the brief — use the world class design as developed.
> Execute that and THEN we can go from there."

## Decision (DECIDED)

1. **The ratified UI Canon is the brief.** The design to build is
   `docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md` (RATIFIED, on master): the
   two-door "room" card + slide-out lens over one river, the build-sequence in
   §13 (data-first — "the UI is starved, not broken"), and the ratified-but-
   unbuilt richness (Spark Line, Emotion Glyph, preview media, venue photo,
   specials, map/nearby, genre+description scent). Execute THAT.
2. **The desktop critique is INPUT, not the brief.** The founder's reactions are
   not discarded — they are recorded here and become the "THEN we can go from
   there" agenda, evaluated *after* the canon is faithfully executed. Notably,
   several critique points (venue text box, map, Nearby, content links,
   genre+description, decluttered top) are things the canon *already specifies*
   but the live build has not yet delivered — i.e. the critique largely describes
   the gap between the ratified canon and the starved live UI, which confirms the
   decision rather than contradicting it.
3. **"One card, not two" is the one genuine open tension.** The live card opens a
   two-door choice (Artist / Venue) that the founder read on desktop as "a new
   window opens ... one card is better than two." The canon's model is a single
   "room" card whose two doors are *lenses within the same card/river*, never a
   new page/window. So the founder's instinct and the canon AGREE at the level of
   intent (no context-losing second surface); the live implementation's
   presentation is what read as "two." Resolution: build the canon's single-card
   in-place lens faithfully; if the founder still wants the two-door affordance
   itself softened after seeing it executed, that is a post-execution refinement,
   logged then — not a reason to abandon the canon now.

## Why this way (not "rebuild from the bullets")

- The UI Canon is founder-RATIFIED and grounded (see the User-Journey canon §7's
  12-framework methodology table). A live off-the-cuff bullet critique of a
  *starved* build is not a ratified replacement for it; treating it as the brief
  would discard months of ratified design work on a first-glance reaction — the
  exact mistake the founder stopped.
- Honest reading of the critique shows most of it is "the canon isn't built yet,"
  not "the canon is wrong." The correct response is to *build the canon*, not to
  re-derive a new one.

## Consequence / next step (bound by process canon §4a / journey §8)

Executing the canon is a substantive build → it requires a **plan presented for
founder approval first** (WHAT/HOW/WHY/WHY-IT-MATTERS/OUTCOMES), then the loop
(build → validate → evaluator → preview → approval → merge → measure → independent
review-of-work). The world-class UI/UX plan is the next founder-facing artifact;
no redesign code lands before that plan is approved. The build-sequence is
data-first (UI Canon §13): the biggest lever is wiring the built-not-wired
enrichment/scent data the cards are starving for, not more chrome.

## Status

DECIDED and recorded (closes the independent review's #1 finding: the
two-door-vs-single-card resolution and the founder's design feedback were
unrecorded on disk). Founder verbatim preserved above.
