# SESSION KICKOFF — 2026-08-06 (successor to SESSION_KICKOFF_2026-08-05.md)

Founder-commissioned work order for the next session. Read this FIRST, then
run `python tools/session_reconcile.py` and verify every claim here against
live state before acting (PR states via the GitHub API, DB via db-report.yml,
site via ops-diagnostics site-probe — the sandbox cannot reach 1live.co or
api.github.com directly). Contract-first: write Session Contract #44 to
STATE.md (five §4a fields) before any build.

Founder directive shaping this kickoff (verbatim, decision record
`docs/memory/decisions/2026-08-05_cards-reflect-updated-content.md`, same
commit as this file):

> "I want the UI/UX to reflect all the updated content on the cards now."

---

## WHERE WE ARE (verified 2026-08-05 ~15:45Z; re-verify at session start)

**The engine is live and publishing end-to-end.** Master `3929987`.
- Scheduled ingest: green, cap 30 sources/run (~every source every 3h),
  extraction ON (certified), dead-man alarmed.
- Gate-verdict persistence (#182, merged): orchestrator stamps every gate3
  verdict onto the candidate row (compare-and-swap, newer-adjudicated-state
  wins); autopromote runs a bounded stamp sweep before its promote phase.
- First live stamp+promote pass (autopromote run 30979536905): StampReport
  examined 1000 / stamped_ready 234 / stamped_hold 744 / escalated 22 /
  errors 0; promote examined 200 / **promoted 136 discovered events as
  confirmed** / errors 64 (single cause, fix already up as PR #186).
- Backlog remaining at that pass: ~3,200 candidates still unstamped
  (4,202-row backlog, 1,000/sweep), plus 744 holds accruing corroboration.
- Eventbrite event-id lane (#178, merged): importer trust boundary enforces
  the evidence-authenticated allow-list `sources/eventbrite_provenance.json`
  (23 event ids, 13 organizers, digest-pinned to harvest run 30944506990).
- Hygiene merged this cycle: sentinel lint R5 (schedule ⇒ dead-man binding),
  authority 2-signal → confirmed, 50:1 KPI registry + ledger, "discovered
  events" vocabulary sweep, ops-diagnostics workflow (#184), search quota
  budget doc.
- Clerk SSL saga: support manually re-issued verification 2026-08-05 ~05:06Z
  ("Folke" email); Clerk domain object updated_at moved to 05:13Z. Proof of
  serving cert = TLS handshake, shipping in PR #185.
- Vercel: AUTH_DISABLED deleted from all targets + production redeployed.
- BEFORE table (for the 50:1 report, collected pre-promotion): today
  18 licensed : 0 discovered; weekend 74:0; next-7-days 120:0; totals 1,633
  published events, 268 sources, 245 producing.

**Open PRs (all subscribed, all drive-to-green):**
- **#186** `claude/artist-ids-uuid-cast` — the 64 promote errors, one cause:
  event insert now casts `%s::uuid[]` for artist_ids + source pin. MERGE
  FIRST; it unblocks every candidate with named artists.
- **#185** `claude/ops-diag-clerk-tls` — site-probe TLS handshakes for
  accounts.1live.co/clerk.1live.co; healthchecks payload via `jq -n`;
  cse-probe key-shape line. Doubles as the diagnostic bench.
- **#177** `claude/source-scanner-v1` — 20-query source scanner (refreshed
  onto current master, suite green). Exercising it awaits the CSE key fix.

**Blocked on founder/external (the standing ask list):**
1. **Google CSE key**: cx PROVEN good (17-hex, probe-verified); stored key
   well-formed (39-char AIza); Custom Search API enabled on project `1live`;
   key restricted to Custom Search API, app restrictions None — yet the API
   still 403s "project does not have access" (9+ hours post-enable, so not
   propagation). Next mechanical step: founder re-pastes the key VALUE fresh
   from the 1live key's own page (Show key) to close the "is the stored key
   THIS key" link; if the 403 survives that, have the founder mint a brand-new
   key in `1live` (not rotate) and re-paste. Probe: ops-diagnostics
   mode=cse-probe (shape lines prove what changed without printing values).
2. **Gmail connector re-auth** (claude.ai settings) — blocks newsletter-lane
   send/receive checks (WS6 here).
3. **SeatGeek approval email** — on arrival: re-dispatch seatgeek dry-run,
   then enable in import_licensed.
4. **v0 design loop** — founder signs in at v0.app when ready; agent owes the
   committed paste-ready 3-direction prompt (Workstream A2 below).
5. **Clerk /ops sign-in walkthrough** — after #185 merges and the TLS probe
   shows the cert serving.

**Protocol in force (unchanged, from the 2026-08-05 kickoff + charter):**
merges are silent on evaluator APPROVE + all checks green on the final head;
freeze all other merges while an exam-bound PR is open; no timers ever — the
webhook subscription IS the trigger; every founder directive gets a verbatim
decision record in the same commit; say "discovered events," never "long
tail"; batch founder asks into ONE list with exact paste-ready values; never
click-path a vendor UI you can't see — use the delegated CI diagnostics
(ops-diagnostics.yml: clerk-domains, vercel-*, healthchecks-*, cse-probe,
site-probe) or ask for a screenshot. Delegations live as repo Actions
secrets: VERCEL_TOKEN, HEALTHCHECKS_API_KEY, CLERK_SECRET_KEY_ADMIN (usable
only via workflows on master). Every PR carries a STATE line or is followed
immediately by the records-only master commit (staleness_check tolerance 0).

---

## BUCKET 1 — BUILT, WAITING TO REACH THE LIVE SITE (merge/exercise only)

**1a. Land the three open PRs** (#186 first, then #185, #177) — evaluator
APPROVE + green → silent merge, records-only STATE commit if any squash
lacks a STATE line.

**1b. Finish the promotion backlog and deliver the 50:1 report.** After #186:
dispatch autopromote.yml (limit 200+, stamp_limit 1000; repeat sweeps until
StampReport examined < stamp_limit — the backlog is ~3,200 rows); re-run
db-report.yml for the AFTER table; dispatch site-probe (post-#185 it also
proves the Clerk certs) and confirm discovered events render on 1live.co.
Deliver ONE plain-language founder report with the before/after table:
licensed vs discovered counts today/weekend/next-7-days, the KPI ledger row
(kpi_report.py --append), and what the 50:1 ratio is doing.
EXPECTED OUTCOME: the founder reads one message and sees discovered events
live, counted, and trending.

**1c. Close the Clerk cert saga.** Post-#185 site-probe: TLS handshake
subject/issuer/expiry for accounts.1live.co + clerk.1live.co. On green,
walk the founder through ONE /ops sign-in (screenshot-guided if anything
looks off). EXPECTED OUTCOME: WS5 closed with handshake evidence.

**1d. First source scan.** The moment the CSE key 403 clears (probe green):
dispatch provider-dryrun mode=source-scan (max 20 queries per the committed
budget docs/ops/SEARCH_QUOTA_BUDGET.md), plus the eventbrite-search retest
(10). Curate the artifact into catalog candidates for founder review.
EXPECTED OUTCOME: first scanner harvest of new first-party Austin domains.

## BUCKET 2 — SCOPED, REMAINING TO BUILD THEN PUSH

**A. CARDS REFLECT THE UPDATED CONTENT (founder-directed, TOP of the build
queue).** Audit-then-align: (1) enumerate every field the promote path now
writes (title, category, subsegment, ticket_url, confidence, provenance,
artist_ids once #186 lands, venue link); (2) audit what /tonight actually
renders (web/app/(public)/tonight/FeedApp.tsx, [id] detail, web/lib) against
that list AND against the ratified canon (ONE_LIVE_MASTER_DESIGN_BRIEF_v2.4
+ ONE_LIVE_TONIGHT_UI_CANON_v1 + Spark Line/Emotion Glyph card anatomy);
(3) close the gap in small PRs — categories/subsegments surfaced, ticket
links actionable, confidence displayed per the trust display rules (quiet
icon, no badges, disputed shown never hidden), WCAG 2.2 AA, CWV budgets.
Evaluator pass against the brief's 8-criterion rubric on every design PR.
EXPECTED OUTCOME: a card on /tonight shows everything the engine now knows,
honestly, in the ratified design language.

**A2. v0 prompt package.** Commit the paste-ready 3-direction brief prompt
(design language only from the ratified canon; NEVER repo code; no v0 Share
links) per docs/memory/decisions/2026-08-04_design-loop-v0.md, so the
founder's v0 sign-in needs zero assembly. Translation of the chosen
direction is a later workstream.

**B. Eventbrite lane to scheduled, alarmed import (WS4 completion).**
Dry-run the 23 registry ids (provider-dryrun mode=eventbrite-events);
then wire the scheduled import + recurring harvest with healthchecks
dead-man checks (HEALTHCHECKS_API_KEY delegated; sentinel lint R5 enforces
the binding). EXPECTED OUTCOME: Eventbrite events flowing on a cadence,
alarmed, allow-list enforced.

**C. Festival Special Situations mode.** Design doc is COMMITTED at
docs/design/FESTIVAL_SPECIAL_SITUATIONS_v1.md (this commit). Build its six
numbered pieces in order, each a small PR: windows-as-data →
window-triggered cadence boost → keyword-pack search lane → pop-up source
class with expiry → festival-week display note → unofficial-vs-official
provenance. ACL/F1 fall season is the rehearsal, SXSW March the proving
ground. EXPECTED OUTCOME: festival machinery merged before ACL windows.

**D. Session hygiene owed from 2026-08-05 (WS10 close-out).** Contract #43
close in STATE, ONE_LIVE_CHANGE_LOG entries, session arc
(docs/session_arcs/), TODOS reconcile, Kaizen rows (retyped-SHA,
docs-only-merge-owes-STATE-line, staleness-drift-window,
db-type-mismatch-invisible-to-hermetic-tests), KPI ledger row per merged PR.
Do these AT THIS SESSION'S OPEN if 2026-08-05's close was cut short.

## BUCKET 3 — REMAINING TO SCOPE, THEN BUILD, THEN PUSH

**E. Newsletter lane on events@1live.co (WS6).** Scope first: signup helper
list of Austin venue/promoter newsletters, mailbox ingestion design (the
opt-in email forwarding source class already exists in the catalog,
skipped-no-base_url), parser worker feeding the NORMAL candidate pipeline
(no gate bypass). Gmail bridge blocked on connector re-auth. Scope doc →
founder ratify → build.

**F. Adaptive cadence + delta-extraction (WS7).** Waits for ~48h of live
cadence data (accruing since 2026-08-05 ~01:00Z — likely ready during this
session). Scope: per-source fetch-yield stats → cadence tiers (hot sources
every run, dead sources weekly) → not_modified/content-hash short-circuit
before extraction spend. Cost discipline: the win is Claude-call reduction;
measure cost-per-verified-event before/after. Scope doc → build.

**G. Post-scan source curation loop.** Once scanner harvests exist (1d):
scope the curation path from scan artifact → founder-reviewed catalog rows →
sources feeding ingest. Includes the "new sources need N clean runs before
trust" question — that is a gate-custody question: PROPOSAL to founder,
never agent-decided.

---

## DEFINITION OF DONE (this session)
Buckets 1a–1d COMPLETE with evidence links (or blocked-on-external with the
blocker named and alarmed); Workstream A visibly underway with at least the
audit + first align PR merged; every other bucket either advanced or
explicitly parked with its trigger written. Report to the founder ONCE, in
plain language, with the before/after 50:1 table and a link to the live
/tonight showing updated cards.
