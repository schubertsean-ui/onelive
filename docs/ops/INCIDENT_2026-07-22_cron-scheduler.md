# Incident narrative: GitHub scheduler pickup + sparse delivery (2026-07-22)

Extracted VERBATIM from docs/RECORD.md's R-008 row at PR #49 r2 (the
evaluator's row-length audit nit, raised twice) — the row now carries
the resolution citations and pointers; this file preserves the full
incident history unchanged. The ACTIVE sparse-delivery deviation is
tracked in R-023 (OPEN), not here.

## The R-008 status narrative, as accumulated in the row

STATUS 2026-07-21: trigger conditions met at founder hands (spend-capped
key, DSN, dead-man URL stored; console cap first; healthchecks check
created — "done") and the friction attack ran non-Claude on PR #43
(FRICTION_LOG entry #3); the arming PR (20-minute `schedule:` per the
founder's cadence directive — hourly at first authoring — +
schedule-only 10-source ceiling + least-recently-attempted rotation) is
in flight; dead-man period at merge: 20 min + ~10 grace. Flips RESOLVED
in the post-merge bookkeeping commit citing: final APPROVE run id, green
capped smoke-run id, and the first green scheduled run.

STATUS 2026-07-22 (the post-merge commit): two of the three citations
exist — APPROVE run 29881030319 (merged ab6819a, fully green) and green
capped runs on the merged master code (29885464970 @ ab6819a: 10/10
sources, zero errors, dead-man assertion + ping-binding proven, artifact
8516375568). The third has NOT occurred: GitHub's scheduler had fired
ZERO schedule-event runs through 02:17Z despite four elapsed slots
(01:07–02:07) — known first-pickup lag for a newly added cron (workflow
state "active", cron verified on master). The dead-man alarm covers
exactly this gap by design; a manual capped dispatch at 02:18Z re-pinged
it. Row flips on the first green schedule-event run — if none fires by
~04:00Z (12+ slots), escalate: the nudge options (touch ingest.yml = new
smoke evidence cycle; disable/enable the workflow via founder's UI) go
to the founder as a consolidated ask.

ESCALATED 04:02Z as recorded: zero schedule-event runs across 9 slots
(01:07–04:00, 3h10m past registration); consolidated ask delivered
(recommended: founder's two-tap disable/enable on the workflow page —
the API surface available to the agent exposes no enable/disable
method); manual capped dispatches at 02:18Z and 03:15Z bridged the
dead-man and rotation meanwhile.

STATUS 12:0xZ: the founder's disable/enable (~04:07Z) did NOT take
(04:27/04:47 slots missed); founder-approved re-registration PR #46
(minutes 7,27,47→9,29,49, cadence unchanged) MERGED at evaluator
APPROVE + trust-gate green as master 76d2290 ~11:56Z — with an
honestly-recorded ~6.5h gap between the 05:28Z APPROVE and the merge
(watch turn ended with no wake-up armed; repeat of the slow-escalation
class, ledger row + ladder amendment in the same commit as that status).

RESOLVED (2026-07-22 ~12:05Z — all three citations now exist: (1) arming
PR #43 merged FULLY GREEN at evaluator APPROVE run 29881030319 (master
ab6819a); (2) green capped runs on the merged code throughout
(29885464970, 29887985205, 29917588982 @ post-#46 master 76d2290); (3)
THE FIRST GENUINE SCHEDULE-EVENT RUN: 29899042357, 2026-07-22T07:07:04Z
— the :07 slot of cron 7,27,47 firing on master ab6819a, success,
followed by 29909962538 at 09:56Z — the founder's disable/enable DID
take effect, first firing ~3h later. Honest post-script: PR #46's minute
shift (merged 11:56Z) was therefore not strictly necessary for
registration, but carried the evaluator-demanded harness fixes and
R-022's resolution; the new minutes 9,29,49 now govern.

OBSERVED: slot firing is SPARSE — 2 runs where ~14 slots elapsed
(GitHub drops scheduled slots under load); slot-fire density on the new
minutes was initially noted as a watch item. DENSITY 15:1xZ: first fire
on the new 9,29,49 registration = run 29927836751 (14:17:02Z, success,
master 76d2290 — re-registration proven, ~2.5h pickup lag). SCOPE
BOUNDARY (PR #49 r1): the R-008 row records the unarmed-cron hold, which
ended at arming + proven scheduled fires — it stays RESOLVED; the
sparse-delivery deviation is an ACTIVE issue and lives in its own OPEN
row, R-023, with owner and objective trigger — never buried in a
resolved row.
