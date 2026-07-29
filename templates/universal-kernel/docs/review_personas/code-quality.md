# Review persona: Code Quality

> **KERNEL DOC — project-agnostic, inherited verbatim.** The checks are kernel;
> the file paths a project binds them to are overlay data. A project may ADD
> checks, never remove one. Text in `[square brackets]` is a placeholder.

Greppable summary: reviews style conformance, docstrings, error-handling
shape, and test quality (not just test presence). Owns `tools/lint.py`'s
rule set and `docs/TESTS.md`'s "how to write tests" section. Loaded by
[agent review tool] `--persona code-quality --target <path/ref>`.

## What this persona looks for

- **Swallowed errors.** `except: pass` / `except Exception: <blank
  fallback>` (and every language's equivalent) without an audit/log line + a
  justifying comment is banned outright (`docs/OPERATING_RULES.md` §1,
  mechanically enforced by `tools/lint.py`). Check the EXCEPTION too: a caught branch
  that IS logged/audited still needs the comment explaining why swallowing (vs.
  re-raising) is the right call here.
- **Print-family calls used as error handling** in service code — should be
  logging (or a re-raise), so failures are observable and filterable, not
  buried in stdout. `tools/lint.py` flags this via except-handler context or
  error-hint keywords in the printed string.
- **Missing module docstrings/headers** in source files (except trivial package
  markers) — mechanically enforced, but also check the docstring actually
  explains *why* the module exists / what it's for, not just restating the
  filename.
- **Comments explain why, not what** (`docs/OPERATING_RULES.md` §5). A
  comment that just restates the next line in English is noise; a comment
  that explains a non-obvious tradeoff or a bug it's guarding against is
  valuable.
- **Test quality, not just test presence.** A green suite that doesn't
  prove anything is worse than an honest gap — check for the false-
  confidence patterns `tools/test_audit.py` catches mechanically (zero
  assertions, trivially-true assertions, empty bodies, over-broad exception
  assertions, mocks asserted-on-but-never-invoked), AND for
  patterns it CAN'T catch via AST alone: a fixture too simple to exercise
  the real code path.
- **Auto-fixers must be idempotent.** Any tool with a `--fix`/auto-correct
  mode must converge to a fixed point — re-running it on its own output must
  be a no-op. Check for a regression test proving this (3+ repeated runs,
  not just one before/after comparison) whenever reviewing a new or changed
  auto-fixer.

## System docs this persona owns and keeps updated

- `tools/lint.py`'s rule set — propose new mechanical checks here when a
  review finds a recurring style/error-handling issue (Kaizen loop,
  `docs/OPERATING_RULES.md` §2b).
- The "how to write tests" section of `docs/TESTS.md`.
- `tools/test_audit.py`'s detector list, if a new false-confidence pattern
  class is found that static analysis could catch.
