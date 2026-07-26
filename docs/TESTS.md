# TESTS — inventory + how to write tests here

Greppable summary: 147 tests across 13 files (`pytest --collect-only -q`), 120
run by default (`python -m pytest -q`), 27 opt-in-skipped (10 `dbintegration`
+ 4 `perf` + 13 `visual`, see conftest.py). Run `python tools/test_audit.py`
before trusting any new test — it catches tests that pass without proving
anything. Table below is kept accurate to the real `tests/` dir; update it in
the same commit whenever a test file is added or a test count changes.

## How to run

```bash
python -m pytest -q                    # default: pure-logic only (120 passed, 27 skipped)
python -m pytest -m dbintegration       # needs ONELIVE_TEST_DB_DSN (see tests/conftest.py)
python -m pytest -m perf -v             # opt-in perf budgets (tools/profile_target.py to dig in)
python -m pytest -m visual -v           # opt-in visual-regression compare/decode tests
python tools/test_audit.py              # false-confidence audit of tests/ itself
```

## Test inventory

| File | Tests | What it tests | Markers |
|---|---|---|---|
| `tests/test_gates.py` | 20 | Multi-confirm gate, 4-state confidence model, disputed-never-dropped guarantee | some `dbintegration` |
| `tests/test_claude_provider.py` | 13 | Claude provider trust behavior: loud fail on misconfig, retry+degrade+audit on transient errors, `_provenance` stamping, upgraded eval harness | none (FakeAnthropic, no network) |
| `tests/test_resolve_entities.py` | 14 | `worker/resolve_entities.py` exact→trigram-fuzzy→placeholder resolution; city-scoping, no-orphan transaction handling | some `dbintegration` |
| `tests/test_migration_0006_rls.py` | 11 | `supabase/migrations/0006_rls_policies.sql` structural parse + live RLS behavior | some `dbintegration` |
| `tests/test_migration_0007_narrow_event_read.py` | 9 | `supabase/migrations/0007_narrow_event_public_read.sql` structural parse + live RLS behavior | some `dbintegration` |
| `tests/test_session_reconcile.py` | 7 | `tools/session_reconcile.py` drift classification (benign/material/unverified) | none |
| `tests/test_trust_gate.py` | 7 | `tools/trust_gate.py` catches each violation class it claims to guard | none |
| `tests/test_ai_extract_integration.py` | 3 | `worker/ai_extract.extract_candidate` end-to-end wiring, provider→store, without a DB | none |
| `tests/test_lint.py` | 17 | `tools/lint.py` rules (positive+negative per rule) + `--fix` idempotency regression guards | none |
| `tests/test_commit_sweep.py` | 12 | `tools/commit_sweep.py` detectors, against real repo history + synthetic commit lists | none |
| `tests/test_test_audit.py` | 13 | `tools/test_audit.py` detectors (synthetic fixtures) + smoke test that real `tests/` audits clean | none |
| `tests/test_perf_benchmarks.py` | 2 (4 collected, see note) | Perf budgets on `derive_confidence`, `multi_confirm_gate`, `score_extraction`; O(n) vs O(n²) scaling guard | `perf` |
| `tests/test_visual_regression.py` | 13 | `tools/visual_regression.py` PNG decode + pixel-diff engine, CLI exit codes, loud-fail-on-missing-browser | `visual` |
| `tests/test_social_carousel.py` | 135 | `social/carousel/` engine: trust selection (confirmed/likely + scheduled + canonical-origin only, unknown states loud), truthful time windows, publish-gate custody (HMAC-signed approvals under the founder key — forged/wrong-key/keyless refused, hash-bound, current confidence+status re-check, full-content rescan), signature-verified autonomy record fail-closed L0/L1/L2 (renderer/series/cadence-bound; release clock gate-owned; journal-counted daily ceiling), agent_loop→publish_gate import guard, typed skip boundary (trust errors propagate loud), bandit determinism/learning/decay, volume tiering, 22-domain GEO bundle, future-only listicle windows (6pm excludes 5:30 start, gen+release), five scenario series rendered from synthetic fixtures | none (hermetic, no network) |
| `tests/test_construction_gate.py` | 23 | Construction Loop Stage 3 gate: deliberate [S3:token] contract citations (bare mentions never pass); path AND content trigger matching; index self-protection (deleted token / narrowed triggers fail closed, bootstrap explicit); duplicate tokens fail closed; stale base-history citations never pass (real temp git repo); unresolvable diff base fails closed; unreadable/empty index fails closed; real-index coverage; base-ref FRESHNESS proof with NO offline path (oid comparison against the remote tip is the only proof; a fetch that succeeds while leaving the ref behind FAILS; an unreachable remote always fails closed, including from the merge-commit topology that a stale base can reproduce) plus the SHIPPED probes against real git in two temp repos (explicit-refspec fetch really moves the remote-tracking ref; end-to-end convergence; unreachable remote returns None); fully-supplied runs never reach for the remote at all | none (hermetic, temp git repos) |
| `tests/test_carousel_launch.py` | 6 | V1 launch versions (founder-directed): assignments valid/complete; FULL-DECK golden reproducibility (committed snapshot, any drift fails); fail-loud unknown/misspelled series; fresh validated copies; corrupt table fails loud; warm-start asserts direct posterior state per factor×level (favored=+weight once, others untouched) via bandit.add_prior | none (hermetic) |
| `tests/test_adversarial_review.py` | 29 | Evaluator gate v1+v2: strict verdict parse (ambiguity = hard fail), key-absent skip vs --require, exit-code convention; v2 panel — po determinism + seed-varying, --panel requires --po-seed, ANY-lens-red = red, absent Gemini seat printed EXPLICITLY, both seats run two lenses when keyed, unparseable lens = hard fail, prompt encodes the ratified escape hatch + CLASS mandate, env model resolver fails closed on empty/Claude ids, the panel prints its own po seed and derived provocations; the second seat's model override is ALLOWLISTED by the base-owned copy (a non-blessed id raises), the shipped default is itself allowlisted, and the OpenAI seat's model is never overridable in CI | none (hermetic, transport monkeypatched) |
| `tests/test_gemini_preflight.py` | 18 | Second-seat model preflight (`tools/gemini_preflight.py`), every branch with an injectable transport: absent/blank key is an explicit empty seat not a failure; listing unreachable fails closed; a pin absent from the advertised list fails closed AND prints the options; an ADVERTISED-BUT-QUOTA-REFUSED model (the 429 `limit: 0` shape) fails closed; a retired model's 404 body is surfaced; probe transport failure fails closed; success asserts the live probe actually happened against the pinned model with a bounded body; listing paginates to exhaustion; non-generateContent models excluded; malformed entries tolerated; bad arguments fail loud; unexhausted pagination RAISES rather than returning a partial registry; opaque page tokens are percent-encoded; and the WORKFLOW custody branch (preflight runs from the trusted base copy; the bootstrap skip is reachable only while the PR carries the tool, so it expires at merge; absent-on-both fails closed), plus the CLASS invariant: every trusted-base custody fetch in the workflow carries a terminating fail-closed path, and ABSENCE is separated from FETCH FAILURE (own mkdir, git cat-file -e existence test, no error-swallowing on the fetch) | none (hermetic, no network) |
| `tests/test_reviewer_scorecard.py` | 10 | M9 reviewer scorecard: mechanical ledger arc parsing (round-1 recall, sibling-misses, novelty), true round-1 semantics (an arc with no r1 row is an explicit unmeasurable), exact 9-part ledger schema enforced (an extra raw pipe RAISES), uncounted class mentions excluded, no-classed-findings guarded (no division error), the real shipped ledger parses clean AND agrees with known merge facts (merged arcs report their true rounds-to-green, so a forgotten close row fails here), an unclosed arc is named rather than guessed, the exact-schema check covers MERGED rows too (raw pipes raise; a well-formed merged row parses) | none (hermetic) |

Note on `test_perf_benchmarks.py`: 2 `def test_*` functions, one of which is
`@pytest.mark.parametrize`d over 3 targets, so `pytest --collect-only` reports
4 individual test IDs from that file.

Totals: 147 collected, 120 passed by default, 10 `dbintegration`-skipped
(no `ONELIVE_TEST_DB_DSN` in this environment), 4 `perf`-skipped, 13
`visual`-skipped (opt-in by design, see `tests/conftest.py`).

## How to write tests here (and what to avoid)

- **Test behavior, not implementation.** Assert on what a function returns/
  writes/raises for a given input, not on internal call sequences, unless the
  call sequence itself IS the contract (e.g. "the AI step must never call
  promote" — that's a trust invariant, test it directly, see `test_gates.py`).
- **Every test must be able to fail.** Zero `assert`/`raises`/`approx` calls,
  a body that's just `pass`, or a trivially-true assertion (`assert True`,
  `assert 1 == 1`) all pass without proving anything — `tools/test_audit.py`
  flags all three. If you write one of these on purpose (rare — e.g. a
  smoke-import test), that's still worth a second look before committing.
- **Don't assert on a mock that never ran.** `mock.assert_called_once()` only
  means something if `mock` was actually wired into the code path under test.
  `tools/test_audit.py` flags mocks that are asserted on but never invoked in
  the same test body.
- **Narrow `pytest.raises`.** `pytest.raises(Exception)` with no `match=`
  passes even when the WRONG exception fires. Raise/catch the specific type
  (see `test_claude_provider.py`'s `ExtractionConfigError` assertions).
- **Use a realistic fixture, not just the simplest one.** The `lint.py --fix`
  non-idempotency bug (see `docs/AGENT_FEEDBACK.md`'s 2026-07-12 entry) shipped
  past a green suite because its only test used a single-import-group fixture
  that never exercised the multi-group separator-line path where the real bug
  lived. When testing something that operates on "real files," include at
  least one fixture shaped like the real files it'll actually run against.
- **Mark `dbintegration` / `perf` / `visual` appropriately, never invent a
  4th ad-hoc marker without registering it in `tests/conftest.py`.**
  `dbintegration` tests use the `db_conn` fixture (auto-skips without
  `ONELIVE_TEST_DB_DSN`); `perf` and `visual` auto-skip via
  `conftest.py`'s `pytest_collection_modifyitems` hook unless explicitly
  selected with `-m`.
- **Perf tests assert a budget, not a benchmark number.** Set the budget
  generously above the observed baseline (10-50x, per
  `tests/test_perf_benchmarks.py`) so it catches a real regression (e.g. an
  accidental O(n²) loop or an added network call), not machine noise. For
  complexity-scaling guards specifically, use large enough inputs that timer
  overhead is negligible (see `test_derive_confidence_is_not_accidentally_
  quadratic`'s 5,001 vs 500,001-item comparison — anything much smaller was
  noise-dominated and flaked before that fix).
- **No red tests, ever** (`docs/OPERATING_RULES.md` §1). If a test fails, fix
  the code or fix the test in the same change — never land on top of red.
