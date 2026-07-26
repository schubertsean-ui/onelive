# Decision — the M3 escape alarm blocks on an OPEN gate gap, not on history (founder, 2026-07-26)

**Status:** RATIFIED by the founder. This is a **gate-threshold change**, which
`CLAUDE.md` reserves to the founder alone — and this one would have loosened the
gate that was blocking the agent's own PR, which is precisely why an agent may not
make it. The agent produced the evidence, recommended, and waited.

## The directive (verbatim)

> **"option a"**

Answering `docs/V1.md` ask 5, option 1: *an escape stops blocking once its
`Gate-gap closed` column names a shipped fix. Count stays 1 and stays visible; a
repeat after the fix alarms immediately.*

## What was wrong

On 2026-07-26 the project recorded its **first ever escaped defect** to the
documented `M3-ESCAPE` convention. `tools/kaizen_trends.py::escapes()` counted the
token; any non-zero count was a hard finding; `tools/validate` went red, and
`--allow-skips` deliberately does not waive it.

**An escape is permanent history — the whole point is that it is never erased. So
the gate was red forever**, on that PR and every future one. Two things follow, and
the second is the dangerous one:

1. Every future PR would have merged on `--allow-skips` or on founder authority.
   That is the R-051 pattern made routine: the last time a gate blocked with no way
   to satisfy it, a whole session's work merged with the mandatory independent
   review never having run.
2. **It created a standing incentive not to record escapes at all** — and the PR #76
   reviewer had already identified omitting the token as the fail-open. A measure
   whose honest use is punished stops being used.

## What changed, precisely

The **blocking condition** moved from *"any escape ever recorded"* to *"any escape
whose `Gate-gap closed` column names no shipped mechanism."*

**What did NOT change, and this is the part worth being able to prove:**

- The **M3 target is still 0, absolute.** Not windowed, not softened.
- The **all-time count still prints on every run** (`m3_escapes:`) and **can never
  decrease** — asserted by
  `test_the_all_time_count_can_never_be_reduced_by_closing_a_gap`.
- **An escape with no shipped mechanism still blocks forever.** Placeholder text
  (`—`, `TBD`, `pending`, `none`, `n/a`, …) does not count as a closed gap, and a
  malformed row **fails closed** — both asserted.
- A closed escape **does not excuse a later open one**
  (`test_a_closed_escape_does_not_excuse_a_later_open_one`).

## Why this shape rather than an invention

**The repo already did exactly this, one function away.**
`tools/kaizen_trends.py::family_alarm` applies the same semantics to the
repeat-class alarm — a fix marker is credit for catches at-or-before its row, and a
recurrence *after* the marker alarms immediately — and those semantics were
ratified by the independent evaluator at round 6 of an earlier PR. The M3 counter
was the one meter in that file that never received the treatment. Option (a) is
consistency, not novelty.

The precedent that cut the other way was weighed and is on the record: **M7's
one-way ratchet** ("thresholds only ever tighten"). It is not violated, because no
threshold moved — the target is still 0. What moved is which condition trips the
alarm, from one that could never be satisfied to one that can.

## The agent's own conflict of interest, stated

`validate` was red on this and PR #76 could not merge. Fixing one's own blocker is
the exact conflict the founder-crucial list exists to prevent, so the agent left
the gate untouched through several rounds of pressure and wrote
`docs/ASK_ANALYSIS_2026-07-26.md` instead. Its recommendation moved (a) → (d) → (a)
as evidence arrived and was labelled moderate confidence, not high.

## Consequence unlocked

PR #76 carries the D1 cron fix. Measured 2026-07-26T18:08Z, `origin/master` still
read the bare `github.event.inputs.limit`, so **the deterministic feed could not
refresh unattended until this PR merged.** This decision was therefore not only
about a gate — it was the thing standing between the fix and production (R-054).

---

**Codified by:** `tools/kaizen_trends.py::open_escapes` (+ the `m3_escapes_open`
report line), the matching `_kpi_escaped_defects` change in `tools/kpi_report.py`,
and 8 new tests in `tests/test_kaizen_trends.py` covering open/closed/mixed,
placeholder text, malformed rows and the never-decreasing count. Declared as a gate
change in `tests/test_health_check.py`'s gate-file assertion, with its authority
named.
