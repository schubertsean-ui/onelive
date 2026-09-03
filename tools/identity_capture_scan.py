#!/usr/bin/env python3
"""Must-do 1's fixture proof: do the repo's fixtures carry per-listing IDs?

Session Contract #57 (2026-09-03) turns on one question the founder made a STOP
condition: "If ai_extract.py is the only place a URL exists, STOP and show the
fixture proof before editing it." This script IS that proof, committed so the
inventory table's numbers are re-runnable rather than typed into prose
(OPERATING_RULES: cite the command that derives a number).

It scans every HTML/ICS fixture the repo carries — files under tests/fixtures/
plus the HTML and iCalendar embedded inline in tests/test_*.py — and counts the
four carriers an identity could arrive on:

  UID                 an ICS VEVENT's own UID property
  LD url              a schema.org Event object's `url`
  LD @id/identifier   that object's `@id` or `identifier`
  block <a href>      an <a href> INSIDE a repeated listing container
                      (li/article/div), which is the anchor worker/segment.py
                      discards when it reduces a block to text

Reports counts only — it asserts nothing and changes nothing. Exit 0 always;
the TABLE is the output.

Usage: python3 tools/identity_capture_scan.py [--root .]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

_JSONLD_BLOCK = re.compile(
    r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S)
#: `UID:` without a word boundary on purpose — inline ICS inside a Python test
#: is written "...\r\nUID:x\r\n", where the literal backslash-n leaves no word
#: boundary before the U. A \b here silently under-counts the inline fixtures,
#: which is the whole corpus the class E / structured paths are tested against.
_ICS_UID = re.compile(r"UID\s*:", re.I)
_CONTAINER = re.compile(r"<(li|article|div)\b[^>]*>(.*?)</\1>", re.I | re.S)
_ANCHOR = re.compile(r"<a\b[^>]*href", re.I)


def _iter_objects(node):
    """Every dict in a JSON-LD payload (bare object, list, or @graph wrapper)."""
    stack = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, dict):
            yield item
            graph = item.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)


def _is_event(obj: dict) -> bool:
    at = obj.get("@type")
    types = at if isinstance(at, list) else [at]
    return any(isinstance(x, str) and x.lower().endswith("event") for x in types)


def scan(name: str, text: str) -> dict:
    vevent = text.count("BEGIN:VEVENT")
    events = urls = ids = 0
    for block in _JSONLD_BLOCK.findall(text):
        try:
            doc = json.loads(block)
        except ValueError:
            # A malformed block is skipped exactly as the parsers skip it — the
            # count is of what a parser could actually read, not of what looks
            # like markup.
            continue
        for obj in _iter_objects(doc):
            if not _is_event(obj):
                continue
            events += 1
            url = obj.get("url")
            if isinstance(url, str) and url.strip():
                urls += 1
            if obj.get("@id") or obj.get("identifier"):
                ids += 1
    hrefs = sum(1 for m in _CONTAINER.finditer(text) if _ANCHOR.search(m.group(2)))
    return {
        "name": name,
        "vevent": vevent,
        "uid": len(_ICS_UID.findall(text)) if vevent else 0,
        "ld_events": events,
        "ld_url": urls,
        "ld_id": ids,
        "block_href": hrefs,
    }


def collect(root: pathlib.Path) -> list:
    rows = []
    for path in sorted(root.glob("tests/fixtures/**/*")):
        if path.is_file() and path.suffix.lower() in (".html", ".ics", ".txt"):
            rows.append(scan(path.relative_to(root).as_posix(),
                             path.read_text(encoding="utf-8", errors="replace")))
    for path in sorted(root.glob("tests/test_*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "ld+json" in text or "BEGIN:VEVENT" in text:
            rows.append(scan(path.relative_to(root).as_posix() + " (inline)", text))
    return rows


def render(rows: list) -> str:
    header = ("fixture", "VEVENT", "UID", "LD-Events", "LD url",
              "LD @id/identifier", "block <a href>")
    keys = ("vevent", "uid", "ld_events", "ld_url", "ld_id", "block_href")
    widths = [max([len(header[0])] + [len(r["name"]) for r in rows] or [0])]
    widths += [len(h) for h in header[1:]]

    def line(cells):
        return "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(cells))

    out = [line(header), line(["-" * w for w in widths])]
    for row in rows:
        out.append(line([row["name"]] + [row[k] for k in keys]))
    out.append(line(["-" * w for w in widths]))
    out.append(line(["TOTAL"] + [sum(r[k] for r in rows) for k in keys]))
    class_b = [r for r in rows if r["name"].startswith("tests/fixtures/class_b/")]
    out.append("")
    out.append(
        f"class_b corpus ({len(class_b)} files) — the pages the crawl path runs on: "
        + ", ".join(f"{h}={sum(r[k] for r in class_b)}"
                    for h, k in zip(header[1:], keys)))
    return "\n".join(out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repo root (default: .)")
    args = parser.parse_args(argv)
    print(render(collect(pathlib.Path(args.root).resolve())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
