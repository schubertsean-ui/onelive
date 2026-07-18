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

### 2026-07-12 — the founding anti-pattern was living inside the enforcement gate

**Session:** cross-model review of PR #8 (agentic-harness buildout), fix, merge
to master, and live-state reconcile.

**Friction:** A cross-model review (GPT-5.5, security + domain-truth-and-trust
personas) of the harness found that `tools/validate` — the gate whose entire
job is to enforce §1 "couldn't verify must not look like passed" — itself
printed `RESULT: PASS` + exit 0 when checks were SKIPPED or advisory. The single
most important quality invariant in the project was violated by the tool meant
to guarantee it. It shipped that way because the author (Claude) and the gate
were never reviewed by a different model before landing.

**Root cause:** self-review blind spot. The buildout was large, internally
consistent, and written in one voice, so the "skip is loud but still green"
compromise looked reasonable in isolation. It took an adversarial second model,
pointed explicitly at the trust persona, to name it as the founding
anti-pattern. Also: PR #8 sat as an unreviewed parallel branch — the process gap
was that harness tooling was allowed to accumulate without the same
cross-model + merge discipline applied to product code.

**Fix applied this session:** `validate` now distinguishes RUN+PASS from
SKIP/ADVISORY: the latter yield `RESULT: INCOMPLETE` + exit 2 unless a human
explicitly acknowledges with `--allow-skips`. Same "unverified is not a pass"
correction applied to `commit_sweep.py` (empty range => exit 2) and
`test_audit.py` (docstring/detector brought into lockstep on patch()-mocks).
Plus the `visual_regression` shell-injection P1 and three other P2s. All with
regression tests; suite 120 -> 127 passing. Merged as `a0b3724`.

**Suggested follow-up:** apply the same cross-model review + merge discipline to
the two still-open PRs (#4, #7) BEFORE they land, not after. And treat harness
tooling as production code for review purposes — it enforces the rules, so a bug
in it is a rules bug. Separately: "OneLive live" is blocked on unpushed
old-sandbox commits (Clerk gate + Next 15) and unmerged #7 (orchestrator) — see
`LIVE_READINESS.md`; the sandbox-portability of in-progress work is a recurring
friction worth solving (push WIP branches early, don't let commits live only on
one sandbox).

## 2026-07-13 — Genesis install + Session Contract #1 (Claude Code, remote sandbox)

**What slowed the session down:**
1. **The sandbox can't run the reconciler's PR/DB legs** — no `gh`, no DSN, no
   Supabase connector. PR state was recovered via the GitHub API tools, but the
   GROUND_TRUTH block stayed stale and had to be flagged in prose instead of
   healed. Follow-up: teach `session_reconcile.py` to fall back to the GitHub
   REST API with a plain token (it already prints the SQL fallback for DB).
2. **Root-privileged test env broke a permissions-based test**
   (`test_fails_loud_on_unwritable_dir`) — chmod can't make a dir unwritable
   for root. Fixed with skipif(euid==0); worth remembering for any future
   permission-denied test.
3. **`next build` needs a Clerk publishable key even for a stealth-gated app**
   (prerender of /ops) — pre-existing, cost a baseline-attribution rebuild.
   Either commit a documented dummy key for CI builds or make /ops
   force-dynamic; decide next web session.
4. **Genesis Step 0's "overwrite CLAUDE.md, preserve in a comment block"
   conflicted with the live repo charter** — resolved by keeping both active
   (arc decision #1). Doc-bundle instructions written off-repo should say
   "merge" when the target file is itself a controlling doc.

**What to automate next:** the outbound proxy blocks the run_once smoke fetch
(httpbin 403) — swap the smoke URL for an allowlisted/static target or a local
fixture server so the offline smoke path stays meaningful in restricted
sandboxes.

## 2026-07-15 — marathon founder session (PRs #14–#22)
- FRICTION: no webhook fires on CI SUCCESS, and self-scheduled check-ins are blocked in this environment — every green verdict needed either a founder ping or a lucky poll. Automate next: a success-notification path (or permit send_later).
- FRICTION: GitHub MCP token expired mid-session once (founder had to reconnect); plan for auth interruptions in long sessions.
- WORKED WELL: the evaluator enforcing KAIZEN §M7 against its own author's PR within hours of merging it — the loop is genuinely self-policing. M1 rounds-to-green trend 5→1 across the arc.
- WORKED WELL: founder-ergonomics investment (DSN splice) directly unblocked a stuck human step; worth repeating the pattern (make the machine absorb the fiddly part).
- WATCH: empty-env fail-open class hit its 4th appearance (#21). Ledger rule says the 5th demands the structural fix (env-contract linter for workflows) — do not patch a 5th time.

## 2026-07-17 — MemoHarness paper review session
- FRICTION: the sandbox network policy blocks arxiv.org (and mirrors: Hugging Face papers, Semantic Scholar) — a founder-supplied research link produced four dead-end fetch attempts before the founder had to upload the PDF by hand. Automate next: allowlist arxiv.org (read-only research domain) in the environment's network settings, or note in the charter that papers reach the agent as uploads.
- FRICTION: `Read` on the uploaded PDF failed until poppler-utils was apt-installed (and the first install 404'd until `apt-get update`). Worth adding poppler-utils to the environment's base image/setup script if paper review recurs.
- WORKED WELL: the standing decision records did their exact job — the 2026-07-14 gate-custody note and the 2026-07-16 Weco AIDE² TODO item let this session classify MemoHarness's outer-loop search as already-adjudicated in minutes, instead of re-litigating the safety question from scratch. Disk beat chat memory, again.
- FRICTION (REPEAT — 2nd occurrence, first 2026-07-15): self-scheduled check-ins (send_later) approval-blocked in this environment; armed-timer request from the founder could not be executed by the agent alone. Structural fix queued in TODOS (pre-approve scheduling MCP in environment settings). Per the repeat-class rule a third occurrence without the fix is a process defect, not friction.
- DEFECT (founder-caught, ledgered 2026-07-18): reported the visual_regression skip without citing R-002 — recorded debt presented as ad-hoc excuse. Class: skip-report-missing-record-citation. Prose rule added to SESSION_START close step 3; mechanical binding in tools/validate queued P2. Meta-lesson: a Red-hat (founder) catch means self-review, the evaluator, and the gate all passed it — treat any founder catch as a gate-gap signal by default, not just a correction.
