# Decision: the ingestion engine must measure and learn, or it fails silently (2026-08-05, founder-directed)

**Founder, verbatim (session chat, escalating over ~40 minutes):**

> "This has been a version of your excuse for days and weeks now. I'm tired
> of it. Get the discovered events engine fixed and working NOW. No more
> delays or excuses. It is the #1 priority."

> "I want and expect to see every event. If you cant surface it it means you
> have coded poorly"

> "Explain what you have learned from this to ensure you do not make this
> kind of specific or category mistake again. Obivously we are dealign with
> data ingestion where the data may be all over the place. You must build
> the process and logic and code to be dynamic and flexible and smart enough
> and empowered and able to learn from it's own actions to search well on
> new sites, existing sites with no changes, existing sites with changes -
> announced or not, and other permutations that may arise based on you
> researching what world class senior engineering team do to make sure they
> build a world class product."

> "NO MORE EXCUSES THAT THE DATA IS BEING STOPPED AND NOT PUSHED ONTI THE
> LIVE PRODUCTION SITE."

> "for goodness sake there are all kinds of search engines out there with
> all kinds of criteria. figure this out. make it work. make it live. asap -
> not tonight, not tomorrow."

**The lesson, specific:** the R-021 datetime rule (refuse any claim without
a full in-text calendar date) was correct fail-closed policy, externally
reviewed 21 rounds — and it silently discarded the date of essentially every
venue-calendar event, because calendars carry the year in page context, not
event text. 1,363 published discovered events, zero upcoming. Every test
passed while 100% of the lane's user-visible value evaporated.

**The lesson, category (named as red class `silent-yield-collapse`):** a
fail-closed policy at a lossy pipeline boundary MUST ship with a yield
measurement and an alarm. The sentinel rule covered "the loop stopped
running"; nothing covered "the loop runs perfectly and produces nothing a
user can see." Reviews asked "does the code safely do what was intended" —
nobody was forced to ask "does the intended thing put events in front of
people." From here, the second question is mechanical, not cultural.

**Executed immediately (same session):** page-context date resolution in the
un-bound shaping layer (worker/datetime_resolve.py — deterministic stated
rule, refuses everything it cannot evidence, provenance-recorded), wired
into live extraction (ai_extract) AND a bounded backfill over the preserved
refused claims (worker/backfill_datetime_resolution.py + backfill-dates.yml,
master-only, dry-run first) — the claims were preserved verbatim by the
R-021 design, so the whole backlog resolves with zero re-crawl and zero AI
spend. Published dateless events inherit their candidate's resolved dates.

**Committed next (the founder's systemic directive, standing work):** the
ingestion engine gains a per-source, per-stage YIELD LEDGER
(fetched → extracted → dated → gate-ready → promoted → rendered-in-window)
with alarms on yield collapse exactly like downtime alarms ("no downtime"
extends to "no silent value loss"); source health states learned from run
history (new-source probation, unchanged-site short-circuit by content hash,
changed-site drift alarm on yield delta — announced or not); and a refusal
ledger surfacing the top refusal classes per week so the next R-021-shaped
loss is a report row within days, never a founder discovery weeks later.
This is the WS7 adaptive-cadence scope, widened by this directive from cost
into correctness; it is the next build after this fix is live.
