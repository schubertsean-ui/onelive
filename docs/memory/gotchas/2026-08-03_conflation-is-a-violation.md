# Conflation is a violation — reading completely is not enough; state it precisely

Retrieval tokens: `conflation`, `conflate`, `imprecise-invariant`,
`paraphrase-from-memory`, `quote-the-canon`, `keep-distinct-concepts-distinct`,
`precision-clause`. Governing rule: `docs/OPERATING_RULES.md` → Rule Zero
("State it precisely — CONFLATION is its own violation", founder-directed
2026-08-03). Companion: `gotchas/2026-08-02_skim-fragment-is-no-read.md`.

## The lesson

Rule Zero's first half fixes the INPUT (read the controlling docs in full, no
fragments). This gotcha fixes the OUTPUT. You can read every word and still fail
by MERGING two distinct things into one claim, or by paraphrasing an invariant
more narrowly (or more broadly) than the doc actually states it. A conflation
asserted as fact misleads exactly like a fragment read — and it is harder to
catch, because the reading was complete.

## How it showed up (2026-08-03, the Spark Line sourcing thread)

1. **Invariant stated too narrowly.** Said "only the entity's OWN image from its
   own domain" — but canon (`ONE_LIVE_VERIFIED_PREVIEW_ENRICHMENT_v1` §2, "past-
   year event photos") also allows **the venue/organizer's own-site imagery**. The
   venue is an entity/host too. Narrowing an invariant from memory is a violation.
2. **Distinct concepts merged.** Blurred **grounding text** (feeds the tier-C
   Spark Line; governed by the Descriptor-Foundry faithfulness gate) with
   **displayed preview media** (governed by media provenance/license). Different
   gates, different rules — never one claim.
3. **Mechanism conflated with mechanism.** Treated "crawl the entity's website"
   as if it were the ratified plan, when the plan is **resolve identity first**
   (MusicBrainz/Wikidata), THEN attach — skipping resolution risks same-name
   mismatch.

## The rule of thumb (do this, every time)

- When you ASSERT an invariant/guardrail: **quote the controlling text**, don't
  paraphrase from memory; state it neither narrower nor broader than the doc.
- Keep load-bearing separations apart by name, and cite each side to its source:
  - **trust in a fact ≠ right to reproduce an image** (credibility vs copyright).
  - **grounding text ≠ displayed media** (Foundry gate vs media/license gate).
  - **resolve identity ≠ crawl a site** (identity-first cascade vs raw fetch).
  - **"own domain" includes the venue/organizer as host,** not only the artist.
- When you feel two ideas collapsing into one sentence: STOP, split them, cite
  each, then write the claim.

## How you know you conflated

You stated a rule's scope from memory instead of its words; two distinct
gate-governed categories appear in one sentence with one verb; a specific
mechanism got described with a general one. Any of these = STOP, separate, quote,
re-state.
