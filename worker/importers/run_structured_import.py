#!/usr/bin/env python3
"""Run the structured first-party feed import: read the master source catalog →
select entries that plausibly publish a machine-readable calendar (ICS / JSON-LD)
→ fetch + parse + classify each into the 22 cultural domains → upsert into
`licensed_event`. Deterministic, no AI. Runs on GitHub Actions (egress reaches the
public calendars; the dev sandbox is network-blocked).

These are FIRST-PARTY sources (venue / university / library / civic / museum) that
publish their OWN schedule as structured data — an authoritative anchor, so rows
are 'confirmed' by construction and flow through the separate licensed_event store
WITHOUT the AI-extraction / human-promote path.

Fail-loud discipline:
  * Missing DSN on a real (non-dry-run) write fails LOUD (worker.db_config).
  * ONE source yielding zero events does NOT fail the run — it is LOGGED (a venue
    calendar can legitimately be empty or briefly unreachable; the others still
    land). But if EVERY selected source yields zero, that is a systemic breakage
    (bad selection, an API-shape/JSON-LD-markup change across the board, or
    normalization drift) — the run FAILS, never a silent green no-op.

Usage:
  python -m worker.importers.run_structured_import [--catalog PATH] [--only id,id]
      [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import logging
import pathlib
from collections import Counter

from worker.db_config import resolve_dsn
from worker.importers.structured_feed import (
    PROVIDER_ICS,
    PROVIDER_JSONLD,
    PROVIDER_PLATFORM_JSON,
    import_source,
)

log = logging.getLogger("structured_import")

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_CATALOG = REPO / "sources" / "master_sources_catalog_120.json"

# `allowed`/`access_method` tokens that indicate a source plausibly exposes a
# machine-readable calendar (ICS or JSON-LD). Conservative on PURPOSE: we only
# reach for sources that advertise structured data, never every public web page.
_STRUCTURED_ALLOWED = {
    "ics_feed_if_offered", "localist_json_feed", "feed_if_offered",
    "ics_upload", "partner_export", "official_feed",
    # The curated local-moat rows (ranks 77-114) carry this token: a verified
    # first-party events page whose EXACT machine-readable feed path is not yet
    # confirmed. Including it is what makes the moat actually import — without
    # it those 38 sources sat in the catalog and were never fetched (found
    # 2026-07-25 when the founder asked "Only 40?"). Safe by construction:
    # import_source auto-detects ICS vs embedded JSON-LD, and a source that
    # exposes neither yields 0 events, which the main loop below logs per source
    # ("yielded 0 events (<url>) — logged, not fatal", named again in the
    # summary's zero-sources tally) rather than failing the run.
    "structured_feed_verify",
}
_STRUCTURED_ACCESS_TOKENS = ("ics", "localist", "feed")


# ---- provider ASSERTIONS from catalog data -----------------------------------
#
# Every `allowed` token in the catalog is classified here: either it ASSERTS a
# wire format (value = the provider) or it does not (value = None). This is the
# join that makes structured_feed.ProviderMismatch real in production — without
# it the fail-loud-on-misconfigured-source guard only fired for direct callers
# and monkeypatched tests, so a wrongly-pointed source still auto-sniffed and
# was counted as "yielded zero" (evaluator blocker r9, PR #68).
#
# The table is DELIBERATELY sparse, and that is the honest reading of the data,
# not timidity: a token spelled `*_if_offered` or `*_verify` says a feed MIGHT
# exist, which is the opposite of a format claim. Asserting a provider from one
# of those would manufacture false ProviderMismatch failures for every venue
# tagged `ics_feed_if_offered` that in fact serves embedded JSON-LD — turning a
# working source into a reported defect. Only `localist_json_feed` names its
# format outright, so today exactly one token asserts.
#
# COMPLETENESS IS TEST-DERIVED, not hand-maintained: a test cross-checks this
# table against every token present in the real catalog, so a future row adding
# e.g. `tribe_json_feed` fails the suite until it is classified here. That is
# the standing response to the incomplete-enumeration class (docs/metrics/
# KAIZEN_LEDGER.md class watch): a hand-kept trust-guarding list gets a
# derivation test, never a fourth hand-audit.
_TOKEN_PROVIDER_CLASSIFICATION: dict[str, str | None] = {
    # ASSERTS a format — drives provider_hint, so a mismatch FAILS the source.
    "localist_json_feed": PROVIDER_PLATFORM_JSON,
    # Conditional or format-free — no assertion, so import_source sniffs.
    "public_calendar_pages": None,
    "structured_feed_verify": None,
    "public_pages": None,
    "public_event_pages": None,
    "feed_if_offered": None,
    "partner_feed": None,
    "api_access": None,
    "oauth_api": None,
    "ics_feed_if_offered": None,
    "opt_in_links": None,
    "jsonld_if_offered": None,
    "partner_access": None,
    "manual_benchmark": None,
    "official_feed": None,
    "partner_export": None,
    "ics_upload": None,
    "csv_upload": None,
    "opt_in_email_parse": None,
    "open_data_lucene_search": None,
}

# Named so the derivation test can assert these are the only providers reachable
# from catalog data (a typo'd value would otherwise raise deep inside a fetch).
_ASSERTABLE_PROVIDERS = (PROVIDER_ICS, PROVIDER_JSONLD, PROVIDER_PLATFORM_JSON)


def provider_hint_for(entry: dict) -> str | None:
    """The wire format this catalog row ASSERTS, or None when it asserts none.

    None is the common and correct answer: most rows say "a feed may exist here",
    which import_source resolves by sniffing. A returned provider is a claim the
    source must honour — if nothing fetched is that format, import_source raises
    ProviderMismatch and the source is reported FAILED, not empty.

    Unknown tokens are ignored (they assert nothing); the derivation test, not a
    runtime guess, is what keeps the table complete.
    """
    hints = {
        _TOKEN_PROVIDER_CLASSIFICATION.get(str(a).lower())
        for a in (entry.get("allowed") or [])
    }
    hints.discard(None)
    if len(hints) != 1:
        # Zero assertions is the normal case. TWO conflicting assertions is a
        # catalog contradiction we must not resolve by picking one — fall back to
        # sniffing and say so, rather than enforcing an arbitrary half of it.
        if len(hints) > 1:
            log.warning("source %s asserts CONFLICTING providers %s — no assertion "
                        "enforced; auto-detecting instead. Fix the catalog row.",
                        entry.get("id"), sorted(hints))
        return None
    return hints.pop()


def _is_structured_candidate(entry: dict) -> bool:
    """True when a catalog entry advertises a structured calendar AND has a URL to
    fetch. base_url may be an HTML calendar page — import_source auto-detects and
    parses whatever embedded JSON-LD (or a served .ics) it finds."""
    if not entry.get("base_url"):
        return False
    allowed = {str(a).lower() for a in (entry.get("allowed") or [])}
    if allowed & _STRUCTURED_ALLOWED:
        return True
    access = str(entry.get("access_method") or "").lower()
    return any(tok in access for tok in _STRUCTURED_ACCESS_TOKENS)


def _select(catalog: list[dict], only: set[str], limit: int | None) -> list[dict]:
    picks = [e for e in catalog if _is_structured_candidate(e)]
    if only:
        picks = [e for e in picks if str(e.get("id")) in only]
    if limit is not None:
        picks = picks[:limit]
    return picks


# Exit code 4 = the import ran and wrote what it could, but one or more sources
# FAILED (denied / throttled / unreachable / TLS / unexpected). Distinct from 3
# (systemic zero-events) so an operator can tell "partly blocked" from "broken".
_EXIT_SOURCE_FAILURES = 4


# ONLY these are recoverable per-source: the network/host/policy failure classes
# an importer must expect. A broad `except Exception` here (which I wrote in r6)
# demoted arbitrary PROGRAMMER BUGS — a TypeError in the parser, say — into a
# per-source "FETCH FAILED" record that --allow-partial could then exit 0 on
# (evaluator blocker r7, PR #68). Bugs must crash the run, loudly.
_RECOVERABLE_SOURCE_ERRORS = (OSError,)   # incl. HTTPError, URLError, SSLError,
                                          # socket.timeout, RobotsDisallowed


def _exit_code(failed_sources: list, allow_partial: bool) -> int:
    """Fail the command when any source FAILED.

    Evaluator blocker r6: failures were logged and named but the process still
    exited 0, so an import gate could pass green while sources were refused. A
    warning in a successful run is not fail-loud. --allow-partial is the explicit,
    separately-named opt-in for "I know some sources are blocked, proceed".
    """
    if not failed_sources:
        return 0
    if allow_partial:
        log.warning("%d source(s) FAILED but --allow-partial was given — exiting 0 "
                    "DELIBERATELY: %s", len(failed_sources), ", ".join(failed_sources))
        return 0
    log.error("%d source(s) FAILED (%s). Exiting non-zero: a failed source must not "
              "pass as a successful import. Pass --allow-partial to accept a partial "
              "import deliberately.", len(failed_sources), ", ".join(failed_sources))
    return _EXIT_SOURCE_FAILURES


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", default=str(DEFAULT_CATALOG),
                    help="path to the master source catalog JSON")
    ap.add_argument("--only", default="",
                    help="comma-separated catalog ids to restrict to (subset of the "
                         "structured candidates)")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap the number of sources fetched (smoke runs)")
    ap.add_argument("--allow-partial", action="store_true",
                    help="exit 0 even when some sources FAILED (denied/throttled/"
                         "unreachable). Off by default: a failed source must make "
                         "the command fail, or an import gate can pass green while "
                         "sources were refused (evaluator blocker r6).")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch + parse + summarize, but do NOT write the DB")
    args = ap.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        log.error("--limit must be >= 1 — failing closed.")
        return 2

    catalog_path = pathlib.Path(args.catalog)
    if not catalog_path.exists():
        log.error("catalog %s does not exist — cannot select sources. Failing closed.",
                  catalog_path)
        return 2
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        log.error("catalog %s is not valid JSON (%s) — failing closed.", catalog_path, exc)
        return 2

    only = {t.strip() for t in args.only.split(",") if t.strip()}
    sources = _select(catalog, only, args.limit)
    if not sources:
        log.error("no structured-feed candidates selected from %s (only=%s) — the "
                  "catalog has no ICS/JSON-LD sources matching, or --only excluded "
                  "them all. Failing closed.", catalog_path, sorted(only) or "-")
        return 2

    log.info("scope: %d first-party structured-feed source(s) (ICS / JSON-LD) from %s",
             len(sources), catalog_path.name)

    all_norm: list[dict] = []
    per_source: Counter = Counter()
    zero_sources: list[str] = []
    # FAILED is not EMPTY. Counting a source that errored into `zero_sources`
    # made "N yielded zero" silently mix hosts that REFUSED us with calendars
    # that genuinely had nothing on — the same failure-as-success class the
    # evaluator flagged inside import_source (self-audit, PR #68 r4).
    failed_sources: list[str] = []

    for entry in sources:
        sid = str(entry.get("id"))
        url = entry.get("base_url")
        domain_hint = entry.get("cultural_domain")
        # Carry the catalog's format ASSERTION (if the row makes one) into the
        # fetch, so a wrongly-pointed source fails loudly here instead of being
        # tallied among the quiet calendars.
        hint = provider_hint_for(entry)
        try:
            norm = import_source(url, source_name=sid, cultural_domain=domain_hint,
                                 provider_hint=hint)
        except _RECOVERABLE_SOURCE_ERRORS as exc:
            # A single source being unreachable is logged, not fatal — the others
            # still import. (Not a swallowed error: it is surfaced in the run log.)
            # Not swallowed: recorded as a FAILED source, named in the summary,
            # and (unless --allow-partial) it makes this command EXIT NON-ZERO.
            log.warning("source %-26s FETCH FAILED (%s): %s: %s",
                        sid, url, type(exc).__name__, exc)
            failed_sources.append(sid)
            continue
        per_source[sid] = len(norm)
        if not norm:
            log.warning("source %-26s yielded 0 events (%s) — logged, not fatal.", sid, url)
            zero_sources.append(sid)
            continue
        log.info("source %-26s %4d events  (%s)", sid, len(norm), domain_hint or "unclassified")
        all_norm.extend(norm)

    by_domain = Counter(n["category"] for n in all_norm)
    by_provider = Counter(n["source_provider"] for n in all_norm)
    log.info("Structured import: %d source(s) selected, %d FAILED, %d yielded zero, "
             "%d events total",
             len(sources), len(failed_sources), len(zero_sources), len(all_norm))
    if failed_sources:
        # Named, not just counted: a refusal/throttle/TLS failure is actionable
        # (it routes that source to a different acquisition path), an empty
        # calendar is not.
        log.warning("FAILED sources (denied, throttled, or unreachable — NOT empty): %s",
                    ", ".join(failed_sources))
    log.info("By parse provider: %s", dict(by_provider))
    for dom, c in by_domain.most_common():
        log.info("  %-18s %d", dom, c)

    # Location-data coverage (calendars rarely carry coordinates; be honest).
    with_addr = sum(1 for n in all_norm if n.get("venue_address"))
    with_city = sum(1 for n in all_norm if n.get("venue_city"))
    with_venue = sum(1 for n in all_norm if n.get("venue_name"))
    log.info("Location coverage: venue %d/%d, address %d/%d, city %d/%d",
             with_venue, len(all_norm), with_addr, len(all_norm), with_city, len(all_norm))

    # A real-data importer must not exit green on nothing. ONE empty source is
    # tolerated (logged above); EVERY source empty is a systemic failure.
    if not all_norm:
        if failed_sources:
            # NOT systemic normalization drift — sources were REFUSED. Reporting
            # this as "markup changed" would misdiagnose a blocked import (the
            # same conflation class as counting failures among the empties).
            #
            # NOTE the flag is NOT consulted here: --allow-partial means "some
            # sources failed but I accept what DID import". With zero normalized
            # events nothing imported at all, so there is no partial success to
            # accept — exiting 0 would break the fail-loud-on-zero-events
            # invariant (evaluator blocker r7; I introduced this hole in r6).
            log.error("normalized 0 events, and %d of %d source(s) FAILED (%s) — "
                      "a BLOCKED import, not a normalization breakage. "
                      "--allow-partial does NOT apply: nothing was imported.",
                      len(failed_sources), len(sources), ", ".join(failed_sources))
            return _EXIT_SOURCE_FAILURES
        log.error("normalized 0 events across ALL %d selected source(s), NONE of "
                  "which failed to fetch — a systemic breakage (bad selection, "
                  "blanket JSON-LD/ICS markup change, or normalization drift). "
                  "Failing loud.", len(sources))
        return 3

    if args.dry_run:
        log.info("dry-run: no DB write")
        return _exit_code(failed_sources, args.allow_partial)

    import psycopg2

    from worker.importers.licensed_store import upsert_events
    conn = psycopg2.connect(resolve_dsn())  # fail loud on missing DSN
    try:
        written = upsert_events(conn, all_norm)
    finally:
        conn.close()
    log.info("upserted %d events into licensed_event", written)
    return _exit_code(failed_sources, args.allow_partial)


if __name__ == "__main__":
    raise SystemExit(main())
