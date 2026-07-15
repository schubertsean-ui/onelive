# Promise Ledger — venture workspace (pre-build groundwork)

**Status:** GROUNDWORK ONLY (Session Contract #16, orig #7). The venture go/no-go is an
open founder decision; nothing in this directory is deployed, spends money, or
contracts a provider (R-016 gates all of that). This workspace lives inside the
OneLive repo for gate coverage (evaluator + trust-gate + tests) and will be
extracted to its own repository if/when the founder greenlights the venture.

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
  **Not yet run against live EDGAR:** this sandbox's egress policy blocks
  sec.gov (verified 2026-07-14: curl and WebFetch both refused) — see R-017.
  Tests use synthetic fixtures explicitly marked as such.
- `eval/` — extraction-precision golden-set harness. Fail-closed: below-bar
  precision exits non-zero; an empty golden set exits non-zero (a gate that
  cannot fail proves nothing). Currently seeded with SYNTHETIC labeled
  examples that exercise the harness mechanics only — **no threshold means
  anything until real EDGAR-sourced examples replace them (R-017)**. The
  market analysis names extraction precision the venture's existential risk;
  this harness exists before any extraction model does, per charter
  discipline.
- `docs/LEDGER_STORAGE_DESIGN.md` — point-in-time storage design
  (append-only claim events, as-of-known-when reads, LEI entity keys).
- `docs/BEACHHEAD_SECTOR_MEMO.md` — decision memo FOR THE FOUNDER (criteria,
  candidates, tradeoffs). No decision is taken here.

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
