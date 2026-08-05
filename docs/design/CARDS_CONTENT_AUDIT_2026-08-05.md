# Cards Content Audit — what the engine writes vs what /tonight shows

Date: 2026-08-05 (Session Contract #44). Founder directive (verbatim record
`docs/memory/decisions/2026-08-05_cards-reflect-updated-content.md`):

> "I want the UI/UX to reflect all the updated content on the cards now."

Method: enumerated every column the promote path writes onto the public
`event` row (`worker/promote.py` insert, migrations 0001/0010/0012), traced
each through the promoted reader (`web/lib/promoted.ts` EVENT_SELECT +
reshape) and every render surface (`FeedApp.tsx` RichCard / CondensedRow /
LineRow / Lens, `[id]` detail page via the shared `web/lib/detail.ts`
helpers), and judged each against the ratified canon
(ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4 trust display rules + UI canon card
anatomy). Licensed rows are the baseline; the audit is about DISCOVERED
(promoted) events, which the engine only began publishing at scale
2026-08-05 (autopromote runs 31022426849 / 31023273235: 700 promoted, 0
errors, post-#186).

## Field-by-field

| Field (promote writes) | Read path | Card | Lens | Detail | Verdict |
|---|---|---|---|---|---|
| `title` | ✓ selected | ✓ `headline()` (performer wins when short) | ✓ | ✓ | OK |
| `artist_ids` → performer names | ✓ resolved, batched | ✓ headline | ✓ | ✓ | OK post-#186 (named-artist events now publish) |
| `category` (cultural domain) | ✓ | ✓ focus line + domain grouping + hue + filters | ✓ | ✓ | OK |
| `subsegment` (genre) | ✓ | ✓ focus line + genre rail facet | ✓ | ✓ | OK |
| `start_time` / `end_time` | ✓ | ✓ `fmtWhen` + on-now computation | ✓ | ✓ | OK ("Date TBA" honest fallback) |
| `status` | ✓ | feed filters to scheduled/moved | ✓ `statusNote` | ✓ any-status (cancelled says so, never 404s) | OK |
| `confidence` | ✓ | ✓ TrustMark (quiet marker; disputed shown-never-hidden; confirmed clean per no-badge rule) | ✓ header both tabs | ✓ | OK |
| `ticket_url` | ✓ | — (card stays spare by canon §2) | ✓ "Get tickets ↗" terminal handoff | ✓ | OK (actionable where canon puts it) |
| `is_private_rsvp` / `private_access` | fenced: RLS 0007 + column grant 0012 exclude them | n/a | n/a | n/a | OK by design (privacy) |
| `notes` (title or raw_text[:120]) | NOT selected (not granted) | — | — | — | DELIBERATE GAP: raw crawl text on a calm card violates canon §1/§2 and the no-fabrication posture (it is unreviewed prose). Stays off-surface; descriptor Foundry is the sanctioned path to card prose. |
| price (`price_min/max/currency/is_free`) | ✓ selected | "See tickets" honest fallback | ✓ | ✓ | OK — promote writes NULL by design (crawl schema has no price; no fabrication). Data gap, not render gap. |
| `image_url` | ✓ selected | domain-hued labeled cover fallback | n/a | ✓ | OK — same: NULL by design until an honest image lane exists. |
| **source provenance** (candidate `source_name` + source `base_url`) | **✗ never carried to `event`** | **✗** | **"How we know" says only "a local venue or organizer listing"** | **same generic wording** | **TOP GAP — see below** |
| venue: name/city/area/address/lat/lng | ✓ PostgREST embed | ✓ name+area door | ✓ + maps link | ✓ | OK (placeholder venues carry name+city only — honest lens gap message) |
| venue contact (url/phone) | columns exist only on `licensed_event` (0014); `venue` has none | hardcoded null for promoted | honest gap message | same | DATA GAP: needs the venue/Places enrichment lane (already the recorded plan in promoted.ts). Not closable by render work. |

## The top gap: provenance dies at the promote boundary

The engine knows exactly where every discovered event came from —
`event_candidate.source_name` and the `source` row's `base_url` — and the
trust gate's whole verdict is built on that provenance. But `event` carries
no source column, so the public row cannot say it, and the "How we know"
sheet (canon: quiet marker → dismissible sheet **+ venue link**) falls back
to the generic "a local venue or organizer listing." For a product whose
entire differentiation is gate-custodied discovered events, the one thing a
card cannot currently show is *which real-world listing it was published
from* — the strongest honest trust signal we hold. This is the
`featurability-dimension-missed` red class (origin at every public emitter)
live on the main consumer surface.

**Close (first align PR, this session):** migration 0020 adds
`event.source_name` + `event.source_url`; `promote.py` writes them from the
candidate's own row + the unique-keyed `source` row (same shape as the 0010
`card_fields` precedent: promote writes public columns from the candidate's
own data, no fabrication); backfill existing promoted rows from
`event_candidate.promoted_event_id` in the migration; anon column grant per
the 0012 revoke-then-grant precedent; reader + "How we know" sheet name and
link the actual source, generic wording as the honest fallback when absent.

## Dispositions recorded

1. `notes` stays off-surface (deliberate, canon-grounded — see table).
2. Price/image stay NULL-honest until real lanes exist (no fabrication).
3. Venue contact for promoted venues waits on the enrichment lane.
4. Everything else the promote path writes is rendered, in the ratified
   language, on every surface (card, lens, detail, Ask/Plan rows all carry
   the TrustMark).
