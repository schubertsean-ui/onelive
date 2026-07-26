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
    LossyFeed,
    ProviderMismatch,
    import_source,
)

log = logging.getLogger("structured_import")

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_CATALOG = REPO / "sources" / "master_sources_catalog_120.json"

# ---- ONE token table: what each `allowed` token MEANS ------------------------
#
# Each catalog token declares BOTH of its properties here:
#   (selectable, asserted_provider)
#     selectable        — does this token advertise a PUBLIC machine-readable
#                         calendar we can fetch today?
#     asserted_provider — does it name the wire format outright? (None = no
#                         claim, so import_source sniffs)
#
# ONE table because two hand-maintained lists drifted (evaluator blocker r14):
# `_STRUCTURED_ALLOWED` (what gets fetched) and the provider-classification
# table (what gets asserted) had no invariant tying them together, so a token
# could be fully classified and still never be selected. `jsonld_if_offered` was
# exactly that — a token that literally advertises JSON-LD, classified, and NOT
# selectable. It happens to cost nothing today (all three rows carrying it are
# selected via a sibling token), but that is luck, not design: one future row
# whose only token is `jsonld_if_offered` would have sat unfetched forever. That
# is the same defect as the founder's "Only 40?" — 38 curated moat sources
# catalogued and never fetched — wearing a different token.
#
# Both former names are now DERIVED views of this table, so they cannot drift
# again, and a production-outcome test asserts every selectable token actually
# reaches import_source through the real main().
#
# Conservative on PURPOSE: we only reach for sources that advertise structured
# data, never every public web page. `partner_feed` is deliberately NOT
# selectable — it means "a feed would exist under a partnership", and we do not
# have those partnerships; fetching those rows' base URLs would be guessing.
#
# COMPLETENESS IS TEST-DERIVED, not hand-maintained: a test cross-checks this
# table against every token in the real catalog, so a future row adding e.g.
# `tribe_json_feed` fails the suite until it is classified. That is the standing
# response to the incomplete-enumeration class (docs/metrics/KAIZEN_LEDGER.md
# class watch): a hand-kept trust-guarding list gets a derivation test, never a
# fourth hand-audit.
_TOKEN_SEMANTICS: dict[str, tuple[bool, str | None]] = {
    # --- selectable: advertises a public machine-readable calendar ------------
    # The only token that names its format outright, so it ASSERTS and a
    # mismatch makes the source MISCONFIGURED.
    "localist_json_feed": (True, PROVIDER_PLATFORM_JSON),
    # `*_if_offered` / `*_verify` say a feed MIGHT exist — the opposite of a
    # format claim. Asserting from one of these would manufacture false failures
    # for every venue tagged `ics_feed_if_offered` that in fact serves embedded
    # JSON-LD, turning a working source into a reported defect.
    "ics_feed_if_offered": (True, None),
    "jsonld_if_offered": (True, None),
    "feed_if_offered": (True, None),
    "official_feed": (True, None),
    # NOT selectable (evaluator blocker r20). The token is FORMAT-BEARING —
    # it names ICS — but mapped to (True, None) it was selectable while
    # asserting no provider, so a row saying `ics_upload` could serve HTML,
    # JSON or garbage and be sniffed, or counted empty, instead of failing as
    # a misconfigured ICS source. Either half had to go, and the honest half
    # to keep is the assertion: `ics_upload` describes an UPLOAD path (a venue
    # hands US a file), not a URL we fetch — which is exactly why its sibling
    # `csv_upload` is already (False, None). A row that genuinely serves ICS at
    # a URL says so with `official_feed` or `ics_feed_if_offered`.
    # Measured before changing: the one live row carrying it
    # (`ics_claimed_upload`) has base_url None and was never selectable anyway,
    # so selectable stays 64 — pinned by the catalog count test.
    "ics_upload": (False, None),
    "partner_export": (True, None),
    # The curated local-moat rows (ranks 77-114): a verified first-party events
    # page whose EXACT feed path is not yet confirmed. Including it is what makes
    # the moat actually import — without it those 38 sources sat in the catalog
    # and were never fetched (found 2026-07-25 when the founder asked "Only 40?").
    # Safe by construction: import_source auto-detects, and a source exposing
    # neither ICS nor JSON-LD yields 0 events, which the main loop logs per
    # source ("yielded 0 events (<url>) — logged, not fatal") rather than failing.
    "structured_feed_verify": (True, None),
    # --- NOT selectable: no public machine-readable calendar to fetch ---------
    "partner_feed": (False, None),        # only under a partnership we lack
    "partner_access": (False, None),
    "api_access": (False, None),          # keyed APIs, handled by their own importers
    "oauth_api": (False, None),
    "public_pages": (False, None),        # prose pages, not a calendar
    "public_event_pages": (False, None),
    "public_calendar_pages": (False, None),
    "opt_in_links": (False, None),
    "opt_in_email_parse": (False, None),  # the newsletter path, not a fetch
    "csv_upload": (False, None),
    "manual_benchmark": (False, None),
    "open_data_lucene_search": (False, None),
}

# DERIVED views — never hand-edited, so selection and assertion cannot disagree.
_STRUCTURED_ALLOWED = {t for t, (sel, _) in _TOKEN_SEMANTICS.items() if sel}
_TOKEN_PROVIDER_CLASSIFICATION: dict[str, str | None] = {
    t: provider for t, (_, provider) in _TOKEN_SEMANTICS.items()
}
# REMOVED at r18 (evaluator blocker): this was `("ics", "localist", "feed")` —
# a SECOND selector table, matched as a SUBSTRING of access_method, living
# outside _TOKEN_SEMANTICS. It was exactly the incomplete-enumeration class the
# r14 "one token table" fix claimed to close, still open:
#
#   * a row selected by it was never classified by provider_hint_for() or
#     checked by validate_catalog_assertions(), because those read `allowed`
#     only — so it could be fetched with NO provider assertion behind it, which
#     is the config fail-open the assertion machinery exists to prevent;
#   * substring matching made accidental selection structurally possible —
#     `no_feed` contains `feed`, and would have selected a row that explicitly
#     says there is no feed.
#
# Measured before removing, rather than assumed: across the live 116-row
# catalog, ZERO rows are selected by this path that `allowed` does not already
# select (64 selectable either way), so this closes a fail-open without costing
# a single source. A future row that only names its format in access_method now
# has to declare a real `allowed` token to be fetched — the tightening is the
# point, and test_selection_is_governed_by_one_table pins both halves.


# Named so the derivation test can assert these are the only providers reachable
# from catalog data (a typo'd value would otherwise raise deep inside a fetch).
_ASSERTABLE_PROVIDERS = (PROVIDER_ICS, PROVIDER_JSONLD, PROVIDER_PLATFORM_JSON)


class CatalogContradiction(ValueError):
    """A catalog row declares two incompatible wire formats.

    NOT an OSError, deliberately: this is not a host misbehaving, it is OUR
    configuration being corrupt, and it is detectable before a single byte is
    fetched. So it never enters the per-source recoverable path — it is caught up
    front by validate_catalog_assertions() and fails the run at exit code 2, the
    same code the runner already returns for a missing or unparseable catalog. A
    contradictory row IS an unparseable catalog, one row down.
    """


def provider_hint_for(entry: dict) -> str | None:
    """The wire format this catalog row ASSERTS, or None when it asserts none.

    None is the common and correct answer: most rows say "a feed may exist here",
    which import_source resolves by sniffing. A returned provider is a claim the
    source must honour — if nothing fetched is that format, import_source raises
    ProviderMismatch and the source is reported MISCONFIGURED (exit 2, never
    overridable by --allow-partial), not empty and not merely FAILED.

    Raises CatalogContradiction when a row asserts TWO incompatible formats. The
    r10 version warned and fell back to sniffing, which the evaluator correctly
    called fail-open (r11): a row declared as both Localist JSON and iCalendar is
    configuration CORRUPTION, and auto-detecting past it means the typo is never
    fixed while whichever format happens to serve gets treated as intended. My
    r10 test asserted that fallback and so codified the bad contract — the third
    time in this PR a test pinned the MECHANISM instead of the OUTCOME. There is
    no safe guess to make here, so no guess is made.

    Unknown tokens assert nothing HERE, but they do not pass silently:
    validate_catalog_assertions() refuses them up front, so a typo in a custom
    --catalog cannot quietly drop an assertion (evaluator nit r12).
    """
    hints = {
        _TOKEN_PROVIDER_CLASSIFICATION.get(str(a).lower())
        for a in (entry.get("allowed") or [])
    }
    hints.discard(None)
    if len(hints) > 1:
        raise CatalogContradiction(
            f"source {entry.get('id')!r} asserts CONFLICTING wire formats "
            f"{sorted(hints)} via allowed={sorted(entry.get('allowed') or [])} — a "
            f"row cannot be two formats at once. Fix the catalog row; we do not "
            f"guess which half was meant.")
    return hints.pop() if hints else None


def validate_catalog_assertions(entries: list[dict]) -> list[str]:
    """Check every selected row's format assertions BEFORE any fetch.

    Returns the defect messages (empty when clean) — CONFLICTING wire formats and
    UNCLASSIFIED tokens, each message naming which. Called on the FULL catalog
    before selection, and ALL defects reported at once, for three reasons: they
    cost nothing to detect (no network), discovering them one-per-run as the
    fetch loop reached each row would make fixing a typo'd catalog an N-run
    exercise, and a row filtered out by selection can still be the defective one
    (r13). Fail fast, fail complete.
    """
    problems: list[str] = []
    for entry in entries:
        try:
            provider_hint_for(entry)
        except CatalogContradiction as exc:
            problems.append(str(exc))
        # An UNCLASSIFIED token is the silent version of the same defect
        # (evaluator nit r12): the derivation test protects the DEFAULT catalog,
        # but --catalog is an operator path, and there a typo'd
        # `localist_json_fed` would simply be ignored — quietly removing a
        # provider assertion and returning us to sniffing. Same treatment as a
        # contradiction: detectable pre-network, so it fails here. The default
        # catalog cannot trip this (the derivation test keeps the table complete),
        # so a new token is classified deliberately rather than absorbed.
        unknown = sorted(
            str(a) for a in (entry.get("allowed") or [])
            if str(a).lower() not in _TOKEN_PROVIDER_CLASSIFICATION)
        if unknown:
            problems.append(
                f"source {entry.get('id')!r} carries UNCLASSIFIED allowed token(s) "
                f"{unknown} — classify each in _TOKEN_PROVIDER_CLASSIFICATION as "
                f"asserting a wire format or not. An ignored token silently drops a "
                f"provider assertion.")
    return problems


def _is_structured_candidate(entry: dict) -> bool:
    """True when a catalog entry advertises a structured calendar AND has a URL to
    fetch. base_url may be an HTML calendar page — import_source auto-detects and
    parses whatever embedded JSON-LD (or a served .ics) it finds.

    ONE TABLE, actually one (evaluator blocker r18): selection reads the
    `allowed` tokens and nothing else, so every selected row is a row that
    provider_hint_for() classifies and validate_catalog_assertions() checks.
    Selection and assertion cannot disagree because they now consult the same
    derived view of _TOKEN_SEMANTICS."""
    if not entry.get("base_url"):
        return False
    allowed = {str(a).lower() for a in (entry.get("allowed") or [])}
    return bool(allowed & _STRUCTURED_ALLOWED)


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


def _exit_code(failed_sources: list, allow_partial: bool,
               misconfigured_sources: list | None = None,
               lossy_sources: list | None = None) -> int:
    """Fail the command when any source FAILED, and fail it UNCONDITIONALLY when
    any source was MISCONFIGURED.

    Evaluator blocker r6: failures were logged and named but the process still
    exited 0, so an import gate could pass green while sources were refused. A
    warning in a successful run is not fail-loud. --allow-partial is the explicit,
    separately-named opt-in for "I know some sources are blocked, proceed".

    Evaluator blocker r12: that opt-in was over-broad. I made ProviderMismatch an
    OSError in r8 so ONE bad row would not abort the other 63 sources — right
    about SCOPE, wrong about OVERRIDABILITY, because it also swept the row into
    the recoverable bucket that --allow-partial can wave through. A flag meant
    for "these hosts denied/throttled us tonight" must never greenlight "our
    catalog is wrong": the first is the world, the second is a defect only we can
    fix, and it does not heal by itself on the next run. Misconfiguration exits 2
    — the config-error code, same as a contradictory or unparseable catalog.
    """
    lossy = lossy_sources or []
    if lossy:
        log.error("%d source(s) LOSSY (%s) — each served its own format and "
                  "produced ZERO rows, so every event they published is missing. "
                  "--allow-partial does NOT apply: it covers hosts that refused "
                  "us, never data we dropped. Fix the reader.",
                  len(lossy), ", ".join(lossy))
        return 2
    misconfigured = misconfigured_sources or []
    if misconfigured:
        log.error("%d source(s) MISCONFIGURED (%s) — the catalog asserts a wire "
                  "format the endpoint does not serve. --allow-partial does NOT "
                  "apply: it covers hosts that refused us, never a catalog defect. "
                  "Fix the row.", len(misconfigured), ", ".join(misconfigured))
        return 2
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

    # Validate the WHOLE catalog, BEFORE selection (evaluator blocker r13).
    # Running this on the SELECTED rows missed the exact typo class it exists to
    # catch: a row whose only `allowed` token is a typo like `localist_json_fed`
    # is not a structured candidate, so _select() drops it first — the source
    # silently disappears while other rows carry the run to exit 0. My r12 test
    # paired the typo WITH a valid selectable token, i.e. covered the easy case
    # and missed the one that actually escapes. A defect in a row we would never
    # fetch is still a defect in the catalog, and it costs nothing to say so.
    contradictions = validate_catalog_assertions(catalog)
    if contradictions:
        for msg in contradictions:
            log.error("catalog defect: %s", msg)
        log.error("%d contradictory or unclassified catalog row(s) — refusing to "
                  "import under a guess. Failing closed BEFORE any fetch, and "
                  "before selection, so a bad row cannot hide by being filtered "
                  "out.", len(contradictions))
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
    # MISCONFIGURED is not FAILED either. A host that denied us tonight may serve
    # tomorrow; a catalog row asserting a format its endpoint does not serve is a
    # defect only we can fix, and --allow-partial must never wave it through
    # (evaluator blocker r12).
    misconfigured_sources: list[str] = []
    lossy_sources: list[str] = []

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
        except ProviderMismatch as exc:
            # Caught BEFORE the recoverable branch (ProviderMismatch subclasses
            # OSError so one bad row does not abort the run — right about scope,
            # wrong about overridability until r12).
            log.error("source %-26s MISCONFIGURED (%s): %s", sid, url, exc)
            misconfigured_sources.append(sid)
            continue
        except LossyFeed as exc:
            # Same overridability reasoning as r12, applied to r21's class: the
            # source served its own format and we produced nothing from it, so
            # every event it published is missing from tonight's feed. That is a
            # defect that does NOT heal on the next run, which is exactly what
            # --allow-partial must never wave through — the flag covers hosts
            # that refused us, not data we silently dropped. Recorded in its own
            # bucket so the message can say what actually happened rather than
            # borrowing the catalog-defect wording.
            log.error("source %-26s LOSSY (%s): %s", sid, url, exc)
            lossy_sources.append(sid)
            continue
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
    log.info("Structured import: %d source(s) selected, %d MISCONFIGURED, %d FAILED, "
             "%d yielded zero, %d events total",
             len(sources), len(misconfigured_sources), len(failed_sources),
             len(zero_sources), len(all_norm))
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
        if misconfigured_sources:
            log.error("normalized 0 events and %d source(s) are MISCONFIGURED (%s) — "
                      "a catalog defect, not a normalization breakage.",
                      len(misconfigured_sources), ", ".join(misconfigured_sources))
            return 2
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
        return _exit_code(failed_sources, args.allow_partial, misconfigured_sources,
                          lossy_sources)

    import psycopg2

    from worker.importers.licensed_store import upsert_events
    conn = psycopg2.connect(resolve_dsn())  # fail loud on missing DSN
    try:
        written = upsert_events(conn, all_norm)
    finally:
        conn.close()
    log.info("upserted %d events into licensed_event", written)
    return _exit_code(failed_sources, args.allow_partial, misconfigured_sources,
                          lossy_sources)


if __name__ == "__main__":
    raise SystemExit(main())
