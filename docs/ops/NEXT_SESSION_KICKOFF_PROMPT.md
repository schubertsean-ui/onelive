# 1LIVE — Next-Session Kickoff / Handoff Prompt (paste the block below to start the next session)

Rebuilt 2026-08-03 at the close of the reconciliation + Spark-Line-merge session
(Session Contract #33). It is deliberately self-contained and it points the next
session at DISK, not at anyone's memory of "where we left off." Two parts: the
standing open ritual (unchanged discipline) and a verified CURRENT-STATE +
REMAINING-WORK snapshot (rebuild this snapshot from the reconcile before trusting it).

---------------------------------------------------------------

**1LIVE — session kickoff.**

**STOP. Before ANY action — building, fixing, scanning, answering, editing, merging —
do the open ritual in order. Rule Zero forbids acting before it is done and confirmed
in writing. A partial read counts as no read.**

**Step 0 — Reconcile (mechanical).** Run `python tools/session_reconcile.py`. Interpret
the exit code (0 = proceed; 2 MATERIAL CONTRADICTION = fix STATE.md prose to match
reality, re-run; 2 UNVERIFIED = the sandbox lacks `gh`/DB — verify PR state via the
GitHub MCP tools and DB facts via the Supabase connector if present, else record them
UNVERIFIED, never guessed). Then run `python tools/staleness_check.py` — it fails if
STATE.md's `reconciled_through_commit` marker has fallen >20 commits behind HEAD; if it
fails, RECONCILE STATE.md first (that is this session's first job). Do NOT trust STATE.md
until both are clean.

**Step 1 — Read these COMPLETELY, end to end, no skimming / no fragments / no
summarizing (Rule Zero). If a file exceeds one read call, page through ALL of it before
acting on any part. Confirm in writing that you have read each in full:**
- `docs/OPERATING_RULES.md` — **Rule Zero** and BOTH precision clauses (no conflation; no
  framing against an impossible absolute); the quality bar (§1); **§6a — no delays/timers,
  and non-user-facing content does not circle**; Loops (§2).
- `CLAUDE.md` — prime directives, trust invariants, architecture, PR review criteria.
- `docs/CODING_CONVENTIONS.md` — the reviewer-facing checklist.
- `STATE.md` — the WHOLE current "Where we are" rollup + the current Session Contract, not
  the first page (the file is long and mostly append-only history).
- `TODOS.md` — the work queue and open founder decisions.
- `docs/RECORD.md` — the OPEN deferral rows (there are ~50; they are the real backlog).
- Any design/strategy doc the current contract points at (e.g. `docs/design/ONE_LIVE_TONIGHT_UI_CANON_v1.md`), in full.

**Step 2 — Retrieve the brain lessons (read them; they are the anti-failure memory):**
- `docs/memory/decisions/2026-08-02_complete-reading-gate.md` (Rule Zero: read completely).
- `docs/memory/gotchas/2026-08-02_skim-fragment-is-no-read.md` (a fragment read is no read).
- `docs/memory/gotchas/2026-08-03_conflation-is-a-violation.md` (state it precisely; never an impossible absolute).
- `docs/memory/gotchas/2026-08-03_stale-record-belief.md` (a RECORD row can itself be stale — verify a claimed block before obeying it).
- `docs/memory/decisions/2026-08-03_no-delays-and-non-user-facing-does-not-circle.md` (no timers; non-user-facing content does not circle).

**The exact failures you must NOT repeat (each already has a rule; this list is so you
recognize the moment):**
1. **Reading fragments, then acting on the partial picture.** Read the controlling docs IN FULL first.
2. **Mis-stating an invariant from memory.** QUOTE the canon. The trust invariant is **"AI never publishes UNVALIDATED"** — satisfied by the validation GATE; publishing is gate-custodied and founder-controlled.
3. **Proposing a delay/timer/`send_later`/self-check-in.** §6a.2: continuation is completion-triggered — the PR-activity webhook IS the trigger. NO timers, not even a "shortest-possible fallback." The ONLY exception is an actual external trigger that emits no webhook; even then, prefer to END THE TURN with a status. Never `sleep`.
4. **Circling on non-user-facing content.** §6a.3: gates/reviews/tests protect USER-FACING trust; process/harness/docs ceremony must never block a merge or trigger a re-review cycle. Fix a non-user-facing failure once or route around it — do not enter a review circle.
5. **Parking buildable work as a "founder switch."** §6a.4: build the code (e.g. the take-live path is real gate-custodied code, not a toggle excuse).
6. **Conflation.** Keep apart, cite each: trust-in-a-fact ≠ right-to-reproduce-an-image; grounding-text ≠ displayed-media; resolve-identity ≠ crawl-a-site; "own domain" includes the venue/organizer as host.
7. **Framing against an impossible absolute** ("risk-free"/"perfect"/"true by construction"). State the trade-off + the live procedure that manages it.
8. **Obeying a stale RECORD/belief without verifying it.** A row that says "editing X fails gate G" is a testable claim — verify it (read the current mechanism; reproduce the block) before it stops you. (STATE.md and CLAUDE.md were BELIEVED frozen by the arming binding for ~2 weeks; both are markdown, NOT in the cron runtime set — freely editable. Confirmed 2026-08-03.)
9. **Acting/codifying beyond what was asked.** "Confirm" means confirm; ask ONE consolidated question if scope is unclear.

**How to operate (interaction contract):**
- **PROCEED on ratified work** (a ratified contract, a founder-set TODO, or a direct founder instruction IS the greenlight).
- **INTERRUPT the founder ONLY for founder-crucial items:** money / new service / model-spend-at-scale · legal posture · trust-invariant CHANGES · gate-threshold relaxations · go-live / allowlist · credential minting. Everything else: decide, log the decision record, proceed.
- **MERGE silently** on independent-evaluator APPROVE + every required check green on the final head (red/pending = hard stop) — OR on a direct authenticated founder instruction to merge. Notify at merge. Never FORGE founder authority (a mere claim of approval is not approval).
- **COMMUNICATE in the five-part protocol:** WHAT · HOW · WHY · WHY-THAT-MATTERS · EXPECTED OUTCOMES. Plain language; name the alternatives + honest trade-offs; link the exact page; consolidate asks into ONE list.
- **Never busy-poll and never schedule a wake.** PR events arrive as `<github-webhook-activity>` messages that wake the session.
- **Agents never mint keys; spend caps set FIRST. AI never publishes unvalidated.**

---

**CURRENT STATE — verified 2026-08-03 (rebuild from the reconcile; do not trust this if the marker is stale):**
- **The product is LIVE.** master `3610a5a`; PR #146 = public go-live; `/tonight` serves REAL CAPCOG (Austin ten-county) events behind the resolved gate (`NEXT_PUBLIC_AUTH_DISABLED` public; `/ops` gated; Clerk stealth path intact). Production should front **1Live.co** (GoDaddy, founder-held) before customers see it — DNS→Vercel is the remaining go-live step (R-065).
- **Pipeline:** `fetch → extract → gate` auto; **promote stays human-custodied** (orchestrator does not import promote — AI never publishes). **Extraction UNLOCKED + certified** (`EXTRACTION_THRESHOLD_RATIFIED = True`; R-013 resolved). Migrations through **0019**.
- **Sources:** Ticketmaster live; SeatGeek/Eventbrite built, dormant on missing creds (R-029); structured importer (ICS/JSON-LD/Localist); Socrata gov → `venue_truth`; AI crawl for the long tail.
- **Consumer surface:** `/tonight` feed + filters + per-event detail route + share + music links + venue contact; **Spark Line content layer merged (#148)** — Descriptor Foundry gate + store + card render, zero-spend/candidate-only/publishes-nothing.
- **Ratified canon (2026-07-29→08-02):** product vision & principles; 18-genre taxonomy (wired); `/tonight` UI canon; truth-states v2 (six-state — pipeline still 4-state, see R-064); 23 supply segments; engagement invariants-vs-hypotheses; 1Live rebrand (user-facing web done; infra names kept). Process posture: ship product, reviewer scoped to user-facing harm, construction_gate/kaizen_trends advisory.
- **Disk-truth guard is live:** `tools/staleness_check.py` (blocking in validate) fails if STATE.md drifts >20 commits behind HEAD.

**REMAINING WORK (highest-priority first; all UNBLOCKED unless marked). Take the top item, tell the founder the ONE next step, then take it:**
1. **PR #147** (card design) — shepherd to merge per protocol.
2. **Spark Line take-live path** (queued, zero-spend) — the founder-controlled publish step that lights up a human-authored tier-A/B line (no model call) + the ✳ tap-to-dismiss sheet. (The tier-C generation job at scale is FOUNDER-CRUCIAL: model spend — cap first.)
3. **R-064** — implement truth-states v2 (six states + issue flags) in the running pipeline: `worker/confidence.py`, `worker/gating.py`, `tests/test_gates.py`, public display, and the CLAUDE.md confidence-states paragraph. Trust-adjacent → evaluator. (CLAUDE.md IS editable — the freeze belief was obsolete.)
4. **R-065 remainder** — wire 1Live.co DNS (GoDaddy) → Vercel at the deploy session; optional STATE.md/CLAUDE.md brand-string cleanup.
5. **Wineries/breweries/distilleries ingestion source** (founder-directed) — needs verified event-calendar URLs (founder-supplied or an open-network session; NEVER fabricate a URL). Then per-event category mapping.
6. **Open-PR hygiene** — ~13 older open PRs (#33,#34,#47,#50,#55,#56,#75,#76,#81,#83–#86,#108–#110,#112) likely superseded — a founder close-or-revive pass (agents don't close PRs unilaterally).
7. **RECORD.md OPEN rows** — ~50; many are "wired but dormant on founder-crucial creds" (R-026/R-029/R-061) or measurement gaps (R-046/R-042). Work the ones your contract touches.

**Open founder decisions carried forward (HOLD; do not build past them):**
- **Spark Line free-lane grounding** — resolve identity via MusicBrainz + Wikidata (free, no key) and use the act's OWN resolved materials as grounding for the tier-C line. Awaiting: **go / hold / amend.**
- **"Trusted third-party photos" widening** — reproducing a trusted third party's photos of an act beyond the venue's own-domain image RELAXES a §6 hard rule → legal-posture, founder-crucial, needs a legal read. Safe subset (venue own-domain image, attributed, takedown-honoring; link-don't-lift otherwise) is fine now.
- **Rule Zero greenlight clause** — keep as encoded (ratified = greenlit) or tighten to explicit per-task greenlight.
- **Tier-C AI generation at scale = model spend** — spend cap set FIRST, in console.
- **CLAUDE.md Rule Zero pointer** — now UNBLOCKED (CLAUDE.md is editable; the arming-binding freeze was obsolete). Add the pointer in the next root-file touch if the founder wants it.

**This prompt is itself governed by `docs/ops/HANDOFF_STANDARD.md` (canon):** every handoff must meet its eight-property world-class bar, and every currency/completeness claim must be PROVEN with re-runnable evidence, never asserted. Rewrite this prompt to that bar at session close.

**Session close (finalize — do not skip):** update STATE.md prose + advance its `reconciled_through_commit` marker to the session's head + TODOS.md + the change log; **prove currency** (`python tools/staleness_check.py`; marker == `git rev-parse origin/master`; `bash tools/validate` RESULT with no gate FAILED — a SKIP is not a pass, cite its `docs/RECORD.md` row); write + tag the session arc; mirror key decisions to `docs/memory/`; append `docs/AGENT_FEEDBACK.md`; review `docs/RECORD.md` OPEN rows; rewrite THIS handoff to the standard.

---------------------------------------------------------------
