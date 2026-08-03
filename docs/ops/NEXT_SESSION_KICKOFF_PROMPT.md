# 1LIVE — Next-Session Kickoff Prompt (paste the block below to start the next session)

Built 2026-08-03 from the failures of the prior session, so each one has a standing
guardrail. Everything below the line is the prompt to paste. It is deliberately
self-contained: it tells the next session to derive truth from disk (reconcile +
read), never from anyone's memory of "where we left off."

---------------------------------------------------------------

**1LIVE — session kickoff.**

**STOP. Before ANY action — building, fixing, scanning, answering, editing, merging —
do the open ritual in order. Rule Zero forbids acting before it is done and confirmed
in writing. A partial read counts as no read.**

**Step 0 — Reconcile (mechanical).** Run `python tools/session_reconcile.py`. Interpret
the exit code (0 = proceed; 2 MATERIAL CONTRADICTION = fix STATE.md prose to match
reality, re-run; 2 UNVERIFIED = verify the printed SQL via the Supabase connector,
update the block). Do NOT trust STATE.md until reconcile is clean.

**Step 1 — Read these COMPLETELY, end to end, no skimming / no fragments / no
summarizing (Rule Zero). If a file exceeds one read call, page through ALL of it before
acting on any part. Confirm in writing that you have read each in full:**
- `docs/OPERATING_RULES.md` — Rule Zero and BOTH its precision clauses (no conflation;
  no framing against an impossible absolute), the quality bar, §6a (no delays), Loops.
- `CLAUDE.md` — prime directives, trust invariants, architecture, PR review criteria.
- `docs/CODING_CONVENTIONS.md` — the reviewer-facing checklist.
- `STATE.md` — the WHOLE current Session Contract, not the first page.
- `TODOS.md` — the work queue and open founder decisions.
- Any design/strategy doc the current contract points at (e.g. the `/tonight` UI canon),
  in full.

**Step 2 — Retrieve the brain lessons from last session (read them, they are the
anti-failure memory):**
- `docs/memory/decisions/2026-08-02_complete-reading-gate.md` (Rule Zero: read completely).
- `docs/memory/gotchas/2026-08-02_skim-fragment-is-no-read.md` (a fragment read is no read).
- `docs/memory/gotchas/2026-08-03_conflation-is-a-violation.md` (state it precisely; and its
  cousin — never frame against an impossible absolute).

**The exact failures from last session you must NOT repeat (each already has a rule —
this list is so you recognize the moment):**
1. **Reading fragments, then acting on the partial picture.** Read the controlling docs
   IN FULL first. "I got the gist" / "to save context" are the rationalizations that
   precede the failure.
2. **Mis-stating an invariant from memory.** QUOTE the canon; never paraphrase an
   invariant, and never state it narrower or broader than the doc. The trust invariant is
   **"AI never publishes UNVALIDATED"** — satisfied by the validation GATE; publishing is
   gate-custodied and founder-controlled. (Not "true by construction / unreachable.")
3. **Proposing a delay or timer.** OPERATING_RULES §6a: no delays beyond the required
   minimum; work is completion-triggered (PR/webhook events), never clock-triggered.
   Never `sleep` to wait for external events.
4. **Parking buildable work as a "founder switch."** §6a.3: build the take-live path as
   real, gate-custodied CODE. A founder switch is the auto-publish decision, not an excuse
   to not build.
5. **Conflation — merging two distinct things into one claim.** Keep these apart by name,
   cite each to its source: trust-in-a-fact ≠ right-to-reproduce-an-image;
   grounding-text ≠ displayed-media; resolve-identity ≠ crawl-a-site; "the entity's own
   domain" includes the venue/organizer as host, not only the artist.
6. **Framing against an impossible absolute.** "Risk-free", "perfect", "zero risk",
   "true by construction", "guaranteed" do not exist. State the trade-off, then name the
   LIVE procedure that manages it as far as is humanly and technologically possible. That
   is the standard — never the absolute.
7. **Acting/codifying beyond what was asked.** When the founder says "confirm," confirm.
   When it says "build," build. If an instruction's scope is unclear, ask ONE consolidated
   question before doing doc churn or irreversible work.

**How to operate (interaction contract):**
- **PROCEED on ratified work.** A ratified contract, a founder-set TODO, or a direct
  founder instruction IS the greenlight (charter "proceed on ratified work").
- **INTERRUPT the founder ONLY for founder-crucial items:** money / new service /
  model-spend-at-scale · legal posture · trust-invariant CHANGES · gate-threshold
  relaxations · go-live / allowlist · credential minting. Everything else: decide, log the
  decision record, proceed.
- **MERGE silently** on independent-evaluator APPROVE + every required check green on the
  final head. Red or pending = hard stop, no exceptions. Notify the founder at merge.
- **COMMUNICATE in the five-part protocol** (`docs/memory/decisions/2026-08-01_comms-framework-canon.md`):
  WHAT · HOW · WHY · WHY THAT WHY MATTERS · EXPECTED OUTCOMES. Plain language for a smart
  non-engineer; name the alternatives and the honest trade-offs; link the exact page;
  consolidate asks into ONE list. No marketing spiel.
- **Never busy-poll.** PR events arrive as `<github-webhook-activity>` messages that wake
  the session; do not `sleep` or repeat status checks.
- **Agents never mint keys; spend caps are set FIRST.** AI never publishes unvalidated.

**Then:** take the highest-priority UNBLOCKED item from TODOS.md (never one that depends
on an open founder decision), and tell the founder the ONE next step you are taking —
then take it.

**Open founder decisions carried forward (hold on these; do not build past them):**
- **Spark Line free-lane grounding** — resolve identity via MusicBrainz + Wikidata (free,
  no key, no legal exposure) and use the act's OWN resolved materials as grounding for the
  tier-C Spark Line. Zero new spend. Awaiting: **go / hold / amend.**
- **"Trusted third-party photos" widening** — whether a trusted third party's (e.g. a
  venue's) displayed photos of an act may be reproduced beyond the venue's own-domain
  image. This RELAXES a §6 hard rule → **legal-posture, founder-crucial; needs a legal
  read** before adoption. Safe subset (venue own-domain image hotlinked+attributed+
  takedown; link-don't-lift otherwise) is fine now.
- **Rule Zero greenlight clause** — keep as encoded (ratified = greenlit) or tighten to
  explicit per-task greenlight even for ratified work.
- **Tier-C AI generation at scale = model spend** — running the dormant, budget-capped
  Descriptor Foundry generation job against many acts consumes paid model calls; that is a
  spend decision (spend cap set FIRST, in console).
- **CLAUDE.md Rule Zero pointer** — queued for the next lawful root-file window (editing
  CLAUDE.md trips the arming-evidence binding; batch it with other root-file work).

**Session close (finalize — do not skip):** update STATE.md prose + TODOS.md + the change
log; re-run `session_reconcile.py --heal`; run `bash tools/validate` (a SKIP is not a pass
— cite its `docs/RECORD.md` row); write + tag the session arc; mirror key decisions to
brain; append `docs/AGENT_FEEDBACK.md`; review `docs/RECORD.md` OPEN rows; run Kaizen
trends.

---------------------------------------------------------------
