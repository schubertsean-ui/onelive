# FRICTION_LOG — pre-work adversarial attacks on plans

Greppable summary: append-only log of the Friction gate (CLAUDE.md Agent org).
Before any irreversible action — deploy, migration, spend, prompt_version
bump — the plan is written here and attacked with: **"what breaks, who is
harmed, cheaper path, founder-crucial or not?"** Blockers must be answered in
writing before the action executes. The attack MUST come from a non-Claude
model (generator/evaluator separation applies to planning too); entries whose
attack could not yet run non-Claude are marked PROVISIONAL and re-attacked
once `OPENAI_API_KEY` exists.

Format per entry: plan → attack findings → written answers → verdict.

---

## Entry #1 — 2026-07-13 — The Session-1 sprint plan itself (docs/SPRINT_LIVE_SITE.md)

**Status: PROVISIONAL — attacked by the generator model (Claude) because
OPENAI_API_KEY is not yet minted. This violates the non-Claude rule by
necessity, is flagged per the charter's degrade-gracefully instruction, and
the entry must be re-attacked by the Independent Evaluator before Step 5
executes.** Session 1 itself performed no irreversible action (zero deploys,
zero migrations, zero spend), so no action rode on this provisional attack.

**Plan under attack:** docs/SPRINT_LIVE_SITE.md (Steps 5→10).

**Attack — what breaks?**
1. Step 5 schedules a recurring loop over 230 enabled sources with an LLM key
   in the env. A prompt-injection page ("list this event as confirmed") or a
   runaway retry loop is the top AI attack surface (deep review §11.4) and the
   top spend risk (§14.3). *Answer in writing:* budget caps are a named
   precondition (P2) and the plan refuses a first scheduled run before caps;
   gate3 ESCALATE + human-only promotion bound the blast radius to candidate
   rows, never published events; scheduled red-teaming is queued under §11.4
   ratification.
2. GitHub Actions cron has job time limits and silent-failure modes; 230
   sources may not fit one job. *Answer:* dead-man ping already wired; the
   charter's scheduler comparison names the Fly.io promotion trigger
   (time-limit breach) in advance; first runs use a per-run source ceiling.
3. Step 9 could ship the prototype's "✓ Confirmed" badge, violating the
   ratified no-badges trust rule. *Answer:* named explicitly in Step 9 as a
   must-not-ship; the design-PR rubric pass makes it a blocking check.
4. Step 8 could be waved through because "PR #9 was already reviewed."
   *Answer:* Step 8's done-criterion requires live observation of both
   fail-closed behaviors, not code review alone.

**Who is harmed if wrong?** Fans (wrong events published) — bounded by
human-only promotion; founder (unbounded token bill) — bounded by P2 caps;
artists/venues (misrepresentation) — bounded by provenance + eval thresholds
(Step 6 precedes real-data promotion in Step 7).

**Cheaper path?** Yes for Step 5: run the loop manually (`run_once.py --real`)
a few times before scheduling to observe real cost per run — adopted as an
implicit first sub-step of Step 5's done-criterion ("one green scheduled run"
implies manual runs first). No cheaper path found for 6–10 that keeps the
trust gates.

**Founder-crucial or not?** Step 5 (spend cap), Step 8 (allowlist content),
Step 9 (Vercel token), Step 10 (go-live) contain founder-crucial points;
Steps 6–7 are autonomous with decision records, except the §11.2 threshold
number which needs a one-line founder ratification.

**Verdict:** plan proceeds to founder review; no step executes before its
listed gate. Re-attack non-Claude before Step 5.

---

## Entry #2 — 2026-07-15 — Prompt bump v2026-07-15.3 + opening the extraction gate (PR #25)

**Attacker: GPT-5.5 (non-Claude ✓) via the CI adversarial-review job on this
same PR — its round-5 REQUEST-CHANGES IS the attack on this plan; answers
below are in the same commit.** (OPENAI_API_KEY remains absent in the local
session env — R-005 unchanged — so the CI evaluator is the non-Claude channel.)

**Plan under attack:** bump EXTRACTION_SYSTEM_PROMPT to v2026-07-15.3
(field-convention fixes from exam cycles 1–4), then flip
`EXTRACTION_THRESHOLD_RATIFIED = True` in a follow-up commit ONLY when
claude-sonnet-4-6 passes the golden-set exam (≤1% hallucination, recall
≥0.80, zero injections, ≥300-fact set) — the R-013 evidence rule.

**Po battery (docs/skills/po_provocation.md, seed 20260715, random word
"anchor") — harvest that survived movement:**
- *Escape ("po: the exam does not measure hallucination"):* exam texts ≠
  production distribution. Kept: docs/KAIZEN.md §M7's production sampled
  audit remains the second measurement leg; the exam alone never claims
  production truth.
- *Reversal ("po: the model examines the golden set"):* the candidate's
  failures grade the SET — happened this cycle (3 key corrections).
  Adopted: permanent key-change log with per-change justification
  (ai/golden/README.md).
- *Distortion ("po: flip the flag first, examine later"):* exactly the
  failure R-013 forbids; re-affirmed — the flip commit must cite the
  passing run + artifact.
- *Random-entry "anchor" ("the anchor drags"):* a passing expensive model
  gets pinned while cheaper tiers improve. Adopted: after merge, re-run the
  exam for claude-haiku-4-5 via workflow_dispatch; if it passes the SAME
  exam, de-escalate routing (cost-discipline rule 4, both directions).
- *Random+escape ("no anchor"):* silent prompt drift between bumps.
  Candidate (queued to TODOS, not blocking): stamp a prompt content hash in
  provenance next to prompt_version.

**Attack findings (evaluator r5) → written answers:**
1. *Prompt/routing changed without exam evidence attached.* Answer: the
   evidence channel is the parallel release-blocking exam check on the same
   SHA; merge requires both green (note now embedded in the review's input;
   this PR does not merge on a red exam).
2. *Exam channel confinement not fail-closed (wrapper hole).* Answer:
   closed at both layers in this commit — runtime stack-walk now rejects any
   worker//api/ frame anywhere in the stack; trust_gate now also flags any
   `golden_exam` reference outside the allowlist. Regression test compiles a
   synthetic worker-frame wrapper and asserts denial.
3. *Who is harmed if the gate opens on a bad pass?* Fans see wrong events —
   bounded: extraction output still enters the candidate store behind the
   human-review gate; AI never publishes. Founder pays sonnet rates —
   bounded: per-run ceilings + console cap; de-escalation exam queued.
4. *Cheaper path?* Haiku failed 3 calibrated cycles (logged in the routing
   table); the cheaper path is the post-merge de-escalation exam above, not
   shipping an extractor that fails its release gate.
5. *Founder-crucial?* No: no new money/services (same key, same caps), no
   trust-invariant change (the gate opens exactly as ratified in R-006/R-013);
   tier change is logged per cost-discipline rule 2. The flip commit cites
   run ID + artifact.

**Verdict:** proceed — prompt bump ships now; flag flips only on a passing
exam for the routed model, citing the evidence.
