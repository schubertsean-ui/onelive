# 1LIVE — Case study: The Continental Club, Austin (proof run, 2026-08-01)

**Status: DEMONSTRATION RECORD (research-grade). Founder directive: "Prove to
me the agent can do what we say it can do… crawl one and use the data you
gather to show screen shots of what the agent would spin up as if it were a
case study." The full visual edition lives in the Marketing Research & AI
Agent Model v1 deliverable (§10, artifacts 10a–10f; sources in
`marketing_model/`). This file is the durable record of what was done, what
was found, and what it does and does not prove.**

## Method (and its one caveat — R-063, renumbered from a duplicate R-025 id)

- **Read pass:** public data on The Continental Club (1315 S Congress Ave,
  Austin) gathered 2026-08-01 via search-index snapshots of its official site
  and listing surfaces — Bandsintown, Songkick, Do512, Eventbrite, Yelp,
  austintexas.org, heyaustin.com, Spotify. The build sandbox's network policy
  blocked direct page fetches; production reads the same surfaces directly.
  **R-063 (docs/RECORD.md): re-run as a direct crawl before any partner-facing
  use.**
- **Corroboration:** every fact cross-checked and assigned a state —
  CONFIRMED / LIKELY / UNVERIFIED — the gate's truth-state logic (six-state model per Truth States v2, 2026-08-01; this run observed CONFIRMED / LIKELY / UNVERIFIED).
- **Drafting:** preview card, engagement-canon campaign kit (video-first
  carousel + per-channel posts per design brief v2.4 §3/§6), machine-readable
  markup — from verified facts and the venue's public voice only.
- **Publishing: nothing.** No account touched, no post made, no correction
  filed. Every artifact is a draft; the send button belongs to the owner.
- **Honesty:** the venue is not affiliated and did not participate; all inputs
  are public; ticket prices were not verifiable and are therefore absent —
  the agent does not invent.

## What the run found (all real, as of 2026-08-01)

| Fact | Sources | State |
|---|---|---|
| The Continental Club — 1315 S Congress Ave · (512) 441-2444 · since 1955 | official site · Yelp · austintexas.org | CONFIRMED |
| The Continental Club Gallery — upstairs, 1313A S Congress | Yelp Gallery listing · official site | CONFIRMED |
| Hours: Mon 6pm–2am · Tue–Fri 4pm–2am · Sat 2pm–2am · Sun 2pm–12am | official site · Yelp — MATCH (no drift) | CONFIRMED |
| Voice/brand: "legendary" roots room — rockabilly, country, swing, blues "every night of the week" | official site copy · heyaustin.com | CONFIRMED |
| The Peterson Brothers — Texas blues/soul/funk — EVERY SATURDAY 8:00 pm residency (Aug 1, 8, 22, 29 all listed) | Bandsintown · Eventbrite · Do512 · Spotify | CONFIRMED |
| Peterson Brothers Sat Aug 29, 8:00–9:30 pm, ticketed (Eventbrite link captured) | Eventbrite · Bandsintown | CONFIRMED |
| Hellbilly Playboy — Tue Aug 4 | Bandsintown | LIKELY |
| Shannon McNally · Next of Kin · Buffalo Hunt — 9:30 pm, date not resolved | Do512 only — one source, no date | UNVERIFIED (held back; becomes one owner question) |
| **DRIFT CAUGHT:** Do512 labels the Aug 1 show "Friday" — Aug 1, 2026 is a SATURDAY; all other sources agree | Do512 vs Bandsintown/Eventbrite + calendar math | DRIFT (flagged) |

## The claim → evidence map

| We claim the agent… | Shown by |
|---|---|
| reads what's public and assembles the calendar without owner effort | extraction table above; preview card (10b) |
| verifies instead of trusting — nothing unverified publishes | 6 CONFIRMED · 1 LIKELY · 1 UNVERIFIED held back |
| catches drift across platforms | the real Do512 "Friday" mislabel |
| drafts the whole campaign on the ratified engagement canon, video-first with THEIR audio (IG Collab post; artist rule: nothing generated touches their art) | artifacts 10c/10d: carousel, reel/YouTube Short cut, FB event, GBP post, SMS/email, ad recipe |
| deploys the machine-readable + GEO layer | artifact 10e: event JSON-LD, NAP across Google/Yelp/Bing/Apple/Foursquare/Nextdoor, AI-crawler access, IndexNow, llms.txt hedge |
| needs minutes, not hours, from the owner | day-one thread (10f): two questions and taps |

## What this does NOT prove (named)

Live posting via connected accounts (Phase-C, behind platform review);
voice-learning from private libraries (public copy only was used); results
measurement (needs a live campaign). Build items, not extraction claims — the
data spine is what is demonstrated, and it ran on the first venue tried.
