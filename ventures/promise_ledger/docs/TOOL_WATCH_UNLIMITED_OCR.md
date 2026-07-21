# Tool watch: Baidu Unlimited-OCR — applicability review (2026-07-17)

**Status:** SCOUTING NOTE, no adoption decision. Founder-directed review
("Deeply review this for applicability"). Provenance: BEST-EFFORT single-pass
web reads — the sandbox proxy 403'd the Hugging Face model card and arXiv
pages; verified directly: the GitHub repo README (github.com/baidu/
Unlimited-OCR, MIT license badge, install/config parameters). Benchmark
numbers below are as reported by the paper via press coverage, NOT
independently reproduced. Re-verify against arXiv 2606.23050 from an
unproxied machine before any adoption decision.

## What it is

- 3B-parameter Mixture-of-Experts OCR model, ~500M active parameters,
  released ~2026-06-24 by Baidu. MIT license. Continue-trained on top of
  DeepSeek-OCR (keeps its DeepEncoder + MoE decoder).
- Novelty: **Reference Sliding Window Attention (R-SWA)** — every output
  token attends to ALL visual (image) tokens plus only the last n=128
  generated tokens; older output tokens are evicted. KV cache is a fixed
  m+n queue, so GPU memory is CONSTANT regardless of document length: a
  500-page PDF costs the same working memory as a 5-page one. Parses
  multi-hundred-page documents in ONE inference pass (32K max output).
- Reported numbers (paper, unreproduced): OmniDocBench v1.5 93.23 (+6.22
  over DeepSeek-OCR), v1.6 93.92 (top of paper's table); text edit distance
  0.038; table TEDS 90.93%; formula CDM 92.61%; 40+-page docs hold edit
  distance <0.11 with 97% Distinct-35; ~5,580 tok/s vs baseline ~4,951.
- Output: structured Markdown (headings, tables, formulas, reading order).
  Languages: English, Chinese, mixed. Runs on vLLM/SGLang/Transformers
  (repo: torch 2.10.0, transformers 4.57.1; gundam/base modes; multi-page
  requires base mode; PDFs rasterized at 300 DPI).

## Applicability map (promise ledger)

| Surface | Fit | Why |
|---|---|---|
| MVP critical path: EDGAR 8-K EX-99.1 HTML | **NONE — do not use** | Our corpus is native HTML text. OCR on born-digital text can only ADD errors (0.038 edit distance ≈ worse than the 0 we have). Nothing on the MVP path needs this. |
| EDGAR PDF exhibits (minority; the r20 recall class) | Narrow | Some EX-99 exhibits are PDF-only. Volume is small; rasterize+OCR only those. |
| Historical backfill: pre-2001 EDGAR scans, Wayback IR-page PDFs | **Strong** | The "enter with robust content" strategy (analysis §12) eventually hits image-only documents at scale. One-pass long-document parsing + constant memory + MIT self-hosting ≈ near-zero marginal cost per page vs ~$1–1.5/1,000 pages for cloud OCR APIs at millions of pages. |
| International venues (phase 2): France info-financiere, UK NSM, HK/China disclosures | **Strongest** | Non-US regulators publish PDF-first. Chinese+English mixed support is directly relevant if the universe ever includes HKEX/CSRC filers. |
| OneLive (nightlife) | Marginal | Event flyers/posters someday; not on any current path. Note only. |

## Trust analysis (the part that matters for us)

1. **It is a GENERATIVE model — hallucination is a failure mode, and it
   lands upstream of our existential risk.** An OCR'd "$1.28B" where the
   page says "$1.2B" poisons the claim record at the provenance layer,
   beneath every gate we built. Char-level edit distance 0.038 is
   state-of-the-art for parsing but is NOT numeric-fidelity-grade for a
   ledger whose product is "receipts."
2. **Repetition/skip modes are real:** the repo ships no_repeat_ngram_size=35
   with ngram_window=1024 for multi-page — i.e., the authors guard against
   repetition loops mechanically; 97% Distinct-35 at 40+ pages implies ~3%
   non-distinct output. Silent page-skips/loops are exactly our
   silent-recall-loss class, at document scale.
3. **Required mitigations if ever adopted** (these become gates, not hopes):
   OCR-derived text gets its own provenance type (model id + version +
   params + page images' sha256, via `record_source_retrieval`); claims
   extracted from OCR-derived text carry a LOWER confidence entry point
   than claims from native text; a golden trial (≥20 docs from OUR corpus,
   page-completeness anchors + numeric-fidelity spot checks against the
   images) must pass BEFORE any pipeline use — same fail-closed shape as
   the extraction exam; per-document completeness checks (page count,
   length sanity) in the ingest path.
4. **Supply chain:** MIT license is clean for our use (no redistribution
   question — we run it, we don't ship it; R-016 unaffected: this is not a
   data provider). The inference code is third-party Python executing
   locally — it gets a security review pass before first run. Self-hosting
   needs a GPU = new service/spend = founder-crucial at adoption time.

## Why this vs alternatives (when the trigger fires)

- **vs cloud OCR APIs** (Azure Document Intelligence, Google DocAI,
  Textract): non-generative, mature, per-page priced. At backfill scale
  (millions of pages) self-hosted MIT wins on cost by orders of magnitude;
  cloud wins on numeric conservatism. A hybrid (Unlimited-OCR for bulk,
  deterministic verification of extracted NUMBERS against page crops) is
  the likely world-class shape.
- **vs DeepSeek-OCR** (its own base): strictly better on every reported
  benchmark + flat memory; no reason to prefer the base.
- **vs MinerU/olmOCR-style pipelines:** page-by-page, heavier orchestration;
  Unlimited-OCR's one-pass design is simpler for whole-filing parsing.

## Recommendation: PARK WITH A NAMED TRIGGER (no adoption now)

The MVP corpus is HTML; adopting OCR today adds risk and spend for zero
critical-path value. Trigger to revisit (objective): **PDF/image share of
required source material exceeds ~10% of the corpus, OR the pre-2001 /
international backfill is scheduled.** On fire: security review of the
inference code → budgeted golden trial on our own documents (completeness +
numeric fidelity) → founder decision on GPU spend. Until then: watch only.
