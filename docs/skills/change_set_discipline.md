# Change-Set Discipline — sizing and freezing what review can actually review

Greppable summary: founder-directed 2026-07-26 after the SAME failure occurred
twice — PR #68 ran 22 review rounds without converging and was diagnosed as
"too large, split it"; PR #74 then reproduced it exactly, at 11 rounds AND
COUNTING when this was written — the number is a floor, not a total, because
the PR was still running. A round count quoted as final is retyped evidence.
The
lesson had been written as PROSE both times and never as a gate rule, which the
Construction Loop (Stage 6) already names as an open defect: *"lessons committed
to brain only in machine-consumed form — a prose-only ledger row is an open
defect."* This file is the machine-consumed form. Mechanism:
`tools/change_set_gate.py`, blocking, in `tools/validate`.

STATUS: ADOPTED 2026-07-26 at founder direction ("Research and evaluate the
world class methods for handling this… Codify your findings… It seems to me we
have previously addressed this and you either ignored it or didn't commit to
the canon"). Thresholds are gate thresholds: raising them is founder-crucial.

---

## 1. What the evidence says

Review effectiveness has a measured ceiling. It is not a function of how hard
the reviewer tries.

| Source | Finding |
|---|---|
| [Sadowski et al., *Modern Code Review: A Case Study at Google*, ICSE-SEIP 2018](https://sback.it/publications/icse2018seip.pdf) | Median change ≈ **24 lines**; ~90% of changes touch **fewer than 10 files**. Small changes are the mechanism Google's review speed and efficacy rest on, not a byproduct. |
| SmartBear/Cisco review study (widely replicated) | Defect-detection rate falls sharply beyond ~**400 lines** in a sitting, and beyond ~60 minutes of continuous review. |
| [DORA — *Working in small batches*](https://dora.dev/capabilities/working-in-small-batches/) and [*Trunk-based development*](https://dora.dev/capabilities/trunk-based-development/) | Small batch size and short-lived branches are among the strongest predictors of delivery performance; recommends ≤3 active branches and merging to trunk at least daily. |
| Reinertsen, *The Principles of Product Development Flow* | Batch size drives cycle time and queue cost (Little's Law); large batches raise **variance** as well as delay. Automated testing lowers transaction cost, which is what *permits* small batches — it does not excuse large ones. |

**Our own measurement, PR #74:** 8,708 changed lines across 36 files — roughly
**twenty times** the point at which defect detection is known to collapse.

---

## 2. The mechanism that actually bit us — scope growth under review

Size alone was not the whole story, and this is the part no external study
would have told us. **PR #74 grew while it was being reviewed:**

| Point in review | Files | Lines |
|---|---:|---:|
| ~round 1 | 20 | 2,918 |
| ~round 5 | 31 | 6,974 |
| round 11 | 36 | 8,708 |

Consequences, all observed:

1. **Each round reviewed a larger subject than the last**, so the finding rate
   had no reason to fall. Counting rounds was useless: the residual was not
   shrinking because it was not the same problem.
2. **Fixes created the next round's blockers.** Round 10's premise-by-address
   correction made the denominator premise-accurate while the matcher still
   keyed on name — round 11 found the resulting overstatement. An anti-stale
   banner added at round 9 hardcoded a number and went stale at round 10.
3. **Every addition felt urgent and was individually defensible.** "The founder
   needs the venue number now" was true every single time. That is exactly the
   condition under which a new branch costs least and feels most expensive.

**Rule: a change under review does not grow.** Adopting a reviewer's blocker is
in scope. New work is not, however urgent — it goes to a new branch.

---

## 3. The rules (mechanically enforced)

`tools/change_set_gate.py`, blocking in `tools/validate`.

| # | Rule | Limit | Why this number |
|---|---|---|---|
| **C1** | Reviewable lines — advisory | > 400 → WARN | the measured degradation point |
| **C2** | Reviewable lines — hard | > 1500 → **FAIL** | ~4× the evidence threshold; deliberately above it because a change here legitimately carries its tests and Record entry |
| **C3** | Reviewable files — hard | > 25 → **FAIL** | ~2.5× Google's 90th percentile |
| **C4** | **Scope freeze** | > +600 lines or +6 files after `--freeze` → **FAIL** | the failure above; tolerance allows blocker adoption, not new work |

"Reviewable" excludes generated artifacts and lockfiles — a reviewer does not
read `capcog_venue_targets.json` line by line. The exclusion list is explicit in
the tool so it cannot quietly grow to swallow real code.

**Workflow:**

```bash
python tools/change_set_gate.py --freeze     # when the PR first goes for review
python tools/change_set_gate.py              # runs inside tools/validate thereafter
```

---

## 4. The convergence test — when to stop and split

Round count is the wrong instrument; it measures effort, not progress. The right
question is whether the **residual is shrinking**.

**SPLIT when any of these is true:**

- **C5 — Non-decreasing blockers.** Blocker count fails to strictly decrease
  across two consecutive rounds on an unchanged scope.
- **C6 — Self-generated findings.** A round's blockers are located in code added
  during a previous round of the same review. This is the definitive signal: the
  change is chasing its own tail.
- **C7 — Round ceiling.** Five rounds. Not a suggestion — an escalation to the
  founder with a split proposal, which is a *decision request*, not a status
  update.

Observed: #68 blockers went 2 → 5 → 2 → 2 → 1 → 6 (C5 fired by round 3, and the
spiral ran to round 22). #74 hit C6 twice at rounds 10 and 11.

---

## 5. One PR, one reversible decision

A change should be describable in a single sentence with no "and". PR #74's
honest sentence was: *"CAPCOG boundary **and** the venue denominator **and** the
source registry **and** the scorecard **and** web discovery **and** reviewer
concurrency."* Six decisions, each with its own failure surface, sharing one
review.

The test is not "are these related?" — everything in a codebase is related. It
is **"could a reviewer approve one and reject another?"** If yes, they are
separate changes.

---

## 6. Why this failed to stick the first two times

Recorded because the meta-failure is the more expensive one.

- The lesson was written as a **recommendation to the founder** and as **prose in
  a plan document**. Both are read by humans, at most once, and neither blocks
  anything.
- The Construction Loop already mandated *small-batch execution* (Stage 5) and
  *machine-consumed lessons* (Stage 6). **The canon was right and was not
  followed** — a rule that is not mechanically checked is a rule that competes
  with whatever feels urgent at the time, and urgency wins.
- `tools/construction_gate.py` existed, ran in `validate`, and contained **no
  size or scope check at all**. The enforcement mechanism had a hole exactly
  where this defect lives.

**Generalisation worth keeping:** when a lesson is written down and the same
failure recurs, the defect is not the recurrence — it is that the lesson was
written in a form nothing executes. Ask of every retro: *what will now fail?*
If the answer is "nothing, but we'll remember", it is not codified.

## Why the scope freeze is ADVISORY (2026-07-26, after four review rounds)

The CEILING blocks: 1500 reviewable lines, 25 files. It earned that on its
first CI run, by condemning its own 4,009-line PR.

The FREEZE reports. Rounds 1-4 of PR #79 each found a real fail-open in the
previous round's attempt to harden it — a resettable baseline, a prefix
starting at the wrong place, a deletable record, paths that could hide behind
unparseable output, a missing review epoch. Every finding was correct, and
every fix was worth making. But they share one premise: that a file the author
controls can be made tamper-proof against that author. It cannot, and a force
push defeats the whole chain regardless.

So the freeze does what it is genuinely good at — telling a reviewer that the
subject of their review changed size under them, which is the signal that made
PR #68 undiagnosable at 22 rounds. Loud detection, no enforcement claim.

Claiming more than a mechanism can deliver is the false-confidence-gate class,
and this file has been cited for exactly that twice. Choosing detection over a
guarantee we cannot honour is not a relaxed threshold; it is the threshold
being stated truthfully. The blocking ceiling is unchanged and raising it is
still founder-crucial.
