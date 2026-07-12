# Scorer Hardening — Build Spec (ai/eval_harness.py → world-class)

## Why
`score_extraction`/`aggregate` are structurally right (precision/recall/F1,
hallucination_rate as the trust KPI, wrong-value counted as both FP+FN) but fail
the world-class bar (OPERATING_RULES.md §1a) at **correct-at-the-core**: the
comparison layer `_norm` is only `strip().lower()`. Consequences to fix:
- `"8pm"` vs `"20:00"` vs `"8:00 PM"` → scored as a hallucination. This poisons
  the exact KPI (hallucination_rate) that governs trust. UNACCEPTABLE.
- venues/cities: `"The Mohawk"` vs `"Mohawk"`, `"Austin, TX"` vs `"Austin"` →
  false errors.
- lineups (lists) compared as exact sets → one missing opener flips the WHOLE
  field to FP+FN; no partial credit.
- `aggregate` gives point estimates only — no way to tell a real move from noise.
- dead code: `evaluate_extraction` (exact-match ratio) is obsoleted by
  `score_extraction`. Sunset Law (§2b): RETIRE it in this change.

## Non-negotiables (OPERATING_RULES.md §1)
- Every behavior change ships WITH its tests IN THIS CHANGE, proving BOTH
  directions (fires when it should; does NOT false-positive on clean input).
- Full suite + `python tools/trust_gate.py` green before done.
- Deterministic, pure-logic, hermetic: NO network, NO DB, NO AI call, NO new
  third-party deps (stdlib only — no dateutil). This module is offline eval.
- Fail loud on malformed comparator config; never silently mis-score.
- Honest docstrings: state what each normalizer does AND its known limits.

## BUILD (edit ai/eval_harness.py in place; keep public API stable where possible)

### 1. Field-typed semantic normalization (the core fix)
Introduce a small, explicit, per-field-KIND normalization layer. Do NOT hardcode
field names — infer kind from a passed-in schema map, defaulting to text.
```
FieldKind = Enum("FieldKind", "TEXT TIME DATE VENUE LIST_TEXT")
DEFAULT_FIELD_KINDS = {  # OneLive extraction fields; extend as schema grows
  "start_time": TIME, "end_time": TIME, "date": DATE,
  "venue": VENUE, "location": VENUE, "city": VENUE,
  "artists": LIST_TEXT, "lineup": LIST_TEXT, "tags": LIST_TEXT,
  # everything else -> TEXT
}
```
Normalizers (all stdlib; deterministic):
- **TIME**: parse common event-time spellings to canonical 24h "HH:MM":
  "8pm","8 pm","8:00 PM","20:00","8:00pm" → "20:00". Handle noon/midnight,
  "7:30pm", bare hour, and a trailing "doors"/"show" prefix stripped by caller
  is NOT required. If a value cannot be parsed, fall back to text-normalized
  compare (do NOT crash, do NOT silently treat unparseable as equal). Record
  unparsed values so a reviewer can see them (see §3 diagnostics).
- **DATE**: parse ISO ("2026-03-14") and common US forms ("March 14, 2026",
  "3/14/2026","Mar 14") to canonical "YYYY-MM-DD" when year present; if year
  absent, compare month-day. Unparseable → text fallback + record.
- **VENUE**: casefold, strip leading "the ", strip trailing state/country after
  a comma ("Austin, TX"→"austin"), collapse whitespace/punctuation. Document
  that this is deliberately lenient (venue aliases beyond this need an entity
  table — name that as a known limit, not silently ignored).
- **LIST_TEXT**: element-wise. Compute per-element set overlap → return enough
  to support PARTIAL CREDIT (see §2), not just equal/not-equal.
- **TEXT**: current strip().lower() behavior (unchanged).

### 2. Per-element list scoring (partial credit)
For LIST_TEXT fields, a field is no longer all-or-nothing. Count element-level
tp/fp/fn INTO the ExtractionScore (matched elements = tp; predicted-not-expected
= fp + hallucinated; expected-not-predicted = fn). This makes a 3-of-4 lineup
score as 3 tp + 1 fn, not a total field failure. Keep scalar fields' existing
semantics. Ensure hallucination_rate still = fp/asserted with the new counts.

### 3. Diagnostics / observability (world-class = observable)
Extend ExtractionScore with:
- `unparsed_values: List[Tuple[str, str]]`  # (field, raw value) that a TIME/DATE
  normalizer could not parse and fell back on — so the corpus author sees which
  cases the normalizer is blind to. NEVER hide this.
Add a `by_field: Dict[str, str]` per-example outcome map ("tp"/"fp"/"fn"/"tn"/
"partial") for debuggability.

### 4. `aggregate`: add statistical rigor
- Keep micro-averaged precision/recall/f1/hallucination_rate.
- Add **bootstrap 95% confidence intervals** for hallucination_rate and f1
  (stdlib `random` with a FIXED seed passed in, default 12345, so results are
  reproducible/deterministic — a world-class eval is not flaky). Return as
  `hallucination_rate_ci95: [lo, hi]`, `f1_ci95: [lo, hi]`.
- Add `n_unparsed: int` surfaced at corpus level.
- Guard n<2 (CI undefined) → return the point estimate as [x, x] and do not crash.

### 5. Sunset Law: retire `evaluate_extraction`
Remove the obsolete exact-match `evaluate_extraction`. First grep the repo for
callers; if any exist (incl. tests), migrate them to `score_extraction`/`.f1`
IN THIS CHANGE. State in the commit what was retired. (If a caller genuinely
needs a 0..1 scalar, add `ExtractionScore.accuracy`property instead — one
representation.)

## TESTS (tests/test_eval_harness.py — create/extend; hermetic)
Prove BOTH directions for each new behavior:
- TIME: "8pm"/"20:00"/"8:00 PM" all score as tp (NOT hallucination); a genuinely
  wrong time ("8pm" vs "9pm") still scores as FP+FN. An unparseable garbage time
  is recorded in unparsed_values AND falls back (doesn't crash).
- DATE: equivalent forms match; wrong date still fails; missing-year compares m-d.
- VENUE: "The Mohawk"/"Mohawk", "Austin, TX"/"Austin" match; different venue fails.
- LIST partial credit: expected 4-act lineup, predicted 3 correct → 3 tp + 1 fn,
  field not counted as total failure; a predicted extra act → +1 fp/hallucinated.
- aggregate: CI returned, deterministic across two runs with same seed, n<2 safe,
  n_unparsed surfaced.
- Retirement: assert `evaluate_extraction` no longer exists (import fails) OR its
  callers now use the new path (whichever the migration chose) — and the suite
  is green either way.
- A sabotage test: temporarily feed a KNOWN-wrong expected value and assert the
  scorer reports the discrepancy (proves the scorer can fail, not vacuous).

## Done =
Full suite + `python tools/trust_gate.py` green; no dead code; docstrings state
limits honestly; ai/eval_harness.py does NOT import worker.promote and pulls in
no new deps.
