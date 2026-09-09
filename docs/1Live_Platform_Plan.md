# 1Live Platform Plan v4

PM guiding document. Lives on master. Read `docs/AI_INSTRUCTIONS.md` first.

Done is not a PR. Done is a person opening https://1live.co and seeing the activity.

## Vision

ONE-LIVE-VISION.md. Do not shrink it.
1Live accurately publishes every activity anywhere in the world.

## Goals

1. Answer tonight in under 2 seconds.
2. Every real activity findable. Discovery never for sale.
3. Time given back.
4. Listed by default if it is on.
5. Places appear from activity, not payment.
6. Social validates, never defines.
7. No sponsored discovery.
8. Heartbeat is city pulse, not a person.

## Alignment

Hourly. Independent of tickets. M reads Vision + Goals. Miss → 15-step process. M does not patch.

## Tickets (run continuously)

Each ticket has a bar. The 15-step process is how a miss is closed. Valid Source Library + FIND_AGGREGATORS apply to all of them.
CAPCOG is the test view filter only. Not the map.

**A — Populate.** A validated door + title becomes a catalog row. Date and place are holes, not holds. One door is enough.
Bar: ingest of a validated door writes rows (`GET /events` moves).

**B — Density (next).** 100% of that locale’s counted aggregator union is on 1live.co. Deduped title + when + place.
Bar: Today on 1live.co ≥ that locale’s union (test floor: Chronicle today).
This is the ingest → showing gap.

**C — Card.** Print title / when / place / kind / via + the other slots when a door printed them. Holes allowed. Nothing invented.

**D — Place is a query.** Locale = device or searched city. CAPCOG is an opt-in test filter.

**E — Gather.** Demand starts a hunt. FIND_AGGREGATORS 15 steps. A hit is a lead.

**F — Pack holes.** Every pack door that is a public list has catalog rows, or an honest ingest miss in the Fix Process.

**G — All locales, all kinds.** New city = new pack + hunt. Roles, not Austin brand names.

## Standing

- No stub desk_read / desk_publish / feed. No merge #273.
- No invented clock or duration.
- Aggregator names are not 1Live fields.
- After a catalog change: ingest → open 1live.co → count.
