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
