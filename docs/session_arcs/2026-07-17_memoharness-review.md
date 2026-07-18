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
skip-citation rule (prose), validate mechanization initially queued P2 —
then SHIPPED in this same PR after evaluator r2 refused the deferral (see
below); send_later approval-block logged as REPEAT friction with a
founder-side fix queued. Meta-lesson recorded in AGENT_FEEDBACK: any founder catch = gate-gap
signal by default.

### CI evidence (run ids, verifiable)

- Original push `efe93da`: trust-gate **success**
  ([run 29645811897](https://github.com/schubertsean-ui/onelive/actions/runs/29645811897/job/88083754350));
  adversarial-review **success** (APPROVE, gpt-5.5)
  ([run 29645811894](https://github.com/schubertsean-ui/onelive/actions/runs/29645811894/job/88083754375)),
  both completed 2026-07-18T13:15Z.
- Addendum push `f654c0f`: adversarial-review **REQUEST-CHANGES r1**
  ([run 29648929954](https://github.com/schubertsean-ui/onelive/actions/runs/29648929954/job/88091806173)):
  blockers gate-evidence-missing + unverifiable-ci-claim (a REPEAT of the
  unverifiable-claim class from #27 r1); nits ledger-chronology +
  overstated-gate-gap-wording.
- Fix push: adversarial-review **REQUEST-CHANGES r2**
  ([run 29649044528](https://github.com/schubertsean-ui/onelive/actions/runs/29649044528/job/88092104841))
  refused the queued mechanization outright — with the repeat-class threshold
  hit, deferral was the violation ("a prose rule is not a failing gate").
  Correct. The mechanization SHIPPED in the next push, same PR:
  `tools/skip_record_binding.py` + validate binding (unrecorded skip = RED
  even under --allow-skips) + machine-stamped evidence + CI attachment of
  validate.log to the evaluator.

### tools/validate evidence — CI artifact, not a pasted block

Per evaluator r3 (a pasted block goes stale the moment the next commit lands
— the exact class this PR fixes), the arc carries NO copied evidence.
The authoritative gate evidence is the `validate.log` that
`adversarial-review.yml` generates and hands to the evaluator on every run
of this PR; the run that produced the final APPROVE on the merged head IS
the evidence, findable from PR #35's checks. Locally, validate writes the
same machine block to gitignored `.validate-evidence.txt` at each run.

Round trail on the gate itself: r3
([run 29649316305](https://github.com/schubertsean-ui/onelive/actions/runs/29649316305/job/88092804231))
caught three fail-open holes in the r2-shipped mechanism — note-substring
quick exemption (→ structured QSKIP status), loose substring Record binding
(→ backticked-marker requirement + negative tests), and this arc's own stale
evidence block (→ this pointer). Same push shipped `tools/kaizen_trends.py`
(founder direction: trends computed, never asserted) — its first run
immediately surfaced R-019 (`empty-env` repeat class, fix due via the
env-contract workflow linter) and the ledger marker-convention backfill.
