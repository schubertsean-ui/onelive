# 2026-07-17 — MemoHarness applicability review (docs-only research session)

**Contract:** founder request — "Deeply review this [arXiv 2607.14159] and
determine applicability to what we've built for OneLive and in general for
our Loop-Harness-Brain model." Scope: analysis + persisted review doc; no
code, no gates, no thresholds. Done-criteria: review delivered to founder,
review doc + queue amendments committed.

## What happened

1. The arXiv link was unreachable from this sandbox (network policy blocks
   arxiv.org and mirrors; the ID was also not yet search-indexed, which
   briefly and wrongly looked like a hallucinated citation). Founder
   uploaded the PDF; reviewed in full (20 pp).
2. Grounded the mapping against SESSION_START, memory/README (Brain 1A),
   MODEL_ROUTING, KAIZEN, night_shift, the gate-custody decision, and TODOS.
3. Delivered the review; persisted as
   `docs/strategy/ONE_LIVE_MEMOHARNESS_APPLICABILITY_REVIEW_v1.md`.

## Decisions (recorded, none founder-crucial)

- **Adopt** D1–D6 harness-dimension tags as optional taxonomy for Kaizen M2
  / gotchas / AGENT_FEEDBACK (new P3 TODO). Why: free second trend axis +
  typed retrieval key for Brain 1B; alternative (own taxonomy) rejected as
  needless invention.
- **Amend Brain 1B TODO spec** with two paper-derived constraints: recall
  returns success AND failure neighbors; retrieved memory assembled as
  stable cacheable prefix blocks (the paper's cost win is 94% cache reuse).
- **Reject** MemoHarness's training-time automated harness search — it is
  the outer-loop-over-harness already forbidden by
  `docs/memory/decisions/2026-07-14_gate-custody.md` and the 2026-07-16
  Weco AIDE² TODO line; its search space includes validators (D6) with no
  independent review of edits. No new decision needed — existing records
  covered it (that is the Brain working as designed).
- Per-source extraction adaptation: evidence upgraded, priority unchanged
  (existing gated P3 po-harvest item).

## Open threads

- Session's validate/PR status recorded in the changelog entry and PR
  description.

## Addendum 2026-07-18 — Kaizen turned on the session itself (founder challenge)

The founder challenged the visual_regression skip report. The skip was
legitimate (R-002, trigger unfired), but the report omitted the citation —
ledgered as the first founder(Red)-caught process defect (class:
skip-report-missing-record-citation). Response in the same push: SESSION_START
skip-citation rule (prose), validate mechanization queued (P2, gate custody),
send_later approval-block logged as REPEAT friction with a founder-side fix
queued. Meta-lesson recorded in AGENT_FEEDBACK: any founder catch = gate-gap
signal by default.

### CI evidence (run ids, verifiable)

- Original push `efe93da`: trust-gate **success**
  ([run 29645811897](https://github.com/schubertsean-ui/onelive/actions/runs/29645811897/job/88083754350));
  adversarial-review **success** (APPROVE, gpt-5.5)
  ([run 29645811894](https://github.com/schubertsean-ui/onelive/actions/runs/29645811894/job/88083754375)),
  both completed 2026-07-18T13:15Z.
- Addendum push `f654c0f`: adversarial-review **REQUEST-CHANGES r1**
  ([run 29648929954](https://github.com/schubertsean-ui/onelive/actions/runs/29648929954/job/88091806173)):
  blockers gate-evidence-missing + unverifiable-ci-claim (this section is the
  fix — an earlier version of it asserted "both green" with no run ids, a
  REPEAT of the unverifiable-claim class from #27 r1); nits ledger-chronology
  + overstated-gate-gap-wording, both fixed. Ledger row updated.

### tools/validate evidence (local session gate, run at commit time of the fix push)

```
  STATUS   CHECK                  NOTE
  ------   -----                  ----
  PASS     trust_gate
  PASS     lint
  PASS     deferral_scan
  PASS     pytest (full suite)     399 passed, 28 skipped locally; CI: 400/27
  PASS     eval_harness import
  PASS     perf benchmarks
  PASS     test_audit
  PASS     commit_sweep
  SKIP     visual_regression      app not running / baselines absent — R-002
RESULT: PASS (--allow-skips) — human-acknowledged incomplete (R-002 trigger unfired)
```

Context for the evaluator: CI attaches only pytest/web logs; `tools/validate`
is the local session-close gate (SESSION_START close step 3), so its evidence
is recorded here in the arc. The queued P2 mechanization (skip→Record binding)
will make this stamping machine-generated instead of hand-copied.
