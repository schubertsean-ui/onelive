# Promise Ledger — venture workspace (build phase 1)

**Status:** GREENLIT — founder said "Go" 2026-07-15 (Contract #17), beachhead
sector = FINANCIALS (Contract #18), first LIVE EDGAR run executed same day.
Nothing here is deployed, spends money, or contracts a provider — R-016
(provider redistribution answers + live pricing re-verification) still gates
step 11, and R-017 (≥20 REAL labeled golden examples) still gates all
extraction-model work. This workspace lives inside the OneLive repo for gate
coverage (evaluator + trust-gate + tests) and extraction to its own repository
is sprint step 12 (a founder call).

**What the product would be** (see `docs/research/PR_AGGREGATOR_MARKET_ANALYSIS.md`):
a longitudinal, point-in-time ledger of corporate claims — what each public
company promised, what changed, what's overdue, what was delivered — built
claim-first (not document-first), LEI-keyed, agent-native (MCP), sold to the
underserved $6–15k/seat tier, consultants (per-dossier), and AI-platform feed
buyers.

## Contents

- `schema/` — **Claim Schema v0** (harvest idea H13, the "promise markup"):
  stdlib dataclass models + validation + JSON Schema export. The claim — not
  the document — is the primary key; lifecycle states include
  `silently_dropped`; fulfillment verdicts use the 4-state confidence model
  (`unverified | likely | confirmed | disputed`) inherited from OneLive's
  trust DNA — never binary.
- `ingest/` — EDGAR client written to the SEC's documented fair-access
  contract (declared User-Agent, ≤10 req/s budget, bulk-archives-first).
  **First live run executed 2026-07-15** after the founder's egress unblock:
  real JPM + BAC Q2-2026 earnings 8-Ks listed, both EX-99.1 press releases
  fetched with provenance. The live run caught a filename-recall bug the
  synthetic fixtures had missed — fixed via the authoritative index-headers
  exhibit-type path; real fixtures now live in `tests/fixtures/edgar/`.
- `eval/` — extraction-precision golden-set harness. Fail-closed: below-bar
  precision exits non-zero; an empty golden set exits non-zero (a gate that
  cannot fail proves nothing). Labeled examples are still SYNTHETIC-ONLY
  (mechanics only); `eval/source_material/` now holds the first 2 REAL press
  releases (manifest-hashed, stored internally per the never-verbatim rule)
  awaiting hand-labeling — **no threshold means anything until ≥20 real
  labeled examples exist (R-017)**. The market analysis names extraction
  precision the venture's existential risk; this harness exists before any
  extraction model does, per charter discipline.
- `docs/LEDGER_STORAGE_DESIGN.md` — point-in-time storage design
  (append-only claim events, as-of-known-when reads, LEI entity keys).
- `docs/BEACHHEAD_SECTOR_MEMO.md` — decision memo FOR THE FOUNDER (criteria,
  candidates, tradeoffs). DECIDED 2026-07-15: FINANCIALS (memo kept as the
  decision record; the post-decision po battery + harvest live alongside it).

## Invariants (inherited, non-negotiable)

1. Point-in-time correctness: no record is ever silently overwritten; later
   knowledge appends, never edits (same rule that forbids yfinance in
   multibagger).
2. Fulfillment verdicts are graded and evidence-linked, never binary — a
   wrong "broken promise" stamp is the product's defamation-adjacent failure
   mode.
3. Published output re-expresses facts; verbatim source text is stored
   internally only (AP-v-Meltwater design rule).
4. Disputed evidence is shown with its verdict attached, never hidden or
   redacted.
