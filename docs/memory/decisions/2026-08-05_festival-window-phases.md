# 2026-08-05 — "Inside an active festival window" is a phased definition

## Founder directive (verbatim, 2026-08-05)

> define this. festivals usually start promoting lineups and activities
> months and weeks in advance - they firm up as the event gets closer and
> even days before and day of updates, new things, cancellations, etc.. so
> we need to capture the right amount of content for the appropriate amount
> of time "inside an active festival window"

Asked against the ratified cadence directive of the same day ("do this: all
the data at launch: full CAPCOG sweep immediately at launch (the
depth-and-breadth proof), weekly full sweeps as the standing cadence,
automatic daily inside festival windows" — decision record
2026-08-05_launch-breadth-directive.md), which left "inside" undefined.

## The definition (implemented, boundaries tunable as data)

Phases are computed from each committed window's dates by
`tools/festival_phase.py` — never scraped, never inferred:

| Phase | Band | Discovery behavior | Why |
| --- | --- | --- | --- |
| announce | months out, until rampup | standing WEEKLY full sweep (already running) | early promo pages surface in search within a week of existing; no daily machinery needed, zero extra cost |
| rampup | starts−28d .. starts−1d | DAILY festival-keyword sweep (the window's `keyword_pack` × its geo, ~7 queries/day) | lineups and side-events firm up week by week; targeted terms catch them the day they appear |
| live | starts .. ends | DAILY FULL sweep (the ratified band) + keyword sweep | day-of pop-ups announce with festival terms ("ACL after party") that the domain pack never queries |
| winddown | ends+1d | one more keyword sweep | day-after additions, cancellations, recap pages naming pop-ups we missed |

Per-window overrides `rampup_days` / `winddown_days` live in
`sources/festival_windows.json`. Updates/cancellations for events ALREADY
ingested are the re-ingest cron's job (catalog sources re-fetch every
cycle); this definition governs only the discovery scanner.

## Cost honesty (charter: no choice presented as free)

The daily-FULL band stays exactly the founder-ratified starts..ends — the
shoulders get the near-free keyword lane, not full sweeps. October 2026
(ACL 10d + F1 3d live-full days + weekly cadence + keyword shoulders)
lands ≈ $36–40/month, at the edge of the standing >$40/month
return-to-founder tripwire. Extending FULL sweeps into the shoulders
(starts−3..ends+1) would add ≈ $12 per festival and cross the tripwire —
available on a founder word, not taken silently.

## Alternatives considered

- Full sweeps daily across the whole rampup: ~$87+ per festival month,
  rejected on cost — keyword sweeps capture the same firming-up content
  because festival side-events name the festival.
- A single undifferentiated starts..ends band (status quo): rejected —
  misses exactly the weeks-ahead firming and day-after churn the founder
  named.
