# Session arc — 2026-08-05/06: engine at scale, backlog drained, provenance to the cards

Contracts: #43 (prior session — merged #186/#185/#177, ran the first post-fix
sweeps, closed the Clerk saga, proved the CSE 403 account-level; its close
rides this arc since its own close was cut short) and #44 (this session —
kickoff execution per docs/ops/SESSION_KICKOFF_2026-08-06.md).

## What happened, in order

1. **Reconcile.** session_reconcile loud-unverified on gh/DB legs (sandbox);
   PR states re-verified via the GitHub API: #186 (b847fb3), #177 (615caa9),
   #185 (8483e57) all MERGED, evaluator-APPROVED, green final heads. None
   carried a STATE line → records-only reconciliation c03f40f (marker →
   8483e57), then the concurrent #43 session's own records commit 3db6c03.
2. **Backlog drained to zero.** Post-#186 sweeps: 15:51Z run 31022426849
   stamp 699 (162 ready/461 hold/75 escalated) + promote 300/300 errors 0;
   16:01Z run 31023273235 stamp 71 (all hold) + promote 400/400 errors 0;
   16:15Z run 31024392369 stamp 0 + promote 340/340 errors 0; 16:17Z run
   31024529659 stamp 0 + promote 0/0 — POOL EMPTY. Compare the pre-fix
   scheduled run 30994644214: 45 promoted / 155 DatatypeMismatch errors.
3. **The honest asterisk.** db-report 31024343862 (16:14Z, mid-drain):
   pipeline lane 1,023 events, ALL confirmed, 74 venues, 323 artists —
   and `canonical_events_upcoming: 0`; ratio_50_to_1 windows 0/0/0. The
   drained backlog was historical (accumulated since July; dates passed) or
   date-refused (fail-closed datetime extractions → NULL start_time). The
   engine publishes flawlessly; UPCOMING date-verified discovered inventory
   is the next bottleneck. Fresh candidates from the live 3h-cycle ingest
   are the supply line to watch.
4. **Clerk cert saga CLOSED** (WS5): site-probe run 31023053306 —
   accounts.1live.co and clerk.1live.co both handshake with
   ssl_verify_result 0, CN-matched certs, issuer Google Trust Services WE1,
   expiry 2026-11-03 (issued at Folke's 05:07–05:10Z re-issue). /ops
   sign-in walkthrough goes to the founder in the session report.
5. **CSE verdict**: founder-delegated API intervention (decision record
   2026-08-05_founder-delegated-google-fix.md) proved the 403 account-level
   on Google's side; every key×project combination refuses identically.
   Founder-owned resolution (support ticket or provider switch =
   founder-crucial). Source scan (Bucket 1d) blocked on it, named + recorded.
6. **Cards workstream opened** (founder directive, TOP of build queue):
   field-by-field audit committed (docs/design/CARDS_CONTENT_AUDIT_2026-08-05.md).
   Verdict: everything the promote path writes renders honestly EXCEPT
   source provenance (dies at the promote boundary — the
   featurability-dimension-missed class live on the main consumer surface),
   plus one drift (detail page hid "How we know" for confirmed states).
   PR #188 closes both: migration 0020 (+backfill, +anon column grant per
   the 0012 precedent), promote-time write, reader passthrough, "How we
   know" names + links the real listing on lens and detail. Full pytest
   2083 green, web 253 green, tsc clean, validate substantive-all-PASS.
7. **Hygiene paid** (Bucket D): four owed Kaizen event rows (retyped-SHA,
   docs-only-merge-owes-STATE-line, staleness-drift-window,
   db-type-mismatch-invisible-to-hermetic-tests), changelog entry, this arc,
   Stage-3 retrieval block on Contract #44.

## Open at close

- PR #188 driving to green (evaluator verdict pending at time of writing).
- KPI ledger fold of the fresh post-drain db-report (values cited from the
  artifact when the dispatched run completes).
- Bucket 2 remainder: v0 prompt package (A2), Eventbrite scheduled import
  (B), festival mode piece 1 (C). Bucket 3 scoping untouched.
- Next engine bottleneck (named, unowned): upcoming/date-verified discovered
  inventory — candidates promoted from live ingest should begin carrying
  future dates; a db-report start_time distribution (null/past/upcoming) for
  the pipeline lane would make the diagnosis mechanical.
