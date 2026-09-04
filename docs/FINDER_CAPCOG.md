# Finder pass — CAPCOG TAM holes

Docs-only. Applies `docs/domain_recipes.md` query packs to the 25 hole rows
`docs/TAM_CAPCOG.csv` carried in from the prior session (PR #220) — every row
whose `clear_state` is `found_unverified` (16 rows) or `blocked_now` (9 rows).
That is Must-do 1's own cap ("all found_unverified + a sample of blocked_now,
not a 10k crawl"): both sets together are 25 rows, already finite, so the
"sample" of blocked_now is all 9 of them, not a subset. Output:
`docs/FINDER_CAPCOG.csv` (27 rows — one TAM_CAPCOG.csv row, the grouped
"St. Edward's/Concordia/Huston-Tillotson" hole, is 3 separate universities and
is reported as 3 finder rows so each school's own evidence is visible).

This is a finder pass, not a TAM-table edit: nothing here writes back into
`docs/TAM_CAPCOG.csv`. Rows this pass found strong evidence for are flagged as
upgrade candidates for a future TAM session, never silently promoted here.

## Method

1. Read `domain_recipes.md` for the finding's cultural domain and instantiated
   its query pack with the row's own specifics (city, gallery, school...).
2. Where a domain doesn't map to one of the 22 content-domain rows — every
   `civic`/`education` TAM `type` row (10 civic + 3 campus), because
   `domain_recipes.md` is built for the cultural domain of a *happening*, not
   the TAM `type` of an entity — this is exactly Must-do 4's "new unmatched
   shape" case. Recipe note, not a skip: two new patterns, tagged
   `other/raw (civic-general)` and `other/raw (campus-general)`, each using
   the generic `site:<domain> events calendar` finder pattern the entity's own
   `retry_paths` cell already implied. If a third civic/education-shaped pass
   recurs, that's the trigger to promote these to named recipe rows in
   `domain_recipes.md` itself, not before.
3. Ran the instantiated query through `WebSearch` and read the returned
   snippets/URLs — never treated a snippet as the listing itself (Must-not).
   `WebFetch` was tested once this session (`https://www.austinforum.org/`)
   and returned `EGRESS_BLOCKED`, the same sandboxed-outbound-fetch
   constraint the prior session hit — so **every row in this pass is
   `evidence_tier: search_only` at best**, never `fetched`. No paid Search
   API was called at any point (Must-not).
4. `hit_kind` was assigned against the ticket's own "Look-for" test: a page
   that *lists* upcoming activity (list/tour/exhibitions/talks/market/
   Home-"upcoming"), not merch and not an artist profile living on someone
   else's card.

## Table

Full 27-row table: `docs/FINDER_CAPCOG.csv` (name, domain, query_used,
hit_url, hit_kind, ingest_rec, clear_next, evidence_tier). Round-trips through
Python's `csv` module; every row carries a non-empty `hit_kind` and
`evidence_tier`; no row claims `official_list`/`publisher` without a citable
`hit_url` (mechanically checked at generation time — see
`clear_next`/Provenance below).

**Counts by hit_kind:**

| hit_kind | count | meaning here |
| --- | --- | --- |
| official_list | 21 | a first-party page that actually lists upcoming activity |
| marketplace | 3 | resolves through an already-catalogued platform (Meetup, Do512 x2), not its own domain |
| publisher | 1 | resolves through an already-trusted desk/tourism-board door, not a first-party page |
| junk | 1 | query dominated by SEO/ticket-reseller farms, no real door |
| unknown | 1 | nothing found for the actual ask |
| linktree | 0 | — |
| social | 0 | — |

**Counts by evidence_tier:** `search_only` 26, `none` 1, `fetched` 0 (egress
blocked all session — see Method).

## What actually moved

**9 blocked_now holes going in; 7 now have a real, citable candidate URL** (Buda,
Pflugerville-general, Llano, all 3 grouped schools, the author, the gallery) —
none promoted to `confirmed` here (that needs an actual fetch, per
ONE-LIVE-TRUST.md), but each is now a same-session upgrade candidate instead of
a bare hole. The 2 that didn't close (band, personality) didn't close for a
documented reason, not silence — see below.

- **Llano's own `retry_paths` guess was wrong.** Last session proposed
  `site:llanotx.us`; the real domain is `cityofllano.com`. Concrete evidence
  for Must-not's "never invent an official URL" — even a plausible-looking
  guessed domain can be the wrong one; this is why the rung is *search*, not
  *invent-and-fetch*.
- **Georgetown resolves through a tourism board, not a first-party `.gov`
  page.** `georgetown.org` is confirmed as the city's real domain (city
  department subdomains `pets.georgetown.org`/`purchasing.georgetown.org` are
  live), but no plain city-wide events path surfaced. `visit.georgetown.org`
  is a tourism-board calendar — ONE-LIVE-TRUST.md explicitly lists "tourism
  board" as a trusted civic door, so this is a legitimate publisher-cover
  resolution, not a downgrade.
- **The touring-band hole reconfirms, on a second example.** Last session
  tested 3 CAPCOG acts and found SEO ticket-reseller farms
  (`shakeygravestour2026.us`-shaped domains) dominating "own site" searches.
  This session's fresh example (Spoon) hit the identical shape
  (`spoontour2026.com`). Two sessions, same result: resolve touring-artist
  presenters through the already-catalogued aggregators (Bandsintown/
  Songkick/MusicBrainz), never an own-site search for this subtype.
- **The personality hole stayed open, honestly** — no independent standing
  show found, same as last session — but the query surfaced two real venues
  not in the catalog at all: **Comedy Mothership** (hosts Kill Tony) and
  **Moontower Comedy Festival** (grep-confirmed absent from `docs/` before
  this pass). Neither is added here — that's TAM-table work, out of this
  finder pass's scope — but both are worth a row next TAM session.
- **A conflation risk caught, not shipped.** The Lakeline Plaza Farmers
  Market query surfaced a *different*, better-established market — "Texas
  Farmers' Market at Lakeline" (`lakelinefarmersmarket.com`, 11200 Lakeline
  Mall Dr) — a different street address than Always Fun Markets' Lakeline
  Plaza site (11066 Pecan Park Blvd). These are two separate entities. The
  finder table keeps `docs/TAM_CAPCOG.csv`'s row resolving through the
  operator it already names (Always Fun Markets) and flags the second market
  as a new, uncatalogued entity for a future session — it is not substituted
  in as if it were the same place.

## Never invent an official URL / never scrape a login

No row in this pass upgrades a `clear_state` in `docs/TAM_CAPCOG.csv` — that
file is untouched. No login-walled page was fetched or proposed (St. Edward's
own interactive calendar requires an SEU login per its snippet; the public
Localist front door `cal.stedwards.edu` was used instead, not the gated view).
No social-only hit was treated as a listing this pass — the one aggregator hit
that is a hosted platform page rather than a first-party domain (Meetup, Do512
x2) is tagged `marketplace`, not `official_list`, per the Look-for test.

## Provenance

Generated by a one-time scratch script (not committed — same precedent as the
TAM/census generators), reading this session's `WebSearch` results captured
2026-09-04, and round-trip-validated (row count, non-empty required fields,
no `official_list`/`publisher` claim without a `hit_url`) before being
written. Domain-recipe source: `docs/domain_recipes.md`. Hole source:
`docs/TAM_CAPCOG.csv` rows 144-168 (this session touched no other row).
