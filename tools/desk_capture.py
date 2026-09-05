"""desk_capture — save what a desk actually served, so a reader is built
against the desk's own bytes instead of against markup we imagined.

Founder ticket 2026-09-05, Must-do 2: "Event identity for Austin Chronicle is
not a CSS card... Do not add a new parser in this ticket unless the live walk
proves the current reader drops /event/{id} links."

Dry run 33989221309 is that proof: 40 live pages read, ONE row returned, keyed
`url:https://www.austinchronicle.com` with eleven headlines concatenated into
its title. To fix that honestly the reader has to be written against the page
the desk really serves — and the committed fixtures say of themselves they are
"NOT a saved copy of any live page: egress to the real desk is denied from the
build sandbox". Building on those is what let a page-collapsing reader be green
in CI, so this tool exists to end that: it walks the desk with the SAME fetcher
and the SAME walker the ingest uses, and writes every body it received to disk.

It holds no credential and touches no database, which is why its workflow may
run on a branch: `.github/workflows/desk-ingest.yml` is master-only precisely
because it carries the DB secrets, so it can never exercise a branch's reader.

A blocked desk is REPORTED, never retried around: a 403 is that desk's answer,
and Coverage Law forbids bypassing bot protection. An unread desk has an
unknown list, never an empty one.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.desk_coverage import live_fetcher  # noqa: E402
from worker.locale.desk_walk import (  # noqa: E402
    DEFAULT_MAX_PAGES, DeskWalk, PageFetch, walk, walk_table,
)
from worker.locale.kind_map import KindMapError, map_for_door  # noqa: E402
from worker.locale.pack import LocalePackError, load_pack  # noqa: E402

#: A captured page is named after its URL, flattened. Anything that is not a
#: safe filename character becomes '_' so a query string cannot escape the
#: output directory.
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_name(url: str, n: int) -> str:
    return f"page-{n:02d}-{_UNSAFE.sub('_', url)[:120]}.html"


def capture(door_ids: List[str], *, locale: str, out_dir: str, max_pages: int,
            timeout: int, min_interval: float) -> Dict[str, object]:
    """Walk each door live, saving every body received. Returns the manifest."""
    pack = load_pack(locale)
    doors = {d.door_id: d for d in pack.doors}
    fetch_live = live_fetcher(timeout_s=timeout, min_interval_s=min_interval)
    os.makedirs(out_dir, exist_ok=True)

    manifest: Dict[str, object] = {
        "note": ("Bytes the live desks served to a GitHub-hosted runner. These "
                 "are REAL captured pages, not shape fixtures."),
        "locale": locale,
        "doors": {},
    }
    walks: List[DeskWalk] = []

    for door_id in door_ids:
        door = doors.get(door_id)
        if door is None:
            raise LocalePackError(
                f"no door {door_id!r} in locale {locale!r}. Have: {sorted(doors)}")
        saved: Dict[str, str] = {}
        counter = {"n": 0}

        def capturing_fetch(url: str, _saved=saved, _c=counter) -> PageFetch:
            got = fetch_live(url)
            _c["n"] += 1
            if got.body:
                name = _safe_name(url, _c["n"])
                door_dir = os.path.join(out_dir, door_id)
                os.makedirs(door_dir, exist_ok=True)
                with open(os.path.join(door_dir, name), "w", encoding="utf-8") as fh:
                    fh.write(got.body)
                _saved[url] = name
            return got

        try:
            kind_map = map_for_door(door.door_id)
        except KindMapError:
            kind_map = None
        one = walk(door, capturing_fetch, max_pages=max_pages, kind_map=kind_map)
        walks.append(one)
        manifest["doors"][door_id] = {
            "start_url": one.start_url,
            "pages": saved,
            "pages_read": sum(1 for p in one.pages if not p.blocked),
            "pages_blocked": sum(1 for p in one.pages if p.blocked),
            "rows_the_current_reader_returned": len(one.rows),
        }

    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    print(walk_table(walks))
    print()
    for door_id, info in manifest["doors"].items():
        print(f"- `{door_id}`: {len(info['pages'])} page body(ies) saved, "
              f"{info['pages_read']} read, {info['pages_blocked']} blocked, "
              f"the CURRENT reader returned {info['rows_the_current_reader_returned']} row(s).")
    return manifest



# --------------------------------------------------------------------------
# digest — what the captured bytes actually contain
# --------------------------------------------------------------------------

def digest_page(html: str, *, url: str, pattern: str, samples: int = 12) -> str:
    """A structural read-out of one captured page.

    This exists because the artifact is not readable from the machine that has
    to write the parser, and because "I think the page looks like X" is exactly
    the assumption that produced a reader which collapses 40 pages into one
    row. Everything printed here is COUNTED from the bytes, never inferred.
    """
    from worker.locale.desk_read import _TreeBuilder, _select_rows  # noqa: PLC0415

    rx = re.compile(pattern)
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    root = builder.root

    def text_of(node) -> str:
        out = []
        for child in node.children:
            if isinstance(child, str):
                out.append(child)
            else:
                out.append(text_of(child))
        return " ".join(" ".join(out).split())

    anchors = [n for n in root.descendants() if n.tag == "a"]
    matching = [n for n in anchors if rx.search(n.attrs.get("href") or "")]

    lines = [f"### {url}",
             f"- bytes: {len(html)}",
             f"- anchors: {len(anchors)}; matching `{pattern}`: {len(matching)}"]

    ld = html.count("schema.org")
    lines.append(f"- 'schema.org' mentions in the raw bytes: {ld}")

    rows, tier = _select_rows(html)
    lines.append(f"- the CURRENT reader selects {len(rows)} row(s) via the "
                 f"`{tier}` tier")

    if matching:
        lines.append(f"- first {min(samples, len(matching))} matching links "
                     f"(href :: link text):")
        for node in matching[:samples]:
            lines.append(f"    - `{(node.attrs.get('href') or '')[:110]}` :: "
                         f"{text_of(node)[:80]!r}")
        # The ancestor chain of the FIRST match, with how many matching anchors
        # each level contains. The smallest level containing exactly one is the
        # listing; anything above it is a wrapper that would swallow the page.
        lines.append("- ancestor chain of the first matching link "
                     "(tag.class -> matching anchors contained):")
        node = matching[0].parent
        depth = 0
        while node is not None and node.tag != "#root" and depth < 8:
            contained = sum(1 for d in node.descendants()
                            if d.tag == "a" and rx.search(d.attrs.get("href") or ""))
            cls = (node.attrs.get("class") or "")[:60]
            lines.append(f"    - `{node.tag}"
                         f"{('.' + cls.replace(' ', '.')) if cls else ''}` -> {contained}")
            node = node.parent
            depth += 1
    else:
        lines.append("- NO link on this page matches the pattern. The pattern "
                     "is wrong, or this desk states identity another way.")
    return "\n".join(lines)

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--locale", default="us-tx-capcog")
    ap.add_argument("--door", action="append", dest="doors", required=True,
                    help="door_id to capture (repeatable)")
    ap.add_argument("--out", default="captured_pages")
    ap.add_argument("--max-pages", type=int, default=2,
                    help="page ceiling per desk; small on purpose — this is a "
                         "capture, not a crawl")
    ap.add_argument("--timeout", type=int, default=20)
    ap.add_argument("--min-interval", type=float, default=2.0)
    ap.add_argument("--digest-pattern", default=r"/event/",
                    help="link shape the digest counts as a listing door")
    args = ap.parse_args(argv)
    manifest = capture(args.doors, locale=args.locale, out_dir=args.out,
                       max_pages=args.max_pages, timeout=args.timeout,
                       min_interval=args.min_interval)
    print("\n## What the captured bytes contain\n")
    for door_id, info in manifest["doors"].items():
        print(f"\n## `{door_id}`\n")
        if not info["pages"]:
            print("No body was received — nothing to digest. The desk's own "
                  "answer stands as the finding.")
            continue
        for url, name in info["pages"].items():
            with open(os.path.join(args.out, door_id, name), encoding="utf-8") as fh:
                print(digest_page(fh.read(), url=url,
                                  pattern=args.digest_pattern))
                print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
