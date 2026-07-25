#!/usr/bin/env python3
"""Automated surface regression-exam — a deterministic, free no-regression guard
on the extraction SURFACE code (worker/segment.py + worker/ai_extract.py).

WHAT THIS IS
------------
The attended golden-exam — the certified single-event prompt/model exam runner
in the ai/ package (named in docs/RECORD.md R-035 and CLAUDE.md) — certifies the
single-event extractor's PROMPT + MODEL against hallucination/recall thresholds.
It runs the
real ClaudeProvider and, by design, REFUSES to certify a PR that changes the
extraction harness surface — it cannot run code that did not exist when the
founder sat the exam. The compensating diff-review on such a PR checks the code
by eye but does NOT re-measure extraction QUALITY empirically. This module
closes exactly that gap for the SURFACE layer (segmentation / fan-out /
normalization), which is deliberately OUTSIDE the certified harness manifest.

It runs a labeled golden corpus of multi-event pages through the REAL
``worker.ai_extract.extract_candidates`` — the real segmenter, the real fan-out,
the real per-event normalization — using a RECORDED provider (no network, no
model, no spend). It then measures, per page:

  * event RECALL   — distinct labeled events the pipeline recovered / labeled
                     events on the page. A page passes only when recall does not
                     drop BELOW its recorded baseline (a one-way ratchet:
                     improving the segmenter RAISES a baseline, never lowers it).
  * FABRICATION    — any recovered event that matches NO labeled event. The bar
                     is absolute: zero fabrications, on every page.

WHAT THIS IS NOT
----------------
This is NOT a certification and carries NO authority over the certified
prompt/model. It never reads or writes EXTRACTION_THRESHOLD_RATIFIED,
CERTIFIED_HARNESS.json, or any HARNESS_MANIFEST-bound file, and it imports none
of the exam harness. The attended golden-exam remains the sole authority for the
certified extractor. This guard only proves the un-certified SURFACE code did
not get WORSE at recovering events — measured on labeled data with a recorded
provider.

THE RECORDED PROVIDER
---------------------
``RecordedSurfaceProvider`` mimics the certified SINGLE-event extractor: handed a
text block, it returns the fields of the FIRST labeled event whose ``signature``
appears in that block — most-prominent-first, one event per block, exactly the
certified extractor's contract. Crucially, if a block contains TWO signatures
(the segmenter under-segmented and merged two real events into one block), the
provider returns only the FIRST — the second event is LOST and recall drops.
That is the whole point: it turns a segmentation regression (the R-034 class:
under-segmentation) into a measurable recall drop, deterministically and for
free. What it CANNOT measure is real-model behavior on unsegmented prose (does
the live model read a second event out of a fused block?) — that is precisely
the attended exam's job, and this guard makes no claim about it.
"""
from __future__ import annotations

import contextlib
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

import worker.ai_extract as _ai_extract

# The objective content fields an AIEventExtraction carries (worker/ai_models.py).
# ``city`` is excluded on purpose: the pipeline defaults it to "Austin" on every
# candidate, so it is never evidence that a real event was recovered.
_CONTENT_FIELDS = (
    "title", "start_time", "end_time", "venue_name",
    "artist_names", "ticket_link", "rsvp_link",
)

DEFAULT_PAGES_PATH = (
    pathlib.Path(__file__).resolve().parent / "golden" / "surface" / "pages.json"
)

# Absolute recall floor applied UNDER the per-page baseline ratchet. Default 0.0
# is a no-op so honestly-low baselines (the R-034 hard cases) are never punished;
# a caller may raise it to impose a coarse global minimum, and raising it can
# only make the exam stricter, never looser.
DEFAULT_RECALL_FLOOR = 0.0


class RecordedSurfaceProvider:
    """A no-network stand-in for the certified single-event extractor.

    Returns the fields of the FIRST labeled event whose ``signature`` substring
    appears in the handed block (most-prominent-first, one event per block); a
    block with no matching signature yields ``None`` (the certified extractor's
    "no event found"). Two signatures in one block => only the first is returned
    => the second is lost => recall drops. That models the R-034 under-
    segmentation class as a measurable regression.
    """

    def __init__(self, expected_events: Iterable[Dict[str, Any]]):
        self._expected = list(expected_events)

    def extract_event_json(self, text, schema_json, system_prompt=None):
        for event in self._expected:
            signature = event["signature"]
            if signature in text:
                fields = {k: v for k, v in event.items() if k != "signature"}
                # Fail LOUD on an authoring error: the signature MUST be
                # recoverable from the shaped event, or recall matching (which
                # scans the stored candidate, not the raw block) is meaningless.
                if signature not in json.dumps(fields, ensure_ascii=False):
                    raise ValueError(
                        f"surface-exam corpus error: signature {signature!r} is "
                        f"not present in the labeled event fields {fields!r}; a "
                        f"signature must appear in the event it identifies."
                    )
                shaped = dict(fields)
                shaped.setdefault("_provenance", {"provider": "recorded-surface"})
                return shaped
        return None


@contextlib.contextmanager
def _captured_store():
    """Run the REAL extract_candidates with the candidate store stubbed out, so
    the exam touches no database. Captures each shaped ``extracted`` dict the
    pipeline would have persisted. Restores the real store on exit — the exam is
    single-threaded and deterministic, so save/restore is sufficient."""
    captured: List[Dict[str, Any]] = []

    def fake_create(**kwargs):
        captured.append(dict(kwargs.get("extracted") or {}))
        return f"surface-cand-{len(captured)}"

    def fake_evidence(**kwargs):
        return f"surface-ev-{len(captured)}"

    def fake_degradation(payload):
        return None

    originals = (
        _ai_extract.create_candidate,
        _ai_extract.add_evidence,
        _ai_extract.record_ai_degradation,
    )
    _ai_extract.create_candidate = fake_create
    _ai_extract.add_evidence = fake_evidence
    _ai_extract.record_ai_degradation = fake_degradation
    try:
        yield captured
    finally:
        (
            _ai_extract.create_candidate,
            _ai_extract.add_evidence,
            _ai_extract.record_ai_degradation,
        ) = originals


def _is_content_bearing(extracted: Dict[str, Any]) -> bool:
    """True when a stored candidate carries a real extracted fact. The zero-event
    flagged-empty candidate (all facts blank, city defaulted) is NOT a recovered
    event and is excluded from both recall and fabrication counting."""
    for k in _CONTENT_FIELDS:
        v = extracted.get(k)
        if v not in (None, "", [], {}):
            return True
    return False


@dataclass
class PageResult:
    id: str
    expected_count: int
    recovered_count: int
    recall: float
    baseline_recall: float
    effective_bar: float
    fabrications: List[str] = field(default_factory=list)

    @property
    def recall_ok(self) -> bool:
        # Float-safe: recall is a ratio of small integers (e.g. 1/3).
        return self.recall + 1e-9 >= self.effective_bar

    @property
    def fabrication_ok(self) -> bool:
        return not self.fabrications

    @property
    def ok(self) -> bool:
        return self.recall_ok and self.fabrication_ok


@dataclass
class ExamReport:
    pages: List[PageResult]
    min_recall_floor: float

    @property
    def ok(self) -> bool:
        return all(p.ok for p in self.pages)

    @property
    def fabrication_count(self) -> int:
        return sum(len(p.fabrications) for p in self.pages)

    @property
    def regressions(self) -> List[PageResult]:
        return [p for p in self.pages if not p.recall_ok]


def _run_page(page: Dict[str, Any]) -> PageResult:
    expected = page["expected_events"]
    if not expected:
        raise ValueError(f"surface-exam corpus error: page {page.get('id')!r} "
                         f"has no expected_events; a labeled page must label >= 1 event.")
    provider = RecordedSurfaceProvider(expected)
    with _captured_store() as captured:
        _ai_extract.extract_candidates(
            ai=provider,
            text=page["content"],
            source_class="surface_exam",
            source_name=str(page["id"]),
            source_url=f"surface-exam://{page['id']}",
        )

    # Every recovered event, serialized for signature matching. The full stored
    # dict is scanned (not just content fields) so a signature preserved only in
    # provenance — e.g. a time-only start moved there by normalization — still
    # counts as recovered.
    events = [c for c in captured if _is_content_bearing(c)]
    blobs = [json.dumps(c, ensure_ascii=False) for c in events]

    signatures = [e["signature"] for e in expected]
    matched = sum(1 for sig in signatures if any(sig in b for b in blobs))
    n = len(expected)
    recall = matched / n

    # A recovered event matching NO labeled signature is a fabrication.
    fabrications = [b for b in blobs if not any(sig in b for sig in signatures)]

    baseline = float(page.get("baseline_recall", 1.0))
    return PageResult(
        id=str(page["id"]),
        expected_count=n,
        recovered_count=matched,
        recall=recall,
        baseline_recall=baseline,
        effective_bar=baseline,  # replaced by run_surface_exam with the floor max
        fabrications=fabrications,
    )


def run_surface_exam(pages: Iterable[Dict[str, Any]], *,
                     min_recall_floor: float = DEFAULT_RECALL_FLOOR) -> ExamReport:
    """Run the whole labeled corpus through the real extraction surface.

    For each page: recall = distinct labeled events recovered / labeled events;
    a page passes when recall >= max(its baseline_recall, min_recall_floor) AND
    it produced zero fabrications. Returns a structured :class:`ExamReport`
    (per-page recall/baseline/pass-fail/fabrications + overall ``ok``); it does
    not raise on failure — callers decide the exit behavior.
    """
    results: List[PageResult] = []
    for page in pages:
        r = _run_page(page)
        r.effective_bar = max(r.baseline_recall, min_recall_floor)
        results.append(r)
    return ExamReport(pages=results, min_recall_floor=min_recall_floor)


def load_pages(path: pathlib.Path = DEFAULT_PAGES_PATH) -> List[Dict[str, Any]]:
    """Load the labeled corpus. Accepts either a bare JSON list or an object with
    a ``pages`` key. Fails LOUD on an empty or malformed corpus."""
    raw = pathlib.Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    pages = data["pages"] if isinstance(data, dict) else data
    if not isinstance(pages, list) or not pages:
        raise ValueError(f"surface-exam corpus at {path} is empty or malformed — "
                         f"a regression guard with no corpus proves nothing.")
    return pages
