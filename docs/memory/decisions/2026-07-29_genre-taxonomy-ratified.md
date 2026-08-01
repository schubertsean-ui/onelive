# 2026-07-29 — Genre taxonomy RATIFIED & WIRED (founder)

**Directive (founder, verbatim, 2026-07-29):** "ratify-and-wire the 18 genres
as the next increment after the share card and recheck Spotify sub genre."

## Decision

The Layer-1 EIGHTEEN of `docs/strategy/ONE_LIVE_GENRE_TAXONOMY_v1.md` are
ratified verbatim and become product canon, superseding the flat 8. The 18:
Rock · Pop · Hip-Hop/Rap · R&B/Soul · Electronic/Dance · Country · Latin ·
Jazz · Blues · Folk/Americana · Metal · Punk · Reggae · Classical · World ·
Singer-Songwriter · Indie/Alternative · Experimental. Today's 8 map losslessly
(proven mechanically in `web/lib/genres.test.ts`).

## The hard pre-ratification check (Spotify recheck) — CLEARED

The doc gated ratification on re-verifying the Spotify microgenre claim against
authoritative data. Result: the "thousands of microgenres" claim is CONFIRMED
via Every Noise at Once (Glenn McDonald, Spotify's own genre-data lead; ~6,000
named genres, https://everynoise.com/). Honest correction recorded in the doc:
that figure is Every-Noise/Spotify-data, not a "Spotify publishes 6,000 genres"
page — Spotify's official API exposes the smaller browse-categories layer. This
strengthens the design (6,000 = analysis layer; 18 = choose-from layer). The
prior blog citation (spudart.org) is superseded.

## Wiring (landed in the same change)

- `web/lib/genres.ts` — the 18 (`GENRES`), the lossless `TODAY_8_TO_18` map, a
  synonym lexicon seed, and `canonicalGenre(raw)` (longest-keyword-wins
  normalizer; unknown → null = honest "Other" + growth signal, never a guess).
- `web/lib/feed.ts` — `genreFacet()` derives the Layer-0 rail from local
  inventory; `applyFilters({genreIds})` filters by canonical id (raw variants of
  one genre collapse — "Alternative Rock" and "Indie" both → indie-alternative).
- `/tonight` — a genre chip row (up to 12), a LENS never a gate; the R&B/Soul
  gap voice persona #7 exposed now resolves exactly.

## Retrieval tokens (for the brain)

- `genre-canon-18` — the ratified Layer-1 set; edits to the list are a founder
  decision, additions to Layer 2 / the lexicon are normal-gate config.
- `genre-normalizer-longest-match` — when mapping free-text labels to a
  controlled vocabulary by keyword containment, pick the LONGEST match, not the
  first (dancehall⊃dance, western swing⊃swing, alternative rock⊃rock). Regression
  cases live in `web/lib/genres.test.ts`.

## Trust posture (unchanged)

Genre is descriptive, from the act's/venue's own words; the canon is a
deterministic lens, never a ranking dimension and never inferred sentiment. The
no-hierarchy / no-pay-to-rank rules are untouched.
