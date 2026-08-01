"""Unit tests for the Socrata (SODA) government open-data client + venue-truth
normalizer (worker/importers/socrata.py). NO network — the HTTP GET is injected
(`_get_fn`) and normalize runs on inline SODA-shaped rows, so paging + the
field-map mapping are proven WITHOUT a live portal. Proves the invariants:
deterministic $offset paging with a stable order, non-fabrication (absent column
→ None), and dropping rows with nothing to anchor on.
"""
import urllib.parse as _up

import pytest

from worker.importers.socrata import (
    build_query,
    fetch_dataset,
    normalize_dataset,
    normalize_venue_record,
)

# ---- build_query ------------------------------------------------------------

def test_build_query_defaults_stable_order():
    qs = dict(_up.parse_qsl(build_query(limit=1000, offset=0, where=None,
                                        select=None, order=None)))
    assert qs["$limit"] == "1000"
    assert qs["$offset"] == "0"
    assert qs["$order"] == ":id"   # stable order defaulted for correct paging


def test_build_query_passes_soql_filters():
    qs = dict(_up.parse_qsl(build_query(limit=50, offset=100,
                                        where="license_status='Active'",
                                        select="name,capacity", order="name")))
    assert qs["$where"] == "license_status='Active'"
    assert qs["$select"] == "name,capacity"
    assert qs["$order"] == "name"
    assert qs["$offset"] == "100"


# ---- fetch_dataset paging (injected GET, no network) ------------------------

def test_fetch_dataset_pages_until_exhausted():
    # 250 rows total, page_size 100 → three pages (100, 100, 50) then stop.
    def fake_get(url):
        q = dict(_up.parse_qsl(_up.urlparse(url).query))
        offset, limit = int(q["$offset"]), int(q["$limit"])
        remaining = max(0, 250 - offset)
        n = min(limit, remaining)
        return [{"id": offset + i, "name": f"Venue {offset + i}"} for i in range(n)]

    rows = fetch_dataset("data.austintexas.gov", "abcd-1234",
                         page_size=100, _get_fn=fake_get)
    assert len(rows) == 250
    assert rows[0]["name"] == "Venue 0" and rows[-1]["name"] == "Venue 249"


def test_fetch_dataset_respects_max_rows():
    def fake_get(url):
        q = dict(_up.parse_qsl(_up.urlparse(url).query))
        offset, limit = int(q["$offset"]), int(q["$limit"])
        return [{"id": offset + i} for i in range(limit)]  # infinite dataset

    rows = fetch_dataset("d", "x", page_size=100, max_rows=150, _get_fn=fake_get)
    assert len(rows) == 150  # capped, never runs away


def test_fetch_dataset_rejects_bad_bounds():
    with pytest.raises(ValueError):
        fetch_dataset("d", "x", page_size=0, _get_fn=lambda u: [])


# ---- normalize_venue_record -------------------------------------------------

# A TABC-license-shaped row with arbitrary Socrata column names.
_TABC_ROW = {
    "trade_name": "The Mohawk",
    "address": "912 Red River St",
    "city": "AUSTIN",
    "state": "TX",
    "zip": "78701",
    "location_latitude": "30.2686",
    "location_longitude": "-97.7361",
    "license_number": "MB123456",
    "license_status_desc": "Active",
    "beverage_type": "Mixed Beverage",
}

_TABC_MAP = {
    "name": "trade_name",
    "address": "address",
    "city": "city",
    "state": "state",
    "postal_code": "zip",
    "latitude": "location_latitude",
    "longitude": "location_longitude",
    "license_type": "beverage_type",
    "license_status": "license_status_desc",
    "external_id": "license_number",
}


def test_normalize_maps_fields_and_coerces_numbers():
    n = normalize_venue_record(_TABC_ROW, _TABC_MAP, provider="socrata",
                               source_name="tabc_licenses")
    assert n is not None
    assert n["name"] == "The Mohawk"
    assert n["address"] == "912 Red River St"
    assert n["city"] == "AUSTIN"
    assert n["postal_code"] == "78701"
    assert n["latitude"] == 30.2686 and n["longitude"] == -97.7361
    assert n["license_type"] == "Mixed Beverage"
    assert n["license_status"] == "Active"
    assert n["external_id"] == "MB123456"
    assert n["source_provider"] == "socrata"
    assert n["capacity"] is None            # not in this dataset → honest null
    assert n["raw"]["license_number"] == "MB123456"


def test_normalize_absent_and_blank_columns_are_null_not_fabricated():
    row = {"trade_name": "Bar X", "beverage_type": ""}  # blank + missing columns
    n = normalize_venue_record(row, _TABC_MAP, provider="socrata", source_name="tabc")
    assert n["name"] == "Bar X"
    assert n["license_type"] is None        # blank string → None, never ""
    assert n["address"] is None             # absent column → None
    assert n["capacity"] is None


def test_normalize_drops_row_with_no_name_and_no_id():
    row = {"city": "Austin"}  # nothing to anchor on
    assert normalize_venue_record(row, _TABC_MAP, provider="socrata", source_name="t") is None


def test_normalize_keeps_row_with_id_but_no_name():
    row = {"license_number": "X1"}  # id present, name absent → still anchorable
    n = normalize_venue_record(row, _TABC_MAP, provider="socrata", source_name="t")
    assert n is not None and n["external_id"] == "X1" and n["name"] is None


def test_normalize_dataset_drops_unanchorable_rows():
    rows = [_TABC_ROW, {"city": "Austin"}, {"license_number": "Y2"}]
    out = normalize_dataset(rows, _TABC_MAP, provider="socrata", source_name="tabc")
    assert len(out) == 2  # the city-only row dropped; named + id-only kept


def test_normalize_synthesizes_stable_id_when_no_id_column():
    # A dataset with a name but NO id column → deterministic synthesized id so
    # idempotent re-imports update the same venue_truth row, never duplicate.
    row = {"trade_name": "The Mohawk", "address": "912 Red River St"}
    a = normalize_venue_record(row, _TABC_MAP, provider="socrata", source_name="fire_occupancy")
    b = normalize_venue_record(row, _TABC_MAP, provider="socrata", source_name="fire_occupancy")
    assert a["external_id"] and a["external_id"].startswith("socrata:")
    assert a["external_id"] == b["external_id"]        # deterministic
    # A different venue (or different source) → a different id.
    other = normalize_venue_record({"trade_name": "Stubbs"}, _TABC_MAP,
                                   provider="socrata", source_name="fire_occupancy")
    assert other["external_id"] != a["external_id"]
