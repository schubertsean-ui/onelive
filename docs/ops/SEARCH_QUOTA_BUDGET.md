# Brave Search API — launch-breadth budget (v4, 2026-08-05)

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

v3 implements the founder's launch-breadth directive, verbatim ("do what I
tell you - I want all the data in the initial launch to prove value and depth
and breadth" and "do this: all the data at launch: full CAPCOG sweep
immediately at launch (the depth-and-breadth proof), weekly full sweeps as
the standing cadence, automatic daily inside festival windows") — decision
record docs/memory/decisions/2026-08-05_launch-breadth-directive.md. That
directive IS the money authorization for the overage math below; a
materially different bill (>$40/month) returns to the founder first.

A full CAPCOG sweep = the canonical 22-domain query pack (44 phrases) × 22
region cities = **968 queries**, each returning up to 20 results.

## Standing allocation (per calendar month)

| Lane | Consumer | Budget/run | Cadence | Monthly cost math |
| --- | --- | --- | --- | --- |
| Source scanner — full CAPCOG sweep | `source-scan.yml` → `tools/scan_new_sources.py` | 968 | weekly (Mon 14:30 UTC cron) + the one-time launch dispatch | ~4,200/mo → free 2,000 + ~2,200 paid ≈ **$7/mo** |
| Festival LIVE-phase daily FULL sweeps | same workflow, daily cron gated by `tools/festival_phase.py` (live phase = starts..ends) | 968 | daily, ONLY in a live phase | ACL live phase (10 days) adds ~9,700 ≈ **+$29 that month** |
| Festival rampup/live/winddown KEYWORD sweeps | same workflow → `tools/scan_new_sources.py --festival <slug>` | ≤40 (a window's `keyword_pack` is ~6–7 queries) | daily, starts−28d..ends+1d | ~280/window-month — inside the free tier |
| Eventbrite search discovery | `tools/search_discover_eventbrite.py` (provider-dryrun: eventbrite-search) | 8 | manual, on demand (~4 runs/month) | 32 (in the free tier) |
| Diagnostics | ops-diagnostics `brave-probe` | 1 | on demand | ~10 (in the free tier) |

Ordinary month ≈ $7; a festival month ≈ $36–40 (October 2026 carries BOTH the
ACL and F1 live phases: ~12,600 full-sweep + ~4,200 weekly + ~600 keyword
queries ≈ 17,400 − 2,000 free ≈ $46 → **over the $40 tripwire, so October
specifically needs a founder word before its crons run both windows**; a
single-festival month stays ≈ $36). The phased definition itself
(docs/memory/decisions/2026-08-05_festival-window-phases.md) keeps the
expensive FULL band exactly the ratified starts..ends; the shoulders use the
near-free keyword lane. Rate limit (1 req/s, enforced in
tools/search_api.py) makes a full sweep take ~17 minutes of wall clock.

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
