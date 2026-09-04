# Domain recipes — CAPCOG

Companion to `docs/TAM_CAPCOG.md`. One row per OneLive cultural domain: where to
look first (seed desks/registries), what to search when CAPCOG is thin (query
pack, write-only — proposed text, no paid search API, nothing executed against a
login), and the honest current hole. Counts below are a dated snapshot via:

```
python3 -c "
import json, collections
data = json.load(open('sources/master_sources_catalog_120.json'))
dom = collections.Counter(e.get('cultural_domain') for e in data)
for k,v in sorted(dom.items(), key=lambda x: (-x[1], str(x[0]))): print(v, k)
"
```
run against `sources/master_sources_catalog_120.json` on 2026-09-04 — a fact about
that fixed moment, re-run the command for a current count rather than trusting the
number below as live.

## The grid is a seed, not a cap

The 22 domains below (`sources/README.md`'s own list) are a **starting grid**, not
an allowlist. A happening that doesn't fit any of them still lists — tagged
`other/raw`, never refused, never held back for want of a category (Coverage Law:
no dropped row, no category weighting). If the **same** unmatched shape shows up
more than once, that recurrence is the trigger to add a NEW recipe row here, not a
reason to keep forcing it into the nearest existing domain or to keep refusing it
silently. `other/raw` is row 23 below, on purpose, not an afterthought.

**Category is per happening, not per place.** A venue that programs more than one
domain (a brewery running both live-music nights and a trivia/comedy night; a
library running both literary talks and family story-time) gets tagged per EVENT,
never pinned to one domain for the whole entity. Nothing in this table or in
`docs/TAM_CAPCOG.md`'s `type` column overrides that — `type` says what KIND of
entity something is (venue/presenter/group/...); cultural domain is a property of
the individual happening it presents.

## The five intakes

Must-do 4's six-rung clear-the-door ladder (`docs/TAM_CAPCOG.md`) is the ORDER you
try things in. The founder's five-intake framing is the CHANNELS themselves —
every rung above resolves through one of these five, and the mapping is worth
stating once so the two documents never drift apart:

| # | intake | maps to ladder rung | notes |
| --- | --- | --- | --- |
| 1 | registries | rung 1, public list | the entity's own page, or a structured registry (NFMD, a state agency list) |
| 2 | desks/marketplaces | rung 3, publisher cover | an already-trusted desk or aggregator already names it — see `docs/TAM_CAPCOG.md` Table 2 |
| 3 | finder queries | rung 2 | **write only** — this session proposes search text, it never calls a paid search API and never treats a snippet as the listing itself |
| 4 | Harbor/claim | rung 4 (+ rung 5 as its activation) | our own existing shared inbox / `/ops/claim` flow — not a new service, see `docs/TAM_CAPCOG.md`, "What Harbor means" |
| 5 | own-on-1Live (future) | not yet a ladder rung | **not built.** The forward-looking path where a presenter/venue manages its own listing directly on 1Live, beyond upload/claim. Named here so the model has room for it later; no code, schema, or service is implied or started by naming it (Must-not: no new service this session) |

Every row below cites intakes 1–3 only, because 4 and 5 are entity-specific
actions (taken per hole in `docs/TAM_CAPCOG.md`), not domain-wide recipes.

## Recipes

| domain | catalog count (2026-09-04) | seed desks/registries | query pack (write-only) | CAPCOG hole |
| --- | --- | --- | --- | --- |
| live-music | 22 | Do512, Bandsintown, Songkick, KUTX Presents, Austin Chronicle (all catalogued) | `"<CAPCOG city>" live music venue calendar` | Nearly all 22 rows are Travis County; Williamson/Hays/Bastrop/Burnet/Caldwell venues are unmapped for this domain specifically |
| performing-arts | 7 | Texas Performing Arts (UT), Long Center, ZACH Theatre, Austin Symphony/Opera/Ballet (catalogued) | `"Georgetown Palace Theatre" schedule`, `"<Hill Country town>" performing arts center calendar` | Nothing confirmed outside Austin proper |
| theater | 1 | Austin Chronicle theater listings (catalogued desk, covers this editorially); local companies not yet catalogued | `Austin community theater company season calendar`, `"Georgetown Palace Theatre"` | Real thin spot — most theater companies route through the desk, not their own catalogued page |
| comedy | 3 | Cap City Comedy Club, The Hideout Theatre, The Velveeta Room (catalogued) | `"<CAPCOG city>" comedy open mic` | Zero outside Austin proper |
| visual-arts | 5 | Blanton, The Contemporary Austin, Mexic-Arte, UMLAUF, Elisabet Ney Museum (catalogued) | `"<gallery name>" exhibition calendar`, `Austin second Saturday gallery walk` | Commercial galleries almost entirely unmapped — one lead this session (Wally Workman Gallery), `found_unverified`, see `docs/TAM_CAPCOG.md` |
| film | 1 | Austin Film Society / AFS Cinema (catalogued) | `"Alamo Drafthouse" Austin locations calendar`, `"Austin Film Festival" schedule` | Alamo Drafthouse (Austin-founded chain) is not in the catalog at all — the most visible single gap in this domain |
| literary | 1 | BookPeople (catalogued); Austin Public Library and Texas Book Festival are catalogued under other domains but cover literary programming too | see `docs/TAM_CAPCOG.md` Presenters/author holes and proposed queries | Individual author presenter pages are the gap, not desk coverage — desks already absorb most of this |
| ideas | 3 | This session's Hot Science Cool Talks + Austin Forum on Technology & Society slot here once confirmed (`found_unverified`, see Table 1) | `"Texas Tribune Festival" schedule` (name only — not fetched, not added as a row) | Public-lecture/ideas programming outside UT is thin |
| festivals | 1 | SXSW (catalogued) | n/a this session | Likely NOT a real hole: single-focus festivals correctly domain-tag under their OWN domain (a food festival tags food-drink, not festivals) — this domain is structurally reserved for multi-industry mega-festivals, so a low count may be correct rather than missing. Flagged as a judgment call, not asserted either way |
| food-drink | 67 | The Hill Country wine-trail expansion; this session's Guest Chef Series, Pflugerville Pfarmers Market, Always Fun Markets | `"<remaining CAPCOG city>" farmers market schedule` | Wineries/breweries are saturated; farmers markets and food halls are the actual remaining gap here, not restaurants |
| nightlife | 3 | Elysium, Kingdom Nightclub, The Concourse Project (catalogued) | `"<CAPCOG city>" nightclub calendar` | Zero outside Austin proper |
| dance | 2 | Ballet Austin, Tapestry Dance Company (catalogued) | `Austin contra dance schedule`, `Austin salsa social calendar` | Social/partner dance nights (not companies) are entirely unmapped |
| community | 8 | Meetup (catalogued); this session's "New To Austin Community" group | see `docs/TAM_CAPCOG.md` group holes and proposed queries | Civic/hobbyist clubs (Rotary, historical societies, running clubs) mostly resolve only through Meetup today |
| heritage | 5 | Bullock Museum, LBJ Library, Austin History Center Association, Carver Museum, AARC (catalogued) | `"<CAPCOG county>" historical museum events` | Nothing outside Travis County confirmed |
| family | 2 | Thinkery, Austin Nature & Science Center (catalogued) | `"<CAPCOG city>" children's museum OR family activity calendar` | Nothing outside Travis County confirmed |
| place-based | 3 | Republic Square, Waterloo Greenway, Mueller Austin (catalogued) | `"<CAPCOG city>" downtown district events calendar` | All 3 are Austin-only districts |
| sports | 4 | Round Rock Express, Austin FC, COTA, Austin Spurs (catalogued) | `"Southwestern University" athletics schedule`, `"Texas State" Bobcats athletics schedule` | College/high-school athletics and rec leagues unmapped |
| library | 1 | Austin Public Library Events (catalogued) | `"<CAPCOG city>" public library events calendar` | **Best near-term win in this table** — every other CAPCOG city's library system is a plain civic (usually class A/B) door and none is catalogued yet |
| fairs-expos | 3 | Rodeo Austin, Maker Faire Austin (catalogued) | `"<CAPCOG county>" county fair schedule` | County fairs outside Travis unconfirmed |
| seasonal | 2 | Austin Trail of Lights, Eeyore's Birthday Party (catalogued) | `"Marble Falls" "Walkway of Lights" schedule` (named lead from this session's search, `found_unverified`, no URL captured — not added as a Table 1 row yet) | Holiday/seasonal programming outside Austin is a named lead, not yet a row |
| wellness | 2 | Austin Yoga Festival, HAAM (catalogued) | `"<CAPCOG city>" yoga studio public class schedule` | Studio-level recurring classes are a long tail, entirely unmapped |
| fashion-design | 1 | Austin Fashion Week (catalogued, hosted on Sched.com) | `Austin maker craft design market schedule` | Everything except the one flagship week is unmapped |
| **other/raw** | **n/a — always open** | none fixed by design | none fixed — a query pack is written only once a shape repeats | This row never closes. Two shapes seen this session that don't fit cleanly anywhere above: a maker/hackerspace collective (ATX Hackerspace) and a multi-site market *operator* (Always Fun Markets) — neither recurred enough this session to justify a new named domain; noted here so the NEXT one of either shape is the trigger, not a surprise |

## Provenance

Domain list: `sources/README.md`'s "22 OneLive cultural categories" enumeration,
quoted verbatim, not re-derived. Counts: the command at the top of this file,
against `sources/master_sources_catalog_120.json`, run 2026-09-04 — 33 additional
catalog rows (mostly ranks 1–41, predating the `cultural_domain` field per
`sources/README.md`) carry no domain tag at all; backfilling them is TODOS.md's
existing R-047, not repeated here. Seed desks/registries name only entities
already in `docs/CENSUS_CAPCOG.md`/`docs/TAM_CAPCOG.md` — nothing new is asserted
in this file that isn't already a row in one of those two.
