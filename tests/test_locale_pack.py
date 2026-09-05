"""The locale pack is DATA and the type system is code — proven both ways.

Two properties matter beyond "it parses": that no brand name lives in the
module (a second locale must be a second FILE), and that every way a pack can
lie about a door is refused at load rather than discovered by a fetch.
"""
from __future__ import annotations

import json
import os

import pytest

from worker.locale import pack as lp

CAPCOG = "us-tx-capcog"
FOUNDER_URL = ("https://calendar.austinchronicle.com/austin/EventSearch"
               "?sortType=date&v=g")


def _pack_dict():
    with open(os.path.join(lp.PACKS_DIR, f"{CAPCOG}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _write(tmp_path, data, name=CAPCOG):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(tmp_path)


# --- the shipped pack --------------------------------------------------------

def test_the_capcog_pack_loads_and_every_door_is_typed():
    doors = lp.hunt(CAPCOG)
    assert doors, "the shipped pack must contain doors"
    for door in doors:
        assert door.door_type in lp.DOOR_TYPES
        assert door.intake in lp.INTAKES
        assert door.evidence in lp.EVIDENCE_GRADES
        assert door.locale_id == CAPCOG


def test_the_founder_named_chronicle_door_is_in_the_pack_verbatim():
    doors = {d.door_id: d for d in lp.hunt(CAPCOG)}
    chronicle = doors["austin-chronicle-eventsearch"]
    assert chronicle.url == FOUNDER_URL
    assert chronicle.door_type == "local_desk"
    assert chronicle.readable is True
    assert chronicle.evidence == "founder_named"


def test_the_pack_covers_every_door_type_the_founder_named():
    present = {d.door_type for d in lp.hunt(CAPCOG)}
    assert present == set(lp.DOOR_TYPES), (
        f"missing door types: {set(lp.DOOR_TYPES) - present}")


def test_walls_and_junk_are_never_readable():
    for door in lp.hunt(CAPCOG, door_types=["wall", "junk"]):
        assert door.readable is False
        assert door.blocked_reason, f"{door.door_id} must say why it is not read"


def test_public_desks_are_the_readable_subset():
    desks = lp.public_desks(CAPCOG)
    assert desks
    assert all(d.readable for d in desks)
    assert set(desks) <= set(lp.hunt(CAPCOG))


def test_hunt_orders_most_trusted_door_type_first():
    types = [d.door_type for d in lp.hunt(CAPCOG)]
    ranks = [lp.DOOR_TYPES.index(t) for t in types]
    assert ranks == sorted(ranks)


def test_the_query_grammar_expands_to_consumer_phrasings():
    queries = lp.load_pack(CAPCOG).queries()
    assert "things to do in Austin TX" in queries
    assert len(queries) == len(set(queries)), "expansion must not duplicate"
    # A kind template crosses every kind; a place-only template does not.
    assert any(q.startswith("music in ") for q in queries)


def test_the_grammar_expansion_is_deterministic():
    assert lp.load_pack(CAPCOG).queries() == lp.load_pack(CAPCOG).queries()


# --- brands live in the pack, never in the code ------------------------------

def test_no_brand_from_the_pack_appears_in_the_locale_modules():
    """Brands only in the pack (founder). A brand literal in code is how a
    locale stops being data — so this greps the modules for every brand the
    shipped pack names."""
    brands = {d["brand"] for d in _pack_dict()["doors"]}
    module_dir = os.path.dirname(os.path.abspath(lp.__file__))
    sources = {}
    for name in sorted(os.listdir(module_dir)):
        if name.endswith(".py"):
            with open(os.path.join(module_dir, name), encoding="utf-8") as fh:
                sources[name] = fh.read()
    offenders = [
        f"{name}: {brand!r}"
        for brand in brands
        for name, text in sources.items()
        if brand and brand in text
    ]
    # The message carries the REMEDY, not just the refusal. This guard has now
    # caught the same mistake in two consecutive sessions (KAIZEN 2026-09-05,
    # contracts #65 and #66), both times from an author quoting the founder's
    # ticket verbatim in a new module's docstring — a case where the offending
    # text is not a hardcoded locale at all, and the fix is not obvious from
    # "brand literal(s) in code". A repeat class whose guard fires correctly and
    # then leaves the author to guess is a gap in the GUARD, not in the author.
    assert offenders == [], (
        f"brand literal(s) in code: {offenders}\n"
        f"Brands live in the pack so a locale stays data. If this is a DOCSTRING "
        f"quoting a ticket or a decision that names a desk: quote it from "
        f"`tools/` or the STATE contract instead (brands belong where the "
        f"locale is chosen, not where it is processed), or keep it here with the "
        f"brand elided in [brackets] and the reason on the same line. If it is "
        f"CODE: read the name off the door or the source catalog — this package "
        f"must work for a locale nobody has written yet.")


def test_no_place_name_from_the_grammar_appears_in_the_locale_modules():
    """The same rule for places: no home town hardcoded in worker defaults."""
    places = {p.split(",")[0].strip() for p in _pack_dict()["query_grammar"]["places"]}
    module_dir = os.path.dirname(os.path.abspath(lp.__file__))
    offenders = []
    for name in sorted(os.listdir(module_dir)):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(module_dir, name), encoding="utf-8") as fh:
            text = fh.read()
        offenders += [f"{name}: {p!r}" for p in places if p and p in text]
    assert offenders == [], f"place literal(s) in code: {offenders}"


def test_hunt_has_no_default_locale():
    with pytest.raises(TypeError):
        lp.hunt()  # noqa: B015 — a caller that names no locale must not get one


# --- everything a pack can get wrong is refused at load ----------------------

def test_an_unknown_locale_raises_and_names_what_is_available():
    with pytest.raises(lp.LocalePackError) as exc:
        lp.hunt("us-tx-nowhere")
    assert "us-tx-nowhere" in str(exc.value)
    assert CAPCOG in str(exc.value)


@pytest.mark.parametrize("bad", ["../secrets", "a/b", ".", "..", ""])
def test_a_locale_id_may_not_steer_the_path(bad):
    with pytest.raises(lp.LocalePackError):
        lp.load_pack(bad)


def test_a_pack_filed_under_the_wrong_name_is_refused(tmp_path):
    data = _pack_dict()
    data["locale"]["locale_id"] = "us-tx-elsewhere"
    with pytest.raises(lp.LocalePackError) as exc:
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))
    assert "us-tx-elsewhere" in str(exc.value)


def test_an_unknown_door_type_is_refused_not_skipped(tmp_path):
    data = _pack_dict()
    data["doors"][0]["door_type"] = "back_alley"
    with pytest.raises(lp.LocalePackError) as exc:
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))
    assert "back_alley" in str(exc.value)


def test_an_unknown_intake_is_refused(tmp_path):
    data = _pack_dict()
    data["doors"][0]["intake"] = "carrier_pigeon"
    with pytest.raises(lp.LocalePackError):
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))


def test_an_unknown_evidence_grade_is_refused(tmp_path):
    data = _pack_dict()
    data["doors"][0]["evidence"] = "trust_me"
    with pytest.raises(lp.LocalePackError):
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))


def test_a_closed_door_with_no_stated_reason_is_refused(tmp_path):
    """An unexplained absence is how coverage silently narrows."""
    data = _pack_dict()
    door = next(d for d in data["doors"] if not d["public"])
    door["blocked_reason"] = None
    with pytest.raises(lp.LocalePackError) as exc:
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))
    assert "blocked_reason" in str(exc.value)


def test_a_readable_door_carrying_a_block_reason_is_refused(tmp_path):
    data = _pack_dict()
    door = next(d for d in data["doors"]
                if d["public"] and d["intake"] != "none"
                and d["door_type"] not in ("wall", "junk"))
    door["blocked_reason"] = "no idea"
    with pytest.raises(lp.LocalePackError):
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))


def test_a_public_wall_is_a_contradiction_and_is_refused(tmp_path):
    data = _pack_dict()
    door = next(d for d in data["doors"] if d["door_type"] == "wall")
    door["public"] = True
    with pytest.raises(lp.LocalePackError) as exc:
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))
    assert "wall" in str(exc.value)


def test_a_duplicate_door_id_is_refused(tmp_path):
    data = _pack_dict()
    data["doors"].append(dict(data["doors"][0]))
    with pytest.raises(lp.LocalePackError) as exc:
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))
    assert "duplicate" in str(exc.value)


def test_an_empty_door_list_is_refused(tmp_path):
    data = _pack_dict()
    data["doors"] = []
    with pytest.raises(lp.LocalePackError):
        lp.load_pack(CAPCOG, packs_dir=_write(tmp_path, data))


def test_an_unreadable_pack_raises_rather_than_returning_nothing(tmp_path):
    (tmp_path / f"{CAPCOG}.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(lp.LocalePackError) as exc:
        lp.load_pack(CAPCOG, packs_dir=str(tmp_path))
    assert "unreadable" in str(exc.value)


def test_an_unknown_door_type_filter_raises_instead_of_returning_empty():
    with pytest.raises(lp.LocalePackError) as exc:
        lp.hunt(CAPCOG, door_types=["local_desk", "speakeasy"])
    assert "speakeasy" in str(exc.value)


def test_declared_kind_is_other_unless_the_door_scopes_exactly_one():
    doors = {d.door_id: d for d in lp.hunt(CAPCOG)}
    assert doors["kutx-concert-calendar"].declared_kind == "music"
    assert doors["austin-chronicle-eventsearch"].declared_kind == lp.KIND_OTHER
    assert doors["do512-family"].declared_kind == "family"


def test_available_locales_lists_the_shipped_pack():
    assert CAPCOG in lp.available_locales()
