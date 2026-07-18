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
signal by default. CI note: trust-gate + adversarial-review both green on the
original push; this addendum re-runs both.
