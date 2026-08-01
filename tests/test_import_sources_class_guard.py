"""The source_class guard in tools/import_sources.py.

Why this matters more than it looks: worker/gating.py promotes an event from a
SINGLE source when that source's class is an anchor, and otherwise demands
2-source corroboration. So source_class is evidence strength, and a source
imported with an unset or unrecognised class becomes a permanent dead end —
its events are held forever on "Insufficient corroboration (have 1; need 2)".
The importer used to write the literal string "unknown" in that case.
"""
import importlib.util
import json
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "import_sources", _ROOT / "tools" / "import_sources.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


imp = _mod()


def test_a_missing_category_fails_loud_instead_of_becoming_unknown():
    with pytest.raises(SystemExit) as e:
        imp._require_source_class({"name": "Some Venue"})
    assert "no `category`" in str(e.value)
    assert "unknown" not in imp._require_source_class.__doc__.lower()


def test_an_unrecognised_category_fails_loud():
    with pytest.raises(SystemExit) as e:
        imp._require_source_class({"name": "X", "category": "vibes"})
    assert "does not recognise" in str(e.value)


def test_a_real_category_passes_through_unchanged():
    assert imp._require_source_class(
        {"name": "X", "category": "venue_calendar"}) == "venue_calendar"
    assert imp._require_source_class(
        {"name": "X", "source_type": "local_media"}) == "local_media"


def test_the_guard_never_INFERS_a_class_from_the_name():
    """Guessing `venue_calendar` from a name would manufacture ANCHOR evidence
    and let unverified single-source events promote — the exact thing the gate
    exists to prevent. An unclassified source is refused, never guessed."""
    with pytest.raises(SystemExit):
        imp._require_source_class({"name": "Paramount Theatre Venue Calendar"})


def test_every_gate_anchor_class_is_a_known_class():
    """The two vocabularies must not drift: an anchor the importer would
    reject is an anchor no source can ever have."""
    spec = importlib.util.spec_from_file_location(
        "gating", _ROOT / "worker" / "gating.py")
    gating = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gating)
    assert gating.ANCHOR_CLASSES <= imp.KNOWN_SOURCE_CLASSES


def test_the_live_catalog_passes_the_guard_it_will_be_imported_through():
    catalog = json.loads(
        (_ROOT / "sources" / "master_sources_catalog_120.json").read_text())
    rows = catalog if isinstance(catalog, list) else catalog.get(
        "sources", catalog.get("items", []))
    assert rows, "catalog is empty — the guard test would prove nothing"
    for row in rows:
        imp._require_source_class(row)
