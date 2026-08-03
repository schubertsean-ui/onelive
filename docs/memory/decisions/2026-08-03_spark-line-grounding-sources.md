# Decision — Spark Line grounding = any TRUSTED source, no fabrication (hold resolved/amended)

One-line: founder-directed — a Spark Line's facts may be grounded in ANY trusted source (venue/org site, artist/person's own site, a licensed API, or a blurb/interview/blog/periodical about the artist), never fabricated. This resolves/amends the "free-lane grounding (MusicBrainz+Wikidata)" hold: MB/Wikidata was one acquisition path, not the rule.

**Date:** 2026-08-03. **Authority:** founder-directed, verbatim: *"there's supposed to be a logic to this. Follow the logic - the point being we don't make stuff up out of thin air but we can and do publish based on a verified source that we trust — eg venue/org site, artist/person's site, an API data from Ticketmaster or other API. If there's a blurb about an artist in a publication a social media interview or blog or periodical - that valid enough."*

## The logic (ratified)

Two halves, kept distinct:

1. **Never fabricate.** No fact "out of thin air." Every proper noun/number in a Spark Line must trace to real source material — enforced mechanically by the Descriptor Foundry faithfulness gate (`worker/descriptor/gate.py::assert_faithful`), unchanged.

2. **Grounding may come from any TRUSTED source.** The `SourceMaterial` the gate checks against may be composed from any of:
   - the **venue/organizer's own site** (a first-party host of the act's appearance);
   - the **artist/person's own site** and self-description;
   - a **licensed API** (Ticketmaster, SeatGeek, or other API data we ingest);
   - a **blurb/interview/blog/periodical about the artist** — a publication, a social-media interview, a blog, a magazine piece. That is "valid enough" grounding.

MusicBrainz + Wikidata identity resolution is ONE way to find an act's own materials among that broader set — not the whole rule. The **"free-lane grounding" hold is therefore RESOLVED/AMENDED** toward "go, grounded in trusted sources," with no-fabrication as the invariant.

## Kept distinct (the conflation rule)

- **Grounding TEXT ≠ displayed MEDIA.** This decision is about the facts/text the AI reads to compose an ORIGINAL 3/5/7-word descriptor (facts-only, no verbatim reproduction). It does NOT license reproducing a third party's photos or copyrighted text. The "trusted third-party photos" widening remains a SEPARATE, still-open legal-posture question.
- **Grounding source ≠ display trust state.** Where a fact came from grounds the descriptor; the event's own confidence/trust display is unchanged.

## Still separate / still gated

- **Tier-C generation at scale = model spend** — running the generator across many acts consumes paid model calls; a spend decision (cap first), unchanged by this.
- The **auto-publish switch** (`AUTO_PUBLISH_SPARK`, default OFF) — flips ON when the founder is ready; this decision removes the grounding-source blocker, not the spend/switch one.

## What changes in practice

The Spark Line acquisition step (when built) may pull `SourceMaterial` from the trusted-source list above, not just MB/Wikidata. The gate + judge still enforce faithfulness on whatever it pulled. No gate code changes here; this records the ratified source policy so a future build targets it.
