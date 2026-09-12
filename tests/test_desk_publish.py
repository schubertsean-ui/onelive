"""The desks' rows become candidates — and only what the desks stated.

`worker/locale_pack/desk_publish.py` is the seam between a walk that reads and a
catalog that publishes, so what it decides is what a friend eventually sees.
These tests pin the five rules the module's docstring states, and each one is
here because getting it wrong puts something false, something duplicated, or
something fixture-shaped on the live site.

Hermetic: no network, no database, no clock. The walks are built in-process
from the committed fixtures (a page someone already fetched) or from rows
constructed here; the three DB seams are injected as plain functions.
"""
from __future__ import annotations

import importlib.util
import os

import pytest
from zoneinfo import ZoneInfo

from worker.locale_pack import pack as lp
from worker.locale_pack.desk_read import Happening
from worker.locale_pack.desk_publish import (
    DESK_KEY,
    DeskPublishError,
    DeskRegistration,
    contradicts,
    drift,
    ingest_key,
    plan,
    plan_digest,
    refuse_fixture_write,
    registration_for,
    write_for,
)
from worker.locale_pack.desk_union import union
from worker.locale_pack.desk_walk import DeskWalk, PageVisit
from worker.locale_pack.kind_map import map_for_door

CAPCOG = "us-tx-capcog"
CHRONICLE = "austin-chronicle-eventsearch"
DO512 = "do512-today"
TZ_ID = "America/Chicago"
TZ = ZoneInfo(TZ_ID)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_tool(name):
    spec = importlib.util.spec_from_file_location(
        f"_tool_{name}", os.path.join(ROOT, "tools", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


coverage_tool = _load_tool("desk_coverage")
ingest_tool = _load_tool("desk_ingest")


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------

def _row(title, *, when=None, when_precision=None, place="Shape Hall",
         via="Austin Chronicle", door_id=CHRONICLE, listing_url=None,
         when_text=None, kind="other"):
    if when and when_precision is None:
        when_precision = "date" if len(when) == 10 else "datetime"
    return Happening(
        title=title, when=when, when_text=when_text,
        when_precision=when_precision, place_text=place, via=via, kind=kind,
        door_id=door_id, door_type="local_desk", locale_id=CAPCOG,
        source_url="https://desk.example/page", listing_url=listing_url)


def _walk(door_id, via, rows, *, blocked=None, stopped="no_next_link"):
    pages = [PageVisit(n=1, url="https://desk.example/", status=200,
                       rows_seen=len(rows), new_rows=len(rows))]
    if blocked:
        pages = [PageVisit(n=1, url="https://desk.example/", status=403,
                           blocked_reason=blocked)]
    return DeskWalk(door_id=door_id, door_type="local_desk", via=via,
                    start_url="https://desk.example/", pages=pages,
                    rows=list(rows), stopped_because=stopped)


def _union(*walks, mode="LIVE"):
    return union(list(walks), timezone=TZ, timezone_id=TZ_ID, mode=mode)


REGS = {
    "Austin Chronicle": DeskRegistration(
        door_id=CHRONICLE, via="Austin Chronicle",
        source_name="Austin Chronicle Events", source_class="local_media",
        base_url="https://www.austinchronicle.com/events/", catalog_id="austin_chronicle"),
    "Do512": DeskRegistration(
        door_id=DO512, via="Do512", source_name="Do512",
        source_class="local_media", base_url="https://do512.com/",
        catalog_id="do512"),
}


@pytest.fixture(scope="module")
def doors():
    return {d.door_id: d for d in lp.hunt(CAPCOG)}


@pytest.fixture(scope="module")
def catalog():
    import json
    with open(os.path.join(ROOT, "sources", "master_sources_catalog_120.json"),
              encoding="utf-8") as fh:
        return json.load(fh)

