#!/usr/bin/env python3
"""Class B multi-page follow — read the venue's calendar, not just its front door.

The ingestion loop fetches each registered source's start URL and stops. For a
class B source (public HTML, ONE-LIVE-COVERAGE-LAW.md) that start URL is almost
always a homepage, and a homepage is marketing copy — the schedule lives one
click away, behind the link the site itself labels "Events" or "Calendar". This
tool makes that click, under a hard budget, and hands what it finds to the
EXISTING extract path.

    start URL -> discover (worker.sourcing.page_discovery)
              -> fetch each page (worker.fetch.http_fetch.fetch_url)
              -> sensor (worker.sensors.assess_input)
              -> extract (worker.ai_extract.extract_candidates)

Nothing here is a new ingest stack: every stage above is the module the armed
scheduled loop already uses, called in the same order, and NO file the armed
cron executes is modified. What is new is the middle step — which pages get
offered to the loop — and the run report that makes it auditable.

RULES IT CANNOT BREAK

  * A wall ends the source. A 401/402/403/407/429, or a redirect to a sign-in
    page, on the start page OR on any followed page demotes the whole source to
    class D via worker.sourcing.source_class.demote_on_response: we stop
    following it that run, record the reason, and route it to the claim queue.
    We knock once. We never knock twice and we never work around it.
  * On-origin only. page_discovery drops every off-site link before this tool
    can fetch it — an off-site link is a different source with its own catalog
    row and its own access posture.
  * Bounded. --max-pages (default 15) caps the EXTRA pages per source per run;
    --limit-sources (default 10) caps the sources per run. Both are validated
    positive: a ceiling of 0 means no run, never "uncapped".

TWO MODES, because one of them cannot run everywhere

  --real       live network + live DB + live model: fetch_url writes its
               raw_fetch audit rows and extract_candidates writes candidates
               through the normal gate path. This is the honest run.
  (default)    dry run: discovery + sensor only. No DB, no model, no candidate
               rows. It reports pages that are EXTRACT-READY (fetched, sensor-
               passed) rather than candidates written, and says so in the table
               header — an "extract-ready" count is never printed as a candidate
               count.

  --fixtures DIR substitutes saved HTML for the network in either mode, so the
               discovery/wall/sensor logic can be exercised where outbound
               fetches are refused. A fixture run is labelled as such in every
               output it produces, and --update-claim-queue is REFUSED without
               --real: a fixture wall is not a real wall and must never enter
               the live claim queue.

Usage:
  python tools/class_b_multipage.py --fixtures tests/fixtures/class_b --limit-sources 10
  python tools/class_b_multipage.py --real --limit-sources 10 --max-pages 15
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.sourcing.page_discovery import (  # noqa: E402
    DEFAULT_MAX_PAGES, DiscoveryResult, discover_event_pages,
)
from worker.sourcing.source_class import (  # noqa: E402
    CLASS_B_PUBLIC_HTML, ClassVerdict, classify_entry, demote_on_response,
)

log = logging.getLogger("class_b_multipage")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CATALOG = os.path.join(REPO_ROOT, "sources", "master_sources_catalog_120.json")
DEFAULT_LIMIT_SOURCES = 10

#: Outcome tokens for one followed page. Constants so the report, the JSON
#: evidence and the tests all name the same string.
PAGE_OK = "ok"
PAGE_MISSING = "missing"          # 404 / gone — a guess that did not pay off
PAGE_WALL = "wall"                # 401/402/403/407/429 or a sign-in redirect
PAGE_ERROR = "error"              # transport failure — NOT a wall, not a miss
PAGE_SENSOR_REJECTED = "sensor_rejected"


@dataclass
class PageOutcome:
    url: str
    via: str
    status: Optional[int]
    outcome: str
    detail: str = ""
    candidates: int = 0
    extract_error: str = ""


@dataclass
class SourceOutcome:
    """One source's whole run — everything the PR table needs, plus evidence."""

    source_id: str
    name: str
    start_url: str
    source_class: str
    pages_followed: List[PageOutcome] = field(default_factory=list)
    candidates: int = 0
    extract_ready: int = 0
    blocked_reason: str = ""
    discovery: Optional[DiscoveryResult] = None
    start_status: Optional[int] = None
    extract_errors: List[str] = field(default_factory=list)

    @property
    def followed_ok(self) -> int:
        return sum(1 for p in self.pages_followed if p.outcome in (PAGE_OK, PAGE_SENSOR_REJECTED))


@dataclass
class FetchOutcome:
    """What one GET produced. `status` is None when the transport never answered."""

    url: str
    status: Optional[int] = None
    text: str = ""
    content_type: Optional[str] = None
    final_url: Optional[str] = None
    error: Optional[str] = None


class FixtureFetcher:
    """Serves saved HTML from disk, keyed by URL through a manifest.

    Manifest shape (`<dir>/manifest.json`), one entry per URL the run may ask
    for:

        {"https://venue.example/": {"file": "venue_home.html", "status": 200},
         "https://venue.example/events": {"file": "venue_events.html"},
         "https://walled.example/": {"status": 403}}

    A URL absent from the manifest answers 404 — the honest result for a
    common-path GUESS that the site does not serve, which is exactly the case
    the guesses exist to test.
    """

    def __init__(self, directory: str) -> None:
        self.directory = directory
        manifest_path = os.path.join(directory, "manifest.json")
        with open(manifest_path, encoding="utf-8") as handle:
            self.manifest: Dict[str, Any] = json.load(handle)
        if not isinstance(self.manifest, dict):
            raise ValueError(f"{manifest_path}: expected a JSON object of url -> entry")

    def get(self, url: str) -> FetchOutcome:
        entry = self.manifest.get(url)
        if entry is None:
            return FetchOutcome(url=url, status=404)
        status = int(entry.get("status", 200))
        if entry.get("final_url"):
            return FetchOutcome(url=url, status=status, final_url=entry["final_url"])
        if status != 200 or not entry.get("file"):
            return FetchOutcome(url=url, status=status)
        with open(os.path.join(self.directory, entry["file"]), encoding="utf-8") as handle:
            text = handle.read()
        return FetchOutcome(
            url=url, status=status, text=text,
            content_type=entry.get("content_type", "text/html; charset=utf-8"),
        )


class LiveFetcher:
    """The EXISTING http adapter (worker.fetch.http_fetch.fetch_url).

    Imported lazily so the dry-run/fixture path never needs psycopg2 or a DSN.
    fetch_url raises on a non-2xx; the HTTP status is recovered from the
    requests exception so a wall is CLASSIFIED rather than lost as a generic
    error — that distinction is the whole of Coverage Law's class-D rule.
    """

    def __init__(self, source_id: Optional[str]) -> None:
        from worker.fetch.http_fetch import fetch_url  # noqa: PLC0415

        self._fetch_url = fetch_url
        self.source_id = source_id

    def get(self, url: str) -> FetchOutcome:
        try:
            result = self._fetch_url(source_id=self.source_id, url=url)
        except Exception as exc:  # noqa: BLE001 — every failure is classified below
            response = getattr(exc, "response", None)
            status = getattr(response, "status_code", None)
            final_url = getattr(response, "url", None)
            return FetchOutcome(
                url=url, status=status, final_url=final_url, error=f"{type(exc).__name__}: {exc}",
            )
        if result.get("status") == "not_modified":
            return FetchOutcome(url=url, status=304)
        storage_ref = result.get("storage_ref")
        text = ""
        if storage_ref:
            with open(storage_ref, "rb") as handle:
                text = handle.read().decode("utf-8", errors="replace")
        return FetchOutcome(
            url=url, status=200, text=text, content_type=result.get("content_type"),
        )


def _positive_int(raw: str) -> int:
    """A budget ceiling is positive or it is rejected — 0/negative must never
    read as "uncapped" (the project-wide fail-closed budget rule)."""
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError(
            f"{value} is not a valid ceiling — must be a positive integer; 0 does "
            "not mean uncapped, it means no run."
        )
    return value


def load_catalog(path: str) -> List[Dict[str, Any]]:
    """Read the source catalog. Fails LOUD — a missing catalog is never an empty
    source list, which would read as "nothing to follow"."""
    with open(path, encoding="utf-8") as handle:
        catalog = json.load(handle)
    if not isinstance(catalog, list):
        raise ValueError(f"{path}: expected a JSON list of source entries")
    return catalog


def select_class_b(catalog: List[Dict[str, Any]], *, limit: int,
                   only_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Class B entries that already carry a start URL, in catalog (rank) order.

    The class comes from the catalog's OWN declared access fields via
    classify_entry — never from a guess about the site — so a source this run
    follows is a source a human classified as publicly readable.
    """
    wanted = set(only_ids or [])
    out: List[Dict[str, Any]] = []
    for entry in catalog:
        if wanted and str(entry.get("id") or "") not in wanted:
            continue
        if not entry.get("base_url"):
            continue
        if classify_entry(entry).source_class != CLASS_B_PUBLIC_HTML:
            continue
        out.append(entry)
        if len(out) >= limit:
            break
    return out


def _wall_verdict(verdict: ClassVerdict, fetched: FetchOutcome) -> ClassVerdict:
    """Apply the EXISTING wall rule to one response (no second implementation)."""
    return demote_on_response(
        verdict,
        status=fetched.status,
        final_url=fetched.final_url,
        error=fetched.error,
    )


def run_source(
    entry: Dict[str, Any],
    fetcher: Any,
    *,
    max_pages: int,
    extract: Optional[str] = None,
) -> SourceOutcome:
    """Follow ONE source: start page -> discovery -> up to max_pages sub-pages.

    A wall anywhere stops this source immediately (Coverage Law: knock once).
    A 404/error on a followed page is recorded and the walk CONTINUES — a
    missing guess is not a wall, and one broken page must not cost the rest of
    a venue's calendar.
    """
    from worker.sensors import assess_input  # noqa: PLC0415 — pure, but keeps import cost at call time

    verdict = classify_entry(entry)
    outcome = SourceOutcome(
        source_id=str(entry.get("id") or ""),
        name=str(entry.get("name") or entry.get("id") or "(unnamed)"),
        start_url=str(entry.get("base_url")),
        source_class=verdict.source_class,
    )

    start = fetcher.get(outcome.start_url)
    outcome.start_status = start.status
    walled = _wall_verdict(verdict, start)
    if walled.is_closed_door:
        outcome.source_class = walled.source_class
        outcome.blocked_reason = walled.reason
        return outcome
    if start.status != 200 or not start.text:
        outcome.blocked_reason = (
            f"start page returned HTTP {start.status} with no readable body"
            + (f" ({start.error})" if start.error else "")
        )
        return outcome

    discovery = discover_event_pages(start.text, outcome.start_url, limit=max_pages)
    outcome.discovery = discovery

    for page in discovery.pages:
        fetched = fetcher.get(page.url)
        walled = _wall_verdict(verdict, fetched)
        if walled.is_closed_door:
            # A wall on a sub-page walls the SOURCE: we stop following it this
            # run and it goes to the claim queue with the reason recorded.
            outcome.source_class = walled.source_class
            outcome.blocked_reason = f"{walled.reason} (at {page.url})"
            outcome.pages_followed.append(PageOutcome(
                url=page.url, via=page.via, status=fetched.status,
                outcome=PAGE_WALL, detail=walled.reason,
            ))
            return outcome
        if fetched.error or fetched.status is None:
            outcome.pages_followed.append(PageOutcome(
                url=page.url, via=page.via, status=fetched.status,
                outcome=PAGE_ERROR, detail=fetched.error or "no response",
            ))
            continue
        if fetched.status != 200 or not fetched.text:
            outcome.pages_followed.append(PageOutcome(
                url=page.url, via=page.via, status=fetched.status,
                outcome=PAGE_MISSING, detail=f"HTTP {fetched.status}",
            ))
            continue

        reading = assess_input(text=fetched.text, content_type=fetched.content_type)
        if not reading.ok:
            outcome.pages_followed.append(PageOutcome(
                url=page.url, via=page.via, status=fetched.status,
                outcome=PAGE_SENSOR_REJECTED, detail=reading.reason,
            ))
            continue

        page_outcome = PageOutcome(
            url=page.url, via=page.via, status=fetched.status, outcome=PAGE_OK,
        )
        outcome.extract_ready += 1
        if extract:
            written, error = _extract_page(
                entry=entry, url=page.url, text=fetched.text,
                source_class=verdict.source_class, provider=extract,
            )
            page_outcome.candidates = written
            outcome.candidates += written
            if error:
                page_outcome.extract_error = error
                if error not in outcome.extract_errors:
                    outcome.extract_errors.append(error)
        outcome.pages_followed.append(page_outcome)

    return outcome


#: Providers this tool may hand to the existing extract path. Both already exist
#: in the repo — `claude` is the production extractor the scheduled loop uses,
#: `stub` is the no-model provider `worker/run_once.py` uses for its offline
#: smoke path. Nothing new is written here: adding an extractor is out of scope,
#: and a hand-written provider that returned invented fields would be
#: fabricating extraction results, which is worse than reporting a zero.
PROVIDER_CLAUDE = "claude"
PROVIDER_STUB = "stub"
PROVIDERS = (PROVIDER_CLAUDE, PROVIDER_STUB)


def _build_provider(name: str):
    """Return the named EXISTING provider. Imported lazily so the no-extract
    path never needs the model SDK."""
    if name == PROVIDER_STUB:
        from ai.bedrock_provider import BedrockProvider  # noqa: PLC0415

        return BedrockProvider(client=None, model_id="stub")
    from ai.claude_provider import ClaudeProvider  # noqa: PLC0415

    return ClaudeProvider()


def _failure_line(exc: BaseException) -> str:
    """One line naming WHERE extraction died: file, function, error.

    Read off the deepest traceback frame rather than the raise site, because
    the useful answer to "why did this fixture not extract?" is the function
    that actually refused, not the caller that asked.
    """
    tb = exc.__traceback__
    filename, funcname = "(unknown)", "(unknown)"
    while tb is not None:
        frame = tb.tb_frame
        try:
            filename = os.path.relpath(frame.f_code.co_filename, REPO_ROOT)
        except ValueError:
            filename = frame.f_code.co_filename
        funcname = frame.f_code.co_name
        tb = tb.tb_next
    message = " ".join(str(exc).split())
    return f"{filename}, {funcname}, {type(exc).__name__}: {message}"


def _extract_page(
    *, entry: Dict[str, Any], url: str, text: str, source_class: str, provider: str,
) -> tuple:
    """Hand ONE fetched page to the EXISTING extract path and count what it wrote.

    This is worker.ai_extract.extract_candidates — the same call the scheduled
    loop makes, with the same prompt, the same schema and the same per-page
    fan-out cap. This tool adds no extraction logic of its own; it only changes
    WHICH page the certified path is pointed at.

    Returns (candidates_written, failure_line). A failure is CAUGHT and reported
    per page rather than killing the walk, because "this fixture could not
    extract, and here is the file/function/error" is the answer the run table
    owes; a traceback that ends the run reports nothing about the other pages.
    """
    from worker.ai_extract import extract_candidates  # noqa: PLC0415

    try:
        result = extract_candidates(
            ai=_build_provider(provider),
            text=text,
            source_class=source_class,
            source_name=str(entry.get("name") or entry.get("id") or url),
            source_url=url,
            source_id=entry.get("source_id"),
        )
    except Exception as exc:  # noqa: BLE001 — reported, never swallowed
        line = _failure_line(exc)
        log.error("extract FAILED for %s — %s", url, line)
        return 0, line
    return len(getattr(result, "candidate_ids", []) or []), ""


def _cell(value: str) -> str:
    """Make a value safe inside a markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def render_table(outcomes: List[SourceOutcome], *, extract: Optional[str],
                 fixtures: bool) -> str:
    """The founder's run table, exactly as commissioned:

        source | start URL | pages followed | candidates | blocked reason

    When extraction ran, `candidates` is a NUMBER — the rows the existing
    extract path actually wrote. A zero is followed by the reason it is zero,
    one line per distinct failure: file, function, error. When extraction did
    not run at all, the column header says so rather than printing a zero that
    would read as "extraction found nothing".
    """
    header = "candidates" if extract else "candidates (extract not run)"
    lines = [
        f"| source | start URL | pages followed | {header} | blocked reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for o in outcomes:
        if extract:
            candidates = str(o.candidates)
        else:
            candidates = f"— ({o.extract_ready} extract-ready)"
        lines.append(
            f"| {_cell(o.name)} | <{o.start_url}> | {o.followed_ok} | "
            f"{candidates} | {_cell(o.blocked_reason) or '—'} |"
        )

    note: List[str] = []
    if extract:
        failures: List[str] = []
        for o in outcomes:
            for error in o.extract_errors:
                if error not in failures:
                    failures.append(error)
        if failures:
            note += [
                "",
                "**Why those are zero — file, function, error:**",
                "",
            ]
            note += [f"- `{f}`" for f in failures]
    if fixtures:
        note += [
            "",
            "_Fixture run: pages came from saved HTML on disk, not from the live "
            "sites — every number above is the code path's verdict on that "
            "fixture, not a claim about a site today._",
        ]
    if not extract:
        note += [
            "",
            "_Extraction did not run. \"extract-ready\" counts pages that fetched "
            "and passed the input-quality sensor — the pages that WOULD be handed "
            "to it._",
        ]
    return "\n".join(lines + note)


def _as_json(outcomes: List[SourceOutcome]) -> str:
    def page(p: PageOutcome) -> Dict[str, Any]:
        return {
            "url": p.url, "via": p.via, "status": p.status,
            "outcome": p.outcome, "detail": p.detail, "candidates": p.candidates,
            "extract_error": p.extract_error,
        }

    payload = []
    for o in outcomes:
        row: Dict[str, Any] = {
            "source_id": o.source_id,
            "name": o.name,
            "start_url": o.start_url,
            "source_class": o.source_class,
            "start_status": o.start_status,
            "pages_followed": [page(p) for p in o.pages_followed],
            "candidates": o.candidates,
            "extract_ready": o.extract_ready,
            "extract_errors": o.extract_errors,
            "blocked_reason": o.blocked_reason,
        }
        if o.discovery is not None:
            row["discovered"] = [
                {"url": p.url, "via": p.via, "evidence": p.evidence}
                for p in o.discovery.pages
            ]
            row["ics_links"] = o.discovery.ics_links
            row["jsonld_events"] = o.discovery.jsonld_events
            row["skipped"] = [
                {"url": u, "reason": r} for u, r in o.discovery.skipped
            ]
        payload.append(row)
    return json.dumps(payload, indent=2, sort_keys=True)


def observed_class_d_rows(outcomes: List[SourceOutcome]) -> List[Any]:
    """Walls this run OBSERVED, as claim-queue rows (the existing queue's shape).

    Imported lazily from tools.class_d_queue so the queue document stays the one
    authority on how a class-D row is written and suggested.
    """
    from tools.class_d_queue import ORIGIN_OBSERVED, QueueRow, suggest_path  # noqa: PLC0415
    from worker.sourcing.source_class import ClassVerdict as _CV  # noqa: PLC0415

    rows = []
    for o in outcomes:
        if o.source_class != "D" or not o.blocked_reason:
            continue
        entry = {"name": o.name, "id": o.source_id, "base_url": o.start_url}
        verdict = _CV("D", o.blocked_reason, False)
        rows.append(QueueRow(
            source_id=o.source_id, name=o.name, url=o.start_url,
            why=o.blocked_reason, origin=ORIGIN_OBSERVED,
            suggested_path=suggest_path(entry, verdict),
        ))
    return rows


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalog", default=DEFAULT_CATALOG)
    parser.add_argument("--limit-sources", type=_positive_int, default=DEFAULT_LIMIT_SOURCES,
                        help="max class B sources this run (default 10)")
    parser.add_argument("--max-pages", type=_positive_int, default=DEFAULT_MAX_PAGES,
                        help="max EXTRA pages followed per source per run (default 15)")
    parser.add_argument("--source-id", action="append", default=None,
                        help="restrict to these catalog ids (repeatable)")
    parser.add_argument("--fixtures", default=None,
                        help="serve pages from a fixture directory instead of the network")
    parser.add_argument("--real", action="store_true",
                        help="live fetch through worker.fetch.http_fetch (needs a DSN); "
                             "implies --extract unless --no-extract is given")
    parser.add_argument("--extract", dest="extract", action="store_true", default=None,
                        help="run the EXISTING worker.ai_extract.extract_candidates on "
                             "every extract-ready page (needs a DSN; the claude provider "
                             "also needs ANTHROPIC_API_KEY)")
    parser.add_argument("--no-extract", dest="extract", action="store_false",
                        help="discovery + sensor only; write no candidate rows")
    parser.add_argument("--provider", choices=PROVIDERS, default=PROVIDER_CLAUDE,
                        help="which EXISTING provider the extract path uses "
                             f"(default {PROVIDER_CLAUDE}, the production extractor)")
    parser.add_argument("--update-claim-queue", action="store_true",
                        help="write observed walls into docs/CLASS_D_CLAIM_QUEUE.md (requires --real)")
    parser.add_argument("--json-out", default=None, help="write the full run evidence as JSON")
    parser.add_argument("--table-out", default=None, help="write the markdown table here")
    args = parser.parse_args(argv)

    extract = args.provider if (args.extract or (args.real and args.extract is None)) else None

    if args.update_claim_queue and not args.real:
        parser.error(
            "--update-claim-queue requires --real: a wall seen in a fixture is not "
            "a wall a site put up, and must never enter the live claim queue."
        )

    catalog = load_catalog(args.catalog)
    selected = select_class_b(catalog, limit=args.limit_sources, only_ids=args.source_id)
    if not selected:
        log.error("no class B source with a start URL matched — nothing to follow.")
        return 1

    outcomes: List[SourceOutcome] = []
    for entry in selected:
        fetcher = (FixtureFetcher(args.fixtures) if args.fixtures
                   else LiveFetcher(entry.get("source_id")))
        outcomes.append(run_source(
            entry, fetcher, max_pages=args.max_pages, extract=extract,
        ))

    table = render_table(outcomes, extract=extract, fixtures=bool(args.fixtures))
    print(table)
    if args.table_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.table_out)), exist_ok=True)
        with open(args.table_out, "w", encoding="utf-8") as handle:
            handle.write(table + "\n")
    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)), exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as handle:
            handle.write(_as_json(outcomes) + "\n")

    if args.update_claim_queue:
        from tools.class_d_queue import write_queue  # noqa: PLC0415

        observed = observed_class_d_rows(outcomes)
        written = write_queue(args.catalog, observed=observed)
        log.info("claim queue updated: %d row(s), %d observed this run",
                 written, len(observed))

    followed = sum(o.followed_ok for o in outcomes)
    walled = sum(1 for o in outcomes if o.source_class == "D")
    log.info("%d source(s): %d page(s) followed, %d walled -> claim queue",
             len(outcomes), followed, walled)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
