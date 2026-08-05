# Brave Search API — 2,000-queries/month budget (v2, 2026-08-05)

**What you're about to see:** how the one shared search-API quota is split
between every lane that queries the licensed search index, so no lane can
silently starve another and no recurring schedule ships without a line here.

Provider: **Brave Search API** (founder-ratified switch 2026-08-05, verbatim
"Switch to Brave - do all the work" — decision record
docs/memory/decisions/2026-08-05_search-lane-brave-switch.md; Google's Custom
Search JSON API refuses this account at the account level, proven in
2026-08-05_founder-delegated-google-fix.md). Free plan: **2,000
queries/month at 1 request/second** (source:
https://brave.com/search/api/, read 2026-08-05). Every consumer goes through
the repo secret BRAVE_SEARCH_API_KEY via `tools/search_api.py`, which also
enforces the 1 rps throttle in code. Paid tiers (Base $3/1,000 queries) are a
MONEY decision: founder-crucial, not an agent knob.

v1 of this file budgeted Google's 100/day; superseded whole. Monthly math
below assumes 30-day months and states the worst case honestly.

## Standing allocation (per calendar month)

| Lane | Consumer | Budget/run | Cadence | Monthly worst case |
| --- | --- | --- | --- | --- |
| Source scanner | `tools/scan_new_sources.py` (provider-dryrun: source-scan) | 20 | manual now; proposed 3×/week after first curation round | 260 |
| Eventbrite search discovery | `tools/search_discover_eventbrite.py` (provider-dryrun: eventbrite-search) | 8 | manual, on demand (~4 runs/month) | 32 |
| Festival adjacent-event sweeps | WS8 machinery (unbuilt — keyword-pack sweeps) | 30 | daily, only inside an ACTIVE festival window | 930 (a full festival month) |
| Diagnostics | ops-diagnostics `brave-probe` | 1 | on demand | ~10 |
| Unallocated headroom | — | — | — | ≥768 even in a festival month |

Rules:
1. **A new consumer or cadence gets a row here in the same PR that ships
   it** — the sentinel rule's quota twin. A `schedule:`d scan additionally
   carries a dead-man check from birth (workflow_env_lint R5 enforces the
   alarm; this file governs the budget).
2. **Every consumer is bounded by an explicit `--max-queries`/MAX_QUERIES
   fail-loud input** — no unbounded loops against the quota (true for both
   tools; `tools/search_api.py` additionally throttles to 1 rps in code so
   no caller can burst).
3. **HTTP 429 is a STOP for the day for that lane**, never a retry loop; the
   tools already fail loud on zero results.
4. Raising the total (paid tier) is founder-crucial (money): the trigger
   would be sustained >80% utilization across a month, measured from the
   Brave dashboard / run logs, not guessed.
