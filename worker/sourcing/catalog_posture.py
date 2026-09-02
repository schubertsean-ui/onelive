"""Where a source's DECLARED access posture comes from when the row has none.

Coverage Law classes are read off a source's declared posture — `access_method`,
`allowed`, `explicitly_disallowed` — and `worker/sourcing/source_class.py` is
the single authority that turns those into a class letter. The ingest loop asks
that question for real now: only a class B source's own event pages are
followed.

The DB row is the natural place to read the posture from: `tools/import_sources
.py` stores the whole catalog entry in `source.config`. Live ground truth,
measured 2026-09-02 by the dispatched run's own diagnostic (ingest run
33578656538): of 266 enabled sources, **264 declare nothing at all**
(`access_method=''`, `allowed=[]`) — one declares `official_feed_or_partner`,
one `api_key`, and 38 rows carry a completely empty config. So classify_entry
correctly resolved 265 of them to class D on its unrecognized-posture rule, the
walk had nothing to walk, and the loop refused before fetching anything.

The same catalog file in this repo declares a posture for all 180 of its
entries — 140 of them class B (Stubb's, Antone's, ACL Live, Continental Club,
the Parish…). The posture is not missing; it never reached the database.

This module closes that gap the read-only way: when a row declares nothing, the
committed catalog's entry for that source supplies the posture. It is a READ of
a file already in the repo — no production write, nothing about the `source`
table changes, and the fallback disappears on its own the moment a real
posture lands on the row.

PRECEDENCE, deliberately DB-first: a row that declares something has been told
something newer than the catalog knows — `worker/claim/intake.py` writes a real
class E/F posture when a venue claims itself, and a stale file must never
override a live claim. The catalog answers only for rows that are silent.

MATCHING is exact or nothing:
  * by NAME (lower-cased) — the importer's own upsert conflict key, so it is
    this catalog's identity for a row, not a guess;
  * failing that, by normalized base_url, and ONLY when that URL belongs to
    exactly one catalog entry. An ambiguous URL resolves to nothing rather
    than to the first match: assigning one source's posture to another is how
    a class D door would get walked.

FAIL CLOSED: an unreadable or malformed catalog yields an empty index (logged
loudly), every row then declares nothing, classify_entry returns D, and nothing
is followed. Losing the file costs coverage — it can never grant access.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: The committed catalog. Registered in tools/arming_runtime.py's _EXTRA_RUNTIME
#: so editing it re-fires the armed cron's smoke-evidence binding — it now
#: decides WHICH sources the cron walks, which makes it cron runtime in fact.
CATALOG_PATH = os.path.join(REPO_ROOT, "sources", "master_sources_catalog_120.json")

#: The three fields that constitute a declared posture. A row carrying any of
#: them has spoken for itself and the catalog stays out of it.
POSTURE_FIELDS = ("access_method", "allowed", "explicitly_disallowed")

_INDEX: Optional[Dict[str, Dict[str, Any]]] = None


def _normalize_url(url: str) -> str:
    """Scheme+host+path, lower-cased host, no trailing slash — enough to match
    a registered start URL against the catalog's, without pretending that two
    different paths are the same page."""
    parts = urllib.parse.urlsplit(url.strip())
    if not parts.netloc:
        return ""
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/")
    return f"{parts.scheme.lower()}://{host}{path}"


def _build_index(entries) -> Dict[str, Dict[str, Any]]:
    """Index catalog entries by 'name:<lower name>' and 'url:<normalized url>'.

    A URL claimed by more than one entry is REMOVED from the index rather than
    resolved to either — an ambiguous key must answer "I don't know", never
    "probably this one".
    """
    index: Dict[str, Dict[str, Any]] = {}
    url_owners: Dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip().lower()
        if name:
            index[f"name:{name}"] = entry
        url = _normalize_url(str(entry.get("base_url") or ""))
        if url:
            url_owners[url] = url_owners.get(url, 0) + 1
            index[f"url:{url}"] = entry
    for url, count in url_owners.items():
        if count > 1:
            index.pop(f"url:{url}", None)
    return index


def _index() -> Dict[str, Dict[str, Any]]:
    global _INDEX
    if _INDEX is None:
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as handle:
                entries = json.load(handle)
            if not isinstance(entries, list):
                raise ValueError(
                    f"expected a JSON list of catalog entries, got {type(entries).__name__}")
            _INDEX = _build_index(entries)
        except Exception as exc:  # noqa: BLE001 — fail closed, never silently
            log.error(
                "catalog posture: %s is unreadable (%s) — every source will "
                "declare nothing and classify as class D, so NOTHING is "
                "followed. Fail closed: a missing catalog costs coverage, it "
                "never grants access.", CATALOG_PATH, exc,
            )
            _INDEX = {}
    return _INDEX


def declares_posture(config: Any) -> bool:
    """True when a stored config speaks for itself on access."""
    if not isinstance(config, dict):
        return False
    return any(config.get(field) for field in POSTURE_FIELDS)


def resolve_entry(*, name: Any, url: Any, config: Any) -> Dict[str, Any]:
    """The entry to hand `classify_entry`, posture resolved DB-first.

    Always returns a dict carrying at least `base_url`, so the caller never has
    to decide what an absent posture means — classify_entry already does, and
    it decides D.
    """
    entry: Dict[str, Any] = dict(config) if isinstance(config, dict) else {}
    if not declares_posture(entry):
        index = _index()
        key = str(name or "").strip().lower()
        found = index.get(f"name:{key}") if key else None
        if found is None:
            normalized = _normalize_url(str(url or ""))
            found = index.get(f"url:{normalized}") if normalized else None
        if found is not None:
            # The catalog supplies the posture ONLY; everything else on the row
            # (its name, its registered URL) stays the row's own.
            for field in POSTURE_FIELDS:
                if found.get(field) is not None:
                    entry[field] = found[field]
    entry.setdefault("base_url", url)
    return entry
