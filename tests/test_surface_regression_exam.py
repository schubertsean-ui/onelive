"""Tests for the automated surface regression-exam (ai/surface_exam.py).

A gate that cannot fail proves nothing (docs §9.6). These tests prove the exam:
  * PASSES on the current extraction surface (all pages meet baseline, zero fab);
  * goes RED on a PLANTED under-segmentation regression (the R-034 class) —
    forcing the segmenter to return one whole-page block drops recall below
    baseline on the multi-event pages;
  * FLAGS a PLANTED fabrication (a provider that returns an event with a
    signature not in the labels);
  * still passes a single-event page under the same whole-page regression.

All hermetic: the RECORDED provider does no network/model/spend, and the
candidate store is stubbed by the exam itself (no DB).
"""
import json

import pytest

import worker.ai_extract as ai_extract
from ai.surface_exam import (
    ExamReport,
    RecordedSurfaceProvider,
    load_pages,
    run_surface_exam,
)


@pytest.fixture
def pages():
    return load_pages()


def test_live_exam_passes_on_current_pipeline(pages):
    """The corpus is green on the current surface: every page meets its measured
    baseline recall and produces zero fabrications."""
    report = run_surface_exam(pages)
    assert isinstance(report, ExamReport)
    assert report.ok, [(p.id, p.recall, p.baseline_recall) for p in report.pages if not p.ok]
    assert report.fabrication_count == 0
    # The corpus must actually exercise multi-event pages (baseline 1.0, >1
    # expected) — otherwise "passes" would be vacuous.
    multi = [p for p in report.pages if p.expected_count > 1 and p.baseline_recall == 1.0]
    assert len(multi) >= 3
    # And it must carry the R-034 hard cases with honest sub-1.0 baselines.
    hard = [p for p in report.pages if p.baseline_recall < 1.0]
    assert len(hard) >= 2


def test_planted_undersegmentation_regression_goes_red(pages, monkeypatch):
    """Force the segmenter to under-segment (one whole-page block). The provider
    then sees both events in one block and returns only the FIRST, so recall
    drops below baseline on the clean multi-event pages — the exam must fire."""
    monkeypatch.setattr(ai_extract, "segment_events", lambda text, **kw: [text])
    report = run_surface_exam(pages)
    assert not report.ok
    reds = {p.id for p in report.regressions}
    # Every page that today segments into >1 clean block (baseline 1.0, >1
    # expected) must regress when segmentation is defeated.
    for p in report.pages:
        if p.expected_count > 1 and p.baseline_recall == 1.0:
            assert p.id in reds, f"{p.id} should have regressed under whole-page segmentation"
    # No fabrications are invented by defeating segmentation — the miss fails
    # toward under-recovery, never toward a fabricated event.
    assert report.fabrication_count == 0


def test_single_event_page_still_passes_under_whole_page_segmentation(pages, monkeypatch):
    """A single-event page is already one block, so forcing whole-page
    segmentation changes nothing — it must stay green."""
    monkeypatch.setattr(ai_extract, "segment_events", lambda text, **kw: [text])
    report = run_surface_exam(pages)
    singles = [p for p in report.pages if p.expected_count == 1]
    assert singles, "corpus must include a single-event page"
    for p in singles:
        assert p.ok
        assert p.recall == 1.0


class _FabricatingProvider:
    """Returns a content-bearing event whose fields match NO labeled signature —
    the shape of a hallucinated event the guard must catch."""

    def extract_event_json(self, text, schema_json, system_prompt=None):
        return {
            "title": "Phantom Gala",
            "venue_name": "Nowhere Hall",
            "artist_names": ["Ghost Act"],
            "_provenance": {"provider": "fabricator"},
        }


def _run_one_page_with_provider(page, provider):
    """Run the REAL extract_candidates over one page with a given provider and a
    stubbed store, returning the exam's per-page result — reuses the exam's own
    machinery so the test measures the same code the gate runs."""
    from ai.surface_exam import _captured_store, _is_content_bearing

    with _captured_store() as captured:
        ai_extract.extract_candidates(
            ai=provider,
            text=page["content"],
            source_class="surface_exam",
            source_name=str(page["id"]),
            source_url=f"surface-exam://{page['id']}",
        )
    events = [c for c in captured if _is_content_bearing(c)]
    blobs = [json.dumps(c, ensure_ascii=False) for c in events]
    sigs = [e["signature"] for e in page["expected_events"]]
    fabrications = [b for b in blobs if not any(s in b for s in sigs)]
    return events, fabrications


def test_planted_fabrication_is_flagged(pages):
    """A provider that returns an unlabeled event must surface as a fabrication."""
    page = next(p for p in pages if p["id"] == "p4_single_event_page")
    events, fabrications = _run_one_page_with_provider(page, _FabricatingProvider())
    assert len(events) == 1
    assert len(fabrications) == 1
    assert "Phantom Gala" in fabrications[0]


def test_recorded_provider_returns_first_signature_only():
    """The recorded provider mimics the single-event extractor: given a block
    with two labeled signatures, it returns only the FIRST (most-prominent) —
    this is the mechanism that turns under-segmentation into a recall drop."""
    expected = [
        {"signature": "First Act", "title": "First Act", "venue_name": "Club A"},
        {"signature": "Second Act", "title": "Second Act", "venue_name": "Club B"},
    ]
    provider = RecordedSurfaceProvider(expected)
    merged_block = "First Act at Club A and also Second Act at Club B"
    result = provider.extract_event_json(merged_block, {})
    assert result["title"] == "First Act"
    assert "Second Act" not in json.dumps(result)
    # A block with no known signature is "no event found" (None).
    assert provider.extract_event_json("nothing familiar here", {}) is None


def test_corpus_signatures_are_present_in_page_content():
    """Corpus integrity: every labeled signature must appear literally in its
    page content, or the exam could never recover that event even in principle."""
    for page in load_pages():
        for event in page["expected_events"]:
            assert event["signature"] in page["content"], (
                f"{page['id']}: signature {event['signature']!r} absent from page content"
            )


def test_min_recall_floor_can_only_tighten(pages):
    """The floor is an under-ratchet: raising it above a page's honest baseline
    turns that page red; it can never relax the per-page baseline bar."""
    # A floor above the hard-case baseline (0.333) must fail those pages.
    strict = run_surface_exam(pages, min_recall_floor=0.9)
    assert not strict.ok
    # Default floor leaves the honest baselines intact — green.
    assert run_surface_exam(pages).ok
