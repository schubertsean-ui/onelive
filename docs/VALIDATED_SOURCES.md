# Validated sources

This is the Valid Source Library. It is not a second ontology.
The rows live in `sources/master_sources_catalog_120.json` plus each locale pack’s doors.

## Rule (non-violable)

- A **validated** door promotes on **one** statement. Title + that door is enough.
- A **second** door is required only when the first statement is unofficial, invalidated, or hearsay (one social post, an SEO scrape, a wall we did not enter, a desk already marked wrong).
- Publishers stay trusted until evidence marks them wrong. Demote that row. Do not raise the bar for everyone.

## What “validated” means

A row in the source catalog with `validated: true` (or class already trusted: official venue/artist/presenter, established local desk, civic calendar, licensed ticketing/marketplace, organizer claim).

Examples of the class (not a closed brand list, not code):
established local desk · venue calendar · ticketing · artist/presenter · civic · meetup-class community calendar.

Austin Chronicle, Do512, Ticketmaster, Bandsintown, Meetup are instances of those classes. A new city uses the same classes. New brands are new catalog rows.

## Do not

- Build a separate Valid Source database.
- Re-validate Chronicle every ingest.
- Ask two validated desks to agree before the row exists.
