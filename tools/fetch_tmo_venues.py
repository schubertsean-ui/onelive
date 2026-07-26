#!/usr/bin/env python3
"""Fetch the Texas Music Office Industry Directory — denominator layer 3.

Founder directive, 2026-07-26: use every source, not one. Found by web search
the same day.

WHY THIS IS THE RIGHT LAYER 3. Layer 2 is TABC — every establishment licensed
to serve mixed beverages. It is authoritative about ALCOHOL, not about live
performance, so it simultaneously OVER-counts (restaurants that never host a
show) and UNDER-counts (theatres, museums, all-ages rooms, record stores,
coffee houses with stages, the dance-hall circuit).

The TMO directory is the state's own map of the MUSIC economy: ~326 live music
venues and ~284 clubs/dancehalls in the Austin region alone, plus radio
stations and weekly publications as separate categories. It is free, needs no
credential, and answers the question the product actually asks — "is this a
music venue?" — where Places would only answer "what kind of business is this?".

TWO THINGS THIS FILE REFUSES TO DO
==================================

1. GUESS THE PAGE STRUCTURE. Earlier today the TABC fetcher was written with
   column names from memory; the query was rejected outright and cost a CI
   round trip to discover something the dataset would have told us. There is no
   documented API here — this is HTML — so `--describe` dumps the real markup
   first and the parser is written against what comes back. Until a parser is
   confirmed against live output, this tool REFUSES to emit rows rather than
   emitting a plausible-looking few.

2. TRUST THE TMO'S "AUSTIN REGION" AS THE MARKET. TMO's austin region is area
   codes 512/737. CAPCOG is ten named counties. They are NOT the same set:
   Fayette and Lee are largely 979, so a region=austin fetch would silently
   miss them — the incomplete-enumeration class, and precisely the counties
   with the thinnest coverage. So the region is a FETCH HINT only; membership
   is always decided by worker/region/capcog.py, and every row whose city the
   boundary cannot place is reported rather than dropped.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from worker.region.capcog import (  # noqa: E402
    CAPCOG_COUNTIES, county_for_place, in_capcog, normalize_place,
)

BASE = "https://gov.texas.gov/Apps/Music/Directory/results"

# Categories that enumerate PLACES. `weekly-publications` and radio stations are
# deliberately excluded here — they are SOURCES, not venues, and belong in the
# source registry rather than the denominator. Conflating the two is how a
# newspaper ends up counted as a room.
VENUE_CATEGORIES = ("venues", "nightclubs-dancehalls-small-venues")

# A fetch hint, never a market definition. See the module docstring.
DEFAULT_REGION = "austin"

MAX_PAGES = 80
USER_AGENT = "OneLive/1.0 (CAPCOG venue denominator; contact via repo)"


def _get(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def page_url(category: str, region: str | None, page: int) -> str:
    parts = [BASE, category]
    if region:
        parts += ["region", region]
    parts.append(f"p{page}")
    return "/".join(parts)


def candidate_urls(category: str, region: str | None) -> list:
    """URL shapes to try, most-specific first.

    The first guess — /results/{category}/region/{region}/p1 — returned HTTP
    500, even though search engines have indexed exactly that shape (…/p5,
    …/p11). So the path form, the casing, or the pagination suffix differs from
    what is publicly linked. Probing every candidate in ONE run beats learning
    one variant per CI round trip, which is the loop that has cost the most time
    today.
    """
    base_lower = BASE.replace("/Apps/", "/apps/").lower()
    shapes: list = []
    for base in (BASE, base_lower):
        for reg in ([region] if region else []) + [None]:
            mid = f"{base}/{category}" + (f"/region/{reg}" if reg else "")
            shapes += [f"{mid}/p1", f"{mid}/", mid]
    # Deduplicate, preserving order.
    seen: set = set()
    return [u for u in shapes if not (u in seen or seen.add(u))]


def describe(category: str, region: str | None) -> int:
    """Dump the real markup so a parser is written against fact, not memory."""
    html = None
    url = None
    print("probing URL shapes (the documented one 500s):")
    for candidate in candidate_urls(category, region):
        try:
            body = _get(candidate)
        except urllib.error.HTTPError as exc:
            print(f"  HTTP {exc.code:<4} {candidate}")
            continue
        except urllib.error.URLError as exc:
            raise SystemExit(
                f"fetch_tmo_venues --describe: could not reach gov.texas.gov "
                f"({exc.reason}). A network failure is not an empty directory.")
        print(f"  HTTP 200  {candidate}   ({len(body):,} bytes)")
        if html is None:
            html, url = body, candidate
    if html is None:
        raise SystemExit(
            "fetch_tmo_venues --describe: every URL shape failed. The directory "
            "is browsable by hand, so this is a request-shape or bot-policy "
            "problem, not an empty directory. Next step is to check whether the "
            "app needs a session cookie or a referrer.")
    print(f"\nparsing the first success: {url}")

    print(f"  {len(html):,} bytes")
    # Tag histogram: shows at a glance whether listings are a table, a list, or
    # divs with classes.
    tags: dict = {}
    for tag in re.findall(r"<(\w+)", html):
        t = tag.lower()
        tags[t] = tags.get(t, 0) + 1
    print("  tag counts (top 15):")
    for t, n in sorted(tags.items(), key=lambda kv: -kv[1])[:15]:
        print(f"    {t:<12} {n}")

    classes: dict = {}
    for cls in re.findall(r'class="([^"]+)"', html):
        for c in cls.split():
            classes[c] = classes.get(c, 0) + 1
    print("  repeated class names (likely the row wrapper), top 20:")
    for c, n in sorted(classes.items(), key=lambda kv: -kv[1])[:20]:
        print(f"    {c:<32} {n}")

    # A generous slice of the middle, where listings usually live.
    mid = len(html) // 3
    print("\n  ---- markup sample (chars %d-%d) ----" % (mid, mid + 4000))
    print(html[mid:mid + 4000])
    print("  ---- end sample ----")
    return 0


def parse_rows(html: str) -> list:
    """Parse listings out of one results page.

    DELIBERATELY UNIMPLEMENTED until --describe output is in hand. Returning []
    from an unwritten parser would be indistinguishable from "this page has no
    venues" — the failure-reads-as-empty class this project keeps paying for,
    and the exact way a 610-venue directory would silently contribute zero.
    """
    raise NotImplementedError(
        "fetch_tmo_venues: the TMO listing parser is not written yet. Run "
        "`--describe` in CI (this sandbox has no egress to gov.texas.gov), read "
        "the real markup, then implement this against it. Refusing to return an "
        "empty list, which would read as 'the directory has no venues'.")


def to_capcog_rows(raw: list) -> tuple:
    """Filter TMO listings to CAPCOG, by BOUNDARY not by TMO region.

    Returns (inside, unplaceable). Rows whose city the boundary cannot place
    are RETURNED, not discarded: TMO's austin region is area codes 512/737 and
    CAPCOG is ten counties, so the mismatch is guaranteed and silently dropping
    it would hide exactly the outer-county venues we are short of.
    """
    inside: list = []
    unplaceable: list = []
    for r in raw:
        city = normalize_place(r.get("city"))
        verdict = in_capcog(city)
        if verdict is True:
            inside.append({
                "name": (r.get("name") or "").strip(),
                "city": city,
                "county": county_for_place(city),
                "source_layer": "tmo",
                "target_kind": "venue",
                "tmo_category": r.get("category"),
            })
        elif verdict is None:
            unplaceable.append(r)
    return inside, unplaceable


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--describe", action="store_true",
                    help="dump real markup instead of guessing at it")
    ap.add_argument("--category", default=VENUE_CATEGORIES[0],
                    choices=list(VENUE_CATEGORIES))
    ap.add_argument("--region", default=DEFAULT_REGION,
                    help="TMO region as a FETCH HINT; membership is decided by "
                         "the CAPCOG boundary regardless. Pass '' for statewide.")
    ap.add_argument("--max-pages", type=int, default=MAX_PAGES)
    ap.add_argument("--out", default=str(REPO / "sources" / "tmo_capcog_raw.json"))
    args = ap.parse_args(argv)

    region = args.region or None
    if args.describe:
        return describe(args.category, region)

    raw: list = []
    for category in VENUE_CATEGORIES:
        for page in range(1, args.max_pages + 1):
            url = page_url(category, region, page)
            try:
                html = _get(url)
            except urllib.error.HTTPError as exc:
                raise SystemExit(
                    f"fetch_tmo_venues: FAIL — HTTP {exc.code} for {url}. "
                    f"A failed fetch is NOT an empty directory.")
            except urllib.error.URLError as exc:
                raise SystemExit(
                    f"fetch_tmo_venues: FAIL — could not reach gov.texas.gov "
                    f"({exc.reason}). A network failure is NOT an empty "
                    f"directory; re-run when connectivity is restored.")
            rows = parse_rows(html)
            if not rows:
                break
            for r in rows:
                r["category"] = category
            raw.extend(rows)
        else:
            raise SystemExit(
                f"fetch_tmo_venues: FAIL — hit the {args.max_pages}-page cap on "
                f"{category} without reaching the end. A truncated directory is "
                f"a denominator that is quietly too small; raise the cap.")

    inside, unplaceable = to_capcog_rows(raw)
    if not inside:
        raise SystemExit(
            "fetch_tmo_venues: FAIL — zero CAPCOG venues from a directory that "
            "advertises hundreds in the Austin area. That is a parser or region "
            "problem, not a finding.")

    pathlib.Path(args.out).write_text(json.dumps(inside, indent=2) + "\n",
                                      encoding="utf-8")
    by_county: dict = {}
    for r in inside:
        by_county[r["county"]] = by_county.get(r["county"], 0) + 1
    print(f"fetch_tmo_venues: {len(inside)} CAPCOG venue(s) from "
          f"{len(raw)} listing(s) -> {args.out}")
    for county in sorted(CAPCOG_COUNTIES):
        print(f"    {county:<12} {by_county.get(county, 0)}")
    if unplaceable:
        # Named, never silently dropped: these are the rows most likely to be
        # outer-county venues the boundary has not learned yet.
        print(f"  city NOT RECOGNISED by the boundary ({len(unplaceable)}) — "
              f"these are worklist items, not rejects:")
        for r in unplaceable[:15]:
            print(f"    - {r.get('name')} ({r.get('city')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
