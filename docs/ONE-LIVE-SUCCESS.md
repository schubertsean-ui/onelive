# 1Live Success catalog

What Success looks like for each aspect of the platform.
The Monitor (M) uses this list. A miss is a failure. That miss starts step 1 of `docs/ONE-LIVE-FIX-LOOP.md`.

Universal. Any locale. Ticket bars are instances of these aspects.

Done for any aspect is observed on the live system that aspect owns — usually https://1live.co. GitHub green is not Success.

## Aspects and Success

| Aspect | Success looks like | Probe |
|---|---|---|
| Site | 1live.co and /tonight load | HTTP page shows the product, not an error |
| Catalog | A trusted readable door + title is a row | That happening can be found in the catalog |
| View | A view filter hides nothing that belongs in that window | Today / All upcoming / searched locale show the rows the catalog holds for that filter |
| Density | 100% of that locale’s counted aggregator union is on 1Live | Live unique N ≥ union U (title + when + place = one) |
| When | Start date is enough; start time only if printed; timezone is the locale pack | Date-only stays that locale day; no invented clock; no invented duration |
| Card | Printed fields came from a door; holes are holes | No invented title, place, time, or price |
| Ingest | The write job finishes and applies the current translator | desk-ingest conclusion success AND no missing-name crash |
| Deploy | Live is running master | Production SHA is master tip (or newer ingest on that tip) |
| Module | Product files are real modules | No `SEE_FILE`, no empty stub on desk_read / desk_publish / feed |
| Locale | A new city is a pack, not a rewrite | Timezone and desks come from the pack; device or search picks the locale |
| Trust | One trusted door is enough; disputed is shown | No second-desk hold; no hide for missing end or missing category |

## How M uses this

For each aspect: observe the probe. If the probe is not Success, that is a failure.
M writes: aspect, actual, Success from this table, then starts the 15-step process at step 1.
M does not patch.
