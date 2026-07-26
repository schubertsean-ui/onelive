# Agent merges its own PR once every gate is green, then notifies the founder — merging is no longer a founder checkpoint; merging on red still is.

**Directed:** 2026-07-18, founder (PR #35 session): "Why do you keep saying my
merge? You do the merge and notify me."

## The decision

1. When a PR reaches full green — evaluator APPROVE plus every required check
   on the PR's FINAL head — the agent merges it and notifies the founder with
   the merge commit and what landed. Waiting for a founder merge tap is no
   longer required and reads as an unnecessary interrupt (charter
   communication rule 5: smallest possible founder effort).
2. Everything upstream of the merge is unchanged: the evaluator gate is still
   mandatory, merging on red or with any check pending stays forbidden
   ("do not merge on red" is printed by the gate itself), and gate custody /
   founder-crucial escalations are untouched.
3. Other irreversible actions (deploy, migration apply, spend, sending,
   credential use) remain founder-checkpoint gated — this decision covers PR
   merges only.

## Why (recorded so future sessions don't re-ask)

The night-shift hard-stop list treated "merging a PR" as a human checkpoint.
In practice every merge-worthy PR has already passed the independent
non-Claude evaluator and all CI gates — the founder tap added latency, not
safety, and the founder explicitly removed it. The protective property was
never "a human clicks merge"; it is "nothing unreviewed merges", which the
gates enforce mechanically.

## Boundary

If any gate is red, pending, or was bypassed, there is no authority to merge
— that situation is still a hard stop. A merge that later proves wrong is an
M3/M2 ledger event like any other escape/catch, not a reason to quietly
reinstate the founder tap; fix the gate that let it through.

## Addendum (founder-ratified 2026-07-18, same day: "Ratified")

The one enumerated exception to "every required check green" is recorded in
the charter's scope note itself: the golden-exam verifier's designed red on
exam-harness PRs (it refuses to certify code it did not run) does not count
as red for that PR class — the adversarial review governs, per the
verifier's own prescribed path. The exception list is closed; additions are
gate-threshold relaxations and therefore founder-crucial.

Executable condition, mirrored from the charter (PR #36 r3 — the precise
mechanics live in prime directive 1; this note carries the why and the
same condition so the two never diverge):

1. The RED that the exception excuses is exactly the classifier's own
   harness-refusal output ("changes extraction HARNESS code that the
   attended exam does not execute"), emitted by
   `tools/classify_extraction_surface.py` running from the BASE branch —
   never any other failure of that check, never agent judgment.
2. The classifier partitions the refused files against HARNESS_MANIFEST
   read as data, and ELIGIBILITY keys on that partition (r4): a refusal
   is covered ONLY when proven to contain no manifest-bound file (an
   unreadable manifest = ineligible, printed by the classifier — fail
   closed). NON-manifest surface files are compensated structurally,
   TODAY: base-owned execution + per-run data bindings + the blocking
   adversarial review on that same PR.
3. MANIFEST-BOUND refusals are covered ONLY when the same PR closes
   extraction (EXTRACTION_THRESHOLD_RATIFIED = literal False, verified
   by the classifier from subject routing data): with the re-lock live,
   a certified-but-changed harness is trust_gate-red on the PR itself,
   so the closure is the only green-at-merge path — the CLOSURE moves,
   not the red. Extraction stays off, fail-closed, until the standing
   three-step re-opens it: founder's attended exam on the new harness →
   authenticated record PR → head-bound flag-flip PR. There is no
   double-red merge path, ever. Record changes riding a refusal,
   unprovable partitions, and still-ratified manifest-bound refusals
   all carry the classifier's EXCEPTION-INELIGIBLE marker, and the
   review's evidence step fails closed on it mechanically.
4. Every other red or pending check still forbids merging — this
   exception names one check's one designed failure mode, nothing more.

---

**Codified by:** `CLAUDE.md` (agent may merge on APPROVED + all-green) and `docs/HOW_WE_WORK.md` §8; the one exception is `docs/EXTRACTION_EXCEPTION.md`, decided by `tools/classify_extraction_surface.py`.
