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

---

## Entry #3 — 2026-07-21 — Arming the scheduled ingestion cron (every 20 minutes by founder amendment below; hourly at first authoring) (Step 5; advances R-005 + R-008 — both rows stay OPEN until the post-merge evidence commit)

**Attacker: the non-Claude CI evaluator on arming PR #43 (Entry #2
precedent — OPENAI_API_KEY remains absent in the local sandbox, so CI is
the only non-Claude channel). The attack HAS RUN: round-1 REQUEST-CHANGES,
run 29867512512, job 88759307805, 2026-07-21T20:54Z, model printed by the
job log as gpt-5.5. Its findings and the written answers are recorded
below (r1 section); each subsequent round lands the same way, per Entry
#2.** This entry also carries Entry #1's Step-5 attack surface into that
non-Claude attack (the re-attack R-005 requires): every Step-5 answer in
Entry #1 (budget caps precede scheduling; dead-man ping; manual runs
before cron; blast radius bounded to candidate rows) is restated and
mechanized below, and the r1 attack judged this text. R-005 flips only
in the post-merge bookkeeping commit, citing the PR's final APPROVE run —
never in this PR's own diff (r1 finding #3, answered below).

**Plan under attack:** (1) add least-recently-fetched rotation to
`worker/run_once.py`'s enabled-source query (unit-tested pure ordering);
(2) add the `schedule:` trigger to `.github/workflows/ingest.yml` (hourly
at first authoring; every 20 minutes since the founder's cadence
amendment below)
with a fixed 10-source ceiling for scheduled runs (dispatch keeps its
required explicit ceiling); (3) after evaluator APPROVE and BEFORE merge,
one manual `workflow_dispatch` smoke run capped at 5 sources must go green
end-to-end (DSN assembly, extraction, gate3, candidate rows, dead-man
success ping, replay artifact) — spend occurs only after the non-Claude
verdict; (4) merge arms the cron; founder notified with the
healthchecks.io period step (1 hour + grace).

**Hat structure (first live shakedown per docs/hats/ — TODOS row):**
- *Blue frame (pre-registered before any lens ran):* decision = "arm the
  hourly cron now, or hold?"; options = arm hourly / arm at lower cadence /
  stay manual; success = a scheduled loop that cannot overspend, cannot die
  silently, cannot starve coverage, and cannot publish; the frame was fixed
  before the White pass below.
- *White (facts, script-verified):* assemble_dsn.py passes a placeholder-free
  DSN through untouched (line 67–68 — a CODE fact about the passthrough
  path only; the live smoke attempt below DISPROVED the stored
  credential itself, so end-to-end correctness is owned exclusively by a
  green run, never by this passthrough property — corrected at r3, the
  original wording overclaimed); sentinel.deadman() pings
  start/success/fail around the run;
  the enabled-source query had NO ORDER BY while the cap "truncates the
  tail" — the starvation fact that became this PR's main code change;
  raw_fetch(source_id, fetched_at) + its index support rotation;
  OPENAI/GEMINI keys absent in the sandbox (Black must fire from CI).
- *Yellow (deliberate best-case, first live firing → M8):* argued upside —
  a capped hourly loop compounds into the launch asset: fresh same-night
  candidates for /tonight, a real per-run cost curve (routing decisions
  get data instead of guesses), daily full-catalog freshness telemetry
  that surfaces dead sources within 24h, and R-012's "one cron week"
  maturity trigger finally starts running. Validation criterion for the
  M8 row: after the first cron week — full catalog swept daily, zero
  dead-man alarms, cost-per-run within the console cap's daily share.
- *Black:* the CI evaluator's attack on this PR (see header) — the only
  non-Claude lens available; the local lenses above are Claude-run and say
  so (independence limitation logged; cross-family lenses need keys that
  don't exist locally).
- *Blue merge (conflict preserved):* Yellow wants hourly for freshness;
  Black-side cost pressure wants fewer runs. Not averaged: hourly ships
  because both caps bound the downside mechanically, and the LOGGED
  fallback (drop to 2-hourly) fires on measured cost, not on fear.

**Po battery (seed 20260721, random word "windmill") — harvest that
survived movement:**
- *Escape ("po: source order does not exist"):* under a per-run cap, order
  IS coverage — plain DB order starves the tail of the ~230-source catalog
  forever. Adopted as the PR's main code change: least-recently-fetched
  rotation, never-fetched first, deterministic tiebreak (10/run × 24
  runs/day ≥ catalog daily).
- *Exaggeration ("po: the cron fires every second / once a decade"):*
  overlapping runs when one exceeds the hour. Already bounded: concurrency
  group `ingest` queues (never doubles) and the 60-min timeout kills
  hangs; the dead-man check flags the missing success ping.
- *Distortion ("po: the ping fires before the run"):* it does — `deadman()`
  pings start/success/fail, so a run that dies mid-flight leaves a started-
  but-never-succeeded check. Adopted: founder step at merge — set the
  healthchecks.io check Period to 1 hour, Grace ~20 min, so a silently
  skipped GitHub cron slot also alarms.
- *Random "windmill" (feathering in storms):* a storm = a source page that
  balloons or turns hostile. Bounded: sensors strip boilerplate, extraction
  output is schema-validated, gate3 ESCALATEs weak signals, and nothing AI
  writes leaves the candidate store without a human. Watch item for the
  supervised first runs: per-run token cost vs the console cap.
- *Wishful ("po: the cron costs nothing"):* the 5-source smoke run measures
  real cost-per-run before the cron ever fires; if cost surprises, the
  cheaper path is dropping cadence (2-hourly), a logged decision — never
  raising the cap silently.

**Attack — what breaks?** Runaway spend → per-run ceiling (fail-closed
validation at both the workflow and `run_once.py` layers) + founder-set
console monthly cap. Silent death → dead-man start/success/fail pings +
founder-set period/grace. Tail starvation → rotation (above). Prompt
injection from fetched pages → gate3 + human-only promotion: worst case is
wrong CANDIDATE rows, never published events (AI never publishes — the
invariant is untouched by this PR). Secret leakage → unchanged PR #19
scope+masking design; arming adds no new secret surface.

**Who is harmed if wrong?** Founder (spend) — double-capped. Fans/venues
(wrong data) — bounded by the human gate; disputed-shown-never-hidden
unchanged. The on-call human (alert fatigue) — one check, one period; no
new alert channels.

**Cheaper path?** Considered: stay manual-only (rejected — Step 5's
done-criterion is a green SCHEDULED run, and manual-only rots into
nobody-runs-it); daily instead of hourly (rejected for launch freshness —
/tonight sells same-night accuracy; cadence drop stays the named fallback
if cost demands it). The smoke-run-before-merge IS the adopted cheaper
path from Entry #1.

**Founder-crucial or not?** The founder-crucial parts already happened at
founder hands: key minted with console cap first, secrets stored, dead-man
check created ("done", 2026-07-21). Arming itself is the charter's current
mission executed through the mandatory evaluator gate; merge-at-APPROVE +
notify is the ratified merge protocol. No gate threshold moves.

**Attack round 1 (run 29867512512, REQUEST-CHANGES) — findings → written
answers, in the same commit:**
1. *Scheduled fallback also applied to manual dispatch* — the `|| '10'`
   expression substituted 10 for ANY empty input, silently weakening the
   fail-closed budget contract for dispatch/API callers. Answer: real
   defect, fixed — the fixed ceiling now keys on
   `github.event_name == 'schedule'` (not caller-influenceable); every
   other event with a missing/empty input fails loud exactly as before.
2. *The entry self-certified the attack before it ran.* Answer: accepted
   and rewritten — this entry now records the attack that actually ran
   (ids above), each round appended as fact, never in advance.
3. *R-005 flipped RESOLVED inside the diff whose merge is the evidence.*
   Answer: accepted — R-005 and R-008 are back to OPEN-with-progress in
   docs/RECORD.md; they flip only in the post-merge bookkeeping commit
   citing the final APPROVE run id and the arming evidence.
4. *R-008 recorded future process as completed state.* Answer: same fix
   as #3; the row now states exactly what exists (PR in flight) and what
   evidence closes it.
5. *The pre-merge smoke run was deferred and non-mechanical.* Answer: the
   smoke run is no longer a promise — it has been EXECUTED and its
   evidence recorded in this entry (section below), so the reviewed diff
   carries the verifiable run id/URL/outcome instead of intent. Nits also
   taken: rotation wiring is now regression-tested through _run_real
   (fake DB, freshest-first rows, cap=2 → rotation-before-cap is the only
   passing order); the never-fetched sort sentinel is named; the model
   name above cites the CI log that prints it; the validate run is cited
   as INCOMPLETE-ACKNOWLEDGED (R-002), never as fully green.

**Smoke-run evidence (executed before merge, after the r1 attack +
written answers — spend followed the non-Claude attack, not preceded
it).** A green run must show DSN assembly, extraction, gate3 decisions,
candidate rows, the dead-man success ping, and the replay artifact.
- *Attempt 1 — run 29868035764, 2026-07-21T20:58Z, FAILED (fail-loud
  path proven, $0 AI spend):* psycopg2 `password authentication failed
  for user "postgres"` at aws-0-us-east-1.pooler.supabase.com:5432 —
  the stored DSN's credential is wrong (the founder hand-spliced the
  password at the generator's earlier instruction, the exact error mode
  tools/assemble_dsn.py exists to prevent; the generator owns that
  instruction as the likely cause). No Anthropic call was made; the job
  died at DB connect and went red, never green — the guard behaved
  exactly as designed. Founder asked (numbered steps, session chat) to
  re-store the DSN AS-PASTED from Supabase plus a separate
  ONELIVE_DB_PASSWORD secret, the designed path.
- *Attempt 2 — intermediate, run 29871230418, 2026-07-21T21:45Z, FAILED
  ($0 AI spend):* founder re-stored the DIRECT-connection URI; the host
  resolves IPv6-only and GitHub runners have no IPv6 ("Network is
  unreachable"). Corrected instruction: the SESSION-POOLER URI.
- *Attempt 3 — run 29873390712, 2026-07-21T22:20Z, SUCCESS (the required
  green run; mechanical evidence):*
  run 29873390712 (workflow_dispatch, master @ 1244783f, max_sources=5),
  conclusion SUCCESS, job 88778460292, every step green. DSN assembly:
  step "Validate DSN + register log mask" green on the Session-pooler
  URI + spliced password. Loop: "processing 5 of 266 enabled sources"
  (live catalog count, printed by the budget guard); RunReport run_id
  05139cf6-3969-4e66-8eca-d8d5a0dbf7c1; counts {fetched 4, extracted 3,
  passed 3, escalated 0, held 0, sensor_rejected 1, errors 1}. gate3
  decisions: SXSW Official Schedule, Ticketmaster Discovery API,
  Eventbrite API → ready_to_promote, "awaiting authenticated ops
  promote" — candidate rows written, AI-never-publishes held live.
  Defenses fired on real input: DICE rejected by the sensor with a
  prompt-injection marker ("you are now") before reaching the extractor;
  AXS 403 isolated per-source with the loud partial-error warning while
  the run stayed green. Dead-man: the pinged step green and no
  "dead-man ping failed" warning in the log (ping failures log loudly)
  → success ping delivered. Replay audit artifact:
  replay-log-29873390712, artifact id 8512039208, zip sha256
  5590f9c51202540096eb876522b17be0fbef88aeba013e4ed5655b8badd6c598.
  Every element the section header requires is present: DSN assembly,
  extraction, gate3 decisions, candidate rows, dead-man success ping,
  replay artifact.

**Attack round 2 (run 29868188958, REQUEST-CHANGES) — findings → written
answers:**
1. *Armed cron + known-bad DB credential is unmergeable, loud failure or
   not.* Answer: agreed without reservation — the merge gate in this
   entry already required a green run; the founder is re-storing the DSN
   the designed way (as-pasted URI + separate ONELIVE_DB_PASSWORD), and
   no merge happens before a green attempt is appended here.
2. *Draft changelog contradicted the live evidence* ("resolves
   R-005/R-008"; "the as-stored secret works"). Answer: corrected in
   place — the entry is unmerged draft in this same PR, so fixing the
   text IS the record staying true; the r2 round row documents both
   corrections.
3. *Rotation nit (real bug): only successful fetches left raw_fetch rows,
   so permanently-failing or perpetually-304 sources would lead the
   rotation forever and monopolize the capped window.* Answer: fixed at
   the adapter, not deferred — failed and not-modified fetches now record
   best-effort ATTEMPT rows (content_hash "attempt:<outcome>"), rotation
   thereby sweeps on last-attempted; regression tests pin the attempt
   writes and the never-masks-original-error property.
4. *Positional tuple fragility in the sort key; "verified" overclaim in
   the workflow header.* Answer: key now unpacks first/last by name;
   header states presence-checked, correctness owned by the recorded
   green smoke run.

**Attack round 3 (run 29869450208, REQUEST-CHANGES) — findings → written
answers:**
1. *Armed cron + known-bad credential + no green smoke (standing).*
   Answer: unchanged and agreed — founder-gated; the green run gates the
   merge, exactly as this entry states.
2. *The entry's own heading and White-facts bullet still overclaimed*
   ("resolves R-005 + R-008"; "the as-stored secret works unchanged").
   Answer: both corrected in place with the correction noted — heading
   now says "advances … rows stay OPEN"; the White fact is scoped to the
   code passthrough property with the live disproof cited beside it.
3. *record_fetch_attempt swallowed write failures unconditionally — on
   the 304 path there is no original error to protect, so a lost attempt
   row silently degrades the rotation invariant.* Answer: real hole,
   fixed with two explicit modes — the failed-fetch path stays
   best-effort (original error must reach the caller); the 304 path is
   STRICT (write failure propagates as that source's loud per-source
   failure). The demanded regression test (304 + broken DB → raises) is
   added and passing.
4. *Nits:* Python-side sort ceiling documented in the rotation docstring
   (fine to catalog scales orders of magnitude beyond target; revisit in
   SQL if the catalog materially outgrows it); changelog "sweeps daily"
   rephrased as capacity-to-sweep with the dead-man check named as the
   alarm for missed slots.

**Cadence amendment (founder-directed, 2026-07-21, session chat:
"Can you accelerate the ingestion to every 15 or 20 minutes?"):** the
schedule is every 20 minutes (7,27,47 past the hour), not hourly — the
gentler end of the founder's stated range. This supersedes the Blue
merge's hourly choice above BY THE RED HAT'S OWNER: spend escalation is
the founder's own decision (charter cost-discipline rule 2 — deliberate,
logged, never silent; ~3x hourly cost, still double-capped by the
10-source per-run ceiling and the console monthly cap). The dead-man
check period becomes 20 minutes + ~10 grace. The cadence-drop fallback
on measured cost stays the logged fallback, now with hourly as its first
step down.

**Attack round 4 (run 29869864335, REQUEST-CHANGES) — findings → written
answers:**
1. *Standing founder-gated blockers (armed cron, failed-only smoke
   evidence).* Answer: unchanged — the green run gates the merge; waiting
   on the re-stored secret.
2. *The r1-era changelog row still described the OLD ordering ("APPROVE →
   smoke → merge"), which would put the evidence after the reviewed
   head.* Answer: real sequencing catch — corrected in place; the
   protocol everywhere now reads evidence-first: green smoke committed to
   this entry → APPROVE on that exact head → merge.
3. *Nit — attempt rows must satisfy the real schema, not just fake
   cursors.* Answer, from migration 0003 read directly: content_hash is
   `text not null` ("attempt:failed" satisfies it), storage_ref is
   nullable (attempt rows pass NULL), headers is jsonb with the detail
   payload, source_id is the real uuid FK — and the green smoke run
   exercises the genuine insert path against the live schema before any
   merge.
4. *Nit — governance-doc churn means live gates must not rest on prose
   sequencing.* Answer: they don't — the mechanical gates are the
   evaluator's APPROVE (blocking check) and the committed green-run id;
   the prose narrates them, it never substitutes for them.

**Attack rounds 5–8 (runs 29870179043, 29870503527, 29871406408,
29871731363, each REQUEST-CHANGES):** standing founder-gated blockers
unchanged; per-round catches all fixed in place — r5: schema-fixture
test binding attempt-row assumptions to migration 0003's real text +
numeric rotation-revisit trigger (>2,000 enabled sources, printed every
capped run); r6: rotation docstring trimmed to the executable invariant;
r7: stale "hourly" purged from four governance records after the
founder's 20-minute cadence directive (top Kaizen class,
stale-cross-reference); r8: attempt-row bookkeeping failures upgraded
from quiet warning to ERROR log + traceback note riding the original
exception, plus the last two stale-cadence sentences.

**Attack round 9 (run 29872115251, REQUEST-CHANGES) — the one new
finding:** the healthchecks period/grace was a prose-only "founder step
at merge" — live alarm config arming a recurring cron cannot rest on
future prose. Answer: recorded honestly as R-020 (docs/RECORD.md) — the
config lives in the founder's healthchecks account outside the repo's
mechanical reach; mechanical assertion requires a read-only healthchecks
API key (new credential = founder-crucial, the row's trigger); until
then the failure mode is BOUNDED, never silent (success pings every ~20
min mean even a stale period alarms within ~period+grace of a dead
cron), and the founder's period confirmation is recorded in the
post-merge R-008 evidence commit.

**Verdict:** r1–r9 attacks recorded and answered above; the arming merges
only at the evaluator's APPROVE on the final head with the smoke evidence
in this entry — REQUEST-CHANGES rounds keep appending here until then.
