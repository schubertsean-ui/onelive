# tools/ — agent helper scripts: how to build them, and what's here

Greppable summary: every script here is stdlib-first (no hard dependency on
a package that might not be installed — mirrors why `lint.py` never
hard-depends on `ruff`), fails loudly with a specific message, exits 0 clean
/ 1 violation / 2 hard-failure, and supports `--help`. Index of every script
below; keep it current in the same commit that adds/changes a script.

## Conventions every script here follows

- **stdlib-first.** If a check can be written with `ast`/`re`/`zlib`/
  `struct`/etc. instead of a third-party package, write it that way — the
  sandbox and CI environments this runs in don't guarantee network access or
  a given package being installed. `tools/lint.py` and `tools/visual_
  regression.py` are the reference examples (the latter decodes PNGs with
  `zlib`+`struct` instead of depending on Pillow).
- **`main(argv=None)` signature.** Every script's entry point takes an
  optional `argv` list (defaulting to `sys.argv[1:]`) so tests can call
  `main([...])` directly instead of shelling out — see any `tests/test_*.py`
  file for the `importlib.util.spec_from_file_location` pattern used to
  import a `tools/*.py` module under test (needed because `tools/` isn't a
  Python package).
- **Exit codes are a contract, not a suggestion.** `0` = clean/pass, `1` =
  violations found (or, for advisory tools, only with `--strict`), `2` =
  hard failure (bad input, missing dependency, couldn't run at all — never
  the same as "0 violations found"). A tool that can't determine an answer
  must never exit 0.
- **Fail loudly, never silently degrade.** If something required is
  missing (a binary, a DSN, a file), raise/print a specific, actionable
  message naming exactly what's missing and how to fix it — never
  skip-and-pass quietly. See `tools/visual_regression.py`'s
  `capture_screenshot` for the reference pattern (names the missing binary,
  refuses to fake a screenshot).
- **`--help` via argparse**, with a one-line description that matches the
  module docstring's first line.
- **Advisory vs. blocking tools are explicit about which they are.**
  `tools/commit_sweep.py` and `tools/test_audit.py` are advisory by default
  (exit 0 even with findings) and only become blocking with `--strict` —
  this is a deliberate choice (surfacing findings shouldn't halt work by
  default until the team trusts the signal), stated in each tool's own
  `--help` text, not left ambiguous.
- **Executable + shebang for anything meant to be run directly.**
  `chmod +x` and a `#!/usr/bin/env python3` (or `#!/usr/bin/env bash`)
  shebang for scripts meant to be invoked as `tools/foo.py` / `tools/foo`
  rather than always through `python tools/foo.py`.

## Index

| Script | Purpose | Exit codes |
|---|---|---|
| `tools/trust_gate.py` | Deterministic trust-invariant CI gate: no dynamic SQL, ads/tastemaker pipeline isolation, AI-never-promotes, promote-import-allowlist | 0 clean / 1 violation |
| `tools/session_reconcile.py` | Session-start/close reconciler: verifies STATE.md's ground-truth block against live git/PRs/DB | 0 clean / 2 material contradiction or unverified |
| `tools/lint.py` | Pure-stdlib OneLive style/trust linter: swallowed errors, `print()`-for-errors, missing module docstrings, TODO/FIXME markers. `--fix` auto-fixes trailing whitespace, missing final newline, leading-import sort | 0 clean / 1 violation |
| `tools/commit_sweep.py` | Cross-commit history sweep: churn, no-test-change, migration-no-test, TODO-growth, large-commit detectors over the last N commits | 0 always (advisory) / 1 with `--strict` |
| `tools/test_audit.py` | AST scan of `tests/` for false-confidence tests (zero assertions, trivially-true assertions, `pass`-only bodies, over-broad `pytest.raises`, unused mocks) | 0 always (advisory) / 1 with `--strict` |
| `tools/profile_target.py` | Time/profile one pure-logic function by dotted `module:function` path; `--profile` for cProfile top-20 | 0 ran / 2 bad target or demo call failed |
| `tools/visual_regression.py` | Pure-stdlib PNG decode + pixel-diff engine; `compare` two PNGs or `capture-and-compare` against a named baseline | 0 match / 1 diff / 2 hard failure |
| `tools/visual_check.sh` (bash) | End-to-end visual regression (R-002): boots /tonight in SYNTHETIC QA fixture mode (deterministic data + frozen clock), screenshots with headless Chromium (pin: build 1194 = Playwright 1.56.0), pixel-diffs against `tests/visual_baselines/`; `--update` recaptures baselines | 0 clean / 1 diverged / 2 hard failure (no browser/deps/boot) |
| `tools/agent_review` (bash) | Cross-agent code-review kickoff: loads a persona doc + prints the review prompt + diff for any agent/model to consume | 0 printed / 2 persona missing or bad target |
| `tools/validate` (bash) | Single "run everything" end-of-shift entrypoint: trust_gate, lint, full pytest, eval_harness import check, perf benchmarks, test_audit, commit_sweep, in order, with a PASS/FAIL summary table | 0 all passed / 1 any check failed |
| `tools/install_hooks.sh` (bash) | Installs a real git pre-commit hook (framework-free fallback) that runs `lint.py --fix` then `trust_gate.py`, blocking the commit on failure | n/a (installer) |
| `tools/import_sources.py` | Source-catalog import for the pipeline's source registry | see script's own `--help` |
| `tools/apply_migration.py` | Applies one idempotent SQL migration file to the DB (ONELIVE_DB_DSN) in a single transaction; fails loud on error | 0 applied / 2 file missing |
| `tools/arming_runtime.py` | Computes the armed ingest-cron's true runtime file set (import closure of ingest.yml's scripts + package __init__ files + installed requirements + an explicit non-import registry) so the arming-evidence binding fires only on code the cron actually runs | 0 prints the set / 2 fail-closed on a dynamic import or a missing declared/first-party input |
| `tools/value_ledger.py` | Agent Value Ledger (founder-directed 2026-08-04): `log` appends every completed agent task (hours saved + $ value, estimate basis required) to the shared Excel workbook `docs/metrics/AGENT_VALUE_LEDGER.xlsx` (founder-editable rate in its Config sheet) and regenerates the "Weekly ROI" sheet + deterministic CSV audit mirror; `report --as-of` prints the founder-facing weekly "you saved $" summary; `verify` refuses when workbook/weekly/mirror disagree; deterministic (dates caller-supplied); needs openpyxl (`tools/requirements.txt`) | 0 ok / 1 refusal-defect (named) / 2 usage |
| `tools/kpi_report.py` | KPI scorecard for the quarterly-prioritization process (`docs/strategy/ONE_LIVE_KPI_FRAMEWORK_v1.md`): reads (never recomputes) the extraction certification record, the Kaizen ledger, the trust gate, `docs/RECORD.md`, the model router, and the Brain IQ score into one scorecard; `--append TIMESTAMP` writes a snapshot to `docs/metrics/KPI_LEDGER.md`; not-yet-instrumented KPIs render honestly, never a guessed number | 0 ok / 1 `--check` found an off-target KPI / 2 could not compute (fail loud) |

## Adding a new script

1. Follow the conventions above — especially `main(argv=None)` and stdlib-
   first.
2. Write `tests/test_<name>.py` using the `importlib.util.spec_from_file_
   location` pattern (see `tests/test_lint.py` for the template) — run it
   for real, paste the output somewhere verifiable (a commit message, a
   session arc), don't just claim it passes.
3. Add a row to the Index table above, in the same commit.
4. If it's meant to be run directly (not just via `python tools/x.py`),
   `chmod +x` it and give it a shebang.
5. If it changes what `tools/validate` should run, update `tools/validate`
   too, in the same commit — an orphaned check that never runs is dead code.
