# 1LIVE Sourcing Model v1 — three layers, reuse-first

**Status:** RATIFIED-BY-DIRECTIVE (founder, 2026-08-03, verbatim: *"Your sourcing
model should be reusable and structured as a world class engineer would to be
able to reuse as much as possible while also planning for unique special
situations for local regional global items"*). Decision record:
`docs/memory/decisions/2026-08-03_sourcing-model-three-layer.md`.

**One sentence:** write every ingestion mechanism ONCE at the protocol level,
define every locality as DATA, and declare every deviation as a named special —
so that scale (Austin → Texas → national → global) is adding files, never
forking pipeline code.

---

## The three layers

### Layer 1 — Pathways (GLOBAL reuse: the protocol, not the place)

The unit of reuse is the **pathway kind** — the machine protocol a source
speaks, never the city it serves. Established by the founder's 2026-07-31
directive and mechanically classified for all catalog sources by
`tools/source_pathways.py` (run `--assert` in CI-facing checks; no source may
be unclassified):

| Kind | Adapter | Reuse span |
|---|---|---|
| `licensed_api` | `worker/importers/ticketmaster.py`, `seatgeek.py`, `eventbrite.py` | national/global per provider |
| `ics_feed` / `jsonld_embedded` / `structured_feed` | `worker/importers/structured_feed.py` | global (open standards) |
| `calendar_platform` (Localist, The Events Calendar, …) | `structured_feed.py` (Localist path) | every customer of the platform, any market |
| `gov_open_data` (Socrata/CKAN/ArcGIS) | `worker/importers/socrata.py` | every jurisdiction on the platform |
| `ai_extract_triangulated` | the AI loop (`worker/run_once.py --real` → orchestrator → gate) | any public HTML calendar, any language the model reads |
| `partner_agreement` / `social` / `manual_upload` | per-agreement / per-platform-app / self-serve | as negotiated |

**Rule:** a new source NEVER gets a new importer unless it speaks a genuinely
new protocol. A new protocol earns a new adapter kind in `source_pathways.py`
in the same PR that lands its adapter — the classifier and the code move
together or not at all.

### Layer 2 — Markets (LOCAL as data, never code)

A **market** is a JSON file in `sources/markets/<id>.json`, loaded by the
fail-closed registry `worker/sourcing/markets.py` (`get_market()`; selection:
arg → `$ONELIVE_MARKET` → `austin`). It carries:

- **boundary** — a REFERENCE (module + symbol) to the geographic predicate,
  never a mirrored county list (mechanical identity: the set in
  `worker/region/capcog.py` stays the single source of truth). New boundary
  kinds (polygon, postal-set for non-US) land WITH their resolver — the
  registry refuses a kind nothing can resolve.
- **timezone + locales** — the operational clock and the language(s) the
  pathway adapters and extraction read in. (Global note: `ai_extract` is
  language-capable; ICS/JSON-LD are language-neutral; `licensed_api` coverage
  varies by country — the market file is where that is declared per market.)
- **catalog** — the market's source list (Austin: `sources/master_sources_catalog_120.json`,
  180 sources). Seeding the `source` table goes through
  `tools/import_sources.py --market <id>` so the market file is the routing
  authority, not a hand-typed path.
- **specials** — see Layer 3.

**Scale path:** Austin is market #1. San Antonio, Dallas, or Berlin = a new
market file + a seeded catalog + (only if the country needs one) a new
boundary resolver kind. Zero importer changes; zero gate changes; the trust
invariants are market-independent by construction.

### Layer 3 — Specials (declared deviations, never silent forks)

Unique local/regional/global situations are **declared** in the market file's
`specials` array — id, kind, description, the implementing code path, and an
honest status (`built` / `accepted` / `planned`) — and **implemented** in the
named code. The registry documents and locates them; it never executes them.

Austin's current specials: SXSW chaos-mode corroboration (3-source rule,
`worker/gating.py`), the Hill Country boundary extension (founder-directed
2026-07-29), and the UTC/DST cron-shift acceptance. Future examples the model
is shaped for: a festival-city takeover week (any market), country-specific
legal posture (GDPR-region source handling), right-to-left locales, markets
where the dominant ticketing API is not Ticketmaster.

**Rule:** a special that exists in code but not in a market file's `specials`
is a defect (silent fork); one declared `planned` with no impl is visible debt,
tracked like any Record entry.

---

## Why this shape (alternatives considered)

- **Per-city importer forks** (the common startup path): fastest first city,
  N× maintenance by city ten, and drift between forks becomes silent behavior
  divergence. Rejected.
- **One mega-config for everything** (sources + markets + specials in one
  file): couples unrelated change rates (a source edit shouldn't touch market
  definitions) and makes per-market review impossible. Rejected.
- **Three layers keyed by change rate** — protocol code changes rarely
  (engineer-owned), market data changes per expansion (ops-owned), specials
  change per local reality (declared, reviewed): chosen. The tradeoff is one
  more indirection (a market file to read before you know a boundary), paid
  once, at the registry.

## Trust invariants (unchanged, stated for the record)

The sourcing model routes ACQUISITION only. Every candidate, from every
pathway, in every market, passes the same gate → promote path; no market or
special may relax a threshold (gate-threshold changes stay founder-crucial).
The boundary reference is fail-closed: an unresolvable or empty boundary
refuses to load rather than defaulting to "everywhere."

## Current honest status

- Layer 1: built for `licensed_api` (TM live; SeatGeek/Eventbrite need keys),
  `ics_feed`/`jsonld_embedded`/`calendar_platform` (built; thin proven yield),
  `ai_extract_triangulated` (loop runs; publish path pending the promote
  engine); `gov_open_data` built-needs-config; `partner_agreement`/`social`/
  `manual_upload` not built.
- Layer 2: registry built (this PR); Austin is the only market file.
- Layer 3: Austin's three specials declared; SXSW + boundary are `built`.
