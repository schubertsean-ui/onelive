# TESTS — inventory + how to write tests here

> **KERNEL DOC — project-agnostic, inherited verbatim.** The "how to write tests"
> rules below are kernel. The INVENTORY table is project data and starts empty —
> the project fills it and keeps it accurate. Text in `[square brackets]` is a
> placeholder the overlay must bind.

Greppable summary: the test inventory plus the house rules for writing tests that
can actually fail. Run `tools/test_audit.py` before trusting any new test — it catches
tests that pass without proving anything. The table below is kept accurate to the
real test directory; update it in the same commit whenever a test file is added or
a test count changes. A stale inventory is doc drift, which is a review finding.

## How to run

```bash
[test runner]                      # default: fast, hermetic tests only
[test runner] -m <integration>     # opt-in: needs a live datastore (see test config)
[test runner] -m perf -v           # opt-in perf budgets
[test runner] -m visual -v         # opt-in visual-regression compare/decode tests
`tools/test_audit.py`                  # false-confidence audit of the test suite itself
```

## Test inventory

Keep this table generated-or-checked against reality, never hand-guessed. One row
per test file; totals stated with how they were counted.

| File | Tests | What it tests | Markers |
|---|---|---|---|
| — | — | *(empty kernel template — fill per project)* | — |

Totals: — collected, — passed by default, — opt-in-skipped (state the reason for
every skipped class; an unexplained skip is an unrecorded deferral).

## How to write tests here (and what to avoid)

- **Test behavior, not implementation.** Assert on what a function returns/
  writes/raises for a given input, not on internal call sequences, unless the
  call sequence itself IS the contract (e.g. "the generative step must never call
  promote" — that's a trust invariant, test it directly).
- **Every test must be able to fail.** Zero assertion calls, a body that's just
  `pass`, or a trivially-true assertion (`assert True`, `assert 1 == 1`) all pass
  without proving anything — `tools/test_audit.py` flags all three. If you write one
  of these on purpose (rare — e.g. a smoke-import test), that's still worth a
  second look before committing.
- **Don't assert on a mock that never ran.** `assert_called_once()` only
  means something if the mock was actually wired into the code path under test.
  `tools/test_audit.py` flags mocks that are asserted on but never invoked in
  the same test body.
- **Narrow your exception assertions.** Catching the base exception class with no
  message match passes even when the WRONG exception fires. Raise/catch the
  specific type.
- **Use a realistic fixture, not just the simplest one.** ILLUSTRATIVE EXAMPLE
  (origin project): an auto-fixer's non-idempotency bug shipped past a green suite
  because its only test used a single-group fixture that never exercised the
  multi-group separator path where the real bug lived. When testing something
  that operates on "real files," include at least one fixture shaped like the
  real files it'll actually run against.
- **Mark opt-in tests with a REGISTERED marker, never an ad-hoc one.**
  Integration tests that need a live datastore auto-skip when its DSN is absent;
  perf and visual tests auto-skip unless explicitly selected. Registering the
  marker in the test config is what makes the skip visible rather than silent.
- **Perf tests assert a budget, not a benchmark number.** Set the budget
  generously above the observed baseline (10–50x) so it catches a real regression
  (e.g. an accidental O(n²) loop or an added network call), not machine noise. For
  complexity-scaling guards specifically, use large enough inputs that timer
  overhead is negligible — anything much smaller is noise-dominated and flakes.
- **No red tests, ever** (`docs/OPERATING_RULES.md` §1). If a test fails, fix
  the code or fix the test in the same change — never land on top of red.
