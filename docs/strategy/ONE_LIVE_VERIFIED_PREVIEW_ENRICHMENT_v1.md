# 1LIVE — Verified Preview & Enrichment (Option B) — Spec v1

**Status:** PROPOSAL — **founder-crucial** (new services · spend · legal posture). The founder
directed "I'd like B" (the verified/specific media beyond Option A search links) and sharpened
it: *"May we need #3 expanded to help fill-in local #1?"* — **yes**. This spec designs a single
**local-first enrichment cascade** that serves the contextual preview (#1), the venue block
(#3), and later the Spark Line (#2). It requires founder decisions (§7) before build.

**The principle (founder, 2026-07-31):** the preview must be **dynamic, contextually accurate
(the *real* entity's *real* media, never a same-name mismatch or fabrication), and
curiosity-inducing.** Option A (shipped, PR #131) is honest *search* links per type. Option B
attaches the **verified specific** media — and the honest way to do that, differentiated and
legally clean, is **local-first**.

**Why local-first (the moat, confirmed by research):** the big platforms (YouTube/Spotify/TMDB)
have almost nothing for a neighborhood lecture, a local band, or a venue's recurring night —
the long tail 1Live exists to cover. The differentiated data lives on the entity's **own**
pages (which the pipeline already fetches via `venue_url`) and in authoritative open cross-link
graphs. Big-platform APIs are a **targeted top-up**, never the foundation. Two of them also
moved *against* this use in 2024–26 (see §5).

---

## §1 · The cascade (precedence — stop at first confident hit, else an honest gap)

For each entity (artist / venue / event), walk down; attach media only above a confidence bar;
below it show **nothing** (an honest gap beats a wrong preview — charter trust invariant):

1. **First-party structured data** — on pages we already fetch: schema.org/JSON-LD
   (`Event`/`MusicGroup`/`Person`/`VideoObject`/`sameAs`), oEmbed, and **embeds the site itself
   hosts** (a YouTube/Spotify iframe the venue chose to put on its own page — the venue vouched
   for it). FREE, lowest legal risk, best local coverage.
2. **Authoritative entity→own-source resolution** — resolve name → official channels via
   schema.org `sameAs`, **Wikidata** (typed external-ID properties: official site P856, YouTube
   channel, Spotify ID), **MusicBrainz** (musicians: MBID + official-homepage/streaming links).
   FREE, no key. This is how we get the *real* entity, not a same-name guess.
3. **Free platform EMBEDS from the resolved official source** — the **YouTube IFrame player**
   (embeds any embeddable video by id; free; creator opted in) and the **Spotify Embed/oEmbed
   player** (free, public URLs, no auth). Rendered from the channel/URL resolved in step 2.
4. **First-party `og:image`** — from the entity's **own domain only**, hotlinked (render *their*
   asset from *their* server), attributed, takedown-honored. FREE; the fallback preview image.
5. **Paid top-up (capped): Google Places** — venue photos + details (address/phone/hours/type)
   *only where the first-party site is thin*. PAID → founder spend cap first (§5, §7).
6. **Honest gap** — "no preview available" is a valid, correct outcome.

Layers 1–4 are **FREE and lowest-legal-risk** *and* cover the local long-tail the paid APIs
miss — which is exactly why they lead.

---

## §2 · What each event type gets (Option B)

Same cascade, resolved per type; falls back down the ladder, honest gap at the bottom:

| Type | Verified preview (best-case, local-first) |
|---|---|
| **Music** | The artist's Spotify/YouTube **embed** resolved via `sameAs`/MusicBrainz; else a track the *venue's own page* embeds; else Option-A search. |
| **Lecture / ideas / literary** | The speaker's **actual talk** from their resolved official channel (or a talk the host org's page embeds); else search. |
| **Comedy** | A set/clip from the comedian's resolved official channel; else search. |
| **Film** | The **official trailer** from the studio/distributor's official YouTube channel (via `sameAs`) — deliberately **avoiding TMDB's licensing** (§5); else search. |
| **Theater / performing-arts / dance** | A clip the company's own site embeds, or its resolved official channel; else search. |
| **Visual arts** | The artist/museum's own images (first-party `og:image`/JSON-LD `image`); else a web-search link. |
| **Venue block (#3)** | First-party venue photo (og:image/JSON-LD) → **Google Places photo** (paid, capped) when the site is thin; plus factual character from the **gov `venue_truth`** we already hold (capacity, type, license) — FREE, no API. |

**"Past-year event photos"** (the recurring-event case): use **only** first-party (the venue/
organizer's own site) or licensed/Places imagery. **Never** reproduce a press outlet's photo —
**link** to the write-up instead (§6).

---

## §3 · Provenance & the gate (contextual accuracy, mechanically)

"Contextually accurate" is enforced, not hoped for. A media attachment is a **publish-path
decision** and rides the same discipline as event data (AI never publishes an unvalidated guess):

- **Resolve by authoritative ID, never by free-text search alone.** `sameAs` → Wikidata →
  MusicBrainz beats any search hit. Search is the last resort, and only above threshold.
- **Disambiguate with side signals we already hold** — city/area, entity type (band vs.
  speaker), event date, co-billed names — matched against the candidate before accepting.
- **Confidence + honest gap.** Every attachment carries a **provenance record** (how the entity
  was resolved · which authoritative link · confidence). Below threshold → **no media**, or →
  the existing **admin-review** step for a human call. Never auto-attach a low-confidence guess.
- **The media confidence rides the 4-state model** conceptually: a verified official-channel
  match is high-confidence; a name-only match is low and stays gated. Same "shown honestly,
  never fabricated" invariant as the feed.

This means a wrong preview is **auditable and reversible**, and the enrichment cannot become a
back-door around the gate.

---

## §4 · Data & pipeline shape (build sketch)

- **New storage:** `entity_media` (per artist/venue/event: kind [video|track|image|embed],
  provider, url/embed_id, `provenance` jsonb {resolved_via, authoritative_link, confidence},
  first_seen) + resolved-identity columns (`sameas_urls`, `wikidata_id`, `musicbrainz_id`,
  `youtube_channel_id`, `spotify_url`). Store Google **`place_id`** (cacheable) but **never**
  cache Places photo references (they expire — fetch on demand, §5).
- **New worker stages:** (a) a first-party **structured-data extractor** over pages we already
  fetch (JSON-LD/oEmbed/og/site-embeds); (b) an **identity resolver** (sameAs→Wikidata→
  MusicBrainz); (c) an optional **platform-lookup** stage (YouTube Data API metered; Places
  paid) that runs only when 1–2 miss and confidence is high.
- **UI:** the lens/detail render an **embed** when we have one (YouTube/Spotify iframe), an
  **image** with attribution when we have one, else the Option-A search link, else nothing —
  one component, cascade-driven. No card clutter: preview stays behind the artist door.
- **Discipline:** cache hard (YouTube `search.list` is 100 quota units — prefer resolved
  channel-id + 1-unit `videos.list`); field-mask Places to the cheapest tier; attribution
  rendered for Spotify, Places, and og:image sources.

---

## §5 · The services (current, researched Aug 2026) — free vs. paid vs. avoid

| Service | Role | Cost / key | Notes |
|---|---|---|---|
| **First-party pages** | Layers 1 & 4 | **FREE** (already fetched) | Lowest risk; the differentiator. |
| **Wikidata / MusicBrainz** | Layer 2 resolver | **FREE, no key** | Open data; the provenance backbone. |
| **YouTube IFrame embed** | Layer 3 render | **FREE, no key** | Permitted when uploader allows embedding. |
| **YouTube Data API v3** | Layer 3 lookup | **FREE key** (Google Cloud), hard **10k units/day** | `search.list`=100 units → cache; raising quota is free but slow (audit). No billing needed. |
| **Spotify Embed / oEmbed** | Layer 3 music | **FREE, no auth** | Must attribute + link back to Spotify. |
| **Google Places (Details+Photos)** | Layer 5 venue | **PAID — needs billing + spend cap** | 2025: no more $200 credit; per-SKU free tiers (Details 10k Essentials/5k Pro/1k Enterprise; Photos separate). Details $5/$17/$20 per 1k by field tier; **Photos $7/1k**. Can't cache photo refs; store only `place_id`; attribution required. |
| **Spotify Web API** | — | **AVOID** | `preview_url` deprecated 2024; top-tracks removed Feb 2026; extended access org-only (≥250k MAU). Not viable — use the Embed player instead. |
| **TMDB** | film metadata | **HOLD — legal** | Free key, but ToS has a **commercial-use** restriction *and* an **AI/ML** prohibition, + 6-mo cache cap. Founder-crucial legal read. Prefer the studio's **official YouTube trailer** and skip TMDB. |
| **Apple Music (MusicKit)** | music | **SKIP v1** | $99/yr + ES256 JWT signing; redundant with Spotify/YouTube embeds. |

---

## §6 · Legal & trust guardrails (hard rules)

1. **Never reproduce a press/third-party photo.** Case-law trend narrows fair use; "it went
   viral" / a caption is not a defense. For write-ups: **link**, don't lift.
2. **First-party og:image only from the entity's own domain**, hotlinked + attributed +
   takedown-honored (og:image is not a blanket license).
3. **Places:** store only `place_id`; **fetch photos on demand** (refs expire); render
   `authorAttributions`; stay in the cheapest field tier; EEA terms if billing is EEA.
4. **Spotify embeds:** attribute with Spotify marks + link back.
5. **YouTube:** official IFrame player only; never scrape stream URLs (ToS/legal).
6. **No pay-to-rank leakage:** media is display only; it never influences ordering (a venue/
   label can't buy a richer preview to rank higher). Same wall as tastemaker posts.
7. **Provenance-gated:** no media attached without the §3 provenance record + confidence bar.

---

## §7 · What the founder must decide (the consolidated ask)

Nothing here is minted by the agent (charter: agents never mint keys; spend caps set *first*).
To unlock Option B, in priority order:

1. **Approve the local-first build (FREE, no keys).** Layers 1–2 + Spotify oEmbed + YouTube
   IFrame embed + og:image — I can build all of this with **no new service and no spend**. This
   is the differentiated core and covers the local long-tail. *→ Just say go.*
2. **Create ONE free key: YouTube Data API v3** (Google Cloud project → enable API → API key;
   no billing). Unlocks the metered video-lookup path for talks/comedy/trailers.
   👉 https://console.cloud.google.com/apis/library/youtube.googleapis.com
3. **Decide on Google Places (the only paid piece).** If yes: create a Places API key with a
   **billing account + a hard monthly spend cap and daily quota set FIRST**, scoped to venue
   photos/details where first-party is thin. Tell me the cap and I'll field-mask to stay under
   it. 👉 https://console.cloud.google.com/apis/library/places-backend.googleapis.com
   (Skip = we rely on first-party venue imagery + the gov `venue_truth` facts we already have.)
4. **TMDB — legal call.** Recommend **skip** (commercial + AI clauses); I'll source film
   trailers from studios' official YouTube channels instead. Only pursue TMDB if you want a
   lawyer to clear those clauses.
5. **Apple Music — confirm skip for v1.**

**My recommendation:** approve #1 now (free, biggest differentiation, zero risk); create the
free YouTube key (#2); **hold Places (#3)** until we see how far first-party venue imagery +
gov facts get us (avoid spend we may not need); **skip TMDB and Apple Music.** That gets Option
B's local-first core live with essentially no cost, and leaves the one paid decision for when
the data proves it's needed.

---

## §8 · Build sequence

1. **Phase B1 (free, no keys):** `entity_media` + identity columns · first-party structured-data
   extractor · sameAs/Wikidata/MusicBrainz resolver · provenance record + confidence gate · lens
   renders resolved YouTube/Spotify **embeds** + first-party og:image + Option-A fallback.
2. **Phase B2 (free key):** wire YouTube Data API metered lookup (cache-hard) for the entities
   step 1 can't resolve to an embed.
3. **Phase B3 (paid, capped — only if approved):** Google Places venue photos/details behind the
   spend cap, on-demand fetch, attributed.
4. Each phase: provenance-gated, honest-gap on low confidence, no pay-to-rank, measured (the
   analytics canon's depth/coverage metrics track how often each layer resolves).

---

## Appendix · Method sources (research 2026-08-01)
YouTube Data API quota + IFrame embed ToS; Spotify Web-API deprecations (preview_url 2024,
top-tracks Feb 2026, extended-access org-only) + Embed/oEmbed player; TMDB ToS (commercial + AI
clauses); Google Places 2025 pricing change (per-SKU free tiers, Details $5/$17/$20 per 1k,
Photos $7/1k, no-cache-photo-refs, attribution); og:image licensing risk; schema.org `sameAs` /
Wikidata / MusicBrainz for authoritative entity resolution; copyright trend limiting reuse of
press photos. Grounds on 1Live assets already held: `venue_url` (fetched pages), gov
`venue_truth` (#122), the authority cascade (`worker/authority.py`, #123), and the 4-state
confidence model (`worker/confidence.py`).
