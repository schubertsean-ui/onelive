# Special Situations: festival mode — design v1 (2026-08-05)

**What you're about to see:** the design for treating festivals (SXSW, ACL,
F1 weekend) as first-class *situations* — windows of time where the city's
event fabric changes shape — so 1LIVE captures the adjacent, unofficial
activity that has no other home. Founder-directed 2026-08-04 (verbatim in
`docs/memory/decisions/2026-08-04_special-situations-festival-mode.md`);
this doc turns that record into buildable pieces. Status: DESIGN — each
numbered piece lands as its own small PR through the normal gates.

## What already exists (verified in code)

- **Trust half:** `sxsw_mode` flows candidate → gate → confidence → publish
  policy: inside a festival window, non-first-party corroboration needs 3
  independent sources instead of 2. First-party anchors publish alone.
- **Sourcing half:** nothing festival-aware. Cadence is uniform; discovery
  queries know no festival vocabulary; short-lived sources have no expiry.

## The pieces (build order)

### 1. Festival windows as DATA (`sources/festival_windows.json`)
A reviewed, committed file — never scraped, never inferred:
```json
{"windows": [{
  "slug": "acl-2026", "name": "Austin City Limits 2026",
  "starts": "2026-10-02", "ends": "2026-10-11",
  "geo": "austin", "sxsw_mode": true,
  "keyword_pack": ["ACL", "Austin City Limits", "day party", "after party",
                    "unofficial showcase", "pop-up", "free show Zilker"]
}]}
```
A tiny resolver (`worker/festival_windows.py`) answers "which windows are
active on date D in market M". The existing `sxsw_mode` flag becomes
window-driven instead of hand-set — the 3-source rule arms and disarms
itself on the recorded dates. Tests pin boundary days (inclusive) and the
timezone (America/Chicago market days, same convention as db_scope_report).

### 2. Cadence surge (hooks into the adaptive-cadence build, WS7)
While a window is active, sources whose geo matches get the "hot" tier
floor regardless of their learned change-rate — festival weeks change
hourly. Fetch-layer only; caps/ceilings unchanged; the surge is bounded by
the same per-pass MAX_SOURCES the cron always enforces.

### 3. Adjacent-event discovery sweep (search lane)
`tools/scan_new_sources.py` (PR #177) gains a `--festival <slug>` mode: the
window's keyword pack becomes the query set (bounded by the festival tranche
in `docs/ops/SEARCH_QUOTA_BUDGET.md` — 30/day, window-active only). Results
are source CANDIDATES for human curation, exactly like every discovery lane.
Scheduled only during active windows; the schedule carries a dead-man check
from birth (workflow_env_lint R5 enforces it mechanically).

### 4. Pop-up source class with expiry
`source` rows gain `expires_on` (nullable). A pop-up's RSVP page or a
one-off Instagram enters the catalog with `expires_on = window.ends + 7d`;
the ingest loop skips expired sources and a weekly sweep disables them
(audit-logged, never deleted — provenance stays). No trust change: a pop-up
source is just a source; its class determines its gate weight as always.

### 5. Festival-week display note
During an active window, the feed carries one quiet line: *"Festival week —
things move fast; confirm with the venue."* (founder-directed 2026-08-05,
kickoff WS8; deliberately does NOT touch the likely-displays-clean ruling —
it is a seasonal context note, not a per-event trust marker). Copy enters
the UI canon; baselines recaptured as an intended diff.

### 6. Unofficial-vs-official provenance honesty
Adjacent events are never labeled as part of the festival. They carry the
provenance of whoever actually announced them (the venue/organizer), and
detail pages state that plainly. No new mechanism needed — this is a copy
and review rule; the gate already refuses fabricated affiliations because
affiliation claims need evidence rows like any other claim.

## What this deliberately does not do

No gate, threshold, or custody change anywhere — the mode is sourcing
breadth + cadence + honest display, judged by the same physics. Arguing any
gate down "because festival" is a gate-threshold relaxation: founder-crucial.

## Proving ground

ACL/F1 (fall 2026) is the rehearsal: pieces 1–4 must be merged and exercised
on a real fall event with measured adjacent-event yield (events discovered
via the sweep that no licensed feed carried). SXSW (March 2027) is the
category-defining run — "perfect it this first year, then roll it to
festivals anywhere in the world" (founder).
