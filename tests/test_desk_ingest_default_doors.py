"""The default walk is the whole public desk of the pack, not two ids.

Founder ticket, 2026-09-07: "Change DEFAULT_DOORS (and the matching
desk-ingest.yml default) so a run with no --door walks every pack door where
public is true AND intake is not none. Derive the list from the pack file. Do
not hard-code Chronicle. Keep --door as an override."

WHY THESE TESTS EXIST. `tools/desk_ingest.py` shipped with

    DEFAULT_DOORS = ("austin-chronicle-eventsearch", "do512-today")

while `sources/locale_packs/us-tx-capcog.json` listed 26 doors we may legally
read. Every run therefore spent its whole budget on two of them and reported
nothing at all about the other 24 — the shape Operating Law calls a defect in
so many words ("Budget that starves all but two sources is a defect. Prefer
round-robin (few pages x many sources)"), and the shape Coverage Law calls a
missing-source defect rather than an empty locale. A constant cannot starve
quietly once a test reads the pack and counts.

Hermetic: the pack and the two workflow files are read off disk; the one run
that walks anything walks COMMITTED FIXTURES and writes nothing.
"""
from __future__ import annotations

import os
import re

import pytest

from tools.desk_ingest import default_doors, main
from worker.locale.pack import load_pack

CAPCOG = "us-tx-capcog"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "desk_ingest.py")
WORKFLOWS = (
    os.path.join(ROOT, ".github", "workflows", "desk-ingest.yml"),
    os.path.join(ROOT, ".github", "workflows", "desk-split-dryrun.yml"),
)

#: The two ids the default was frozen at, kept here ONLY as the thing a test
#: refuses. Nothing else in this file may name a door.
THE_STARVED_PAIR = ("austin-chronicle-eventsearch", "do512-today")


@pytest.fixture(scope="module")
def pack():
    return load_pack(CAPCOG)


def test_the_default_is_no_longer_the_two_door_tuple(pack):
    """The defect itself, pinned: two doors out of a pack of many."""
    doors = default_doors(CAPCOG)
    assert tuple(sorted(doors)) != tuple(sorted(THE_STARVED_PAIR)), (
        "the default walk is still exactly the two desks the starve defect "
        "named — a run with no --door must walk the pack, not a pair")
    assert len(doors) > 2, (
        f"{len(doors)} door(s) in the default walk: a locale pack with "
        f"{len(pack.doors)} doors cannot be covered by a handful")


def test_the_default_is_every_public_door_with_a_read_path(pack):
    """The founder's predicate, over the pack's own data.

    `public is true AND intake is not none`, carrying the door TYPE with it —
    `wall` is class D (never fetched) and `junk` is a copy farm (a lead, never
    a listing), and neither is a door a happening may be listed from
    (ONE-LIVE-TRUST.md). In this pack the type leg subtracts nothing: every
    door that is public with a read path is already one of the four listable
    types, which is what makes the two readings the same list here.
    """
    expected = [d.door_id for d in pack.doors
                if d.public and d.intake != "none"
                and d.door_type in ("local_desk", "civic", "official_list",
                                    "marketplace")]
    assert sorted(default_doors(CAPCOG)) == sorted(expected)
    # And the founder's sentence on its own terms, so a future pack that puts a
    # junk door behind a read path is a FAILURE HERE rather than a silent
    # narrowing of what the default covers.
    loose = [d.door_id for d in pack.doors if d.public and d.intake != "none"]
    assert sorted(loose) == sorted(expected), (
        "this pack now has a public, readable door of a type a happening may "
        "not be listed from — decide deliberately whether the default walks "
        "it, do not let this test paper over the difference")


def test_no_door_the_pack_shuts_is_in_the_default(pack):
    """Class D and the copy farms stay out — including the licensed feed.

    `ticketmaster-discovery` is `public: false` / `intake: none` in the pack
    and is imported through its own licensed API job. A default that walked it
    would HTML-fetch a door we hold a licence to read properly.
    """
    walked = set(default_doors(CAPCOG))
    for door in pack.doors:
        if door.public and door.intake != "none":
            continue
        assert door.door_id not in walked, (
            f"{door.door_id} is public={door.public} intake={door.intake} in "
            f"the pack and must never be in the default walk")


def test_the_list_is_derived_from_the_pack_not_typed_into_python(pack):
    """No door id is a literal in the tool — the pack file is the source.

    Locale Launch Law §5: peculiarities live in pack JSON, never in Python.
    A default typed here would have to be edited for every locale, which is
    how "Austin" ends up in a worker default.
    """
    source = open(TOOL, encoding="utf-8").read()
    named = [d.door_id for d in pack.doors if d.door_id in source]
    assert not named, (
        f"tools/desk_ingest.py names {named} — derive the list from the pack "
        f"file instead")


def test_a_second_locale_needs_no_code(pack, tmp_path):
    """`default_doors` reads the locale it is given, and nothing else."""
    import json

    raw = json.load(open(os.path.join(ROOT, "sources", "locale_packs",
                                      f"{CAPCOG}.json"), encoding="utf-8"))
    raw["locale"]["locale_id"] = "zz-elsewhere"
    keep = {d.door_id for d in pack.doors if d.public and d.intake != "none"}
    raw["doors"] = [d for d in raw["doors"] if d["door_id"] in keep][:3]
    (tmp_path / "zz-elsewhere.json").write_text(json.dumps(raw), encoding="utf-8")

    from worker.locale.pack import public_desks
    assert len(public_desks("zz-elsewhere", packs_dir=str(tmp_path))) == 3


def test_both_workflows_default_to_the_whole_pack():
    """A dispatch with the fields untouched walks every public door.

    `all` is how a dispatch says "no --door"; the step blanks that one word
    and passes whatever is left as `--door` arguments, so the default reaches
    the tool as an EMPTY door list and the tool's own pack-derived default
    takes over. It is a word rather than an empty string because
    `tools/workflow_env_lint.py` requires a terminating guard on every
    expression-backed value, and an input that arrives empty must still be a
    misconfigured dispatch rather than a silent change of scope.

    A door id typed into a default here would re-create the starve defect one
    layer out, where no Python test would ever see it.
    """
    for path in WORKFLOWS:
        name = os.path.basename(path)
        text = open(path, encoding="utf-8").read()
        block = re.search(r"^      doors:\s*$\n(?:.*\n)*?^        default: (.*)$",
                          text, re.MULTILINE)
        assert block, f"{name} no longer declares a doors default"
        assert block.group(1).strip().strip('"\'') == "all", (
            f"{name} defaults `doors` to {block.group(1).strip()} — `all` is "
            f"the value that walks the whole pack")
        assert "s/^all$//" in text, (
            f"{name} no longer maps the `all` sentinel to an empty door list, "
            f"so its default would reach the tool as a door id")
        assert ': "${IN_DOORS:?' in text, (
            f"{name} dropped the non-empty guard on the doors input")
        for door_id in THE_STARVED_PAIR:
            assert door_id not in text, (
                f"{name} still names {door_id}")


# --------------------------------------------------------------------------
# The founder's dry-run table
# --------------------------------------------------------------------------

FOUNDER_COLUMNS = ("door_id", "door_type", "fetched?", "pages", "rows_split",
                   "mash_n", "dated_n", "placed_n", "403_n", "unsplit_n")


def _fixture_report(capsys, *argv) -> str:
    assert main(list(argv)) == 0
    return capsys.readouterr().out


def _walk_rows(out: str):
    """The founder's table, parsed: its header row and its body rows.

    Read as the block under the `| door_id |` header up to the first blank
    line, so no other table in the report can be mistaken for this one.
    """
    lines = out.splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.startswith("| door_id |"))
    header = [c.strip() for c in lines[start].strip("|").split("|")]
    rows = []
    for line in lines[start + 2:]:
        if not line.strip():
            break
        rows.append([c.strip() for c in line.strip("|").split("|")])
    return header, rows


def test_the_walk_table_is_one_row_per_door_walked(capsys):
    """The artifact the founder reads: his columns, his order, one row a door.

    A FIXTURE run walks the doors somebody committed pages for, so the row
    count here is the number of doors this run could actually walk — which is
    the point of the column `fetched?`: a door that opened nothing says so.
    """
    header, rows = _walk_rows(_fixture_report(capsys, "--dry-run",
                                              "--follow-pages", "0"))
    assert header == list(FOUNDER_COLUMNS)
    assert rows, "the walk table printed no door"
    for cells in rows:
        assert len(cells) == len(FOUNDER_COLUMNS), cells
        assert cells[1] in ("local_desk", "civic", "official_list",
                            "marketplace"), f"door_type is not a trusted door: {cells}"
        assert cells[2] in ("yes", "no"), f"fetched? is not a yes/no: {cells}"
        assert cells[5] == "0", (
            f"mash_n must be 0 — a row addressed by the list's own url keys a "
            f"whole desk to one identity: {cells}")


def test_a_walled_door_reads_as_unknown_never_as_zero_events(capsys):
    """403 is triage, not an empty calendar (Operating Law, effectiveness 4)."""
    out = _fixture_report(capsys, "--dry-run", "--follow-pages", "0")
    assert "UNKNOWN" in out
    assert "403_n" in out


def test_a_door_we_cannot_walk_is_named_and_does_not_delete_the_others(capsys):
    """One unwalkable door is that door's defect, not the run's.

    Registration used to stop the whole run at the first door with no catalog
    row. With two named desks that was a tripwire; with a pack of 26 it means
    one unlisted publisher deletes every other desk from the night. The door is
    REPORTED by name with its remedy, nothing is written for it, and the walk
    goes on.
    """
    out = _fixture_report(capsys, "--dry-run", "--follow-pages", "0")
    assert "were NOT walked" in out, (
        "the doors this run could not walk are not named anywhere in the "
        "report — a shorter list is the one thing a coverage report may not "
        "be quiet about")
    assert "## 4. The write plan" in out, "the run stopped instead of walking on"


def test_naming_doors_overrides_the_default_rather_than_adding_to_it(capsys):
    """`--door` is still the override the founder asked to keep."""
    only = THE_STARVED_PAIR[1]
    _header, rows = _walk_rows(_fixture_report(
        capsys, "--dry-run", "--door", only, "--follow-pages", "0"))
    assert [cells[0] for cells in rows] == [f"`{only}`"], (
        f"a run naming one door walked {[cells[0] for cells in rows]}")
