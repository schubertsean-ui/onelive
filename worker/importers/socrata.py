"""Government open-data (Socrata / SODA) client + venue-truth normalizer.

The `gov_open_data` ingestion pathway (docs/strategy/ONE_LIVE_INGESTION_ENGINE_v1.md
§3): local & state administrative agencies publish authoritative VENUE facts —
liquor licensing (TABC), fire-marshal occupancy/capacity, health-department
permits and service type, business registration — as machine-readable JSON via
the Socrata Open Data API (SODA). This is a differentiated triangulation ANCHOR
(does this venue exist, licensed, at this capacity?), reusable across every US
jurisdiction on Socrata with only a per-dataset field map — no per-city code.

This module is the deterministic FETCH + NORMALIZE layer (stdlib-only urllib/json;
the dev sandbox is network-blocked so live fetches run on CI, exactly like
ticketmaster.py / seatgeek.py). It produces a normalized VENUE-TRUTH record; it
writes NOTHING itself and never touches the event feed or the AI/promote path.

Discipline (mirrors the other importers): fail LOUD on a fetch error (never a
silent empty), never fabricate a field (absent column → None), and page
deterministically. This is venue enrichment / corroboration, NOT an event list —
stated plainly so it is never mistaken for feed volume.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from typing import Any, Iterable, Optional

_USER_AGENT = "OneLiveGovOpenData/1.0 (+https://onelive.example; deterministic no-AI venue-truth import)"

# SODA 2.1 resource endpoint: https://{domain}/resource/{dataset}.json
_RESOURCE_PATH = "/resource/{dataset}.json"

# SODA hard page ceiling per request; we page with $offset beyond it.
SODA_MAX_LIMIT = 50000


def _get(url: str, *, app_token: Optional[str], timeout: int) -> list:
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
    # A Socrata app token raises rate limits but is NOT required for public
    # datasets — absent is fine, never fabricated.
    if app_token:
        headers["X-App-Token"] = app_token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        body = resp.read().decode(charset, errors="replace")
    data = json.loads(body)
    if not isinstance(data, list):
        # SODA returns a JSON array of rows; an object is an error envelope.
        raise ValueError(f"Socrata response was not a row array: {str(data)[:200]}")
    return data


def build_query(*, limit: int, offset: int, where: Optional[str],
                select: Optional[str], order: Optional[str]) -> str:
    """Build a SODA querystring (SoQL `$` params). Kept pure + separate so the
    query construction is unit-testable without a network call."""
    params: list[tuple[str, str]] = [("$limit", str(limit)), ("$offset", str(offset))]
    if where:
        params.append(("$where", where))
    if select:
        params.append(("$select", select))
    if order:
        params.append(("$order", order))
    else:
        # A STABLE order is required for correct $offset pagination — without it
        # Socrata may repeat/skip rows across pages. `:id` is the system row id,
        # present on every dataset.
        params.append(("$order", ":id"))
    return urllib.parse.urlencode(params)


def fetch_dataset(domain: str, dataset: str, *, app_token: Optional[str] = None,
                  where: Optional[str] = None, select: Optional[str] = None,
                  order: Optional[str] = None, page_size: int = 1000,
                  max_rows: int = 20000, timeout: int = 30,
                  _get_fn=None) -> list[dict]:
    """Fetch rows from a Socrata dataset, paging by $offset until exhausted or
    max_rows. `domain` is the portal host (e.g. 'data.austintexas.gov'), `dataset`
    the 4x4 resource id (e.g. 'nuhn-tc9j'). Returns the raw row dicts. Raises
    LOUD on any HTTP/parse error (never a silent empty). `_get_fn` is an injection
    seam for tests (defaults to the real urllib GET)."""
    if page_size < 1 or max_rows < 1:
        raise ValueError("page_size and max_rows must be >= 1")
    get = _get_fn or (lambda url: _get(url, app_token=app_token, timeout=timeout))
    base = f"https://{domain}{_RESOURCE_PATH.format(dataset=dataset)}"
    rows: list[dict] = []
    offset = 0
    while len(rows) < max_rows:
        limit = min(page_size, max_rows - len(rows))
        qs = build_query(limit=limit, offset=offset, where=where,
                         select=select, order=order)
        page = get(f"{base}?{qs}")
        rows.extend(r for r in page if isinstance(r, dict))
        if len(page) < limit:
            break  # last page reached
        offset += limit
    return rows


# Canonical venue-truth fields this pathway produces. A per-dataset field_map maps
# each to the dataset's actual (arbitrary) column name; an unmapped or absent
# field stays None — never fabricated.
VENUE_TRUTH_FIELDS = (
    "name", "address", "city", "state", "postal_code",
    "latitude", "longitude", "capacity", "license_type", "license_status",
    "service_type", "external_id",
)


def _num(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def normalize_venue_record(record: dict, field_map: dict, *, provider: str,
                           source_name: str) -> Optional[dict]:
    """Map ONE Socrata row into the canonical venue-truth dict using field_map
    ({canonical_field: dataset_column}). Non-fabricating: an absent/blank column
    is None. Returns None when there is no venue name AND no stable external id —
    a row with nothing to anchor on is dropped, never invented.

    latitude/longitude/capacity are coerced to numbers (blank → None); everything
    else is passed through as the source's own string. `provider` records HOW the
    row was obtained ('socrata') for honest provenance.
    """
    out: dict[str, Any] = {f: None for f in VENUE_TRUTH_FIELDS}
    for canonical, column in field_map.items():
        if canonical not in out or not column:
            continue
        val = record.get(column)
        if val == "":
            val = None
        out[canonical] = val
    out["latitude"] = _num(out["latitude"])
    out["longitude"] = _num(out["longitude"])
    out["capacity"] = _num(out["capacity"])
    if not out.get("external_id"):
        # No stable id column in this dataset: synthesize a DETERMINISTIC id from
        # the venue's own name + address so an idempotent re-import updates the
        # same row instead of duplicating (venue_truth is keyed on external_id).
        # A row with neither an id nor a name has nothing to anchor on — dropped,
        # never fabricated.
        if out.get("name"):
            digest = hashlib.sha1(
                f"{provider}|{source_name}|{out['name']}|{out.get('address') or ''}"
                .encode("utf-8")).hexdigest()
            out["external_id"] = f"{provider}:{digest}"
        else:
            return None
    out["source_provider"] = provider
    out["source_name"] = source_name
    out["raw"] = record
    return out


def normalize_dataset(records: Iterable[dict], field_map: dict, *, provider: str,
                      source_name: str) -> list[dict]:
    """Normalize many Socrata rows, dropping the un-anchorable ones (no name, no
    id) rather than fabricating them."""
    out: list[dict] = []
    for r in records:
        n = normalize_venue_record(r, field_map, provider=provider, source_name=source_name)
        if n:
            out.append(n)
    return out
