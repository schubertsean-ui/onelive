# Session kickoff — 2026-08-05 — FINISH THE PROJECT

Founder directive (verbatim): "create a prompt to get that going with what will
actually complete the project as a world class senior engineer - nothing
remaining outstanding is allowed to be skipped or held or otherwise not listed."

Standing conduct rules for this session, non-negotiable:
1. Run `python tools/session_reconcile.py` first; verify every claim below
   against disk/API before acting on it.
2. NEVER give the founder click-path instructions through a third-party UI you
   cannot see. Delegation-token or API first; if a human step is unavoidable,
   ask for a screenshot FIRST and direct from what is actually on screen.
3. While any exam-bound PR is open, FREEZE all other merges to master.
4. Merges are silent (evaluator APPROVE + all green on final head). Every
   founder directive → verbatim decision record, same commit.
5. Vocabulary: "licensed events" vs "DISCOVERED events" (founder killed
   "long tail", 2026-08-05). The KPI is 50 discovered : 1 licensed per
   day/weekend/week (instrumented in tools/db_scope_report.py).
6. The founder is exhausted by redo-loops. Batch founder asks into ONE list,
   only when truly blocked, with exact values to paste.

DELEGATIONS LIVE (founder, 2026-08-05 — repo Actions secrets; usable ONLY via
workflows on master, the sandbox cannot read them): VERCEL_TOKEN (env vars,
redeploys — includes deleting the stray AUTH_DISABLED var), HEALTHCHECKS_API_KEY
(create/tune alarm checks programmatically — no more founder copy-trick),
CLERK_SECRET_KEY_ADMIN (Backend API: GET /v1/domains for certificate status —
Workstream 5's verification path). Founder ALSO sent the Clerk support email.
Build a small dispatch-only ops-diagnostics workflow early: it unlocks all
three delegations (Clerk cert status, Vercel env cleanup, healthchecks CRUD).

State at handoff (verify, don't trust): extraction ON (master 9f844ac);
auto-publish live hourly at :15 (AUTOPROMOTE_PING_URL set); ingest cron every
20 min; 4 healthchecks live + 3 more created by founder for #175's workflows;
GOOGLE_CSE_KEY/CX secrets set (first call 400'd — diagnose); events@1live.co
exists (alias→contact@→personal Gmail); Clerk SSL for accounts.1live.co stuck
>8h (founder emailing Clerk support); SeatGeek awaiting their approval email.

---

## Workstream 1 — Land the three open PRs (#176, #177, #178)
WHAT: Drive to evaluator-green and merge, in this order: #178 (Eventbrite
event-id lane), #176 (ingest cap 30), #177 (source scanner v1). Also open the
missing PR for the already-pushed branch `claude/records-festival-mode`
(festival-mode decision record) and merge it.
HOW: Standard drive-to-green: fix findings, reconcile STATE staleness on each
merge (marker + rollup), merge silently, keep the merge queue serialized so
branches stop invalidating each other.
WHY IT MATTERS: #178 is the only working Eventbrite ingestion path; #176 is
the founder's freshness order ("make sure this isn't too restrictive"); #177
is the founder's scanner ("Saxon Pub is an institution" — catalog at ~6% of
the ~4,200-source universe).
WHY THAT MATTERS: these three are the breadth engine — without them the 50:1
numerator (discovered events) cannot grow beyond the current 268 sources.
EXPECTED OUTCOMES: three merges + festival record merged; no branch left
unPRed; master green.

## Workstream 2 — Prove the live engine end-to-end (first-night verification)
WHAT: (a) verify the first scheduled ingest runs green with extraction ON and
the `onelive-ingestion` healthcheck flips up; (b) verify gates stamp the 4,202
candidate backlog and autopromote's hourly pass shows examined>0, promoted>0;
(c) verify discovered events render on 1live.co; (d) verify the ~08:00 UTC
licensed import passes its NEW dead-man assertion (founder-created check —
if the assert fails on period mismatch, fix the check config via API or the
workflow's EXPECTED_PERIOD, never by weakening the assert); (e) run
db-report.yml and deliver the founder a before/after 50:1 table.
HOW: Actions run logs + healthchecks status + the public feed + the scope
report artifact. If any stage stalls (e.g. candidates lack evidence rows →
autopromote examined=0 persists), diagnose the stage that stamps
`ready_to_promote` and fix forward.
WHY IT MATTERS: the founder ordered "everything ingesting and feeding and
showing on the live site" — merged code is not that; only the running loop is.
WHY THAT MATTERS: trust with the founder is repaired by visible results on
1live.co, not by PR counts; this workstream is the receipt.
EXPECTED OUTCOMES: a message to the founder with: ingest run link (green),
autopromote counts, N discovered events live on the site, 50:1 per window,
all alarms quiet/green.

## Workstream 3 — Search/discovery lane live (Google CSE)
WHAT: (a) fix the search-lane 400 — DIAGNOSED 2026-08-05 01:20Z: Google returns
{"status":"INVALID_ARGUMENT","reason":"badRequest"} with the key accepted,
which nearly always means the CX value is malformed. First test a plain query
(no site: operator) via a branch dispatch; if still INVALID_ARGUMENT, the
GOOGLE_CSE_CX secret needs re-entry (one founder paste — the engine id shown
in the PSE embed code, e.g. 707d7bec86b814566, no spaces/newline); (b) after #177
merges, dispatch source-scan (20 queries) and hand the founder the curated
new-domain candidate list; (c) plan the 100-queries/day free quota across
scanner + eventbrite-search + future festival sweeps before ANY recurring
schedule ships (a scheduled scan is a new loop → sentinel rule applies).
HOW: provider-dryrun dispatches; artifacts; then a catalog-additions PR from
curated candidates (human/founder approves names, agent commits with
provenance).
WHY IT MATTERS: the scanner is how the catalog grows without founder effort —
new venues/artists/groups appear continuously.
WHY THAT MATTERS: catalog breadth is the ONLY lever that scales discovered
events to 50:1 and to new markets.
EXPECTED OUTCOMES: search lane returns real results; first scan candidates
delivered; quota budget written down; recurring cadence proposed with alarm.

## Workstream 4 — Eventbrite lane to completion
WHAT: after #178 merges: (a) dispatch eventbrite-events dry-run with the 23
harvested event ids (founder approved all 13 organizers, verbatim "all good");
(b) verify normalize + geo coverage in the summary; (c) commit the curated
organizer/event provenance file (sources/ record of the 13 names + ids +
found_on); (d) wire a scheduled event-id import (extend import_licensed.yml or
a sibling) fed by a recurring eventbrite-harvest — BOTH new schedules carry
dead-man checks from birth (use HEALTHCHECKS_API_KEY if the founder delegated
it; otherwise one consolidated founder ask).
HOW: dispatch → read artifact → small PRs; the harvest already runs on demand
(mode exists on master).
WHY IT MATTERS: Eventbrite carries the community/venue events Ticketmaster
never sees — museums, breweries, bookstores (the harvest found exactly those).
WHY THAT MATTERS: those are discovered-event sources in licensed-quality form:
they raise breadth WITHOUT extraction spend.
EXPECTED OUTCOMES: Eventbrite events in licensed_event on a schedule, alarmed,
visible on the site; provenance file committed.

## Workstream 5 — /ops door (Clerk SSL) to done
WHAT: founder emails Clerk support (drafted, in chat 2026-08-05). When Clerk
reports issued (or if the founder delegates CLERK_SECRET_KEY_ADMIN as a repo
secret): verify via Clerk Backend API GET /v1/domains that certificates are
issued, then walk the founder through ONE sign-in at 1live.co/ops (their
email is allowlisted), and confirm the escalations queue renders.
HOW: Clerk Backend API from a runner or local curl-through-proxy if reachable;
founder screenshot as fallback.
WHY IT MATTERS: /ops is the human half of custody — the escalations queue
(conflicts, below-threshold sources) has no other reviewer surface.
WHY THAT MATTERS: with auto-publish live, unreviewable escalations silently
accumulate; the trust model assumes a working human door.
EXPECTED OUTCOMES: founder signed into /ops on production; escalation queue
visible; the stuck-cert saga closed.

## Workstream 6 — Newsletter/opt-in lane (events@1live.co exists)
WHAT: (a) generate the signup helper list (each catalog source's newsletter/
signup page — extend the harvest tool to capture signup links); (b) design
least-privilege mailbox access for the parser: recommended dedicated ingest
Gmail + founder's Gmail filter (to:events@1live.co → auto-forward), NEVER an
app password to the personal account; (c) build the parser worker: poll the
scoped mailbox on schedule, treat each mail as a fetched page into the SAME
sensor → extract → gate line (email_opt_in is already an ANCHOR class —
publishes alone as confirmed); dead-man + Sentry from birth; (d) bridge:
prototype parsing via the founder's connected Gmail (events label) before the
standalone worker exists.
HOW: helper list from catalog pages on a runner; parser as a worker module +
scheduled workflow; one consolidated founder ask for the forward filter.
WHY IT MATTERS: newsletters are pure first-party signal that PUSH to us —
zero-crawl, often carrying events that never hit any website.
WHY THAT MATTERS: it is the most cost-efficient discovered-events source per
the founder's token/cost/new-data-efficiency directive.
EXPECTED OUTCOMES: signup list delivered; scoped mailbox agreed; parser
publishing gated events from real newsletters.

## Workstream 7 — Efficiency batch (founder-approved)
WHAT: adaptive per-source cadence (learned from raw_fetch changed/unchanged
history; hot sources every pass, cold daily) + delta-extraction (diff vs
stored content; extract only changed regions). Festival cadence-surge hooks in
here.
HOW: fetch-layer only; no gate moves; measured against cost-per-verified-event
after ~48h of live extraction data (charter: measure, don't guess).
WHY IT MATTERS: founder directive verbatim: "token and cost-efficient and most
critically new data efficient… not a whole lot of backend work if a venue has
nothing new."
WHY THAT MATTERS: this is what makes 20-minute freshness affordable at 4,200
sources and in every future market — spend scales with activity, not catalog
size.
EXPECTED OUTCOMES: cost-per-verified-event drops measurably; cadence table
visible per source; caps stop being the freshness bottleneck.

## Workstream 8 — Special Situations festival mode (founder-directed)
WHAT: festival windows as data (name/dates/geo/keyword pack) → cadence surge →
adjacent-event keyword sweeps (search lane) → pop-up source class with expiry
→ festival-week display note ("things move fast — confirm with the venue",
per founder 2026-08-05, WITHOUT touching the likely-displays-clean ruling) →
honest unofficial-vs-official provenance. Trust half already live (sxsw_mode
3-source rule).
HOW: decision record already written (records branch); design doc → build in
small PRs; ACL/F1 fall season is the rehearsal, SXSW March the proving ground.
WHY IT MATTERS: founder: adjacent/unofficial festival activity mostly has NO
home; capturing it is a category-defining opportunity.
WHY THAT MATTERS: "perfect it this first year, then roll it to festivals
anywhere in the world" — it is the expansion playbook.
EXPECTED OUTCOMES: festival window machinery merged and exercised on a real
fall event with measured adjacent-event yield.

## Workstream 9 — External waits + delegated chores (do the moment they unblock)
WHAT: (a) SeatGeek approval email → re-dispatch seatgeek dry-run → enable in
import_licensed (secrets already set); (b) if founder adds VERCEL_TOKEN →
delete stray AUTH_DISABLED env var + take over env/deploy chores; (c) v0
design loop when founder signs in: deliver the prepared 3-direction brief
prompt from the ratified canon (design language only, never repo code; no v0
Share links) → translate the chosen direction (founder's standing UI
complaints: missing pieces vs mockups, layout/density, design direction);
(d) watch R-079's trigger (any second push-access identity → environment-
scoped secrets migration).
HOW: event-driven; no polling theater; single consolidated founder list when
something truly needs them.
WHY IT MATTERS: each is a committed thread the founder already invested in.
WHY THAT MATTERS: dropped threads are exactly the "redoing things" tax the
founder called out; the register exists so nothing silently dies.
EXPECTED OUTCOMES: each thread either DONE or parked with a written trigger.

## Workstream 10 — Hygiene that keeps the machine honest
WHAT: (a) sentinel-lint: extend workflow_env_lint to FAIL any `schedule:`
workflow lacking a dead-man step (Kaizen class rule from tonight); (b) align
authority.py's dormant 2-signal 'likely' label to the confirmed-tier ruling;
(c) register the 50:1 KPI in docs/metrics/kpi_registry.json wired to
db_scope_report; (d) session bookends: close Contract #41 properly — STATE
contract close, ONE_LIVE_CHANGE_LOG entries, session arc, TODOS reconcile,
memory writes (decisions are already recorded; write the gotchas: organizer-
vs-organization id spaces, GitHub input-validation-against-default-branch,
vendor-UI-drift rule, merge-freeze-during-exam-bound-PRs); (e) wave-2
frictionless-nav residue (prefetch-on-intent, View Transitions) stays queued
unless the founder reprioritizes.
HOW: small PRs; the lint lands with tests proving it fails an unalarmed
schedule fixture.
WHY IT MATTERS: every one of tonight's internally-caught defects has a class
rule; the rules only count if they become gates.
WHY THAT MATTERS: "no downtime, no excuses, every market all the time" is a
property of gates, not vigilance.
EXPECTED OUTCOMES: a `schedule:` workflow without an alarm cannot merge;
ledgers/state current; zero open threads unlisted.

---
Definition of DONE for this session: every workstream either COMPLETE with
evidence links, or blocked-on-external with the blocker named and alarmed.
Report to the founder in plain language, once, with the 50:1 table.
