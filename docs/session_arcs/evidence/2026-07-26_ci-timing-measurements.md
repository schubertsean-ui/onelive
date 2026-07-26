# CI + performance measurements — commands and their verbatim output

Created at #73 r9, after the OpenAI absence-only lens found TEN instances of
`unverified-claim-as-fact` in the very commit that codified the proof-or-label
rule: I shipped performance numbers with no commands behind them, in a diff
whose own new canon says "a number never appears without the command that
produced it". This file is the proof object those claims must cite.

Every number below was produced by the command shown, on this branch. Nothing
here is retyped from memory. Where a previously-stated number turned out to be
wrong, the correction is stated rather than quietly replaced.

---

## 1. Test suite: 49.73s → 27.83s

CONTROLLED measurement — the pre-change `tools/kaizen_trends.py` and
`tests/test_kpi_report.py` restored from commit `077dfd0`, suite run, then the
current versions restored and the suite run again, same machine, same session,
`-p no:randomly` to remove ordering variance:

```
$ git show 077dfd0:tools/kaizen_trends.py > tools/kaizen_trends.py
$ git show 077dfd0:tests/test_kpi_report.py > tests/test_kpi_report.py
$ time python -m pytest -q -p no:randomly
1689 passed, 30 skipped, 1 warning in 49.73s
real    0m50.188s

# current versions restored
$ time python -m pytest -q -p no:randomly
1690 passed, 30 skipped, 1 warning in 27.83s
real    0m28.375s
```

**CORRECTION.** Earlier commits and reports in this arc said "57s → 30s".
That figure was taken from an ad-hoc run earlier in the session against a
different tree state, not from a controlled before/after. The measured
numbers are **49.73s → 27.83s** (1689 vs 1690 tests — the current tree has
one more test, so the comparison slightly UNDER-states the gain). Every
statement of this number is corrected to the measured pair.

## 2. Where the suite time actually went — 106,476 redundant regex scans

```
$ python -c "
import cProfile,pstats,io as _io
import tools.kpi_report as k
pr=cProfile.Profile(); pr.enable(); k._kpi_repeat_class_alarms(); pr.disable()
s=_io.StringIO(); pstats.Stats(pr,stream=s).sort_stats('cumulative').print_stats(6); print(s.getvalue())"

         410636 function calls (410588 primitive calls) in 3.885 seconds
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.000    0.000    3.885    3.885 tools/kpi_report.py:228(_kpi_repeat_class_alarms)
        1    0.001    0.001    3.884    3.884 tools/kaizen_trends.py:250(build_report)
      296    0.005    0.000    3.789    0.013 tools/kaizen_trends.py:172(family_alarm)
   106476    3.410    0.000    3.410    0.000 {method 'findall' of 're.Pattern' objects}
      296    0.061    0.000    2.724    0.009 tools/kaizen_trends.py:158(family_row_counts)
      278    0.269    0.001    1.056    0.004 tools/kaizen_trends.py:146(family_marker_last_row)
```

296 families × ~200 rows × 2 cells = 106,476 `findall` calls, 3.410s of a
3.885s report. That is the source of the "~300 families / ~200 rows / 106k
scans / 3.4s of a 3.9s report" figures in `tools/kaizen_trends.py`.

## 3. The memoization changes NOTHING about the output — byte-identical

Both copies loaded into one process and compared directly, rather than
inferring safety from "the tests still pass":

```
$ git show HEAD:tools/kaizen_trends.py > /tmp/kt_old.py   # pre-change copy
$ python - <<'EOF'
  ... loads both modules, runs build_report(text) on the real ledger ...
EOF
report identical: True
findings identical: True
old 3.731s -> new 0.087s  (43x)
findings: 0
```

## 4. CI job wall clock: 489s → 418s measured, and what remains

From the GitHub Actions API (`list_workflow_jobs`), job `adversarial-review`:

| Step | run 30187255366 (baseline) | run 30212687096 (after) |
|---|---|---|
| Set up job + checkout + setup-python | 3s | 8s |
| Install worker + api deps | 10s | 8s |
| Test suite (standalone) | 45s | **step removed** |
| Full validate gate | 96s | 64s |
| Extract diff / web checks | 0s | 1s |
| **Attach the golden-exam check's log** | **124s** | **125s** |
| Preflight | 0s | 1s |
| Independent evaluator | 207s | 207s |
| Post steps + complete | 1s | 0s |
| **JOB TOTAL** | **489s** | **418s** |

Measured delta: **−71s**.

**RETRACTED CLAIM.** "Roughly 8 minutes → 90 seconds per round" was stated
earlier in this arc as though measured. It was a decomposition, never a
measurement. The 8-minute BASELINE is confirmed (489s). The 90-second target
is **not reachable** by the work in this PR: the golden-exam log attach
(125s) and validate (64s) alone floor a round near 190s before the evaluator
step is counted at all.

**UNVERIFIED, labelled as such:** if the four lenses parallelise to roughly
the slowest single call, the 207s evaluator step should fall to ~60s, putting
a round near 280s (~4m40s). No measurement supports that yet and none can
until this merges, because CI runs the reviewer from the BASE ref. The
figure stays unknown until a merged run produces it.

The 125s golden-exam attach is the largest remaining cost and was NOT among
the four items originally diagnosed. Recorded as **R-055** with an objective
trigger; founder chose a dedicated PR after #73 merges.

## 5. `shutdown(wait=False)` does NOT make the process exit fast

The r9 attacker-smuggle finding, verified rather than reasoned about:

```
$ python threadprobe.py     # worker sleeps 6s; first error raises immediately
run_panel-equivalent raised at t=0.00s
PROCESS_EXIT_AT=0.00
TOTAL PROCESS WALL CLOCK: 6.071353108s
```

The raise is immediate; the PROCESS takes the full 6.07s, because
`concurrent.futures` registers its non-daemon workers with an atexit hook
that joins them. So the honest guarantee is **verdict immediate, process exit
bounded by the per-request timeout (300s)** — not "exits immediately", which
is what the code comment claimed before this measurement. Pinned by
`test_the_PROCESS_exit_bound_is_the_request_timeout_not_zero`.

## 6. The two gate mechanisms rejected by measuring first

**Prose claim-scanner** (would have required a proof token near every
claim-shaped line in agent-authored records):

```
added record lines : 79
  claim-shaped     : 55
  WITHOUT any proof token (would fire): 36
```

65% of claim lines would fire. Rejected — a gate that noisy gets weakened.

**Prose deferral-scanner** (extending `tools/deferral_scan.py` over STATE.md
and TODOS.md): 7 lines would fire, of which 6 are false positives — a session
contract title, the phrase "is not revisited here", and historical references
to resolved decisions. The single true positive is now `R-054`.

## 7. Duplicate suite execution removed

```
$ git show origin/claude/onelife-meta-carousel-wu7sh7:.github/workflows/adversarial-review.yml \
    | grep -c 'python -m pytest'
0
```

Three suite runs per PR became two. The remaining second run is in
`trust-gate.yml` and is KEPT deliberately: a separate workflow on a separate
trigger is independent verification, not duplication.
