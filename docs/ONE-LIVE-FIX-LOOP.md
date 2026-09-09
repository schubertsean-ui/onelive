# 1Live Fix Loop (non-violable)

Binding on Ticket B and every future ticket. Ceremony is off. Three seats. Not five.

Done is not a PR. Done is a person opening https://1live.co and seeing the activity.

## Bar (Ticket B)

Right: 100% of the counted union of local aggregators is on 1Live.
Wrong: anything less.

Same title + when + place = one happening.
A green GitHub job is not 100%.

## Seats

### 1. Definer
Writes one prescription:
- expected count (the union)
- actual count on 1live.co
- what is missing or hidden
- which file or step hides it
- done = this number on https://1live.co

Definer does not write the patch.

### 2. Fixer
Implements only that prescription.
Does not open a second ticket.
Does not stub desk_read.py or desk_publish.py.
Does not invent a clock or a duration.

### 3. Publisher
Three checks, in order:
1. The change is on **master** (not a stub, not SEE_FILE).
2. desk-ingest write=true doors=all if the hole is in the catalog.
3. Open https://1live.co and count.

If the live count did not move toward 100% of the union, the fix failed.
Stop. Return to Definer. Do not start a second theory.

## Rules that do not yield

- Definer is not Fixer.
- Master is not live.
- Live is the only pass.
- One prescription, one change, one count.
- Ticket B owns the union bar. No other ticket may declare B done.
