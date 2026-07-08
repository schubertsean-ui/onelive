# Source Catalog — Coverage Gap

`master_sources_catalog_120.json` currently has real, populated entries for ranks 1-41 and 119-120 only (ticketing, venue_calendar, city_calendar, local_media, artist_aggregator, social, music_platform, link_hub, claimed_upload, email_opt_in, calendar_feed, community, directory, and search_benchmark categories, all Austin-focused).

**Ranks 42-118 are an explicit TODO gap** inherited from the reference build. Per the original spec note:

> "For a real production catalog you will expand ranks 42–118 with additional venue calendars (Austin + top target cities), ticketing platforms, local media, newsletters, and social APIs. The schema and policy rails above are the enforced contract."

When expanding, follow the same schema and priority-scoring model in `worker/source_rank.py`, and respect the `explicitly_disallowed` policy rails (no login/paywall/bot-protection bypass).
