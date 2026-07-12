# Source Catalog

## Canonical: `austin_metro_catalog.json` (193 verified sources)

The production source catalog for the 5-county Austin metro (Travis, Williamson,
Hays, Bastrop, Caldwell). Every entry has: `name`, `base_url`, `category`,
`county`, `sub_region`, `coverage_categories`, `note`.

### Provenance & verification discipline (trust-critical)

Every URL in this catalog was surfaced through live web research and then
**liveness-verified**, not invented:

1. Two research passes gathered candidate sources per county × category from
   official city/county calendars, chambers, universities, real venues,
   festivals, local media, and cultural orgs.
2. All 196 candidates were swept with an HTTP liveness check.
3. Every non-200 was re-verified in a real browser. That pass:
   - **corrected 8 URLs** whose domain was live but whose events path had moved
     (e.g. Stubb's → `/concert-calendar/`, City of Austin → `/events`, Thinkery
     → `my.thinkeryaustin.org/events`, Radio East → Radio Coffee & Beer);
   - **dropped 3 dead sources** (Empire Control Room — parked domain; Skylark
     Lounge — disconnected Wix site; LeanderWins — persistent WordPress fault).
4. All 8 corrected URLs were re-checked live (200).

Result: 196 candidates → **193 verified sources**. A hallucinated or wrong URL
is a runtime trust defect, so reality was checked, never assumed.

### Coverage

Coverage is a queryable property (migration 0010: `county`, `sub_region`,
`coverage_categories`). Run the report any time:

```bash
python tools/coverage_report.py --json sources/austin_metro_catalog.json   # hermetic
python tools/coverage_report.py                                            # live DB (ONELIVE_DB_DSN)
```

The report renders a county × category grid and surfaces **coverage debt**
explicitly — empty cells, uncategorized sources, out-of-domain county values.
Known debt in the current catalog (surfaced, not hidden): the `university`
culture-tag is unpopulated (university sources are typed by `source_type`, not
the culture category), and comedy/dance/film are thin in the rural counties.

### Import

```bash
python tools/import_sources.py --json sources/austin_metro_catalog.json
```

Idempotent upsert on `name` (migration 0009 unique constraint); refreshes
mutable + geo columns on conflict, so re-importing an updated catalog is a true
upsert, not a silent no-op. `coverage_categories` is type-checked; a bad
`county` value fails loud at the DB CHECK constraint (migration 0010).

## Legacy: `master_sources_catalog_43_LEGACY.json`

The original inherited catalog — 43 entries, all with `null` county and no
`coverage_categories` (the "coverage theater" the new catalog replaced). Kept
for provenance only; **do not import**. Running the coverage report against it
shows 72/72 empty cells — the gap made numeric.
