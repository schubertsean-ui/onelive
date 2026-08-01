Assessed StarTrail-org/PixelRAG (Apache-2.0) for OneLive ingestion and DECLINED adopting it: PixelRAG is a visual *retrieval* engine, OneLive needs structured *extraction*, so it is the wrong half of the pipeline and new heavy infra. We KEPT the insight it validates — image-only event sources (gig-poster JPEGs, PDF/Instagram flyers, calendar-as-image) are invisible to our text-only extraction — and escalated a cost-disciplined fix to the founder (`docs/escalations/2026-07-29_visual-ingestion-fallback.md`).

## The retrieval token (what a future session should recall)

**"PixelRAG is retrieval, we need extraction"** — before reaching for any
visual-RAG / screenshot-embedding library for ingestion, remember it answers
"find the visually-similar document," not "pull structured event facts from
this image." We already know which pages to fetch (`worker/source_catalog.py`);
we do not have a corpus-search problem.

## What PixelRAG is

Open-source (Apache-2.0) *visual RAG*: renders documents/web pages to
screenshots (`pixelshot`, Playwright/Chrome), embeds the page images with a
LoRA-fine-tuned `Qwen3-VL-Embedding` model, indexes them in FAISS/Qdrant, and
serves a "search a corpus by how pages *look*" API. Its value is preserving
tables/charts/layout that text parsing discards, so a reader can *locate* the
right page. Ships a pre-built Wikipedia index and a Claude Code plugin.

## Why we declined it (the three blockers)

1. **Wrong half of the pipeline.** OneLive's ingestion need is extraction —
   raw source text/image → `event_candidate` rows through the gate
   (`worker/ai_extract.py`). PixelRAG's output is "here is a visually-similar
   tile," not structured event fields. We would still need an extractor on top,
   so it solves a problem (retrieval) we do not have.
2. **New services + spend → founder-crucial.** A Qwen3-VL embedding model
   (GPU hosting) plus FAISS/Qdrant is new recurring infra. That trips CLAUDE.md
   *money/new services* and *cost discipline* ("least costly method first") —
   a per-page visual-embedding stack is far heavier than our current text calls.
3. **Trust-invariant collision → founder-crucial.** Any new path that turns
   source material into candidate facts is a change to the certified,
   hash-locked extraction harness (Prime Directive #1). It cannot ship as an
   agent decision and must pass the golden exam.

## The gap it validated (grounded, not guessed)

Confirmed by inspection that OneLive extraction is 100% text-based:
`worker/ai_extract.py` segments HTML *text* and fans out the certified
single-event extractor per block; `worker/fetch/render_fetch.py` already runs
headless Chromium but only to recover rendered *HTML text* — it explicitly
**blocks images** (`_BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}`).
A grep of `worker/` finds no vision/OCR/multimodal path. Therefore events that
exist **only as an image** (a gig-poster JPEG, a PDF flyer, an Instagram flyer,
a calendar rendered as a background image) are currently unextractable — a real
long-tail ingestion gap.

## The recommended fix (a proposal, NOT built here)

If we close the gap, the cost-disciplined route is **not** PixelRAG's stack but
our *existing* Playwright plus **Claude's own multimodal vision** as an
extraction fallback: screenshot the page/region, hand the image to the
already-certified extractor's model family, emit the same `AIEventExtraction`
schema. Reuses infra we already have, adds no new service, keeps a single
extraction path. Still an extraction-harness change → founder-crucial, so it is
escalated, not started. Full escalation:
`docs/escalations/2026-07-29_visual-ingestion-fallback.md`.

## Regression / gate note

No code changed. If the escalation is later approved and built, the visual
fallback MUST route through the golden exam like any extraction-path change
(Prime Directive #1); a green build alone is not authority to ship it.
