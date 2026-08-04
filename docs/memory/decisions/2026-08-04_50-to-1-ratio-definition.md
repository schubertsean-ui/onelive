# Decision: the 50:1 ratio, defined by the founder (2026-08-04)

**Founder, verbatim:**
> "The 50:1 is non-API ticketed events to API events on any given day weekend
> or weekly period."

(Issued while demanding the engine scope report and stating "I expect to see my
50:1 ratio exceeded.")

**The KPI.** For any given day, weekend, or week: published events discovered
by OUR pipeline (non-API — the long tail no licensed feed carries) should
outnumber licensed ticketing-API events by at least 50 to 1. This is the
product's breadth thesis made measurable: the licensed APIs are the floor
anyone can buy; the 50× on top is what 1LIVE exists to surface.

**Measurement (instrumented in `tools/db_scope_report.py::ratio_50_to_1`,
`db-report.yml`):** non-API = canonical `event` rows (extraction → gate →
promote); API = `licensed_event` rows. Windows in Austin market time
(America/Chicago): today, the containing-or-upcoming Fri→Sun weekend, and the
next 7 days. Each window reports api_events, non_api_events, the ratio, and
target_met against 50.0. The interpretation of "non-API ticketed" as
"pipeline-published canonical events" is stated in the code docstring so the
founder can correct it rather than have it silently assumed.

**Honest baseline at definition time:** the ratio is far BELOW target — the
pipeline lane publishes ~0 while extraction is closed (re-opens at PR #170's
merge) and the candidate backlog is only now starting to drain (auto-publish
flipped ON at #169, first pass pending the AUTOPROMOTE_PING_URL secret). The
levers, in order of impact: extraction re-open → autopromote drain → SeatGeek
approval → Eventbrite organizer list → catalog growth. The report makes the
gap visible per run; nobody gets to claim the ratio without the query.
