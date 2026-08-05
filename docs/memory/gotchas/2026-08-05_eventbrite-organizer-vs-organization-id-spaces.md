# Gotcha: Eventbrite "organizer" ids and "organization" ids are DIFFERENT id spaces

**Date:** 2026-08-05 · **Source:** the 2026-08-04/05 overnight Eventbrite lane
(dry-run 404s), carried into the kickoff as a required memory write.

**What happened.** Public `eventbrite.com/o/<slug>-<id>` pages carry ORGANIZER
ids. The API's `/organizations/{id}/events` endpoint serves ORGANIZATION ids —
and only for organizations the calling token belongs to. Feeding harvested
organizer ids to the organization endpoint 404s every time; there is no
public-search fallback (removed 2020). The two id spaces look identical
(numeric strings) and nothing in the API error says "wrong id space".

**The rule.** For third parties the ONLY workable id space is EVENT ids
(`GET /events/{id}` serves any public event). The lane is therefore: harvest
event ids from our own catalog pages → founder review → provenance registry
(`sources/eventbrite_provenance.json`) → `--kind event` import, allow-listed
against that registry (PR #182-era trust boundary on PR #178). Organizer ids
remain useful only as CANDIDATE metadata for humans, never as API queries.

**Retrieval tokens:** `eventbrite-id-spaces`, `organizer-vs-organization`.
