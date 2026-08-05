# Google Programmable Search — 100-queries/day budget (v1, 2026-08-05)

**What you're about to see:** how the one shared free search-API quota is
split between every lane that queries Google, so no lane can silently starve
another and no recurring schedule ships without a line here.

The Custom Search JSON API free tier is **100 queries/day per project**
(source: https://developers.google.com/custom-search/v1/overview, read
2026-08-05). Every consumer goes through a repo secret pair
(GOOGLE_CSE_KEY/GOOGLE_CSE_CX), so this file is the single budget ledger for
that key. Paid overage ($5/1000) is a MONEY decision: founder-crucial, not an
agent knob.

## Standing allocation (per UTC day)

| Lane | Consumer | Budget | Cadence | Notes |
| --- | --- | --- | --- | --- |
| Source scanner | `tools/scan_new_sources.py` (source-scan dispatch; PR #177) | 20 | manual now; proposed 3×/week after first curation round | category query pack → new-domain candidates for human curation |
| Eventbrite search discovery | `tools/search_discover_eventbrite.py` (provider-dryrun: eventbrite-search) | 10 | manual, on demand | organizer-page discovery; complements the harvest lane (which costs zero quota) |
| Festival adjacent-event sweeps | WS8 machinery (unbuilt — keyword-pack sweeps) | 30 | only inside an ACTIVE festival window | reserved; outside windows this tranche is idle headroom |
| Diagnostics | ops-diagnostics `cse-probe` | 2 | on demand | plain-query health probe |
| Unallocated headroom | — | 38 | — | absorbs retries and manual founder-requested searches; NOT a lane's to claim silently |

Rules:
1. **A new consumer or cadence gets a row here in the same PR that ships it** —
   the sentinel rule's quota twin. A `schedule:`d scan additionally carries a
   dead-man check from birth (workflow_env_lint R5 enforces the alarm; this
   file governs the budget).
2. **Every consumer is bounded by an explicit `--max-queries`/MAX_QUERIES
   fail-loud input** — no unbounded loops against the quota (already true for
   both existing tools).
3. **429/dailyLimitExceeded is a STOP for the day for that lane**, never a
   retry loop; the tools already fail loud on zero results.
4. Raising the total (paid tier) is founder-crucial (money): the trigger
   would be sustained >80% utilization across a week, measured from run
   logs, not guessed.
