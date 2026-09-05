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
    args = ap.parse_args(argv)
    capture(args.doors, locale=args.locale, out_dir=args.out,
            max_pages=args.max_pages, timeout=args.timeout,
            min_interval=args.min_interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
