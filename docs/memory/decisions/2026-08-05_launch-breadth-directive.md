# Decision: launch with all the data — full CAPCOG breadth, founder-directed (2026-08-05)

**Founder, verbatim (session chat, in order):**

> "5 results and '20 query' - these seems tiny in terms of what's available
> in the capcog area"

> "this is the wrong number - it's at least 23 '20 category searches' -
> where are you getting all this?"

> "do what I tell you _ I want all the data in the initial launch to prove
> value and depth and breadth" (quoting, as the accepted budget: "weekly
> sweeps would run ~1,400/month, still free. If we ever want more, Brave's
> paid tier is $3 per 1,000 queries")

> "do this: all the data at launch: full CAPCOG sweep immediately at launch
> (the depth-and-breadth proof), weekly full sweeps as the standing cadence,
> automatic daily inside festival windows."

**What the founder caught.** The scanner's v1 query pack was an ad-hoc list
of 20 phrases (tools/scan_new_sources.py, written under Google's old 100/day
quota) covering ONE city and missing whole canonical domains — film, sports,
family, wellness, heritage, fashion-design, seasonal, ideas had zero queries.
The canonical taxonomy is the 22 cultural domains in
worker/importers/domain_map.DOMAINS.

**The build (rides in PR #187 with the Brave switch):**
- Query pack DERIVED from the canonical 22 domains, two plain phrases each
  (44 phrases), with a sentinel test pinning pack-keys == DOMAINS so a new
  canonical domain fails the suite until the scanner covers it.
- CAPCOG region sweep: 22 cities (Travis/Williamson/Hays/Bastrop/Caldwell/
  Burnet/Blanco/Llano county towns), cities × phrases = 968 queries/sweep.
- `.github/workflows/source-scan.yml`: workflow_dispatch (the launch sweep),
  weekly cron (standing cadence, dead-man check onelive-source-scan, 7d
  period — sentinel rule honored from birth), and a daily cron that runs
  ONLY inside an active window in `sources/festival_windows.json` (committed
  now with ACL 2026 + F1 2026 — festival-mode piece 1 landing early);
  outside a window the daily firing prints why it is not owed and exits
  green, honest never silent.

**Money, stated.** Ordinary month ≈ $7, festival month ≈ $36 (ledger:
docs/ops/SEARCH_QUOTA_BUDGET.md v3). The founder's verbatim directive above
is the authorization; anything materially beyond that envelope (>$40/month)
returns to the founder before it is spent.
