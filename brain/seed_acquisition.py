"""Seed the acquisition toolkit from the master sources catalog + technique library.

Greppable summary: turns the 120-rank source catalog
(sources/master_sources_catalog_120.json) into per-source AcquisitionRecipes,
and installs the reusable technique library we already built (ICS/JSON-LD
parsing, JS-render fallback, Localist feed, block segmentation, and the
always-on robots/ToS gate). Idempotent: re-seeding an already-seeded toolkit
adds nothing (registration is a no-op when the recipe/technique exists), so it
is safe to call at the start of any session.

Every mapping RESPECTS the catalog's legal flags: a source's
`explicitly_disallowed` list is carried onto the recipe as a guardrail, robots
is assumed to be respected (robots_ok stays True — a recipe that ignores robots
cannot be stored), and opt-in / manual / benchmark channels are seeded with
automated_ok=False so the toolkit knows NOT to auto-fetch them. No mapping ever
produces a login/paywall/robots-bypass method; `_assert_recipe_legal` is the
backstop.
"""
from __future__ import annotations

import json
import pathlib
from typing import Optional

from brain.acquisition import (
    AcquisitionRecipe,
    AcquisitionTechnique,
    AcquisitionToolkit,
)

_CATALOG_PATH = (pathlib.Path(__file__).resolve().parent.parent
                 / "sources" / "master_sources_catalog_120.json")

# Disallowed-flag tokens that mean "no automated fetch of this source at all"
# (a manual, opt-in, or benchmark-only channel). These are LEGITIMATE sources,
# just not a "go read the calendar page" recipe — seeded automated_ok=False.
_NO_AUTOMATED_INGEST = frozenset({
    "automated_ingest", "email_interception", "auth_bypass",
})

# Catalog `allowed` hints that indicate an offered structured feed / API, in
# descending preference (cheapest + most authoritative first — cost discipline).
_STRUCTURED_HINTS = (
    ("localist_json_feed", "api", "none"),
    ("api_access", "api", "none"),
    ("oauth_api", "api", "none"),
    ("official_feed", "api", "none"),
    ("partner_feed", "api", "none"),
    ("partner_export", "api", "none"),
    ("partner_access", "api", "none"),
    ("ics_feed_if_offered", "ics_feed", "ics"),
    ("ics_upload", "ics_feed", "ics"),
    ("jsonld_if_offered", "jsonld", "jsonld"),
)

# Note substrings that betray a JS-rendered calendar widget (render fallback).
_RENDER_HINT_TOKENS = ("squarespace", "wix", "bandsintown", "javascript", "js widget")
# Note substrings that betray a WordPress "The Events Calendar" (ICS/JSON-LD).
_WORDPRESS_TOKENS = ("wordpress", "the events calendar")


def _pick_method(source: dict) -> tuple[str, str, str]:
    """Map a catalog row to (access_method, structured_format, plan_note).

    Prefers an offered structured feed/API (cheap, authoritative) over a plain
    HTML fetch. Never returns a bypass method — the returned methods are all in
    the policy-safe ACCESS_METHODS set.
    """
    allowed = {a.lower() for a in source.get("allowed", [])}
    access = (source.get("access_method") or "").lower()
    notes = (source.get("notes") or "").lower()

    for hint, method, fmt in _STRUCTURED_HINTS:
        if hint in allowed:
            return method, fmt, f"read offered {hint} ({method})"
    if "localist" in access:
        return "api", "none", "read Localist public JSON feed"
    if any(t in access for t in ("api", "oauth", "feed")):
        return "api", "none", "read official/partner API or feed"

    # Falls back to a public HTML fetch; JS-shell venues get js_render.
    if any(t in notes for t in _RENDER_HINT_TOKENS):
        return "js_render", "none", "headless-render the JS calendar widget, then parse"
    return "plain_http", "none", "GET the public calendar page and parse"


def _calendar_url(source: dict) -> tuple[str, bool]:
    """Return (calendar_url, is_homepage). Uses base_url; flags it honestly as a
    homepage when it carries no events/calendar path (the real listing URL is a
    per-source discovery step — never fabricated here)."""
    base = source.get("base_url") or ""
    if not base:
        return "", False
    path = base.split("://", 1)[-1]
    path = path[path.find("/"):] if "/" in path else "/"
    listing_marker = any(seg in path.lower() for seg in
                         ("event", "calendar", "shows", "show", "whats-on", "upcoming"))
    return base, not listing_marker


def recipe_from_source(source: dict) -> AcquisitionRecipe:
    """Build ONE AcquisitionRecipe from a catalog row (legal flags respected)."""
    method, fmt, plan = _pick_method(source)
    calendar_url, is_home = _calendar_url(source)
    disallowed = list(source.get("explicitly_disallowed", []))
    automated_ok = not (set(a.lower() for a in disallowed) & _NO_AUTOMATED_INGEST)
    notes = (source.get("notes") or "").lower()
    render_required = method == "js_render" or any(t in notes for t in _RENDER_HINT_TOKENS)

    # segmentation hint: structured feeds are self-segmenting (one record per
    # event); unstructured HTML pages get the deterministic block segmenter.
    if fmt in ("ics", "jsonld") or method == "api":
        seg = "structured feed: one record per event (no page segmentation needed)"
    elif any(t in notes for t in _WORDPRESS_TOKENS):
        seg = "WordPress The Events Calendar: prefer ICS/JSON-LD; else segment .type-tribe_events blocks"
    else:
        seg = "segment repeated dated event blocks (worker/segment.py)"

    tos_note = ("respect source policy; explicitly disallowed: "
                + (", ".join(disallowed) if disallowed else "none stated"))
    # Seed reliability/confidence from the catalog's own access-reliability +
    # credibility so a brand-new toolkit already ranks sources sensibly.
    access_rel = float(source.get("access_reliability", 0.5))
    cred = float(source.get("credibility_weight", 0.5))
    cost = "high" if method == "js_render" else "low"

    return AcquisitionRecipe(
        source_id=source["id"],
        source_name=source.get("name", source["id"]),
        calendar_url=calendar_url,
        calendar_url_is_homepage=is_home,
        access_method=method,
        render_required=render_required,
        structured_format=fmt,
        segmentation_hint=seg,
        plan_note=plan,
        robots_ok=True,
        tos_note=tos_note,
        explicitly_disallowed=disallowed,
        automated_ok=automated_ok,
        reliability=round(access_rel, 6),
        cost_hint=cost,
        confidence=round(cred, 6),
    )


def technique_library() -> list:
    """The reusable techniques we already built, ready to seed.

    Each names the page SIGNALS that trigger it and a prior success rate; real
    `record_outcome` calls then move the observed rate. `respect-robots-tos-gate`
    is the always-on legal gate (prior ~1.0) that runs before any fetch.
    """
    return [
        AcquisitionTechnique(
            name="respect-robots-tos-gate",
            description=("Before ANY fetch, check robots.txt + the source's ToS "
                         "and explicitly_disallowed list. Never login/paywall/"
                         "robots bypass. This gate has no extraction output; it "
                         "authorises or blocks the acquisition."),
            when_to_use="always, first, on every source",
            applies_to_signals=["any", "robots", "tos", "legal"],
            prior_success_rate=0.99, cost_hint="none"),
        AcquisitionTechnique(
            name="detect-js-shell-then-render",
            description=("A plain GET returns a boilerplate JS shell ('enable "
                         "javascript', no listings). Re-fetch through headless "
                         "Chromium (worker/fetch/render_fetch.py) and parse the "
                         "rendered DOM."),
            when_to_use="plain fetch yields a JS-only shell with no events",
            applies_to_signals=["js_shell", "empty_shell", "squarespace", "wix"],
            prior_success_rate=0.6, cost_hint="high"),
        AcquisitionTechnique(
            name="find-ics-on-wordpress",
            description=("A WordPress venue on 'The Events Calendar' almost always "
                         "offers an .ics export and JSON-LD; prefer the feed over "
                         "scraping the rendered grid."),
            when_to_use="page is WordPress + The Events Calendar",
            applies_to_signals=["wordpress", "the-events-calendar", "maybe_ics"],
            prior_success_rate=0.65, cost_hint="low"),
        AcquisitionTechnique(
            name="parse-jsonld-graph-event",
            description=("Extract schema.org/Event JSON-LD from a page's "
                         "<script type=application/ld+json> blocks, tolerating a "
                         "single object, a list, or an @graph container "
                         "(worker/importers/structured_feed.parse_jsonld)."),
            when_to_use="page embeds schema.org Event JSON-LD",
            applies_to_signals=["has_jsonld", "jsonld", "squarespace"],
            prior_success_rate=0.7, cost_hint="low"),
        AcquisitionTechnique(
            name="parse-localist-feed",
            description=("A Localist calendar (universities/civic) exposes a public "
                         "JSON feed; read it directly instead of the HTML view."),
            when_to_use="source is a Localist calendar",
            applies_to_signals=["localist"],
            prior_success_rate=0.7, cost_hint="low"),
        AcquisitionTechnique(
            name="parse-ics-feed",
            description=("Parse an offered iCalendar (.ics / VEVENT, RFC 5545) feed "
                         "into events (worker/importers/structured_feed.parse_ics)."),
            when_to_use="source offers an .ics feed",
            applies_to_signals=["ics", "has_ics", "ics_feed"],
            prior_success_rate=0.72, cost_hint="low"),
        AcquisitionTechnique(
            name="segment-repeated-event-blocks",
            description=("An unstructured listings page: split into per-event text "
                         "blocks on repeated schema.org containers or repeated "
                         "line-initial date anchors (worker/segment.py), then run "
                         "the certified single-event extractor per block."),
            when_to_use="unstructured multi-event page, no structured feed",
            applies_to_signals=["repeated_blocks", "listing_page", "multi_event"],
            prior_success_rate=0.6, cost_hint="low"),
    ]


def load_catalog(path: Optional[pathlib.Path] = None) -> list:
    return json.loads((path or _CATALOG_PATH).read_text(encoding="utf-8"))


def seed(toolkit: AcquisitionToolkit, *, run_id: str = "seed-acquisition-v1",
         catalog_path: Optional[pathlib.Path] = None) -> dict:
    """Seed recipes (from the catalog) + the technique library into `toolkit`.

    Idempotent. Returns a small summary dict {recipes, techniques,
    recipes_new, techniques_new} for the caller/demo to print.
    """
    catalog = load_catalog(catalog_path)
    src_uri = str((catalog_path or _CATALOG_PATH).name)

    recipes_new = 0
    for source in catalog:
        before = toolkit.recipe_for(source["id"])
        toolkit.register_recipe(
            recipe_from_source(source), run_id=run_id, source_uri=src_uri)
        if before is None:
            recipes_new += 1

    techniques_new = 0
    for tech in technique_library():
        before = toolkit.technique(tech.name)
        toolkit.register_technique(tech, run_id=run_id, source_uri="technique-library-v1")
        if before is None:
            techniques_new += 1

    return {
        "recipes": len(toolkit.all_recipes()),
        "techniques": len(toolkit.all_techniques()),
        "recipes_new": recipes_new,
        "techniques_new": techniques_new,
    }
