"""read(directory_page) — Place and Actor names the page declared.

ONE-LIVE-ENTITY-SPLIT-LAW.md §3.3: a license/directory writes Place/Actor
(universe), not Happenings on Tonight. This module is that reader.

Identity is the href path the directory printed:

  /venues/{slug}  → Place
  /artists/{slug} → Actor

Those shapes do NOT belong in sources/identity_patterns.json. That file is
how a page declares a HAPPENING permalink. Putting a venue URL there would
make desk-ingest treat a place as an event (R-104).

No dates. No event rows. A link that is an event permalink, nav, or Follow
button is ignored.

Pure: stdlib only, no network, no DB, no clock.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urldefrag, urljoin, urlsplit

CENSUS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "sources", "directory_census.json",
)

KINDS = ("place", "actor")
SKIP_NAMES = frozenset({
    "follow", "following", "more", "next", "previous", "prev", "see all",
    "venues", "artists", "events", "home",
})


class DirectoryReadError(ValueError):
    """The directory table or page cannot be read as asked."""


@dataclass(frozen=True)
class DirectorySpec:
    directory_id: str
    brand: str
    url: str
    entity_kind: str
    path_re: str
    city: Optional[str]
    evidence: str
    note: str

    @property
    def rx(self) -> "re.Pattern[str]":
        return re.compile(self.path_re)


@dataclass(frozen=True)
class DirectoryEntity:
    kind: str
    name: str
    url: str
    directory_id: str
    city: Optional[str] = None


@dataclass
class DirectoryRead:
    directory_id: str
    source_url: str
    entities: List[DirectoryEntity]
    skipped_nameless: int = 0
    skipped_other_links: int = 0
    notes: List[str] = None

    def __post_init__(self) -> None:
        if self.notes is None:
            self.notes = []

    @property
    def count(self) -> int:
        return len(self.entities)


def load_directories(path: Optional[str] = None) -> Tuple[DirectorySpec, ...]:
    target = path or CENSUS_PATH
    try:
        with open(target, encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError as exc:
        raise DirectoryReadError(f"no directory census table at {target}") from exc
    except (OSError, ValueError) as exc:
        raise DirectoryReadError(f"directory census table {target} is unreadable: {exc}") from exc
    rows = raw.get("directories")
    if not isinstance(rows, list) or not rows:
        raise DirectoryReadError(f"{target}: 'directories' must be a non-empty list")
    out: List[DirectorySpec] = []
    seen = {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise DirectoryReadError(f"{target} directories[{i}] must be an object")
        directory_id = str(row.get("directory_id") or "").strip()
        if not directory_id:
            raise DirectoryReadError(f"{target} directories[{i}]: missing directory_id")
        if directory_id in seen:
            raise DirectoryReadError(f"{target}: duplicate directory_id {directory_id!r}")
        seen[directory_id] = i
        kind = str(row.get("entity_kind") or "").strip()
        if kind not in KINDS:
            raise DirectoryReadError(
                f"{target} {directory_id}: entity_kind {kind!r} is not one of {KINDS}")
        path_re = str(row.get("path_re") or "").strip()
        if not path_re:
            raise DirectoryReadError(f"{target} {directory_id}: missing path_re")
        try:
            re.compile(path_re)
        except re.error as exc:
            raise DirectoryReadError(
                f"{target} {directory_id}: path_re does not compile: {exc}") from exc
        city = row.get("city")
        if city is not None and (not isinstance(city, str) or not city.strip()):
            raise DirectoryReadError(
                f"{target} {directory_id}: city must be a non-empty string or null")
        out.append(DirectorySpec(
            directory_id=directory_id,
            brand=str(row.get("brand") or "").strip(),
            url=str(row.get("url") or "").strip(),
            entity_kind=kind,
            path_re=path_re,
            city=city.strip() if isinstance(city, str) else None,
            evidence=str(row.get("evidence") or "").strip(),
            note=str(row.get("note") or ""),
        ))
    return tuple(out)


def spec_for(directory_id: str, specs: Optional[Sequence[DirectorySpec]] = None) -> DirectorySpec:
    table = specs if specs is not None else load_directories()
    hits = [s for s in table if s.directory_id == directory_id]
    if not hits:
        raise DirectoryReadError(f"no directory {directory_id!r} in the census table")
    return hits[0]


class _AnchorCollector(HTMLParser):
    """Collect (href, text) for every <a>. Furniture names are filtered later."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: List[Tuple[str, str]] = []
        self._href: Optional[str] = None
        self._parts: List[str] = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = ""
        for key, value in attrs:
            if key.lower() == "href":
                href = value or ""
                break
        if self._depth == 0:
            self._href = href
            self._parts = []
        self._depth += 1

    def handle_endtag(self, tag):
        if tag != "a" or self._depth == 0:
            return
        self._depth -= 1
        if self._depth == 0 and self._href is not None:
            self.anchors.append((self._href, "".join(self._parts)))
            self._href = None
            self._parts = []

    def handle_data(self, data):
        if self._depth > 0:
            self._parts.append(data)


def _clean_name(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _same_host(page_url: str, href: str) -> bool:
    page_host = (urlsplit(page_url).hostname or "").lower()
    href_host = (urlsplit(href).hostname or "").lower()
    if page_host.startswith("www."):
        page_host = page_host[4:]
    if href_host.startswith("www."):
        href_host = href_host[4:]
    return bool(page_host) and page_host == href_host


def read(spec: DirectorySpec, html: str, *, base_url: Optional[str] = None) -> DirectoryRead:
    """Turn one directory page into Place or Actor rows.

    `html` is bytes somebody else fetched. This function does not fetch.
    """
    if not isinstance(spec, DirectorySpec):
        raise DirectoryReadError("read() takes a DirectorySpec, not a door or a string")
    page_url = base_url or spec.url
    parser = _AnchorCollector()
    parser.feed(html or "")
    parser.close()
    entities: List[DirectoryEntity] = []
    seen = set()
    skipped_nameless = 0
    skipped_other = 0
    for href, raw_name in parser.anchors:
        absolute, _frag = urldefrag(urljoin(page_url, href or ""))
        parts = urlsplit(absolute)
        if parts.scheme not in ("http", "https"):
            skipped_other += 1
            continue
        if not _same_host(page_url, absolute):
            skipped_other += 1
            continue
        path = (parts.path or "").rstrip("/") or "/"
        if not spec.rx.match(path):
            skipped_other += 1
            continue
        name = _clean_name(raw_name)
        if not name or name.lower() in SKIP_NAMES:
            skipped_nameless += 1
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        entities.append(DirectoryEntity(
            kind=spec.entity_kind,
            name=name,
            url=absolute,
            directory_id=spec.directory_id,
            city=spec.city,
        ))
    notes = []
    if not entities:
        notes.append(
            "zero directory rows — that is UNREAD / unsplit, never 'this place has no venues'"
        )
    return DirectoryRead(
        directory_id=spec.directory_id,
        source_url=page_url,
        entities=entities,
        skipped_nameless=skipped_nameless,
        skipped_other_links=skipped_other,
        notes=notes,
    )
