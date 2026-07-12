# AGENT_FEEDBACK — session-end friction log, ingested periodically

Append-only log of honest agent feedback from real sessions: what was slow,
confusing, or broke, and what would have prevented it. Reviewed periodically
(weekly Kaizen loop, `docs/OPERATING_RULES.md` §2b) to turn recurring friction
into a rule, test, lint check, or doc fix — never left to just accumulate.

## How this is used

1. **Append at session close** (see `docs/SESSION_START.md` session-close
   steps) — one entry per session that hit real friction, using the template
   below. Skip it only if the session was genuinely frictionless; don't pad it.
2. **Ingested in the weekly Kaizen loop** — scan entries since the last pass,
   look for repeats (the same friction hitting 2+ sessions is a signal, not a
   coincidence), and for each repeat: encode a guard (rule/test/lint) so it
   can't recur silently, per OPERATING_RULES §2b.
3. **Entries are not deleted** once acted on — mark them `[RESOLVED: <link to
   the fix>]` so the history of what was learned stays intact.

## Entry template

```
### YYYY-MM-DD — <short title>
**Session:** <branch/PR/task link>
**Friction:** <what was slow, confusing, ambiguous, or broke>
**Root cause:** <why, not just what>
**Fix applied this session (if any):** <what you changed, with a link/commit>
**Suggested follow-up (if not fixed here):** <concrete next step, not "investigate more">
```

---

### 2026-07-12 — `--fix` non-idempotency silently baked bloat into two commits before being caught

**Session:** `feat/agentic-harness-buildout`, building `tools/lint.py` (item 5)
and `tools/commit_sweep.py` (item 10).

**Friction:** `tools/lint.py --fix`'s import-block sorter was not idempotent —
each run added one more blank line after the sorted import block than the
last run. Because `tools/install_hooks.sh`'s pre-commit hook auto-runs
`lint.py --fix` on every commit, this had *already* landed in two real local
commits before I noticed (blank-line counts silently crept up to 8-10
consecutive blank lines in several files). I only caught it because I
happened to re-run `--fix` a third time out of caution and saw the file
still reported as "changed" — a single run looked completely clean.

**Root cause:** `_sort_leading_imports` computed how many blank lines to
re-append after the sorted block as `len(block) - len(import_lines)` — a
count that included blank *separator* lines already sitting between import
groups from the *previous* run, then added a new separator per group boundary
on top of that recycled count. Classic "count something that isn't reset
between runs" bug. The test I wrote for this (`test_fix_is_noop_on_already_
clean_file`) used a trivial single-group synthetic fixture that never
exercised the multi-group-separator path where the bug actually lived — so a
green test suite gave real false confidence here (the exact failure mode
`tools/test_audit.py`, built later this same session, now exists to catch).

**Fix applied this session:** rewrote the separator logic to rebuild blank
lines from scratch every run (one between non-empty groups, one trailing iff
something follows) instead of carrying forward a count from the block being
replaced; separately found and fixed a second real bug this exposed — the
generated pre-commit hook's `git diff | grep | xargs git add` pipeline under
`set -euo pipefail` aborted the whole commit whenever `grep` found zero
matches (the common, already-clean case) — fixed with `{ grep ... || true; }`.
Added two regression tests
(`test_fix_import_sort_is_idempotent`,
`test_fix_import_sort_no_blank_line_growth_across_many_files`) that call
`apply_fixes` 3+ times in a row and assert convergence to a fixed point,
specifically to prevent this class of bug from passing review again on a
too-simple fixture. See commit `57b3ece` on this branch for the full fix +
root-cause writeup in the commit message.

**Suggested follow-up:** none outstanding — `tools/test_audit.py` (item 14,
built later this session) now flags any *future* test this shallow (zero
assertions, trivially-true assertions, or a fixture too simple to exercise
the real code path would still slip past AST-level detection, so human
review of new regression tests for auto-fixers specifically should still
double-check they use a realistic multi-group/multi-file fixture, not just a
single trivial one).

### 2026-07-11 — cost/model-routing (Loop step 17) has no home in the harness yet

**Session:** `feat/agentic-harness-buildout`, closing pass (assessment vs. the
20-step Loop Engineering roadmap + controlling-doc wiring).

**Friction:** Assessing OneLive against the Loop Engineering roadmap surfaced one
world-class gap the buildout could NOT close with existing structure: step 17
(route each loop step to the cheapest capable model; reuse stable prompt
prefixes). There was no doc or helper to point the routing rule at, so it lives
only as prose in `docs/skills/night_shift.md` §4 with an explicit "apply by
judgment until a router exists" caveat. That is a documented gap, not a silent
one — but it is judgment where the rest of the harness is mechanical.

**Root cause:** the harness matured verifier-first (trust_gate, validate,
test_audit) and state-first (STATE.md, reconcile, arcs). Cost was never a
first-class concern because most work has been interactive/human-paced, where the
model choice is made by the operator, not the loop. The moment a real scheduled
runner exists (step 19), un-routed model selection becomes a live cost risk.

**Fix applied this session:** none (out of scope for a doc/harness buildout;
routing needs a small runtime helper + a policy doc, and ideally hooks into the
actual model-call sites which are currently the CI Claude actions + interactive
sessions, not a central call path).

**Suggested follow-up:** add `docs/MODEL_ROUTING.md` (policy: which stage → which
tier, with the reasoning) + a `tools/` helper that resolves a stage label to a
model id, and wire it into any future scheduled runner and the CI actions
(currently hardcoded `claude-sonnet-4-6`). Tracked as TODOS.md item + arc
`2026-07-11_agentic-harness-buildout.md` open thread #1.
