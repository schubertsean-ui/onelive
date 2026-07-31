# ONE LIVE — Ingestion Engine (v1)

**Status:** PROPOSAL, founder-directed 2026-07-31. Records the founder's
corrections to how ingestion is framed and sets the build order. The engine — not
Austin — is the product: *"I want it as differentiated, e.g. people can't
understand how we are able to get the information."*

Companion artifacts (kept in lockstep with this doc):
- `tools/source_pathways.py` — assigns **every** catalog source a reusable pathway
  kind + honest status; run it to refresh the matrix.
- `docs/strategy/SOURCE_PATHWAY_MATRIX.md` — the generated per-source matrix.

---

## 1. The corrected publish principle (founder, 2026-07-31)

The charter line *"AI never publishes"* was being read too narrowly by the agent,
and the founder corrected it verbatim:

> "The point was AI never publishes **directly** UNLESS IT'S GONE THROUGH THE
> VALIDATION PROCESS AND THAT'S WHY WE CREATED CONFIDENCE SCORING BASED ON OUR
> ABILITY TO TRIANGULATE an AI find against other potential sources such as the
> web pages of other aggregators … their calendars, or comments, or feeds, or
> social media … Work the process!!"

So the invariant is **AI never publishes DIRECTLY** — it publishes **through**
validation. Publishing is the *output* of the triangulation/confidence process,
not a manual switch a human flips per event. This is fully consistent with the
existing four-state model (`unverified | likely | confirmed | disputed`) and with
`worker/publish_policy.py` (earned-confidence). What was missing was not a
decision — it was the **engine that earns the confidence**. That engine is the
build. The hard trust rules are unchanged and still physics: `disputed` is shown,
never hidden; no pay-to-rank surface, ever; RLS stays fail-closed; the promote
path stays gate-custodied.

## 2. Pathways are reusable KINDS, not cities

A source's ingestion pathway is defined by the **machine protocol it speaks**, not
by the market it serves. One adapter per kind, reusable across every US market:

| Kind | What it reads | Reusable because |
|---|---|---|
| `licensed_api` | Ticketing/data APIs (Ticketmaster, SeatGeek, Eventbrite, Meetup) | Same API nationwide |
| `ics_feed` | An iCalendar feed the site publishes/advertises | RFC 5545 is universal |
| `jsonld_embedded` | schema.org/Event JSON-LD in the page | schema.org is universal |
| `calendar_platform` | A hosted calendar PLATFORM's JSON API (Localist, The Events Calendar, Squarespace) | Every customer of that platform, any city |
| `gov_open_data` | Government OPEN-DATA portals — Socrata (SODA), CKAN, ArcGIS | Every US jurisdiction on those platforms |
| `structured_feed` | A generic RSS/Atom/JSON feed the source offers | Standard formats |
| `ai_extract_triangulated` | Plain HTML calendars — AI extract, published via triangulation | Any page, any market |
| `partner_agreement` / `social` / `manual_upload` | Partner exports, OAuth social, self-serve upload | Same integration everywhere |

Naming note (founder 2026-07-31): "Localist" is a **third-party vendor platform**
(localist.com) that universities and cities pay to run their calendars — not a
name we invented. The `calendar_platform` kind is the adapter for *any* site on
that platform, which is why it is inherently multi-market. Where our own names
described a vendor instead of a function, they are renamed to the function.

## 3. The differentiator: government / administrative data

The catalog today has **zero** government open-data sources (only MusicBrainz
carries an `open_data` token, and that is an artist directory). The founder's
directive:

> "you should be accessing the local and state administrative agencies who have
> all kinds of licensing and other data including fire, emergency, rescue and
> police and health departments, for data like capacity, type of services, etc."

The `gov_open_data` pathway reads authoritative **venue-truth**: fire-marshal
**occupancy/capacity**, health-department **permits and service type**, TABC and
other **licensing**, business registration. Most US cities and states expose this
as machine-readable JSON via **Socrata (SODA API)**, **CKAN**, or **ArcGIS** — no
key for public datasets, deterministic, no AI. This data:
1. is a first-class **triangulation anchor** (an event at a venue the fire marshal
   lists at capacity 400, licensed for live music, is far more corroborated);
2. powers venue facts users can't get elsewhere (capacity, service type), which is
   a visible differentiator; and
3. binds to the opaque venue identity from `ONE_LIVE_GEO_IDENTITY_v1.md`.

It is primarily venue enrichment + corroboration, **not** an event list — stated
plainly so it is never mistaken for feed volume.

## 4. The triangulation / confidence engine (the moat)

For the 131 `ai_extract_triangulated` sources (the bulk), the flow is:

```
AI extracts a candidate from a public calendar page
        │
        ▼
Triangulate against INDEPENDENT corroboration for the same event:
   • other aggregators' calendars / feeds / JSON-LD
   • the venue's own social posts, comments, feeds
   • gov_open_data venue-truth (does this venue exist, licensed, at this capacity?)
   • licensed_api / structured_feed rows for the same show
        │
        ▼
Confidence rises with each independent agreement:
   unverified → likely → confirmed          (agreement)
   any credible contradiction → disputed    (shown as disputed, never hidden)
        │
        ▼
`confirmed` == validated → publishes (worker/publish_policy.py earned-confidence).
AI never publishes DIRECTLY; it publishes THROUGH this process.
```

This is what makes the sourcing hard to reverse-engineer: no single feed explains
the coverage, because corroboration is assembled across many independent kinds.

## 5. Build order (each item ends in a proven run, not a claim)

1. **Prove the `ics_feed` discovery** already shipped (PR #115) on the live
   `import-structured` run; report per-source yield by name.
2. **`calendar_platform` adapter** (Localist JSON API) — lights up university /
   city / library calendars deterministically, no key. Reusable for every Localist
   market.
3. **`gov_open_data` adapter** (Socrata SODA first) — venue capacity / licensing /
   service type as a triangulation anchor and a visible differentiator.
4. **Triangulation / confidence engine** — turn the 131 `ai_extract_triangulated`
   sources from candidates into validated, published events by corroboration.
   This is the moat and the largest build.
5. Only after a kind proves LIVE does its matrix status flip from `ADAPTER_BUILT`
   to `LIVE`. "It works" is always a run, never a sentence.

## 6. What each status means for "does it work"

`LIVE` (1 today: Ticketmaster) = a real run produced events. `ADAPTER_BUILT` (149)
= the code exists but live yield for that source is not yet proven — the honest
majority. `CODE_READY_NEEDS_KEY` (2) = blocked only on a credential (Eventbrite;
SeatGeek, whose API application is **not yet approved** — do not count it as
imminent). `NEEDS_BUILD` (19) and `NEEDS_AGREEMENT` (9) name the remaining work
plainly. The gap between 149 built and 1 live IS the triangulation engine plus the
per-kind proving runs above — that gap is the work, stated without gloss.
