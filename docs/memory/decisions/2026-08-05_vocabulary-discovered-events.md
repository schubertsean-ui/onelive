# Decision: vocabulary — "discovered events", never "long tail" (founder, 2026-08-05)

**Source and honest provenance:** relayed through the founder-commissioned
session kickoff (`docs/ops/SESSION_KICKOFF_2026-08-05.md`, conduct rule 5),
which records it as: *"Vocabulary: 'licensed events' vs 'DISCOVERED events'
(founder killed 'long tail', 2026-08-05)."* The founder's original sentence was
spoken in the 2026-08-04/05 overnight session and is not quoted verbatim here —
this record carries the kickoff's wording, not an invented quote
(red class founder-verbatim-corrected: a missing verbatim quote is stated,
never fabricated).

**The rule.** The two event populations are named **licensed events** (rows
from ticketing APIs anyone can license) and **discovered events** (events the
pipeline finds, extracts, gates, and publishes itself). The phrase "long tail"
is retired everywhere: founder-facing prose, PR text, code comments, docs.
The KPI is **50 discovered : 1 licensed** per day/weekend/week, computed by
`tools/db_scope_report.py::ratio_50_to_1` and registered as
`coverage-discovered-to-licensed-ratio` in `docs/metrics/kpi_registry.json`.

**Applied in the same change:** comment-level sweep of the living surfaces
that still carried the phrase (`tools/db_scope_report.py`,
`worker/source_catalog.py`, `worker/promote.py`, `web/app/(public)/tonight/`,
`web/lib/`). Historical records keep their original text, append-only.
