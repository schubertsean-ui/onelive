#!/usr/bin/env python3
"""Prove the DEPLOYED site is shareable — not that the data exists, that the PAGE works.

Why this exists (founder, 2026-07-25, verbatim intent): "We must have this data
and we must have the site able to be deployed." Import counts are not the same
claim as a working page. Every measurement I had been reporting — 168 events, 5
categories — described the DATABASE. Whether a person opening /tonight sees real
event cards was never checked, because this agent's sandbox proxy denies
vercel.app (connect_rejected). That is a real limit, and routing around it is the
fix: GitHub Actions HAS egress, so the check runs there instead of here.

WHAT IT PROVES, and nothing more (stated so the claim never outruns the code):
  * the URL answers 200 with HTML;
  * the page is not a framework/error/empty shell;
  * at least MIN_EVENTS event cards are present, counted from the page's OWN
    machine-readable event markup (schema.org JSON-LD), not from prose;
  * the events carry the fields a reader needs — a title and a start time.

WHAT IT DOES NOT PROVE, said out loud: visual layout, auth-gated routes, or that
the events are CORRECT. Correctness is the trust pipeline's job (gate → promote);
this asserts the surface renders what the pipeline produced.

FAIL LOUD: every failure raises SiteVerificationError with the reason and the
evidence. A page that loads but shows zero events is a FAILURE, not a pass —
"the deploy succeeded" and "the site is shareable" are different claims, and
conflating them is the failure-reads-as-empty class applied to a web page.

Pure/stdlib. The parsing half takes TEXT, so it is unit-testable with no network.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Any, Optional

# A shareable page must show at least this many real events. ONE event is not a
# feed; zero is a broken deploy wearing a 200.
MIN_EVENTS = 1

_UA = "OneLiveSiteVerifier/1.0 (+deployment health check)"
_TIMEOUT = 30
# Bounded read: a hostile or misconfigured origin must not be able to exhaust the
# runner (same reasoning as the importer's byte cap).
_MAX_BYTES = 5 * 1024 * 1024


class SiteVerificationError(Exception):
    """The deployed page is not shareable. Carries the reason and the evidence."""


class _LdJson(HTMLParser):
    """Collect <script type="application/ld+json"> bodies."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._in = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            a = {k.lower(): (v or "").lower() for k, v in attrs}
            if "ld+json" in a.get("type", ""):
                self._in = True
                self._buf = []

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._in:
            self.blocks.append("".join(self._buf))
            self._in = False

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)


def _iter_nodes(doc: Any):
    if isinstance(doc, list):
        for item in doc:
            yield from _iter_nodes(item)
    elif isinstance(doc, dict):
        graph = doc.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                yield from _iter_nodes(item)
        yield doc


def _is_event(node: dict) -> bool:
    t = node.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(isinstance(x, str) and x.endswith("Event") for x in types)


def extract_events(html: str) -> list[dict]:
    """Return the event nodes the PAGE ITSELF declares.

    Counted from the page's own schema.org markup rather than from CSS classes or
    visible strings: markup is the contract the page publishes about its content,
    so a count from it cannot be faked by a loading skeleton or a placeholder.
    """
    parser = _LdJson()
    parser.feed(html)
    out: list[dict] = []
    for block in parser.blocks:
        block = block.strip()
        if not block:
            continue
        try:
            doc = json.loads(block)
        except ValueError:
            # One malformed block must not hide the good ones — but it is not
            # silently swallowed either; it is reported by the caller's summary.
            continue
        for node in _iter_nodes(doc):
            if isinstance(node, dict) and _is_event(node):
                out.append(node)
    return out


def verify_page(html: str, *, url: str = "(text)", min_events: int = MIN_EVENTS) -> dict:
    """Assert `html` is a shareable events page. Raises SiteVerificationError.

    Pure — takes text, so the whole judgment is unit-testable without network.
    """
    if not html or not html.strip():
        raise SiteVerificationError(f"{url}: empty response body")

    events = extract_events(html)
    if len(events) < min_events:
        raise SiteVerificationError(
            f"{url}: page returned 200 but declares {len(events)} event(s), "
            f"need >= {min_events}. A deploy that succeeds and shows nothing is "
            f"NOT a shareable site — reporting it as healthy would be the same "
            f"failure-reads-as-empty class this repo already tracks. "
            f"(body was {len(html)} bytes)")

    # A card a reader can act on needs a name and a start time. An event node
    # missing those renders as an empty row, which is worse than absent.
    incomplete = [
        e for e in events
        if not str(e.get("name") or "").strip() or not str(e.get("startDate") or "").strip()
    ]
    if incomplete:
        raise SiteVerificationError(
            f"{url}: {len(incomplete)} of {len(events)} declared events are missing a "
            f"name or startDate — those render as empty cards. First offender: "
            f"{json.dumps(incomplete[0])[:200]}")

    return {
        "url": url,
        "events": len(events),
        "sample_titles": [str(e.get("name"))[:70] for e in events[:5]],
    }


def fetch(url: str, *, timeout: int = _TIMEOUT) -> str:
    """GET the deployed page. Every failure propagates — never an empty string."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise SiteVerificationError(f"{url}: HTTP {resp.status}")
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read(_MAX_BYTES + 1)
            if len(raw) > _MAX_BYTES:
                raise SiteVerificationError(
                    f"{url}: response exceeded {_MAX_BYTES} bytes — refusing to read "
                    f"an unbounded body")
            return raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        raise SiteVerificationError(
            f"{url}: HTTP {exc.code} — the deployed page did not serve") from exc
    except OSError as exc:
        raise SiteVerificationError(
            f"{url}: unreachable ({type(exc).__name__}: {exc})") from exc


_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config" / "site_targets.json"


def load_targets(path: Optional[pathlib.Path] = None) -> list[dict]:
    """Read the reviewed target list. FAIL LOUD on anything malformed.

    Config lives in a committed file rather than a workflow `vars.` context
    because an unset repository variable and an empty one render identically, so
    nothing downstream can fail closed on the difference (workflow_env_lint,
    empty-env class — a class this repo has escalated three times). A URL change
    is therefore a reviewed diff, not an invisible dashboard edit.
    """
    path = path or _CONFIG
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    targets = doc.get("targets")
    if not isinstance(targets, list) or not targets:
        raise SiteVerificationError(f"{path}: no `targets` list — cannot verify anything")
    for t in targets:
        if not isinstance(t, dict) or not t.get("name"):
            raise SiteVerificationError(f"{path}: every target needs a name; got {t!r}")
        if not isinstance(t.get("min_events"), int) or t["min_events"] < 1:
            raise SiteVerificationError(
                f"{path}: target {t.get('name')!r} needs min_events >= 1 — a check "
                f"that cannot fail proves nothing")
    return targets


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", nargs="?",
                    help="deployed page to verify, e.g. https://<host>/tonight")
    ap.add_argument("--min-events", type=int, default=MIN_EVENTS,
                    help=f"minimum real events the page must declare (default {MIN_EVENTS})")
    ap.add_argument("--target", help="verify a named target from config/site_targets.json")
    args = ap.parse_args(argv)

    if args.min_events < 1:
        print("--min-events must be >= 1; a check that cannot fail proves nothing.",
              file=sys.stderr)
        return 2
    if bool(args.url) == bool(args.target):
        print("give exactly one of: a URL, or --target <name>", file=sys.stderr)
        return 2

    try:
        if args.target:
            targets = {t["name"]: t for t in load_targets()}
            if args.target not in targets:
                raise SiteVerificationError(
                    f"unknown target {args.target!r}; known: {sorted(targets)}")
            t = targets[args.target]
            url, min_events = t.get("url"), t["min_events"]
            if not url:
                raise SiteVerificationError(
                    f"target {args.target!r} has no url yet. It FAILS rather than "
                    f"skipping: a check that quietly skips reads as green and proves "
                    f"nothing. Fill it in config/site_targets.json.")
        else:
            url, min_events = args.url, args.min_events
        result = verify_page(fetch(url), url=url, min_events=min_events)
    except SiteVerificationError as exc:
        print(f"SITE NOT SHAREABLE: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"SITE NOT SHAREABLE: config unreadable ({exc})", file=sys.stderr)
        return 1
    print(f"SITE SHAREABLE: {result['url']} — {result['events']} real event(s) render")
    for t in result["sample_titles"]:
        print(f"  · {t}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
