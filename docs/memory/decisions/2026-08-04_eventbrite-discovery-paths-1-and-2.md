# Decision: Eventbrite organizer discovery — founder picks paths 1+2 (2026-08-04)

**Context.** Eventbrite's edge 405-blocks page fetches from datacenter IPs even
with protocol-correct headers (verified, PR #172 run 30942079518). The agent
ruled UA-spoofing and residential proxies OUT (circumvention/deception — ToS and
legal exposure, and contrary to the honest-crawler identity we publish). The
founder rejected "automated discovery is dead" and demanded options.

**Founder, verbatim:**
> "No I don't accept that. Provide options to solve this?"
and, on the five options presented:
> "Focus on 1 and 2"

**The chosen paths (both automated, both honest — eventbrite.com is never
fetched by us):**
1. **Harvest from our own catalog pages** (`tools/harvest_eventbrite_links.py` +
   `eventbrite-harvest` workflow mode): read the pages of sources already in the
   ratified catalog — only entries whose own `allowed` list grants a public_*
   access method, and structurally never eventbrite.com itself — and collect the
   `/o/<id>` organizer and `/e/<id>` event links THOSE pages publish. Event ids
   are then resolved to organizers through Eventbrite's DOCUMENTED API with the
   founder-minted token (`tools/resolve_eventbrite_event_orgs.py`,
   GET /v3/events/{id}/?expand=organizer).
2. **Search-API discovery** (`tools/search_discover_eventbrite.py` +
   `eventbrite-search` workflow mode): Google Programmable Search JSON API
   (`site:eventbrite.com/o "austin"`), free tier 100 queries/day; organizer ids
   read off result URLs. Needs founder-created GOOGLE_CSE_KEY + GOOGLE_CSE_CX
   secrets; fail-closed until they exist.

Both lanes output CANDIDATES to artifacts for human review; the committed
curated list then drives the R-029 dry-run before any DB write — the custody
chain is unchanged. Fail-loud contracts on both (zero-fetch/zero-result exits
are red, pipefail set per the 2026-08-04 pipe-masked-exit Kaizen rule).

**Standing options 3-5** (founder can invoke anytime): a browser bookmarklet
copy-helper, pasted organizer URLs, and a permission email to Eventbrite.

**Tradeoff, stated.** Path 1's coverage is bounded by our catalog (a venue not
in the catalog can't donate its links); path 2 is bounded by Google's index and
the free quota. Neither weakness is hidden — counts are printed per run.
