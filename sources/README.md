# Source Catalog — Coverage Gap

`master_sources_catalog_120.json` currently has real, populated entries for ranks 1-59 and 119-120 (ticketing, venue_calendar, university_calendar, library_calendar, city_calendar, local_media, artist_aggregator, social, music_platform, link_hub, claimed_upload, email_opt_in, calendar_feed, community, directory, and search_benchmark categories, all Austin/CAPCOG-focused).

**Institutional non-music expansion (2026-07-24):** ranks 42-59 add real,
first-party, publicly-viewable structured event sources beyond live music —
universities (UT Austin Texas Performing Arts + the Localist master calendar,
Texas State Presents + main events, Austin Community College), Austin Public
Library, the City of Austin civic calendar, museums/visual arts (Blanton, The
Contemporary Austin, Mexic-Arte), theater/performing arts (ZACH, the Long
Center), film (Austin Film Society), literary (BookPeople), comedy (Cap City,
The Hideout, The Velveeta Room), and public-radio events (KUTX Presents). Every
one is the institution's OWN official events page/feed — no partner-gated APIs,
no login/paywall/bot-protection bypass (`explicitly_disallowed` rails preserved).
Structured-data method (ICS / Localist JSON / schema.org) is noted per entry via
`access_method`; where the exact structured-feed path was not confirmed the entry
points at the known first-party events page and is marked for verification. Two
additive honest fields carry the founder-requested detail: `cultural_domain` (the
OneLive domain hint — performing-arts, ideas, library, community, visual-arts,
theater, film, literary, comedy, live-music) and `county` (read by
`tools/real_source_probe.py`). Paramount/Stateside is already covered by rank 20
(austintheatre.org) and was not duplicated.

**Ranks 60-118 remain an explicit TODO gap** inherited from the reference build. Per the original spec note:

> "For a real production catalog you will expand ranks 42–118 with additional venue calendars (Austin + top target cities), ticketing platforms, local media, newsletters, and social APIs. The schema and policy rails above are the enforced contract."

When expanding, follow the same schema and priority-scoring model in `worker/source_rank.py`, and respect the `explicitly_disallowed` policy rails (no login/paywall/bot-protection bypass).
