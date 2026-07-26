# tools/ — the portable agent harness: what ships here, and what a project must add

Greppable summary: every script here is stdlib-first (no hard dependency on a
package that might not be installed), fails loudly with a specific message,
exits `0` clean / `1` violation / `2` hard-failure / `3` advisory-findings, and
supports `--help`. Nothing here knows anything about a particular product —
project-specific gates are added by the project (see the last section). Keep
the index current in the same commit that adds or changes a script.

## Conventions every script here follows

- **stdlib-first.** If a check can be written with `ast`/`re`/`subprocess`
  instead of a third-party package, write it that way — the sandbox and CI
  environments this runs in don't guarantee network access or a given package
  being installed.
- **`main(argv=None)` signature.** Every script's entry point takes an optional
  `argv` list so tests can call `main([...])` directly instead of shelling out.
- **Exit codes are a contract, not a suggestion.** `0` = clean/pass, `1` =
  violations found, `2` = hard failure (bad input, missing dependency, couldn't
  run at all — never the same as "0 violations found"), `3` = findings from an
  advisory tool (distinguishable from clean without parsing stdout). A tool
  that can't determine an answer must never exit 0.
- **Fail loudly, never silently degrade.** If something required is missing (a
  binary, a DSN, a file), print a specific, actionable message naming exactly
  what's missing and how to fix it — never skip-and-pass quietly.
- **`--help` via argparse**, with a one-line description matching the module
  docstring's first line.
- **Advisory vs. blocking tools are explicit about which they are**, in their
  own `--help` text, never left ambiguous.

## Index

| Script | Purpose | Exit codes |
|---|---|---|
| `tools/validate` (bash) | The single "run everything" end-of-shift entrypoint: runs the project's own checks from `tools/project_checks.d/` first, then lint, deferral_scan, full pytest, test_audit, commit_sweep, kaizen_trends; binds every SKIP to an OPEN `docs/RECORD.md` row and emits a machine-generated evidence block | 0 all passed (or skips acknowledged with `--allow-skips`) / 1 any check failed / 2 INCOMPLETE (a SKIP or advisory finding, unacknowledged) |
| `tools/validate_bind_skips.sh` (bash) | Sourced by `validate`: turns any environmental SKIP with no OPEN Record row into a FAIL. Structured `QSKIP` status exempts `--quick` skips (never note text) | n/a (sourced function) |
| `tools/skip_record_binding.py` | Answers one question mechanically: does an OPEN `docs/RECORD.md` row name this check as a backticked token? Prints the row id | 0 bound / 1 no OPEN row / 2 register unreadable |
| `tools/lint.py` | Pure-stdlib style/trust linter: swallowed errors, `print()`-for-errors in service code, missing module docstrings, TODO/FIXME/XXX markers. `--fix` auto-fixes trailing whitespace, missing final newline, leading-import sort | 0 clean / 1 violation |
| `tools/deferral_scan.py` | Mechanical arm of the no-silent-deferrals rule: every deferral-language code comment must carry an `[R-###]` tag pointing at an OPEN `docs/RECORD.md` row (dangling or resolved tags also fail) | 0 clean / 1 violations / 2 register missing or unparseable |
| `tools/test_audit.py` | AST scan of `tests/` for false-confidence tests (zero assertions, trivially-true assertions, `pass`-only bodies, over-broad `pytest.raises`, mocks asserted-on but never invoked) | 0 clean / 3 findings (advisory) / 1 with `--strict` |
| `tools/commit_sweep.py` | Cross-commit history sweep: churn, code-without-test-change, migration-without-test, TODO growth, oversized commits over the last N commits | 0 clean / 3 findings (advisory) / 1 with `--strict` / 2 empty range (unverified) |
| `tools/kaizen_trends.py` | Computes the Kaizen trend report from `docs/metrics/KAIZEN_LEDGER.md`: M3 escapes (must be 0), repeat-class alarms, rounds-to-green direction, founder catches, catches per gate | 0 clean / 1 findings / 2 ledger missing or unparseable |
| `tools/session_reconcile.py` | Session-start/close reconciler: verifies STATE.md's machine-readable ground-truth block against live git / PRs / DB, auto-heals benign drift, hard-stops on material contradiction | 0 clean or benign drift / 2 material contradiction or unverified critical fact / 3 usage error |
| `tools/adversarial_review.py` | Independent non-Claude review gate: posts the raw diff + test logs to the OpenAI API and demands a final `VERDICT: APPROVE` / `VERDICT: REQUEST-CHANGES`; ambiguity is a hard failure, and a Claude/Anthropic reviewer id is rejected outright | 0 APPROVE (or explicit no-key skip without `--require`) / 1 REQUEST-CHANGES / 2 hard failure |
| `tools/model_router.py` | Resolves a loop-stage label (`mechanical`/`standard`/`critical`/`extraction`/`evaluator`) to the cheapest-capable model id; per-stage env override `KERNEL_MODEL_<STAGE>`; evaluator stage refuses generator-family models | 0 resolved / 2 unknown stage, bad override, or a fail-closed stage |
| `tools/routing_data.py` | PURE DATA: the stage→model table plus `EXTRACTION_THRESHOLD_RATIFIED` (shipped `False` — fail-closed until a project's own exam certifies the stage) | n/a (data module) |
| `tools/po_battery.py` | Prints the full de Bono po provocation battery for a target statement (all operators + random-entry combos + movement techniques); seedable for tests | 0 printed / 2 empty statement |
| `tools/install_hooks.sh` (bash) | Installs a framework-free git pre-commit hook: `lint.py --fix`, then the project's trust gate if one is registered (loud banner if none), re-staging what `--fix` touched | n/a (installer) |

## Environment variables this harness reads

Project-owned names use the `KERNEL_` prefix; vendor names keep their vendor
spelling.

| Var | Used by | Meaning |
|---|---|---|
| `KERNEL_DB_DSN` | `session_reconcile.py` | DSN for direct DB ground-truth queries. Unset = those facts are UNVERIFIED (loud), never assumed clean |
| `KERNEL_CORE_TABLES` | `session_reconcile.py` | Comma-separated tables whose row counts are load-bearing. Unset = the question is not asked |
| `KERNEL_MIGRATIONS_TABLE` | `session_reconcile.py` | `schema.table` of the migrations ledger, e.g. `supabase_migrations.schema_migrations` |
| `KERNEL_MODEL_<STAGE>` | `model_router.py` | Per-stage model override. Present-but-empty is a hard failure, never "default" |
| `KERNEL_CLAUDE_MODEL` | `model_router.py` | Legacy override for the `extraction` stage |
| `KERNEL_TRUST_GATE_CMD` | `install_hooks.sh` | Shell command that runs the project's trust gate, if it isn't `tools/trust_gate.py` |
| `OPENAI_API_KEY`, `OPENAI_REVIEW_MODEL`, `OPENAI_BASE_URL` | `adversarial_review.py`, `model_router.py` | Vendor names, unchanged. Present-but-empty values hard-fail |
| `PYTHON` | `validate` | Python interpreter to use (default `python3`) |

## What a project must add

The kernel deliberately ships **no** product knowledge. A project is not
verified until it supplies these:

1. **`tools/project_checks.d/*.sh` — its own checks.** Every executable `*.sh`
   in that directory is discovered and run by `tools/validate` **first**, and
   the script's **exit code is its verdict** (0 = PASS, anything else = FAIL).
   This is where a project's trust-invariant gate, schema/RLS checks, perf
   budgets, visual-regression run, eval-harness thresholds, and second-language
   linters belong. Rules the runner enforces:
   - If the directory is absent or holds no `*.sh`, validate prints a LOUD
     SKIP banner and records a `project_checks` SKIP — which then **must** be
     bound to an OPEN `docs/RECORD.md` row naming `` `project_checks` `` or it
     becomes a FAIL. A repo with zero project checks can never report GREEN.
   - A `*.sh` that is present but **not executable** is a hard FAIL: an inert
     check is false coverage, not a skip.
   - `--quick` never skips project checks. Trust invariants are not a speed knob.
2. **Its own trust-invariant gate.** Write the invariants down in `CLAUDE.md` /
   `OVERLAY.md` (the adversarial reviewer is instructed to read exactly those
   files), then make them *mechanical* in `tools/trust_gate.py` (or any command
   named by `KERNEL_TRUST_GATE_CMD`), and register it in `project_checks.d/`.
   Prose invariants that no script can fail are not invariants.
3. **`docs/RECORD.md`** — the deferral register, a Markdown table of
   `| R-### | … | STATUS |` rows. `deferral_scan.py`, `skip_record_binding.py`
   and `validate` all fail closed without it.
4. **`docs/metrics/KAIZEN_LEDGER.md`** — a `## PR rows` table of 7-column rows
   (`date | pr | m1 | m2 | m4 | m5 | notes`). `kaizen_trends.py` exits 2 without it.
5. **`STATE.md`** with a `<!-- GROUND_TRUTH:BEGIN -->` … `<!-- GROUND_TRUTH:END -->`
   fenced JSON block for `session_reconcile.py` (it creates the block if absent).
6. **`tests/`** with real tests. `test_audit.py` treats an empty or missing
   tests directory as a loud misconfiguration (exit 1), not a clean pass.
7. **`docs/MODEL_ROUTING.md`** if it changes `routing_data.py` — the table
   implements the doc, not the other way around.

## Adding a new script

1. Follow the conventions above — especially `main(argv=None)` and stdlib-first.
2. Write `tests/test_<name>.py` using the
   `importlib.util.spec_from_file_location` pattern — run it for real, paste the
   output somewhere verifiable (a commit message, a session arc), don't just
   claim it passes.
3. Add a row to the Index table above, in the same commit.
4. If it's meant to be run directly, `chmod +x` it and give it a shebang.
5. If it changes what `tools/validate` should run, update `tools/validate` too,
   in the same commit — an orphaned check that never runs is dead code.
