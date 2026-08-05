"""AI extraction entrypoint — turns raw source text into event_candidate rows.
Source: extracted from Entertainment-App-Code-v1-4 reference build (worker/ai_extract.py)

A page is not one event. A venue calendar can list dozens of shows, so this
module SEGMENTS a fetched page into per-event blocks (worker/segment.py) and
FANS OUT — running the UNCHANGED, golden-exam-certified single-event extractor
(ai/prompts.py + AIEventExtraction) once per block and creating one candidate +
one evidence row per extracted event. The certified extractor's prompt, schema,
and model are untouched: the multi-event capability lives entirely in the
un-bound segmentation + fan-out layer, so the extraction certification hash is
unaffected and extraction stays ON (EXTRACTION_THRESHOLD_RATIFIED stays True).

The single-event page is just the 1-block case, so behavior on pages we already
handle is unchanged. A page that HAD real text but yields ZERO events is a loud
signal (the source may have moved or reorganized its calendar), never a silent
drop: it fires the AI_EXTRACT_ZERO_EVENTS_SOURCE_MAY_HAVE_MOVED marker and still
records one flagged empty candidate for ops.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import copy
import inspect
import logging
import os

from pydantic import TypeAdapter, ValidationError

from ai.prompts import EXTRACTION_SYSTEM_PROMPT
from ai.provider import AIProvider
from worker.ai_models import AIEventExtraction
from worker.candidate_store import create_candidate, add_evidence, record_ai_degradation
from worker.date_callback import recover_dates_from_url
from worker.datetime_normalize import (
    normalize_datetime_claim,
    normalize_extracted_datetimes,
    preserve_discarded_claims,
    resolve_yearless_claim,
)
from worker.segment import segment_events

logger = logging.getLogger(__name__)

# Per-page AI-call COST CAP (FinOps, R-043). The multi-event fan-out makes ONE
# real extraction call per event block, so an unbounded page could make hundreds
# of calls — which silently defeated the per-run source ceiling (that caps PAGES,
# not calls). Capping calls PER PAGE restores a hard, predictable per-run bound:
# max_sources x this. Event blocks past the cap are DEFERRED (picked up on a
# later run) and LOGGED — never silently dropped. Env-tunable; the default is
# conservative and founder-tunable (the exact number is a FinOps decision).
_DEFAULT_MAX_EVENTS_PER_PAGE = 50


def _max_events_per_page() -> int:
    raw = os.environ.get("EXTRACT_MAX_EVENTS_PER_PAGE", "").strip()
    if not raw:
        return _DEFAULT_MAX_EVENTS_PER_PAGE
    try:
        n = int(raw)
    except ValueError:
        logger.warning("EXTRACT_MAX_EVENTS_PER_PAGE=%r is not an int — using default %d",
                       raw, _DEFAULT_MAX_EVENTS_PER_PAGE)
        return _DEFAULT_MAX_EVENTS_PER_PAGE
    return n if n >= 1 else _DEFAULT_MAX_EVENTS_PER_PAGE

# Meta keys the provider may attach (e.g. Claude provenance). These are NOT event
# fields, so they are separated out before pydantic validation (which would drop
# them) and merged back into the stored `extracted` jsonb afterwards, so the
# audit trail — which model/prompt/when produced this candidate — persists.
_META_PREFIX = "_"

# Characters that can CONTINUE a URL token. Used by the source-quoted-link
# guard: an extracted link only counts as quoted from the source when its
# occurrence in the block text is a COMPLETE token — not a prefix of a longer
# URL (evaluator blocker, PR #189 r3: `l in text` accepted ".../e/1" when the
# source only published ".../e/123", letting a hallucinated prefix-link fetch
# an unrelated page). "." and ")" etc. are technically valid URL characters,
# so a link followed by sentence punctuation is REFUSED too — fail-closed:
# the claim just stays honestly refused, dateless beats wrongly dated.
_URL_CONTINUATION = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "-._~%/?#&=+@:!$'()*,;")


def _link_source_quoted(link: str, text: str) -> bool:
    """True iff ``link`` appears in ``text`` as a complete URL token —
    both neighbours (where present) outside the URL character set."""
    start = 0
    while True:
        i = text.find(link, start)
        if i == -1:
            return False
        before_ok = i == 0 or text[i - 1] not in _URL_CONTINUATION
        j = i + len(link)
        after_ok = j >= len(text) or text[j] not in _URL_CONTINUATION
        if before_ok and after_ok:
            return True
        start = i + 1

# Greppable, structured marker logged when a page that HAD real text yields zero
# events across all its blocks. Ops/monitoring grep for this to find sources
# whose calendar may have moved or changed layout. Do NOT rename without
# updating the runbook/alerts that match on it.
SOURCE_MAY_HAVE_MOVED_MARKER = "AI_EXTRACT_ZERO_EVENTS_SOURCE_MAY_HAVE_MOVED"


@dataclass
class ExtractionOutcome:
    """Result of fanning one fetched page out into candidates.

    - ``candidate_ids``: every candidate created for this page (N for an
      N-event calendar; exactly one — a flagged empty candidate — for the
      zero-event case, so the legacy "always a row for ops" contract holds).
    - ``source_returned_empty``: True when the page had real text but the
      model found zero events in every block — the "source may have
      moved/changed" signal.
    """
    candidate_ids: List[str] = field(default_factory=list)
    source_returned_empty: bool = False


def _split_meta(d: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split a provider dict into (meta, event_fields) by the ``_`` prefix."""
    meta = {k: v for k, v in d.items() if k.startswith(_META_PREFIX)}
    fields = {k: v for k, v in d.items() if not k.startswith(_META_PREFIX)}
    return meta, fields


def _extract_kwargs_for(ai: AIProvider, source_name: str) -> Dict[str, Any]:
    """The certified extraction call's kwargs — built EXACTLY as the historical
    single-event path did, so the call is a byte-for-byte drop-in.

    The degradation audit hook / source_name are passed only to providers that
    accept them (the real Claude provider does; the minimal protocol stub does
    not), so the call stays a true drop-in across implementations.
    """
    extract_kwargs: Dict[str, Any] = {"system_prompt": EXTRACTION_SYSTEM_PROMPT}
    try:
        params = inspect.signature(ai.extract_event_json).parameters
        if "audit_hook" in params:
            extract_kwargs["audit_hook"] = record_ai_degradation
        if "source_name" in params:
            extract_kwargs["source_name"] = source_name
    except (TypeError, ValueError):
        pass
    return extract_kwargs


def _shape_and_store_one(
    event_fields: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    source_id: Optional[str],
    source_name: str,
    source_url: str,
    source_class: str,
    text: str,
    sxsw_mode: bool,
    fetched_at: Optional[datetime] = None,
) -> str:
    """Validate, R-021-normalize, and persist ONE event as candidate + evidence.

    ``meta`` is DEEP-COPIED first: events on the same page may share provider
    provenance, and the per-event mutations below (validation_error flag,
    unstored_datetime_claims) must never leak one event's refusals onto
    another's audit trail.
    """
    meta = copy.deepcopy(meta)

    # Validate/shape. A validation failure is NOT silently blanked: an empty
    # candidate that looks identical to "no event found" would hide a real
    # extraction bug (the silent-degradation anti-pattern banned project-wide,
    # cf. resolve_entities._fuzzy_match). We log loudly, tag the candidate as a
    # malformed extraction in its provenance, and still create a review row so
    # ops can see it rather than losing it.
    adapter = TypeAdapter(AIEventExtraction)
    try:
        shaped = adapter.validate_python(event_fields).model_dump()
    except ValidationError as exc:
        logger.error("AI extraction for source %r produced schema-invalid fields; "
                     "creating a flagged empty candidate for ops review rather than "
                     "silently dropping it. Errors: %s", source_name, exc.errors())
        shaped = AIEventExtraction().model_dump()
        prov = meta.get("_provenance")
        meta["_provenance"] = dict(prov) if isinstance(prov, dict) else {}
        meta["_provenance"]["validation_error"] = True
    # Default city when absent OR explicitly null (setdefault alone misses the
    # null case, which is the common one when the model finds no city).
    if not shaped.get("city"):
        shaped["city"] = "Austin"
    # R-021 (PR #43): store a timestamp ONLY when the extracted string
    # evidences a full calendar date — never fabricate one. Time-only
    # claims ("6pm") become NULL with the raw claim preserved in
    # provenance; the candidate row still reaches ops review, so no false
    # fact is asserted and no event is lost to a formatting detail. Applied
    # PER EVENT so each show's date claim is judged on its own text.
    discarded_times = normalize_extracted_datetimes(shaped)
    if discarded_times:
        # Date recovery, founder-directed 2026-08-05 ("more of a call back
        # position than a logic process"): (1) CALLBACK — read the explicit
        # machine-declared date off the event's own linked page; (2) only
        # then the year rule, for claims that are full dates minus the year.
        # Both re-enter the STRICT normalizer / the narrow year resolver, so
        # neither path can bypass the full-date bar; every recovery is
        # recorded in provenance with its method and basis.
        recovery: Dict[str, Dict[str, str]] = {}
        # The callback link must appear VERBATIM in the block text the event
        # was extracted from (evaluator finding, PR #189 r1: an AI-shaped
        # link the source never published — hallucinated or prompt-injected —
        # could point at an unrelated single-Event page and launder an
        # attacker-chosen date into "recovered evidence"), and as a COMPLETE
        # URL token (r3 blocker: substring matching accepted a prefix of a
        # longer source URL). A faithful extraction quotes the source's own
        # link exactly; anything else gets no callback and the claim
        # honestly stays refused.
        link = next((l for l in (shaped.get("ticket_link"),
                                 shaped.get("rsvp_link"))
                     if l and _link_source_quoted(l, text)), None)
        if link:
            recovered_raw = recover_dates_from_url(
                link, candidate_title=shaped.get("title"))
            for field, claim in recovered_raw.items():
                if field not in discarded_times:
                    continue
                normalized, refusal = normalize_datetime_claim(claim)
                if normalized and not refusal:
                    shaped[field] = normalized
                    recovery[field] = {"method": "detail-page-callback",
                                       "source": link, "raw": claim}
                    discarded_times.pop(field)
        # Year rule LAST, and ONLY against the SOURCE FETCH time threaded from
        # the fetch site (evaluator finding, PR #189 r2): no fetched_at means
        # no resolution — replay/backfill must never re-date a claim off this
        # worker's clock; the claim honestly stays refused instead.
        for field in list(discarded_times):
            if fetched_at is None:
                break
            if discarded_times[field].get("reason") != "no-full-date-evidence":
                continue
            normalized, note = resolve_yearless_claim(
                discarded_times[field].get("raw"), fetched_at)
            if normalized and note:
                shaped[field] = normalized
                recovery[field] = {"method": "year-from-fetch-date", **note}
                discarded_times.pop(field)
        if recovery:
            prov = meta.get("_provenance")
            meta["_provenance"] = dict(prov) if isinstance(prov, dict) else {}
            meta["_provenance"]["datetime_recovery"] = recovery
            logger.info("source %r: datetime claim(s) RECOVERED by %s",
                        source_name,
                        {f: r["method"] for f, r in recovery.items()})
    if discarded_times:
        logger.warning(
            "source %r: datetime claim(s) refused (stored as NULL, raw + "
            "reason preserved in provenance): %s",
            source_name, discarded_times,
        )
        # preserve_discarded_claims REPLACES a malformed _provenance rather
        # than silently skipping preservation (PR #44 r1 blocker) — the
        # malformed original is kept under _provenance_malformed_original.
        if preserve_discarded_claims(meta, discarded_times):
            logger.error(
                "source %r: _provenance was malformed (non-dict) — replaced "
                "so the unstored datetime claims stay preserved; original kept "
                "under _provenance_malformed_original.", source_name,
            )
    # Re-attach provider meta so it persists in the `extracted` jsonb column.
    shaped.update(meta)

    candidate_id = create_candidate(
        source_id=source_id,
        source_name=source_name,
        source_url=source_url,
        source_class=source_class,
        raw_text=text,
        extracted=shaped,
        sxsw_mode=sxsw_mode,
    )
    # Evidence from the originating source. In the fan-out, ``text`` is this
    # event's OWN block, so each candidate is backed by the exact text it was
    # extracted from — isolated per-event provenance, no cross-event leak.
    add_evidence(
        candidate_id=candidate_id,
        source_class=source_class,
        source_name=source_name,
        source_url=source_url,
        quote=text[:500],
    )
    return candidate_id


def extract_candidates(
    *,
    ai: AIProvider,
    text: str,
    source_class: str,
    source_name: str,
    source_url: str,
    sxsw_mode: bool = False,
    source_id: Optional[str] = None,
    fetched_at: Optional[datetime] = None,
) -> ExtractionOutcome:
    """Extract EVERY event on a page and fan out one candidate per event.

    Segments the page, then runs the UNCHANGED certified single-event extractor
    once per block. Returns an :class:`ExtractionOutcome`. A multi-event
    calendar creates N candidates; a single-event page, exactly one (unchanged
    behavior); a page that had real text but yielded zero events fires the
    moved/changed signal AND still records one flagged empty candidate, so the
    source is never silently dropped.
    """
    blocks = segment_events(text)
    # FinOps hard bound (R-043): one real extraction call per block, so cap the
    # calls PER PAGE. Overflow blocks are DEFERRED to a later run + LOGGED loudly,
    # never silently dropped — so a run's total AI spend stays max_sources x cap.
    cap = _max_events_per_page()
    if len(blocks) > cap:
        logger.warning(
            "extract_candidates: source %r segmented into %d event blocks; "
            "extracting the first %d this run (per-page AI-call cost cap "
            "EXTRACT_MAX_EVENTS_PER_PAGE=%d) — %d block(s) DEFERRED to a later run, "
            "NOT dropped (R-043).",
            source_name, len(blocks), cap, cap, len(blocks) - cap,
        )
        blocks = blocks[:cap]
    # AIEventExtraction (single-event) schema — the CERTIFIED shape, unchanged.
    schema = AIEventExtraction.model_json_schema()
    extract_kwargs = _extract_kwargs_for(ai, source_name)

    store_kwargs = dict(
        source_id=source_id,
        source_name=source_name,
        source_url=source_url,
        source_class=source_class,
        sxsw_mode=sxsw_mode,
        fetched_at=fetched_at,
    )
    outcome = ExtractionOutcome()

    for block in blocks:
        # One certified single-event extraction PER block. Same prompt, same
        # schema, same model as today — just run once per event on the page.
        raw = ai.extract_event_json(block, schema, **extract_kwargs) or {}
        meta, fields = _split_meta(raw)
        # A block that yields no content-bearing fields had no extractable event
        # (e.g. a footer/nav fragment caught by the split) — skip it. This is
        # NOT a silent drop of a real event; the whole-page zero-event case
        # below is the one that must be surfaced.
        if not any(v for v in fields.values()):
            continue
        outcome.candidate_ids.append(
            _shape_and_store_one(fields, meta, text=block, **store_kwargs)
        )

    if not outcome.candidate_ids:
        # Zero events across every block. Was there real text to extract FROM?
        # If yes, this is suspicious — the page changed or the source moved its
        # calendar — and must be surfaced loudly, not dropped. (A concurrent
        # ai_extraction_degraded audit row, written by the provider, is how a
        # transient provider failure is told apart from a genuine move.)
        page_had_text = bool(text and text.strip())
        empty_meta: Dict[str, Any] = {}
        if page_had_text:
            outcome.source_returned_empty = True
            logger.warning(
                "%s: source %r (%s) returned ZERO events from non-empty page "
                "text (%d chars) — the source may have MOVED or changed its "
                "calendar layout; recording a flagged empty candidate for ops "
                "follow-up rather than dropping it.",
                SOURCE_MAY_HAVE_MOVED_MARKER, source_name, source_url, len(text),
            )
            empty_meta["_provenance"] = {"source_returned_empty": True}
        # Preserve the legacy contract of always producing a candidate row for
        # ops (empty page text is normally stopped upstream by the sensor).
        outcome.candidate_ids.append(
            _shape_and_store_one({}, empty_meta, text=text, **store_kwargs)
        )

    return outcome


def extract_candidate(
    *,
    ai: AIProvider,
    text: str,
    source_class: str,
    source_name: str,
    source_url: str,
    sxsw_mode: bool = False,
    source_id: Optional[str] = None,
    fetched_at: Optional[datetime] = None,
) -> str:
    """Backward-compatible single-id entrypoint (used by worker/orchestrator.py).

    Fans the page out via :func:`extract_candidates` — so a calendar still
    produces N stored candidates — and returns the FIRST candidate id to keep
    the orchestrator's existing per-candidate gate/replay contract unchanged.
    Callers that need the full fan-out (and the moved/changed signal) should
    call :func:`extract_candidates` directly.
    """
    outcome = extract_candidates(
        ai=ai,
        text=text,
        source_class=source_class,
        source_name=source_name,
        source_url=source_url,
        sxsw_mode=sxsw_mode,
        source_id=source_id,
        fetched_at=fetched_at,
    )
    # extract_candidates always records at least one candidate (a flagged empty
    # one on the zero-event path), so there is always an id to return.
    return outcome.candidate_ids[0]
